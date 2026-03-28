"""
Fetches weather data for the trip dates using Open-Meteo (free, no API key).

- Within 16 days of today → real forecast
- Further out             → same calendar dates from last year via the
                            ERA5 archive (good proxy for typical conditions)
- No start date           → skipped gracefully
"""

import requests
from datetime import date, timedelta
from src.state import AgentState

# WMO weather interpretation codes → human-readable label
_WMO = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}

def _wmo_label(code: int) -> str:
    return _WMO.get(code, "Variable")


def _geocode(destination: str) -> tuple[float, float] | None:
    """Return (lat, lon) using Open-Meteo's free geocoding API."""
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": destination, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        )
        results = r.json().get("results", [])
        if results:
            return results[0]["latitude"], results[0]["longitude"]
    except Exception as e:
        print(f"[Weather] Geocode failed: {e}")
    return None


def _fetch_forecast(lat: float, lon: float, start: date, end: date) -> list[dict]:
    """Real forecast — works up to ~16 days ahead."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
                "timezone": "auto",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            timeout=10,
        )
        return r.json().get("daily", {})
    except Exception as e:
        print(f"[Weather] Forecast fetch failed: {e}")
        return {}


def _fetch_archive(lat: float, lon: float, start: date, end: date) -> list[dict]:
    """Historical ERA5 archive for the same calendar dates one year ago."""
    start_prev = start.replace(year=start.year - 1)
    end_prev   = end.replace(year=end.year - 1)
    try:
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": "auto",
                "start_date": start_prev.isoformat(),
                "end_date": end_prev.isoformat(),
            },
            timeout=10,
        )
        return r.json().get("daily", {})
    except Exception as e:
        print(f"[Weather] Archive fetch failed: {e}")
        return {}


def _parse_daily(raw: dict, trip_start: date, is_forecast: bool) -> list[dict]:
    """Convert Open-Meteo daily response into our weather_data list."""
    dates      = raw.get("time", [])
    highs      = raw.get("temperature_2m_max", [])
    lows       = raw.get("temperature_2m_min", [])
    rain_probs = raw.get("precipitation_probability_max") or raw.get("precipitation_sum") or []
    codes      = raw.get("weathercode", [])

    result = []
    for i, d in enumerate(dates):
        # Map archive date back to the actual trip date
        data_date = date.fromisoformat(d)
        if not is_forecast:
            # shift back by 1 year to get the real trip date
            actual_date = data_date.replace(year=data_date.year + 1)
        else:
            actual_date = data_date

        day_num = (actual_date - trip_start).days + 1

        rain_raw = rain_probs[i] if i < len(rain_probs) else None
        # archive uses precipitation_sum (mm) instead of probability
        rain_prob = int(rain_raw) if rain_raw is not None and is_forecast else None
        # For archive data, convert mm → rough probability (>5mm ≈ rainy day)
        if rain_raw is not None and not is_forecast:
            rain_prob = min(100, int(float(rain_raw) * 10))

        code = int(codes[i]) if i < len(codes) else 0

        result.append({
            "day":         day_num,
            "date":        actual_date.isoformat(),
            "high_c":      round(highs[i], 1)  if i < len(highs) else None,
            "low_c":       round(lows[i],  1)  if i < len(lows)  else None,
            "rain_prob":   rain_prob,
            "description": _wmo_label(code),
            "is_forecast": is_forecast,
        })
    return result


def _format_context(weather: list[dict], destination: str) -> str:
    if not weather:
        return ""
    label = "Weather forecast" if weather[0]["is_forecast"] else "Historical weather (typical conditions)"
    lines = [f"═══ {label} for {destination} ═══"]
    for w in weather:
        parts = [f"Day {w['day']} ({w['date']}): {w['description']}"]
        if w["high_c"] is not None:
            parts.append(f"High {w['high_c']}°C / Low {w['low_c']}°C")
        if w["rain_prob"] is not None:
            parts.append(f"Rain {w['rain_prob']}%")
        lines.append("  " + " · ".join(parts))
    lines.append("Use this to schedule outdoor activities on clear days and indoor ones when rain is likely.")
    return "\n".join(lines)


# ── node ─────────────────────────────────────────────────────────────────────

def weather_enricher(state: AgentState) -> dict:
    destination  = state["destination"]
    preferences  = state["preferences"]
    start_str    = preferences.travel_start_date
    duration     = preferences.duration_days or 3

    if not start_str:
        print("[Weather] No travel date — skipping.")
        return {"weather_data": []}

    try:
        trip_start = date.fromisoformat(start_str)
    except ValueError:
        print(f"[Weather] Invalid date '{start_str}' — skipping.")
        return {"weather_data": []}

    trip_end = trip_start + timedelta(days=duration - 1)
    today    = date.today()
    days_out = (trip_start - today).days

    latlon = _geocode(destination)
    if not latlon:
        print("[Weather] Could not geocode destination — skipping.")
        return {"weather_data": []}

    lat, lon = latlon

    if days_out <= 15:
        print(f"[Weather] Fetching forecast for {destination} ({start_str} → {trip_end})…")
        raw         = _fetch_forecast(lat, lon, trip_start, trip_end)
        is_forecast = True
    else:
        print(f"[Weather] Trip is {days_out} days out — using historical data for {destination}…")
        raw         = _fetch_archive(lat, lon, trip_start, trip_end)
        is_forecast = False

    weather = _parse_daily(raw, trip_start, is_forecast)
    if not weather:
        return {"weather_data": []}

    # Append weather context to existing RAG+live context so draft_plan can use it
    weather_ctx = _format_context(weather, destination)
    existing_ctx = state.get("context", "")
    combined_ctx = f"{existing_ctx}\n\n{weather_ctx}" if existing_ctx else weather_ctx

    print(f"[Weather] Got {len(weather)} day(s) of {'forecast' if is_forecast else 'historical'} data.")
    return {"weather_data": weather, "context": combined_ctx}
