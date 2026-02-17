# apps/orchestrator/app/nodes.py

import os
from typing import Any, Dict
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from .state import GraphState

# ... (Keep existing URL constants) ...
FLIGHT_TOOL_URL = os.getenv("FLIGHT_TOOL_URL", "http://localhost:8001")
DB_TOOL_URL = os.getenv("DB_TOOL_URL", "http://localhost:8002")

# ... (Keep resolve_locations, save_trip_draft, search_and_persist_flights) ...

# --- New Node for Phase 1.6 ---
async def research_city(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Uses an LLM and Web Search to generate a short city guide.
    """
    print("---NODE: RESEARCHING CITY---")
    
    # 1. Check if we have the destination name (not just code)
    # In a real app, we might want the full city name, but let's use the user's input 'destination'
    city = state["request_body"].destination
    travel_date = state["request_body"].date
    
    # 2. Initialize Tool and LLM
    # Note: In production, you might initialize these once globally or pass via config to save overhead
    try:
        search_tool = TavilySearchResults(max_results=3)
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5)
        
        # 3. Define the Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful travel assistant. Your goal is to provide a 3-sentence summary of what is happening in a specific city on a specific date, including weather and one major event."),
            ("user", "Research {city} for a trip on {date}. Use the search tool to find real info.")
        ])
        
        # 4. Create the Chain: Prompt -> LLM (with tools bound)
        # For simplicity in this phase, we will just do a direct search then synthesis, 
        # rather than a full ReAct loop, to keep latency low.
        
        # A. Perform Search
        search_results = await search_tool.ainvoke(f"events in {city} on {travel_date} weather")
        
        # B. Synthesize with LLM
        synthesis_prompt = ChatPromptTemplate.from_template(
            "Based on these search results: {results}\n\n"
            "Write a helpful 3-sentence guide for a traveler going to {city} on {date}. "
            "Include expected weather and one key event or tip."
        )
        chain = synthesis_prompt | llm
        
        response = await chain.ainvoke({
            "results": search_results,
            "city": city,
            "date": travel_date
        })
        
        return {"city_guide": response.content}

    except Exception as e:
        # If research fails (e.g., API key missing), we don't want to fail the whole trip plan.
        # We just return a fallback message.
        print(f"Research failed: {e}")
        return {"city_guide": "Could not generate city guide at this time."}
