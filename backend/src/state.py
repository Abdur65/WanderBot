from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing import Literal

class Preferences(BaseModel):
    budget: Literal["budget", "mid", "luxury"] = "mid"
    pace: Literal["slow", "moderate", "fast"] = "moderate"
    interests: list[str] = []
    dietary: list[str] = []
    mobility: Literal["walking", "transit", "driving"] = "transit"

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    destination: str
    preferences: Preferences
    context: str                  
    draft_itinerary: str         
    tavily_calls: int             
    knowledge_ready: bool       