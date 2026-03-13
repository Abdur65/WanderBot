from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from src.state import AgentState
from src.nodes.analyze import analyze_request
from src.nodes.curate import curate_knowledge
from src.nodes.rag_retriever import rag_retriever
from src.nodes.live_verifier import live_verifier
from src.nodes.draft_plan import draft_plan

def human_review(state: AgentState) -> dict:
    # LangGraph interrupt — pauses the graph and waits for external input
    user_input = interrupt({
        "draft_itinerary": state["draft_itinerary"],
        "message": "Review the itinerary above. Type 'approve' to export or provide feedback."
    })
    return {"messages": [{"role": "user", "content": user_input}]}

def route_after_review(state: AgentState) -> str:
    last = state["messages"][-1].content.lower().strip()
    if last == "approve":
        return "export"
    elif any(w in last for w in ["food", "restaurant", "eat", "cuisine"]):
        return "rag"   # re-retrieve with new angle
    else:
        return "draft"  # small adjustment, re-draft only

def build_graph():
    builder = StateGraph(AgentState)
    
    builder.add_node("analyze", analyze_request)
    builder.add_node("curate", curate_knowledge)
    builder.add_node("rag_retriever", rag_retriever)
    builder.add_node("live_verifier", live_verifier)
    builder.add_node("draft_plan", draft_plan)
    builder.add_node("human_review", human_review)
    
    # Linear backbone
    builder.set_entry_point("analyze")
    builder.add_edge("analyze", "curate")
    builder.add_edge("curate", "rag_retriever")
    builder.add_edge("rag_retriever", "live_verifier")
    builder.add_edge("live_verifier", "draft_plan")
    builder.add_edge("draft_plan", "human_review")
    
    # Conditional edges after review
    builder.add_conditional_edges("human_review", route_after_review, {
        "export": END,
        "rag": "rag_retriever",
        "draft": "draft_plan",
    })
    
    memory = MemorySaver()
    return builder.compile(checkpointer=memory, interrupt_before=["human_review"])

graph = build_graph()