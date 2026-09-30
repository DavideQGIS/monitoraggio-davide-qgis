import datetime
import json
import urllib.parse
import urllib.request

from qgis.PyQt.QtCore import QObject, pyqtSignal


INGV_API = "https://webservices.ingv.it/fdsnws/event/1/query"


class IngvWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, days=7):
        super().__init__()
        self.days = days

    def run(self):
        try:
            self.progress.emit(15, "Scarico eventi sismici INGV")
            start = (datetime.datetime.utcnow() - datetime.timedelta(days=self.days)).strftime("%Y-%m-%d")
            params = urllib.parse.urlencode({
                "starttime": start, "format": "geojson",
                "minlatitude": 44.0, "maxlatitude": 47.7,
                "minlongitude": 8.0, "maxlongitude": 14.2,
            })
            request = urllib.request.Request(INGV_API + "?" + params, headers={"User-Agent": "Monitoraggio-Davide/0.4"})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
            events = []
            for feature in payload.get("features", []):
                props = feature.get("properties") or {}
                coords = (feature.get("geometry") or {}).get("coordinates") or []
                if len(coords) < 2:
                    continue
                events.append({
                    "event_id": str(props.get("eventId", "")), "time": str(props.get("time", "")),
                    "magnitude": props.get("mag"), "mag_type": str(props.get("magType", "")),
                    "place": str(props.get("place", "")), "longitude": coords[0], "latitude": coords[1],
                    "depth": coords[2] if len(coords) > 2 else None,
                })
            events.sort(key=lambda item: item["time"], reverse=True)
            self.progress.emit(100, "INGV completato")
            self.finished.emit(events)
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
