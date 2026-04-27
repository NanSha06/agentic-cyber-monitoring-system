"""
preprocessing/features/fusion.py
Cross-domain fusion features that combine battery + cyber signals.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def engineer_fusion_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ── Battery drain during active threat window ──────────────────────
    is_threat = df["threat_type"] != "normal"
    soc_drop = df.get("soc_drop_under_load", pd.Series(0.0, index=df.index))
    df["battery_drain_during_alert"] = soc_drop.where(is_threat, other=0.0).astype("float32")

    # ── Heat spike post portscan (15-min window) ───────────────────────
    # Simplified: flag rows where threat_type==portscan as heat_spike candidates
    df["heat_spike_post_scan"] = (df["threat_type"] == "portscan").astype("float32")

    # ── Cross-domain risk delta ────────────────────────────────────────
    soh_val = df.get("soh", pd.Series(100.0, index=df.index)).fillna(100.0)
    burst   = df.get("auth_failure_burst_rate", pd.Series(0.0, index=df.index)).fillna(0.0).clip(0, 100)
    df["raw_risk_proxy"] = (0.4 * (100 - soh_val) + 0.6 * burst).astype("float32")

    try:
        df["cross_domain_risk_delta"] = (
            df.groupby("asset_id")["raw_risk_proxy"]
            .transform(lambda x: x.rolling(10, min_periods=1).mean().diff().fillna(0).astype("float32"))
        )
    except Exception:
        df["cross_domain_risk_delta"] = df["raw_risk_proxy"].diff().fillna(0).astype("float32")

    print(f"✅ Fusion features engineered — {len(df):,} rows")
    return df
