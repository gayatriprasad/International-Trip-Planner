from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, conint
from .models import TripLeg, FlightOffer, AirportCandidate

class RegistryTool(BaseModel):
    name: str
    description: str
    version: str = "v1"
    input_schema: dict
    output_schema: dict
    timeout_ms: int = 5000
    rate_limit: str = "n/a"

class ToolRegistryResponse(BaseModel):
    tools: List[RegistryTool]

# Flight tools
class ResolveLocationRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=64)

class ResolveLocationResponse(BaseModel):
    candidates: List[AirportCandidate]

class SearchFlightsRequest(BaseModel):
    legs: List[TripLeg] = Field(..., min_length=1, max_length=4)
    passengers: Optional[dict] = None
    max_results: conint(ge=1, le=50) = 25
    max_stops: conint(ge=0, le=3) = 2
    max_price: Optional[float] = None
    currency: str = "USD"

class SearchFlightsResponse(BaseModel):
    flights: List[FlightOffer]
    count: int
    cached: bool = False

# DB tools
class SaveTripRequest(BaseModel):
    session_id: str
    trip_type: str
    status: str = "draft"

class SaveTripResponse(BaseModel):
    trip_id: str

class LogToolCallRequest(BaseModel):
    trace_id: str
    tool_name: str
    input_json: dict
    output_json: dict
    latency_ms: int
    status: str

class SaveSearchRequest(BaseModel):
    trip_id: str
    provider: str
    params_json: dict
    query_hash: str

class SaveSearchResponse(BaseModel):
    search_id: str

class SaveOffersRequest(BaseModel):
    search_id: str
    offers: List[dict]  # store normalized offers as dict

class GetTripResponse(BaseModel):
    trip: dict
    searches: List[dict]
    offers: List[dict]
