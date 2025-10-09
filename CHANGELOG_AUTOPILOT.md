## 2025-10-09

- Add retry_with_backoff utility in `app/data_fetcher.py` and tests.
- Add `send_alert` webhook helper in `app/observability.py` with tests.
- Cache `/api/market/indices` results for 60s via in-process cache; added tests.
- Upgraded dependencies for Python 3.13 compatibility (pydantic v2, pandas/numpy pins).
- Expanded pytest discovery to include `backend/tests/`.
- Lint/format/typecheck clean; all tests passing.
