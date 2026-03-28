import json
import re
import uuid
from datetime import date, timedelta
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from langgraph.types import Command

from src.state import Preferences
from src.api.models import (
    PlanRequest,
    FeedbackRequest,
    SessionResponse,
    StateResponse,
    NodeStartEvent,
    NodeCompleteEvent,
    LLMTokenEvent,
    InterruptEvent,
    VenueCoordinate,
    WeatherDay,
    DoneEvent,
    ErrorEvent,
)

router = APIRouter()

# Nodes whose output is worth including in node_complete events
_INFORMATIVE_NODES = {"analyze", "draft_plan", "validate_citations"}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream_graph_events(
    inputs,
    config: dict,
    thread_id: str,
    graph,
) -> AsyncIterator[str]:
    try:
        async for event in graph.astream_events(inputs, config, version="v2"):
            kind = event["event"]
            name = event.get("name", "")
            data = event.get("data", {})

            # ── node started ───────────────────────────────────────────────
            if kind == "on_chain_start" and name in graph.nodes:
                yield _sse(NodeStartEvent(node=name).model_dump())

            # ── node finished ──────────────────────────────────────────────
            elif kind == "on_chain_end" and name in graph.nodes:
                output = data.get("output") or {}
                if isinstance(output, dict) and name in _INFORMATIVE_NODES:
                    draft = output.get("draft_itinerary", "")
                    yield _sse(NodeCompleteEvent(
                        node=name,
                        destination=output.get("destination"),
                        verification_score=output.get("verification_score"),
                        draft_snippet=draft[:200] if draft else None,
                    ).model_dump(exclude_none=True))
                else:
                    yield _sse(NodeCompleteEvent(node=name).model_dump(exclude_none=True))

            # ── LLM token streaming ────────────────────────────────────────
            elif kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk:
                    token = getattr(chunk, "content", "")
                    if token:
                        yield _sse(LLMTokenEvent(token=token).model_dump())

            # ── graph interrupt (human_review) ─────────────────────────────
            elif kind == "on_chain_stream":
                chunk = data.get("chunk", {})
                if isinstance(chunk, dict):
                    interrupt_val = chunk.get("__interrupt__")
                    if interrupt_val:
                        iv      = interrupt_val[0]
                        iv_data = iv.value if hasattr(iv, "value") else iv

                        graph_state = await graph.aget_state(config)
                        sv = graph_state.values

                        raw_coords = sv.get("venue_coordinates", [])
                        coords = [
                            VenueCoordinate(**c) for c in raw_coords
                            if all(k in c for k in ("name", "lat", "lon", "day", "time"))
                        ]

                        raw_weather = sv.get("weather_data", [])
                        weather = [WeatherDay(**w) for w in raw_weather]

                        prefs = sv.get("preferences")
                        start_date = getattr(prefs, "travel_start_date", None) if prefs else None

                        yield _sse(InterruptEvent(
                            draft_itinerary=iv_data.get("draft_itinerary", ""),
                            verification_score=iv_data.get("verification_score", 0.0),
                            venue_coordinates=coords,
                            weather_data=weather,
                            travel_start_date=start_date,
                        ).model_dump())
                        return

    except Exception as e:
        yield _sse(ErrorEvent(detail=str(e)).model_dump())
        return

    yield _sse(DoneEvent(thread_id=thread_id).model_dump())


# ── POST /session ──────────────────────────────────────────────────────────────

@router.post("/session", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    return SessionResponse(thread_id=str(uuid.uuid4()))


# ── POST /plan (SSE) ───────────────────────────────────────────────────────────

@router.post("/plan")
async def plan(body: PlanRequest, request: Request) -> StreamingResponse:
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": body.thread_id}}

    initial_prefs = Preferences(
        travel_start_date=body.start_date or None
    )

    initial_state = {
        "messages":          [{"role": "user", "content": body.message}],
        "destination":       "",
        "preferences":       initial_prefs,
        "context":           "",
        "draft_itinerary":   "",
        "tavily_calls":      0,
        "knowledge_ready":   False,
        "verification_score": 0.0,
        "venue_coordinates": [],
        "weather_data":      [],
    }
    return StreamingResponse(
        _stream_graph_events(initial_state, config, body.thread_id, graph),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── POST /feedback (SSE) ───────────────────────────────────────────────────────

@router.post("/feedback")
async def feedback(body: FeedbackRequest, request: Request) -> StreamingResponse:
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": body.thread_id}}
    state  = await graph.aget_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")
    if not state.interrupts:
        raise HTTPException(
            status_code=409,
            detail="No pending interrupt. Start a run with POST /plan first.",
        )

    return StreamingResponse(
        _stream_graph_events(Command(resume=body.feedback), config, body.thread_id, graph),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /state/{thread_id} ─────────────────────────────────────────────────────

@router.get("/state/{thread_id}", response_model=StateResponse)
async def get_state(thread_id: str, request: Request) -> StateResponse:
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state  = await graph.aget_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    values         = state.values
    is_interrupted = bool(state.interrupts)
    interrupt_msg  = state.interrupts[0].value.get("message") if is_interrupted else None

    return StateResponse(
        thread_id=thread_id,
        destination=values.get("destination", ""),
        verification_score=values.get("verification_score", 0.0),
        draft_itinerary=values.get("draft_itinerary", ""),
        is_interrupted=is_interrupted,
        interrupt_message=interrupt_msg,
    )


# ── GET /export/{thread_id} ────────────────────────────────────────────────────

@router.get("/export/{thread_id}")
async def export_itinerary(thread_id: str, request: Request) -> Response:
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state  = await graph.aget_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    draft       = state.values.get("draft_itinerary", "")
    destination = state.values.get("destination", "destination")

    if not draft:
        raise HTTPException(status_code=404, detail="No itinerary available yet.")

    clean = re.sub(r'\[src:[^\]]+\]', '', draft, flags=re.IGNORECASE)
    clean = re.sub(r'\[Unverified[^\]]*\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^>.*Verification:.*\n\n', '', clean)

    safe     = destination.lower().replace(" ", "_").replace(",", "")
    filename = f"itinerary_{safe}.md"
    content  = f"# Travel Itinerary — {destination}\n\n{clean}"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── GET /export/calendar/{thread_id} ──────────────────────────────────────────

@router.get("/export/calendar/{thread_id}")
async def export_calendar(thread_id: str, request: Request) -> Response:
    """Download the approved itinerary as an iCal (.ics) file."""
    graph  = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state  = await graph.aget_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    sv          = state.values
    draft       = sv.get("draft_itinerary", "")
    destination = sv.get("destination", "Trip")
    prefs       = sv.get("preferences")
    start_str   = getattr(prefs, "travel_start_date", None) if prefs else None

    if not draft:
        raise HTTPException(status_code=404, detail="No itinerary available yet.")

    # Parse time-slot headings: ### HH:MM–HH:MM  Name
    SLOT_RE  = re.compile(
        r'^###\s+(\d{1,2}:\d{2})[–\-](\d{1,2}:\d{2})\s{1,}(.+)$', re.MULTILINE
    )
    DAY_RE   = re.compile(r'^##\s+Day\s+(\d+)', re.MULTILINE | re.IGNORECASE)

    # Build an ordered list of (day_num, start_time, end_time, name)
    # by walking through the text linearly
    events: list[tuple[int, str, str, str]] = []
    current_day = 1
    pos = 0
    text = draft

    # Collect all day headings and venue headings with their positions
    markers = []
    for m in DAY_RE.finditer(text):
        markers.append(("day", int(m.group(1)), m.start()))
    for m in SLOT_RE.finditer(text):
        markers.append(("venue", m.group(1), m.group(2), m.group(3).strip(), m.start()))
    markers.sort(key=lambda x: x[-1])  # sort by position

    for marker in markers:
        if marker[0] == "day":
            current_day = marker[1]
        else:
            _, t_start, t_end, name, _ = marker
            events.append((current_day, t_start, t_end, name))

    # Determine base date
    if start_str:
        try:
            base = date.fromisoformat(start_str)
        except ValueError:
            base = None
    else:
        base = None

    def _dt(day_num: int, hhmm: str) -> str:
        """Format as YYYYMMDDTHHMMSS (floating local time)."""
        if base:
            d = base + timedelta(days=day_num - 1)
            return d.strftime("%Y%m%d") + "T" + hhmm.replace(":", "") + "00"
        else:
            # No date: use a placeholder week starting 2025-01-06 (a Monday)
            d = date(2025, 1, 6) + timedelta(days=day_num - 1)
            return d.strftime("%Y%m%d") + "T" + hhmm.replace(":", "") + "00"

    now_str = date.today().strftime("%Y%m%d") + "T000000Z"
    safe    = destination.lower().replace(" ", "_").replace(",", "")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WanderBot//Travel Itinerary//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{destination} — WanderBot Itinerary",
        "X-WR-CALDESC:Generated by WanderBot AI travel planner",
    ]

    for idx, (day_num, t_start, t_end, name) in enumerate(events):
        uid = f"wanderbot-{safe}-d{day_num}-{idx}@wanderbot"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_str}",
            f"DTSTART:{_dt(day_num, t_start)}",
            f"DTEND:{_dt(day_num, t_end)}",
            f"SUMMARY:{name}",
            f"LOCATION:{name}\\, {destination}",
            f"DESCRIPTION:Day {day_num} of your {destination} itinerary — WanderBot",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    ical_content = "\r\n".join(lines) + "\r\n"

    filename = f"itinerary_{safe}.ics"
    return Response(
        content=ical_content.encode("utf-8"),
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
