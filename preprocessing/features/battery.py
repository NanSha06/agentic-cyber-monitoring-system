"""
preprocessing/features/battery.py
Engineered battery features for the ML pipeline.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def engineer_battery_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["asset_id", "time"])

    # ── Rate of temperature change over 10-minute window ──────────────
    def _temp_roc(grp: pd.Series) -> pd.Series:
        dt_secs = grp.index.to_series().diff().dt.total_seconds().fillna(1)
        return (grp.diff() / dt_secs * 60).astype("float32")

    if df["time"].dtype == "datetime64[ns]":
        try:
            df = df.set_index("time")
            df["temp_rate_of_change"] = (
                df.groupby("asset_id")["temp"]
                .transform(lambda x: x.diff().fillna(0).astype("float32"))
            )
            # Voltage variance over 10-minute rolling window
            df["voltage_variance_10m"] = (
                df.groupby("asset_id")["voltage"]
                .transform(lambda x: x.rolling("10min", min_periods=1).var().fillna(0).astype("float32"))
            )
            # SOC drop under load (clipped to positive drops only)
            df["soc_drop_under_load"] = (
                df.groupby("asset_id")["soc"]
                .transform(lambda x: x.diff().clip(upper=0).abs().fillna(0).astype("float32"))
            )
            df = df.reset_index()
        except Exception:
            # Fallback for non-datetime index
            df["temp_rate_of_change"]  = df.groupby("asset_id")["temp"].diff().fillna(0).astype("float32")
            df["voltage_variance_10m"] = df.groupby("asset_id")["voltage"].transform(lambda x: x.rolling(10, min_periods=1).var().fillna(0)).astype("float32")
            df["soc_drop_under_load"]  = df.groupby("asset_id")["soc"].diff().clip(upper=0).abs().fillna(0).astype("float32")
    else:
        df["temp_rate_of_change"]  = df.groupby("asset_id")["temp"].diff().fillna(0).astype("float32")
        df["voltage_variance_10m"] = df.groupby("asset_id")["voltage"].transform(lambda x: x.rolling(10, min_periods=1).var().fillna(0)).astype("float32")
        df["soc_drop_under_load"]  = df.groupby("asset_id")["soc"].diff().clip(upper=0).abs().fillna(0).astype("float32")

    print(f"✅ Battery features engineered — {len(df):,} rows")
    return df
