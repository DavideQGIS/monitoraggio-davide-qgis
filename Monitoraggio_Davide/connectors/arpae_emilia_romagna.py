import json
import datetime
import time

from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..core.parsers.arpae import number, parse_hydro_payload
from .http import get_bytes


ARPAE_HYDRO = "https://allertameteo.regione.emilia-romagna.it/o/api/allerta/get-sensor-values-no-time?variabile=254,0,0/1,-,-,-/B13215"
ARPAE_HYDRO_TIME = "https://allertameteo.regione.emilia-romagna.it/o/api/allerta/get-sensor-values?variabile=254,0,0/1,-,-,-/B13215&time="
class ArpaeEmiliaRomagnaWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(10, "Scarico idrometri ARPAE Emilia-Romagna")
            initial = json.loads(get_bytes(ARPAE_HYDRO).decode("utf-8"))
            offset = number(initial[0].get("time")) if initial and isinstance(initial[0], dict) else 0
            instant_ms = int(time.time() * 1000 + (offset or 0))
            payload = json.loads(get_bytes(ARPAE_HYDRO_TIME + str(instant_ms)).decode("utf-8"))
            observed_at = datetime.datetime.fromtimestamp(instant_ms / 1000.0).astimezone().isoformat(timespec="minutes")
            stations = parse_hydro_payload(payload, observed_at)
            measurements = sum(1 for item in stations if (item.get("latest") or {}).get("value") is not None)
            self.progress.emit(100, "ARPAE Emilia-Romagna completato")
            self.finished.emit(stations, {"stations": len(stations), "sensors": len(stations), "measurements": measurements})
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
