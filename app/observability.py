"""
Observability helpers for Legend AI API.

Provides JSON logging setup and optional Sentry integration. Import and call
`setup_json_logging()` early in process startup, and wrap FastAPI app with
`setup_sentry(app)` to enable Sentry when SENTRY_DSN is provided.

Additionally exposes a small `send_alert` helper that posts to a webhook when
`ALERT_WEBHOOK_URL` is set. The function fails open and returns False if the
post fails. This is used by reliability tests.
"""

import json
import logging
import os
import time
from typing import Any, Dict

try:  # optional dependency for webhook posting in tests
    import httpx  # type: ignore
except Exception:  # pragma: no cover - allow tests to monkeypatch
    httpx = None  # type: ignore


def setup_json_logging() -> None:
    """Configure root logger to emit JSON-formatted logs to stdout."""

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
            payload: Dict[str, Any] = {
                "ts": time.time(),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
            }
            if record.exc_info:
                payload["exc_info"] = self.formatException(record.exc_info)
            return json.dumps(payload)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def setup_sentry(app):
    """Wrap ASGI app with Sentry middleware if SENTRY_DSN is set.

    Returns the original app if DSN is missing.
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return app
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
    return SentryAsgiMiddleware(app)


def send_alert(message: str, *, extras: Dict[str, Any] | None = None) -> bool:
    """Send a lightweight alert to a webhook if configured.

    Returns True if the post was attempted and succeeded (HTTP 2xx), otherwise
    returns False. Never raises.
    """
    url = os.getenv("ALERT_WEBHOOK_URL")
    if not url or httpx is None:
        return False
    try:
        payload: Dict[str, Any] = {"text": f"[Legend AI] {message}"}
        if extras:
            payload["extras"] = extras
        resp = httpx.post(url, json=payload, timeout=2.5)  # type: ignore[operator]
        return 200 <= int(getattr(resp, "status_code", 0)) < 300
    except Exception:
        return False
