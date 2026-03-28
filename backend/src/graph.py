import aiosqlite
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import interrupt

from src.state import AgentState
from src.nodes.analyze import analyze_request
from src.nodes.curate import curate_knowledge
from src.nodes.rag_retriever import rag_retriever
from src.nodes.live_verifier import live_verifier
from src.nodes.weather_enricher import weather_enricher
from src.nodes.draft_plan import draft_plan
from src.nodes.logistics_enricher import logistics_enricher
from src.nodes.validate_citations import validate_citations

def human_review(state: AgentState) -> dict:
    user_input = interrupt({
        "draft_itinerary": state["draft_itinerary"],
        "verification_score": state.get("verification_score", 0.0),
        "message": "Review the itinerary above. Type 'approve' to export or provide feedback.",
    })
    return {"messages": [{"role": "user", "content": user_input}]}

def route_after_review(state: AgentState) -> str:
    last = state["messages"][-1].content.lower().strip()
    if last == "approve":
        return "export"
    elif any(w in last for w in ["food", "restaurant", "eat", "cuisine"]):
        return "rag"
    else:
        return "draft"

async def build_graph_async():
    conn = await aiosqlite.connect("wanderbot_checkpoints.db")
    checkpointer = AsyncSqliteSaver(conn)

    builder = StateGraph(AgentState)

    builder.add_node("analyze", analyze_request)
    builder.add_node("curate", curate_knowledge)
    builder.add_node("rag_retriever", rag_retriever)
    builder.add_node("live_verifier", live_verifier)
    builder.add_node("weather_enricher", weather_enricher)
    builder.add_node("draft_plan", draft_plan)
    builder.add_node("logistics_enricher", logistics_enricher)
    builder.add_node("validate_citations", validate_citations)
    builder.add_node("human_review", human_review)

    builder.set_entry_point("analyze")
    builder.add_edge("analyze", "curate")
    builder.add_edge("curate", "rag_retriever")
    builder.add_edge("rag_retriever", "live_verifier")
    builder.add_edge("live_verifier", "weather_enricher")
    builder.add_edge("weather_enricher", "draft_plan")
    builder.add_edge("draft_plan", "logistics_enricher")
    builder.add_edge("logistics_enricher", "validate_citations")
    builder.add_edge("validate_citations", "human_review")

    builder.add_conditional_edges("human_review", route_after_review, {
        "export": END,
        "rag": "rag_retriever",
        "draft": "draft_plan",
    })

    return builder.compile(checkpointer=checkpointer)