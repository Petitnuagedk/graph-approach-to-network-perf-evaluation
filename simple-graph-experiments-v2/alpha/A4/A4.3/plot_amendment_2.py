#!/usr/bin/env python3
"""Replot the combined A4.3 phi 1--10 extension using the existing plotter."""
import csv
import sys
from pathlib import Path
import plot_a43 as base

root = Path(__file__).resolve().parent
combined = root / "per_run_amendment_2.csv"
with (root / "per_run_amendment_1.csv").open(newline="", encoding="utf-8") as first:
    old = list(csv.DictReader(first))
with (root / "per_run_amendment_2.csv").open(newline="", encoding="utf-8") as second:
    new = list(csv.DictReader(second))
fields = list(old[0])
with combined.open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(old)
    writer.writerows(new)

base.PHIS = list(range(1, 11))
_original_read_rows = base.read_rows
def read_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = [dict(row) for row in csv.DictReader(stream)]
    rows = [row for row in rows if row.get("status") in {"success", "reused"}]
    if len(rows) != 100 or any(row.get("N") != "42" for row in rows):
        raise SystemExit(f"Expected 100 combined corrected N=42 rows, found {len(rows)}")
    return rows
base.read_rows = read_rows
sys.argv = [sys.argv[0], "--data", str(combined), "--output-dir", str(root / "plots_amendment_2")]
base.main()
