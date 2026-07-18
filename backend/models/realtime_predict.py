import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sklearn._loss

def dummy_unpickle(*args, **kwargs):
    return None

# Patch for loading older scikit-learn models
sys.modules["_loss"] = sklearn._loss
sklearn._loss.__pyx_unpickle_CyHalfMultinomialLoss = dummy_unpickle
sklearn._loss.__pyx_unpickle_HalfMultinomialLoss = dummy_unpickle
sklearn._loss.CyHalfMultinomialLoss = getattr(sklearn._loss, "HalfMultinomialLoss", None)
sklearn._loss.CyHalfBinomialLoss = getattr(sklearn._loss, "HalfBinomialLoss", None)

import pandas as pd
import numpy as np
import json
import joblib
import requests
from datetime import datetime, timezone
from collectors.binance_updater import update_hourly_data
from features.indicators import add_indicators
from features.grouped_indicators import build_grouped_summaries, build_tab_explanations
from features.decision_copy import plain_decision_reason, confirmation_label
from features.decision_support import (
    build_change_since_last,
    build_news_takeaway,
    build_price_zone_context,
    build_signal_history,
    build_signal_snapshot,
    build_what_would_change,
)

try:
    from sentiment.public_fear_greed_sentiment import (
        get_fear_greed_sentiment,
        analyze_fear_greed,
    )
except ImportError:
    def get_fear_greed_sentiment(symbol, hours=6, verbose=False):
        return 0.0
    def analyze_fear_greed(timeout=5.0):
        return {
            "fear_greed_value": 50,
            "fear_greed_label": "Neutral",
            "fear_greed_normalized": 0.0,
            "fear_greed_history": {
                "now": {"value": 50, "label": "Neutral"},
                "yesterday": None,
                "last_week": None,
                "last_month": None,
            },
            "fear_greed_trend": "unknown",
            "fear_greed_trend_plain": "Fear & Greed unavailable.",
            "fallback_used": True,
            "source": "https://api.alternative.me/fng/",
        }

try:
    from sentiment.news_sentiment import get_news_sentiment, analyze_news_sentiment
except ImportError:
    def get_news_sentiment(symbol, verbose=False):
        return 0.0
    def analyze_news_sentiment(symbol, articles=None, verbose=False):
        return {
            "news_sentiment_score": 0.0,
            "news_sentiment_label": "Neutral",
            "articles": [],
            "fallback_used": True,
        }

try:
    from sentiment.public_risk_sentiment import get_risk_sentiment, analyze_risk_sentiment
except ImportError:
    def get_risk_sentiment(symbol, verbose=False):
        return {"risk_score": 0.0, "is_high_risk": False, "risk_events": [], "risk_level": "Low"}
    def analyze_risk_sentiment(symbol, articles=None, verbose=False):
        return get_risk_sentiment(symbol)

try:
    from sentiment.decision_overlay import (
        apply_sentiment_decision_overlay,
        build_human_explanation,
    )
except ImportError:
    apply_sentiment_decision_overlay = None
    build_human_explanation = None

BINANCE_URL = "https://api.binance.com/api/v3/klines"
MODELS_DIR = Path(__file__).parent
SIGNAL_LOG_PATH = MODELS_DIR / "reports" / "signal_log.jsonl"
SIGNAL_SUMMARY_PATH = MODELS_DIR / "reports" / "signal_summary.json"
MAX_SIGNAL_LOG_ROWS = 40

# v1 defaults (Strategy B)
V1_BUY_PROB = 0.40
V1_SELL_PROB = 0.33
V1_BUY_CONFIRMS = 2
V1_SELL_CONFIRMS = 3


def _ensure_signal_log_files() -> None:
    SIGNAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SIGNAL_LOG_PATH.touch(exist_ok=True)
    SIGNAL_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)


def _read_signal_log() -> list:
    _ensure_signal_log_files()
    if not SIGNAL_LOG_PATH.exists() or SIGNAL_LOG_PATH.stat().st_size == 0:
        return []
    with SIGNAL_LOG_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_signal_log(records: list) -> None:
    _ensure_signal_log_files()
    trimmed = records[-MAX_SIGNAL_LOG_ROWS:]
    with SIGNAL_LOG_PATH.open("w", encoding="utf-8") as f:
        for record in trimmed:
            f.write(json.dumps(record) + "\n")


def _write_signal_summary(records: list) -> None:
    _ensure_signal_log_files()
    closed_records = [r for r in records if r.get("status") == "closed"]
    wins = sum(1 for r in closed_records if r.get("outcome") == "win")
    losses = sum(1 for r in closed_records if r.get("outcome") == "loss")
    pending = sum(1 for r in records if r.get("status") == "open")
    total_closed = len(closed_records)
    win_rate = round((wins / total_closed) * 100, 1) if total_closed else 0.0
    summary = {
        "total_signals": len(records),
        "closed_signals": total_closed,
        "open_signals": pending,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    with SIGNAL_SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def _close_last_open_signal(symbol: str, current_close: float) -> None:
    records = _read_signal_log()
    if not records:
        return
    for record in reversed(records):
        if record.get("symbol") != symbol or record.get("status") != "open":
            continue
        entry_close = record.get("entry_close")
        if entry_close is None:
            break
        pnl = ((current_close - entry_close) / entry_close) if entry_close else None
        decision = record.get("decision", "HOLD")
        outcome = None
        if decision == "BUY" and pnl is not None:
            outcome = "win" if pnl > 0 else "loss"
        elif decision == "SELL" and pnl is not None:
            outcome = "win" if pnl < 0 else "loss"
        record["status"] = "closed"
        record["outcome"] = outcome
        record["pnl"] = round(float(pnl), 6) if pnl is not None else None
        record["close_price"] = round(float(current_close), 6)
        record["closed_at"] = datetime.now(timezone.utc).isoformat()
        break
    _write_signal_log(records)
    _write_signal_summary(records)


def _append_signal_log_entry(entry: dict) -> None:
    records = _read_signal_log()
    records.append(entry)
    _write_signal_log(records)
    _write_signal_summary(records)


def _last_snapshot_for_symbol(symbol: str):
    records = _read_signal_log()
    for r in reversed(records):
        if str(r.get("symbol", "")).upper() == str(symbol).upper():
            return r
    return None


def _model_paths(symbol: str, model_version: str) -> dict:
    if model_version == "v2":
        base = MODELS_DIR / "saved_v2"
        return {
            "model": base / f"{symbol}_model.pkl",
            "features": base / f"{symbol}_features.json",
            "calibrator": base / f"{symbol}_calibrator.pkl",
            "thresholds": base / f"{symbol}_thresholds.json",
            "manifest": base / f"{symbol}_manifest.json",
        }
    base = MODELS_DIR / "saved"
    return {
        "model": base / f"{symbol}_model.pkl",
        "features": base / f"{symbol}_features.json",
        "calibrator": None,
        "thresholds": None,
        "manifest": None,
    }


def _load_thresholds(paths: dict, model_version: str, symbol: str = "") -> dict:
    if model_version == "v2" and paths["thresholds"] and paths["thresholds"].exists():
        with open(paths["thresholds"]) as f:
            data = json.load(f)
        policy = data.get("default_policy", "balanced")
        thr = data.get(policy, data.get("balanced", {}))
        return {
            "buy_prob": float(thr.get("buy_prob", 0.40)),
            "sell_prob": float(thr.get("sell_prob", 0.40)),
            "buy_confirms": int(thr.get("buy_confirms", 2)),
            "sell_confirms": int(thr.get("sell_confirms", 3)),
            "policy": policy,
        }
    # v1 defaults — SOL uses lighter confirmations (model-led) until overnight
    # training validates a better asset-specific policy.
    if str(symbol).upper().startswith("SOL"):
        return {
            "buy_prob": V1_BUY_PROB,
            "sell_prob": V1_SELL_PROB,
            "buy_confirms": 1,
            "sell_confirms": 2,
            "policy": "strategy_b_v1_sol_light",
        }
    return {
        "buy_prob": V1_BUY_PROB,
        "sell_prob": V1_SELL_PROB,
        "buy_confirms": V1_BUY_CONFIRMS,
        "sell_confirms": V1_SELL_CONFIRMS,
        "policy": "strategy_b_v1",
    }


def _btc_eth_context(df: pd.DataFrame, symbol: str):
    """Attach aligned BTC/ETH closes for v2 cross-asset features when needed."""
    btc_close = eth_close = None
    if symbol == "BTCUSDT":
        return btc_close, eth_close
    try:
        btc_df = update_hourly_data("BTCUSDT")
        btc_df["timestamp"] = pd.to_datetime(btc_df["timestamp"], utc=True)
        merged = pd.merge(
            df[["timestamp"]],
            btc_df[["timestamp", "close"]].rename(columns={"close": "_btc"}),
            on="timestamp",
            how="left",
        )
        btc_close = merged["_btc"]
    except Exception as e:
        print(f"  Warning: BTC context unavailable: {e}")
    if symbol == "SOLUSDT":
        try:
            eth_df = update_hourly_data("ETHUSDT")
            eth_df["timestamp"] = pd.to_datetime(eth_df["timestamp"], utc=True)
            merged = pd.merge(
                df[["timestamp"]],
                eth_df[["timestamp", "close"]].rename(columns={"close": "_eth"}),
                on="timestamp",
                how="left",
            )
            eth_close = merged["_eth"]
        except Exception as e:
            print(f"  Warning: ETH context unavailable: {e}")
    return btc_close, eth_close


def _badge_from_reasons(
    final_decision,
    raw_decision,
    reasons,
    is_high_risk,
    confirmation_score,
    thr,
    confidence: float = 0.0,
    confidence_label: str = "Standard",
    sentiment_impact: str = "none",
) -> str:
    """User-facing decision badge (no generic 'Low Confidence')."""
    if is_high_risk and (raw_decision == "BUY" or "risk_override" in reasons):
        if final_decision == "HOLD":
            return "BUY Blocked — High Risk"

    if final_decision == "BUY":
        if confidence >= 0.55 or confidence_label in ("Elevated",):
            return "High-Confidence BUY"
        return "Moderate BUY"

    if final_decision == "SELL":
        if confidence >= 0.55 or confidence_label in ("Elevated",):
            return "High-Confidence SELL"
        return "Moderate SELL"

    # HOLD variants
    if "insufficient_confirmations" in reasons:
        return "HOLD — Insufficient Evidence"
    if sentiment_impact == "conflicting_sentiment_penalty" or any(
        x in reasons for x in ("low_buy_confidence", "low_sell_confidence")
    ):
        return "HOLD — Conflicting Signals"
    if any(str(r).startswith("low_model_confidence") for r in reasons):
        return "HOLD — Insufficient Evidence"
    if raw_decision in ("BUY", "SELL") and final_decision == "HOLD":
        return "HOLD — Conflicting Signals"
    return "HOLD — Insufficient Evidence"


def _build_confirmation_checks(raw_decision: str, latest_row) -> list:
    """Six technical checks with Passed / Failed / Not Available for the UI.

    Labels match the dashboard chip names. Status uses the same thresholds as
    Strategy B BUY confirmations so Passed/Failed stay interpretable.
    """
    def _num(key, default=None):
        try:
            v = latest_row.get(key, default)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
            return float(v)
        except Exception:
            return None

    momentum = _num("momentum_agreement")
    rsi = _num("rsi_14")
    rsi_slope = _num("rsi_slope")
    macd_hist = _num("macd_histogram")
    vol_z = _num("volume_zscore")
    vpm = _num("volume_price_momentum")

    def status(value, ok_fn):
        if value is None:
            return "Not Available"
        return "Passed" if ok_fn(value) else "Failed"

    _ = raw_decision  # reserved for future side-specific chips
    specs = [
        ("momentum", "Momentum Agreement", status(momentum, lambda m: m >= 0.6)),
        ("rsi_healthy", "RSI Healthy", status(rsi, lambda r: 45 < r < 75)),
        ("rsi_rising", "RSI Rising", status(rsi_slope, lambda s: s > 0)),
        ("macd", "MACD", status(macd_hist, lambda h: h > 0)),
        ("volume", "Volume", status(vol_z, lambda z: z > 0.3)),
        ("price_volume", "Price-Volume Momentum", status(vpm, lambda v: v > 0)),
    ]
    return [
        {"id": cid, "label": confirmation_label(cid, fallback), "status": st}
        for cid, fallback, st in specs
    ]


def _rejection_reason(final_decision, raw_decision, reasons, is_high_risk) -> str:
    if final_decision in ("BUY", "SELL"):
        return "accepted"
    if is_high_risk and raw_decision == "BUY":
        return "high_risk_buy_blocked"
    if "insufficient_confirmations" in reasons:
        return "insufficient_confirmations"
    if "low_buy_confidence" in reasons:
        return "low_buy_confidence"
    for r in reasons:
        if r.startswith("low_model_confidence"):
            return "low_model_confidence"
    if raw_decision == "HOLD":
        return "model_predicted_hold"
    return "filtered_to_hold"


def predict(symbol: str = "BTCUSDT", model_version: str = "v1") -> dict:
    """
    Real-time prediction with multi-signal confirmation.

    model_version: 'v1' (production default) or 'v2' (only after overnight
    training + finalize_after_training -EnableV2). Falls back to v1 if v2
    artifacts are missing.
    """
    requested_version = model_version
    paths = _model_paths(symbol, model_version)
    if model_version == "v2" and not paths["model"].exists():
        print(f"  v2 model missing for {symbol}; falling back to v1")
        model_version = "v1"
        paths = _model_paths(symbol, "v1")

    df = update_hourly_data(symbol)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    try:
        params = {"symbol": symbol, "interval": "1h", "limit": 2}
        r = requests.get(BINANCE_URL, params=params, timeout=10)
        data = r.json()
        if len(data) >= 2:
            candles_to_append = []
            for candle in data[-2:]:
                candles_to_append.append(
                    {
                        "timestamp": pd.to_datetime(candle[0], unit="ms", utc=True),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                    }
                )
            df = pd.concat([df, pd.DataFrame(candles_to_append)], ignore_index=True)
            df = df.drop_duplicates(subset="timestamp", keep="last")
            df = df.sort_values("timestamp").reset_index(drop=True)
    except Exception as e:
        print(f"  Warning: Failed to fetch live candles for {symbol}: {e}")

    btc_close = eth_close = None
    if model_version == "v2":
        btc_close, eth_close = _btc_eth_context(df, symbol)
    df = add_indicators(df, btc_close=btc_close, eth_close=eth_close)

    try:
        model = joblib.load(paths["model"])
    except FileNotFoundError:
        print(f"  ERROR: Model not found for {symbol} ({model_version}).")
        return None

    try:
        with open(paths["features"], "r") as f:
            saved_features = json.load(f)
    except FileNotFoundError:
        print(f"  ERROR: Feature list not found for {symbol}.")
        return None

    calibrator = None
    if model_version == "v2" and paths["calibrator"] and paths["calibrator"].exists():
        try:
            calibrator = joblib.load(paths["calibrator"])
        except Exception as e:
            print(f"  Warning: could not load calibrator: {e}")

    thr = _load_thresholds(paths, model_version, symbol=symbol)

    missing_features = set(saved_features) - set(df.columns)
    if missing_features:
        print(f"  ERROR: Missing features for {symbol}: {missing_features}")
        if model_version == "v2":
            print("  Falling back to v1...")
            return predict(symbol, model_version="v1")
        return None

    latest_row = df.iloc[-1]
    X = pd.DataFrame([latest_row[saved_features]])

    # Rich sentiment / F&G / risk (never crash prediction)
    try:
        news_pack = analyze_news_sentiment(symbol, verbose=False)
    except Exception:
        news_pack = {
            "news_sentiment_score": 0.0,
            "news_sentiment_label": "Neutral",
            "articles": [],
            "fallback_used": True,
        }
    try:
        fg_pack = analyze_fear_greed()
    except Exception:
        fg_pack = {
            "fear_greed_value": 50,
            "fear_greed_label": "Neutral",
            "fear_greed_normalized": 0.0,
            "fallback_used": True,
        }
    try:
        # Reuse fetched news articles for risk when available
        risk_pack = analyze_risk_sentiment(
            symbol,
            articles=None,  # separate fetch OK; analyze_risk also safe
            verbose=False,
        )
    except Exception:
        risk_pack = {
            "risk_score": 0.0,
            "risk_level": "Low",
            "is_high_risk": False,
            "risk_events": [],
            "fallback_used": True,
        }

    news_sentiment = float(news_pack.get("news_sentiment_score", 0.0))
    fear_greed_index = float(fg_pack.get("fear_greed_normalized", 0.0))
    fear_greed_value = int(fg_pack.get("fear_greed_value", 50))
    fear_greed_label = fg_pack.get("fear_greed_label", "Neutral")
    news_sentiment_label = news_pack.get("news_sentiment_label", "Neutral")
    risk_score = float(risk_pack.get("risk_score", 0.0))
    is_high_risk = bool(risk_pack.get("is_high_risk", False))
    risk_events = risk_pack.get("risk_events", []) or []
    risk_level = risk_pack.get("risk_level", "Low")
    combined_sentiment = (fear_greed_index + news_sentiment) / 2.0

    predictor = calibrator if calibrator is not None else model
    y_pred = predictor.predict(X)[0]
    y_proba = predictor.predict_proba(X)[0]
    classes = list(predictor.classes_)

    def class_prob(label):
        if label in classes:
            return float(y_proba[list(classes).index(label)])
        return 0.0

    prob_sell = class_prob(0)
    prob_buy = class_prob(1)
    prob_hold = class_prob(2)
    raw_decision = ["SELL", "BUY", "HOLD"][int(y_pred)]
    max_prob = max(prob_sell, prob_buy, prob_hold)

    momentum_score = latest_row.get("momentum_agreement", 0.5)
    rsi = latest_row.get("rsi_14", 50)
    rsi_slope = latest_row.get("rsi_slope", 0)
    macd_hist = latest_row.get("macd_histogram", 0)
    vol_zscore = latest_row.get("volume_zscore", 0)
    vpm = latest_row.get("volume_price_momentum", 0)

    confirmation_score = 0
    confirmation_reasons = []
    final_decision = raw_decision

    if raw_decision == "BUY" and prob_buy >= thr["buy_prob"]:
        checks = [
            ("momentum_agree", momentum_score >= 0.6),
            ("rsi_healthy", 45 < rsi < 75),
            ("rsi_rising", rsi_slope > 0),
            ("macd_bullish", macd_hist > 0),
            ("volume_up", vol_zscore > 0.3),
            ("vol_price_momentum", vpm > 0),
        ]
        for name, ok in checks:
            if ok:
                confirmation_score += 1
                confirmation_reasons.append(name)
        if confirmation_score < thr["buy_confirms"]:
            final_decision = "HOLD"
            confirmation_reasons.append("insufficient_confirmations")
        if prob_buy < thr["buy_prob"]:
            final_decision = "HOLD"
            confirmation_reasons.append("low_buy_confidence")
    elif raw_decision == "SELL" and prob_sell >= thr["sell_prob"]:
        checks = [
            ("momentum_bearish", momentum_score <= 0.4),
            ("rsi_weak", 20 < rsi < 55),
            ("rsi_falling", rsi_slope < 0),
            ("macd_bearish", macd_hist < 0),
            ("volume_up", vol_zscore > 0.3),
            ("vol_price_momentum_neg", vpm < 0),
        ]
        for name, ok in checks:
            if ok:
                confirmation_score += 1
                confirmation_reasons.append(name)
        if confirmation_score < thr["sell_confirms"]:
            final_decision = "HOLD"
            confirmation_reasons.append("insufficient_confirmations")
    else:
        final_decision = "HOLD"
        if raw_decision == "BUY" and prob_buy < thr["buy_prob"]:
            confirmation_reasons.append("low_buy_confidence")
        elif raw_decision == "SELL" and prob_sell < thr["sell_prob"]:
            confirmation_reasons.append("low_sell_confidence")
        else:
            confirmation_reasons.append(f"low_model_confidence_{max_prob:.2f}")

    risk_override = False
    after_conf = final_decision
    if final_decision == "HOLD":
        confidence = max_prob
    else:
        confidence = max(prob_sell, prob_buy)

    sentiment_alignment = "unknown"
    sentiment_impact = "none"
    confidence_label = "Standard"
    if apply_sentiment_decision_overlay is not None:
        overlay = apply_sentiment_decision_overlay(
            raw_decision=raw_decision,
            final_after_confirmations=after_conf,
            confidence=confidence,
            news_score=news_sentiment,
            fear_greed_norm=fear_greed_index,
            risk_score=risk_score,
            is_high_risk=is_high_risk,
            risk_level=risk_level,
            confirmation_reasons=confirmation_reasons,
        )
        final_decision = overlay["final_decision"]
        confidence = overlay["confidence"]
        confirmation_reasons = overlay["confirmation_reasons"]
        risk_override = bool(overlay.get("risk_blocked_buy", False))
        sentiment_alignment = overlay["sentiment_alignment"]
        sentiment_impact = overlay["sentiment_impact"]
        confidence_label = overlay["confidence_label"]
    elif final_decision == "BUY" and is_high_risk:
        final_decision = "HOLD"
        risk_override = True
        confirmation_reasons.append("risk_override")

    strategy_badge = _badge_from_reasons(
        final_decision,
        raw_decision,
        confirmation_reasons,
        is_high_risk,
        confirmation_score,
        thr,
        confidence=float(confidence),
        confidence_label=confidence_label,
        sentiment_impact=sentiment_impact,
    )
    rejection_reason = _rejection_reason(
        final_decision, raw_decision, confirmation_reasons, is_high_risk
    )
    confirmation_checks = _build_confirmation_checks(raw_decision, latest_row)

    try:
        grouped_pack = build_grouped_summaries(latest_row, symbol=symbol)
        tab_explanations = build_tab_explanations(latest_row)
    except Exception as e:
        print(f"  Warning: grouped indicators failed: {e}")
        grouped_pack = {"grouped_indicators": [], "grouped_by_name": {}}
        tab_explanations = {}

    sorted_probs = sorted([prob_buy, prob_sell, prob_hold], reverse=True)
    probability_margin = float(sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) >= 2 else 0.0

    passed_checks = [c["label"] for c in confirmation_checks if c.get("status") == "Passed"]
    failed_checks = [c["label"] for c in confirmation_checks if c.get("status") == "Failed"]
    # Display score always reflects chip Pass count (policy score kept in confirmation_score_policy)
    confirmation_score_policy = confirmation_score
    confirmation_score = len(passed_checks)

    top_articles = (news_pack.get("articles") or [])[:3]
    human_explanation = ""
    if build_human_explanation is not None:
        human_explanation = build_human_explanation(
            raw_decision=raw_decision,
            final_decision=final_decision,
            confirmation_reasons=confirmation_reasons,
            confirmation_score=confirmation_score,
            news_label=news_sentiment_label,
            news_score=news_sentiment,
            fg_label=fear_greed_label,
            fg_value=fear_greed_value,
            risk_level=risk_level,
            risk_events=risk_events,
            sentiment_impact=sentiment_impact,
            confidence_label=confidence_label,
            prob_buy=float(prob_buy),
            prob_sell=float(prob_sell),
            prob_hold=float(prob_hold),
        )

    current_close = float(latest_row.get("close", 0.0))
    _close_last_open_signal(symbol, current_close)

    snapshot = build_signal_snapshot(
        symbol=symbol,
        raw_decision=raw_decision,
        final_decision=final_decision,
        confidence=confidence,
        confirmation_score=confirmation_score,
        fear_greed_value=fear_greed_value,
        fear_greed_label=fear_greed_label,
        news_label=news_sentiment_label,
        news_score=news_sentiment,
        risk_level=risk_level,
        grouped_indicators=grouped_pack.get("grouped_indicators", []),
    )
    previous_snap = _last_snapshot_for_symbol(symbol)
    change_since = build_change_since_last(snapshot, previous_snap)
    prior_records = _read_signal_log()

    log_entry = {
        **snapshot,
        "decision": final_decision,
        "strategy_badge": strategy_badge,
        "reasons": confirmation_reasons,
        "entry_close": round(current_close, 6),
        "model_version": model_version,
        "status": "open",
        "outcome": None,
        "pnl": None,
        "close_price": None,
        "closed_at": None,
    }
    _append_signal_log_entry(log_entry)

    what_would_change = build_what_would_change(
        raw_decision=raw_decision,
        final_decision=final_decision,
        prob_buy=float(prob_buy),
        prob_sell=float(prob_sell),
        prob_hold=float(prob_hold),
        confirmation_score=confirmation_score,
        confirmation_checks=confirmation_checks,
        thr=thr,
        is_high_risk=is_high_risk,
        risk_level=risk_level,
    )
    price_zone = build_price_zone_context(latest_row)
    news_takeaway = build_news_takeaway(
        news_sentiment_label,
        news_sentiment,
        risk_level,
        risk_events,
        is_high_risk,
    )
    signal_history = build_signal_history(
        prior_records + [log_entry], symbol=symbol, limit=5
    )

    result = {
        "asset": symbol,
        "symbol": symbol,
        "model_version": model_version,
        "model_display_name": (
            "Production model — live"
            if model_version == "v1"
            else "Updated model — live"
        ),
        "requested_model_version": requested_version,
        "prediction_horizon": "1h",
        "horizon_hours": 1,
        "model_decision": raw_decision,
        "raw_prediction": raw_decision,
        "raw_model_outlook": raw_decision,
        "final_decision": final_decision,
        "confidence": round(float(confidence), 3),
        "confidence_label": confidence_label,
        "probability_margin": round(probability_margin, 3),
        "prob_sell": round(float(prob_sell), 3),
        "prob_buy": round(float(prob_buy), 3),
        "prob_hold": round(float(prob_hold), 3),
        "calibrated_probabilities": {
            "SELL": round(float(prob_sell), 3),
            "BUY": round(float(prob_buy), 3),
            "HOLD": round(float(prob_hold), 3),
        },
        "fear_greed_index": round(float(fear_greed_index), 3),
        "fear_greed_value": fear_greed_value,
        "fear_greed_label": fear_greed_label,
        "fear_greed_history": fg_pack.get("fear_greed_history"),
        "fear_greed_trend": fg_pack.get("fear_greed_trend", "unknown"),
        "fear_greed_trend_plain": fg_pack.get("fear_greed_trend_plain"),
        "fear_greed_source": fg_pack.get("source", "https://api.alternative.me/fng/"),
        "fear_greed_updated": fg_pack.get("fear_greed_updated"),
        "news_sentiment": round(float(news_sentiment), 3),
        "news_sentiment_score": round(float(news_sentiment), 3),
        "news_sentiment_label": news_sentiment_label,
        "news_takeaway": news_takeaway,
        "combined_sentiment": round(float(combined_sentiment), 3),
        "sentiment": round(float(combined_sentiment), 3),
        "risk_score": round(float(risk_score), 3),
        "risk_level": risk_level,
        "is_high_risk": is_high_risk,
        "risk_events": risk_events,
        "risk_event_count": len(risk_events or []),
        "risk_override": risk_override,
        "sentiment_alignment": sentiment_alignment,
        "sentiment_impact": sentiment_impact,
        "human_readable_explanation": human_explanation,
        "decision_reason": plain_decision_reason(rejection_reason),
        "decision_reason_code": rejection_reason,
        "top_headlines": [
            {
                "title": a.get("title"),
                "source": a.get("source"),
                "age_hours": a.get("age_hours"),
                "vader_compound": a.get("vader_compound"),
            }
            for a in top_articles
        ],
        "confirmation_score": confirmation_score,
        "confirmation_score_policy": confirmation_score_policy,
        "confirmation_reasons": confirmation_reasons,
        "confirmation_checks": confirmation_checks,
        "passed_confirmations": passed_checks,
        "failed_confirmations": failed_checks,
        "grouped_indicators": grouped_pack.get("grouped_indicators", []),
        "grouped_by_name": grouped_pack.get("grouped_by_name", {}),
        "tab_explanations": tab_explanations,
        "rejection_reason": rejection_reason,
        "acceptance_reason": rejection_reason if final_decision in ("BUY", "SELL") else None,
        "decision_thresholds": thr,
        "strategy_badge": strategy_badge,
        "what_would_change": what_would_change,
        "change_since_last": change_since,
        "signal_history": signal_history,
        "price_zone_context": price_zone,
        "signal_log_path": str(SIGNAL_LOG_PATH),
        "signal_summary_path": str(SIGNAL_SUMMARY_PATH),
    }

    # Forward-evaluation log (as-of sentiment/risk for future ablation)
    try:
        from models.forward_eval_logger import append_forward_record, build_record_from_prediction

        candle_ts = latest_row.get("timestamp", datetime.now(timezone.utc))
        thr_val = 0.002 if symbol == "SOLUSDT" else 0.0015
        append_forward_record(
            build_record_from_prediction(result, candle_ts, current_close, threshold=thr_val)
        )
        result["forward_eval_log"] = str(
            Path(__file__).parent / "reports" / "forward_eval_log.jsonl"
        )
    except Exception as e:
        print(f"  Warning: forward eval log failed: {e}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CryptoBuddy realtime predictor")
    parser.add_argument(
        "--model-version",
        choices=["v1", "v2"],
        default="v2",
        help="Model artifact version (default: v2, falls back to v1)",
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Single symbol (default: run BTC/ETH/SOL)",
    )
    args = parser.parse_args()

    print(f"\n{'=' * 70}")
    print(f"REAL-TIME PREDICTION (model-version={args.model_version})")
    print(f"{'=' * 70}\n")

    coins = [args.symbol] if args.symbol else ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    for coin in coins:
        result = predict(coin, model_version=args.model_version)
        if result is None:
            continue
        print(f"\n{result['symbol']:10s} | {result['final_decision']:4s} | "
              f"Confirms: {result['confirmation_score']}/6 | v={result['model_version']}")
        print(f"  Badge: {result['strategy_badge']}")
        print(
            f"  Raw: {result['raw_prediction']} "
            f"(SELL={result['prob_sell']:.3f}, BUY={result['prob_buy']:.3f}, HOLD={result['prob_hold']:.3f})"
        )
        print(f"  Reason: {result['rejection_reason']}")
        print(
            f"  Sentiment: FearGreed={result['fear_greed_index']:.3f}, "
            f"News={result['news_sentiment']:.3f}"
        )
        print(
            f"  Risk: score={result['risk_score']:.3f}, "
            f"high_risk={result['is_high_risk']}"
        )
    print(f"\n{'=' * 70}\n")
