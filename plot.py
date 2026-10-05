#!/usr/bin/env python3
"""
plot_results.py

Plots graph-run.cc results produced by run_pipeline.py.

    python3 plot_results.py --results <path> --outDir <dir>

--results is either
  * a directory holding one <label>/trace_replay_results.csv per DG (what
    run_pipeline.py's ns3-results/ looks like), or
  * a single trace_replay_results.csv.

Labels are "dg" for a single DG, or "<param>_<value>" (e.g. stability_0.3000)
for a sweep point. With >= 2 sweep points the metrics are drawn against the
swept parameter, one line per routing protocol; with a single DG they are
drawn as grouped bars per protocol.

Writes into --outDir:
    summary.csv                 every row of every results file, plus the
                                parsed param_name / param_value
    metrics_<param>.png         (sweep)  or  metrics.png  (single DG)
"""

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless: only ever writes files
import matplotlib.pyplot as plt

RESULTS_NAME = "trace_replay_results.csv"
LABEL_RE = re.compile(r"^(?P<name>.+)_(?P<value>-?\d+(?:\.\d+)?)$")

# (column, axis label, scale applied to the raw value)
METRICS = [
    ("pdr",          "Packet delivery ratio",            1.0),
    ("goodput_mbps", "Goodput (Mbps)",                   1.0),
    ("eed_mean_s",   "Mean end-to-end delay (ms)",       1e3),
    ("routing_tx",   "Routing/control packets sent",     1.0),
]


def find_results(path: Path):
    """Return [(label, csv_path)] from a directory of per-label results or one file."""
    if path.is_file():
        return [(path.parent.name or "dg", path)]
    found = sorted((p.parent.name, p) for p in path.glob(f"*/{RESULTS_NAME}"))
    if not found and (path / RESULTS_NAME).exists():
        found = [(path.name, path / RESULTS_NAME)]
    if not found:
        raise FileNotFoundError(f"No {RESULTS_NAME} found under {path}")
    return found


def read_rows(entries):
    rows = []
    for label, csv_path in entries:
        m = LABEL_RE.match(label)
        with open(csv_path, newline="") as fh:
            for r in csv.DictReader(fh):
                r["label"] = label
                r["param_name"] = m.group("name") if m else ""
                r["param_value"] = float(m.group("value")) if m else float("nan")
                rows.append(r)
    return rows


def num(row, col, scale=1.0):
    try:
        return float(row[col]) * scale
    except (KeyError, ValueError):
        return float("nan")


def write_summary(rows, out_dir: Path):
    if not rows:
        return
    cols = list(rows[0].keys())
    with open(out_dir / "summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def plot_sweep(rows, param_name, out_dir: Path):
    """Produce one figure per network metric for a parameter sweep."""
    by_proto = defaultdict(list)
    for r in rows:
        by_proto[r["protocol"]].append(r)

    written = []

    for col, ylabel, scale in METRICS:
        fig, ax = plt.subplots(figsize=(9, 6))

        for proto, rs in sorted(by_proto.items()):
            rs = sorted(rs, key=lambda r: r["param_value"])
            ax.plot(
                [r["param_value"] for r in rs],
                [num(r, col, scale) for r in rs],
                marker="o",
                label=proto,
            )

        ax.set_xlabel(param_name)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(title="routing")
        ax.set_title(f"{ylabel} vs {param_name}")
        fig.tight_layout()

        metric_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", col)
        out = out_dir / f"metrics_{param_name}_{metric_name}.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)
        written.append(out)

    return written


def plot_single(rows, out_dir: Path):
    protos = sorted({r["protocol"] for r in rows})
    by_proto = {r["protocol"]: r for r in rows}

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    for ax, (col, ylabel, scale) in zip(axes.flat, METRICS):
        ax.bar(protos, [num(by_proto[p], col, scale) for p in protos])
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.3)
    fig.suptitle("ns-3 replay results")
    fig.tight_layout()
    out = out_dir / "metrics.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser(description="Plot graph-run.cc results")
    ap.add_argument("--results", type=Path, required=True,
                    help="ns3-results directory (one <label>/ per DG) or a single "
                         "trace_replay_results.csv")
    ap.add_argument("--outDir", type=Path, required=True)
    args = ap.parse_args()

    args.outDir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(find_results(args.results))
    write_summary(rows, args.outDir)

    swept = defaultdict(list)
    for r in rows:
        if r["param_name"]:
            swept[r["param_name"]].append(r)

    written = []
    for param_name, rs in swept.items():
        if len({r["param_value"] for r in rs}) >= 2:
            written.extend(plot_sweep(rs, param_name, args.outDir))
    if not written:
        # single DG (label "dg"), or a sweep that only produced one point
        written.append(plot_single(rows, args.outDir))

    print(f"Wrote {args.outDir / 'summary.csv'}")
    for p in written:
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()