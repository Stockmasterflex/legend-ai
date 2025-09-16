import logging
import os
from typing import Dict, Any, List

log = logging.getLogger("legend.sentiment")

def _fetch_news_newsapi(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    key = os.getenv("NEWSAPI_KEY")
    if not key:
        return []
    import requests, datetime
    q = f'"{symbol}"'
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": q,
        "language": "en",
        "pageSize": limit,
        "sortBy": "publishedAt",
        "from": (datetime.datetime.utcnow() - datetime.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "apiKey": key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        js = r.json()
        arts = js.get("articles", []) or []
        return [{"title": a.get("title"), "url": a.get("url")} for a in arts[:limit]]
    except Exception as e:
        log.warning("newsapi error: %s", e)
        return []

def _analyze_finbert(texts: List[str]) -> Dict[str, Any]:
    try:
        from transformers import pipeline
        model_name = "ProsusAI/finbert"
        clf = pipeline("text-classification", model=model_name, tokenizer=model_name, truncation=True, top_k=None)
        res = clf(texts[:5])
        scores = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
        for item in res:
            label = item[0]["label"].lower() if isinstance(item, list) else item["label"].lower()
            score = item[0]["score"] if isinstance(item, list) else item["score"]
            scores[label] = scores.get(label, 0.0) + float(score)
        label = max(scores, key=scores.get)
        total = sum(scores.values()) or 1.0
        return {"label": label, "score": scores[label]/total, "confidence": max(scores.values())}
    except Exception as e:
        log.info("finbert unavailable, returning neutral: %s", e)
        return {"label": "neutral", "score": 0.0, "confidence": 0.5}

def fetch_headlines_and_sentiment(symbol: str, limit: int = 5) -> Dict[str, Any]:
    heads = _fetch_news_newsapi(symbol, limit) if os.getenv("NEWSAPI_KEY") else []
    if not heads:
        return {"label": "neutral", "score": 0.0, "confidence": 0.5, "headlines": [], "is_sample": True}
    labels = _analyze_finbert([h["title"] for h in heads])
    labels["headlines"] = heads
    labels["is_sample"] = False
    return labels

