import json
import urllib.parse
import urllib.request

from qgis.PyQt.QtCore import QObject, pyqtSignal


STATIONS_API = "https://www.dati.lombardia.it/resource/nf78-nj6b.json"
MEASURES_API = "https://www.dati.lombardia.it/resource/647i-nhxk.json"


def _value(row, *names):
    lowered = {str(k).lower().replace("_", ""): v for k, v in row.items()}
    for name in names:
        key = name.lower().replace("_", "")
        if key in lowered and lowered[key] not in (None, ""):
            return lowered[key]
    return ""


def _float(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def normalize_station(row):
    location = row.get("location") or row.get("geocoded_column") or {}
    coordinates = location.get("coordinates") if isinstance(location, dict) else None
    lon = _float(_value(row, "lng", "lon", "longitudine", "longitude", "x"))
    lat = _float(_value(row, "lat", "latitudine", "latitude", "y"))
    if coordinates and len(coordinates) >= 2:
        lon = lon if lon is not None else _float(coordinates[0])
        lat = lat if lat is not None else _float(coordinates[1])
    return {
        "station_id": str(_value(row, "idstazione", "id_station", "stationid")),
        "sensor_id": str(_value(row, "idsensore", "id_sensor", "sensorid")),
        "name": str(_value(row, "nomestazione", "stazione", "name", "namestation")),
        "municipality": str(_value(row, "comune", "municipality")),
        "province": str(_value(row, "provincia", "province", "siglaprovincia")),
        "sensor_type": str(_value(row, "tipologia", "tiposensore", "sensore", "sensor_type")),
        "unit": str(_value(row, "unitamisura", "unit", "unita")),
        "elevation": _float(_value(row, "quota", "elevation", "altitudine")),
        "longitude": lon,
        "latitude": lat,
        "raw": row,
    }


def normalize_measure(row):
    return {
        "sensor_id": str(_value(row, "idsensore", "id_sensor", "sensorid")),
        "observed_at": str(_value(row, "data", "date", "datetime")),
        "value": _float(_value(row, "valore", "value")),
        "state": str(_value(row, "stato", "state")),
    }


def fetch_json(url, params=None, timeout=30):
    query = urllib.parse.urlencode(params or {}, safe=",()' ")
    full_url = url + ("?" + query if query else "")
    request = urllib.request.Request(full_url, headers={"Accept": "application/json", "User-Agent": "Monitoraggio-UTR/0.2"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def province_codes(province):
    return {"Brescia": ("BS", "BRESCIA"), "Padova": ("PD", "PADOVA"), "Trento": ("TN", "TRENTO")}.get(province, (province.upper(),))


class ArpaLombardiaWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    failed = pyqtSignal(str)

    def __init__(self, province="Brescia", station_limit=5000, measure_limit=50000):
        super().__init__()
        self.province = province
        self.station_limit = station_limit
        self.measure_limit = measure_limit

    def run(self):
        try:
            self.progress.emit(10, "Scarico anagrafica ARPA Lombardia")
            raw = fetch_json(STATIONS_API, {"$limit": self.station_limit})
            stations = [normalize_station(item) for item in raw]
            codes = province_codes(self.province)
            selected = [s for s in stations if not s["province"] or s["province"].strip().upper() in codes]
            if not selected:
                selected = [s for s in stations if self.province.upper() in (s["municipality"] + " " + s["name"]).upper()]
            sensor_ids = sorted({s["sensor_id"] for s in selected if s["sensor_id"]})
            self.progress.emit(45, "%d sensori trovati · scarico ultimi dati" % len(sensor_ids))
            latest = {}
            # Query a blocchi per evitare URL troppo lunghi e download dell'intero mese.
            for start in range(0, len(sensor_ids), 80):
                block = sensor_ids[start:start + 80]
                quoted = ",".join("'%s'" % value.replace("'", "") for value in block)
                measures = fetch_json(MEASURES_API, {
                    "$select": "idsensore,data,valore,stato",
                    "$where": "idsensore in(%s)" % quoted,
                    "$order": "data DESC",
                    "$limit": min(self.measure_limit, max(1000, len(block) * 20)),
                })
                for item in measures:
                    measure = normalize_measure(item)
                    sid = measure["sensor_id"]
                    if sid and sid not in latest:
                        latest[sid] = measure
                pct = 45 + int(45 * min(len(sensor_ids), start + len(block)) / max(1, len(sensor_ids)))
                self.progress.emit(pct, "Ultimi dati ARPA %d/%d" % (min(len(sensor_ids), start + len(block)), len(sensor_ids)))
            for station in selected:
                station["latest"] = latest.get(station["sensor_id"], {})
            self.progress.emit(100, "ARPA Lombardia completato")
            self.finished.emit(selected, {"stations": len(selected), "sensors": len(sensor_ids), "measurements": len(latest)})
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
