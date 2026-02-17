# apps/orchestrator/app/main.py

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

# --- LangGraph Imports ---
from .graph import app as graph_app
# Import CityResearch here
from .state import FlightSearchIn, GraphState, CityResearch 
# --- End LangGraph Imports ---

from shared.logging import configure_logging, get_logger
from shared.redis_client import RedisClient
from shared.limits import RedisRateLimiter, RedisCircuitBreaker

logger = get_logger(__name__)

FLIGHT_TOOL_URL = os.getenv("FLIGHT_TOOL_URL", "http://localhost:8001")
DB_TOOL_URL = os.getenv("DB_TOOL_URL", "http://localhost:8002")

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
CB_FAIL_THRESHOLD = int(os.getenv("CB_FAIL_THRESHOLD", "5"))
CB_WINDOW_SECONDS = int(os.getenv("CB_WINDOW_SECONDS", "60"))
CB_OPEN_SECONDS = int(os.getenv("CB_OPEN_SECONDS", "60"))


class FlightSearchOut(BaseModel):
    trace_id: str
    trip_id: str
    origin: str
    destination: str
    results: list[dict]
    research: Optional[CityResearch] = None


app = FastAPI(title="orchestrator", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    configure_logging()
    logger.info("orchestrator starting")

    app.state.redis = RedisClient.from_env()
    r = app.state.redis.client()
    app.state.rate_limiter = RedisRateLimiter(r, per_minute=RATE_LIMIT_PER_MINUTE)
    app.state.cbreaker = RedisCircuitBreaker(
        r,
        fail_threshold=CB_FAIL_THRESHOLD,
        window_seconds=CB_WINDOW_SECONDS,
        open_seconds=CB_OPEN_SECONDS,
    )

    ok = await app.state.redis.ping()
    logger.info("redis ping ok=%s", ok)


@app.on_event("shutdown")
async def shutdown() -> None:
    await app.state.redis.close()


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "service": "orchestrator"}


def _user_key(req: Request, payload_session_id: Optional[str]) -> str:
    if payload_session_id:
        return f"sess:{payload_session_id}"
    client_host = req.client.host if req.client else "unknown"
    return f"ip:{client_host}"


async def _tool_post(
    tool_name: str,
    url: str,
    payload: dict,
    trace_id: str,
    timeout_s: float,
) -> dict:
    # This entire function, with its robust circuit breaker logic, remains unchanged.
    # It is a dependency that we will inject into our graph.
    allowed, state = await app.state.cbreaker.allow(tool_name)
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail={"error": "tool_unavailable", "tool": tool_name, "circuit": state},
        )

    headers = {"x-trace-id": trace_id}
    started = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        await app.state.cbreaker.on_success(tool_name)
        return data
    except Exception as e:
        await app.state.cbreaker.on_failure(tool_name)
        elapsed_ms = int((time.time() - started) * 1000)
        logger.warning(
            "tool_call_failed tool=%s state=%s latency_ms=%s err=%s",
            tool_name,
            state,
            elapsed_ms,
            repr(e),
        )
        raise HTTPException(
            status_code=502,
            detail={"error": "tool_call_failed", "tool": tool_name, "circuit": await app.state.cbreaker.state(tool_name)},
        )


@app.post("/v1/flight_search", response_model=FlightSearchOut)
async def flight_search(req: Request, body: FlightSearchIn) -> FlightSearchOut:
    trace_id = str(uuid.uuid4())
    user_key = _user_key(req, body.session_id)

    # 1. Rate limit at the boundary (unchanged)
    rl = await app.state.rate_limiter.check(user_key=user_key, tool="flight_search")
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "limit_per_minute": rl.limit,
                "reset_in_seconds": rl.reset_in_seconds,
            },
        )

    # 2. Define the initial state for the graph
    initial_state: GraphState = {
        "request_body": body,
        "trace_id": trace_id,
        "origin_code": None,
        "destination_code": None,
        "trip_id": None,
        "search_id": None,
        "flight_results": [],
        "error": None,
    }

    # 3. Define the configuration to pass runtime dependencies to the nodes
    # This is how our nodes get access to the robust `_tool_post` function.
    config = {"configurable": {"tool_post": _tool_post}}

    # 4. Invoke the graph and let it orchestrate the tool calls
    final_state = await graph_app.ainvoke(initial_state, config)

    # 5. Handle the result from the graph
    if final_state.get("error"):
        logger.error("Graph execution failed with error: %s", final_state["error"])
        # You can create more specific error codes based on the error message
        raise HTTPException(
            status_code=500,
            detail={"error": "workflow_failed", "details": final_state["error"], "trace_id": trace_id}
        )

    # 6. Construct the final response from the successful graph state
    return FlightSearchOut(
        trace_id=trace_id,
        trip_id=final_state["trip_id"],
        origin=final_state["origin_code"],
        destination=final_state["destination_code"],
        results=final_state["flight_results"],
    )
