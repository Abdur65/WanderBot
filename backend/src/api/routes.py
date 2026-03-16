import json
import re
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from langgraph.types import Command

from src.graph import graph
from src.api.models import (
    PlanRequest,
    FeedbackRequest,
    SessionResponse,
    StateResponse,
    NodeStartEvent,
    NodeCompleteEvent,
    LLMTokenEvent,
    InterruptEvent,
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
                        iv = interrupt_val[0]
                        iv_data = iv.value if hasattr(iv, "value") else iv
                        yield _sse(InterruptEvent(
                            draft_itinerary=iv_data.get("draft_itinerary", ""),
                            verification_score=iv_data.get("verification_score", 0.0),
                        ).model_dump())
                        return  # client must POST /feedback to continue

    except Exception as e:
        yield _sse(ErrorEvent(detail=str(e)).model_dump())
        return

    yield _sse(DoneEvent(thread_id=thread_id).model_dump())


# ── POST /session ──────────────────────────────────────────────────────────────

@router.post("/session", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    """Creates a new thread_id. The client stores this for all subsequent requests."""
    return SessionResponse(thread_id=str(uuid.uuid4()))


# ── POST /plan (SSE) ───────────────────────────────────────────────────────────

@router.post("/plan")
async def plan(request: PlanRequest) -> StreamingResponse:
    """
    Starts a new planning run. Streams SSE events through all nodes until the
    human_review interrupt fires (the agent has finished the first draft).
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    initial_state = {
        "messages": [{"role": "user", "content": request.message}],
        "destination": "",
        "context": "",
        "draft_itinerary": "",
        "tavily_calls": 0,
        "knowledge_ready": False,
        "verification_score": 0.0,
    }
    return StreamingResponse(
        _stream_graph_events(initial_state, config, request.thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── POST /feedback (SSE) ───────────────────────────────────────────────────────

@router.post("/feedback")
async def feedback(request: FeedbackRequest) -> StreamingResponse:
    """
    Resumes the graph after a human_review interrupt.
    Send 'approve' to finalise, or any natural-language feedback to refine.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    state = graph.get_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")
    if not state.interrupts:
        raise HTTPException(
            status_code=409,
            detail="No pending interrupt. Start a run with POST /plan first.",
        )

    return StreamingResponse(
        _stream_graph_events(Command(resume=request.feedback), config, request.thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /state/{thread_id} ─────────────────────────────────────────────────────

@router.get("/state/{thread_id}", response_model=StateResponse)
async def get_state(thread_id: str) -> StateResponse:
    """Returns the current graph state — useful for rehydrating after a page reload."""
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    values = state.values
    is_interrupted = bool(state.interrupts)
    interrupt_message = (
        state.interrupts[0].value.get("message") if is_interrupted else None
    )

    return StateResponse(
        thread_id=thread_id,
        destination=values.get("destination", ""),
        verification_score=values.get("verification_score", 0.0),
        draft_itinerary=values.get("draft_itinerary", ""),
        is_interrupted=is_interrupted,
        interrupt_message=interrupt_message,
    )


# ── GET /export/{thread_id} ────────────────────────────────────────────────────

@router.get("/export/{thread_id}")
async def export_itinerary(thread_id: str) -> Response:
    """Downloads the approved itinerary as a Markdown file."""
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    draft = state.values.get("draft_itinerary", "")
    destination = state.values.get("destination", "destination")

    if not draft:
        raise HTTPException(status_code=404, detail="No itinerary available yet.")

    # Strip internal citation tags before export — scoring is already done
    clean = re.sub(r'\[src:\d+\]', '', draft)
    clean = re.sub(r'\[Unverified[^\]]*\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'^>.*Verification:.*\n\n', '', clean)  # strip badge blockquote

    safe_name = destination.lower().replace(" ", "_").replace(",", "")
    filename = f"itinerary_{safe_name}.md"
    content = f"# Travel Itinerary — {destination}\n\n{clean}"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
