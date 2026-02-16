# apps/orchestrator/app/state.py

from typing import TypedDict, List, Any, Optional
from pydantic import BaseModel, Field

# This is the initial input from the user, matching your existing Pydantic model
# We can keep it here or import it from main, but defining it here is cleaner for the graph.
class FlightSearchIn(BaseModel):
    origin: str = Field(min_length=2, max_length=64)
    destination: str = Field(min_length=2, max_length=64)
    date: str = Field(min_length=10, max_length=10, description="YYYY-MM-DD")
    session_id: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=50)
    max_stops: int = Field(default=2, ge=0, le=3)
    max_price: Optional[float] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)


# This is the central state of our graph.
# It's the single object that gets passed around and updated by each node.
class GraphState(TypedDict):
    # Input state
    request_body: FlightSearchIn
    trace_id: str
    
    # Intermediate state, populated by nodes
    origin_code: Optional[str]
    destination_code: Optional[str]
    trip_id: Optional[str]
    search_id: Optional[str]
    
    # Final output state
    flight_results: List[Any]

    # Centralized error handling
    error: Optional[str]
