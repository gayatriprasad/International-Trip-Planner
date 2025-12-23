from __future__ import annotations
import json
import uuid
from fastapi import FastAPI
from shared.logging import configure_logging, get_logger
from travel_schemas.tool_schemas import (
    ToolRegistryResponse, RegistryTool,
    SaveTripRequest, SaveTripResponse,
    SaveSearchRequest, SaveSearchResponse,
    SaveOffersRequest, GetTripResponse,
    LogToolCallRequest
)
from .config import LOG_LEVEL
from .db import init_db, get_conn

configure_logging(LOG_LEVEL)
log = get_logger()

app = FastAPI(title="DB Tool Server", version="v1")

@app.on_event("startup")
def _startup():
    init_db()
    log.info("db_initialized")

@app.get("/health")
def health():
    return {"ok": True, "service": "db_tool"}

@app.get("/tools/registry", response_model=ToolRegistryResponse)
def registry():
    tools = [
        RegistryTool(
            name="save_trip",
            description="Create a trip draft",
            input_schema=SaveTripRequest.model_json_schema(),
            output_schema=SaveTripResponse.model_json_schema(),
        ),
        RegistryTool(
            name="save_search",
            description="Store a search request for a trip",
            input_schema=SaveSearchRequest.model_json_schema(),
            output_schema=SaveSearchResponse.model_json_schema(),
        ),
        RegistryTool(
            name="save_offers",
            description="Store flight offers for a search",
            input_schema=SaveOffersRequest.model_json_schema(),
            output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        ),
        RegistryTool(
            name="log_tool_call",
            description="Audit log tool invocations (traceable replay)",
            input_schema=LogToolCallRequest.model_json_schema(),
            output_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        ),
        RegistryTool(
            name="get_trip",
            description="Fetch trip + searches + offers",
            input_schema={"type": "object", "properties": {"trip_id": {"type": "string"}}, "required": ["trip_id"]},
            output_schema=GetTripResponse.model_json_schema(),
        ),
    ]
    return ToolRegistryResponse(tools=tools)

@app.post("/tools/save_trip", response_model=SaveTripResponse)
def save_trip(req: SaveTripRequest):
    trip_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute(
        "INSERT INTO trips(trip_id, session_id, trip_type, status) VALUES (?, ?, ?, ?)",
        (trip_id, req.session_id, req.trip_type, req.status),
    )
    conn.commit()
    conn.close()
    return SaveTripResponse(trip_id=trip_id)

@app.post("/tools/save_search", response_model=SaveSearchResponse)
def save_search(req: SaveSearchRequest):
    search_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute(
        "INSERT INTO searches(search_id, trip_id, provider, params_json, query_hash) VALUES (?, ?, ?, ?, ?)",
        (search_id, req.trip_id, req.provider, json.dumps(req.params_json), req.query_hash),
    )
    conn.commit()
    conn.close()
    return SaveSearchResponse(search_id=search_id)

@app.post("/tools/save_offers")
def save_offers(req: SaveOffersRequest):
    conn = get_conn()
    for offer in req.offers:
        conn.execute(
            "INSERT INTO offers(search_id, offer_json) VALUES (?, ?)",
            (req.search_id, json.dumps(offer)),
        )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.post("/tools/log_tool_call")
def log_tool_call(req: LogToolCallRequest):
    conn = get_conn()
    conn.execute(
        "INSERT INTO tool_calls(trace_id, tool_name, input_json, output_json, latency_ms, status) VALUES (?, ?, ?, ?, ?, ?)",
        (req.trace_id, req.tool_name, json.dumps(req.input_json), json.dumps(req.output_json), req.latency_ms, req.status),
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/tools/get_trip/{trip_id}", response_model=GetTripResponse)
def get_trip(trip_id: str):
    conn = get_conn()
    trip = conn.execute("SELECT * FROM trips WHERE trip_id=?", (trip_id,)).fetchone()
    searches = conn.execute("SELECT * FROM searches WHERE trip_id=? ORDER BY created_at", (trip_id,)).fetchall()

    offers = []
    for s in searches:
        rows = conn.execute("SELECT offer_json FROM offers WHERE search_id=? ORDER BY created_at", (s["search_id"],)).fetchall()
        for r in rows:
            offers.append(json.loads(r["offer_json"]))

    conn.close()
    return GetTripResponse(
        trip=dict(trip) if trip else {},
        searches=[dict(x) for x in searches],
        offers=offers,
    )

@app.get("/tools/get_trace/{trace_id}")
def get_trace(trace_id: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT tool_name, input_json, output_json, latency_ms, status, created_at "
        "FROM tool_calls WHERE trace_id=? ORDER BY created_at",
        (trace_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return {}

    return {
        "trace_id": trace_id,
        "steps": [dict(r) for r in rows],
    }
