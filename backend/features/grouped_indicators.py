"""
Grouped indicator summaries for explainable live predictions.

Scores are deterministic functions of backward-looking feature columns.
They are for decision-support display (not ML features by default).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np

from features.decision_copy import GROUP_PLAIN


def _f(row, key: str, default: float = 0.0) -> float:
    try:
        v = row.get(key, default) if hasattr(row, "get") else row[key]
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return float(default)
        return float(v)
    except Exception:
        return float(default)


def _clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


def _status_from_signed(score_0_100: float, high_risk: bool = False) -> str:
    if high_risk:
        return "High Risk"
    if score_0_100 >= 62:
        return "Bullish"
    if score_0_100 <= 38:
        return "Bearish"
    if 45 <= score_0_100 <= 55:
        return "Neutral"
    return "Mixed"


def _pack(
    name: str,
    score_0_100: float,
    indicators: List[str],
    support: str,
    conflict: str,
    explanation: str,
    high_risk: bool = False,
) -> Dict[str, Any]:
    score = int(round(max(0, min(100, score_0_100))))
    status = _status_from_signed(score, high_risk=high_risk)
    what = GROUP_PLAIN.get(name, name)
    return {
        "group": name,
        "status": status,
        "score": score,
        "what_it_means": what,
        "indicators_used": indicators,
        "strongest_support": support,
        "strongest_conflict": conflict,
        "explanation": explanation,
        "plain_summary": (
            f"{name}: {status} ({score}/100). {what} "
            f"Helping: {support}. Watching: {conflict}."
        ),
    }


def score_momentum(row) -> Dict[str, Any]:
    """
    Momentum score (0–100):
      +20 if RSI14 in (45, 70) healthy bullish zone
      +15 if rsi_slope > 0
      +20 if macd_histogram > 0
      +15 if stoch_k > stoch_d
      +15 if return_3h > 0
      +15 if momentum_agreement >= 0.6
    Base 20; map sum of points into 0–100 via clip.
    """
    rsi = _f(row, "rsi_14", 50)
    slope = _f(row, "rsi_slope", 0)
    hist = _f(row, "macd_histogram", 0)
    sk = _f(row, "stoch_k", 50)
    sd = _f(row, "stoch_d", 50)
    r3 = _f(row, "return_3h", 0)
    agr = _f(row, "momentum_agreement", 0.5)

    pts = 20.0
    support_bits: List[Tuple[float, str]] = []
    conflict_bits: List[Tuple[float, str]] = []

    if 45 < rsi < 70:
        pts += 20
        support_bits.append((20, f"RSI looks healthy ({rsi:.0f}) — not extreme"))
    elif rsi >= 70:
        pts += 5
        conflict_bits.append((15, f"RSI is high ({rsi:.0f}) — may be overheated"))
    elif rsi <= 30:
        pts += 5
        conflict_bits.append((15, f"RSI is low ({rsi:.0f}) — may be washed out"))
    else:
        conflict_bits.append((10, f"RSI is middling ({rsi:.0f}) — weak push"))

    if slope > 0:
        pts += 15
        support_bits.append((15, "RSI has been rising lately"))
    else:
        conflict_bits.append((15, "RSI is flat or falling"))

    if hist > 0:
        pts += 20
        support_bits.append((20, "MACD momentum is positive"))
    else:
        conflict_bits.append((20, "MACD momentum is not positive"))

    if sk > sd:
        pts += 15
        support_bits.append((15, "Short-term oscillator agrees with upside"))
    else:
        conflict_bits.append((10, "Short-term oscillator does not confirm"))

    if r3 > 0:
        pts += 15
        support_bits.append((15, "Last 3 hours closed higher overall"))
    else:
        conflict_bits.append((10, "Last 3 hours were flat or down"))

    if agr >= 0.6:
        pts += 15
        support_bits.append((15, "Several momentum tools agree"))
    else:
        conflict_bits.append((10, "Momentum tools disagree with each other"))

    score = _clip01(pts / 120.0) * 100.0
    support_bits.sort(reverse=True)
    conflict_bits.sort(reverse=True)
    support = support_bits[0][1] if support_bits else "little upside momentum"
    conflict = conflict_bits[0][1] if conflict_bits else "nothing major against it"
    status_word = "Bullish" if score >= 62 else ("Bearish" if score <= 38 else "Mixed")
    expl = (
        f"{status_word} momentum ({int(round(score))}/100). "
        f"In plain terms: is recent strength building? Helping: {support}. "
        f"Watching: {conflict}."
    )
    return _pack(
        "Momentum",
        score,
        ["rsi_14", "rsi_slope", "macd_histogram", "stoch_k", "stoch_d", "return_3h", "momentum_agreement"],
        support,
        conflict,
        expl,
    )


def score_trend(row) -> Dict[str, Any]:
    """
    Trend score:
      +25 price > ema20, +20 price > ema50, +15 price > ema100
      +20 ema20 > ema50, +10 ema_cross_slope > 0
      +10 trend_strength > 0.6
    """
    pts = 15.0
    support_bits: List[Tuple[float, str]] = []
    conflict_bits: List[Tuple[float, str]] = []

    p20 = _f(row, "price_vs_ema20", 0)
    p50 = _f(row, "price_vs_ema50", 0)
    p100 = _f(row, "price_vs_ema100", 0)
    cross = _f(row, "ema_cross", 0)
    cslope = _f(row, "ema_cross_slope", 0)
    strength = _f(row, "trend_strength", 0.5)

    if p20 > 0:
        pts += 25
        support_bits.append((25, "Price is above the short average (EMA20)"))
    else:
        conflict_bits.append((25, "Price is below the short average (EMA20)"))
    if p50 > 0:
        pts += 20
        support_bits.append((20, "Price is above the medium average (EMA50)"))
    else:
        conflict_bits.append((20, "Price is below the medium average (EMA50)"))
    if p100 > 0:
        pts += 15
        support_bits.append((15, "Price is above the longer average (EMA100)"))
    else:
        conflict_bits.append((12, "Price is below the longer average (EMA100)"))
    if cross > 0:
        pts += 20
        support_bits.append((20, "Short average is above medium (uptrend structure)"))
    else:
        conflict_bits.append((20, "Short average is below medium (downtrend structure)"))
    if cslope > 0:
        pts += 10
        support_bits.append((10, "That uptrend structure is strengthening"))
    if strength > 0.6:
        pts += 10
        support_bits.append((10, "Trend looks relatively clear, not choppy"))

    score = _clip01(pts / 115.0) * 100.0
    support_bits.sort(reverse=True)
    conflict_bits.sort(reverse=True)
    support = support_bits[0][1] if support_bits else "no clear trend structure"
    conflict = conflict_bits[0][1] if conflict_bits else "nothing major against it"
    word = "Bullish" if score >= 62 else ("Bearish" if score <= 38 else "Mixed")
    expl = (
        f"{word} trend ({int(round(score))}/100). "
        f"In plain terms: is price riding above its recent path? "
        f"Helping: {support}. Watching: {conflict}."
    )
    return _pack(
        "Trend",
        score,
        ["price_vs_ema20", "price_vs_ema50", "price_vs_ema100", "ema_cross", "ema_cross_slope", "trend_strength"],
        support,
        conflict,
        expl,
    )


def score_volatility(row) -> Dict[str, Any]:
    """
    Volatility is not directional. High atr_pctile / wide bands / elevated
    vol_regime → High Risk (score forced toward extremes for UI: lower = calmer).

    Calm score (higher = safer/calmer):
      base 70
      -25 if vol_regime == 1
      -20 if atr_pctile > 0.75
      -15 if bb_width in top quartile proxy (atr_pctile>0.7 used if width missing)
      +10 if bb_position mid (0.3–0.7)
    """
    atr_p = _f(row, "atr_pctile", 0.5)
    vol_reg = _f(row, "vol_regime", 0)
    bb_pos = _f(row, "bb_position", 0.5)
    bb_w = _f(row, "bb_width", 0)
    atr_pct = _f(row, "atr_pct", 0)

    pts = 70.0
    support_bits: List[Tuple[float, str]] = []
    conflict_bits: List[Tuple[float, str]] = []
    high_risk = False

    if vol_reg >= 1:
        pts -= 25
        high_risk = True
        conflict_bits.append((25, "Market is in a jumpy (high-volatility) regime"))
    else:
        support_bits.append((15, "Volatility is not unusually elevated"))

    if atr_p > 0.75:
        pts -= 20
        high_risk = True
        conflict_bits.append((20, "Hourly swings are large vs recent history"))
    else:
        support_bits.append((15, "Hourly swings look moderate vs recent history"))

    if atr_p > 0.7 or bb_w > 0.08:
        pts -= 10
        conflict_bits.append((10, "Price bands are widening — bigger moves possible"))

    if 0.3 <= bb_pos <= 0.7:
        pts += 10
        support_bits.append((10, "Price sits mid-range (not pressed to extremes)"))

    score = _clip01(pts / 100.0) * 100.0
    support_bits.sort(reverse=True)
    conflict_bits.sort(reverse=True)
    support = support_bits[0][1] if support_bits else "volatility looks stable"
    conflict = conflict_bits[0][1] if conflict_bits else "nothing major against calm"
    if high_risk:
        status = "High Risk"
    elif score >= 55:
        status = "Neutral"
    else:
        status = "Mixed"
    expl = (
        f"Volatility: {status} ({int(round(score))}/100). "
        f"In plain terms: calm is safer for acting; jumpy markets raise risk. "
        f"Helping: {support}. Watching: {conflict}."
    )
    pack = _pack(
        "Volatility",
        score,
        ["atr_pct", "atr_pctile", "bb_width", "bb_position", "vol_regime", "volatility_24h"],
        support,
        conflict,
        expl,
        high_risk=high_risk,
    )
    pack["status"] = status
    return pack


def score_volume(row) -> Dict[str, Any]:
    """
    Volume participation (bullish participation when price up + volume up):
      +25 volume_zscore > 0.3
      +20 abnormal_volume
      +25 price_volume_agree > 0
      +15 volume_price_momentum > 0
      +15 volume_change_1h > 0
    """
    pts = 20.0
    support_bits: List[Tuple[float, str]] = []
    conflict_bits: List[Tuple[float, str]] = []

    vz = _f(row, "volume_zscore", 0)
    abn = _f(row, "abnormal_volume", 0)
    agree = _f(row, "price_volume_agree", 0)
    vpm = _f(row, "volume_price_momentum", 0)
    vc = _f(row, "volume_change_1h", 0)

    if vz > 0.3:
        pts += 25
        support_bits.append((25, "More trading activity than usual"))
    else:
        conflict_bits.append((15, "Trading activity is soft vs usual"))
    if abn >= 1:
        pts += 20
        support_bits.append((20, "Unusually high volume spike"))
    if agree > 0:
        pts += 25
        support_bits.append((25, "Price move is backed by volume"))
    else:
        conflict_bits.append((20, "Price moved without matching volume support"))
    if vpm > 0:
        pts += 15
        support_bits.append((15, "Price and volume momentum point the same way"))
    else:
        conflict_bits.append((10, "Price/volume momentum is not aligned"))
    if vc > 0:
        pts += 15
        support_bits.append((15, "Volume rose versus the prior hour"))

    score = _clip01(pts / 120.0) * 100.0
    support_bits.sort(reverse=True)
    conflict_bits.sort(reverse=True)
    support = support_bits[0][1] if support_bits else "quiet participation"
    conflict = conflict_bits[0][1] if conflict_bits else "nothing major against it"
    word = "Bullish" if score >= 62 else ("Bearish" if score <= 38 else "Mixed")
    expl = (
        f"{word} volume participation ({int(round(score))}/100). "
        f"In plain terms: are traders showing up? Helping: {support}. "
        f"Watching: {conflict}."
    )
    return _pack(
        "Volume",
        score,
        ["volume_zscore", "abnormal_volume", "price_volume_agree", "volume_price_momentum", "volume_change_1h"],
        support,
        conflict,
        expl,
    )


def score_market_context(row, symbol: str = "") -> Dict[str, Any]:
    """
    Market context from sessions + BTC/ETH relative returns when present.
      +20 session_us or session_europe (liquidity)
      +25 btc_return_1h > 0 (for alts) / own return for BTC
      +20 rel_return_vs_btc_1h > 0 when available
      +15 return_24h > 0
      +20 breakout not at extreme (dist_to_high_24 > -0.01)
    """
    pts = 20.0
    support_bits: List[Tuple[float, str]] = []
    conflict_bits: List[Tuple[float, str]] = []

    sess_us = _f(row, "session_us", 0)
    sess_eu = _f(row, "session_europe", 0)
    btc_r = _f(row, "btc_return_1h", 0)
    rel = _f(row, "rel_return_vs_btc_1h", 0)
    r24 = _f(row, "return_24h", 0)
    dist_h = _f(row, "dist_to_high_24", 0)
    own = _f(row, "return_1h", 0)

    if sess_us >= 1 or sess_eu >= 1:
        pts += 20
        support_bits.append((20, "Major market hours (EU/US) — usually more liquidity"))
    else:
        conflict_bits.append((10, "Outside peak EU/US hours — thinner liquidity possible"))

    if symbol.upper().startswith("BTC"):
        if own > 0:
            pts += 25
            support_bits.append((25, "Bitcoin is up over the last hour"))
        else:
            conflict_bits.append((20, "Bitcoin is flat or down over the last hour"))
    else:
        if btc_r > 0:
            pts += 25
            support_bits.append((25, "Bitcoin (market leader) is up this hour"))
        else:
            conflict_bits.append((20, "Bitcoin (market leader) is flat/down this hour"))
        if rel > 0:
            pts += 20
            support_bits.append((20, "This coin is outperforming Bitcoin short-term"))
        else:
            has_btc = False
            try:
                if hasattr(row, "index") and "btc_return_1h" in list(row.index):
                    has_btc = True
                elif hasattr(row, "get") and row.get("btc_return_1h") is not None:
                    has_btc = True
            except Exception:
                has_btc = False
            if has_btc:
                conflict_bits.append((15, "This coin is lagging Bitcoin short-term"))

    if r24 > 0:
        pts += 15
        support_bits.append((15, "Last 24 hours finished positive overall"))
    else:
        conflict_bits.append((10, "Last 24 hours were flat or negative"))

    if dist_h > -0.02:
        pts += 20
        support_bits.append((15, "Price is near its 24h highs"))
    else:
        conflict_bits.append((15, "Price has pulled away from its 24h high"))

    score = _clip01(pts / 120.0) * 100.0
    support_bits.sort(reverse=True)
    conflict_bits.sort(reverse=True)
    support = support_bits[0][1] if support_bits else "mixed market backdrop"
    conflict = conflict_bits[0][1] if conflict_bits else "nothing major against it"
    word = "Bullish" if score >= 62 else ("Bearish" if score <= 38 else "Mixed")
    expl = (
        f"{word} market context ({int(round(score))}/100). "
        f"In plain terms: what is the broader backdrop? Helping: {support}. "
        f"Watching: {conflict}."
    )
    return _pack(
        "Market Context",
        score,
        ["session_us", "session_europe", "btc_return_1h", "rel_return_vs_btc_1h", "return_24h", "dist_to_high_24"],
        support,
        conflict,
        expl,
    )


def build_grouped_summaries(latest_row, symbol: str = "") -> Dict[str, Any]:
    """Return all five groups plus a compact list for the API."""
    groups = [
        score_momentum(latest_row),
        score_trend(latest_row),
        score_volatility(latest_row),
        score_volume(latest_row),
        score_market_context(latest_row, symbol=symbol),
    ]
    return {
        "grouped_indicators": groups,
        "grouped_by_name": {g["group"]: g for g in groups},
    }


def build_tab_explanations(latest_row) -> Dict[str, Any]:
    """Plain-English snapshots for RSI / MACD / MA / Volume tabs."""
    rsi = _f(latest_row, "rsi_14", 50)
    if rsi < 30:
        rsi_state = "Oversold"
        rsi_hint = "Selling pressure may have gone far — rebounds can happen, but are not guaranteed."
    elif rsi > 70:
        rsi_state = "Overbought"
        rsi_hint = "Buying pressure looks stretched — pullbacks can happen, but are not guaranteed."
    else:
        rsi_state = "Healthy"
        rsi_hint = "Neither extreme overbought nor oversold — a more 'normal' momentum zone."
    slope = _f(latest_row, "rsi_slope", 0)
    rsi_expl = (
        f"RSI measures how hard price has been pushed up or down lately "
        f"(0–100). Current reading {rsi:.0f} → {rsi_state}. "
        f"{'It has been rising.' if slope > 0 else 'It has been flat or falling.'} "
        f"{rsi_hint}"
    )

    hist = _f(latest_row, "macd_histogram", 0)
    macd = _f(latest_row, "macd", 0)
    sig = _f(latest_row, "macd_signal", 0)
    if hist > 0 and macd > sig:
        macd_state = "Bullish"
        macd_hint = "Short-term momentum is stronger than the slower signal — often read as upside pressure."
    elif hist < 0 and macd < sig:
        macd_state = "Bearish"
        macd_hint = "Short-term momentum is weaker than the slower signal — often read as downside pressure."
    else:
        macd_state = "Neutral"
        macd_hint = "Lines are mixed — no clear momentum story from MACD alone."
    macd_expl = (
        f"MACD compares a fast and slow trend of price. "
        f"Right now it looks {macd_state}. {macd_hint}"
    )

    p20 = _f(latest_row, "price_vs_ema20", 0)
    p50 = _f(latest_row, "price_vs_ema50", 0)
    p100 = _f(latest_row, "price_vs_ema100", 0)
    if p20 > 0 and p50 > 0:
        ma_state = "Uptrend"
        ma_hint = "Price is riding above short and medium averages — typically a constructive path."
    elif p20 < 0 and p50 < 0:
        ma_state = "Downtrend"
        ma_hint = "Price is below short and medium averages — typically a weaker path."
    else:
        ma_state = "Mixed"
        ma_hint = "Short and medium averages disagree — trend is unclear."
    ma_expl = (
        f"Moving averages smooth price so you can see the path. "
        f"Status: {ma_state}. Price is "
        f"{'above' if p20 > 0 else 'below'} the short average, "
        f"{'above' if p50 > 0 else 'below'} the medium, and "
        f"{'above' if p100 > 0 else 'below'} the longer one. {ma_hint}"
    )

    vz = _f(latest_row, "volume_zscore", 0)
    if vz > 0.8:
        vol_state = "Strong"
        vol_hint = "Lots of participation — moves are more 'real' when volume shows up."
    elif vz < -0.5:
        vol_state = "Weak"
        vol_hint = "Quiet market — moves may reverse more easily."
    else:
        vol_state = "Normal"
        vol_hint = "Activity is roughly typical for recent hours."
    vol_expl = (
        f"Volume is how much is being traded. "
        f"Right now activity looks {vol_state} versus the recent average. {vol_hint}"
    )

    return {
        "rsi": {
            "value": round(rsi, 2),
            "state": rsi_state,
            "explanation": rsi_expl,
        },
        "macd": {
            "histogram": round(hist, 6),
            "state": macd_state,
            "explanation": macd_expl,
        },
        "moving_average": {
            "state": ma_state,
            "price_vs_ema20": round(p20, 4),
            "price_vs_ema50": round(p50, 4),
            "price_vs_ema100": round(p100, 4),
            "explanation": ma_expl,
        },
        "volume": {
            "zscore": round(vz, 3),
            "state": vol_state,
            "explanation": vol_expl,
        },
    }
