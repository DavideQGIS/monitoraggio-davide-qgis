import urllib.request
import xml.etree.ElementTree as ET

from qgis.PyQt.QtCore import QObject, pyqtSignal


ARPAV_XML = "https://www.arpa.veneto.it/api/risorse/data-meteo/xml/Ultime48ore.xml"


def _number(value):
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


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
            request = urllib.request.Request(ARPAV_XML, headers={"User-Agent": "Monitoraggio-Davide/0.4"})
            with urllib.request.urlopen(request, timeout=60) as response:
                root = ET.fromstring(response.read())
            code = {"Padova": "PD", "Belluno": "BL", "Rovigo": "RO", "Treviso": "TV", "Venezia": "VE", "Verona": "VR", "Vicenza": "VI"}.get(self.province)
            stations = []
            nodes = root.findall(".//STAZIONE")
            for index, node in enumerate(nodes, 1):
                province = (node.findtext("PROVINCIA") or "").strip().upper()
                if code and province != code:
                    continue
                base = {
                    "station_id": node.findtext("IDSTAZ") or "",
                    "name": node.findtext("NOME") or "",
                    "municipality": node.findtext("COMUNE") or "",
                    "province": province,
                    "elevation": _number(node.findtext("QUOTA")),
                    "longitude": _number(node.findtext("X")),
                    "latitude": _number(node.findtext("Y")),
                    "source": "ARPAV",
                }
                for sensor in node.findall("SENSORE"):
                    samples = sensor.findall("DATI")
                    latest_node = samples[-1] if samples else None
                    value = _number(latest_node.findtext("VM")) if latest_node is not None else None
                    observed = latest_node.attrib.get("ISTANTE", "") if latest_node is not None else ""
                    item = dict(base)
                    item.update({
                        "sensor_id": sensor.findtext("ID") or "",
                        "sensor_type": sensor.findtext("PARAMNM") or sensor.findtext("TYPE") or "",
                        "unit": sensor.findtext("UNITNM") or "",
                        "latest": {"value": value, "observed_at": observed, "state": "automatico non validato"},
                    })
                    stations.append(item)
                if index % 15 == 0:
                    self.progress.emit(20 + int(70 * index / max(1, len(nodes))), "Lettura ARPAV %d/%d" % (index, len(nodes)))
            measurements = sum(1 for item in stations if (item.get("latest") or {}).get("value") is not None)
            self.progress.emit(100, "ARPAV completato")
            self.finished.emit(stations, {"stations": len(stations), "sensors": len(stations), "measurements": measurements})
        except Exception as exc:
            self.failed.emit("%s: %s" % (type(exc).__name__, exc))
