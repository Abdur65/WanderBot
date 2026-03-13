# Product Requirements Document (PRD)
## WanderBot — AI-Powered Travel Itinerary Planning Assistant

**Document Version:** 1.1
**Status:** Draft
**Last Updated:** March 2026

---

## 1. Product Overview

**Product Name:** WanderBot
**Type:** AI Web Application
**Tagline:** Your autonomous travel planner, grounded in real-world knowledge.

WanderBot is an autonomous AI agent that generates personalised, verified travel
itineraries by combining real-time web research, scraped travel guide content, and
logistics data. Users interact through a conversational interface, refine their plan
iteratively, and export a final verified itinerary.

---

## 2. Problem Statement

Travellers planning a trip face three compounding problems. First, generic AI
assistants produce itineraries from stale training data — recommending venues that
have closed, citing outdated opening hours, and fabricating specifics with false
confidence. Second, the output is logistically incomplete — a list of places with no
indication of how long it takes to get between them or how to do so. Third, the
planning process is fragmented across multiple tools: one tab for blogs, another for
maps, another for weather — with no unified interface to synthesise it all.

WanderBot solves all three by acting as a single autonomous agent that researches,
verifies, enriches with logistics, and presents a ready-to-use itinerary.

---

## 3. Goals & Non-Goals

### Goals
- Produce day-by-day itineraries grounded exclusively in verified, sourced
  information.
- Enrich every itinerary stop with real travel time and travel mode to the next stop.
- Allow iterative refinement through natural conversation.
- Persist planning sessions so users can return and continue later.
- Deliver the experience through a modern, responsive web interface (React +
  FastAPI).

### Non-Goals
- WanderBot will not book flights, hotels, or activities.
- WanderBot will not provide visa or legal travel advice.
- WanderBot will not support group itinerary collaboration in v1.
- WanderBot will not operate as a mobile native app in v1.
- WanderBot will not integrate Google AI or Vertex AI tooling.

---

## 4. Target Users

**Primary — The Independent Planner**
A traveller aged 22–45 who plans their own trips, is comfortable with technology,
and is frustrated by the time it takes to cross-reference blogs, maps, and review
sites to build a coherent itinerary.

**Secondary — The Spontaneous Traveller**
Someone with a destination in mind but no plan, who wants a solid starting point
quickly without spending hours researching.

**Out of Scope for v1**
Travel agents, corporate travel managers, and group trip coordinators.

---

## 5. User Stories

### Epic 1 — Destination Input & Preference Capture

**US-01**
As a user, I want to describe my trip in plain language (e.g. "I want to spend 4 days
in Kyoto, I love food and temples, mid-range budget") so that WanderBot understands
my destination and preferences without filling in a form.

**US-02**
As a user, I want WanderBot to confirm the destination and preferences it extracted
from my message so that I can correct any misunderstanding before research begins.

**US-03**
As a user, I want to specify dietary requirements, mobility preferences, and travel
pace so that the itinerary reflects my actual constraints.

---

### Epic 2 — Autonomous Research

**US-04**
As a user, I want WanderBot to automatically find and read relevant travel guides for
my destination so that I do not have to provide any source URLs manually.

**US-05**
As a user, I want the agent to verify current conditions (weather, closures, opening
hours) via live web search so that the itinerary reflects the real state of the
destination at the time of planning.

**US-06**
As a user, I want to see a source citation next to each factual claim in the itinerary
so that I know where the information came from and can verify it myself.

**US-07**
As a user, I want any unverified claim to be clearly flagged as [Unverified] rather
than presented as fact so that I am never misled by fabricated information.

---

### Epic 3 — Itinerary Generation

**US-08**
As a user, I want the itinerary to be structured by day and time slot (e.g.
09:00–11:00) so that it is immediately actionable without reformatting.

**US-09**
As a user, I want each itinerary stop to include the estimated travel time and
recommended travel mode to the next stop (e.g. ↳ [Walk · 14 min]) so that I can
plan my day realistically.

**US-10**
As a user, I want the travel time and mode to be computed from a real logistics API
and not estimated by the AI so that the figures are accurate.

**US-11**
As a user, I want the itinerary to respect my budget level — suggesting free or cheap
options for budget travellers and premium options for luxury travellers.

---

### Epic 4 — Iterative Refinement

**US-12**
As a user, I want to provide natural language feedback on the draft itinerary (e.g.
"less walking, more food") and have WanderBot regenerate a revised plan so that I
can shape the itinerary without starting from scratch.

**US-13**
As a user, I want WanderBot to remember the context of my earlier feedback across
multiple refinement rounds so that I do not have to repeat myself.

**US-14**
As a user, I want to be able to swap a specific day's activities without affecting the
rest of the itinerary so that targeted changes do not require a full regeneration.

---

### Epic 5 — Session Persistence

**US-15**
As a user, I want my planning session to be saved automatically so that I can close
the browser and return later to continue where I left off.

**US-16**
As a user, I want each browser tab to maintain its own independent session so that I
can plan two different trips simultaneously without them interfering.

---

### Epic 6 — Review & Export

**US-17**
As a user, I want to review the final itinerary in a clean, readable preview panel
before approving it so that I can catch any issues before exporting.

**US-18**
As a user, I want to approve the itinerary and download it as a Markdown (.md) file
so that I have an offline copy I can use during my trip.

**US-19**
As a user, I want to see a verification badge on the itinerary indicating how many
claims are fully sourced vs flagged as unverified so that I can gauge the overall
reliability of the plan at a glance.

---

### Epic 7 — Interface & Experience

**US-20**
As a user, I want to interact with WanderBot through a chat interface so that the
experience feels conversational rather than form-based.

**US-21**
As a user, I want to see the itinerary update in a side panel as the agent works so
that I have visibility into progress without waiting for a full page reload.

**US-22**
As a user, I want to set my preferences (budget, pace, interests) from a sidebar
panel so that I can adjust them at any point during the session.

**US-23**
As a user, I want the interface to work well on both desktop and tablet so that I can
plan my trip from whatever device I am using.

---

## 6. Functional Requirements

| ID    | Requirement                                                                 | Priority |
|-------|-----------------------------------------------------------------------------|----------|
| FR-01 | System must extract destination and preferences from free-text input        | Must     |
| FR-02 | System must search for and scrape travel blog content automatically         | Must     |
| FR-03 | System must fall back to live search results if scraping fails              | Must     |
| FR-04 | System must verify facts via Tavily before including them in the draft      | Must     |
| FR-05 | System must enforce tool-use before any LLM factual output                  | Must     |
| FR-06 | System must flag unverified claims rather than omit or fabricate them       | Must     |
| FR-07 | System must compute travel time and mode via Logistics API for every stop   | Must     |
| FR-08 | System must support iterative refinement without losing session context     | Must     |
| FR-09 | System must persist sessions across browser closes via LangGraph checkpoint | Must     |
| FR-10 | System must export the approved itinerary as a .md file                     | Must     |
| FR-11 | System must cap Tavily search calls per session to prevent runaway costs    | Must     |
| FR-12 | System must display source citations inline in the itinerary output         | Should   |
| FR-13 | System must show a verification health badge on the itinerary preview       | Should   |
| FR-14 | System must support targeted day-level regeneration                         | Could    |

---

## 7. Non-Functional Requirements

**Performance**
The first draft itinerary should be delivered within 60 seconds of the user's initial
message under normal network conditions. Logistics API calls must be parallelised
to prevent sequential blocking.

**Reliability**
If any external API (Tavily, Logistics, HuggingFace) is unavailable, the system must
degrade gracefully — continuing with available data and flagging gaps — rather than
crashing the session.

**Security**
All API keys must be loaded via environment variables and never exposed to the
frontend. The FastAPI backend must validate all inputs with Pydantic before
processing.

**Scalability**
The v1 architecture is single-user per process. The session model (thread_id per
tab) must be designed so that moving to a multi-user deployment requires only the
addition of a persistent store (e.g. Redis) with no changes to agent logic.

**Maintainability**
Each LangGraph node must be a self-contained Python module. Adding or removing a
node must not require changes to any other node's code.

---

## 8. Tech Stack

| Layer             | Technology                              |
|-------------------|-----------------------------------------|
| Frontend          | React (Vite + TypeScript), TailwindCSS  |
| Backend API       | FastAPI, uvicorn                        |
| Agent Framework   | LangGraph (StateGraph, MemorySaver)     |
| LLM               | Groq — llama-3.3-70b-versatile          |
| Vector Store      | Qdrant                                  |
| Embeddings        | HuggingFace — all-MiniLM-L6-v2         |
| Web Search        | Tavily                                  |
| Scraping          | WebBaseLoader, BeautifulSoup            |
| Logistics         | OpenRouteService                        |
| Config            | python-decouple                         |
| Package Manager   | uv (Python), Bun (frontend)             |
| Containerisation  | Docker, Docker Compose *(optional)*     |

---

## 9. Architecture Summary
```
[ React Frontend ]
        ↕ SSE stream / REST
[ FastAPI Backend ]
        ↕ graph.invoke() / astream_events()
[ LangGraph Agent ]
  Analyze → Curate → RAG_Retriever → Live_Verifier
  → Draft_Plan → Validate_Citations → Logistics_Enricher
  → Human_Review → END
        ↕                ↕                   ↕
   [ Qdrant ]        [ Tavily ]     [ OpenRouteService ]
```

---

## 10. Development Phases

| Phase | Scope                                    |
|-------|------------------------------------------|
| 1     | Core LangGraph agent — no UI             |
| 2     | Anti-hallucination layer                 |
| 3     | Logistics enrichment                     |
| 4     | FastAPI backend + SSE streaming          |
| 5     | React frontend                           |
| 6     | Integration testing & hardening          |
| 7     | Polish, export, and deployment           |

---

## 11. Deployment

### Standard Deployment (Recommended)

| Service       | Role              | Free Tier                              |
|---------------|-------------------|----------------------------------------|
| Netlify        | React frontend    | Free for personal projects        |
| Render        | FastAPI backend   | 750 hrs/month, spins down on idle      |
| Qdrant Cloud  | Vector store      | 1 free cluster, 1GB storage            |

### Docker Deployment *(Optional)*

Docker may be used to containerise the FastAPI backend for teams who prefer
environment consistency or plan to self-host. It is not required for deployment to
Render or Netlify.

When Docker is used:

- The backend is packaged via a `Dockerfile` in `backend/`.
- Local development uses `docker-compose.yml` to orchestrate the backend and an
  optional local Qdrant instance.
- Render accepts a Dockerfile directly, replacing the default Python build process.
- The frontend is deployed to Netlify regardless of whether Docker is used for the
  backend.
- API keys are always passed as runtime environment variables and never baked
  into the image.

---

## 12. Out of Scope (v1)

- User authentication and accounts
- Saving multiple itineraries per user
- Social sharing of itineraries
- Mobile native app
- Multi-language support
- Real-time flight or hotel pricing

---

## 13. Open Questions

| #  | Question                                                                      | Owner |
|----|-------------------------------------------------------------------------------|-------|
| 1  | Should Qdrant run in-memory (dev) or cloud (prod) from day one?               | Dev   |
| 2  | What is the maximum number of days an itinerary should cover in v1?           | Dev   |
| 3  | Should the .md export include source URLs as a reference section?             | Dev   |
| 4  | Should Docker be adopted as the standard deployment approach or kept optional? | Dev   |

---
