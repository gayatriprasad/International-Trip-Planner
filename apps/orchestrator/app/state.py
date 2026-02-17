# apps/orchestrator/app/state.py

from typing import TypedDict, List, Any, Optional
from pydantic import BaseModel, Field

class FlightSearchIn(BaseModel):
    origin: str = Field(min_length=2, max_length=64)
    destination: str = Field(min_length=2, max_length=64)
    date: str = Field(min_length=10, max_length=10, description="YYYY-MM-DD")
    session_id: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=50)
    max_stops: int = Field(default=2, ge=0, le=3)
    max_price: Optional[float] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)

class GraphState(TypedDict):
    # Input
    request_body: FlightSearchIn
    trace_id: str
    
    # Intermediate
    origin_code: Optional[str]
    destination_code: Optional[str]
    trip_id: Optional[str]
    search_id: Optional[str]
    
    # --- New Field for Phase 1.6 ---
    city_guide: Optional[str] 
    # -------------------------------

    # Output
    flight_results: List[Any]
    error: Optional[str]
