from typing import Literal, Optional
from pydantic import BaseModel, Field

# ── Request bodies ─────────────────────────────────────────────────────────────

class PlanRequest(BaseModel):
    thread_id: str
    message: str = Field(
        ...,
        description="Natural-language trip request, e.g. '3 days in Kyoto, Japan, budget traveller'",
    )
    start_date: str | None = Field(
        default=None,
        description="Optional travel start date in ISO-8601 format (YYYY-MM-DD).",
    )

class FeedbackRequest(BaseModel):
    thread_id: str
    feedback: str = Field(
        ...,
        description="User feedback. Use 'approve' to finalise the itinerary.",
    )

# ── SSE event payloads ─────────────────────────────────────────────────────────

class NodeStartEvent(BaseModel):
    event: Literal["node_start"] = "node_start"
    node: str

class NodeCompleteEvent(BaseModel):
    event: Literal["node_complete"] = "node_complete"
    node: str
    destination: Optional[str] = None
    verification_score: Optional[float] = None
    draft_snippet: Optional[str] = None  # first 200 chars of draft_itinerary

class LLMTokenEvent(BaseModel):
    event: Literal["llm_token"] = "llm_token"
    token: str

class VenueCoordinate(BaseModel):
    name: str
    lat: float
    lon: float
    day: int
    time: str

class WeatherDay(BaseModel):
    day: int
    date: str
    high_c: float | None = None
    low_c: float | None = None
    rain_prob: int | None = None
    description: str
    is_forecast: bool

class InterruptEvent(BaseModel):
    event: Literal["interrupt"] = "interrupt"
    draft_itinerary: str
    verification_score: float
    venue_coordinates: list[VenueCoordinate] = []
    weather_data: list[WeatherDay] = []
    travel_start_date: str | None = None
    message: str = "Review the itinerary above. Type 'approve' to export or provide feedback."

class DoneEvent(BaseModel):
    event: Literal["done"] = "done"
    thread_id: str

class ErrorEvent(BaseModel):
    event: Literal["error"] = "error"
    detail: str

# ── REST response bodies ───────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    thread_id: str

class StateResponse(BaseModel):
    thread_id: str
    destination: str
    verification_score: float
    draft_itinerary: str
    is_interrupted: bool
    interrupt_message: Optional[str] = None
