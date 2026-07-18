"""Shared sentiment labels and helpers."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional


def news_sentiment_label(score: float) -> str:
    if score >= 0.60:
        return "Strongly Bullish"
    if score >= 0.25:
        return "Bullish"
    if score >= 0.08:
        return "Slightly Bullish"
    if score > -0.08:
        return "Neutral"
    if score > -0.25:
        return "Slightly Bearish"
    if score > -0.60:
        return "Bearish"
    return "Strongly Bearish"


def fear_greed_label(value_0_100: int) -> str:
    if value_0_100 <= 24:
        return "Extreme Fear"
    if value_0_100 <= 44:
        return "Fear"
    if value_0_100 <= 55:
        return "Neutral"
    if value_0_100 <= 74:
        return "Greed"
    return "Extreme Greed"


def risk_level_label(score: float, is_high_risk: bool = False) -> str:
    if score >= 0.75 or (is_high_risk and score >= 0.65):
        return "Critical"
    if score >= 0.50 or is_high_risk:
        return "High"
    if score >= 0.25:
        return "Medium"
    return "Low"


def normalize_fear_greed(value_0_100: int) -> float:
    """Map 0-100 Fear&Greed to [-1, +1]."""
    return round(max(-1.0, min(1.0, (value_0_100 - 50) / 50.0)), 3)


def parse_entry_time(entry: dict) -> Optional[datetime]:
    """Best-effort publication time as UTC datetime."""
    import time as time_mod

    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            ts = time_mod.mktime(parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (OverflowError, ValueError, OSError):
            pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if not raw:
            continue
        try:
            # feedparser sometimes leaves ISO strings
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def headline_key(title: str) -> str:
    """Normalize title for deduplication."""
    t = re.sub(r"\s+", " ", (title or "").strip().lower())
    t = re.sub(r"[^\w\s]", "", t)
    return t[:180]


def keyword_match(text: str, keywords: list) -> list:
    """Word-boundary aware keyword hits (avoids 'sol' in 'resolution')."""
    text_l = text.lower()
    hits = []
    for kw in keywords:
        kw_l = kw.lower().strip()
        if not kw_l:
            continue
        # multi-word: substring; single token: word boundary
        if " " in kw_l:
            if kw_l in text_l:
                hits.append(kw)
        else:
            if re.search(rf"\b{re.escape(kw_l)}\b", text_l):
                hits.append(kw)
    return hits
