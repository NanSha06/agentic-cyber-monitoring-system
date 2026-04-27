"""
preprocessing/run_pipeline.py
Master pipeline: raw data → cleaned → feature-engineered → unified.parquet

Usage:
    python preprocessing/run_pipeline.py
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from preprocessing.schema import enforce_schema, validate_schema, UNIFIED_SCHEMA
from preprocessing.cleaning.battery_cleaner import load_nasa_battery, clean_battery
from preprocessing.cleaning.cyber_cleaner import load_cic_ids2017, clean_cyber
from preprocessing.features.battery import engineer_battery_features
from preprocessing.features.cyber import engineer_cyber_features
from preprocessing.features.fusion import engineer_fusion_features


RAW_BATTERY_DIR = "datasets/raw/battery"
RAW_CYBER_DIR   = "datasets/raw/cicids"
OUTPUT_PATH     = "datasets/processed/unified.parquet"


def run_battery_pipeline() -> pd.DataFrame | None:
    path = Path(RAW_BATTERY_DIR)
    if not path.exists() or not list(path.rglob("*.csv")):
        print(f"⚠️  No battery CSVs found in {RAW_BATTERY_DIR} — skipping battery pipeline")
        return None
    print("\n🔋 Battery Pipeline")
    raw  = load_nasa_battery(RAW_BATTERY_DIR)
    df   = clean_battery(raw)
    df   = enforce_schema(df)
    df   = engineer_battery_features(df)
    df   = engineer_fusion_features(df)
    return df


def run_cyber_pipeline() -> pd.DataFrame | None:
    path = Path(RAW_CYBER_DIR)
    if not path.exists() or not list(path.rglob("*.csv")):
        print(f"⚠️  No cyber CSVs found in {RAW_CYBER_DIR} — skipping cyber pipeline")
        return None
    print("\n🌐 Cyber Pipeline")
    raw  = load_cic_ids2017(RAW_CYBER_DIR)
    df   = clean_cyber(raw)
    df   = enforce_schema(df)
    df   = engineer_cyber_features(df)
    df   = engineer_fusion_features(df)
    return df


def merge_domains(battery_df: pd.DataFrame | None,
                  cyber_df: pd.DataFrame | None) -> pd.DataFrame:
    keep_cols = list(UNIFIED_SCHEMA.keys()) + [
        "temp_rate_of_change", "voltage_variance_10m", "soc_drop_under_load",
        "auth_failure_burst_rate", "lateral_move_indicator",
        "battery_drain_during_alert", "heat_spike_post_scan",
        "raw_risk_proxy", "cross_domain_risk_delta",
    ]

    frames = [df[list(set(keep_cols) & set(df.columns))]
              for df in [battery_df, cyber_df] if df is not None]

    if not frames:
        raise RuntimeError("No data loaded — check dataset directories")

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values("time").reset_index(drop=True)
    print(f"\n✅ Merged dataset — {len(merged):,} rows, {len(merged.columns)} columns")
    return merged


def main():
    print("=" * 60)
    print("🛡️  Agentic Cyber-Battery Platform — Data Pipeline")
    print("=" * 60)

    battery_df = run_battery_pipeline()
    cyber_df   = run_cyber_pipeline()

    unified = merge_domains(battery_df, cyber_df)
    validate_schema(unified)

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    unified.to_parquet(OUTPUT_PATH, index=False)
    print(f"\n💾 Saved → {OUTPUT_PATH}")
    print(f"   Shape : {unified.shape}")
    print(f"   dtypes:\n{unified.dtypes.to_string()}")


if __name__ == "__main__":
    main()
