from travel_schemas.models import AirportCandidate

# tiny MVP mapping (replace with Amadeus autocomplete later)
CITY_MAP = {
    "paris": [
        AirportCandidate(code="CDG", city="Paris", country="FR", name="Charles de Gaulle"),
        AirportCandidate(code="ORY", city="Paris", country="FR", name="Orly"),
    ],
    "london": [
        AirportCandidate(code="LHR", city="London", country="GB", name="Heathrow"),
        AirportCandidate(code="LGW", city="London", country="GB", name="Gatwick"),
    ],
    "new york": [
        AirportCandidate(code="JFK", city="New York", country="US", name="John F. Kennedy"),
        AirportCandidate(code="EWR", city="Newark", country="US", name="Newark Liberty"),
        AirportCandidate(code="LGA", city="New York", country="US", name="LaGuardia"),
    ],
    "hyderabad": [AirportCandidate(code="HYD", city="Hyderabad", country="IN", name="RGIA")],
    "dubai": [AirportCandidate(code="DXB", city="Dubai", country="AE", name="Dubai International")],
}

def resolve(query: str):
    q = query.strip().lower()
    if q in CITY_MAP:
        return CITY_MAP[q]
    # direct IATA code fallback
    if len(q) == 3 and q.isalpha():
        return [AirportCandidate(code=q.upper(), city=q.upper())]
    return []
