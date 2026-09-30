import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Tuple


PROVINCE_CODES = {
    "Padova": "PD",
    "Belluno": "BL",
    "Rovigo": "RO",
    "Treviso": "TV",
    "Venezia": "VE",
    "Verona": "VR",
    "Vicenza": "VI",
}


def number(value):
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None


def format_timestamp(value: str) -> str:
    text = (value or "").strip()
    try:
        return datetime.strptime(text, "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text


def latest_valid_sample(samples):
    """Preferisce l'ultima misura numerica agli intervalli ARPAV ancora vuoti."""
    ordered = sorted(samples, key=lambda item: item.attrib.get("ISTANTE", ""), reverse=True)
    return next((item for item in ordered if number(item.findtext("VM")) is not None), ordered[0] if ordered else None)


def parse_arpav_xml(payload: bytes, province: str = "Padova") -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    root = ET.fromstring(payload)
    projection = (root.findtext("PROJECTION") or "").strip().upper()
    if projection and projection not in ("EPSG:4258", "EPSG:4326"):
        raise ValueError("Sistema di riferimento ARPAV non previsto: %s" % projection)

    province_code = PROVINCE_CODES.get(province)
    stations = []
    station_nodes = root.findall(".//STAZIONE")
    selected_station_ids = set()

    for node in station_nodes:
        node_province = (node.findtext("PROVINCIA") or "").strip().upper()
        if province_code and node_province != province_code:
            continue

        station_id = (node.findtext("IDSTAZ") or "").strip()
        selected_station_ids.add(station_id)
        base = {
            "station_id": station_id,
            "name": (node.findtext("NOME") or "").strip(),
            "municipality": (node.findtext("COMUNE") or "").strip(),
            "province": node_province,
            "elevation": number(node.findtext("QUOTA")),
            "longitude": number(node.findtext("X")),
            "latitude": number(node.findtext("Y")),
            "source": "ARPAV",
        }

        for sensor in node.findall("SENSORE"):
            samples = sensor.findall("DATI")
            latest_node = latest_valid_sample(samples)
            item = dict(base)
            item.update({
                "sensor_id": (sensor.findtext("ID") or "").strip(),
                "sensor_type": (sensor.findtext("PARAMNM") or sensor.findtext("TYPE") or "").strip(),
                "unit": (sensor.findtext("UNITNM") or "").strip(),
                "latest": {
                    "value": number(latest_node.findtext("VM")) if latest_node is not None else None,
                    "observed_at": format_timestamp(latest_node.attrib.get("ISTANTE", "")) if latest_node is not None else "",
                    "state": "automatico non validato",
                },
            })
            stations.append(item)

    summary = {
        "stations": len(selected_station_ids),
        "sensors": len(stations),
        "measurements": sum(1 for item in stations if item["latest"]["value"] is not None),
        "provided_at": format_timestamp(root.findtext("ISTANTERUN") or ""),
        "projection": projection,
    }
    return stations, summary
