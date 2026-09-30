from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, Optional


RECENT_MINUTES = 30
DELAYED_MINUTES = 180


def parse_observed_at(value: str, utc_offset_minutes: Optional[int] = None) -> Optional[datetime]:
    text = (value or "").strip()
    if not text:
        return None

    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    parsed = None
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for pattern in ("%Y%m%d%H%M", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue

    if parsed is None:
        return None
    if parsed.tzinfo is None and utc_offset_minutes is not None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(minutes=utc_offset_minutes)))
    return parsed


def freshness_state(
    observed_at: str,
    now: Optional[datetime] = None,
    utc_offset_minutes: Optional[int] = None,
) -> Dict[str, object]:
    observed = parse_observed_at(observed_at, utc_offset_minutes)
    if observed is None:
        return {"state": "Data assente", "age_minutes": None}

    reference = now or datetime.now(observed.tzinfo)
    if observed.tzinfo is not None and reference.tzinfo is None:
        reference = reference.replace(tzinfo=observed.tzinfo)
    elif observed.tzinfo is None and reference.tzinfo is not None:
        observed = observed.replace(tzinfo=reference.tzinfo)

    age = max(0, int((reference - observed).total_seconds() // 60))
    if age <= RECENT_MINUTES:
        state = "Recente"
    elif age <= DELAYED_MINUTES:
        state = "Ritardato"
    else:
        state = "Scaduto"
    return {"state": state, "age_minutes": age}


def annotate_freshness(stations: Iterable[Dict[str, object]], now: Optional[datetime] = None) -> Dict[str, int]:
    counts = {"Recente": 0, "Ritardato": 0, "Scaduto": 0, "Data assente": 0}
    for station in stations:
        latest = station.setdefault("latest", {})
        result = freshness_state(
            str(latest.get("observed_at", "")),
            now=now,
            utc_offset_minutes=latest.get("utc_offset_minutes"),
        )
        latest["freshness"] = result["state"]
        latest["age_minutes"] = result["age_minutes"]
        counts[result["state"]] += 1
    return counts

