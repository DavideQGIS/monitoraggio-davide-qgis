from typing import Dict, Optional

from qgis.PyQt.QtCore import QByteArray, QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsBlockingNetworkRequest, QgsFeedback


class NetworkRequestError(RuntimeError):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _no_error_value():
    if hasattr(QgsBlockingNetworkRequest, "NoError"):
        return QgsBlockingNetworkRequest.NoError
    return QgsBlockingNetworkRequest.ErrorCode.NoError


def _http_status_attribute():
    if hasattr(QNetworkRequest, "HttpStatusCodeAttribute"):
        return QNetworkRequest.HttpStatusCodeAttribute
    return QNetworkRequest.Attribute.HttpStatusCodeAttribute


def get_bytes(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    force_refresh: bool = True,
    feedback: Optional[QgsFeedback] = None,
) -> bytes:
    """GET sincrono thread-safe che rispetta proxy e autenticazione di QGIS."""
    return _request_bytes("GET", url, headers, force_refresh, feedback)


def post_bytes(
    url: str,
    data: bytes = b"",
    headers: Optional[Dict[str, str]] = None,
    force_refresh: bool = True,
    feedback: Optional[QgsFeedback] = None,
) -> bytes:
    """POST sincrono thread-safe tramite il gestore di rete di QGIS."""
    return _request_bytes("POST", url, headers, force_refresh, feedback, data)


def _request_bytes(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]],
    force_refresh: bool,
    feedback: Optional[QgsFeedback],
    data: bytes = b"",
) -> bytes:
    request = QNetworkRequest(QUrl(url))
    request_headers = {"Accept": "*/*", "User-Agent": "Monitoraggio-Davide/0.7"}
    request_headers.update(headers or {})
    for name, value in request_headers.items():
        request.setRawHeader(name.encode("ascii"), value.encode("utf-8"))

    blocking = QgsBlockingNetworkRequest()
    if method == "POST":
        error_code = blocking.post(request, QByteArray(data), force_refresh, feedback)
    else:
        error_code = blocking.get(request, force_refresh, feedback)
    reply = blocking.reply()
    status_code = int(reply.attribute(_http_status_attribute()) or 0)
    if error_code != _no_error_value():
        raise NetworkRequestError(blocking.errorMessage() or "Errore di rete QGIS", status_code)

    if reply.error():
        raise NetworkRequestError(reply.errorString() or "Risposta di rete QGIS non valida", status_code)
    return bytes(reply.content())
