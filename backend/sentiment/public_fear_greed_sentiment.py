"""Crypto Fear & Greed Index (Alternative.me)."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from sentiment.labels import fear_greed_label, normalize_fear_greed


def analyze_fear_greed(timeout: float = 5.0) -> Dict[str, Any]:
    """
    Fetch current Fear & Greed (+ history for dashboard).
    Never raises; fallback_used=True on failure.
    """
    hist = analyze_fear_greed_history(limit=31, timeout=timeout)
    now = hist["history"].get("now") or {}
    value = int(now.get("value", 50))
    label = now.get("label") or fear_greed_label(value)
    return {
        "fear_greed_value": value,
        "fear_greed_label": label,
        "fear_greed_normalized": normalize_fear_greed(value),
        "fear_greed_history": hist["history"],
        "fear_greed_trend": hist["trend"],
        "fear_greed_trend_plain": hist["trend_plain"],
        "fear_greed_updated": now.get("timestamp"),
        "fallback_used": hist.get("fallback_used", False),
        "error": hist.get("error"),
        "api_latency_ms": hist.get("api_latency_ms", 0),
        "source": "https://api.alternative.me/fng/",
    }


def analyze_fear_greed_history(limit: int = 31, timeout: float = 8.0) -> Dict[str, Any]:
    """Pull recent daily F&G points. Keys: now, yesterday, last_week, last_month."""
    t0 = time.time()
    try:
        response = requests.get(
            f"https://api.alternative.me/fng/?limit={limit}", timeout=timeout
        )
        response.raise_for_status()
        data = response.json().get("data") or []
        points: List[Dict[str, Any]] = []
        for row in data:
            value = int(row.get("value", 50))
            ts = row.get("timestamp")
            ts_iso = None
            if ts:
                try:
                    ts_iso = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
                except Exception:
                    ts_iso = None
            points.append(
                {
                    "value": value,
                    "label": row.get("value_classification") or fear_greed_label(value),
                    "timestamp": ts_iso,
                }
            )

        def at(idx: int) -> Optional[Dict[str, Any]]:
            if 0 <= idx < len(points):
                return points[idx]
            return None

        now = at(0) or {"value": 50, "label": "Neutral", "timestamp": None}
        yesterday = at(1)
        last_week = at(7) if len(points) > 7 else (at(len(points) - 1) if len(points) > 1 else None)
        last_month = at(30) if len(points) > 30 else (at(len(points) - 1) if points else None)

        history = {
            "now": now,
            "yesterday": yesterday,
            "last_week": last_week,
            "last_month": last_month,
        }
        trend, trend_plain = _fg_trend(now, yesterday, last_week)
        return {
            "history": history,
            "points": points[:14],
            "trend": trend,
            "trend_plain": trend_plain,
            "fallback_used": False,
            "api_latency_ms": int((time.time() - t0) * 1000),
            "source": "https://api.alternative.me/fng/",
        }
    except Exception as e:
        neutral = {"value": 50, "label": "Neutral", "timestamp": None}
        return {
            "history": {
                "now": neutral,
                "yesterday": None,
                "last_week": None,
                "last_month": None,
            },
            "points": [],
            "trend": "unknown",
            "trend_plain": "Fear & Greed history unavailable right now — showing a neutral fallback.",
            "fallback_used": True,
            "error": str(e),
            "api_latency_ms": int((time.time() - t0) * 1000),
            "source": "https://api.alternative.me/fng/",
        }


def _fg_trend(now: dict, yesterday: Optional[dict], last_week: Optional[dict]):
    n = int(now.get("value", 50))
    if yesterday:
        y = int(yesterday.get("value", n))
        delta = n - y
        if delta >= 3:
            return "improving", (
                f"Fear is easing versus yesterday ({y} → {n}). Mood is improving a little."
            )
        if delta <= -3:
            return "worsening", (
                f"Fear is deepening versus yesterday ({y} → {n}). Mood is more cautious."
            )
        return "stable", (
            f"Fear & Greed is roughly stable versus yesterday ({y} → {n})."
        )
    if last_week:
        w = int(last_week.get("value", n))
        delta = n - w
        if delta >= 5:
            return "improving", f"Fear has eased versus last week ({w} → {n})."
        if delta <= -5:
            return "worsening", f"Fear has deepened versus last week ({w} → {n})."
        return "stable", f"Fear & Greed is roughly stable versus last week ({w} → {n})."
    return "stable", f"Current Fear & Greed is {n} ({now.get('label')})."


def get_fear_greed_sentiment(symbol: str = "BTCUSDT") -> float:
    """Backward-compatible normalized [-1, 1]."""
    return float(analyze_fear_greed()["fear_greed_normalized"])


def fear_greed_from_value(value: int) -> Dict[str, Any]:
    """Deterministic helper for scenario tests (no network)."""
    value = int(max(0, min(100, value)))
    point = {"value": value, "label": fear_greed_label(value), "timestamp": None}
    return {
        "fear_greed_value": value,
        "fear_greed_label": fear_greed_label(value),
        "fear_greed_normalized": normalize_fear_greed(value),
        "fear_greed_history": {
            "now": point,
            "yesterday": None,
            "last_week": None,
            "last_month": None,
        },
        "fear_greed_trend": "stable",
        "fear_greed_trend_plain": f"Current Fear & Greed is {value} (test value).",
        "fallback_used": False,
        "api_latency_ms": 0,
        "source": "https://api.alternative.me/fng/",
    }
