from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class SourceDefinition:
    """Descrizione stabile di una fonte interrogata dal plugin."""

    key: str
    name: str
    group: str
    area: str
    url: str
    live_data: bool = True
    notes: str = ""

    def as_catalog_row(self) -> Dict[str, object]:
        row = asdict(self)
        row.pop("key")
        return row


@dataclass
class Observation:
    """Misura normalizzata prodotta da qualsiasi connettore."""

    source_key: str
    station_id: str
    sensor_id: str
    sensor_type: str
    observed_at: str
    value: Optional[float]
    unit: str = ""
    quality: str = ""

