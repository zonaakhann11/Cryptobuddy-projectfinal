import csv
from datetime import datetime

files = {
    'BTCUSDT': 'data/historical/BTCUSDT_hourly.csv',
    'ETHUSDT': 'data/historical/ETHUSDT_hourly.csv',
    'SOLUSDT': 'data/historical/SOLUSDT_hourly.csv',
}

def summarize(path):
    count = 0
    first = None
    last = None
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row:
                continue
            ts = row[0]
            try:
                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            except Exception:
                # try alternative formats
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    continue
            if first is None:
                first = dt
            last = dt
            count += 1
    return count, first, last

if __name__ == '__main__':
    for symbol, path in files.items():
        try:
            cnt, first, last = summarize(path)
            if cnt == 0:
                print(f"{symbol}: 0 rows (no data)")
            else:
                print(f"{symbol}: {cnt} rows — {first} to {last}")
        except FileNotFoundError:
            print(f"{symbol}: file not found: {path}")
        except Exception as e:
            print(f"{symbol}: error: {e}")
