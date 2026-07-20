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
    grouped_indicators: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    buy_prob_need = float(thr.get("buy_prob", 0.40))
    sell_prob_need = float(thr.get("sell_prob", 0.33))
    buy_conf_need = int(thr.get("buy_confirms", 2))
    sell_conf_need = int(thr.get("sell_confirms", 3))

    failed = [c.get("label") for c in (confirmation_checks or []) if c.get("status") == "Failed"]
    passed = [c.get("label") for c in (confirmation_checks or []) if c.get("status") == "Passed"]
    lean = str(raw_decision or "").upper()
    groups = grouped_indicators or []

    def _group(name: str) -> Dict[str, Any]:
        for g in groups:
            if str(g.get("group", "")).lower() == name.lower():
                return g
        return {}

    def _watching(name: str) -> Optional[str]:
        w = (_group(name).get("strongest_conflict") or "").strip().rstrip(".")
        return w or None

    def _helping(name: str) -> Optional[str]:
        h = (_group(name).get("strongest_support") or "").strip().rstrip(".")
        return h or None

    to_buy: List[str] = []
    to_sell: List[str] = []
    invalidate: List[str] = []

    if final_decision == "HOLD":
        if lean == "HOLD":
            headline = (
                "Suggested action stays HOLD because the model outlook is HOLD — "
                "bullish charts alone do not unlock BUY or SELL."
            )
            to_buy.append(
                f"Next-hour model outlook must flip to BUY "
                f"(now HOLD wins at {prob_hold * 100:.0f}%; BUY is only {prob_buy * 100:.0f}%)."
            )
            to_buy.append(
                f"Then BUY probability must clear {buy_prob_need * 100:.0f}% "
                f"and at least {buy_conf_need}/6 BUY checks must still agree."
            )
            vol_watch = _watching("Volatility")
            mom_watch = _watching("Momentum")
            ctx_watch = _watching("Market Context")
            vol_status = str(_group("Volatility").get("status") or "").lower()
            if vol_watch or vol_status in ("high risk", "bearish"):
                to_buy.append(
                    f"Volatility cools — currently watching: "
                    f"{vol_watch or 'jumpy / high-volatility regime'}."
                )
            if mom_watch:
                to_buy.append(f"Momentum confirmation improves: {mom_watch}.")
            if ctx_watch:
                to_buy.append(f"Broader market helps: {ctx_watch}.")
            if is_high_risk:
                to_buy.append(
                    f"Risk must cool from {risk_level} (high-risk blocks BUY even if lean flips)."
                )

            to_sell.append(
                f"Next-hour model outlook must flip to SELL "
                f"(now HOLD wins at {prob_hold * 100:.0f}%; SELL is {prob_sell * 100:.0f}%)."
            )
            to_sell.append(
                f"Then SELL probability must clear {sell_prob_need * 100:.0f}% "
                f"and at least {sell_conf_need}/6 SELL checks must agree."
            )
            trend_help = _helping("Trend")
            if trend_help and str(_group("Trend").get("status") or "").lower() == "bullish":
                to_sell.append(
                    f"Trend would need to weaken (now bullish — {trend_help})."
                )
            mom_help = _helping("Momentum")
            if mom_help and str(_group("Momentum").get("status") or "").lower() == "bullish":
                to_sell.append(
                    f"Momentum would need to roll over (now bullish — {mom_help})."
                )
        elif lean == "BUY":
            headline = (
                "Model leaned BUY, but filters kept HOLD — "
                "here is what would unlock BUY."
            )
            if prob_buy < buy_prob_need:
                to_buy.append(
                    f"BUY probability rises to >= {buy_prob_need * 100:.0f}% "
                    f"(now {prob_buy * 100:.0f}%)."
                )
            if confirmation_score < buy_conf_need:
                to_buy.append(
                    f"At least {buy_conf_need}/6 BUY-side checks agree "
                    f"(now {confirmation_score}/6)."
                )
            if failed:
                to_buy.append(f"Turn these red checks green: {', '.join(failed[:3])}.")
            if is_high_risk:
                to_buy.append(f"Risk cools from {risk_level}.")
            vol_watch = _watching("Volatility")
            if vol_watch:
                to_buy.append(f"Volatility: {vol_watch}.")
            to_sell.append(
                f"A SELL path needs the model to lean SELL (>= {sell_prob_need * 100:.0f}%) "
                f"with >= {sell_conf_need} SELL-side checks."
            )
        else:
            headline = (
                "Model leaned SELL, but filters kept HOLD — "
                "here is what would unlock SELL."
            )
            if prob_sell < sell_prob_need:
                to_sell.append(
                    f"SELL probability rises to >= {sell_prob_need * 100:.0f}% "
                    f"(now {prob_sell * 100:.0f}%)."
                )
            if confirmation_score < sell_conf_need:
                to_sell.append(
                    f"At least {sell_conf_need}/6 SELL-side checks agree "
                    f"(now {confirmation_score}/6)."
                )
            if failed:
                to_sell.append(f"Turn these red checks green: {', '.join(failed[:3])}.")
            mom_help = _helping("Momentum")
            if mom_help:
                to_sell.append(f"Bullish leftovers still in the way: {mom_help}.")
            to_buy.append(
                f"A BUY path needs the model to lean BUY (>= {buy_prob_need * 100:.0f}%) "
                f"with >= {buy_conf_need} BUY-side checks"
                + (" and no high-risk block." if is_high_risk else ".")
            )
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
        vol_watch = _watching("Volatility")
        if vol_watch:
            invalidate.append(f"Volatility flare-up: {vol_watch}.")
        to_buy = ["Already suggesting BUY — watch invalidation conditions."]
        to_sell = [
            f"A flip would need SELL lean >= {sell_prob_need * 100:.0f}% and "
            f">= {sell_conf_need} agreeing SELL-side checks."
        ]
    else:
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
            f"A flip would need BUY lean >= {buy_prob_need * 100:.0f}%, "
            f">= {buy_conf_need} BUY-side checks, and no high-risk block."
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


def build_buddy_take(
    *,
    latest_row,
    symbol: str,
    raw_decision: str,
    final_decision: str,
    prob_buy: float,
    prob_sell: float,
    prob_hold: float,
    confirmation_score: int,
    confirmation_checks: List[dict],
    confirmation_reasons: List[str],
    thr: Dict[str, Any],
    grouped_indicators: List[dict],
    news_label: str,
    fg_label: str,
    fg_value: int,
    risk_level: str,
    risk_events: List[str],
    is_high_risk: bool,
    price_zone: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Plain-English sum-up for someone who doesn't know trading jargon.
    Gives CryptoBuddy's opinion + why, plus an own-risk reminder.
    """
    buy_p = int(round(float(prob_buy) * 100))
    sell_p = int(round(float(prob_sell) * 100))
    hold_p = int(round(float(prob_hold) * 100))
    lean = str(raw_decision or "HOLD").upper()
    action = str(final_decision or "HOLD").upper()
    reasons = list(confirmation_reasons or [])
    groups = {str(g.get("group")): g for g in (grouped_indicators or [])}

    def gstat(name: str) -> str:
        return str((groups.get(name) or {}).get("status") or "")

    # --- market story in everyday words (from raw features, not jargon labels) ---
    market_bits: List[str] = []
    rsi = _f(latest_row, "rsi_14", 50)
    slope = _f(latest_row, "rsi_slope", 0)
    hist = _f(latest_row, "macd_histogram", 0)
    vz = _f(latest_row, "volume_zscore", 0)
    vpm = _f(latest_row, "volume_price_momentum", 0)
    p20 = _f(latest_row, "price_vs_ema20", 0)

    if vz > 0.3 and vpm > 0:
        market_bits.append(
            "plenty of traders seem to be joining the move, and price and activity are moving the same way"
        )
    elif vz > 0.3 and vpm < 0:
        market_bits.append(
            "trading activity is busy, but more on the way down than up"
        )
    elif vz <= 0.3:
        market_bits.append(
            "the move looks a bit thin — not many traders are really jumping in yet"
        )

    if rsi >= 70:
        market_bits.append(
            "price has already been pushed quite hard upward, so chasing it higher looks stretched"
        )
    elif rsi <= 30:
        market_bits.append(
            "price looks washed out / sold hard already, which can mean sellers are tired"
        )
    elif 45 < rsi < 70 and slope > 0:
        market_bits.append(
            "price hasn't been stretched too far yet, and the short-term push still looks alive"
        )
    elif slope < 0:
        market_bits.append(
            "the short-term upward push is cooling off"
        )
    else:
        market_bits.append(
            "price looks fairly balanced — not clearly overstretched either way"
        )

    if hist > 0 and p20 > 0:
        market_bits.append(
            "recent strength is still pointing up and price is sitting above its short average path"
        )
    elif hist < 0 and p20 < 0:
        market_bits.append(
            "recent strength is pointing down and price is under its short average path"
        )
    elif hist > 0:
        market_bits.append("short-term strength still leans a little upward")
    elif hist < 0:
        market_bits.append("short-term strength still leans a little downward")

    if gstat("Volatility") in ("High Risk", "Bearish"):
        market_bits.append(
            "the market feels jumpy right now, which makes sudden swings more likely"
        )

    if gstat("Market Context") == "Bullish":
        market_bits.append("the broader crypto backdrop looks okay for this coin")
    elif gstat("Market Context") == "Bearish":
        market_bits.append("the broader crypto backdrop looks a bit weak")

    market_story = ""
    if market_bits:
        bits = market_bits[:4]
        if len(bits) == 1:
            market_story = bits[0].capitalize() + "."
        elif len(bits) == 2:
            market_story = bits[0].capitalize() + ", and " + bits[1] + "."
        else:
            market_story = (
                bits[0].capitalize()
                + ", "
                + ", ".join(bits[1:-1])
                + ", and "
                + bits[-1]
                + "."
            )
    # --- news / mood ---
    mood_bits: List[str] = []
    nl = (news_label or "Neutral").lower()
    if "bull" in nl:
        mood_bits.append("Headlines lean a bit positive")
    elif "bear" in nl:
        mood_bits.append("Headlines lean a bit cautious")
    else:
        mood_bits.append("Headlines look mostly mixed / quiet")

    fg = (fg_label or "Neutral").lower()
    if "fear" in fg:
        mood_bits.append(
            f"Overall market mood is fearful (fear/greed around {int(fg_value)})"
        )
    elif "greed" in fg:
        mood_bits.append(
            f"Overall market mood is greedy (fear/greed around {int(fg_value)})"
        )
    else:
        mood_bits.append(
            f"Overall market mood is fairly neutral (fear/greed around {int(fg_value)})"
        )

    if is_high_risk or risk_level in ("High", "Critical"):
        ev = (risk_events or ["a worrying news flag"])[0]
        mood_bits.append(f"We also flagged extra risk ({risk_level}): {ev}")
    elif risk_level == "Medium":
        mood_bits.append("Risk looks medium — nothing extreme, but not risk-free")
    else:
        mood_bits.append("We did not see a high-risk news alarm")

    mood_story = ". ".join(mood_bits) + "."

    # --- price zone (simple) ---
    zone_story = ""
    pz = price_zone or {}
    support = pz.get("support")
    resistance = pz.get("resistance")
    zone_parts = []
    try:
        if support is not None:
            zone_parts.append(f"a nearby support area around ${float(support):,.2f}")
        if resistance is not None:
            zone_parts.append(f"resistance around ${float(resistance):,.2f}")
    except Exception:
        zone_parts = []
    if zone_parts:
        zone_story = "On the chart, price is near " + " and ".join(zone_parts) + "."

    # --- our opinion / why this suggestion ---
    buy_need = int(round(float(thr.get("buy_prob", 0.40)) * 100))
    sell_need = int(round(float(thr.get("sell_prob", 0.33)) * 100))
    buy_conf_need = int(thr.get("buy_confirms", 2))
    sell_conf_need = int(thr.get("sell_confirms", 3))
    failed_raw = [
        c.get("label")
        for c in (confirmation_checks or [])
        if c.get("status") == "Failed"
    ]

    def _plain_fail(label: str) -> str:
        t = str(label or "").lower()
        if "volume" in t and "lower" in t:
            return "price and trading activity are not moving down together"
        if "volume" in t or "trading" in t:
            return "not enough trading activity yet"
        if "momentum" in t and "weak" in t:
            return "short-term strength is not clearly weak"
        if "momentum" in t:
            return "short-term strength is not clearly lined up"
        if "rsi" in t and "falling" in t:
            return "the short-term push is not clearly fading"
        if "rsi" in t and "rising" in t:
            return "the short-term push is not clearly rising"
        if "rsi" in t and "weak" in t:
            return "price is not clearly in a soft/weak zone"
        if "rsi" in t and "healthy" in t:
            return "price is not in a comfortable mid-range"
        if "macd" in t and "down" in t:
            return "downside strength is not confirmed"
        if "macd" in t:
            return "upside strength is not confirmed"
        if "price and volume" in t or "move together" in t:
            return "price and activity are not clearly moving together"
        return "one of the market checks still disagrees"

    failed_plain = [_plain_fail(x) for x in failed_raw[:3]]

    opinion_parts: List[str] = []
    if action == "HOLD" and lean == "HOLD":
        opinion_parts.append(
            f"Our take: sit this one out (HOLD). The model itself does not see a clear "
            f"next-hour edge — it puts about {hold_p}% on sitting out, {buy_p}% on buying, "
            f"and {sell_p}% on selling."
        )
        if vz <= 0.3:
            opinion_parts.append(
                "Even where the chart looks okay, the move does not look busy enough yet "
                "for us to push a buy or sell call."
            )
        opinion_parts.append(
            f"For a BUY call we usually want the model closer to {buy_need}%+ on buy "
            f"and clearer agreement from the market checks; for SELL, about {sell_need}%+ "
            f"on sell with stronger chart agreement."
        )
    elif action == "HOLD" and lean == "BUY":
        opinion_parts.append(
            f"Our take: still HOLD for now. The model leaned BUY (~{buy_p}%), but we did "
            f"not get enough agreement from the market checks "
            f"({confirmation_score}/6 passed; we like at least {buy_conf_need})."
        )
        if vz <= 0.3:
            opinion_parts.append(
                "In plain words: it is not busy enough / not confirmed enough to recommend buying yet."
            )
        if failed_plain:
            opinion_parts.append(
                "What is still missing: " + "; ".join(failed_plain) + "."
            )
        if is_high_risk or "risk_override" in reasons:
            opinion_parts.append(
                "Also, risk context made us extra careful about recommending a buy."
            )
    elif action == "HOLD" and lean == "SELL":
        opinion_parts.append(
            f"Our take: still HOLD for now. The model leaned SELL (~{sell_p}%), but not "
            f"enough chart checks agreed ({confirmation_score}/6; we like at least "
            f"{sell_conf_need} for a sell call)."
        )
        if failed_plain:
            opinion_parts.append(
                "What is still missing: " + "; ".join(failed_plain) + "."
            )
    elif action == "BUY":
        opinion_parts.append(
            f"Our take: a cautious BUY lean. The model puts about {buy_p}% on buy, "
            f"and {confirmation_score}/6 market checks agreed enough for us to show that suggestion."
        )
        if vz > 0.3:
            opinion_parts.append(
                "Activity looks supportive enough that the upward idea is not empty."
            )
    else:  # SELL
        opinion_parts.append(
            f"Our take: a cautious SELL lean. The model puts about {sell_p}% on sell, "
            f"and {confirmation_score}/6 market checks agreed enough for us to show that suggestion."
        )

    # forward-looking soft opinion
    forward = ""
    if action == "HOLD":
        if vz <= 0.3 and hist >= 0 and rsi < 70:
            forward = (
                "If more traders start joining and the upward push stays healthy — "
                "without price getting stretched — a clearer buy case could form later. "
                "If strength fades and selling picks up, a sell case could form instead."
            )
        elif hist < 0 or slope < 0:
            forward = (
                "If selling keeps building and the short-term push stays weak, "
                "a clearer sit-out or sell case becomes more believable. "
                "A bounce with real participation would be needed before we'd lean buy."
            )
        else:
            forward = (
                "We'd want a clearer next-hour lean from the model, plus stronger "
                "agreement from activity and short-term strength, before calling buy or sell."
            )
    elif action == "BUY":
        forward = (
            "That buy lean would look weaker if activity dries up, the short-term push "
            "fades, or scary news shows up."
        )
    else:
        forward = (
            "That sell lean would look weaker if buyers return with real activity "
            "and short-term strength turns back up."
        )

    disclaimer = (
        "This is decision support from CryptoBuddy — not financial advice and not an order "
        "to trade. Crypto is risky; if you act, you do so on your own judgment and your own risk."
    )

    paragraphs = [
        p for p in [
            market_story,
            mood_story,
            zone_story,
            " ".join(opinion_parts),
            forward,
            disclaimer,
        ]
        if p
    ]
    full = " ".join(paragraphs)

    # Short line for history cards
    if action == "HOLD" and lean == "HOLD":
        short = (
            f"We said HOLD — no clear next-hour edge (buy {buy_p}% / sell {sell_p}% / hold {hold_p}%). "
            + (
                "Move looks thin on activity."
                if vz <= 0.3
                else "Waiting for a clearer setup."
            )
        )
    elif action == "HOLD":
        short = (
            f"Model leaned {lean}, we still said HOLD — not enough market agreement yet "
            f"({confirmation_score}/6)."
        )
    else:
        short = (
            f"We suggested {action} — model ~{max(buy_p, sell_p)}% on that side with "
            f"{confirmation_score}/6 checks agreeing. Trade only if you accept the risk."
        )

    return {
        "title": "Buddy's take",
        "summary": full,
        "short": short,
        "action": action,
        "model_lean": lean,
        "paragraphs": paragraphs,
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
                "buddy_take_short": r.get("buddy_take_short") or r.get("short_take"),
            }
        )
    return out
