from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..core.parsers.arpav import parse_arpav_xml
from .http import get_bytes


ARPAV_XML = "https://www.arpa.veneto.it/api/risorse/data-meteo/xml/Ultime48ore.xml"


class ArpavWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list, dict)
    failed = pyqtSignal(str)

    def __init__(self, province="Padova"):
        super().__init__()
        self.province = province

    def run(self):
        try:
            self.progress.emit(10, "Scarico rete idrometeorologica ARPAV")
            payload = get_bytes(ARPAV_XML, {"Accept": "application/xml,text/xml"})
            self.progress.emit(75, "Normalizzazione dati ARPAV")
            stations, summary = parse_arpav_xml(payload, self.province)
            self.progress.emit(100, "ARPAV completato")
            self.finished.emit(stations, summary)
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
