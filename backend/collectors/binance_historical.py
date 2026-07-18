import requests
import pandas as pd
import time
from datetime import datetime

BASE_URL = "https://api.binance.com/api/v3/klines"

def fetch_symbol(symbol, start_str, interval="1h"):
    print(f"Fetching {symbol} from {start_str} ...")

    start_ts = int(pd.to_datetime(start_str).timestamp() * 1000)
    all_rows = []

    while True:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ts,
            "limit": 1000
        }

        response = requests.get(BASE_URL, params=params)
        data = response.json()

        if not data:
            break

        for k in data:
            all_rows.append({
                "timestamp": pd.to_datetime(k[0], unit="ms"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })

        start_ts = data[-1][0] + 1
        time.sleep(0.5)  # respect rate limit

    return pd.DataFrame(all_rows)

def fetch_and_save(symbol, start_date):
    df = fetch_symbol(symbol, start_date)
    df.to_csv(f"data/historical/{symbol}_hourly.csv", index=False)
    print(f"{symbol} DONE | rows: {len(df)}")

if __name__ == "__main__":
    symbols = {
        "BTCUSDT": "2017-08-01",
        "ETHUSDT": "2017-08-01",
        "SOLUSDT": "2020-08-01"  # SOL launched later
    }

    for sym, start in symbols.items():
        fetch_and_save(sym, start)
