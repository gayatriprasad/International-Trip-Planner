from __future__ import annotations
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.logging import configure_logging, get_logger
from travel_schemas.tool_schemas import (
    ToolRegistryResponse, RegistryTool,
    ResolveLocationRequest, ResolveLocationResponse,
    SearchFlightsRequest, SearchFlightsResponse
)
from travel_schemas.models import FlightOffer
from .config import LOG_LEVEL
from .location_resolver import resolve

configure_logging(LOG_LEVEL)
log = get_logger()

app = FastAPI(title="Flight Tool Server", version="v1")

@app.get("/health")
def health():
    return {"ok": True, "service": "flight_tool"}

@app.get("/tools/registry", response_model=ToolRegistryResponse)
def registry():
    tools = [
        RegistryTool(
            name="resolve_location",
            description="Resolve a city/name/IATA code into candidate airports",
            input_schema=ResolveLocationRequest.model_json_schema(),
            output_schema=ResolveLocationResponse.model_json_schema(),
            timeout_ms=2000,
            rate_limit="60/min/user",
        ),
        RegistryTool(
            name="search_flights",
            description="Search flights for 1..4 legs and return normalized offers",
            input_schema=SearchFlightsRequest.model_json_schema(),
            output_schema=SearchFlightsResponse.model_json_schema(),
            timeout_ms=5000,
            rate_limit="20/min/user",
        ),
    ]
    return ToolRegistryResponse(tools=tools)

@app.post("/tools/resolve_location", response_model=ResolveLocationResponse)
def tool_resolve_location(req: ResolveLocationRequest):
    candidates = resolve(req.query)
    return ResolveLocationResponse(candidates=candidates)

@app.post("/tools/search_flights", response_model=SearchFlightsResponse)
def tool_search_flights(req: SearchFlightsRequest):
    # MVP = mock offers (we will replace with Amadeus)
    start = time.time()

    if not req.legs:
        raise HTTPException(status_code=400, detail="legs must not be empty")

    # produce deterministic mock offers
    flights = []
    base_price = 250.0 + 50.0 * (len(req.legs) - 1)
    for i in range(req.max_results):

        flights.append(
            FlightOffer(
                offer_id=f"mock_{i}",
                airline=["AI", "EK", "BA", "LH"][i % 4],
                price_total=base_price + i * 23.5,
                currency=req.currency,
                duration_minutes=420 + i * 15,
                stops=min(req.max_stops, i % 3),
                legs=req.legs,
                source="mock",
            )
        )

    latency_ms = int((time.time() - start) * 1000)
    log.info("search_flights", legs=len(req.legs), returned=len(flights), latency_ms=latency_ms)
    return SearchFlightsResponse(flights=flights, count=len(flights), cached=False)
