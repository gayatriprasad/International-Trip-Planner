# apps/orchestrator/app/graph.py

from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import resolve_locations, save_trip_draft, search_and_persist_flights

def should_continue(state: GraphState) -> str:
    """Determines whether to continue or end the workflow based on errors."""
    return "end" if state.get("error") else "continue"

# This defines the workflow
workflow = StateGraph(GraphState)

# Add the nodes
workflow.add_node("resolve_locations", resolve_locations)
workflow.add_node("save_trip_draft", save_trip_draft)
workflow.add_node("search_and_persist_flights", search_and_persist_flights)

# Set the entrypoint
workflow.set_entry_point("resolve_locations")

# Define conditional edges
workflow.add_conditional_edges(
    "resolve_locations",
    should_continue,
    {"continue": "save_trip_draft", "end": END}
)
workflow.add_conditional_edges(
    "save_trip_draft",
    should_continue,
    {"continue": "search_and_persist_flights", "end": END}
)

# The final node always ends the graph
workflow.add_edge("search_and_persist_flights", END)

# Compile the graph into a runnable app
app = workflow.compile()
