import json
import datetime
import time

from qgis.PyQt.QtCore import QObject, pyqtSignal

from .http import get_bytes


ARPAE_HYDRO = "https://allertameteo.regione.emilia-romagna.it/o/api/allerta/get-sensor-values-no-time?variabile=254,0,0/1,-,-,-/B13215"
ARPAE_HYDRO_TIME = "https://allertameteo.regione.emilia-romagna.it/o/api/allerta/get-sensor-values?variabile=254,0,0/1,-,-,-/B13215&time="
REFERENCE = "https://allertameteo.regione.emilia-romagna.it/livello-idrometrico"


def _number(value, zero_is_none=False):
    try:
        result = float(str(value).replace(",", "."))
        return None if zero_is_none and result == 0 else result
    except Exception:
        return None


class ArpaeEmiliaRomagnaWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(10, "Scarico idrometri ARPAE Emilia-Romagna")
            initial = json.loads(get_bytes(ARPAE_HYDRO).decode("utf-8"))
            offset = _number(initial[0].get("time")) if initial and isinstance(initial[0], dict) else 0
            instant_ms = int(time.time() * 1000 + (offset or 0))
            payload = json.loads(get_bytes(ARPAE_HYDRO_TIME + str(instant_ms)).decode("utf-8"))
            observed_at = datetime.datetime.fromtimestamp(instant_ms / 1000.0).astimezone().isoformat(timespec="minutes")
            stations = []
            for index, row in enumerate(payload, 1):
                sensor_id = str(row.get("idstazione", ""))
                if not sensor_id:
                    continue
                # Le coordinate del servizio sono gradi decimali moltiplicati per 100000.
                lon = _number(row.get("lon")); lat = _number(row.get("lat"))
                if lon is not None: lon /= 100000.0
                if lat is not None: lat /= 100000.0
                threshold = {
                    "source": "ARPAE Emilia-Romagna", "sensor_id": sensor_id,
                    "station_name": str(row.get("nomestaz", "")), "sensor_type": "Livello idrometrico",
                    "direction": "above", "attention": _number(row.get("soglia1"), True),
                    "prealarm": _number(row.get("soglia2"), True), "alarm": _number(row.get("soglia3"), True),
                    "unit": "m", "valid_from": "", "reference": REFERENCE,
                }
                stations.append({
                    "station_id": sensor_id, "sensor_id": sensor_id,
                    "name": str(row.get("nomestaz", "")), "municipality": "", "province": "ER",
                    "sensor_type": "Livello idrometrico", "unit": "m", "elevation": None,
                    "longitude": lon, "latitude": lat, "source": "ARPAE Emilia-Romagna",
                    "latest": {"value": _number(row.get("value")), "observed_at": observed_at, "state": "precedente" if row.get("precedente") == "S" else "corrente"},
                    "threshold": threshold,
                })
                if index % 40 == 0:
                    self.progress.emit(10 + int(85 * index / max(1, len(payload))), "Idrometri ARPAE %d/%d" % (index, len(payload)))
            measurements = sum(1 for item in stations if (item.get("latest") or {}).get("value") is not None)
            self.progress.emit(100, "ARPAE Emilia-Romagna completato")
            self.finished.emit(stations, {"stations": len(stations), "sensors": len(stations), "measurements": measurements})
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
