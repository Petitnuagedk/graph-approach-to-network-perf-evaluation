#!/usr/bin/env python3
"""
plot_results.py

Plots graph-run.cc results produced by run_pipeline.py.

    python3 plot_results.py --results <path> --outDir <dir>

--results is either
  * a directory holding one <label>/trace_replay_results.csv per DG (what
    run_pipeline.py's ns3-results/ looks like), or
  * a single trace_replay_results.csv.

Sweep results are aggregated over all graph-generation and replay epochs.
One trend figure is written per metric and swept parameter. The mean is shown
as a connected line, while box-and-whisker glyphs show the interquartile range
and full observed min-to-max range at each sweep point.

Writes into --outDir:
    summary.csv                 every raw result row
    aggregate.csv               distribution statistics by parameter value
                                and routing protocol
    <METRIC>_<parameter>.png       e.g. PDR_stab.png
"""

import argparse
import csv
import hashlib
import math
import random
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
    ("pdr",          "PDR",      "Packet delivery ratio",            1.0),
    ("goodput_mbps", "GOODPUT",  "Goodput (Mbps)",                   1.0),
    ("eed_mean_s",   "EED",      "Mean end-to-end delay (ms)",       1e3),
    ("routing_tx",   "RTX",      "Routing/control packets sent",     1.0),
    ("routing_efficiency", "ROUTING_EFFICIENCY", "PDR / oracle uptime ratio", 1.0),
    ("control_packets_per_delivered", "CONTROL_PACKETS_PER_DELIVERED",
     "Control packets per delivered data packet", 1.0),
    ("control_bytes_per_delivered", "CONTROL_BYTES_PER_DELIVERED",
     "Control bytes per delivered data packet", 1.0),
    ("oracle_uptime_ratio", "ORACLE_UPTIME", "Oracle S–R uptime ratio", 1.0),
    ("oracle_mean_up_run_s", "ORACLE_UP_RUN", "Mean oracle up-run (s)", 1.0),
]

PARAMETER_ALIASES = {
    "stability": "stab",
    "path_life": "lifetime",
    "pathPersistency": "persist",
}


def find_results(path: Path):
    """Return [(label, csv_path)] from a directory of per-label results or one file."""
    if path.is_file():
        return [(path.parent.name or "dg", path)]
    found = []
    for p in path.rglob(RESULTS_NAME):
        if p.parent.name.startswith("epoch_"):
            label = p.parent.parent.name
            # Pipeline labels are sweep-point names, graph epochs, or the
            # single-run label. Ignore ad-hoc nested smoke-test folders.
            if not (LABEL_RE.match(label) or label.startswith("graph_") or label == "dg"):
                continue
            found.append((label, p))
        elif not any(child.name.startswith("epoch_") for child in p.parent.iterdir() if child.is_dir()):
            found.append((p.parent.name, p))
    if not found and (path / RESULTS_NAME).exists():
        found = [(path.name, path / RESULTS_NAME)]
    if not found:
        raise FileNotFoundError(f"No {RESULTS_NAME} found under {path}")
    return found


def read_rows(entries):
    rows = []
    for label, csv_path in entries:
        # A graph epoch label includes the graph id before "__"; only the
        # sweep-point suffix identifies the parameter being plotted.
        point_label = label.split("__", 1)[-1]
        m = LABEL_RE.match(point_label)
        with open(csv_path, newline="") as fh:
            for r in csv.DictReader(fh):
                r["label"] = label
                r["param_name"] = m.group("name") if m else "run"
                r["param_value"] = float(m.group("value")) if m else 0.0
                r["realization_id"] = (label.split("__", 1)[0]
                                       if label.split("__", 1)[0].startswith("graph_")
                                       else label)
                r["replay_epoch"] = (csv_path.parent.name
                                     if csv_path.parent.name.startswith("epoch_") else "epoch_0001")
                rows.append(r)
    return rows


def num(row, col, scale=1.0):
    try:
        return float(row[col]) * scale
    except (KeyError, ValueError):
        return float("nan")


def quantile(values, probability):
    """Return a linearly interpolated quantile from a non-empty sequence."""
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def write_summary(rows, out_dir: Path):
    if not rows:
        return
    cols = list(rows[0].keys())
    with open(out_dir / "summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def write_aggregate(rows, out_dir: Path):
    groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = (r["param_name"], r["param_value"], r["protocol"])
        groups[key][r["realization_id"]].append(r)
    fields = ["param_name", "param_value", "protocol", "n_realizations", "n_epochs"]
    for col, _, _, _ in METRICS:
        fields.extend((f"{col}_mean", f"{col}_std", f"{col}_ci95_low", f"{col}_ci95_high"))
    out_rows = []
    aggregated = {}
    for (param, value, proto), realization_rows in sorted(groups.items()):
        realization_values = {}
        for col, _, _, scale in METRICS:
            per_realization = {}
            for realization, samples in realization_rows.items():
                values = [num(row, col, scale) for row in samples]
                values = [sample for sample in values if math.isfinite(sample)]
                if values:
                    per_realization[realization] = sum(values) / len(values)
            realization_values[col] = per_realization
        agg = {"param_name": param, "param_value": value, "protocol": proto,
               "n_realizations": len(realization_rows),
               "n_epochs": sum(len(samples) for samples in realization_rows.values())}
        for col, _, _, scale in METRICS:
            values = list(realization_values[col].values())
            if values:
                mean = sum(values) / len(values)
                std = (sum((sample - mean) ** 2 for sample in values) / len(values)) ** 0.5
                seed_key = f"{param}|{value}|{proto}|{col}".encode()
                seed = int.from_bytes(hashlib.sha256(seed_key).digest()[:8], "big")
                rng = random.Random(seed)
                boot_means = []
                for _ in range(2000):
                    draw = [values[rng.randrange(len(values))] for _ in values]
                    boot_means.append(sum(draw) / len(draw))
                agg[f"{col}_mean"] = mean
                agg[f"{col}_std"] = std
                agg[f"{col}_ci95_low"] = quantile(boot_means, 0.025)
                agg[f"{col}_ci95_high"] = quantile(boot_means, 0.975)
            else:
                for statistic in ("mean", "std", "ci95_low", "ci95_high"):
                    agg[f"{col}_{statistic}"] = ""
        out_rows.append(agg)
        aggregated[(param, value, proto)] = realization_values
    with open(out_dir / "aggregate.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)
    return aggregated


def plot_aggregated(groups, out_dir: Path):
    """Plot realization means with percentile-bootstrap 95% confidence intervals."""
    written = []
    parameters = sorted({param for param, _value, _proto in groups})
    for param in parameters:
        values = sorted({value for p, value, _proto in groups if p == param})
        protocols = sorted({proto for p, _value, proto in groups if p == param})
        gaps = [right - left for left, right in zip(values, values[1:]) if right > left]
        spacing = min(gaps) if gaps else 1.0
        group_width = spacing * 0.72
        offset_step = group_width / max(len(protocols), 1)
        for col, metric, ylabel, _scale in METRICS:
            if not any(values for (p, _v, _proto), data in groups.items()
                       if p == param for values in [data.get(col, {})]):
                continue
            fig, ax = plt.subplots(figsize=(8, 5))
            for protocol_index, proto in enumerate(protocols):
                offset = (protocol_index - (len(protocols) - 1) / 2) * offset_step
                positions, means, lower, upper = [], [], [], []
                for value in values:
                    samples = groups.get((param, value, proto), {}).get(col, {})
                    samples = list(samples.values())
                    samples = [sample for sample in samples if math.isfinite(sample)]
                    if not samples:
                        continue
                    positions.append(value + offset)
                    mean = sum(samples) / len(samples)
                    means.append(mean)
                    seed_key = f"{param}|{value}|{proto}|{col}".encode()
                    rng = random.Random(int.from_bytes(hashlib.sha256(seed_key).digest()[:8], "big"))
                    bootstrap = [sum(rng.choice(samples) for _ in samples) / len(samples)
                                 for _ in range(2000)]
                    low, high = quantile(bootstrap, 0.025), quantile(bootstrap, 0.975)
                    lower.append(max(0.0, mean - low))
                    upper.append(max(0.0, high - mean))
                if positions:
                    ax.errorbar(positions, means, yerr=[lower, upper], marker="o",
                                linewidth=1.8, markersize=4, capsize=3,
                                label=proto, zorder=3)
            ax.set_ylabel(ylabel)
            ax.set_xlabel(PARAMETER_ALIASES.get(param, param))
            ax.set_title(
                f"{metric} across {PARAMETER_ALIASES.get(param, param)} sweep\n"
                "Mean over graph realizations; bars are 95% bootstrap CI",
                fontsize=10,
            )
            ax.set_xticks(values)
            ax.grid(True, alpha=0.3)
            if protocols:
                ax.legend(title="Routing protocol")
            fig.tight_layout()
            alias = PARAMETER_ALIASES.get(param, param)
            out = out_dir / f"{metric}_{alias}.png"
            fig.savefig(out, dpi=150)
            plt.close(fig)
            written.append(out)
    return written


DG_PROPERTY_METRICS = {
    "uptime_ratio": "Achieved S–R uptime ratio",
    "mean_up_run_frames": "Mean consecutive up-run length (frames)",
    "path_identity_retention": "Shortest-route identity retention",
}


def plot_dg_properties(properties_root: Path, out_dir: Path):
    """Plot measured DG properties for each generated sweep point."""
    entries = []
    for csv_path in properties_root.rglob("properties.csv"):
        with csv_path.open(newline="") as stream:
            entries.extend(csv.DictReader(stream))
    entries = [row for row in entries if row.get("param_name") not in (None, "", "run")]
    if not entries:
        print(f"No swept DG property files found under {properties_root}")
        return []

    with (out_dir / "dg_properties_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(entries[0]))
        writer.writeheader()
        writer.writerows(entries)

    written = []
    parameters = sorted({row["param_name"] for row in entries})
    for param in parameters:
        values = sorted({float(row["param_value"]) for row in entries
                         if row["param_name"] == param})
        for metric, ylabel in DG_PROPERTY_METRICS.items():
            distributions = []
            means = []
            for value in values:
                samples = []
                for row in entries:
                    if row["param_name"] != param or float(row["param_value"]) != value:
                        continue
                    try:
                        sample = float(row[metric])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if math.isfinite(sample):
                        samples.append(sample)
                if samples:
                    distributions.append(samples)
                    means.append(sum(samples) / len(samples))
                else:
                    distributions.append([])
                    means.append(float("nan"))

            valid = [(value, samples, mean) for value, samples, mean
                     in zip(values, distributions, means) if samples]
            if not valid:
                continue
            fig, ax = plt.subplots(figsize=(8, 5))
            positions = [item[0] for item in valid]
            ax.boxplot(
                [item[1] for item in valid], positions=positions,
                widths=(min((b - a for a, b in zip(positions, positions[1:]) if b > a),
                            default=1.0) * 0.6),
                whis=(0, 100), showfliers=False,
            )
            ax.plot(positions, [item[2] for item in valid], marker="o",
                    linewidth=1.8, label="Mean across DG realizations")
            ax.set_xlabel(PARAMETER_ALIASES.get(param, param))
            ax.set_ylabel(ylabel)
            ax.set_title(f"Achieved dynamic-graph property across {param} sweep")
            ax.set_xticks(values)
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            output = out_dir / f"DG_{metric}_{PARAMETER_ALIASES.get(param, param)}.png"
            fig.savefig(output, dpi=150)
            plt.close(fig)
            written.append(output)
    return written


def main():
    ap = argparse.ArgumentParser(description="Plot graph-run.cc results")
    ap.add_argument("--results", type=Path,
                    help="ns3-results directory (one <label>/ per DG) or a single "
                         "trace_replay_results.csv")
    ap.add_argument("--outDir", type=Path, required=True)
    ap.add_argument("--dg-properties", type=Path, default=None,
                    help="Optional dynamic_frames root containing per-DG properties.csv files")
    ap.add_argument("--dg-properties-only", action="store_true",
                    help="Plot only measured DG properties; does not require ns-3 result CSVs")
    args = ap.parse_args()

    args.outDir.mkdir(parents=True, exist_ok=True)
    if args.dg_properties_only:
        if args.dg_properties is None:
            ap.error("--dg-properties is required with --dg-properties-only")
        written = plot_dg_properties(args.dg_properties, args.outDir)
        for output in written:
            print(f"Wrote {output}")
        return

    if args.results is None:
        ap.error("--results is required unless --dg-properties-only is selected")
    rows = read_rows(find_results(args.results))
    write_summary(rows, args.outDir)

    groups = write_aggregate(rows, args.outDir)
    written = plot_aggregated(groups, args.outDir)
    if args.dg_properties is not None and args.dg_properties.exists():
        written.extend(plot_dg_properties(args.dg_properties, args.outDir))

    print(f"Wrote {args.outDir / 'summary.csv'}")
    for p in written:
        print(f"Wrote {p}")


if __name__ == "__main__":
    main()