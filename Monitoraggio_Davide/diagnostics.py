import time

from qgis.PyQt.QtCore import QObject, pyqtSignal

from .connectors.http import NetworkRequestError, get_bytes


class DiagnosticWorker(QObject):
    progress = pyqtSignal(int, str)
    row = pyqtSignal(dict)
    finished = pyqtSignal(dict)

    def __init__(self, sources, timeout=12):
        super().__init__()
        self.sources = list(sources)
        self.timeout = timeout

    def run(self):
        ok = warnings = errors = 0
        total = max(1, len(self.sources))
        for index, source in enumerate(self.sources, 1):
            started = time.monotonic()
            status, detail = "OK", "Raggiungibile"
            code = ""
            try:
                get_bytes(source["url"])
                ok += 1
            except NetworkRequestError as exc:
                code = str(exc.status_code or "")
                if source.get("name", "").startswith("AINEVA") and exc.status_code == 404:
                    status, detail = "AVVISO", "Nessun bollettino corrente: possibile periodo fuori stagione"
                    warnings += 1
                elif exc.status_code in (401, 403):
                    status, detail = "AVVISO", "Servizio attivo: autenticazione richiesta"
                    warnings += 1
                elif not source.get("live_data", True):
                    status, detail = "AVVISO", "Fonte catalogata, non disponibile come feed live: %s" % exc
                    warnings += 1
                else:
                    status, detail = "ERRORE", str(exc)
                    errors += 1
            except Exception as exc:
                if not source.get("live_data", True):
                    status, detail = "AVVISO", "Fonte catalogata, non disponibile come feed live: %s: %s" % (type(exc).__name__, exc)
                    warnings += 1
                else:
                    status, detail = "ERRORE", "%s: %s" % (type(exc).__name__, exc)
                    errors += 1
            elapsed = int((time.monotonic() - started) * 1000)
            self.row.emit({"source": source["name"], "group": source["group"], "status": status, "http": code, "ms": elapsed, "detail": detail})
            self.progress.emit(int(index * 100 / total), "Verifica %s" % source["name"])
        self.finished.emit({"ok": ok, "warnings": warnings, "errors": errors})
