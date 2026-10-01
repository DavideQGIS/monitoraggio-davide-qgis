from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..core.parsers.aineva import parse_caaml_bulletin
from .http import NetworkRequestError, get_bytes


AINEVA_CAAML = "https://bollettini.aineva.it/albina_files/latest/it.xml"


class AinevaWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(20, "Scarico bollettino AINEVA")
            payload = get_bytes(AINEVA_CAAML, headers={"Accept": "application/xml,text/xml"})
            bulletin = parse_caaml_bulletin(payload)
            self.progress.emit(100, "Bollettino AINEVA completato")
            self.finished.emit(bulletin)
        except NetworkRequestError as exc:
            if exc.status_code == 404:
                self.finished.emit({
                    "bulletin_id": "", "published_at": "", "valid_from": "", "valid_to": "",
                    "danger_levels": [], "max_danger": None, "problems": [], "regions": [],
                })
            else:
                self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
