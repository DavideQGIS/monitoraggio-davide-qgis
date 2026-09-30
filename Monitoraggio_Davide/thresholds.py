import csv


FIELDS = [
    "source", "sensor_id", "station_name", "sensor_type", "direction",
    "attention", "prealarm", "alarm", "unit", "valid_from", "reference",
]


def _number(value):
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return None


def load_thresholds(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Colonne mancanti: " + ", ".join(missing))
        for raw in reader:
            row = {field: (raw.get(field) or "").strip() for field in FIELDS}
            row["attention"] = _number(row["attention"])
            row["prealarm"] = _number(row["prealarm"])
            row["alarm"] = _number(row["alarm"])
            row["direction"] = (row["direction"] or "above").lower()
            if row["direction"] not in ("above", "below"):
                raise ValueError("direction deve essere above oppure below")
            if not row["sensor_id"] and not row["station_name"]:
                continue
            rows.append(row)
    return rows


def write_template(path):
    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerow({
            "source": "ARPA Lombardia", "sensor_id": "ID_UFFICIALE", "station_name": "",
            "sensor_type": "Livello idrometrico", "direction": "above",
            "attention": "", "prealarm": "", "alarm": "", "unit": "m",
            "valid_from": "AAAA-MM-GG", "reference": "Atto o URL ufficiale",
        })


def _matches(station, threshold, source):
    if threshold["source"] and threshold["source"].casefold() != source.casefold():
        return False
    if threshold["sensor_id"]:
        return threshold["sensor_id"] == str(station.get("sensor_id", ""))
    return (
        threshold["station_name"].casefold() == str(station.get("name", "")).casefold()
        and (not threshold["sensor_type"] or threshold["sensor_type"].casefold() in str(station.get("sensor_type", "")).casefold())
    )


def evaluate(value, threshold):
    if value is None:
        return "Dato assente"
    if not threshold or not any(threshold.get(key) is not None for key in ("attention", "prealarm", "alarm")):
        return "Soglia assente"
    ordered = (("Allarme", threshold.get("alarm")), ("Preallarme", threshold.get("prealarm")), ("Attenzione", threshold.get("attention")))
    for label, limit in ordered:
        if limit is None:
            continue
        if threshold.get("direction") == "below" and value <= limit:
            return label
        if threshold.get("direction") != "below" and value >= limit:
            return label
    return "Regolare"


def apply_thresholds(stations, thresholds, source):
    counts = {"Regolare": 0, "Attenzione": 0, "Preallarme": 0, "Allarme": 0, "Soglia assente": 0, "Dato assente": 0}
    for station in stations:
        threshold = station.get("threshold") or next((item for item in thresholds if _matches(station, item, source)), None)
        station["threshold"] = threshold or {}
        station["criticality"] = evaluate((station.get("latest") or {}).get("value"), threshold)
        counts[station["criticality"]] += 1
    return counts
