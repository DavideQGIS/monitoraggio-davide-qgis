import datetime
import json
import urllib.parse

from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..core.parsers.ingv import parse_geojson
from .http import get_bytes


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
            payload = json.loads(get_bytes(INGV_API + "?" + params).decode("utf-8"))
            events = parse_geojson(payload)
            self.progress.emit(100, "INGV completato")
            self.finished.emit(events)
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
