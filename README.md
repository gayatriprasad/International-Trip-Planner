# International Trip Planner  
**Agentic Travel Planning System – Phase 1**

---

## Why this project exists

This project is **not** a full travel booking product.

It is a **production-minded, agentic system** built to explore:
- How modern AI agents coordinate via tools
- How to design reliable, observable, replayable agent workflows
- How industry-grade systems balance intelligence with determinism

The goal is **depth over features** — understanding agent architecture, tool contracts, and operational quirks at a staff / AI architect level.

---

## What Phase 1 delivers

Phase 1 implements a **tool-driven agent system** composed of three services:

### 1. Orchestrator  
*(LLM-ready, policy-driven control plane)*

- Interprets user intent (deterministic in Phase 1)
- Selects and calls tools via schema-first contracts
- Enforces policy: validation, rate limits, result caps, timeouts
- Manages workflow state via explicit state machine
- Owns all writes (transaction boundary)

### 2. Flight Tool Server  
*(Stateless action layer)*

- `resolve_location(query)` → city / airport candidates
- `search_flights(legs, passengers, filters)` → normalized offers
- Provider integration is isolated here (mock + Amadeus-ready)
- No persistence, no workflow state

### 3. DB Tool Server  
*(Persistence + audit authority)*

- `save_trip`, `save_search`, `save_offers`, `get_trip`
- Immutable audit log of every tool call (inputs + outputs)
- SQLite for MVP, designed for Postgres migration
- Orchestrator-only writes (enforced by design)

---

## Why this is an *agentic* system

This is **not** just microservices.

The system is agentic because:
- A central agent (orchestrator) reasons over **state, policy, and tools**
- Tools are capability-focused, schema-described, and discoverable
- Execution is **intent → plan → action → observe → persist**
- All actions are replayable and auditable
- Intelligence can be added *without breaking determinism*

Phase 1 intentionally prioritizes **control and trust** over intelligence.

---

## Phase 1 Scope

### Supported
- One-way, round-trip, simple multi-city (≤2 legs)
- Tool registry with strict request/response schemas
- Input validation + output caps + timeouts
- Full audit trail of tool invocations
- Replay-friendly persistence model

### Explicit non-goals (Phase 1)
- Payments, ticketing, hotel booking
- Distributed transactions (workflow events + DB transactions only)
- Dynamic plugin loading (static tools, registry generated at startup)
- LLM-based reasoning in execution path

---

## Architecture (Phase 1)

Key design decisions:
- **Orchestrator-only persistence** (single transaction owner)
- Tools are stateless and side-effect free (except DB tools)
- Workflow modeled as explicit states:

```
TRIP_DRAFTED
  → FLIGHTS_FETCHED
    → OFFERS_SCORED
      → PRESENTED
```

Documentation:
- Architecture: `docs/architecture/phase1-overview.md`
- ADR: `docs/decisions/adr-001-orchestrator-writes.md`

---

## Tool contracts & schemas

All contracts are schema-first and validated at runtime.

- Pydantic models:  
  `packages/schemas/travel_schemas/models.py`

- Tool request / response schemas:  
  `packages/schemas/travel_schemas/tool_schemas.py`

Schemas act as:
- API contracts
- Validation layer
- Documentation
- Replay guarantees

---

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Health checks:
- Orchestrator: http://localhost:8000/health
- Flight tool: http://localhost:8001/health
- DB tool: http://localhost:8002/health

---

## Phase roadmap (high level)

**Phase 2A – Trust Infrastructure**
- Redis for rate limiting & circuit breaker state
- OpenTelemetry tracing (Jaeger)
- Offline evaluation harness (regression + safety tests)

**Phase 2B – Intelligence Layer**
- LLM-based intent parsing with schema validation + fallback
- Multi-city planning logic
- User preference memory

Each phase builds only after the previous is observable and measurable.

---

## Intended audience

- Engineers exploring agentic architectures
- AI / ML engineers moving into systems roles
- Staff-level interview preparation
- Anyone interested in how agents work *beyond demos*
