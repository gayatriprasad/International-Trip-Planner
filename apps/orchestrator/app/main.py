from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

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


class FlightSearchIn(BaseModel):
    # allow city names too; orchestrator will resolve to IATA via flight_tool
    origin: str = Field(min_length=2, max_length=64)
    destination: str = Field(min_length=2, max_length=64)
    date: str = Field(min_length=10, max_length=10, description="YYYY-MM-DD")
    session_id: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=50)
    max_stops: int = Field(default=2, ge=0, le=3)
    max_price: Optional[float] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)


class FlightSearchOut(BaseModel):
    trace_id: str
    trip_id: str
    origin: str
    destination: str
    results: list[dict]


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
    # Prefer explicit session_id, otherwise IP-based.
    # (For local dev: stable enough.)
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
    # Circuit breaker gating
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

    # Rate limit at orchestrator boundary
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

    # 1) Resolve origin/destination to IATA codes via flight_tool resolve_location
    origin_res = await _tool_post(
        tool_name="flight_tool.resolve_location",
        url=f"{FLIGHT_TOOL_URL}/tools/resolve_location",
        payload={"query": body.origin},
        trace_id=trace_id,
        timeout_s=2.0,
    )
    dest_res = await _tool_post(
        tool_name="flight_tool.resolve_location",
        url=f"{FLIGHT_TOOL_URL}/tools/resolve_location",
        payload={"query": body.destination},
        trace_id=trace_id,
        timeout_s=2.0,
    )

    if not origin_res.get("candidates") or not dest_res.get("candidates"):
        raise HTTPException(status_code=400, detail={"error": "could_not_resolve_location"})

    origin_code = origin_res["candidates"][0]["code"]
    dest_code = dest_res["candidates"][0]["code"]

    # 2) Save trip draft in db_tool
    trip = await _tool_post(
        tool_name="db_tool.save_trip",
        url=f"{DB_TOOL_URL}/tools/save_trip",
        payload={"session_id": body.session_id or "anonymous", "trip_type": "one-way", "status": "draft"},
        trace_id=trace_id,
        timeout_s=5.0,
    )
    trip_id = trip["trip_id"]

    # 3) Call flight_tool search_flights
    flight_payload = {
        "legs": [{"origin": origin_code, "destination": dest_code, "date": body.date}],
        "max_results": body.max_results,
        "max_stops": body.max_stops,
        "max_price": body.max_price,
        "currency": body.currency,
    }
    results = await _tool_post(
        tool_name="flight_tool.search_flights",
        url=f"{FLIGHT_TOOL_URL}/tools/search_flights",
        payload=flight_payload,
        trace_id=trace_id,
        timeout_s=5.0,
    )

    # 4) Persist search + offers in db_tool
    # query_hash is computed by db_tool caller usually; we keep simple here.
    query_hash = f"{origin_code}:{dest_code}:{body.date}:{body.max_results}:{body.max_stops}:{body.max_price}:{body.currency}"
    saved_search = await _tool_post(
        tool_name="db_tool.save_search",
        url=f"{DB_TOOL_URL}/tools/save_search",
        payload={"trip_id": trip_id, "provider": "flight_tool", "params_json": flight_payload, "query_hash": query_hash},
        trace_id=trace_id,
        timeout_s=5.0,
    )
    search_id = saved_search["search_id"]

    await _tool_post(
        tool_name="db_tool.save_offers",
        url=f"{DB_TOOL_URL}/tools/save_offers",
        payload={"search_id": search_id, "offers": results.get("flights", [])},
        trace_id=trace_id,
        timeout_s=5.0,
    )

    return FlightSearchOut(
        trace_id=trace_id,
        trip_id=trip_id,
        origin=origin_code,
        destination=dest_code,
        results=results.get("flights", []),
    )
