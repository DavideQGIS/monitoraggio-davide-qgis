from typing import Dict, List, Optional


REFERENCE = "https://allertameteo.regione.emilia-romagna.it/livello-idrometrico"


def number(value, zero_is_none: bool = False) -> Optional[float]:
    try:
        result = float(str(value).replace(",", "."))
        return None if zero_is_none and result == 0 else result
    except (TypeError, ValueError):
        return None


def parse_hydro_payload(payload, observed_at: str) -> List[Dict[str, object]]:
    """Normalizza idrometri e tre soglie ufficiali del feed ARPAE."""
    stations = []
    for row in payload:
        sensor_id = str(row.get("idstazione", ""))
        if not sensor_id:
            continue
        longitude = number(row.get("lon"))
        latitude = number(row.get("lat"))
        if longitude is not None:
            longitude /= 100000.0
        if latitude is not None:
            latitude /= 100000.0
        name = str(row.get("nomestaz", ""))
        threshold = {
            "source": "ARPAE Emilia-Romagna",
            "sensor_id": sensor_id,
            "station_name": name,
            "sensor_type": "Livello idrometrico",
            "direction": "above",
            "attention": number(row.get("soglia1"), True),
            "prealarm": number(row.get("soglia2"), True),
            "alarm": number(row.get("soglia3"), True),
            "unit": "m",
            "valid_from": "",
            "reference": REFERENCE,
        }
        stations.append({
            "station_id": sensor_id,
            "sensor_id": sensor_id,
            "name": name,
            "municipality": "",
            "province": "ER",
            "sensor_type": "Livello idrometrico",
            "unit": "m",
            "elevation": None,
            "longitude": longitude,
            "latitude": latitude,
            "source": "ARPAE Emilia-Romagna",
            "latest": {
                "value": number(row.get("value")),
                "observed_at": observed_at,
                "state": "precedente" if row.get("precedente") == "S" else "corrente",
            },
            "threshold": threshold,
        })
    return stations
