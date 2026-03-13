from src.state import AgentState
from src.nodes.curate import get_vector_store
from src.config import RAG_TOP_K

def rag_retriever(state: AgentState) -> dict:
    destination = state["destination"]
    preferences = state["preferences"]
    
    query_parts = [f"things to do in {destination}"]
    if preferences.interests:
        query_parts.append(" ".join(preferences.interests))
    if preferences.budget == "budget":
        query_parts.append("free cheap affordable")
    elif preferences.budget == "luxury":
        query_parts.append("luxury premium exclusive")
    
    query = " ".join(query_parts)
    print(f"[RAG] Querying Qdrant: '{query}'")
    
    vector_store = get_vector_store(destination)
    
    try:
        docs = vector_store.similarity_search(query, k=RAG_TOP_K)
        context = "\n\n---\n\n".join(
            f"[Source: {doc.metadata.get('source', 'unknown')}]\n{doc.page_content}"
            for doc in docs
        )
        print(f"[RAG] Retrieved {len(docs)} relevant chunks.")
    except Exception as e:
        print(f"[RAG] Retrieval failed: {e}. Continuing with empty context.")
        context = ""
    
    return {"context": context}