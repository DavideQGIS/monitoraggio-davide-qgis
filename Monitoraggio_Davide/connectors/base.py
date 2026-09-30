from abc import ABC, abstractmethod
from typing import Iterable

from ..core.models import Observation, SourceDefinition


class Connector(ABC):
    """Contratto comune dei connettori della serie 0.7.x."""

    source: SourceDefinition

    @abstractmethod
    def fetch(self) -> Iterable[Observation]:
        """Restituisce osservazioni normalizzate senza modificare la mappa."""

