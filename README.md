# International Trip Planner

**Agentic Travel Planning System – Phase 1.5**

## Why this project exists

This project is not a full travel booking product. It is a production-minded, agentic system built to explore:

*   **How modern AI agents coordinate via tools**
*   **How to design reliable, observable, replayable agent workflows**
*   **How industry-grade systems balance intelligence with determinism**

The goal is depth over features — understanding agent architecture, tool contracts, and operational quirks at a Staff / AI Architect level.

## What Phase 1.5 Delivers (Current State)

Phase 1.5 refactors the core orchestration engine to use **LangGraph**, moving from a custom state machine to an industry-standard, graph-based workflow. This enables deep observability and easier extensibility for future agents.

### 1. Orchestrator (LangGraph-Powered)
*   **Workflow Engine:** Uses `langgraph.graph.StateGraph` to manage the trip planning lifecycle.
*   **Observability:** Native integration with **LangSmith** for full trace visualization of every node execution.
*   **Resilience:** Retains the custom Redis-backed Rate Limiting and Circuit Breakers from Phase 1.

### 2. Flight Tool Server (Stateless Action Layer)
*   `resolve_location(query)` → city / airport candidates
*   `search_flights(legs, passengers, filters)` → normalized offers
*   Provider integration is isolated here (mock + Amadeus-ready).

### 3. DB Tool Server (Persistence + Audit)
*   Immutable audit log of every tool call (inputs + outputs).
*   SQLite for MVP, designed for Postgres migration.

### 4. Infrastructure Services
*   **Redis:** Now required for distributed rate limiting and circuit breaker state.

## Architecture

The system follows a **Controller-Worker** pattern where the Orchestrator (Controller) executes a directed graph of tasks, delegating actual work to stateless Tool Servers (Workers).

**The Workflow (LangGraph):**
`START` → `resolve_locations` → `save_trip_draft` → `search_and_persist_flights` → `END`

## Quickstart (Docker)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/gayatriprasad/International-Trip-Planner.git
    cd International-Trip-Planner
    ```

2.  **Configure Environment:**
    Create a `.env` file in the root directory. You can copy the example:
    ```bash
    cp .env.example .env
    ```
    **Crucial:** Open `.env` and add your **LangSmith API Key** to enable tracing.
    ```bash
    LANGCHAIN_API_KEY=lsv2_...
    LANGCHAIN_TRACING_V2=true
    ```

3.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4.  **Test the API:**
    ```bash
    curl -X POST "http://localhost:8000/v1/flight_search"          -H "Content-Type: application/json"          -d '{
               "origin": "New York",
               "destination": "London",
               "date": "2025-06-15",
               "session_id": "test-session-1"
             }'
    ```

5.  **Observe in LangSmith:**
    Go to your LangSmith project (`International-Trip-Planner`) to see the graph execution trace, inputs, and outputs for each node.

## Tool Contracts & Schemas

All contracts are schema-first and validated at runtime using Pydantic.
*   **Location:** `packages/schemas/travel_schemas/`

## Roadmap

*   **Phase 1:** Basic Orchestrator & Tool Registry ✅
*   **Phase 1.5:** LangGraph Refactor & LangSmith Tracing ✅ (**Current**)
*   **Phase 1.6:** Intelligence Layer (Research Agent) 🚧
    *   Add `ResearchAgent` node to the graph.
    *   Integrate web search tools (Tavily/Serper).
*   **Phase 2:** Multi-Agent Collaboration
    *   Separate `PlanningAgent` and `BookingAgent`.
    *   User preference memory (Vector Store).

## Intended Audience

*   Engineers exploring agentic architectures.
*   AI / ML engineers moving into systems roles.
*   Staff-level interview preparation.
