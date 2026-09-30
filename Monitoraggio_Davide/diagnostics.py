import socket
import time
import urllib.error
import urllib.request

from qgis.PyQt.QtCore import QObject, pyqtSignal


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
                req = urllib.request.Request(source["url"], headers={"User-Agent": "Monitoraggio-UTR/0.1"})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    code = str(getattr(response, "status", ""))
                    response.read(256)
                ok += 1
            except urllib.error.HTTPError as exc:
                code = str(exc.code)
                if exc.code in (401, 403):
                    status, detail = "AVVISO", "Servizio attivo: autenticazione richiesta"
                    warnings += 1
                else:
                    status, detail = "ERRORE", str(exc)
                    errors += 1
            except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
                status, detail = "ERRORE", str(exc)
                errors += 1
            except Exception as exc:
                status, detail = "ERRORE", "%s: %s" % (type(exc).__name__, exc)
                errors += 1
            elapsed = int((time.monotonic() - started) * 1000)
            self.row.emit({"source": source["name"], "group": source["group"], "status": status, "http": code, "ms": elapsed, "detail": detail})
            self.progress.emit(int(index * 100 / total), "Verifica %s" % source["name"])
        self.finished.emit({"ok": ok, "warnings": warnings, "errors": errors})
