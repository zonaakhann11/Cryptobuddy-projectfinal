"""Shared utilities for CryptoBuddy v2 experiments (no leakage)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

RANDOM_STATE = 42
CLASS_LABELS = ["SELL", "BUY", "HOLD"]  # 0, 1, 2

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "experiments" / "results"
MANIFEST_DIR = REPO_ROOT / "experiments" / "feature_manifests"
SAVED_V2 = BACKEND_ROOT / "models" / "saved_v2"

EXCLUDE_COLS = {
    "target",
    "target_bin",
    "future_close",
    "future_return",
    "timestamp",
    "open_time",
    "close_time",
    "date",
    "action",
}


def chronological_split(
    n: int, train_frac: float = 0.6, val_frac: float = 0.2
) -> Tuple[slice, slice, slice]:
    """Return train / val / test index slices for a sorted series of length n."""
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    train = slice(0, n_train)
    val = slice(n_train, n_train + n_val)
    test = slice(n_train + n_val, n)
    return train, val, test


def make_labels(future_return: pd.Series, threshold: float) -> pd.Series:
    """Ternary labels from future return and absolute threshold."""
    y = pd.Series(2, index=future_return.index, dtype=int)
    y = y.mask(future_return < -threshold, 0)
    y = y.mask(future_return > threshold, 1)
    return y


def make_atr_labels(
    future_return: pd.Series, atr_pct: pd.Series, k: float = 0.5
) -> pd.Series:
    """Volatility-adjusted threshold: ± k * atr_pct."""
    thr = (k * atr_pct).clip(lower=1e-4)
    y = pd.Series(2, index=future_return.index, dtype=int)
    y = y.mask(future_return < -thr, 0)
    y = y.mask(future_return > thr, 1)
    return y


def feature_columns(df: pd.DataFrame) -> List[str]:
    return [
        c
        for c in df.select_dtypes(include=[np.number]).columns
        if c not in EXCLUDE_COLS
    ]


def ternary_metrics(y_true, y_pred) -> Dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(
            f1_score(y_true, y_pred, average="weighted", zero_division=0)
        ),
    }


def binary_metrics(y_true, y_pred, y_proba=None) -> Dict[str, float]:
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(
            precision_score(y_true, y_pred, average="binary", zero_division=0)
        ),
        "recall": float(recall_score(y_true, y_pred, average="binary", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="binary", zero_division=0)),
    }
    if y_proba is not None:
        try:
            out["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        except ValueError:
            out["roc_auc"] = float("nan")
    return out


def class_distribution(y: pd.Series) -> Dict[str, float]:
    n = len(y)
    out = {}
    for cls, name in enumerate(CLASS_LABELS):
        c = int((y == cls).sum())
        out[f"{name}_count"] = c
        out[f"{name}_pct"] = 100.0 * c / n if n else 0.0
    return out


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for a proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = successes / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    return ((centre - margin) / denom, (centre + margin) / denom)


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    SAVED_V2.mkdir(parents=True, exist_ok=True)
