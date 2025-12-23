# International-Trip-Planner

# Travel Agent System (Phase 1)

Phase-1 is a production-minded, tool-driven mini travel planning system built as **three services**:
1. **Orchestrator** (LLM + policy + routing + workflow state machine)
2. **Flight Tool Server** (location resolve + flight search wrapper)
3. **DB Tool Server** (persistence + audit log; orchestrator-only writes)

## Phase-1 Scope
- One-way / round-trip / simple multi-city (2 legs)
- Tool registry + schema-first tool calling
- Strict input validation + output caps + timeouts
- Audit trail of every tool call
- Replay-friendly storage of tool I/O (via DB tool)

Non-goals (Phase 1):
- Payments, ticketing, hotel booking
- Distributed transactions (we use workflow events + DB transactions only)
- Dynamic plugin loading (static tools, registry generated at startup)

## Architecture (Phase 1)
- **Orchestrator-only persistence**: only the orchestrator calls DB write tools.
- Tools are **side-effect-free** except DB tools.
- Workflow uses evented state:
  `TRIP_DRAFTED -> FLIGHTS_FETCHED -> OFFERS_SCORED -> PRESENTED`

See: `docs/architecture/phase1-overview.md`  
ADR: `docs/decisions/adr-001-orchestrator-writes.md`

## Services
### Orchestrator (`apps/orchestrator`)
- Routes user intent to tools
- Validates inputs against schema
- Enforces policy (rate limit budgets, result caps, timeouts)
- Stores workflow state via DB tool

### Flight Tool (`apps/flight_tool`)
- `resolve_location(query)` -> airports/candidates
- `search_flights(legs, pax, cabin, filters)` -> normalized offers
- Provider integration is isolated here (Amadeus in v1)

### DB Tool (`apps/db_tool`)
- `save_trip`, `save_search`, `save_offers`, `get_trip`
- `append_audit_event`, `log_tool_call`
- SQLite for MVP, designed to migrate to Postgres

## Tool Contracts
Schemas live in `packages/schemas`.
- Pydantic models: `packages/schemas/travel_schemas/models.py`
- Tool request/response: `packages/schemas/travel_schemas/tool_schemas.py`

## Quickstart (Docker)
1) Copy env:
```bash
cp .env.example .env
