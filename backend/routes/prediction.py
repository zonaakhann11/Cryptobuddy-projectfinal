from flask import Blueprint, request, jsonify
from models.realtime_predict import predict
from features.indicators import add_indicators
from collectors.binance_updater import update_hourly_data
import pandas as pd
import numpy as np
import json
from datetime import datetime

prediction_bp = Blueprint('prediction', __name__)

# Fallback helper if update_hourly_data isn't easily accessible
def fetch_latest_completed_hour(symbol):
    try:
        import requests
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": "1h", "limit": 2}
        response = requests.get(url, params=params)
        data = response.json()
        if len(data) >= 2:
            kline = data[-2]
            return {
                "timestamp": pd.to_datetime(kline[0], unit='ms'),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5])
            }
    except Exception:
        pass
    return None

@prediction_bp.route('/predict', methods=['GET', 'POST', 'OPTIONS'])
def get_prediction():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    # Browser address-bar hits are GET — explain how to call the API
    if request.method == 'GET':
        return jsonify({
            "ok": True,
            "message": "Use POST with JSON body {\"symbol\": \"BTCUSDT\"}. Opening this URL in a browser sends GET, which cannot run a prediction.",
            "example": {
                "method": "POST",
                "url": "/api/predict",
                "body": {"symbol": "BTCUSDT", "model_version": "v1"},
            },
            "dashboard": "Start the frontend (npm run dev) and click PREDICT.",
        }), 200
        
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({"success": False, "error": "Missing symbol"}), 400
            
        symbol = data['symbol']
        model_version = data.get('model_version', 'v1')
        if model_version not in ('v1', 'v2'):
            model_version = 'v1'
        
        # 1. Get the ML prediction (treating realtime_predict as a black box)
        prediction_result = predict(symbol, model_version=model_version)
        
        if not prediction_result:
            return jsonify({"success": False, "error": f"Failed to generate prediction for {symbol}"}), 503
            
        # 2. Get technical indicators safely without modifying ML pipeline
        try:
            df = update_hourly_data(symbol)
            
            # Fetch latest completed and forming candles (limit=2) for real-time price accuracy
            try:
                import requests
                url = "https://api.binance.com/api/v3/klines"
                params = {"symbol": symbol, "interval": "1h", "limit": 2}
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                if len(data) >= 2:
                    candles_to_append = []
                    for candle in data[-2:]:  # data[-2] is completed, data[-1] is forming (live price)
                        candles_to_append.append({
                            "timestamp": pd.to_datetime(candle[0], unit='ms'),
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "volume": float(candle[5])
                        })
                    df = pd.concat([df, pd.DataFrame(candles_to_append)], ignore_index=True)
                    df = df.drop_duplicates(subset="timestamp", keep="last")
            except Exception as e:
                print(f"Warning: Failed to fetch live candles for {symbol} in prediction route: {e}")
            
            df = add_indicators(df)
            latest_row = df.iloc[-1]
            
            indicators = {
                "RSI": float(latest_row.get("rsi_14", 0)),
                "MACD Histogram": float(latest_row.get("macd_histogram", 0)),
                "ATR %": float(latest_row.get("atr_pct", 0) * 100), # Percentage
                "Bollinger Position": float(latest_row.get("bb_position", 0)),
                "Volume Z Score": float(latest_row.get("volume_zscore", 0)),
                "Volume Price Momentum": float(latest_row.get("volume_price_momentum", 0)),
                "Momentum Agreement": float(latest_row.get("momentum_agreement", 0)),
                "EMA Cross": float(latest_row.get("ema_cross", 0)),
                "Stochastic K": float(latest_row.get("stoch_k", 0)),
                "Stochastic D": float(latest_row.get("stoch_d", 0))
            }
            prediction_result["indicators"] = indicators

            # Chart history uses EMA 20/50 (aligned with feature pipeline); keep ma7/ma25 keys for UI
            chart_df = df.tail(30)
            indicator_history = []
            for _, row in chart_df.iterrows():
                indicator_history.append({
                    "macd": float(row.get("macd", 0) or 0) if not pd.isna(row.get("macd", 0)) else 0.0,
                    "signal": float(row.get("macd_signal", 0) or 0) if not pd.isna(row.get("macd_signal", 0)) else 0.0,
                    "histogram": float(row.get("macd_histogram", 0) or 0) if not pd.isna(row.get("macd_histogram", 0)) else 0.0,
                    "rsi": float(row.get("rsi_14", 50) or 50) if not pd.isna(row.get("rsi_14", 50)) else 50.0,
                    "price": float(row.get("close", 0) or 0) if not pd.isna(row.get("close", 0)) else 0.0,
                    "ma7": float(row.get("ema_20", 0) or 0) if not pd.isna(row.get("ema_20", np.nan)) else 0.0,
                    "ma25": float(row.get("ema_50", 0) or 0) if not pd.isna(row.get("ema_50", np.nan)) else 0.0,
                    "ema_20": float(row.get("ema_20", 0) or 0) if not pd.isna(row.get("ema_20", np.nan)) else 0.0,
                    "ema_50": float(row.get("ema_50", 0) or 0) if not pd.isna(row.get("ema_50", np.nan)) else 0.0,
                    "ema_100": float(row.get("ema_100", 0) or 0) if not pd.isna(row.get("ema_100", np.nan)) else 0.0,
                    "volume": float(row.get("volume", 0) or 0) if not pd.isna(row.get("volume", 0)) else 0.0,
                    "volume_ma": float(row.get("volume_ma_6h", 0) or 0) if not pd.isna(row.get("volume_ma_6h", np.nan)) else 0.0,
                    "open": float(row.get("open", 0) or 0) if not pd.isna(row.get("open", 0)) else 0.0,
                    "close": float(row.get("close", 0) or 0) if not pd.isna(row.get("close", 0)) else 0.0,
                })
            prediction_result["indicator_history"] = indicator_history
            # Enrich indicators snapshot for tabs
            prediction_result["indicators"] = {
                **(prediction_result.get("indicators") or {}),
                "EMA20": float(latest_row.get("ema_20", 0) or 0) if not pd.isna(latest_row.get("ema_20", np.nan)) else 0.0,
                "EMA50": float(latest_row.get("ema_50", 0) or 0) if not pd.isna(latest_row.get("ema_50", np.nan)) else 0.0,
                "EMA100": float(latest_row.get("ema_100", 0) or 0) if not pd.isna(latest_row.get("ema_100", np.nan)) else 0.0,
                "Volume MA 6h": float(latest_row.get("volume_ma_6h", 0) or 0) if not pd.isna(latest_row.get("volume_ma_6h", np.nan)) else 0.0,
            }
        except Exception as e:
            # If indicator extraction fails, still return the prediction but without indicators
            prediction_result["indicators"] = None
            prediction_result["indicator_history"] = []
            print(f"Warning: Failed to compute indicators: {e}")
            
        # 3. Add success envelope
        return jsonify(prediction_result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
