r"""Compare our conflict finder with FHWA's SSAM on a folder of .trj files (#484).

    python -m crashiq.ssam.compare <folder> --exe C:\path\SSAM_MT.exe [--ttc 1.5] [--pet 5.0] [--out report.txt]
    python -m crashiq.ssam.compare <folder> --fhwa-dir <dir>     (reuse saved SSAM_MT CSVs, <dir>/<stem>.csv, no exe)

FHWA's SSAM_MT.exe is run as a black box, once per .trj: its conflict listing has no file column. Its CSVs are kept
in <folder>/fhwa/<stem>.csv. SSAM_MT writes no CSV when a file has no conflicts, so a missing CSV is zero conflicts.
Conflicts are matched per file by vehicle pair (either order), in time order within a pair. The report lists
conflicts found by both, only by FHWA and only by us, type agreement, and the TTC/PET differences (median and
worst, with the pair).
"""

from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path

from .conflicts import find_conflicts
from .trj import read_trj


def _norm_type(v) -> str:
    """'rear end', 'Rear-End', 'lane change' -> 'rear-end', 'lane-change'. Other values are kept as written."""
    s = "".join(ch for ch in str(v).lower() if ch.isalpha())
    return {"rearend": "rear-end", "lanechange": "lane-change", "crossing": "crossing"}.get(s, str(v).strip())


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def read_fhwa_csv(path) -> list[dict]:
    """One SSAM_MT CSV -> its conflicts. Skips the summary block; reads the table after 'Conflict Listing,<n>'."""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        rows = list(csv.reader(f))
    h = next((i + 1 for i, r in enumerate(rows) if r and r[0].strip().lower() == "conflict listing"), None)
    if h is None or h >= len(rows):
        raise ValueError(f"{path}: no 'Conflict Listing' table (not an SSAM_MT CSV)")
    names = [c.strip().lower().replace("fristvid", "firstvid") for c in rows[h]]  # 'FristVID' is FHWA's spelling
    col = {n: i for i, n in enumerate(names)}
    if not {"firstvid", "secondvid", "ttc", "pet", "conflicttype", "time (min ttc)"} <= col.keys():
        raise ValueError(f"{path}: conflict table header lacks FirstVID/SecondVID/TTC/PET/ConflictType/Time")
    get = lambda r, n: r[col[n]].strip() if col[n] < len(r) else ""
    out = [{"FirstVID": int(float(get(r, "firstvid"))), "SecondVID": int(float(get(r, "secondvid"))),
            "tMinTTC": _num(get(r, "time (min ttc)")), "TTC": _num(get(r, "ttc")), "PET": _num(get(r, "pet")),
            "ConflictType": _norm_type(get(r, "conflicttype"))}
           for r in rows[h + 1:] if r and get(r, "firstvid")]
    n = _num(rows[h - 1][1]) if len(rows[h - 1]) > 1 else None
    if n is not None and int(n) != len(out):
        raise ValueError(f"{path}: 'Conflict Listing' says {int(n)} conflicts, the table has {len(out)}")
    return out


def run_fhwa(exe, trj: Path, csv_out: Path, ttc: float, pet: float) -> list[dict]:
    """Run SSAM_MT.exe on one .trj; its conflicts. Paths go unquoted: SSAM_MT rejects quoted paths."""
    csv_out.unlink(missing_ok=True)
    exe = Path(exe).resolve()
    cmd = [str(exe), f"trjfiles={trj.resolve()}", f"csvfile={csv_out.resolve()}", f"ttc={ttc}", f"pet={pet}"]
    r = subprocess.run(cmd, cwd=str(exe.parent), capture_output=True, text=True, errors="replace")
    if r.returncode == 0xC0000135:  # Windows "DLL not found"
        raise RuntimeError("SSAM_MT.exe could not start: install the Microsoft Visual C++ 2012 x64 runtime")
    if r.returncode != 0 or "Analysis complete" not in r.stdout:
        raise RuntimeError(f"SSAM_MT.exe failed on {trj} (exit {r.returncode}): {r.stdout[-500:]}")
    return read_fhwa_csv(csv_out) if csv_out.exists() else []  # no CSV = no conflicts


MATCH_S = 2.0  # two conflicts of the same pair match when their tMinTTC are at most this far apart


def _match(ours: list[dict], theirs: list[dict]):
    """Pairs (ours, theirs) per unordered vehicle pair, aligned in tMinTTC order (within MATCH_S); unmatched ones
    come back with None. The engines can split one long interaction into a different number of events."""
    pair = lambda c: frozenset((c["FirstVID"], c["SecondVID"]))
    when = lambda c: c["tMinTTC"] or 0.0
    go, gt = {}, {}
    for cs, g in ((ours, go), (theirs, gt)):
        for c in sorted(cs, key=when):
            g.setdefault(pair(c), []).append(c)
    out = []
    for k in sorted(go.keys() | gt.keys(), key=sorted):
        a, b, i, j = go.get(k, []), gt.get(k, []), 0, 0
        while i < len(a) or j < len(b):
            if i < len(a) and j < len(b) and abs(when(a[i]) - when(b[j])) <= MATCH_S:
                out.append((a[i], b[j]))
                i, j = i + 1, j + 1
            elif j >= len(b) or (i < len(a) and when(a[i]) < when(b[j])):
                out.append((a[i], None))
                i += 1
            else:
                out.append((None, b[j]))
                j += 1
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
                only_o.append(label + (" (no PET)" if o["PET"] is None else ""))
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
               "only_ours_no_pet": sum(x.endswith("(no PET)") for x in only_o),
               "type_agree": len(both) - len(type_diff), "type_differ": len(type_diff),
               "ttc_worst": max(d_ttc)[0] if d_ttc else None, "pet_worst": max(d_pet)[0] if d_pet else None}
    lines = ["CrashIQ conflicts vs FHWA SSAM", f"Files: {', '.join(sorted(ours.keys() | fhwa.keys()))}", "",
             f"Found by both: {len(both)}", f"Only FHWA: {len(only_f)}",
             f"Only CrashIQ: {len(only_o)} ({summary['only_ours_no_pet']} with no PET)",
             f"Same type: {summary['type_agree']} of {len(both)}", spread("TTC", d_ttc), spread("PET", d_pet)]
    for title, items in (("Only FHWA", only_f), ("Only CrashIQ", only_o), ("Type differs", type_diff)):
        if items:
            lines += ["", f"{title}:"] + [f"  {s}" for s in items]
    return summary, "\n".join(lines) + "\n"


def _ours(path: Path, ttc: float, pet: float) -> list[dict]:
    return find_conflicts(read_trj(path), ttc, pet)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m crashiq.ssam.compare", description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path, help="folder of .trj files")
    ap.add_argument("--ttc", type=float, default=1.5)
    ap.add_argument("--pet", type=float, default=5.0)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--exe", help="path to FHWA's SSAM_MT.exe (run as a black box)")
    src.add_argument("--fhwa-dir", type=Path, help="saved SSAM_MT CSVs, one <stem>.csv per .trj, instead of the exe")
    ap.add_argument("--out", type=Path, help="write the report here (default: <folder>/ssam_compare.txt)")
    a = ap.parse_args(argv)
    if not a.folder.is_dir():
        ap.error(f"not a folder: {a.folder}")
    files = sorted(p for p in a.folder.iterdir() if p.suffix.lower() == ".trj")
    if not files:
        ap.error(f"no .trj files in {a.folder}")
    t0 = time.perf_counter()
    if a.exe:
        (a.folder / "fhwa").mkdir(exist_ok=True)
        fhwa = {p.stem.lower(): run_fhwa(a.exe, p, a.folder / "fhwa" / f"{p.stem}.csv", a.ttc, a.pet) for p in files}
        src_note = f"SSAM_MT.exe run now, CSVs in {a.folder / 'fhwa'}"
        fhwa_s = f"{time.perf_counter() - t0:.1f} s"
    else:
        saved = {p.stem.lower(): p for p in a.fhwa_dir.glob("*.csv")}
        fhwa = {p.stem.lower(): read_fhwa_csv(saved[p.stem.lower()]) if p.stem.lower() in saved else [] for p in files}
        src_note = f"saved SSAM_MT CSVs in {a.fhwa_dir} (no CSV = no conflicts)"
        fhwa_s = "not run (saved CSVs)"
    t0 = time.perf_counter()
    with ProcessPoolExecutor() as pool:  # one process per .trj file
        ours = dict(zip((p.stem.lower() for p in files), pool.map(_ours, files, repeat(a.ttc), repeat(a.pet))))
    ours_s = f"{time.perf_counter() - t0:.1f} s"
    _, report = compare(ours, fhwa)
    report += (f"\nSettings: TTC {a.ttc} s, PET {a.pet} s. FHWA conflicts from {src_note}.\n"
               f"Wall-clock: FHWA SSAM_MT {fhwa_s}, CrashIQ {ours_s} ({len(files)} files, one process each).\n")
    out = a.out or a.folder / "ssam_compare.txt"
    out.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
