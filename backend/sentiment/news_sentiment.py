"""
News sentiment via RSS + VADER.

Returns structured results for live testing and realtime predict.
Backward compatible: get_news_sentiment() still returns a float in [-1, 1].
"""
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
    news_sentiment_label,
    parse_entry_time,
)

analyzer = SentimentIntensityAnalyzer()

# Primary keywords get stronger weight; avoid ultra-short ambiguous tokens alone.
COIN_CONFIG = {
    "BTCUSDT": {
        "primary": ["bitcoin", "btc"],
        "secondary": ["bitcoin price", "bitcoin market", "btc etf"],
    },
    "ETHUSDT": {
        "primary": ["ethereum", "ether", "eth"],
        "secondary": ["ethereum etf", "eth etf"],
    },
    "SOLUSDT": {
        "primary": ["solana"],
        "secondary": ["sol"],
    },
}

NEWS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
]

# CoinGecko /news API is Pro-only; we also pull their free curated homepage feed.
COINGECKO_HOME = "https://www.coingecko.com/"
COINGECKO_API_NEWS = "https://api.coingecko.com/api/v3/news"
_CG_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

MAX_AGE_HOURS = 48.0
STALE_FLOOR_WEIGHT = 0.05

# Light crypto-domain nudge on top of VADER (clamped later)
_BULL_TERMS = [
    "rally", "surge", "surges", "record", "inflow", "inflows", "adoption",
    "bullish", "soar", "soars", "gains", "breakthrough", "all-time high",
    "accumulat", "upgrade", "growth", "grows", "demand rises",
]
_BEAR_TERMS = [
    "drop", "drops", "crash", "outflow", "outflows", "hack", "exploit",
    "ban", "decline", "declines", "selloff", "sell-off", "bearish",
    "liquidation", "collapse", "fraud", "lawsuit", "instability",
]


def _domain_nudge(title: str) -> float:
    t = title.lower()
    bull = sum(1 for w in _BULL_TERMS if w in t)
    bear = sum(1 for w in _BEAR_TERMS if w in t)
    return max(-0.25, min(0.25, 0.08 * bull - 0.08 * bear))


def _all_keywords(symbol: str) -> List[str]:
    cfg = COIN_CONFIG.get(symbol, {})
    keys = list(cfg.get("primary", [])) + list(cfg.get("secondary", []))
    seen = set()
    out = []
    for k in keys:
        k2 = k.strip()
        if k2 and k2 not in seen:
            seen.add(k2)
            out.append(k2)
    return out


def _primary_keywords(symbol: str) -> List[str]:
    cfg = COIN_CONFIG.get(symbol, {})
    return list(cfg.get("primary", []))


def _coin_relevance_weight(text: str, symbol: str) -> float:
    """
    Stronger weight when this coin is clearly the subject.
    Cross-coin headlines (many other coins named) get reduced weight.
    """
    prim = keyword_match(text, _primary_keywords(symbol))
    all_hits = keyword_match(text, _all_keywords(symbol))
    if not all_hits:
        return 0.0
    weight = 2.0 if prim else 1.0

    # Penalize if other major coins dominate
    others = {
        "BTCUSDT": ["bitcoin", "btc"],
        "ETHUSDT": ["ethereum", "ether", "eth"],
        "SOLUSDT": ["solana"],
    }
    other_hits = 0
    for sym, kws in others.items():
        if sym == symbol:
            continue
        if keyword_match(text, kws):
            other_hits += 1
    if other_hits >= 2 and not prim:
        weight *= 0.35
    elif other_hits >= 1 and not prim:
        weight *= 0.55
    return weight


def score_headlines(
    articles: List[Dict[str, Any]],
    symbol: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Score a list of article dicts (for live OR synthetic scenario tests).

    Each article: title, summary?, source?, published_at? (datetime|None), link?
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    seen = set()
    used = []
    total_w = 0.0
    total_ws = 0.0
    rejected_future = 0
    rejected_stale = 0
    rejected_dup = 0
    rejected_irrelevant = 0

    for art in articles:
        title = (art.get("title") or "").strip()
        if not title:
            continue
        summary = (art.get("summary") or "").strip()
        text = f"{title} {summary}"
        key = headline_key(title)
        if key in seen:
            rejected_dup += 1
            continue
        seen.add(key)

        if not keyword_match(text, _all_keywords(symbol)):
            rejected_irrelevant += 1
            continue

        pub = art.get("published_at")
        age_hours = None
        recency = 0.5
        if pub is not None:
            if isinstance(pub, str):
                try:
                    pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                except Exception:
                    pub = None
            if pub is not None:
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                # Future-dated rejected
                if pub > now.replace(microsecond=0) and (pub - now).total_seconds() > 300:
                    rejected_future += 1
                    continue
                age_hours = (now - pub).total_seconds() / 3600.0
                if age_hours > MAX_AGE_HOURS:
                    rejected_stale += 1
                    continue
                recency = max(STALE_FLOOR_WEIGHT, 1.0 - (age_hours / 24.0))
                recency = min(1.0, recency)

        vader = float(analyzer.polarity_scores(title).get("compound", 0.0))
        vader = max(-1.0, min(1.0, vader + _domain_nudge(title)))
        coin_w = _coin_relevance_weight(text, symbol)
        if coin_w <= 0:
            rejected_irrelevant += 1
            continue
        weight = coin_w * recency
        if weight <= 0:
            continue
        contrib = vader * weight
        total_w += weight
        total_ws += contrib
        used.append(
            {
                "title": title,
                "source": art.get("source") or "unknown",
                "link": art.get("link"),
                "published_at": pub.isoformat() if isinstance(pub, datetime) else None,
                "age_hours": round(age_hours, 2) if age_hours is not None else None,
                "vader_compound": round(vader, 4),
                "coin_relevance_weight": round(coin_w, 3),
                "recency_weight": round(recency, 3),
                "weight": round(weight, 4),
                "weighted_contribution": round(contrib, 4),
            }
        )

    if total_w > 0:
        score = max(-1.0, min(1.0, total_ws / total_w))
    else:
        score = 0.0

    score = round(float(score), 3)
    return {
        "symbol": symbol,
        "news_sentiment_score": score,
        "news_sentiment_label": news_sentiment_label(score),
        "articles_fetched": len(articles),
        "articles_unique_used": len(used),
        "articles": used,
        "rejected_duplicate": rejected_dup,
        "rejected_future": rejected_future,
        "rejected_stale": rejected_stale,
        "rejected_irrelevant": rejected_irrelevant,
        "fallback_used": False,
    }


def fetch_coingecko_articles(timeout: float = 12.0) -> List[Dict[str, Any]]:
    """
    CoinGecko-curated headlines, merged into the same news pool as RSS.

    Prefer official /news API when COINGECKO_API_KEY is set (Pro/Analyst).
    Otherwise scrape the free homepage "Latest Crypto News" strip.
    """
    import os
    import re
    from html import unescape

    import requests

    articles: List[Dict[str, Any]] = []
    api_key = (os.environ.get("COINGECKO_API_KEY") or "").strip()

    if api_key:
        try:
            resp = requests.get(
                COINGECKO_API_NEWS,
                params={"page": 1, "per_page": 20, "language": "en", "type": "news"},
                headers={
                    "User-Agent": _CG_UA,
                    "x-cg-pro-api-key": api_key,
                    "x-cg-demo-api-key": api_key,
                },
                timeout=timeout,
            )
            if resp.ok:
                payload = resp.json()
                rows = payload if isinstance(payload, list) else (
                    payload.get("data") or payload.get("news") or []
                )
                for row in rows:
                    title = (row.get("title") or "").strip()
                    if not title:
                        continue
                    pub = row.get("posted_at") or row.get("updated_at")
                    published_at = None
                    if isinstance(pub, str):
                        try:
                            published_at = datetime.fromisoformat(
                                pub.replace("Z", "+00:00")
                            )
                        except Exception:
                            published_at = None
                    articles.append(
                        {
                            "title": title,
                            "summary": (row.get("description") or "")[:500],
                            "source": "coingecko.com",
                            "link": row.get("url") or row.get("link"),
                            "published_at": published_at,
                        }
                    )
                if articles:
                    return articles
        except Exception:
            pass

    # Free fallback: curated strip on CoinGecko homepage
    try:
        resp = requests.get(
            COINGECKO_HOME,
            headers={"User-Agent": _CG_UA, "Accept-Language": "en-US,en;q=0.9"},
            timeout=timeout,
        )
        resp.raise_for_status()
        html = resp.content.decode("utf-8", errors="replace")
        idx = html.lower().find("latest crypto news")
        chunk = html[idx : idx + 40000] if idx >= 0 else html
        pairs = re.findall(
            r'href="(https://(?!www\.coingecko\.com)[^"]+)"[^>]*>'
            r"\s*(?:<[^>]+>\s*)*([^<]{20,180})\s*<",
            chunk,
            flags=re.I | re.S,
        )
        seen = set()
        now = datetime.now(timezone.utc)
        for link, raw_title in pairs:
            title = unescape(re.sub(r"\s+", " ", raw_title)).strip()
            if not title or title.lower() in ("see more news", "see more articles"):
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            host = urlparse(link).netloc or "coingecko.com"
            articles.append(
                {
                    "title": title,
                    "summary": "",
                    "source": f"coingecko.com/{host}",
                    "link": link,
                    # Homepage strip is live; treat as recent so recency weight applies
                    "published_at": now,
                }
            )
            if len(articles) >= 15:
                break
    except Exception:
        return articles

    return articles


def fetch_rss_articles(timeout_hint: float = 8.0) -> List[Dict[str, Any]]:
    """Fetch raw articles from RSS feeds + CoinGecko curated news (best-effort)."""
    articles: List[Dict[str, Any]] = []
    for feed_url in NEWS_FEEDS:
        try:
            # feedparser has no timeout; rely on OS defaults / failures
            feed = feedparser.parse(feed_url)
            source = urlparse(feed_url).netloc or feed_url
            for entry in feed.entries[:20]:
                title = entry.get("title") or ""
                if not title.strip():
                    continue
                articles.append(
                    {
                        "title": title.strip(),
                        "summary": (entry.get("summary") or "")[:500],
                        "source": source,
                        "link": entry.get("link"),
                        "published_at": parse_entry_time(entry),
                    }
                )
        except Exception:
            continue

    try:
        articles.extend(fetch_coingecko_articles(timeout=max(8.0, float(timeout_hint))))
    except Exception:
        pass

    return articles


def analyze_news_sentiment(
    symbol: str = "BTCUSDT",
    articles: Optional[List[Dict[str, Any]]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Full news sentiment analysis.
    If articles is None, fetch live RSS. Pass articles for offline tests.
    """
    t0 = time.time()
    fallback = False
    try:
        if articles is None:
            articles = fetch_rss_articles()
            if not articles:
                fallback = True
                articles = []
        result = score_headlines(articles, symbol)
        result["fallback_used"] = fallback or (
            result["articles_unique_used"] == 0 and articles == []
        )
        result["api_latency_ms"] = int((time.time() - t0) * 1000)
        if verbose:
            print(
                f"  {symbol} news={result['news_sentiment_score']:+.3f} "
                f"({result['news_sentiment_label']}) "
                f"used={result['articles_unique_used']}"
            )
        return result
    except Exception as e:
        if verbose:
            print(f"  News sentiment error: {e}")
        return {
            "symbol": symbol,
            "news_sentiment_score": 0.0,
            "news_sentiment_label": "Neutral",
            "articles_fetched": 0,
            "articles_unique_used": 0,
            "articles": [],
            "rejected_duplicate": 0,
            "rejected_future": 0,
            "rejected_stale": 0,
            "rejected_irrelevant": 0,
            "fallback_used": True,
            "error": str(e),
            "api_latency_ms": int((time.time() - t0) * 1000),
        }


def get_news_sentiment(symbol: str = "BTCUSDT", verbose: bool = False) -> float:
    """Backward-compatible float in [-1, 1]. Never raises."""
    try:
        return float(analyze_news_sentiment(symbol, verbose=verbose)["news_sentiment_score"])
    except Exception:
        return 0.0


if __name__ == "__main__":
    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        r = analyze_news_sentiment(symbol, verbose=True)
        print(r["news_sentiment_label"], r["news_sentiment_score"])
