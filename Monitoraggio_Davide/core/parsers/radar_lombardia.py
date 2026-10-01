import re
from datetime import datetime, timezone
from typing import Dict, List


RADAR_FILE_RE = re.compile(r"CMP(?P<stamp>\d{10})\.MAX\.tif\.gz")


def radar_products(index_payload: bytes) -> List[Dict[str, object]]:
    """Estrae e ordina i prodotti CMP pubblicati nell'indice ARPA Lombardia."""
    text = index_payload.decode("utf-8", errors="replace")
    products = {}
    for match in RADAR_FILE_RE.finditer(text):
        filename = match.group(0)
        stamp = match.group("stamp")
        observed = datetime.strptime(stamp, "%y%m%d%H%M").replace(tzinfo=timezone.utc)
        products[filename] = {
            "filename": filename,
            "observed_at": observed.isoformat().replace("+00:00", "Z"),
            "observed_at_utc": observed.strftime("%d/%m/%Y %H:%M UTC"),
        }
    return sorted(products.values(), key=lambda item: item["filename"])


def latest_radar_product(index_payload: bytes) -> Dict[str, object]:
    products = radar_products(index_payload)
    if not products:
        raise ValueError("Nessun GeoTIFF radar CMP trovato nell'indice ARPA Lombardia")
    return products[-1]
