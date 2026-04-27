"""
preprocessing/cleaning/cyber_cleaner.py
Cleans raw CIC-IDS2017 CSV data into the unified schema.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path


# CIC-IDS2017 label to threat_type mapping
LABEL_MAP: dict[str, str] = {
    "BENIGN":              "normal",
    "benign":              "normal",
    "Normal":              "normal",
    "DoS Hulk":            "dos",
    "DoS GoldenEye":       "dos",
    "DoS slowloris":       "dos",
    "DoS Slowhttptest":    "dos",
    "DDoS":                "ddos",
    "PortScan":            "portscan",
    "Port Scan":           "portscan",
    "FTP-Patator":         "bruteforce",
    "SSH-Patator":         "bruteforce",
    "Bot":                 "botnet",
    "Web Attack – Brute Force": "bruteforce",
    "Web Attack – XSS":    "web_attack",
    "Web Attack – Sql Injection": "web_attack",
    "Infiltration":        "infiltration",
    "Heartbleed":          "exploit",
}


def load_cic_ids2017(data_dir: str = "datasets/raw/cicids") -> pd.DataFrame:
    """Load all CIC-IDS2017 CSV files from directory."""
    path = Path(data_dir)
    frames = []
    for f in sorted(path.rglob("*.csv")):
        try:
            df = pd.read_csv(f, low_memory=False, encoding="utf-8",
                             on_bad_lines="skip")
            df["_source_file"] = f.name
            frames.append(df)
            print(f"  📂 Loaded {f.name} — {len(df):,} rows")
        except Exception as e:
            print(f"  ⚠️  Skipped {f.name}: {e}")
    if not frames:
        raise FileNotFoundError(f"No CIC-IDS2017 CSV files found in {data_dir}")
    return pd.concat(frames, ignore_index=True)


def clean_cyber(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise CIC-IDS2017 flow data into unified schema.
    Keeps key flow features and maps labels to threat_type.
    """
    # Strip whitespace from column names (CIC CSVs have leading spaces)
    df.columns = df.columns.str.strip()

    # Map label column
    label_col = next((c for c in ["Label", "label", " Label"] if c in df.columns), None)
    if label_col:
        df["threat_type"] = df[label_col].map(LABEL_MAP).fillna("unknown")
        df["threat_type"] = df["threat_type"].astype("category")
        df["risk_label"] = (df["threat_type"] != "normal").astype("int8")
    else:
        df["threat_type"] = "unknown"
        df["risk_label"]  = np.int8(0)

    # Assign fake asset IDs (CIC doesn't have battery assets)
    df["asset_id"] = "NETWORK-" + (df.index % 100).astype(str).str.zfill(3)

    # Synthetic timestamp if not present
    if "Timestamp" in df.columns:
        df["time"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    else:
        df["time"] = pd.date_range(start="2020-01-01", periods=len(df), freq="1s")

    # Auth failures proxy from "Init_Win_bytes_fwd" or default 0
    df["auth_failures"] = np.int32(0)

    # Packet entropy proxy from flow byte ratio
    flow_bytes_col = next((c for c in ["Total Fwd Packets", "TotFwdPkts"] if c in df.columns), None)
    if flow_bytes_col:
        fwd = pd.to_numeric(df[flow_bytes_col], errors="coerce").fillna(1)
        total_col = next((c for c in ["Total Length of Fwd Packets", "TotLenFwdPkts"] if c in df.columns), None)
        if total_col:
            total = pd.to_numeric(df[total_col], errors="coerce").fillna(1)
            ratio = (fwd / (total + 1e-6)).clip(0, 1)
            from scipy.stats import entropy as scipy_entropy
            df["packet_entropy"] = ratio.apply(
                lambda p: float(-p * np.log2(p + 1e-9) - (1 - p) * np.log2(1 - p + 1e-9))
            ).astype("float32")
        else:
            df["packet_entropy"] = np.float32(0.0)
    else:
        df["packet_entropy"] = np.float32(0.0)

    # Battery defaults (cyber data has no battery readings)
    for col, default in [("temp", 25.0), ("voltage", 3.7), ("current", 0.0),
                          ("soc", 100.0), ("soh", 100.0)]:
        df[col] = np.float32(default)

    df = df.drop(columns=["_source_file"], errors="ignore")
    print(f"✅ Cyber clean complete — {len(df):,} rows retained")
    return df.reset_index(drop=True)
