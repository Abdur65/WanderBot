import re

from src.state import AgentState

PLACEHOLDER_PATTERN = re.compile(r'↳ \[LOGISTICS_PLACEHOLDER\]\n?')


def logistics_enricher(state: AgentState) -> dict:
    draft = state.get("draft_itinerary", "")
    cleaned = PLACEHOLDER_PATTERN.sub('', draft)
    return {"draft_itinerary": cleaned}
