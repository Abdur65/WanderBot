from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.config import GROQ_API_KEY, GROQ_MODEL
from src.state import AgentState, Preferences

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL)
structured_llm = llm.with_structured_output(Preferences)

SYSTEM = """
You are a travel assistant intake agent.
Extract the travel destination and user preferences from the conversation.
If a value is not mentioned, use the default.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "{input}")
])

chain = prompt | structured_llm

def analyze_request(state: AgentState) -> dict:
    last_message = state["messages"][-1].content
    
    # Extract destination — simple parse for Phase 1
    destination = ""
    for phrase in ["to ", "in ", "visiting ", "trip to ", "travel to "]:
        if phrase in last_message.lower():
            after = last_message.lower().split(phrase)[-1]
            destination = after.split()[0].strip(".,!?").title()
            break
    
    if not destination:
        destination = last_message.strip().title()
    
    preferences = chain.invoke({"input": last_message})
    
    print(f"[Analyze] Destination: {destination}")
    print(f"[Analyze] Preferences: {preferences}")
    
    return {
        "destination": destination,
        "preferences": preferences,
        "knowledge_ready": False,
        "tavily_calls": 0,
    }