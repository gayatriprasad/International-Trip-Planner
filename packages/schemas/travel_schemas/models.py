from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, conint

class AirportCandidate(BaseModel):
    code: str = Field(..., pattern=r"^[A-Z]{3}$")
    city: str
    country: Optional[str] = None
    name: Optional[str] = None

class TripLeg(BaseModel):
    origin: str = Field(..., pattern=r"^[A-Z]{3}$")
    destination: str = Field(..., pattern=r"^[A-Z]{3}$")
    date: str = Field(..., description="YYYY-MM-DD")

class PassengerInfo(BaseModel):
    adults: conint(ge=1, le=9) = 1
    children: conint(ge=0, le=9) = 0
    infants: conint(ge=0, le=9) = 0

class FlightOffer(BaseModel):
    offer_id: str
    airline: str
    price_total: float
    currency: str = "USD"
    duration_minutes: int
    stops: int
    legs: List[TripLeg]
    source: Literal["mock", "amadeus"] = "mock"

class ToolError(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
