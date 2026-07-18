"""
Post-overnight finalization: compare v1 vs v2, write tables, optional EnableV2.

Does NOT enable v2 for the dashboard unless --enable-v2 is passed.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from experiments.common import RESULTS_DIR, SAVED_V2  # noqa: E402

V1_DIR = BACKEND / "models" / "saved"
MANIFEST = SAVED_V2 / "final_model_manifest.json"
ENABLE_FLAG = SAVED_V2 / "ENABLE_V2.flag"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable-v2", action="store_true", help="Allow API/dashboard to prefer v2")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    SAVED_V2.mkdir(parents=True, exist_ok=True)

    # Placeholder / merge comparison from training CSV
    cmp = RESULTS_DIR / "final_model_comparison.csv"
    if cmp.exists():
        print(f"Loaded {cmp}")
    else:
        print("WARNING: final_model_comparison.csv missing — run overnight training first")
        pd.DataFrame(
            columns=["symbol", "horizon_hours", "selected_model", "balanced_accuracy"]
        ).to_csv(cmp, index=False)

    # Signal distribution stub (filled when eval harness runs after training)
    dist = RESULTS_DIR / "final_signal_distribution.csv"
    if not dist.exists():
        pd.DataFrame(columns=["symbol", "horizon_hours", "BUY", "SELL", "HOLD", "coverage"]).to_csv(
            dist, index=False
        )

    acc = RESULTS_DIR / "final_accuracy_coverage.csv"
    if not acc.exists():
        pd.DataFrame(
            columns=["symbol", "horizon_hours", "accuracy", "balanced_accuracy", "coverage"]
        ).to_csv(acc, index=False)

    grouped = RESULTS_DIR / "final_grouped_indicator_examples.csv"
    if not grouped.exists():
        pd.DataFrame(
            columns=["symbol", "group", "status", "score", "explanation"]
        ).to_csv(grouped, index=False)

    # Manifest: list v2 artifacts without deleting v1
    artifacts = []
    for p in sorted(SAVED_V2.glob("*_model*.pkl")):
        artifacts.append({"path": str(p), "exists": True})
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "v1_dir": str(V1_DIR),
        "v2_dir": str(SAVED_V2),
        "v2_artifacts": artifacts,
        "v2_enabled_for_dashboard": bool(args.enable_v2),
        "note": "v1 remains the default until ENABLE_V2.flag is written",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST}")

    if args.enable_v2:
        ENABLE_FLAG.write_text("enabled\n", encoding="utf-8")
        print(f"Wrote {ENABLE_FLAG} — dashboard/API may use v2 when artifacts exist")
    else:
        if ENABLE_FLAG.exists():
            print(f"Note: {ENABLE_FLAG} already exists; leave it or delete to force v1")
        print("v2 NOT enabled for dashboard (pass --enable-v2 to switch)")


if __name__ == "__main__":
    main()
