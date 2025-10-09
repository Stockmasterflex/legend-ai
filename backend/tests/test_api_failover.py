import os
import types
from typing import Any, Dict


def test_retry_with_backoff_retries_then_succeeds(monkeypatch):
    from app import data_fetcher as df

    calls = {"n": 0}

    def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    # Avoid actual sleeping during test
    monkeypatch.setattr(df, "time", types.SimpleNamespace(sleep=lambda s: None))

    result = df.retry_with_backoff(op, retries=3, backoff_base=0.01)
    assert result == "ok"
    assert calls["n"] == 3


def test_send_alert_posts_when_webhook_set(monkeypatch):
    os.environ["ALERT_WEBHOOK_URL"] = "https://example.com/hook"

    sent: Dict[str, Any] = {}

    class DummyResp:
        status_code = 200

    def fake_post(url: str, json: Dict[str, Any], timeout: float):
        sent["url"] = url
        sent["json"] = json
        sent["timeout"] = timeout
        return DummyResp()

    from app import observability as obs

    monkeypatch.setattr(obs, "httpx", types.SimpleNamespace(post=fake_post))

    ok = obs.send_alert("provider error", extras={"area": "provider", "code": 429})
    assert ok is True
    assert sent["url"].endswith("/hook")
    assert sent["json"]["text"].startswith("[Legend AI]")



def test_cache_helpers_roundtrip(monkeypatch):
    from app import cache

    store: Dict[str, str] = {}

    class FakeClient:
        def setex(self, key: str, ttl: int, value: str) -> None:
            store[key] = value

        def get(self, key: str):
            return store.get(key)

    monkeypatch.setattr(cache, "_client", FakeClient())

    payload = {"a": 1, "b": "x"}
    cache.cache_set("k1", payload, ttl=5)
    out = cache.cache_get("k1")
    assert out == payload
