import ta
import pandas as pd
import numpy as np


def add_indicators(df: pd.DataFrame, btc_close: pd.Series | None = None,
                   eth_close: pd.Series | None = None) -> pd.DataFrame:
    """
    Comprehensive technical indicators for 1-hour crypto prediction.

    All rolling / lag operations are backward-looking (no future peeking).
    Optional btc_close / eth_close series must be aligned by timestamp and
    already known at time t (market context features).
    """
    df = df.copy()

    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)

    # ===== RSI (Momentum - Multiple Timeframes) =====
    df["rsi_7"] = ta.momentum.RSIIndicator(df["close"], window=7).rsi()
    df["rsi_14"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["rsi_21"] = ta.momentum.RSIIndicator(df["close"], window=21).rsi()
    df["rsi_slope"] = df["rsi_14"].diff(3)

    # ===== MACD (Trend Momentum) =====
    macd_obj = ta.trend.MACD(df["close"], window_fast=12, window_slow=26, window_sign=9)
    df["macd"] = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()
    df["macd_histogram"] = macd_obj.macd_diff()
    df["macd_hist_slope"] = df["macd_histogram"].diff(2)

    # ===== Bollinger Bands (Volatility & Position) =====
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / (df["bb_mid"] + 1e-9)
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"] + 1e-9)
    # Percentile of bb_position over trailing window (backward-looking)
    df["bb_position_pctile"] = df["bb_position"].rolling(48, min_periods=12).rank(pct=True)

    # ===== Stochastic Oscillator =====
    stoch = ta.momentum.StochasticOscillator(
        df["high"], df["low"], df["close"], window=14, smooth_window=3
    )
    df["stoch_k"] = stoch.stoch()
    df["stoch_d"] = stoch.stoch_signal()
    df["stoch_diff"] = df["stoch_k"] - df["stoch_d"]

    # ===== ATR (Volatility Context) =====
    atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14)
    df["atr"] = atr.average_true_range()
    df["atr_pct"] = df["atr"] / (df["close"] + 1e-9)
    df["atr_pctile"] = df["atr_pct"].rolling(96, min_periods=24).rank(pct=True)

    # ===== Multi-Horizon Returns =====
    df["return_1h"] = df["close"].pct_change(1)
    df["return_2h"] = df["close"].pct_change(2)
    df["return_3h"] = df["close"].pct_change(3)
    df["return_6h"] = df["close"].pct_change(6)
    df["return_12h"] = df["close"].pct_change(12)
    df["return_24h"] = df["close"].pct_change(24)
    df["return_48h"] = df["close"].pct_change(48)

    # Log returns (backward-looking)
    log_ret = np.log(df["close"] / df["close"].shift(1))
    df["log_return_1h"] = log_ret
    df["log_return_6h"] = np.log(df["close"] / df["close"].shift(6))
    df["log_return_24h"] = np.log(df["close"] / df["close"].shift(24))

    # ===== Rolling Volatility =====
    df["volatility_3h"] = df["close"].pct_change().rolling(3).std()
    df["volatility_6h"] = df["close"].pct_change().rolling(6).std()
    df["volatility_12h"] = df["close"].pct_change().rolling(12).std()
    df["volatility_24h"] = df["close"].pct_change().rolling(24).std()
    df["volatility_ratio"] = df["volatility_3h"] / (df["volatility_12h"] + 1e-9)

    # ===== Volume Features =====
    df["volume_change_1h"] = df["volume"].pct_change(1)
    df["volume_change_3h"] = df["volume"].pct_change(3)
    df["volume_ma_6h"] = df["volume"].rolling(6).mean()
    df["volume_zscore"] = (
        (df["volume"] - df["volume"].rolling(24).mean())
        / (df["volume"].rolling(24).std() + 1e-9)
    )
    df["volume_price_momentum"] = df["return_1h"] * df["volume_zscore"]
    df["volume_pctile"] = df["volume"].rolling(96, min_periods=24).rank(pct=True)
    df["price_volume_agree"] = (
        np.sign(df["return_1h"]) * np.sign(df["volume_change_1h"])
    ).fillna(0)
    # Abnormal volume: z-score above +1.5 vs 24h baseline (backward-looking)
    df["abnormal_volume"] = (df["volume_zscore"] > 1.5).astype(float)

    # ===== EMA Structure =====
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["ema_100"] = ta.trend.EMAIndicator(df["close"], window=100).ema_indicator()
    df["ema_cross"] = (df["ema_20"] - df["ema_50"]) / (df["close"] + 1e-9)
    df["ema_cross_20_100"] = (df["ema_20"] - df["ema_100"]) / (df["close"] + 1e-9)
    df["ema_cross_slope"] = df["ema_cross"].diff(3)
    df["price_vs_ema20"] = (df["close"] - df["ema_20"]) / (df["ema_20"] + 1e-9)
    df["price_vs_ema50"] = (df["close"] - df["ema_50"]) / (df["ema_50"] + 1e-9)
    df["price_vs_ema100"] = (df["close"] - df["ema_100"]) / (df["ema_100"] + 1e-9)
    # Trend direction (+1/-1/0) and strength (0–1 from |ema_cross| rank)
    df["trend_direction"] = np.sign(df["ema_cross"]).fillna(0)
    df["trend_strength"] = (
        df["ema_cross"].abs().rolling(96, min_periods=24).rank(pct=True)
    )

    # ===== Candle Pattern Features =====
    df["candle_body"] = (df["close"] - df["open"]) / (df["close"] + 1e-9)
    df["candle_upper_wick"] = (
        (df["high"] - df[["open", "close"]].max(axis=1)) / (df["close"] + 1e-9)
    )
    df["candle_lower_wick"] = (
        (df[["open", "close"]].min(axis=1) - df["low"]) / (df["close"] + 1e-9)
    )
    df["high_low_range"] = (df["high"] - df["low"]) / (df["close"] + 1e-9)
    hl = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_to_range"] = (df["close"] - df["open"]).abs() / (hl + 1e-9)
    df["upper_wick_ratio"] = (
        (df["high"] - df[["open", "close"]].max(axis=1)) / (hl + 1e-9)
    )
    df["lower_wick_ratio"] = (
        (df[["open", "close"]].min(axis=1) - df["low"]) / (hl + 1e-9)
    )

    # ===== Rolling highs / lows / breakout distance =====
    for w in [12, 24, 48]:
        roll_high = df["high"].rolling(w).max()
        roll_low = df["low"].rolling(w).min()
        df[f"dist_to_high_{w}"] = (df["close"] - roll_high) / (df["close"] + 1e-9)
        df[f"dist_to_low_{w}"] = (df["close"] - roll_low) / (df["close"] + 1e-9)
        df[f"breakout_range_{w}"] = (roll_high - roll_low) / (df["close"] + 1e-9)

    # ===== Trend / volatility regimes =====
    df["trend_regime"] = np.sign(df["ema_cross"]).fillna(0)
    vol_med = df["volatility_24h"].rolling(96, min_periods=24).median()
    df["vol_regime"] = (df["volatility_24h"] > vol_med).astype(float)

    # ===== Multi-Signal Confirmation Score =====
    df["momentum_agreement"] = (
        (df["return_1h"] > 0).astype(int)
        + (df["return_3h"] > 0).astype(int)
        + (df["return_6h"] > 0).astype(int)
        + (df["macd_histogram"] > 0).astype(int)
        + (df["rsi_14"] > 50).astype(int)
    ) / 5.0

    # ===== Time / session features (cyclical, no leakage) =====
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"], utc=True)
        hour = ts.dt.hour
        dow = ts.dt.dayofweek
        df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        df["dow_cos"] = np.cos(2 * np.pi * dow / 7)
        df["is_weekend"] = (dow >= 5).astype(float)
        # Approximate major sessions in UTC
        df["session_asia"] = ((hour >= 0) & (hour < 8)).astype(float)
        df["session_europe"] = ((hour >= 7) & (hour < 16)).astype(float)
        df["session_us"] = ((hour >= 13) & (hour < 22)).astype(float)

    # ===== Lag Features =====
    for lag in [1, 2, 3]:
        df[f"close_lag_{lag}"] = df["close"].shift(lag)
        df[f"return_lag_{lag}"] = df["return_1h"].shift(lag)
        df[f"rsi_lag_{lag}"] = df["rsi_14"].shift(lag)
        df[f"volume_lag_{lag}"] = df["volume"].shift(lag)

    # ===== Cross-asset market context (aligned past closes only) =====
    if btc_close is not None:
        btc = btc_close.reindex(df.index).astype(float)
        df["btc_return_1h"] = btc.pct_change(1)
        df["btc_return_6h"] = btc.pct_change(6)
        df["btc_vol_12h"] = btc.pct_change().rolling(12).std()
        df["rel_return_vs_btc_1h"] = df["return_1h"] - df["btc_return_1h"]

    if eth_close is not None:
        eth = eth_close.reindex(df.index).astype(float)
        df["eth_return_1h"] = eth.pct_change(1)
        df["eth_return_6h"] = eth.pct_change(6)
        df["rel_return_vs_eth_1h"] = df["return_1h"] - df["eth_return_1h"]

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna()
    return df


def get_feature_columns(df: pd.DataFrame) -> list:
    """Numeric feature columns excluding labels and future leakage columns."""
    exclude = {
        "target",
        "future_close",
        "future_return",
        "timestamp",
        "open_time",
        "close_time",
        "date",
        "action",  # two-stage intermediate
    }
    return [
        c
        for c in df.select_dtypes(include=[np.number]).columns
        if c not in exclude
    ]
