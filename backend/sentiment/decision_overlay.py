"""
Sentiment / risk overlay on model decisions.

Rules (documented):
- Sentiment never invents BUY/SELL from HOLD.
- Mild disagreement does not force HOLD.
- Strong aligned sentiment may raise confidence label.
- Strong conflict may lower confidence label.
- High/Critical risk may block BUY only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def apply_sentiment_decision_overlay(
    raw_decision: str,
    final_after_confirmations: str,
    confidence: float,
    news_score: float,
    fear_greed_norm: float,
    risk_score: float,
    is_high_risk: bool,
    risk_level: str,
    confirmation_reasons: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Adjust final decision / confidence narrative after technical confirmations.

    Returns keys used by API + dashboard explanations.
    """
    confirmation_reasons = list(confirmation_reasons or [])
    decision = final_after_confirmations
    conf = float(confidence)
    impact = "none"
    alignment = "neutral"
    reasons = []

    # Alignment vs directional final (or raw if still directional before filters)
    ref = decision if decision in ("BUY", "SELL") else raw_decision
    combined = 0.6 * news_score + 0.4 * fear_greed_norm

    if ref == "BUY":
        if combined >= 0.15:
            alignment = "aligned_bullish"
        elif combined <= -0.25:
            alignment = "conflicting_bearish"
        else:
            alignment = "mild_or_neutral"
    elif ref == "SELL":
        if combined <= -0.15:
            alignment = "aligned_bearish"
        elif combined >= 0.25:
            alignment = "conflicting_bullish"
        else:
            alignment = "mild_or_neutral"
    else:
        alignment = "n/a_hold"

    # Risk guard: block BUY only
    risk_blocked = False
    if decision == "BUY" and (is_high_risk or risk_level in ("High", "Critical") or risk_score >= 0.5):
        decision = "HOLD"
        risk_blocked = True
        impact = "buy_blocked_by_risk"
        reasons.append("BUY blocked by high-risk event")
        confirmation_reasons.append("risk_override")

    # Sentiment never creates directional signal from HOLD
    if raw_decision == "HOLD" or final_after_confirmations == "HOLD":
        if not risk_blocked:
            impact = impact if impact != "none" else "no_directional_override"
        # keep HOLD
        if decision != "HOLD" and final_after_confirmations == "HOLD":
            decision = "HOLD"

    # Confidence adjustments (labels only; do not flip strong decisions on mild news)
    confidence_label = "Standard"
    if decision in ("BUY", "SELL"):
        if alignment.startswith("aligned") and abs(combined) >= 0.20:
            conf = min(0.99, conf + 0.05)
            confidence_label = "Elevated"
            impact = "aligned_sentiment_boost"
            reasons.append("Sentiment aligned with model direction")
        elif alignment.startswith("conflicting") and abs(combined) >= 0.35:
            # Strong conflict: reduce confidence label, do NOT auto-HOLD on mild
            conf = max(0.05, conf - 0.08)
            confidence_label = "Reduced"
            impact = "conflicting_sentiment_penalty"
            reasons.append("Sentiment conflicts with model direction")
        elif alignment == "mild_or_neutral" or (
            alignment.startswith("conflicting") and abs(combined) < 0.35
        ):
            confidence_label = "Moderate"
            if impact == "none":
                impact = "mild_sentiment_no_flip"
            reasons.append("Mild sentiment disagreement did not force HOLD")

    if risk_blocked:
        confidence_label = "Blocked"
        conf = min(conf, 0.5)

    return {
        "final_decision": decision,
        "confidence": round(conf, 3),
        "confidence_label": confidence_label,
        "sentiment_alignment": alignment,
        "sentiment_impact": impact,
        "sentiment_combined_score": round(combined, 3),
        "risk_blocked_buy": risk_blocked,
        "overlay_reasons": reasons,
        "confirmation_reasons": confirmation_reasons,
    }


def build_human_explanation(
    raw_decision: str,
    final_decision: str,
    confirmation_reasons: List[str],
    confirmation_score: int,
    news_label: str,
    news_score: float,
    fg_label: str,
    fg_value: int,
    risk_level: str,
    risk_events: List[str],
    sentiment_impact: str,
    confidence_label: str,
    prob_buy: float = 0.0,
    prob_sell: float = 0.0,
    prob_hold: float = 0.0,
) -> str:
    """Plain-language decision-support narrative for the dashboard / report."""
    probs_txt = (
        f"Model lean: BUY {prob_buy * 100:.0f}%, "
        f"SELL {prob_sell * 100:.0f}%, HOLD {prob_hold * 100:.0f}%."
    )
    side = str(raw_decision or "").upper()
    side_word = "BUY-side" if side == "BUY" else "SELL-side" if side == "SELL" else "technical"
    checks_txt = f"{confirmation_score} of 6 {side_word} technical checks currently agree."

    if final_decision == "HOLD" and sentiment_impact == "buy_blocked_by_risk":
        ev = risk_events[0] if risk_events else "a high-risk news or market event"
        return (
            f"Suggested action: HOLD. The model briefly leaned {raw_decision}, "
            f"but a high-risk context was detected ({risk_level}). "
            f"Example: {ev}. We block BUY suggestions in that case so you can "
            f"re-check safely. {probs_txt} News mood: {news_label}. "
            f"Fear & Greed: {fg_label} ({fg_value})."
        )

    if final_decision == "HOLD":
        reasons = confirmation_reasons or []
        if raw_decision == "HOLD":
            why = (
                f"the model itself sees no clear next-hour move "
                f"(HOLD is the top class at {prob_hold * 100:.0f}% — "
                f"BUY {prob_buy * 100:.0f}%, SELL {prob_sell * 100:.0f}%). "
                f"Bullish evidence groups or {confirmation_score}/6 snapshot checks "
                f"are context only; they do not unlock BUY while outlook is HOLD"
            )
        elif "low_buy_confidence" in reasons or "low_sell_confidence" in reasons:
            why = (
                f"the model leaned {raw_decision}, but its {raw_decision} "
                f"probability was below the action threshold"
            )
        elif "insufficient_confirmations" in reasons:
            why = (
                f"the model leaned {raw_decision}, but not enough {side_word} "
                f"technical checks agreed ({checks_txt})"
            )
        else:
            why = (
                f"the model leaned {raw_decision}, but filters did not confirm "
                f"a clear action ({checks_txt})"
            )
        return (
            f"Suggested action: HOLD — {why}. "
            f"{probs_txt} News mood: {news_label}. "
            f"Fear & Greed: {fg_label} ({fg_value}). Risk: {risk_level}. "
            f"HOLD means 'not enough clear evidence to act' — you still decide."
        )

    align_bit = ""
    if sentiment_impact == "aligned_sentiment_boost":
        align_bit = f" News mood ({news_label}) roughly supports this lean."
    elif sentiment_impact == "conflicting_sentiment_penalty":
        align_bit = (
            f" News mood ({news_label}) conflicts with the model, "
            f"so confidence is marked {confidence_label}."
        )
    elif sentiment_impact == "mild_sentiment_no_flip":
        align_bit = (
            f" News mood ({news_label}) mildly disagrees, but did not flip the suggestion."
        )
    else:
        align_bit = f" News mood: {news_label}."

    return (
        f"Suggested action: {final_decision} "
        f"(model outlook was {raw_decision}). {checks_txt} {probs_txt}"
        f"{align_bit} Fear & Greed: {fg_label} ({fg_value}). "
        f"Risk: {risk_level}. This is decision support — not an order to trade."
    )
