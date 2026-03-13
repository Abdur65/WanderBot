from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.config import GROQ_API_KEY, GROQ_MODEL
from src.state import AgentState

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)

SYSTEM = """
You are an expert travel planner. Draft a detailed day-by-day itinerary in Markdown.

Rules:
- Only use facts present in the provided context. 
- If a fact has no source, write [Unverified] next to it.
- Structure each day with time slots: ## Day N — City, then ### HH:MM–HH:MM  Place Name
- Keep the pace aligned with the user's preference: {pace}
- Budget level: {budget}
- Interests: {interests}
- Dietary needs: {dietary}

Context from research:
{context}

If context is sparse, build a reasonable plan but mark every unconfirmed detail with [Unverified].
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "Plan a trip to {destination} for me.")
])

chain = prompt | llm

def draft_plan(state: AgentState) -> dict:
    destination = state["destination"]
    preferences = state["preferences"]
    context = state.get("context", "No context available.")
    
    print(f"[Draft] Generating itinerary for {destination}...")
    
    response = chain.invoke({
        "destination": destination,
        "context": context,
        "pace": preferences.pace,
        "budget": preferences.budget,
        "interests": ", ".join(preferences.interests) if preferences.interests else "general sightseeing",
        "dietary": ", ".join(preferences.dietary) if preferences.dietary else "no restrictions",
    })
    
    draft = response.content
    print(f"[Draft] Itinerary drafted ({len(draft)} chars).")
    
    return {"draft_itinerary": draft}