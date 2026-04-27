"""
preprocessing/features/cyber.py
Engineered cyber / network-flow features.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def engineer_cyber_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ── Auth failure burst rate — rolling 5-min count ─────────────────
    try:
        if df.index.name == "time" or "time" in df.columns:
            if "time" in df.columns:
                df = df.set_index("time")
            df["auth_failure_burst_rate"] = (
                df.groupby("asset_id")["auth_failures"]
                .transform(lambda x: x.rolling("5min", min_periods=1).sum().astype("float32"))
            )
            df = df.reset_index()
        else:
            df["auth_failure_burst_rate"] = (
                df.groupby("asset_id")["auth_failures"]
                .transform(lambda x: x.rolling(5, min_periods=1).sum().astype("float32"))
            )
    except Exception:
        df["auth_failure_burst_rate"] = df["auth_failures"].astype("float32")

    # ── Lateral movement indicator ─────────────────────────────────────
    # Proxy: if threat is non-normal AND auth failures exist, flag as lateral
    df["lateral_move_indicator"] = (
        (df["threat_type"] != "normal") & (df["auth_failures"] > 0)
    ).astype("int8")

    print(f"✅ Cyber features engineered — {len(df):,} rows")
    return df
