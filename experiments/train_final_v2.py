"""
Final v2 training pipeline (manual run only).

- Never overwrites backend/models/saved/ (production / legacy)
- Writes to backend/models/saved_v2/ and experiments/checkpoints/
- Chronological 60/20/20 split; select on validation; test once
- Uses existing OHLCV CSVs under backend/data/historical/ (no new download)

Quick mode (~30–90 min typical): --quick → 1h horizon only, lighter zoo
Full overnight: --all (1h + 4h, full model zoo)

Usage:
  python -m experiments.train_final_v2 --all --quick
  python -m experiments.train_final_v2 --asset BTCUSDT --quick --resume
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.metrics import balanced_accuracy_score

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from experiments.common import (  # noqa: E402
    RESULTS_DIR,
    SAVED_V2,
    chronological_split,
    feature_columns,
    make_labels,
    ternary_metrics,
)
from features.indicators import add_indicators  # noqa: E402

CHECKPOINT_DIR = ROOT / "experiments" / "checkpoints" / "final_v2"
LOG_PATH = ROOT / "experiments" / "logs" / "train_final_v2.log"
HISTORICAL_DIR = BACKEND / "data" / "historical"
PROCESSED_DIR = BACKEND / "data" / "processed"

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
HORIZONS = [1, 4]  # hours
THRESHOLDS = {"BTCUSDT": 0.0015, "ETHUSDT": 0.0015, "SOLUSDT": 0.0020}

RANDOM_STATE = 42
QUICK_MODE = False


def log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_ohlcv(symbol: str) -> pd.DataFrame:
    candidates = [
        HISTORICAL_DIR / f"{symbol}_hourly.csv",
        PROCESSED_DIR / f"{symbol}_1h.csv",
        PROCESSED_DIR / f"{symbol}.csv",
        BACKEND / "data" / f"{symbol}_1h.csv",
    ]
    for p in candidates:
        if p.exists():
            df = pd.read_csv(p)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                df = df.sort_values("timestamp").reset_index(drop=True)
            log(f"  loaded {p.name} rows={len(df)}")
            return df
    raise FileNotFoundError(
        f"No OHLCV CSV for {symbol}. Expected e.g. {HISTORICAL_DIR / f'{symbol}_hourly.csv'}"
    )


def _btc_eth_series(df: pd.DataFrame, symbol: str):
    btc_close = eth_close = None
    if symbol != "BTCUSDT":
        try:
            btc = _load_ohlcv("BTCUSDT")
            merged = pd.merge(df[["timestamp"]], btc[["timestamp", "close"]], on="timestamp", how="left")
            btc_close = merged["close"]
        except Exception as e:
            log(f"  BTC context skip: {e}")
    if symbol == "SOLUSDT":
        try:
            eth = _load_ohlcv("ETHUSDT")
            merged = pd.merge(df[["timestamp"]], eth[["timestamp", "close"]], on="timestamp", how="left")
            eth_close = merged["close"]
        except Exception as e:
            log(f"  ETH context skip: {e}")
    return btc_close, eth_close


def _model_zoo(quick: bool = False):
    """Full zoo for overnight; quick = GB + ExtraTrees only, fewer trees."""
    if quick:
        return {
            "GradientBoosting": GradientBoostingClassifier(
                random_state=RANDOM_STATE, max_depth=3, n_estimators=100, learning_rate=0.05
            ),
            "ExtraTrees": ExtraTreesClassifier(
                n_estimators=150, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1
            ),
        }
    models = {
        "GradientBoosting": GradientBoostingClassifier(
            random_state=RANDOM_STATE, max_depth=3, n_estimators=150, learning_rate=0.05
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=300, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1
        ),
    }
    try:
        from lightgbm import LGBMClassifier

        models["LightGBM"] = LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=6,
            random_state=RANDOM_STATE,
            verbosity=-1,
        )
    except Exception:
        log("LightGBM not available — skipping")
    return models


def _checkpoint_path(symbol: str, horizon: int) -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR / f"{symbol}_h{horizon}.json"


def _done(symbol: str, horizon: int) -> bool:
    p = _checkpoint_path(symbol, horizon)
    if not p.exists():
        return False
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("status") == "complete"
    except Exception:
        return False


def _mark(symbol: str, horizon: int, payload: dict) -> None:
    payload = {**payload, "status": "complete", "finished_at": datetime.now(timezone.utc).isoformat()}
    _checkpoint_path(symbol, horizon).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def train_one(symbol: str, horizon: int, resume: bool = False, quick: bool = False) -> dict:
    if resume and _done(symbol, horizon):
        log(f"SKIP {symbol} h{horizon} (checkpoint complete)")
        return json.loads(_checkpoint_path(symbol, horizon).read_text(encoding="utf-8"))

    log(f"START {symbol} horizon={horizon}h quick={quick}")
    df = _load_ohlcv(symbol)
    btc_close, eth_close = _btc_eth_series(df, symbol)
    feat = add_indicators(df, btc_close=btc_close, eth_close=eth_close)
    feat["future_return"] = feat["close"].shift(-horizon) / feat["close"] - 1.0
    thr = THRESHOLDS.get(symbol, 0.0015)
    feat["target"] = make_labels(feat["future_return"], thr)
    feat = feat.dropna(subset=["future_return", "target"]).reset_index(drop=True)

    cols = feature_columns(feat)
    X = feat[cols]
    y = feat["target"].astype(int)
    n = len(feat)
    tr, va, te = chronological_split(n, 0.6, 0.2)

    X_tr, y_tr = X.iloc[tr], y.iloc[tr]
    X_va, y_va = X.iloc[va], y.iloc[va]
    X_te, y_te = X.iloc[te], y.iloc[te]

    zoo = _model_zoo(quick=quick)
    best_name, best_bal = None, -1.0
    val_rows = []
    for name, clf in zoo.items():
        log(f"  fit {name} …")
        clf.fit(X_tr, y_tr)
        pred = clf.predict(X_va)
        bal = balanced_accuracy_score(y_va, pred)
        val_rows.append({"model": name, "val_balanced_accuracy": float(bal)})
        log(f"  {name} val_bal={bal:.4f}")
        if bal > best_bal:
            best_bal, best_name = bal, name

    # Retrain selected on train+val
    X_tv = pd.concat([X_tr, X_va], axis=0)
    y_tv = pd.concat([y_tr, y_va], axis=0)
    final_clf = _model_zoo(quick=quick)[best_name]
    final_clf.fit(X_tv, y_tv)

    test_pred = final_clf.predict(X_te)
    metrics = ternary_metrics(y_te, test_pred)
    metrics["val_balanced_accuracy"] = float(best_bal)
    metrics["selected_model"] = best_name
    metrics["symbol"] = symbol
    metrics["horizon_hours"] = horizon
    metrics["n_train"] = int(len(X_tr))
    metrics["n_val"] = int(len(X_va))
    metrics["n_test"] = int(len(X_te))
    metrics["n_features"] = len(cols)
    metrics["train_mode"] = "quick" if quick else "full"
    log(f"  TEST bal={metrics.get('balanced_accuracy', metrics)} selected={best_name}")

    # Save under saved_v2 only — never touch saved/
    out = SAVED_V2
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if horizon == 1 else f"_h{horizon}"
    model_path = out / f"{symbol}_model{suffix}.pkl"
    feat_path = out / f"{symbol}_features{suffix}.json"
    joblib.dump(final_clf, model_path)
    feat_path.write_text(json.dumps(cols, indent=2), encoding="utf-8")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cmp_path = RESULTS_DIR / "final_model_comparison.csv"
    row_df = pd.DataFrame([{**metrics, **{f"val_{r['model']}": r["val_balanced_accuracy"] for r in val_rows}}])
    if cmp_path.exists():
        old = pd.read_csv(cmp_path)
        old = old[~((old.get("symbol") == symbol) & (old.get("horizon_hours") == horizon))]
        row_df = pd.concat([old, row_df], ignore_index=True)
    row_df.to_csv(cmp_path, index=False)

    payload = {
        "symbol": symbol,
        "horizon_hours": horizon,
        "selected_model": best_name,
        "metrics": metrics,
        "model_path": str(model_path),
        "features_path": str(feat_path),
        "val_leaderboard": val_rows,
        "train_mode": "quick" if quick else "full",
    }
    _mark(symbol, horizon, payload)
    log(f"DONE {symbol} h{horizon}")
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset", default=None, help="BTCUSDT|ETHUSDT|SOLUSDT")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--horizon", type=int, default=None, help="1 or 4 (default both; quick forces 1)")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Fast path: 1h only, GB+ExtraTrees, lighter trees. Uses full existing CSVs.",
    )
    args = parser.parse_args()

    global QUICK_MODE
    QUICK_MODE = bool(args.quick)

    assets = [args.asset] if args.asset else ASSETS
    if args.quick:
        horizons = [1]
    else:
        horizons = [args.horizon] if args.horizon in (1, 4) else HORIZONS

    log(
        f"=== train_final_v2 assets={assets} horizons={horizons} "
        f"resume={args.resume} quick={args.quick} ==="
    )
    log("Data source: existing historical hourly CSVs (full history in those files).")

    for symbol in assets:
        for h in horizons:
            try:
                train_one(symbol, h, resume=args.resume, quick=args.quick)
            except Exception:
                log(f"ERROR {symbol} h{h}:\n{traceback.format_exc()}")
                raise

    log("=== ALL REQUESTED STAGES COMPLETE ===")


if __name__ == "__main__":
    main()
