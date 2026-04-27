"""
preprocessing/cleaning/battery_cleaner.py
Cleans raw NASA battery CSV/Parquet data into the unified schema.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path


def load_nasa_battery(data_dir: str = "datasets/raw/battery") -> pd.DataFrame:
    """Load all CSV files from the battery data directory."""
    path = Path(data_dir)
    frames = []
    csv_files = list(path.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    for f in csv_files:
        try:
            df = pd.read_csv(f, low_memory=False)
            # Try to infer asset_id from filename
            df["_source_file"] = f.name
            frames.append(df)
            print(f"  📂 Loaded {f.name} — {len(df):,} rows")
        except Exception as e:
            print(f"  ⚠️  Skipped {f.name}: {e}")
    if not frames:
        raise ValueError("No battery data could be loaded")
    return pd.concat(frames, ignore_index=True)


def clean_battery(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise battery telemetry into unified schema columns:
    time, asset_id, temp, voltage, current, soc, soh
    """
    col_map = {
        # NASA / CALCE common column name variants
        "Voltage_measured":    "voltage",
        "Voltage(V)":          "voltage",
        "voltage":             "voltage",
        "Current_measured":    "current",
        "Current(A)":          "current",
        "current":             "current",
        "Temperature_measured": "temp",
        "Temperature(C)":      "temp",
        "temperature":         "temp",
        "Capacity":            "soh",        # used as SOH proxy
        "capacity":            "soh",
        "SOH":                 "soh",
        "SOC":                 "soc",
        "Time":                "time",
        "time":                "time",
        "datetime":            "time",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Assign asset_id from source file if not present
    if "asset_id" not in df.columns:
        if "_source_file" in df.columns:
            df["asset_id"] = df["_source_file"].str.replace(r"\.\w+$", "", regex=True)
        else:
            df["asset_id"] = "B0001"

    # Parse time
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    else:
        # Create synthetic timestamps if missing
        df["time"] = pd.date_range(start="2020-01-01", periods=len(df), freq="1min")

    # Normalise SOH: if raw capacity, scale 0-100
    if "soh" in df.columns:
        soh_max = df["soh"].replace([np.inf, -np.inf], np.nan).dropna().max()
        if soh_max > 1.5:
            df["soh"] = (df["soh"] / soh_max * 100).clip(0, 100)

    # Derive SOC from voltage if missing (rough proxy)
    if "soc" not in df.columns and "voltage" in df.columns:
        v_min, v_max = 2.5, 4.2
        df["soc"] = ((df["voltage"] - v_min) / (v_max - v_min) * 100).clip(0, 100)

    # Add cyber columns with defaults
    df["threat_type"]   = "normal"
    df["auth_failures"] = np.int32(0)
    df["packet_entropy"] = np.float32(0.0)
    df["risk_label"]    = np.int8(0)

    # Drop nulls in critical columns
    critical = [c for c in ["voltage", "temp"] if c in df.columns]
    df = df.dropna(subset=critical)

    # Remove out-of-range values
    if "voltage" in df.columns:
        df = df[(df["voltage"] > 0) & (df["voltage"] < 10)]
    if "temp" in df.columns:
        df = df[(df["temp"] > -40) & (df["temp"] < 100)]

    df = df.drop(columns=["_source_file"], errors="ignore")
    print(f"✅ Battery clean complete — {len(df):,} rows retained")
    return df.reset_index(drop=True)
