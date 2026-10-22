"""Load FARS (NHTSA) California accident rows into the app database: the reference store for fatal crashes (#174).

Refresh once a year, when NHTSA publishes a new FARS year (usually in spring, for the year before last), then pull
fresh crash data so studies pick it up. How and why: data/reference/fars.md.

    # from the official national files (downloads ~35 MB per year, keeps only California rows):
    python backend/scripts/load_fars.py --download 2021 2022 2023 2024
    # from accident.csv files already on disk (national, or California rows only):
    python backend/scripts/load_fars.py --csv path/to/accident_2024.csv ...
    # which database: CRASHIQ_DB (default data/crashiq.sqlite); --db to override
"""
import argparse, io, os, sys, tempfile, urllib.request, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crashiq import fars                                       # noqa: E402
from crashiq.db import Database                                # noqa: E402
from crashiq.settings import ROOT                              # noqa: E402

URL = "https://static.nhtsa.gov/nhtsa/downloads/FARS/{y}/National/FARS{y}NationalCSV.zip"


def download(year: int) -> tuple[bytes, str]:
    url = URL.format(y=year)
    with urllib.request.urlopen(url, timeout=300) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    name = next(n for n in z.namelist() if n.lower().endswith("accident.csv"))
    return z.read(name), f"{url}#{name}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", nargs="*", type=int, default=[])
    ap.add_argument("--csv", nargs="*", default=[])
    ap.add_argument("--db", default=os.environ.get("CRASHIQ_DB", str(ROOT / "data" / "crashiq.sqlite")))
    a = ap.parse_args()
    db = Database(a.db)
    for y in a.download:
        data, src = download(y)
        with tempfile.NamedTemporaryFile(suffix=".csv") as f:
            f.write(data)
            f.flush()
            print(y, fars.load_csv(db, f.name, src), "California rows from", src)
    for p in a.csv:
        print(p, fars.load_csv(db, p), "California rows")
    print("FARS years loaded:", fars.years_loaded(db))


if __name__ == "__main__":
    main()
