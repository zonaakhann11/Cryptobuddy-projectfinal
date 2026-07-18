"""
Forward-evaluation logger for CryptoBuddy.

Because historical news / Fear&Greed / risk archives are unavailable, live
hourly predictions must be logged with as-of sentiment fields and later
joined to the next-hour outcome.

Log path: backend/models/reports/forward_eval_log.jsonl
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG_PATH = (
    Path(__file__).resolve().parent / "reports" / "forward_eval_log.jsonl"
)


def _ensure():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)


def append_forward_record(record: Dict[str, Any]) -> None:
    """Append one hourly prediction record (no outcome yet)."""
    _ensure()
    row = dict(record)
    row.setdefault("logged_at", datetime.now(timezone.utc).isoformat())
    row.setdefault("status", "open")
    row.setdefault("actual_next_hour_return", None)
    row.setdefault("actual_label", None)  # SELL/BUY/HOLD
    row.setdefault("outcome_correct", None)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def build_record_from_prediction(
    result: dict,
    candle_timestamp: Any,
    entry_close: float,
    threshold: float = 0.0015,
) -> dict:
    """Build a logger record from realtime_predict output."""
    return {
        "timestamp": str(candle_timestamp),
        "asset": result.get("symbol"),
        "model_version": result.get("model_version"),
        "raw_prediction": result.get("raw_prediction") or result.get("model_decision"),
        "final_decision": result.get("final_decision"),
        "probabilities": {
            "SELL": result.get("prob_sell"),
            "BUY": result.get("prob_buy"),
            "HOLD": result.get("prob_hold"),
        },
        "confidence": result.get("confidence"),
        "confirmation_score": result.get("confirmation_score"),
        "confirmation_reasons": result.get("confirmation_reasons"),
        "news_sentiment": result.get("news_sentiment"),
        "fear_greed": result.get("fear_greed_index"),
        "risk_score": result.get("risk_score"),
        "is_high_risk": result.get("is_high_risk"),
        "risk_events": result.get("risk_events"),
        "articles_events_used": {
            "risk_events": result.get("risk_events", []),
            "rejection_reason": result.get("rejection_reason"),
        },
        "rejection_reason": result.get("rejection_reason"),
        "strategy_badge": result.get("strategy_badge"),
        "entry_close": entry_close,
        "label_threshold": threshold,
        "status": "open",
    }


def read_log() -> List[dict]:
    _ensure()
    rows = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_log(rows: List[dict]) -> None:
    _ensure()
    with LOG_PATH.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")


def resolve_outcomes(
    price_lookup: Dict[str, Dict[str, float]],
    threshold: float = 0.0015,
) -> int:
    """
    Close open records when next-hour close is available.

    price_lookup: {asset: {iso_timestamp: close, ...}}
    Returns number of newly resolved rows.
    """
    rows = read_log()
    updated = 0
    for r in rows:
        if r.get("status") != "open":
            continue
        asset = r.get("asset")
        ts = r.get("timestamp")
        entry = r.get("entry_close")
        if not asset or not ts or entry is None:
            continue
        try:
            t0 = pd_to_datetime(ts)
            t1 = t0 + timedelta(hours=1)
            key = t1.isoformat()
            # try several key formats
            closes = price_lookup.get(asset, {})
            next_close = closes.get(key)
            if next_close is None:
                # try without tz / with space
                for k, v in closes.items():
                    if abs((pd_to_datetime(k) - t1).total_seconds()) < 60:
                        next_close = v
                        break
            if next_close is None:
                continue
            ret = (float(next_close) - float(entry)) / float(entry)
            if ret > threshold:
                label = "BUY"
            elif ret < -threshold:
                label = "SELL"
            else:
                label = "HOLD"
            decision = r.get("final_decision", "HOLD")
            if decision in ("BUY", "SELL"):
                correct = decision == label
            else:
                correct = None  # HOLD not scored as directional
            r["actual_next_hour_return"] = round(ret, 6)
            r["actual_label"] = label
            r["outcome_correct"] = correct
            r["status"] = "closed"
            r["resolved_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1
        except Exception:
            continue
    if updated:
        write_log(rows)
    return updated


def pd_to_datetime(ts):
    import pandas as pd

    return pd.to_datetime(ts, utc=True)
