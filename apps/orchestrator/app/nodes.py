# apps/orchestrator/app/nodes.py

import os
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from .state import GraphState

# We get the URLs from the environment, just like in main.py
FLIGHT_TOOL_URL = os.getenv("FLIGHT_TOOL_URL", "http://localhost:8001")
DB_TOOL_URL = os.getenv("DB_TOOL_URL", "http://localhost:8002")

async def resolve_locations(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Resolves origin and destination names to IATA codes by calling the flight_tool.
    """
    print("---NODE: RESOLVING LOCATIONS---")
    tool_post = config["configurable"]["tool_post"]
    origin_query = state["request_body"].origin
    dest_query = state["request_body"].destination
    trace_id = state["trace_id"]

    try:
        origin_res = await tool_post(
            "flight_tool.resolve_location", f"{FLIGHT_TOOL_URL}/tools/resolve_location",
            {"query": origin_query}, trace_id, 2.0
        )
        dest_res = await tool_post(
            "flight_tool.resolve_location", f"{FLIGHT_TOOL_URL}/tools/resolve_location",
            {"query": dest_query}, trace_id, 2.0
        )

        if not origin_res.get("candidates") or not dest_res.get("candidates"):
            return {"error": "Could not resolve one or both locations."}

        return {
            "origin_code": origin_res["candidates"][0]["code"],
            "destination_code": dest_res["candidates"][0]["code"],
        }
    except Exception as e:
        return {"error": f"Failed in resolve_locations: {repr(e)}"}


async def save_trip_draft(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """Saves the trip to the database via the db_tool and gets a trip_id."""
    print("---NODE: SAVING TRIP DRAFT---")
    tool_post = config["configurable"]["tool_post"]
    try:
        trip = await tool_post(
            "db_tool.save_trip", f"{DB_TOOL_URL}/tools/save_trip",
            {"session_id": state["request_body"].session_id or "anonymous", "trip_type": "one-way", "status": "draft"},
            state["trace_id"], 5.0
        )
        return {"trip_id": trip["trip_id"]}
    except Exception as e:
        return {"error": f"Failed in save_trip_draft: {repr(e)}"}


async def search_and_persist_flights(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    A single logical node that performs the flight search and then persists the
    search request and the resulting offers to the database.
    """
    print("---NODE: SEARCHING AND PERSISTING FLIGHTS---")
    tool_post = config["configurable"]["tool_post"]
    body = state["request_body"]
    
    # 1. Search for flights
    flight_payload = {
        "legs": [{"origin": state["origin_code"], "destination": state["destination_code"], "date": body.date}],
        "passengers": {"adults": 1}, # Example, can be enhanced
        "max_results": body.max_results,
        "max_stops": body.max_stops,
        "max_price": body.max_price,
        "currency": body.currency,
    }
    try:
        results = await tool_post(
            "flight_tool.search_flights", f"{FLIGHT_TOOL_URL}/tools/search_flights",
            flight_payload, state["trace_id"], 5.0
        )
        
        # 2. Persist the search
        query_hash = f"{state['origin_code']}:{state['destination_code']}:{body.date}" # Simplified hash
        saved_search = await tool_post(
            "db_tool.save_search", f"{DB_TOOL_URL}/tools/save_search",
            {"trip_id": state["trip_id"], "provider": "flight_tool", "params_json": flight_payload, "query_hash": query_hash},
            state["trace_id"], 5.0
        )
        search_id = saved_search["search_id"]

        # 3. Persist the offers
        flight_offers = results.get("flights", [])
        await tool_post(
            "db_tool.save_offers", f"{DB_TOOL_URL}/tools/save_offers",
            {"search_id": search_id, "offers": flight_offers},
            state["trace_id"], 5.0
        )

        return {
            "search_id": search_id,
            "flight_results": flight_offers
        }
    except Exception as e:
        return {"error": f"Failed in search_and_persist_flights: {repr(e)}"}
