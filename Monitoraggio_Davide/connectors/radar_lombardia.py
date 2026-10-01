import gzip
import os
import tempfile

from qgis.PyQt.QtCore import QObject, pyqtSignal

from ..core.parsers.radar_lombardia import latest_radar_product
from .http import get_bytes


RADAR_INDEX = "https://radarlive.arpalombardia.it/CMP/"


class RadarLombardiaWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.progress.emit(10, "Leggo indice radar ARPA Lombardia")
            index_payload = get_bytes(RADAR_INDEX, {"Accept": "text/html"})
            product = latest_radar_product(index_payload)
            self.progress.emit(45, "Scarico %s" % product["filename"])
            compressed = get_bytes(RADAR_INDEX + product["filename"], {"Accept": "application/gzip,application/octet-stream"})
            raster_bytes = gzip.decompress(compressed)

            cache_dir = os.path.join(tempfile.gettempdir(), "Monitoraggio_Davide", "radar")
            os.makedirs(cache_dir, exist_ok=True)
            tif_name = product["filename"][:-3]
            tif_path = os.path.join(cache_dir, tif_name)
            with open(tif_path, "wb") as stream:
                stream.write(raster_bytes)

            for old_name in os.listdir(cache_dir):
                if old_name.startswith("CMP") and old_name.endswith(".MAX.tif") and old_name != tif_name:
                    try:
                        os.remove(os.path.join(cache_dir, old_name))
                    except OSError:
                        pass

            product.update({"path": tif_path, "compressed_bytes": len(compressed), "raster_bytes": len(raster_bytes)})
            self.progress.emit(100, "Radar ARPA Lombardia aggiornato")
            self.finished.emit(product)
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
