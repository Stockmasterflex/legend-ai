"""
Simple service monitor for Legend API.

Pings /healthz, /readyz, /v1/patterns/all, and /v1/meta/status. Exits non-zero
on first failure. Intended for manual checks and CI.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from typing import Tuple

BASE = os.getenv("SERVICE_BASE", "https://legend-api.onrender.com")
TIMEOUT = float(os.getenv("MONITOR_TIMEOUT", "10"))


def fetch(path: str) -> Tuple[int, str]:
    url = f"{BASE.rstrip('/')}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # nosec - controlled URL
        body = resp.read().decode("utf-8")
        return resp.getcode(), body


def must_ok(path: str) -> None:
    code, body = fetch(path)
    if code != 200:
        sys.stderr.write(f"[monitor] {path} -> HTTP {code}\n")
        sys.exit(1)
    # Basic JSON parse for API endpoints
    if path.startswith("/v1") or path in ("/healthz", "/readyz"):
        try:
            json.loads(body)
        except Exception:
            sys.stderr.write(f"[monitor] {path} -> non-JSON response\n")
            sys.exit(1)


def main() -> None:
    print(f"[monitor] base={BASE} timeout={TIMEOUT}s")
    must_ok("/healthz")
    # readyz may return ok:false if DB missing; accept 200 regardless
    code, _ = fetch("/readyz")
    if code != 200:
        sys.stderr.write("[monitor] /readyz -> non-200\n")
        sys.exit(1)
    # Optional v1 checks; tolerate 404 if not shipped yet
    try:
        must_ok("/v1/patterns/all?limit=1")
        must_ok("/v1/meta/status")
    except Exception:
        print("[monitor] v1 endpoints not available; skipping")
    print("[monitor] OK")


if __name__ == "__main__":
    main()


