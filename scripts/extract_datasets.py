"""
scripts/extract_datasets.py
Extracts the raw zipped datasets into the correct dataset directories.

Usage:
    python scripts/extract_datasets.py
"""
from __future__ import annotations
import sys
import zipfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent

EXTRACTIONS = [
    # (source zip, destination dir)
    (BASE / "5. Battery Data Set.zip", BASE / "datasets/raw/battery"),
    (BASE / "cicids/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.zip", BASE / "datasets/raw/cicids"),
    (BASE / "cicids/Monday-WorkingHours.pcap_ISCX.csv.zip",  BASE / "datasets/raw/cicids"),
    (BASE / "cicids/Tuesday-WorkingHours.pcap_ISCX.csv.zip", BASE / "datasets/raw/cicids"),
    (BASE / "cicids/Wednesday-workingHours.pcap_ISCX.csv.zip", BASE / "datasets/raw/cicids"),
]


def extract(src: Path, dst: Path):
    if not src.exists():
        print(f"⚠️  Not found: {src.name} — skipping")
        return
    dst.mkdir(parents=True, exist_ok=True)
    print(f"📦 Extracting {src.name} → {dst}")
    with zipfile.ZipFile(src, "r") as z:
        members = z.namelist()
        print(f"   {len(members)} files inside")
        for member in members:
            # Flatten — extract files directly into dst (no subdirs)
            target = dst / Path(member).name
            if member.endswith("/"):
                continue
            with z.open(member) as src_f, open(target, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)
    print(f"   ✅ Done")


def main():
    print("=" * 60)
    print("📦 Dataset Extraction")
    print("=" * 60)
    for src, dst in EXTRACTIONS:
        extract(src, dst)
    print("\n✅ All extractions complete")
    print("   Next: python preprocessing/run_pipeline.py")


if __name__ == "__main__":
    main()
