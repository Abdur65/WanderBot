import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import openrouteservice
from openrouteservice.geocode import pelias_search
from openrouteservice.directions import directions

from src.config import ORS_API_KEY
from src.state import AgentState

# Matches: ### 09:00–11:00  Senso-ji Temple  (en-dash or hyphen, 2+ spaces before venue)
STOP_PATTERN = re.compile(
    r"^###\s+\d{2}:\d{2}[–\-]\d{2}:\d{2}\s{2,}(.+)$",
    re.MULTILINE,
)
PLACEHOLDER_PATTERN = re.compile(r"↳ \[LOGISTICS_PLACEHOLDER\]")

MOBILITY_TO_ORS_PROFILE = {
    "walking": "foot-walking",
    "transit": "foot-walking",   # conservative upper bound; labelled differently
    "driving": "driving-car",
}
MOBILITY_TO_LABEL = {
    "walking": "walking",
    "transit": "est. transit",
    "driving": "driving",
}


def _geocode(
    client: openrouteservice.Client,
    venue_name: str,
    destination: str,
) -> Optional[tuple[float, float]]:
    """Returns (lon, lat) for the venue or None on failure."""
    query = f"{venue_name}, {destination}"
    try:
        result = pelias_search(client, text=query, size=1)
        features = result.get("features", [])
        if not features:
            return None
        coords = features[0]["geometry"]["coordinates"]  # [lon, lat]
        return (float(coords[0]), float(coords[1]))
    except Exception as e:
        print(f"[Logistics] Geocode failed for '{venue_name}': {e}")
        return None


def _route_segment(
    client: openrouteservice.Client,
    origin: tuple[float, float],
    dest: tuple[float, float],
    profile: str,
    label: str,
) -> str:
    """Returns a formatted `↳ label · ~N min` string, or a fallback."""
    try:
        result = directions(
            client,
            coordinates=[list(origin), list(dest)],
            profile=profile,
        )
        duration_s = sum(
            seg["duration"] for seg in result["routes"][0]["segments"]
        )
        duration_min = max(1, round(duration_s / 60))
        return f"↳ {label} · ~{duration_min} min"
    except Exception as e:
        print(f"[Logistics] Directions failed ({profile}): {e}")
        return f"↳ {label} · [time unavailable]"


def _enrich(draft: str, destination: str, mobility: str) -> str:
    if not ORS_API_KEY:
        print("[Logistics] ORS_API_KEY not set — skipping enrichment.")
        return draft

    client = openrouteservice.Client(key=ORS_API_KEY)
    profile = MOBILITY_TO_ORS_PROFILE.get(mobility, "foot-walking")
    label = MOBILITY_TO_LABEL.get(mobility, "transit")

    venue_names = [m.group(1).strip() for m in STOP_PATTERN.finditer(draft)]
    if len(venue_names) < 2:
        return draft

    # Phase A — geocode all venues in parallel
    coords: dict[str, Optional[tuple[float, float]]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        fut_to_name = {
            pool.submit(_geocode, client, name, destination): name
            for name in venue_names
        }
        for fut in as_completed(fut_to_name):
            coords[fut_to_name[fut]] = fut.result()

    # Phase B — compute directions for each consecutive pair in parallel
    pairs = list(zip(venue_names[:-1], venue_names[1:]))
    segment_results: dict[int, str] = {}

    def _compute(idx: int, origin_name: str, dest_name: str) -> tuple[int, str]:
        o = coords.get(origin_name)
        d = coords.get(dest_name)
        if o is None or d is None:
            return idx, f"↳ {label} · [route unavailable — geocoding failed]"
        return idx, _route_segment(client, o, d, profile, label)

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_compute, i, o, d): i for i, (o, d) in enumerate(pairs)}
        for fut in as_completed(futs):
            idx, seg = fut.result()
            segment_results[idx] = seg

    # Replace placeholders sequentially (re.sub calls replacement left-to-right)
    counter = [0]

    def _replace(_match):
        result = segment_results.get(counter[0], "↳ [logistics unavailable]")
        counter[0] += 1
        return result

    enriched = PLACEHOLDER_PATTERN.sub(_replace, draft)
    print(f"[Logistics] Replaced {counter[0]} logistics placeholder(s).")
    return enriched


def logistics_enricher(state: AgentState) -> dict:
    destination = state["destination"]
    mobility = state["preferences"].mobility
    draft = state.get("draft_itinerary", "")

    print(f"[Logistics] Enriching stops for {destination} (mobility: {mobility})...")
    return {"draft_itinerary": _enrich(draft, destination, mobility)}
