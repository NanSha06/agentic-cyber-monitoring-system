"""
models/train_all.py
Master training script — trains all 5 models sequentially.

Usage:
    python models/train_all.py
    python models/train_all.py --skip-lstm   # skip LSTM if no GPU
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

UNIFIED_PATH = "datasets/processed/unified.parquet"


def load_data() -> pd.DataFrame:
    path = Path(UNIFIED_PATH)
    if not path.exists():
        print(f"❌ Unified dataset not found at {UNIFIED_PATH}")
        print("   Run: python preprocessing/run_pipeline.py first")
        sys.exit(1)
    df = pd.read_parquet(path)
    print(f"📊 Loaded unified.parquet — {len(df):,} rows, {len(df.columns)} columns")
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-lstm", action="store_true", help="Skip LSTM training")
    parser.add_argument("--skip-tf",   action="store_true", help="Skip all TensorFlow models")
    args = parser.parse_args()

    df = load_data()
    battery_df = df[df["temp"].notna() & (df["temp"] > 0)].copy() if "temp" in df.columns else df
    cyber_df   = df[df["auth_failure_burst_rate"].notna()].copy() if "auth_failure_burst_rate" in df.columns else df

    print("\n" + "=" * 60)
    print("🔋 Model 1/5 — SOH Predictor (XGBoost)")
    print("=" * 60)
    try:
        from models.battery.soh_predictor import train as train_soh
        if "soh" in battery_df.columns and battery_df["soh"].notna().sum() > 100:
            train_soh(battery_df)
        else:
            print("  ⚠️  Insufficient SOH labels — skipping")
    except Exception as e:
        print(f"  ❌ SOH training failed: {e}")

    if not args.skip_lstm and not args.skip_tf:
        print("\n" + "=" * 60)
        print("🔋 Model 2/5 — RUL Forecaster (LSTM)")
        print("=" * 60)
        try:
            from models.battery.rul_forecaster import train as train_rul
            train_rul(battery_df)
        except Exception as e:
            print(f"  ❌ RUL training failed: {e}")
    else:
        print("\n⏭️  Skipping RUL Forecaster (LSTM)")

    print("\n" + "=" * 60)
    print("🔋 Model 3/5 — Battery Anomaly Detector (Isolation Forest)")
    print("=" * 60)
    try:
        from models.battery.anomaly_detector import train as train_anomaly
        train_anomaly(battery_df)
    except Exception as e:
        print(f"  ❌ Anomaly Detector training failed: {e}")

    print("\n" + "=" * 60)
    print("🌐 Model 4/5 — Attack Classifier (Random Forest)")
    print("=" * 60)
    try:
        from models.cyber.attack_classifier import train as train_classifier
        if "threat_type" in cyber_df.columns:
            train_classifier(cyber_df)
        else:
            print("  ⚠️  No threat_type column — skipping")
    except Exception as e:
        print(f"  ❌ Attack Classifier training failed: {e}")

    if not args.skip_tf:
        print("\n" + "=" * 60)
        print("🌐 Model 5/5 — Zero-Day Detector (Autoencoder)")
        print("=" * 60)
        try:
            from models.cyber.zero_day_detector import train as train_zero_day
            train_zero_day(cyber_df)
        except Exception as e:
            print(f"  ❌ Zero-Day Detector training failed: {e}")
    else:
        print("\n⏭️  Skipping Zero-Day Detector (TF)")

    print("\n✅ Training complete — all models saved to models/")


if __name__ == "__main__":
    main()
