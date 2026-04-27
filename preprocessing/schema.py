"""
preprocessing/schema.py
Defines and enforces the unified cross-domain schema for the platform.
"""
from __future__ import annotations
import pandas as pd

UNIFIED_SCHEMA: dict[str, str] = {
    "time":                  "datetime64[ns]",
    "asset_id":              "object",        # pseudonymised battery ID
    "temp":                  "float32",       # °C
    "voltage":               "float32",       # V
    "current":               "float32",       # A
    "soc":                   "float32",       # State of Charge 0–100
    "soh":                   "float32",       # State of Health 0–100
    "threat_type":           "category",      # normal | ddos | bruteforce | portscan …
    "auth_failures":         "int32",
    "packet_entropy":        "float32",
    "risk_label":            "int8",          # 0=nominal 1=warning 2=critical
}


def enforce_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Cast all required columns to their declared dtypes. Missing columns are
    filled with NaN / 0 / 'normal' defaults so downstream code never KeyErrors."""
    defaults: dict[str, object] = {
        "threat_type":    "normal",
        "auth_failures":  0,
        "packet_entropy": 0.0,
        "risk_label":     0,
        "soc":            float("nan"),
        "soh":            float("nan"),
    }
    for col, dtype in UNIFIED_SCHEMA.items():
        if col not in df.columns:
            df[col] = defaults.get(col, float("nan"))
        try:
            if dtype == "datetime64[ns]":
                df[col] = pd.to_datetime(df[col])
            elif dtype == "category":
                df[col] = df[col].astype("category")
            elif dtype == "int32":
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int32")
            elif dtype == "int8":
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int8")
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")
        except Exception as exc:
            print(f"  ⚠️  Schema cast failed for '{col}': {exc}")
    return df


def validate_schema(df: pd.DataFrame) -> None:
    missing = [c for c in UNIFIED_SCHEMA if c not in df.columns]
    if missing:
        raise ValueError(f"Unified schema validation failed — missing columns: {missing}")
    print("✅ Schema validation passed")
