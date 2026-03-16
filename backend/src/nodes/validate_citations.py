import re
from src.state import AgentState

# [src:1], [src:12], etc.
SRC_PATTERN = re.compile(r"\[src:(\d+)\]")
# [Unverified], [Unverified — recommend calling ahead], etc.
UNVERIFIED_PATTERN = re.compile(r"\[unverified[^\]]*\]", re.IGNORECASE)


def validate_citations(state: AgentState) -> dict:
    draft = state.get("draft_itinerary", "")

    cited_indices = set(SRC_PATTERN.findall(draft))
    cited_count = len(cited_indices)
    unverified_count = len(UNVERIFIED_PATTERN.findall(draft))

    total_claims = cited_count + unverified_count
    score = (cited_count / total_claims) if total_claims > 0 else 0.0

    if score >= 0.80:
        colour = "🟢"
    elif score >= 0.50:
        colour = "🟡"
    else:
        colour = "🔴"

    badge = (
        f"> **Verification:** {colour} {cited_count} sourced · "
        f"🔴 {unverified_count} unverified · Score: {round(score * 100)}%\n\n"
    )

    print(
        f"[Citations] sourced={cited_count}, unverified={unverified_count}, "
        f"score={round(score * 100)}%"
    )

    return {
        "draft_itinerary": badge + draft,
        "verification_score": round(score, 4),
    }
