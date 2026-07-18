"""Risk-event detection from crypto news RSS + keywords."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from sentiment.labels import (
    headline_key,
    keyword_match,
    parse_entry_time,
    risk_level_label,
)
from sentiment.news_sentiment import NEWS_FEEDS, _all_keywords

analyzer = SentimentIntensityAnalyzer()

# Critical vs elevated risk keywords
CRITICAL_RISK_KEYWORDS = [
    "hack", "hacked", "exploit", "breach", "stolen", "theft",
    "rug pull", "exit scam", "insolvent", "bankruptcy",
]
HIGH_RISK_KEYWORDS = CRITICAL_RISK_KEYWORDS + [
    "scam", "fraud", "phishing",
    "lawsuit", "ban", "banned", "illegal", "crackdown",
    "freeze", "suspended", "delisted",
    "crash", "collapse", "liquidation", "contagion",
    "sec charges", "emergency",
]

# Keep "sec" only as whole word via keyword_match word boundaries


def analyze_risk_from_articles(
    symbol: str,
    articles: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    coin_kws = _all_keywords(symbol)
    seen = set()
    scores = []
    events = []
    keywords_found = set()

    for art in articles:
        title = (art.get("title") or "").strip()
        if not title:
            continue
        key = headline_key(title)
        if key in seen:
            continue
        seen.add(key)

        summary = art.get("summary") or ""
        text = f"{title} {summary}"
        if not keyword_match(text, coin_kws):
            continue

        risk_hits = keyword_match(text, HIGH_RISK_KEYWORDS)
        if not risk_hits:
            continue

        pub = art.get("published_at")
        if isinstance(pub, str):
            try:
                pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except Exception:
                pub = None
        if pub is not None:
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub > now and (pub - now).total_seconds() > 300:
                continue
            age_h = (now - pub).total_seconds() / 3600.0
            if age_h > 72:
                continue

        vader = float(analyzer.polarity_scores(title).get("compound", 0.0))
        crit = keyword_match(text, CRITICAL_RISK_KEYWORDS)
        # Base from keyword severity + negative tone
        base = 0.55 if crit else 0.35
        tone = max(0.0, -vader)  # negative vader increases risk
        amp = 0.5 + 0.5 * min(len(risk_hits) / 3.0, 1.0)
        risk_score = min(1.0, (base + 0.45 * tone) * amp)
        if crit:
            risk_score = max(risk_score, 0.65)

        scores.append(risk_score)
        keywords_found.update(risk_hits)
        events.append(
            {
                "headline": title[:120],
                "source": art.get("source") or "unknown",
                "keywords": risk_hits[:4],
                "risk_score": round(risk_score, 3),
                "published_at": pub.isoformat() if isinstance(pub, datetime) else None,
            }
        )

    if scores:
        risk_score = max(scores)  # worst event drives guard
        risk_score = max(0.0, min(1.0, float(risk_score)))
    else:
        risk_score = 0.0

    is_high = risk_score >= 0.5
    level = risk_level_label(risk_score, is_high)
    return {
        "symbol": symbol,
        "risk_score": round(risk_score, 3),
        "risk_level": level,
        "is_high_risk": is_high,
        "risk_events": [e["headline"] for e in events[:5]],
        "risk_event_details": events[:5],
        "detected_risk_keywords": sorted(keywords_found),
        "fallback_used": False,
    }


def analyze_risk_sentiment(
    symbol: str = "BTCUSDT",
    articles: Optional[List[Dict[str, Any]]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    t0 = time.time()
    try:
        if articles is None:
            from sentiment.news_sentiment import fetch_rss_articles

            articles = fetch_rss_articles()
        result = analyze_risk_from_articles(symbol, articles or [])
        result["api_latency_ms"] = int((time.time() - t0) * 1000)
        if not articles:
            result["fallback_used"] = True
        if verbose:
            print(
                f"  {symbol} risk={result['risk_score']:.3f} "
                f"level={result['risk_level']} high={result['is_high_risk']}"
            )
        return result
    except Exception as e:
        return {
            "symbol": symbol,
            "risk_score": 0.0,
            "risk_level": "Low",
            "is_high_risk": False,
            "risk_events": [],
            "risk_event_details": [],
            "detected_risk_keywords": [],
            "fallback_used": True,
            "error": str(e),
            "api_latency_ms": int((time.time() - t0) * 1000),
        }


def get_risk_sentiment(symbol: str = "BTCUSDT", verbose: bool = False) -> dict:
    """Realtime-compatible dict."""
    return analyze_risk_sentiment(symbol, verbose=verbose)
