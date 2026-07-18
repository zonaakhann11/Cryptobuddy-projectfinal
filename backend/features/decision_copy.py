"""
Human-friendly copy for the decision-support layer.

Internal codes stay machine-stable; UI/report text comes from these maps.
"""
from __future__ import annotations

from typing import Optional

REASON_PLAIN = {
    "accepted": (
        "The model outlook and enough technical checks agree, "
        "so this directional suggestion is shown."
    ),
    "insufficient_confirmations": (
        "Not enough technical checks agree with the model, "
        "so the suggestion stays HOLD — wait for clearer evidence."
    ),
    "low_buy_confidence": (
        "The model leans BUY, but its BUY probability is too weak "
        "to recommend acting — suggestion stays HOLD."
    ),
    "low_model_confidence": (
        "The model is not confident enough in a direction, "
        "so the suggestion stays HOLD."
    ),
    "high_risk_buy_blocked": (
        "A high-risk market or news context was detected, "
        "so a BUY suggestion was blocked — suggestion stays HOLD."
    ),
    "model_predicted_hold": (
        "The model itself sees no clear next-hour move (HOLD). "
        "That is a valid outcome — sitting out can be the cautious choice."
    ),
    "filtered_to_hold": (
        "Filters did not find enough agreement for BUY or SELL, "
        "so the suggestion stays HOLD."
    ),
}

CONFIRMATION_LABELS = {
    "momentum": "Short-term momentum agrees",
    "rsi_healthy": "RSI in a healthy zone",
    "rsi_rising": "RSI is rising",
    "macd": "MACD supports upside",
    "volume": "Trading volume is active",
    "price_volume": "Price and volume move together",
}

GROUP_PLAIN = {
    "Momentum": "Is recent price strength building or fading?",
    "Trend": "Is price above or below its recent average path?",
    "Volatility": "Is the market calm or unusually jumpy right now?",
    "Volume": "Are traders participating, or is the move thin?",
    "Market Context": "What is the broader crypto backdrop (session / BTC)?",
}


def plain_decision_reason(code: Optional[str]) -> str:
    if not code:
        return "Run Predict to see why this suggestion was formed."
    return REASON_PLAIN.get(code, str(code).replace("_", " "))


def confirmation_label(check_id: str, fallback: str) -> str:
    return CONFIRMATION_LABELS.get(check_id, fallback)
