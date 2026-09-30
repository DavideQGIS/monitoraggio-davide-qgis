from typing import Dict, List


def parse_geojson(payload) -> List[Dict[str, object]]:
    events = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 2:
            continue
        events.append({
            "event_id": str(properties.get("eventId", "")),
            "time": str(properties.get("time", "")),
            "magnitude": properties.get("mag"),
            "mag_type": str(properties.get("magType", "")),
            "place": str(properties.get("place", "")),
            "longitude": coordinates[0],
            "latitude": coordinates[1],
            "depth": coordinates[2] if len(coordinates) > 2 else None,
        })
    events.sort(key=lambda item: item["time"], reverse=True)
    return events
