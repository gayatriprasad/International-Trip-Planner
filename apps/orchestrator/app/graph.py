# apps/orchestrator/app/graph.py

from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import resolve_locations, save_trip_draft, search_and_persist_flights, research_city

def should_continue(state: GraphState) -> str:
    return "end" if state.get("error") else "continue"

workflow = StateGraph(GraphState)

# Add Nodes
workflow.add_node("resolve_locations", resolve_locations)
workflow.add_node("save_trip_draft", save_trip_draft)
workflow.add_node("search_and_persist_flights", search_and_persist_flights)
workflow.add_node("research_city", research_city) # <--- New Node

# Set Entry Point
workflow.set_entry_point("resolve_locations")

# Edges
workflow.add_conditional_edges(
    "resolve_locations",
    should_continue,
    {"continue": "save_trip_draft", "end": END}
)

# --- Parallel Execution ---
# After saving the draft, we branch to BOTH search_flights AND research_city
workflow.add_conditional_edges(
    "save_trip_draft",
    should_continue,
    {
        "continue": ["search_and_persist_flights", "research_city"], 
        "end": END
    }
)

# Both parallel nodes go to END
workflow.add_edge("search_and_persist_flights", END)
workflow.add_edge("research_city", END)

app = workflow.compile()
