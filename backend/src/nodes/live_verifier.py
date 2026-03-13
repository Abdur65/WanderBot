from langchain_community.tools.tavily_search import TavilySearchResults
from src.config import TAVILY_API_KEY, MAX_TAVILY_CALLS
from src.state import AgentState

search = TavilySearchResults(api_key=TAVILY_API_KEY, max_results=3)

def live_verifier(state: AgentState) -> dict:
    destination = state["destination"]
    calls = state.get("tavily_calls", 0)
    
    if calls >= MAX_TAVILY_CALLS:
        print("[Verifier] Max Tavily calls reached. Skipping live verification.")
        return {}
    
    print(f"[Verifier] Fetching live data for {destination}...")
    
    queries = [
        f"{destination} current weather travel conditions",
        f"{destination} top attractions opening hours 2024 2025",
    ]
    
    live_snippets = []
    for query in queries:
        if calls >= MAX_TAVILY_CALLS:
            break
        try:
            results = search.invoke(query)
            calls += 1
            for r in results:
                live_snippets.append(f"[Live src:{calls}] {r.get('content', '')}")
        except Exception as e:
            print(f"[Verifier] Search failed for '{query}': {e}")
    
    live_context = "\n\n".join(live_snippets)
    combined_context = state.get("context", "") + "\n\n" + live_context
    
    print(f"[Verifier] Live context added ({len(live_snippets)} results).")
    
    return {"context": combined_context, "tavily_calls": calls}