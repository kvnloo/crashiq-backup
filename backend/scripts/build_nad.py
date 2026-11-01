"""Build the NAD address-point index (data/cache/nad/nad_ca.sqlite) ahead of the first pull that needs it (#283), from
data/cache/nad/nad_ca_r24.csv (California rows of USDOT NAD r24; knowledge/sources/us-nad.md). About 4 minutes; no
network. Without this, the first house-address crash a pull meets builds it.

Run:  python backend/scripts/build_nad.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from crashiq import nad  # noqa: E402
from crashiq.settings import Settings  # noqa: E402

if __name__ == "__main__":
    s = Settings()
    idx = nad.addresses(s.nad_dir, s.addrfeat_dir).nad
    if not idx.ready():
        sys.exit(f"No {idx.csv_path}: put the NAD California CSV there first (knowledge/sources/us-nad.md).")
    print(f"NAD index ready: {idx.db_path}")
