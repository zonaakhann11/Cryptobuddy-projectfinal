import pandas as pd
import requests
import time

BINANCE_URL = "https://api.binance.com/api/v3/klines"


def update_hourly_data(symbol: str) -> pd.DataFrame:
    """
    Fetch ALL missing hourly candles since last timestamp
    and update the CSV on disk.
    """

    file_path = f"data/historical/{symbol}_hourly.csv"
    df = pd.read_csv(file_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Clean up existing incomplete candles from CSV (started less than 1 hour ago)
    now = pd.Timestamp.utcnow()
    cutoff = now - pd.Timedelta(hours=1)
    if df["timestamp"].dt.tz is None:
        cutoff = cutoff.tz_localize(None)
    df = df[df["timestamp"] <= cutoff]

    last_ts = df["timestamp"].iloc[-1]
    last_ms = int(last_ts.timestamp() * 1000)

    now_ms = int(now.timestamp() * 1000)

    all_new = []

    while True:
        params = {
            "symbol": symbol,
            "interval": "1h",
            "startTime": last_ms,
            "limit": 1000
        }

        r = requests.get(BINANCE_URL, params=params)
        candles = r.json()

        # Binance returns the start candle again → skip first
        candles = candles[1:]

        if not candles:
            break

        for c in candles:
            # c[0] is open time. The candle is completed if c[0] + 3600000 <= now_ms
            if c[0] + 3600000 <= now_ms:
                all_new.append({
                    "timestamp": pd.to_datetime(c[0], unit="ms"),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                })

        last_ms = candles[-1][0]
        time.sleep(0.2)  # rate-limit safety

        if last_ms >= now_ms:
            break

    if all_new:
        new_df = pd.DataFrame(all_new)
        df = pd.concat([df, new_df], ignore_index=True)
        df = df.drop_duplicates(subset="timestamp")
        df.to_csv(file_path, index=False)
        print(f"{symbol}: added {len(all_new)} new candles")

    else:
        # Re-save to disk to clean up any incomplete candles that were removed
        df.to_csv(file_path, index=False)
        print(f"{symbol}: already up-to-date")

    return df
