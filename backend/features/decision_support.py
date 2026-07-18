"""
Decision-support payloads for the dashboard (plain English, real values).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _f(row, key: str, default: float = 0.0) -> float:
    try:
        v = row.get(key, default) if hasattr(row, "get") else row[key]
        if v is None:
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _group_score(grouped: List[dict], name: str) -> Optional[Dict[str, Any]]:
    for g in grouped or []:
        if g.get("group") == name:
            return {
                "status": g.get("status"),
                "score": g.get("score"),
            }
    return None


def build_news_takeaway(
    news_label: str,
    news_score: float,
    risk_level: str,
    risk_events: List[str],
    is_high_risk: bool,
) -> Dict[str, Any]:
    if is_high_risk or (risk_events and risk_level in ("High", "Critical")):
        ev = risk_events[0] if risk_events else "a high-risk keyword"
        summary = (
            f"High-risk news context detected ({risk_level}). "
            f"Example: {ev}. The system stays cautious and can block BUY."
        )
        tone = "caution"
    elif abs(float(news_score)) < 0.08:
        summary = (
            "Recent headlines are mostly neutral and do not strongly support BUY or SELL."
        )
        tone = "neutral"
    elif float(news_score) < 0:
        summary = (
            f"Recent headlines lean cautious ({news_label}). "
            "That supports staying careful, but it is not a trade order by itself."
        )
        tone = "bearish"
    else:
        summary = (
            f"Recent headlines lean constructive ({news_label}). "
            "Treat this as supportive context only — still check confirmations."
        )
        tone = "bullish"
    return {
        "summary": summary,
        "tone": tone,
        "news_label": news_label,
        "news_score": round(float(news_score), 3),
        "risk_level": risk_level,
        "has_high_risk_news": bool(is_high_risk or risk_events),
    }


def build_price_zone_context(latest_row) -> Dict[str, Any]:
    close = _f(latest_row, "close", 0)
    fallback = False

    # dist_to_high_24 = (close - roll_high) / close  →  high = close * (1 - dist)
    dist_h = _f(latest_row, "dist_to_high_24", 0)
    dist_l = _f(latest_row, "dist_to_low_24", 0)
    if close > 0 and abs(dist_h) < 0.5:
        resistance = close * (1.0 - dist_h)
    else:
        resistance = close * 1.015
        fallback = True
    if close > 0 and abs(dist_l) < 0.5:
        support = close * (1.0 - dist_l)
    else:
        support = close * 0.985
        fallback = True

    if support <= 0 or support >= close:
        support = min(close * 0.985, close - abs(resistance - close))
        fallback = True
    if resistance <= close:
        resistance = close * 1.01
        fallback = True

    p20 = _f(latest_row, "price_vs_ema20", 0)
    p50 = _f(latest_row, "price_vs_ema50", 0)
    p100 = _f(latest_row, "price_vs_ema100", 0)

    dist_sup_pct = (close - support) / close * 100.0 if close else 0.0
    dist_res_pct = (resistance - close) / close * 100.0 if close else 0.0

    def ema_phrase(name: str, rel: float) -> str:
        if rel > 0.001:
            return f"above {name}"
        if rel < -0.001:
            return f"below {name}"
        return f"near {name}"

    plain = (
        f"Nearby support sits around ${support:,.2f} "
        f"({dist_sup_pct:.2f}% below price). "
        f"Nearby resistance sits around ${resistance:,.2f} "
        f"({dist_res_pct:.2f}% above price). "
        f"Price is {ema_phrase('the short average (EMA20)', p20)}, "
        f"{ema_phrase('the medium average (EMA50)', p50)}, and "
        f"{ema_phrase('the longer average (EMA100)', p100)}."
    )

    return {
        "price": round(close, 4),
        "nearest_support": round(support, 4),
        "nearest_resistance": round(resistance, 4),
        "distance_to_support_pct": round(dist_sup_pct, 3),
        "distance_to_resistance_pct": round(dist_res_pct, 3),
        "vs_ema20_pct": round(p20 * 100, 3),
        "vs_ema50_pct": round(p50 * 100, 3),
        "vs_ema100_pct": round(p100 * 100, 3),
        "ema_plain": (
            f"{ema_phrase('EMA20', p20).capitalize()}; "
            f"{ema_phrase('EMA50', p50)}; "
            f"{ema_phrase('EMA100', p100)}."
        ),
        "plain_summary": plain,
        "fallback_used": fallback,
        "source": "24h high/low distance + EMA distances from live indicators",
    }


def build_what_would_change(
    *,
    raw_decision: str,
    final_decision: str,
    prob_buy: float,
    prob_sell: float,
    prob_hold: float,
    confirmation_score: int,
    confirmation_checks: List[dict],
    thr: Dict[str, Any],
    is_high_risk: bool,
    risk_level: str,
) -> Dict[str, Any]:
    buy_prob_need = float(thr.get("buy_prob", 0.40))
    sell_prob_need = float(thr.get("sell_prob", 0.33))
    buy_conf_need = int(thr.get("buy_confirms", 2))
    sell_conf_need = int(thr.get("sell_confirms", 3))

    failed = [c.get("label") for c in (confirmation_checks or []) if c.get("status") == "Failed"]
    passed = [c.get("label") for c in (confirmation_checks or []) if c.get("status") == "Passed"]

    to_buy: List[str] = []
    to_sell: List[str] = []
    invalidate: List[str] = []

    if final_decision == "HOLD":
        if prob_buy < buy_prob_need:
            to_buy.append(
                f"BUY probability rises to at least {buy_prob_need * 100:.0f}% "
                f"(now {prob_buy * 100:.0f}%)."
            )
        else:
            to_buy.append(f"BUY probability already meets {buy_prob_need * 100:.0f}%.")
        if confirmation_score < buy_conf_need:
            to_buy.append(
                f"At least {buy_conf_need} technical checks agree "
                f"(now {confirmation_score}/6)."
            )
        if failed:
            to_buy.append(f"Improve failing checks such as: {', '.join(failed[:3])}.")
        if is_high_risk:
            to_buy.append(f"Risk must cool from {risk_level} (BUY is blocked while high-risk).")
        if raw_decision == "HOLD":
            to_buy.append("Model outlook itself would need to lean BUY (currently HOLD).")

        if prob_sell < sell_prob_need:
            to_sell.append(
                f"SELL probability rises to at least {sell_prob_need * 100:.0f}% "
                f"(now {prob_sell * 100:.0f}%)."
            )
        else:
            to_sell.append(f"SELL probability already meets {sell_prob_need * 100:.0f}%.")
        if confirmation_score < sell_conf_need:
            to_sell.append(
                f"At least {sell_conf_need} technical checks agree for SELL "
                f"(now {confirmation_score}/6)."
            )
        if raw_decision == "HOLD":
            to_sell.append("Model outlook itself would need to lean SELL (currently HOLD).")

        headline = "HOLD means evidence is incomplete — here is what would unlock a direction."
    elif final_decision == "BUY":
        headline = "BUY is active — here is what would invalidate it."
        invalidate.append(
            f"BUY probability falling below {buy_prob_need * 100:.0f}% "
            f"(now {prob_buy * 100:.0f}%)."
        )
        invalidate.append(
            f"Confirmations dropping below {buy_conf_need}/6 (now {confirmation_score}/6)."
        )
        invalidate.append("A high-risk news/event flag appearing.")
        if passed:
            invalidate.append(f"Key supports fading: {', '.join(passed[:2])}.")
        to_buy = ["Already suggesting BUY — watch invalidation conditions."]
        to_sell = [
            f"A flip would need SELL lean ≥ {sell_prob_need * 100:.0f}% and "
            f"≥ {sell_conf_need} agreeing checks."
        ]
    else:  # SELL
        headline = "SELL is active — here is what would invalidate it."
        invalidate.append(
            f"SELL probability falling below {sell_prob_need * 100:.0f}% "
            f"(now {prob_sell * 100:.0f}%)."
        )
        invalidate.append(
            f"Confirmations dropping below {sell_conf_need}/6 (now {confirmation_score}/6)."
        )
        if passed:
            invalidate.append(f"Key supports fading: {', '.join(passed[:2])}.")
        to_sell = ["Already suggesting SELL — watch invalidation conditions."]
        to_buy = [
            f"A flip would need BUY lean ≥ {buy_prob_need * 100:.0f}%, "
            f"≥ {buy_conf_need} checks, and no high-risk block."
        ]

    return {
        "headline": headline,
        "final_decision": final_decision,
        "to_unlock_buy": to_buy,
        "to_unlock_sell": to_sell,
        "would_invalidate": invalidate,
        "thresholds": {
            "buy_prob": buy_prob_need,
            "sell_prob": sell_prob_need,
            "buy_confirms": buy_conf_need,
            "sell_confirms": sell_conf_need,
        },
        "current": {
            "prob_buy": round(prob_buy, 3),
            "prob_sell": round(prob_sell, 3),
            "prob_hold": round(prob_hold, 3),
            "confirmation_score": confirmation_score,
            "raw_decision": raw_decision,
        },
    }


def build_signal_snapshot(
    *,
    symbol: str,
    raw_decision: str,
    final_decision: str,
    confidence: float,
    confirmation_score: int,
    fear_greed_value: int,
    fear_greed_label: str,
    news_label: str,
    news_score: float,
    risk_level: str,
    grouped_indicators: List[dict],
) -> Dict[str, Any]:
    mom = _group_score(grouped_indicators, "Momentum") or {}
    trend = _group_score(grouped_indicators, "Trend") or {}
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "raw_outlook": raw_decision,
        "final_decision": final_decision,
        "confidence": round(float(confidence), 3),
        "confirmation_score": int(confirmation_score),
        "fear_greed_value": int(fear_greed_value),
        "fear_greed_label": fear_greed_label,
        "news_label": news_label,
        "news_score": round(float(news_score), 3),
        "risk_level": risk_level,
        "momentum_score": mom.get("score"),
        "momentum_status": mom.get("status"),
        "trend_score": trend.get("score"),
        "trend_status": trend.get("status"),
    }


def build_change_since_last(
    current: Dict[str, Any], previous: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    if not previous:
        return {
            "available": False,
            "summary": "No earlier prediction for this coin yet — run Predict again later to see what changed.",
            "changes": [],
            "highlight": None,
        }

    changes: List[Dict[str, Any]] = []

    def add(field: str, label: str, before, after, important: bool = False):
        if before == after:
            return
        changes.append(
            {
                "field": field,
                "label": label,
                "before": before,
                "after": after,
                "important": important,
            }
        )

    add(
        "final_decision",
        "Suggested action",
        previous.get("final_decision") or previous.get("decision"),
        current.get("final_decision"),
        True,
    )
    add(
        "raw_outlook",
        "Model outlook",
        previous.get("raw_outlook") or previous.get("raw_prediction"),
        current.get("raw_outlook"),
        True,
    )
    pc = previous.get("confidence")
    cc = current.get("confidence")
    if pc is not None and cc is not None and abs(float(pc) - float(cc)) >= 0.02:
        add(
            "confidence",
            "Confidence",
            f"{round(float(pc) * 100)}%",
            f"{round(float(cc) * 100)}%",
            True,
        )
    add(
        "momentum",
        "Momentum group",
        f"{previous.get('momentum_status')} ({previous.get('momentum_score')})",
        f"{current.get('momentum_status')} ({current.get('momentum_score')})",
    )
    add(
        "trend",
        "Trend group",
        f"{previous.get('trend_status')} ({previous.get('trend_score')})",
        f"{current.get('trend_status')} ({current.get('trend_score')})",
    )
    if previous.get("fear_greed_value") != current.get("fear_greed_value"):
        add(
            "fear_greed",
            "Fear & Greed",
            f"{previous.get('fear_greed_label')} ({previous.get('fear_greed_value')})",
            f"{current.get('fear_greed_label')} ({current.get('fear_greed_value')})",
            True,
        )
    add(
        "news",
        "News mood",
        previous.get("news_label"),
        current.get("news_label"),
    )
    add(
        "risk",
        "Risk level",
        previous.get("risk_level"),
        current.get("risk_level"),
        True,
    )

    if not changes:
        summary = "Little changed since the last prediction for this coin — the picture is stable."
        highlight = "Stable vs last run"
    else:
        top = next((c for c in changes if c.get("important")), changes[0])
        summary = (
            f"Biggest change: {top['label']} went from {top['before']} to {top['after']}."
        )
        highlight = summary

    return {
        "available": True,
        "previous_timestamp": previous.get("timestamp"),
        "summary": summary,
        "highlight": highlight,
        "changes": changes,
    }


def build_signal_history(records: List[dict], symbol: str, limit: int = 5) -> List[dict]:
    rows = [r for r in records if str(r.get("symbol", "")).upper() == str(symbol).upper()]
    rows = rows[-limit:]
    out = []
    for r in reversed(rows):
        out.append(
            {
                "timestamp": r.get("timestamp"),
                "raw_outlook": r.get("raw_outlook") or r.get("raw_prediction") or "—",
                "final_decision": r.get("final_decision") or r.get("decision"),
                "confidence": r.get("confidence"),
                "confirmation_score": r.get("confirmation_score"),
            }
        )
    return out
