import concurrent.futures
import json
import urllib.request
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import QObject, pyqtSignal


LIST_URL = "https://dati.meteotrentino.it/service.asmx/listaStazioniGeoJson"
DATA_URL = "https://dati.meteotrentino.it/service.asmx/ultimiDatiStazione?codice="


def _number(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def _fetch(url, data=None, timeout=35):
    request = urllib.request.Request(url, data=data, headers={"User-Agent": "Monitoraggio-Davide/0.4"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _latest_station(feature):
    props = feature.get("properties") or {}
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    code = str(props.get("codice", ""))
    if not code or len(coords) < 2:
        return []
    root = ET.fromstring(_fetch(DATA_URL + code))
    for node in root.iter():
        if "}" in node.tag:
            node.tag = node.tag.split("}", 1)[1]
    base = {
        "station_id": code, "name": str(props.get("nome", "")), "municipality": "",
        "province": "TN", "elevation": _number(props.get("quota")),
        "longitude": _number(coords[0]), "latitude": _number(coords[1]), "source": "Meteotrentino",
    }
    result = []
    series = (("Temperatura aria", "°C", ".//temperatura_aria", "temperatura"), ("Precipitazione", "mm", ".//precipitazione", "pioggia"))
    for label, unit, path, value_tag in series:
        samples = root.findall(path)
        if not samples:
            continue
        last = samples[-1]
        item = dict(base)
        item.update({"sensor_id": code + "-" + value_tag, "sensor_type": label, "unit": unit,
                     "latest": {"value": _number(last.findtext(value_tag)), "observed_at": last.findtext("data") or "", "state": "automatico"}})
        result.append(item)
    return result


class MeteotrentinoWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(10, "Scarico anagrafica Meteotrentino")
            payload = json.loads(_fetch(LIST_URL, data=b"").decode("utf-8"))
            active = [feature for feature in payload.get("features", []) if not str((feature.get("properties") or {}).get("fine", "")).strip()]
            stations = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                futures = [pool.submit(_latest_station, feature) for feature in active]
                for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
                    try:
                        stations.extend(future.result())
                    except Exception:
                        pass
                    if index % 10 == 0:
                        self.progress.emit(15 + int(80 * index / max(1, len(futures))), "Meteotrentino %d/%d" % (index, len(futures)))
            measurements = sum(1 for item in stations if (item.get("latest") or {}).get("value") is not None)
            self.progress.emit(100, "Meteotrentino completato")
            self.finished.emit(stations, {"stations": len(stations), "sensors": len(stations), "measurements": measurements})
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
