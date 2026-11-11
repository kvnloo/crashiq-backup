r"""Compare our conflict finder with FHWA's SSAM on a folder of .trj files (#484).

    python -m crashiq.ssam.compare <folder> --exe C:\path\SSAM_MT.exe [--ttc 1.5] [--pet 5.0] [--out report.txt]
    python -m crashiq.ssam.compare <folder> --fhwa-csv saved.csv     (reuse a saved SSAM_MT conflict CSV, no exe)

FHWA's SSAM_MT.exe is run as a black box. Conflicts are matched per file by vehicle pair (either order), in time
order within a pair. The report lists conflicts found by both, only by FHWA and only by us, type agreement, and the
TTC/PET differences (median and worst, with the pair).
"""

from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import sys
from pathlib import Path

from .conflicts import find_conflicts
from .trj import read_trj


def _norm_type(v) -> str:
    """'Rear End', 'rear-end', 'REAR_END' -> 'rear-end'. Other values (e.g. numeric codes) are kept as written."""
    s = "".join(ch for ch in str(v).lower() if ch.isalpha())
    return {"rearend": "rear-end", "lanechange": "lane-change", "crossing": "crossing"}.get(s, str(v).strip())


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def read_fhwa_csv(path) -> dict[str, list[dict]]:
    """SSAM conflict-table CSV -> {trj file stem (lower case): [conflict]}. Columns are found by name."""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    for h, header in enumerate(rows):
        names = [c.strip().lower() for c in header]
        if "firstvid" in names and "secondvid" in names and "ttc" in names:
            break
    else:
        raise ValueError(f"{path}: no conflict-table header (FirstVID, SecondVID, TTC) found")
    col = {n: i for i, n in enumerate(names)}
    get = lambda r, n: r[col[n]].strip() if n in col and col[n] < len(r) else ""
    out: dict[str, list[dict]] = {}
    for r in rows[h + 1:]:
        if not r or not get(r, "firstvid"):
            continue
        stem = Path(get(r, "trjfile").replace("\\", "/")).stem.lower()
        out.setdefault(stem, []).append({
            "FirstVID": int(float(get(r, "firstvid"))), "SecondVID": int(float(get(r, "secondvid"))),
            "tMinTTC": _num(get(r, "tminttc")), "TTC": _num(get(r, "ttc")), "PET": _num(get(r, "pet")),
            "ConflictType": _norm_type(get(r, "conflicttype"))})
    return out


def run_fhwa(exe, files: list[Path], csv_out: Path, ttc: float, pet: float) -> None:
    trj = ",".join(f'"{p.resolve()}"' for p in files)
    cmd = f'"{Path(exe).resolve()}" trjfiles={trj} csvfile="{csv_out.resolve()}" ttc={ttc} pet={pet}'
    rc = subprocess.run(cmd, cwd=str(Path(exe).resolve().parent), shell=sys.platform == "win32").returncode
    if rc == 0xC0000135:  # Windows "DLL not found"
        raise RuntimeError("SSAM_MT.exe could not start: install the Microsoft Visual C++ 2012 x64 runtime")
    if rc != 0:
        raise RuntimeError(f"SSAM_MT.exe exited with code {rc}: {cmd}")
    if not csv_out.exists():
        raise RuntimeError(f"SSAM_MT wrote no CSV: {cmd}")


def _match(ours: list[dict], theirs: list[dict]):
    """Pairs (ours, theirs) per unordered vehicle pair, in tMinTTC order; unmatched ones come back with None."""
    group = lambda cs: {k: sorted((c for c in cs if frozenset((c["FirstVID"], c["SecondVID"])) == k),
                                  key=lambda c: c["tMinTTC"] or 0.0)
                        for k in {frozenset((c["FirstVID"], c["SecondVID"])) for c in cs}}
    go, gt = group(ours), group(theirs)
    out = []
    for k in sorted(go.keys() | gt.keys(), key=sorted):
        a, b = go.get(k, []), gt.get(k, [])
        out += [(a[i] if i < len(a) else None, b[i] if i < len(b) else None) for i in range(max(len(a), len(b)))]
    return out


def compare(ours: dict[str, list[dict]], fhwa: dict[str, list[dict]]) -> tuple[dict, str]:
    """Both inputs {file stem: conflicts}. Returns (summary numbers, plain-text report)."""
    both, only_f, only_o, type_diff, d_ttc, d_pet = [], [], [], [], [], []
    for stem in sorted(ours.keys() | fhwa.keys()):
        for o, f in _match(ours.get(stem, []), fhwa.get(stem, [])):
            c = o or f
            label = f"{stem}: vehicles {c['FirstVID']}-{c['SecondVID']} at t={c['tMinTTC'] if c['tMinTTC'] is None else round(c['tMinTTC'], 2)}"
            if o is None:
                only_f.append(label)
                continue
            if f is None:
                only_o.append(label)
                continue
            both.append(label)
            if o["ConflictType"] != f["ConflictType"]:
                type_diff.append(f"{label}: ours {o['ConflictType']}, FHWA {f['ConflictType']}")
            if o["TTC"] is not None and f["TTC"] is not None:
                d_ttc.append((round(abs(o["TTC"] - f["TTC"]), 3), label))
            if o["PET"] is not None and f["PET"] is not None:
                d_pet.append((round(abs(o["PET"] - f["PET"]), 3), label))

    def spread(name, ds):
        if not ds:
            return f"{name} difference: no matched values"
        worst = max(ds)
        return f"{name} difference (s): median {statistics.median(d for d, _ in ds):.3f}, worst {worst[0]:.3f} ({worst[1]})"

    summary = {"both": len(both), "only_fhwa": len(only_f), "only_ours": len(only_o),
               "type_agree": len(both) - len(type_diff), "type_differ": len(type_diff),
               "ttc_worst": max(d_ttc)[0] if d_ttc else None, "pet_worst": max(d_pet)[0] if d_pet else None}
    lines = ["CrashIQ conflicts vs FHWA SSAM", f"Files: {', '.join(sorted(ours.keys() | fhwa.keys()))}", "",
             f"Found by both: {len(both)}", f"Only FHWA: {len(only_f)}", f"Only CrashIQ: {len(only_o)}",
             f"Same type: {summary['type_agree']} of {len(both)}", spread("TTC", d_ttc), spread("PET", d_pet)]
    for title, items in (("Only FHWA", only_f), ("Only CrashIQ", only_o), ("Type differs", type_diff)):
        if items:
            lines += ["", f"{title}:"] + [f"  {s}" for s in items]
    return summary, "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m crashiq.ssam.compare", description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path, help="folder of .trj files")
    ap.add_argument("--ttc", type=float, default=1.5)
    ap.add_argument("--pet", type=float, default=5.0)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--exe", help="path to FHWA's SSAM_MT.exe (run as a black box)")
    src.add_argument("--fhwa-csv", type=Path, help="a saved SSAM_MT conflict CSV instead of running the exe")
    ap.add_argument("--out", type=Path, help="write the report here (default: <folder>/ssam_compare.txt)")
    a = ap.parse_args(argv)
    if not a.folder.is_dir():
        ap.error(f"not a folder: {a.folder}")
    files = sorted(p for p in a.folder.iterdir() if p.suffix.lower() == ".trj")
    if not files:
        ap.error(f"no .trj files in {a.folder}")
    csv_path = a.fhwa_csv
    if csv_path is None:
        csv_path = a.folder / "fhwa_ssam.csv"
        run_fhwa(a.exe, files, csv_path, a.ttc, a.pet)
    ours = {p.stem.lower(): find_conflicts(read_trj(p), a.ttc, a.pet) for p in files}
    _, report = compare(ours, read_fhwa_csv(csv_path))
    report += f"\nSettings: TTC {a.ttc} s, PET {a.pet} s. FHWA conflicts from {csv_path}.\n"
    out = a.out or a.folder / "ssam_compare.txt"
    out.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
