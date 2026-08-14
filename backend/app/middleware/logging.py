"""Logs applicatifs au format JSON, une ligne par requete.

Format JSON parce que les logs sont destines a etre lus par `jq` et tournes
par logrotate (cahier des charges section 13 - monitoring proportionne, pas de
Prometheus/Grafana a cette echelle).

Ce que ces logs ne contiennent JAMAIS : corps de requete, en-tetes
d'autorisation, cookies, parametres de requete. Un mot de passe ou un token ne
doit pas pouvoir se retrouver dans un fichier de log.
"""

import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

access_logger = logging.getLogger("sentinel_ops.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if isinstance(getattr(record, "extra_fields", None), dict):
            payload.update(record.extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        started = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        access_logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                }
            },
        )
        # Renvoye au client pour pouvoir relier un incident utilisateur a une
        # ligne de log precise.
        response.headers["X-Request-ID"] = request_id
        return response
