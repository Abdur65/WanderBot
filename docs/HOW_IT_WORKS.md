# WanderBot — How It Works

A technical walkthrough of the entire system: from a user typing a destination to
a verified, downloadable travel itinerary.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack at a Glance](#2-tech-stack-at-a-glance)
3. [System Architecture](#3-system-architecture)
4. [The LLM — What It Is and How It Is Used](#4-the-llm--what-it-is-and-how-it-is-used)
5. [The Agent — LangGraph StateGraph](#5-the-agent--langgraph-stategraph)
6. [Node-by-Node Walkthrough](#6-node-by-node-walkthrough)
   - 6.1 [analyze](#61-analyze)
   - 6.2 [curate](#62-curate)
   - 6.3 [rag_retriever](#63-rag_retriever)
   - 6.4 [live_verifier](#64-live_verifier)
   - 6.5 [draft_plan](#65-draft_plan)
   - 6.6 [validate_citations](#66-validate_citations)
   - 6.7 [human_review](#67-human_review)
7. [RAG — Retrieval-Augmented Generation](#7-rag--retrieval-augmented-generation)
8. [The API Layer — FastAPI and SSE Streaming](#8-the-api-layer--fastapi-and-sse-streaming)
9. [Session Persistence — Checkpointing](#9-session-persistence--checkpointing)
10. [The Frontend — React Application](#10-the-frontend--react-application)
11. [End-to-End Data Flow](#11-end-to-end-data-flow)
12. [Anti-Hallucination Strategy](#12-anti-hallucination-strategy)
13. [Iterative Refinement Loop](#13-iterative-refinement-loop)
14. [Deployment](#14-deployment)
15. [Environment Variables Reference](#15-environment-variables-reference)

---

## 1. Project Overview

WanderBot is an AI-powered travel itinerary planner. The user describes their
trip in plain English — destination, duration, budget, interests — and WanderBot
autonomously researches that destination, retrieves travel knowledge, verifies
live conditions, and produces a day-by-day itinerary with time slots, venue
details, and source citations.

The key problem WanderBot solves is that generic AI assistants hallucinate travel
facts: inventing opening hours, citing closed venues, and presenting stale data as
current truth. WanderBot structurally prevents this by requiring every factual
claim to be traced to a real source retrieved at run time. Claims that cannot be
sourced are explicitly flagged as *not confirmed* rather than silently invented.

---

## 2. Tech Stack at a Glance

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | React 19, Vite, TypeScript, TailwindCSS, DaisyUI | Browser UI |
| **Backend API** | FastAPI, Uvicorn | HTTP server, SSE streaming |
| **Agent Framework** | LangGraph `StateGraph` | Orchestrates the AI pipeline |
| **LLM** | Groq `llama-3.3-70b-versatile` | Language understanding and generation |
| **Web Search** | Tavily Search API | Live fact retrieval |
| **Web Scraping** | LangChain `WebBaseLoader` | Travel blog ingestion |
| **Vector Store** | Qdrant Cloud | Stores and searches document embeddings |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | Converts text to vectors |
| **Checkpointing** | LangGraph `MemorySaver` | Persists session state across interrupts |
| **Config** | `python-decouple` | Loads secrets from `.env` safely |
| **Package managers** | `uv` (Python), `bun` (frontend) | Dependency management |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend (Netlify)               │
│  TripInput → PipelineProgress → ItineraryView           │
│  FeedbackPanel → Download (MD / PDF)                    │
└─────────────────┬───────────────────────────────────────┘
                  │  POST /api/v1/plan   (SSE stream)
                  │  POST /api/v1/feedback (SSE stream)
                  │  POST /api/v1/session
                  │  GET  /api/v1/export/{thread_id}
┌─────────────────▼───────────────────────────────────────┐
│              FastAPI Backend (Render)                    │
│  routes.py: _stream_graph_events()                      │
│  astream_events → node_start / node_complete / llm_token│
└─────────────────┬───────────────────────────────────────┘
                  │  graph.astream_events(initial_state, config)
                  │  graph.astream_events(Command(resume=feedback), config)
┌─────────────────▼───────────────────────────────────────┐
│          LangGraph StateGraph (AgentState)               │
│                                                         │
│  analyze → curate → rag_retriever → live_verifier       │
│         → draft_plan → validate_citations               │
│         → human_review ──(interrupt)──►                 │
│                    ↑                                    │
│         ┌──────────┴──────────┐                         │
│         │ route_after_review  │                         │
│      "rag" ↑       "draft" ↑  └─"export"→ END           │
└────┬────────────┬─────────────────────────┬─────────────┘
     │            │                         │
┌────▼───┐  ┌─────▼──────┐         ┌────────▼──────────┐
│Qdrant  │  │  Tavily    │         │  HuggingFace       │
│(vectors│  │  Search    │         │  Embeddings API    │
│+ docs) │  │  API       │         │  (all-MiniLM-L6-v2)│
└────────┘  └────────────┘         └───────────────────-┘
```

The frontend and backend communicate exclusively over HTTP. The agent pipeline
runs entirely on the backend. The frontend never holds LLM credentials or calls
external APIs directly.

---

## 4. The LLM — What It Is and How It Is Used

### What is an LLM?

A Large Language Model (LLM) is a neural network trained on vast amounts of text
to predict the next token in a sequence. Because it has been trained on human
writing, it can understand natural language instructions and generate fluent,
coherent text in response.

WanderBot uses **Groq's hosted `llama-3.3-70b-versatile`** — a 70-billion parameter
open-weights model served by Groq's LPU (Language Processing Unit) inference
hardware, which delivers significantly lower latency than GPU-based providers.

### How the LLM is called

LangChain's `ChatGroq` class wraps the Groq API. Each call takes a list of
messages (system prompt + user message) and returns a response:

```python
from langchain_groq import ChatGroq

llm = ChatGroq(api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")
```

### Structured output

Two nodes (`analyze` and others) need the LLM to return data in a specific
schema rather than free text. LangChain's `.with_structured_output()` method
wraps the LLM with a Pydantic model. Groq responds with valid JSON that
LangChain automatically parses and validates:

```python
class Preferences(BaseModel):
    budget: Literal["budget", "mid", "luxury"] = "mid"
    pace: Literal["slow", "moderate", "fast"] = "moderate"
    interests: list[str] = []
    ...

structured_llm = llm.with_structured_output(Preferences)
preferences = structured_llm.invoke({"input": user_message})
# preferences is a fully typed Preferences instance
```

If the LLM returns a value outside the Literal constraints (e.g. a budget value
not in `["budget", "mid", "luxury"]`), Pydantic raises a `ValidationError` which
propagates as an error event.

### Token streaming

During the `draft_plan` node, the LLM generates the itinerary text token by
token. LangChain + LangGraph expose each token as an `on_chat_model_stream`
event, which the backend forwards to the frontend in real time so the user can
watch the itinerary appear word-by-word.

---

## 5. The Agent — LangGraph StateGraph

### What is an agent?

An agent is a program that decides what to do next based on the current state of
the world, takes an action, observes the result, and repeats until a goal is
reached. In WanderBot, the "world" is the planning session state and the
"actions" are the pipeline nodes (research, retrieve, draft, etc.).

### LangGraph

LangGraph is a library built on top of LangChain that lets you define an agent as
a directed graph of nodes (functions) connected by edges (transitions). It handles
state management, checkpointing, and streaming automatically.

```python
from langgraph.graph import StateGraph, END

builder = StateGraph(AgentState)
builder.add_node("analyze", analyze_request)
builder.add_node("curate", curate_knowledge)
# ... more nodes ...
builder.set_entry_point("analyze")
builder.add_edge("analyze", "curate")
builder.add_edge("curate", "rag_retriever")
# ... more edges ...
graph = builder.compile(checkpointer=MemorySaver())
```

### AgentState

All nodes share a single state object — a `TypedDict` that flows through the
entire graph:

```python
class AgentState(TypedDict):
    messages:           Annotated[list, add_messages]  # conversation history
    destination:        str                            # e.g. "Kyoto, Japan"
    preferences:        Preferences                    # budget, pace, interests…
    context:            str                            # all retrieved text
    draft_itinerary:    str                            # LLM-generated markdown
    tavily_calls:       int                            # rate-limit counter
    knowledge_ready:    bool                           # curate already ran?
    verification_score: float                          # 0.0–1.0 citation health
```

The `messages` field uses `add_messages` as its reducer, which means new
messages are appended (with deduplication by ID) rather than replacing the
existing list. Every other field is replaced by whatever the current node
returns.

### Graph execution model

When `graph.astream_events(initial_state, config)` is called, LangGraph:

1. Initialises the state from `initial_state`
2. Looks up the thread's existing checkpoint in `MemorySaver` (if any) and
   merges it with the new input
3. Starts executing from the entry point (`analyze`)
4. After each node completes, writes its return dict into the state
5. Follows the outgoing edge to determine the next node
6. Continues until it reaches a node that calls `interrupt()` or reaches `END`

---

## 6. Node-by-Node Walkthrough

### 6.1 analyze

**File:** `backend/src/nodes/analyze.py`

**What it does:** Extracts the destination and all travel preferences from the
user's message. This is a pure LLM step — no external APIs are called.

**How it works:**

Two separate LLM chains run in sequence:

1. **Destination extraction** — a lightweight structured-output call using a
   `TripInfo` Pydantic model. The system prompt instructs the model to return
   only the place name exactly as the user stated it (e.g. "Tokyo, Japan").
   This runs on the *latest* message only, so a feedback message like "add more
   food" doesn't corrupt the destination.

2. **Preference extraction** — a full structured-output call using the
   `Preferences` Pydantic model. This runs on the *entire conversation history*
   (joined as a single string) so that preferences mentioned across multiple
   refinement rounds are all captured. The system prompt includes a detailed
   mapping for each field:

   ```
   "budget", "cheap", "affordable" → "budget"
   "mid-range", "moderate"         → "mid"
   "luxury", "premium", "splurge"  → "luxury"
   ```

**Returns:** `{"destination": str, "preferences": Preferences}`

---

### 6.2 curate

**File:** `backend/src/nodes/curate.py`

**What it does:** Searches for travel blog articles about the destination,
scrapes their content, splits it into chunks, embeds each chunk, and stores them
in Qdrant for later retrieval.

**How it works step by step:**

1. **Guard check** — if `state["knowledge_ready"]` is `True` (curate already ran
   in a previous refinement round), the node immediately returns `{}` and is
   skipped. This avoids re-scraping and re-embedding on every feedback iteration.

2. **Tavily search** — a query like
   `"Best travel guide blog Tokyo, Japan things to do tips"` is sent to the
   Tavily Search API, which returns up to 5 URLs of relevant travel articles.

3. **Web scraping** — LangChain's `WebBaseLoader` fetches the HTML of up to 4
   of those URLs. `WebBaseLoader` uses `BeautifulSoup` to strip navigation,
   footers, and boilerplate, returning only the meaningful article body text. Any
   URL that fails to load is silently skipped.

4. **Chunking** — `RecursiveCharacterTextSplitter` splits each article into
   overlapping chunks (`CHUNK_SIZE=1000` chars, `CHUNK_OVERLAP=200` chars). The
   overlap ensures that a sentence that spans a chunk boundary is included in
   both adjacent chunks so context is never lost during retrieval.

5. **Embedding** — `HuggingFaceEndpointEmbeddings` sends each chunk to the
   HuggingFace Inference API running `sentence-transformers/all-MiniLM-L6-v2`.
   This model produces a 384-dimensional vector for each chunk that encodes its
   semantic meaning. Semantically similar texts produce numerically similar
   vectors.

6. **Qdrant storage** — a Qdrant collection named
   `travel_<destination_lowercase>` is created if it does not already exist
   (with `Distance.COSINE` similarity). The chunks and their vectors are written
   to the collection via `QdrantVectorStore.add_documents()`.

**Returns:** `{"knowledge_ready": True, "tavily_calls": <n>}`

---

### 6.3 rag_retriever

**File:** `backend/src/nodes/rag_retriever.py`

**What it does:** Queries Qdrant for the most semantically relevant chunks from
the scraped travel articles given the user's specific interests.

This is the **retrieval** step in Retrieval-Augmented Generation (RAG). See
[Section 7](#7-rag--retrieval-augmented-generation) for a deep dive.

**How it works:**

1. **Query construction** — a search query is built from the destination and
   preferences. For a budget traveller interested in street food:

   ```
   "things to do in Tokyo, Japan street food free cheap affordable"
   ```

2. **Vector similarity search** — the query string is embedded into a 384-dim
   vector using the same `all-MiniLM-L6-v2` model. Qdrant then finds the
   `RAG_TOP_K=5` stored chunks whose vectors are closest (cosine similarity) to
   the query vector. These are the chunks most likely to contain relevant
   information.

3. **Context assembly** — the retrieved chunk texts are concatenated with their
   source URLs into a single `context` string that later nodes will use.

**Returns:** `{"context": str}`

---

### 6.4 live_verifier

**File:** `backend/src/nodes/live_verifier.py`

**What it does:** Runs live Tavily web searches for current conditions — weather,
recent closures, updated opening hours — and appends the results to the context.

**Why this is needed:** The scraped travel blog content may be weeks or months
old. A temple could have changed its hours, a weather event could have affected
access, or entry prices might have changed. The live verifier fetches real-time
snippets to supplement the static RAG context.

**How it works:**

Two search queries run sequentially:

```
"{destination} current weather travel conditions"
"{destination} top attractions opening hours 2025 2026"
```

Each result is prefixed with `[Live src:N]` to distinguish it from the
RAG-retrieved content. The guard `if calls >= MAX_TAVILY_CALLS` prevents
runaway API spend. Each query increments the `tavily_calls` counter.

**Returns:** `{"context": combined_context, "tavily_calls": int}`

---

### 6.5 draft_plan

**File:** `backend/src/nodes/draft_plan.py`

**What it does:** Uses the LLM to write the full day-by-day itinerary in
Markdown format, grounded exclusively in the retrieved context.

**How it works:**

A `ChatPromptTemplate` is constructed with a detailed system prompt that:

- Injects all retrieved and live context (`{context}`)
- Injects all user preferences (`{destination}`, `{budget}`, `{pace}`,
  `{interests}`, `{dietary}`, `{mobility}`, `{duration_days}`, etc.)
- **Enforces strict anti-hallucination rules** (see Section 12)
- Specifies the exact Markdown structure to use

The prompt includes this critical instruction:

> Every factual claim MUST be annotated with a source citation in the format
> `[src:N]` where N is the index of the tool result that supports it. If a
> claim cannot be traced to any tool result, write `[Unverified]` immediately
> after the claim.

The LLM is called without `with_structured_output` here because the response is
free-form Markdown text. The call returns a full itinerary, which is stored in
`state["draft_itinerary"]`.

**Token streaming:** this is the only node that generates LLM tokens the
frontend renders live. Every token emitted by the LLM during this call propagates
as a `llm_token` SSE event to the frontend.

**Returns:** `{"draft_itinerary": str}`

---

### 6.6 validate_citations

**File:** `backend/src/nodes/validate_citations.py`

**What it does:** Parses the drafted itinerary with regular expressions to count
how many claims are sourced vs. unverified, computes a verification score, and
prepends a summary badge to the itinerary text.

**How it works:**

Two regex patterns scan the draft:

```python
SRC_PATTERN       = re.compile(r"\[src:(\d+)\]")          # sourced claims
UNVERIFIED_PATTERN = re.compile(r"\[unverified[^\]]*\]", re.IGNORECASE)
```

```
score = sourced_count / (sourced_count + unverified_count)
```

A colour-coded badge is prepended to the itinerary markdown:

```
> **Verification:** 🟢 8 sourced · 🔴 3 unverified · Score: 73%
```

This badge is stripped by the frontend before rendering (the score is shown
separately), but it is preserved in the Markdown export.

**Returns:** `{"draft_itinerary": badge + draft, "verification_score": float}`

---

### 6.7 human_review

**File:** `backend/src/graph.py`

**What it does:** Pauses the graph execution and presents the draft itinerary to
the user for review. The graph suspends here until the user either approves or
provides refinement feedback.

**How it works — LangGraph interrupt:**

LangGraph's `interrupt()` function is the mechanism that pauses execution:

```python
def human_review(state: AgentState) -> dict:
    user_input = interrupt({
        "draft_itinerary": state["draft_itinerary"],
        "verification_score": state.get("verification_score", 0.0),
        "message": "Review the itinerary. Type 'approve' or provide feedback.",
    })
    return {"messages": [{"role": "user", "content": user_input}]}
```

When `interrupt()` is called:

1. LangGraph serialises the entire current state to the `MemorySaver` checkpoint
2. Execution freezes — no further nodes run
3. The `interrupt()` call itself suspends, waiting for a resume value

The backend detects this state via the `__interrupt__` key in the
`on_chain_stream` event and emits an `interrupt` SSE event to the frontend.

**Resuming:** When the user clicks "Approve" or submits feedback, the frontend
POSTs to `/api/v1/feedback`. The backend calls:

```python
graph.astream_events(Command(resume=feedback_text), config)
```

`Command(resume=...)` passes `feedback_text` as the return value of the
suspended `interrupt()` call. Execution resumes from inside `human_review`,
which stores the feedback in the messages list, then `route_after_review`
decides where to go next:

```python
def route_after_review(state: AgentState) -> str:
    last = state["messages"][-1].content.lower().strip()
    if last == "approve":
        return "export"        # → END
    elif any(w in last for w in ["food", "restaurant", "eat", "cuisine"]):
        return "rag"           # → rag_retriever (re-retrieve with food focus)
    else:
        return "draft"         # → draft_plan (small adjustment, re-draft only)
```

---

## 7. RAG — Retrieval-Augmented Generation

### The problem RAG solves

An LLM's knowledge is frozen at its training cutoff. It has no real-time
information about a specific restaurant's current hours, a newly opened attraction,
or a recent weather event. Feeding an LLM raw scraped text directly would exceed
context limits and waste tokens on irrelevant content.

RAG solves this by pre-indexing documents as vectors, then at query time
retrieving only the most semantically relevant chunks to include in the prompt.
The LLM receives focused, relevant, up-to-date information rather than an
overwhelming firehose.

### How RAG works in WanderBot

```
INDEXING PHASE (curate node)
─────────────────────────────
Travel blog articles
        │
        ▼
WebBaseLoader (scrape HTML → plain text)
        │
        ▼
RecursiveCharacterTextSplitter
chunk_size=1000, overlap=200
        │  "...Kinkakuji is open 9am-5pm daily [chunk 1]..."
        │  "...Admission fee is ¥500 [chunk 2]..."
        │  "...The rock garden at Ryoanji... [chunk 3]..."
        ▼
HuggingFace all-MiniLM-L6-v2
(each chunk → 384-dim float vector)
        │  [0.12, -0.34, 0.07, ..., 0.91]  ← chunk 1 vector
        │  [0.15, -0.31, 0.09, ..., 0.88]  ← chunk 2 vector (similar to chunk 1)
        ▼
Qdrant Cloud
(store chunk text + vector, keyed by collection "travel_kyoto")


RETRIEVAL PHASE (rag_retriever node)
──────────────────────────────────────
User query: "things to do in Kyoto, Japan temples nature walks"
        │
        ▼
HuggingFace all-MiniLM-L6-v2
(query → 384-dim vector)
        │  [0.14, -0.33, 0.08, ..., 0.90]
        ▼
Qdrant cosine similarity search (top-5)
        │  Returns: chunk 1 (sim=0.94), chunk 3 (sim=0.91), chunk 7 (sim=0.87)...
        ▼
Concatenated context string → injected into draft_plan prompt
```

### Why cosine similarity?

Cosine similarity measures the angle between two vectors rather than their
magnitude. Semantically similar texts produce vectors that point in similar
directions regardless of length. A chunk about "temple admission fees" and a
query about "cost to enter shrines" will have a high cosine similarity even
though they share no exact words.

### Why `all-MiniLM-L6-v2`?

This 22-million parameter sentence transformer model produces high-quality 384-
dimensional embeddings efficiently. It runs via the HuggingFace Inference API,
requiring no local GPU. 384 dimensions provides a good balance: small enough for
fast Qdrant indexing and search, but expressive enough to capture nuanced
semantic similarity.

---

## 8. The API Layer — FastAPI and SSE Streaming

### Why SSE?

The agent pipeline takes 30–90 seconds to complete (web scraping, embedding,
LLM calls). A traditional HTTP request-response would leave the user staring at
a blank screen for that entire time. Server-Sent Events (SSE) solve this by
keeping the HTTP connection open and pushing events to the client as they happen.

SSE is one-directional (server → client) which is exactly what is needed here:
the server pushes progress updates and token streams; the client uses separate
POST requests for user input.

### Event types

The backend defines and emits the following SSE event types:

| Event | When emitted | Key fields |
|---|---|---|
| `node_start` | A pipeline node begins executing | `node` |
| `node_complete` | A pipeline node finishes | `node`, `destination`, `verification_score` |
| `llm_token` | A token is emitted during `draft_plan` | `token` |
| `interrupt` | The graph pauses at `human_review` | `draft_itinerary`, `verification_score` |
| `done` | The graph reaches `END` | `thread_id` |
| `error` | An exception is caught | `detail` |

### How streaming is implemented

```python
async def _stream_graph_events(inputs, config, thread_id):
    async for event in graph.astream_events(inputs, config, version="v2"):
        kind = event["event"]
        name = event.get("name", "")

        if kind == "on_chain_start" and name in graph.nodes:
            yield _sse(NodeStartEvent(node=name).model_dump())

        elif kind == "on_chain_end" and name in graph.nodes:
            yield _sse(NodeCompleteEvent(node=name, ...).model_dump())

        elif kind == "on_chat_model_stream":
            token = event["data"]["chunk"].content
            if token:
                yield _sse(LLMTokenEvent(token=token).model_dump())

        elif kind == "on_chain_stream":
            if event["data"]["chunk"].get("__interrupt__"):
                yield _sse(InterruptEvent(...).model_dump())
                return  # stop streaming; client resumes via POST /feedback

    yield _sse(DoneEvent(thread_id=thread_id).model_dump())
```

`graph.astream_events()` is LangGraph's async generator that yields every
internal event from the graph and all its nested LangChain calls. The
`version="v2"` parameter uses the newer event format with more granular events.

Each SSE message is a JSON-encoded string prefixed with `data: `:

```
data: {"event": "node_start", "node": "curate"}

data: {"event": "llm_token", "token": "##"}

data: {"event": "interrupt", "draft_itinerary": "# Kyoto...", "verification_score": 0.73}
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/session` | Creates a new `thread_id` (UUID) |
| `POST` | `/api/v1/plan` | Starts a new planning run, returns SSE stream |
| `POST` | `/api/v1/feedback` | Resumes from interrupt, returns SSE stream |
| `GET` | `/api/v1/state/{thread_id}` | Returns current graph state (for page reload) |
| `GET` | `/api/v1/export/{thread_id}` | Returns itinerary as `.md` file download |

---

## 9. Session Persistence — Checkpointing

### What is a checkpoint?

A checkpoint is a snapshot of the complete `AgentState` at a particular moment
in graph execution. LangGraph writes a checkpoint every time a node completes
and every time `interrupt()` is called.

### MemorySaver

In the current deployment, `MemorySaver` stores checkpoints as Python dicts in
the process's RAM:

```python
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
```

### thread_id

Every planning session is identified by a `thread_id` (a UUID created by
`POST /api/v1/session`). The frontend stores this ID and includes it in every
subsequent API call. LangGraph uses it as the checkpoint key:

```python
config = {"configurable": {"thread_id": request.thread_id}}
graph.astream_events(initial_state, config)
```

This means:

- Each browser tab gets its own `thread_id` → independent sessions
- If the user refreshes, `GET /api/v1/state/{thread_id}` can restore the UI
  to the interrupted state
- `Command(resume=feedback)` can only resume a thread that has a pending
  interrupt checkpoint for that `thread_id`

### Limitation

`MemorySaver` is in-memory only. If the Render instance restarts (it spins down
after 15 minutes of inactivity on the free tier), all checkpoints are lost.
Migrating to a Redis- or PostgreSQL-backed checkpointer would make sessions
durable across restarts without any changes to the agent logic.

---

## 10. The Frontend — React Application

### Application phases

The frontend is a state machine with six phases:

```
idle → streaming → interrupted → resuming → done
                               ↘ error
```

| Phase | What the user sees |
|---|---|
| `idle` | Trip input form with example chips |
| `streaming` | Pipeline progress bar + live token preview |
| `interrupted` | Full itinerary + feedback / approve panel |
| `resuming` | Pipeline re-running after feedback |
| `done` | Final itinerary + download buttons |
| `error` | Error message + retry button |

### State management — `usePlanSession`

All session state lives in a single `usePlanSession` custom hook:

```typescript
interface PlanState {
  phase: AppPhase
  threadId: string | null
  destination: string
  activeNode: string | null      // which node is currently running
  completedNodes: string[]       // nodes that have finished
  streamingText: string          // accumulated LLM tokens for live preview
  draftItinerary: string         // final markdown from interrupt event
  verificationScore: number
  error: string | null
}
```

The hook exposes `submitTrip`, `submitFeedback`, `triggerDownload`, and `reset`.

### SSE connection — `fetchEventSource`

`@microsoft/fetch-event-source` is used instead of the native `EventSource`
API because `EventSource` does not support POST requests. The library is
configured with:

```typescript
fetchEventSource(`${BASE}/plan`, {
  method: 'POST',
  body: JSON.stringify({ thread_id, message }),
  openWhenHidden: true,   // keep connection alive when tab is switched
  onerror(err) { throw err },  // prevent auto-reconnect on errors
  onmessage(msg) { onEvent(JSON.parse(msg.data)) },
})
```

`openWhenHidden: true` is critical. Without it, `fetchEventSource` listens for
the browser's `visibilitychange` event and aborts the SSE connection whenever
the tab is hidden (user switches tabs or windows). When the tab becomes visible
again, it reopens the connection by re-POSTing to `/plan`, restarting the entire
graph from the beginning. Setting `openWhenHidden: true` disables this listener
and keeps the pipeline running regardless of tab focus.

### Pipeline progress

`PipelineProgress` receives `activeNode` and `completedNodes` and renders a
horizontal step indicator (desktop) or vertical list (mobile). Each step shows a
Lucide icon:

- Idle: faded icon
- Active: spinning `Loader2` icon with pulse animation
- Complete: DaisyUI `step-primary` styling

### PDF export

When "Download as PDF" is clicked, `jspdf` and `html2canvas` are loaded via
dynamic `import()` (they are code-split and not included in the initial bundle).
The rendered prose div is cloned into a hidden `data-theme="light"` wrapper,
so the captured image always has dark text on a white background regardless of
whether the user is in dark or light mode. The canvas is then sliced into A4
pages and assembled into a multi-page PDF.

---

## 11. End-to-End Data Flow

Here is the complete data flow for a single planning session:

```
1. USER: types "5 days in Kyoto, Japan — couple, mid-range, temples and food"
   clicks "Plan My Trip"

2. FRONTEND: POST /api/v1/session → receives thread_id = "abc-123"
   POST /api/v1/plan { thread_id: "abc-123", message: "5 days in Kyoto..." }
   SSE stream opens.

3. BACKEND: creates initial AgentState, starts graph.astream_events()

4. [analyze node]
   SSE → { event: "node_start", node: "analyze" }
   LLM call 1: extracts destination = "Kyoto, Japan"
   LLM call 2: extracts preferences = { budget: "mid", pace: "moderate",
                interests: ["temples", "food"], travel_party: "couple", ... }
   SSE → { event: "node_complete", node: "analyze", destination: "Kyoto, Japan" }

5. [curate node]
   SSE → { event: "node_start", node: "curate" }
   Tavily search → 5 blog URLs
   WebBaseLoader scrapes 4 URLs → ~200 KB of travel article text
   Chunked into 140 chunks (1000 chars each, 200 overlap)
   HuggingFace embeds 140 chunks → 140 × 384 float vectors
   Qdrant creates "travel_kyoto_japan" collection, stores 140 vectors
   SSE → { event: "node_complete", node: "curate" }

6. [rag_retriever node]
   SSE → { event: "node_start", node: "rag_retriever" }
   Query: "things to do Kyoto, Japan temples food couple mid"
   HuggingFace embeds query → 384-dim vector
   Qdrant similarity search → top 5 chunks returned
   context = joined chunk texts with source metadata
   SSE → { event: "node_complete", node: "rag_retriever" }

7. [live_verifier node]
   SSE → { event: "node_start", node: "live_verifier" }
   Tavily: "Kyoto, Japan current weather travel conditions" → 3 results
   Tavily: "Kyoto, Japan top attractions opening hours 2025 2026" → 3 results
   context += "[Live src:2] Kinkakuji Temple: open 9:00–17:00, ¥500..."
   SSE → { event: "node_complete", node: "live_verifier" }

8. [draft_plan node]
   SSE → { event: "node_start", node: "draft_plan" }
   LLM prompt contains: all user preferences + RAG context + live context
   LLM generates itinerary, token by token:
   SSE → { event: "llm_token", token: "#" }
   SSE → { event: "llm_token", token: " Kyoto" }
   SSE → { event: "llm_token", token: ", Japan" }
   ... (500+ tokens)
   SSE → { event: "node_complete", node: "draft_plan" }

9. [validate_citations node]
   SSE → { event: "node_start", node: "validate_citations" }
   Regex scan: 6 [src:N] tags found, 4 [Unverified] tags found
   score = 6 / (6 + 4) = 0.60
   Badge prepended to itinerary
   SSE → { event: "node_complete", node: "validate_citations" }

10. [human_review node]
    interrupt() called → LangGraph saves full checkpoint to MemorySaver
    SSE → { event: "interrupt", draft_itinerary: "# Kyoto...", verification_score: 0.60 }
    SSE stream closes.

11. FRONTEND: phase → "interrupted"
    Renders ItineraryView (full markdown) + FeedbackPanel

12. USER: reads the draft, clicks "Approve & Download Itinerary"
    FRONTEND: POST /api/v1/feedback { thread_id: "abc-123", feedback: "approve" }
    SSE stream reopens.

13. BACKEND: Command(resume="approve") → human_review returns feedback to graph
    route_after_review: "approve" → returns "export" → graph reaches END
    SSE → { event: "done", thread_id: "abc-123" }
    SSE stream closes.

14. FRONTEND: phase → "done"
    User clicks "Download as PDF" → dynamic import of jspdf + html2canvas
    PDF generated from rendered prose div, saved as "itinerary_kyoto_japan.pdf"
```

---

## 12. Anti-Hallucination Strategy

Hallucination — an LLM confidently asserting false information — is the core
problem WanderBot is designed to solve. Three structural measures are in place:

### Measure 1: RAG grounding

The draft_plan LLM call receives only content retrieved from real web sources in
the current session. It does not rely on its training weights for factual
claims about specific venues, hours, or prices.

### Measure 2: Mandatory tool use

The `draft_plan` system prompt includes a non-negotiable rule:

> You MUST invoke at least one tool before generating any itinerary text.
> Tool calls are not optional — they are required by the system.

In WanderBot's architecture, the "tools" are the RAG and live search results
pre-populated into the context before the LLM call. This instruction prevents
the LLM from bypassing the retrieved evidence and writing from memory.

### Measure 3: Citation enforcement

Every factual claim must carry `[src:N]` (sourced from a retrieved result) or
`[Unverified]` (cannot be confirmed). The prompt instructs:

> Training data is not a source. If your training data says a venue closes at
> 18:00 but no tool result confirms this, write [Unverified].

`validate_citations` then counts these annotations and computes a score. The
frontend replaces `[Unverified]` with *not confirmed* (italic) in the rendered
view so users can immediately see which claims need independent verification.

---

## 13. Iterative Refinement Loop

After the first draft, the user can request changes rather than approving.
WanderBot resumes from the checkpoint and re-runs a subset of the pipeline:

```
User feedback: "add more restaurant options, Day 3 is too packed"
    ↓
route_after_review detects "restaurant" keyword → returns "rag"
    ↓
rag_retriever re-runs with updated query (food-focused)
    ↓
live_verifier re-runs (fetches updated live data)
    ↓
draft_plan re-runs with refined context + full message history
    (The LLM sees all previous messages so it knows what was already discussed)
    ↓
validate_citations re-runs
    ↓
human_review fires again → new interrupt
    ↓
User reviews revised draft
```

The `analyze` and `curate` nodes are skipped in refinement rounds:
- `analyze` only re-runs if a new `POST /plan` is made (new trip)
- `curate` is skipped because `knowledge_ready = True` from the first run

This makes refinement significantly faster than a full re-run.

---

## 14. Deployment

### Services

| Service | What runs there | URL |
|---|---|---|
| **Netlify** | React frontend (static build) | `wanderbot-frontend.netlify.app` |
| **Render** | FastAPI backend (Python process) | `wanderbot-backend.onrender.com` |
| **Qdrant Cloud** | Vector store | Qdrant Cloud cluster URL |

### Frontend (Netlify)

Netlify builds the frontend with `tsc -b && vite build`. The `VITE_API_URL`
environment variable is baked into the JS bundle at build time:

```typescript
const BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`
```

In development, `VITE_API_URL` is unset and `BASE` becomes `/api/v1`, which
Vite's dev server proxies to `localhost:8000`. In production, `VITE_API_URL` is
set to `https://wanderbot-backend.onrender.com`.

### Backend (Render)

Render runs: `uvicorn src.api.app:app --host 0.0.0.0 --port 8000`

`ALLOWED_ORIGINS` is set to `https://wanderbot-frontend.netlify.app` so the
FastAPI CORS middleware allows cross-origin requests from Netlify.

### Environment variables

See [Section 15](#15-environment-variables-reference).

---

## 15. Environment Variables Reference

All secrets are loaded by `python-decouple` from a `.env` file in development.
On Render, they are set as environment variables in the service dashboard.

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |
| `TAVILY_API_KEY` | Yes | Tavily Search API key |
| `HUGGINGFACEHUB_API_TOKEN` | Yes | HuggingFace token for embeddings inference |
| `QDRANT_URL` | Yes | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Yes | Qdrant Cloud API key |
| `ALLOWED_ORIGINS` | Yes (prod) | Comma-separated list of allowed CORS origins |
| `ORS_API_KEY` | No | OpenRouteService key (logistics, future use) |

Frontend (Netlify):

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | Yes (prod) | Backend base URL, e.g. `https://wanderbot-backend.onrender.com` |
