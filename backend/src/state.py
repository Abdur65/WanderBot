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

    duration_days: int | None = None          # number of days
    travel_party: Literal[
        "solo", "couple", "family", "group"
    ] = "solo"
    accommodation_area: str | None = None     # neighbourhood or landmark
    must_see: list[str] = []                  # anchored stops
    avoid: list[str] = []                     # explicit exclusions
    accessibility: list[str] = []            # physical constraints
    travel_start_date: str | None = None      # ISO-8601 e.g. "2025-06-15"

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    destination: str
    preferences: Preferences
    context: str
    draft_itinerary: str
    tavily_calls: int
    knowledge_ready: bool
    verification_score: float     # computed by validate_citations
    venue_coordinates: list       # [{name, lat, lon, day, time}] — set by logistics_enricher
    weather_data: list            # [{day, date, high_c, low_c, rain_prob, description, is_forecast}]