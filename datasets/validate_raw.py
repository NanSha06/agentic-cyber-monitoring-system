"""
datasets/validate_raw.py
Validates that required datasets are present and structurally correct.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

EXPECTED = {
    "nasa_battery": ["Voltage_measured", "Current_measured", "Temperature_measured", "Capacity"],
    "cic_ids2017":  ["Flow Duration", "Total Fwd Packets", "Label"],
}

def validate_dataset(name: str, path: str, required_cols: list[str]):
    p = Path(path)
    if not p.exists():
        print(f"❌ {name} — not found at {path}")
        return False
    df = pd.read_csv(path, nrows=5)
    df.columns = df.columns.str.strip()
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"⚠️  {name} — missing columns: {missing}")
        print(f"   Found: {list(df.columns)[:10]}")
        return False
    print(f"✅ {name} — OK ({p.stat().st_size // 1024} KB)")
    return True


def check_directories():
    dirs = {
        "Battery raw":  "datasets/raw/battery",
        "Cyber raw":    "datasets/raw/cicids",
        "Processed":    "datasets/processed",
    }
    for name, path in dirs.items():
        p = Path(path)
        if p.exists():
            files = list(p.glob("*"))
            print(f"✅ {name} — {len(files)} files in {path}")
        else:
            print(f"⚠️  {name} — directory missing: {path}")


if __name__ == "__main__":
    print("=" * 50)
    print("🔍 Dataset Validation")
    print("=" * 50)
    check_directories()
    print("\nNote: Column validation skipped — run preprocessing/run_pipeline.py to validate.")
