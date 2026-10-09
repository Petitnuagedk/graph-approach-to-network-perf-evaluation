#!/usr/bin/env python3
"""Corrected Phase 5 replay statistics and measured-feature analysis for Phase 6E."""
from __future__ import annotations

import csv
import hashlib
import itertools
import math
import random
import statistics
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from oracle_metrics import compute_oracle_metrics, compute_traffic_window_usable_uptime

PHASE5 = ROOT / "simple-graph-experiments-v2" / "phase5"
OUT = Path(__file__).resolve().parent
TOPOLOGIES = ("line", "ladder", "two-lines")
PARAMETERS = ("pathPersistency", "path_life", "stability")
PROTOCOLS = ("olsr", "aodv", "static")
PAIRED = tuple(itertools.combinations(PROTOCOLS, 2))
BOOTSTRAPS = 5000


def read_frames(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    labels = [value.strip() for value in rows[0]]
    frames, matrix = [], []
    for row in rows[1:]:
        if not row or not any(value.strip() for value in row):
            if matrix:
                frames.append(matrix)
                matrix = []
        else:
            matrix.append([int(value) for value in row])
    if matrix:
        frames.append(matrix)
    return labels, frames


def read_csv(path: Path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def sample_sd(values):
    finite = [value for value in values if math.isfinite(float(value))]
    return statistics.stdev(finite) if len(finite) > 1 else (0.0 if finite else float("nan"))


def quantile(values, q):
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    frac = position - low
    return ordered[low] * (1.0 - frac) + ordered[high] * frac


def bootstrap_mean_ci(values, seed):
    values = [value for value in values if math.isfinite(float(value))]
    if not values:
        return float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(values)
    means = [statistics.mean(values[rng.randrange(n)] for _ in range(n)) for _ in range(BOOTSTRAPS)]
    return quantile(means, 0.025), quantile(means, 0.975)


def stable_seed(*parts):
    encoded = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:4], "big")


def linear_fit(rows, x_names, y_name):
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("numpy is required for the preregistered least-squares summaries") from exc
    valid = [row for row in rows
             if all(math.isfinite(float(row[name])) for name in x_names)
             and math.isfinite(float(row[y_name]))]
    if len(valid) < len(x_names) + 1:
        return [float("nan")] * (len(x_names) + 1), float("nan")
    x = np.asarray([[1.0] + [float(row[name]) for name in x_names] for row in valid], dtype=float)
    y = np.asarray([float(row[y_name]) for row in valid], dtype=float)
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    predicted = x @ coefficients
    residual = float(((y - predicted) ** 2).sum())
    total = float(((y - y.mean()) ** 2).sum())
    return coefficients, 1.0 - residual / total if total > 0 else 0.0


def collect_realizations():
    records = []
    for topology in TOPOLOGIES:
        for parameter in PARAMETERS:
            frames_root = PHASE5 / topology / parameter / "dynamic_frames"
            for graph_dir in sorted(frames_root.glob("graph_*")):
                for trace_dir in sorted(path for path in graph_dir.iterdir() if path.is_dir()):
                    frames_path = trace_dir / "frames.csv"
                    labels, frames = read_frames(frames_path)
                    source, destination = labels.index("S"), labels.index("R")
                    oracle = compute_oracle_metrics(frames, source, destination)
                    usable = compute_traffic_window_usable_uptime(
                        frames, source, destination, 0.1, len(frames) - 1,
                        frame_duration_s=1.0, link_up_loss_db=10.0,
                        link_down_loss_db=125.0, tx_power_dbm=20.0,
                        rx_sensitivity_dbm=-101.0, sparse_threshold_db=150.0,
                        default_loss_db=1e6, interpolate=True,
                    )
                    graph_id, cell = graph_dir.name, trace_dir.name
                    result_dir = PHASE5 / topology / parameter / "ns3-results" / f"{graph_id}__{cell}"
                    epoch_paths = sorted(result_dir.glob("epoch_*/trace_replay_results.csv"))
                    if not epoch_paths:
                        legacy = result_dir / "trace_replay_results.csv"
                        epoch_paths = [legacy] if legacy.exists() else []
                    if not epoch_paths:
                        raise FileNotFoundError(f"No replay CSVs in {result_dir}")
                    protocol_epoch_pdrs = {protocol: [] for protocol in PROTOCOLS}
                    for epoch_path in epoch_paths:
                        for row in read_csv(epoch_path):
                            if row["protocol"] in protocol_epoch_pdrs:
                                protocol_epoch_pdrs[row["protocol"]].append(float(row["pdr"]))
                    pdr = {protocol: statistics.mean(values) if values else float("nan")
                           for protocol, values in protocol_epoch_pdrs.items()}
                    record = {
                        "topology": topology, "parameter": parameter, "cell": cell,
                        "parameter_value": float(cell.rsplit("_", 1)[1]),
                        "graph_id": graph_id, "replay_epochs": len(epoch_paths),
                        "trace_frames": len(frames), "raw_frame_uptime": oracle["uptime_ratio"],
                        "usable_traffic_uptime": usable["usable_uptime_ratio"],
                        "mean_up_run_s": oracle["mean_up_run_s"],
                        "transition_count": oracle["transition_count"],
                        "path_identity_retention": oracle["path_identity_retention"],
                        "frame0_connected": int(oracle["connected"][0]),
                        "frame0_up": int(oracle["connected"][0]),
                        "mean_outage_s": statistics.mean(oracle["outage_durations_s"])
                            if oracle["outage_durations_s"] else 0.0,
                        "source_frames_path": str(frames_path.relative_to(ROOT)),
                    }
                    for protocol in PROTOCOLS:
                        record[f"{protocol}_pdr"] = pdr[protocol]
                        record[f"{protocol}_normalized_to_static"] = (
                            pdr[protocol] / pdr["static"] if pdr["static"] > 0 else float("nan")
                        )
                    records.append(record)
    return records


def cell_statistics(records):
    summaries, paired = [], []
    grouped = {}
    for record in records:
        grouped.setdefault((record["topology"], record["parameter"], record["cell"]), []).append(record)
    for group_key, rows in sorted(grouped.items()):
        topology, parameter, cell = group_key
        for protocol in PROTOCOLS:
            pdr_values = [row[f"{protocol}_pdr"] for row in rows
                          if math.isfinite(float(row[f"{protocol}_pdr"]))]
            normalized = [row[f"{protocol}_normalized_to_static"] for row in rows
                          if math.isfinite(float(row[f"{protocol}_normalized_to_static"]))]
            lo, hi = bootstrap_mean_ci(pdr_values, stable_seed(*group_key, protocol, "pdr"))
            nlo, nhi = bootstrap_mean_ci(normalized, stable_seed(*group_key, protocol, "norm"))
            summaries.append({
                "topology": topology, "parameter": parameter, "cell": cell,
                "realizations": len(pdr_values), "protocol": protocol,
                "pdr_mean": statistics.mean(pdr_values) if pdr_values else float("nan"),
                "pdr_median": statistics.median(pdr_values) if pdr_values else float("nan"),
                "pdr_sample_sd_ddof1": sample_sd(pdr_values), "pdr_bootstrap_ci95_low": lo,
                "pdr_bootstrap_ci95_high": hi,
                "normalized_to_static_mean": statistics.mean(normalized) if normalized else float("nan"),
                "normalized_to_static_median": statistics.median(normalized) if normalized else float("nan"),
                "normalized_to_static_sample_sd_ddof1": sample_sd(normalized),
                "normalized_to_static_bootstrap_ci95_low": nlo,
                "normalized_to_static_bootstrap_ci95_high": nhi,
            })
        for left, right in PAIRED:
            differences = [row[f"{left}_pdr"] - row[f"{right}_pdr"] for row in rows
                           if math.isfinite(float(row[f"{left}_pdr"]))
                           and math.isfinite(float(row[f"{right}_pdr"]))]
            lo, hi = bootstrap_mean_ci(differences, stable_seed(*group_key, left, right))
            paired.append({
                "topology": topology, "parameter": parameter, "cell": cell,
                "realizations": len(differences), "protocol_left": left, "protocol_right": right,
                "paired_difference_mean": statistics.mean(differences) if differences else float("nan"),
                "paired_difference_median": statistics.median(differences) if differences else float("nan"),
                "paired_difference_sample_sd_ddof1": sample_sd(differences),
                "paired_bootstrap_ci95_low": lo, "paired_bootstrap_ci95_high": hi,
                "per_realization_differences": ";".join(f"{value:.8f}" for value in differences),
            })
    return summaries, paired


def measured_feature_models(records):
    outputs = []
    feature_names = ("usable_traffic_uptime", "mean_up_run_s", "transition_count",
                     "path_identity_retention", "frame0_up")
    for topology in TOPOLOGIES:
        topology_rows = [row for row in records if row["topology"] == topology]
        for protocol in PROTOCOLS:
            y_name = f"{protocol}_pdr"
            for feature in feature_names:
                valid_count = sum(
                    math.isfinite(float(row[feature])) and math.isfinite(float(row[y_name]))
                    for row in topology_rows
                )
                coefficients, r2 = linear_fit(topology_rows, [feature], y_name)
                outputs.append({
                    "topology": topology, "protocol": protocol, "model": f"pdr~{feature}",
                    "n_trace_realizations": valid_count, "feature": feature,
                    "slope": float(coefficients[1]), "intercept": float(coefficients[0]),
                    "r_squared": r2,
                    "warning": "Descriptive only: Phase 6C found one distinct S-R timeline per cell across five DG seeds.",
                })

    attenuation = []
    for topology in TOPOLOGIES:
        for parameter in ("stability", "pathPersistency"):
            sweep_rows = [row for row in records if row["topology"] == topology and row["parameter"] == parameter]
            for protocol in PROTOCOLS:
                y_name = f"{protocol}_pdr"
                raw, raw_r2 = linear_fit(sweep_rows, ["parameter_value"], y_name)
                adjusted, adjusted_r2 = linear_fit(sweep_rows, ["parameter_value", "mean_up_run_s"], y_name)
                raw_beta, adjusted_beta = float(raw[1]), float(adjusted[1])
                attenuation_fraction = ((raw_beta - adjusted_beta) / raw_beta
                                        if abs(raw_beta) > 1e-12 else float("nan"))
                attenuation.append({
                    "topology": topology, "swept_parameter": parameter, "protocol": protocol,
                    "n_realization_rows": len(sweep_rows),
                    "distinct_parameter_values": len({r["parameter_value"] for r in sweep_rows}),
                    "unadjusted_parameter_slope": raw_beta, "unadjusted_r_squared": raw_r2,
                    "adjusted_parameter_slope_controlling_mean_up_run": adjusted_beta,
                    "adjusted_r_squared": adjusted_r2,
                    "signed_slope_attenuation_fraction": attenuation_fraction,
                    "warning": "Only five unique sweep values; repeated DG seeds share identical S-R timelines within cells.",
                })
    return outputs, attenuation


def ladder_aodv_spread(records):
    grouped = {}
    for row in records:
        if row["topology"] == "ladder" and math.isfinite(row["aodv_pdr"]):
            grouped.setdefault((row["parameter"], row["cell"]), []).append(row)
    features = ("usable_traffic_uptime", "mean_up_run_s", "transition_count",
                "path_identity_retention", "frame0_up")
    output = []
    for (parameter, cell), rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda row: row["aodv_pdr"])
        lowest, highest = ordered[0], ordered[-1]
        result = {
            "parameter": parameter, "cell": cell, "n_realizations": len(rows),
            "aodv_mean": statistics.mean(row["aodv_pdr"] for row in rows),
            "aodv_median": statistics.median(row["aodv_pdr"] for row in rows),
            "aodv_sample_sd_ddof1": sample_sd([row["aodv_pdr"] for row in rows]),
            "aodv_min": lowest["aodv_pdr"], "aodv_min_graph_id": lowest["graph_id"],
            "aodv_max": highest["aodv_pdr"], "aodv_max_graph_id": highest["graph_id"],
            "aodv_realization_values": ";".join(
                f"{row['graph_id']}:{row['aodv_pdr']:.6f}" for row in ordered
            ),
            "interpretation_warning": "Five-point descriptive spread; extrema do not establish statistical modes.",
        }
        for feature in features:
            result[f"min_{feature}"] = lowest[feature]
            result[f"max_{feature}"] = highest[feature]
        output.append(result)
    return output


def phase6a_deadline_summary():
    source = OUT.parent / "6A" / "corrected_6a_realizations.csv"
    if not source.exists():
        return []
    rows = read_csv(source)
    groups = {}
    for row in rows:
        groups.setdefault(row["condition"], []).append(row)
    summary = []
    for condition, condition_rows in sorted(groups.items()):
        for protocol in PROTOCOLS:
            for deadline, suffix in ((0.5, "0_5s"), (1, "1s"), (2, "2s")):
                metric = f"{protocol}_deadline_pdr_{suffix}"
                values = [float(row[metric]) for row in condition_rows
                          if math.isfinite(float(row[metric]))]
                summary.append({
                    "condition": condition, "protocol": protocol, "deadline_s": deadline,
                    "realizations": len(values),
                    "deadline_pdr_mean": statistics.mean(values) if values else float("nan"),
                    "deadline_pdr_median": statistics.median(values) if values else float("nan"),
                    "deadline_pdr_sample_sd_ddof1": sample_sd(values),
                    "per_realization_values": ";".join(f"{value:.8f}" for value in values),
                    "source": str(source.relative_to(ROOT)),
                })
    return summary


def write_csv(path: Path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_strip_plots(records):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib unavailable; strip plots not produced")
        return
    colors = {"olsr": "#3b82f6", "aodv": "#ef4444", "dsdv": "#9ca3af", "static": "#111827"}
    offsets = {"olsr": -0.24, "aodv": -0.08, "dsdv": 0.08, "static": 0.24}
    for topology in TOPOLOGIES:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
        for axis, parameter in zip(axes, PARAMETERS):
            subset = [row for row in records if row["topology"] == topology and row["parameter"] == parameter]
            values = sorted({row["parameter_value"] for row in subset})
            for protocol in PROTOCOLS:
                for index, value in enumerate(values):
                    ys = [row[f"{protocol}_pdr"] for row in subset if row["parameter_value"] == value]
                    jitter = [((i * 17 + index * 7) % 13 - 6) * 0.006 for i in range(len(ys))]
                    axis.scatter([index + offsets[protocol] + j for j in jitter], ys,
                                 color=colors[protocol], alpha=0.72 if protocol != "dsdv" else 0.38,
                                 s=24, label=protocol if index == 0 else None)
                    if ys:
                        axis.plot([index + offsets[protocol] - 0.035, index + offsets[protocol] + 0.035],
                                  [statistics.mean(ys)] * 2, color=colors[protocol], linewidth=1.6)
            axis.set_xticks(range(len(values)), [f"{value:g}" for value in values])
            axis.set_title(parameter)
            axis.set_xlabel("parameter value")
            axis.grid(axis="y", alpha=0.2)
        axes[0].set_ylabel("PDR (epoch-average per DG realization)")
        fig.suptitle(f"Phase 5 realization-level PDR — {topology}")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False)
        fig.tight_layout(rect=(0, 0.08, 1, 0.93))
        fig.savefig(OUT / f"strip_pdr_{topology}.png", dpi=160)
        plt.close(fig)


def main() -> None:
    records = collect_realizations()
    summaries, paired = cell_statistics(records)
    feature_models, attenuation = measured_feature_models(records)
    write_csv(OUT / "phase5_realization_features_pdr.csv", records)
    write_csv(OUT / "phase5_cell_statistics.csv", summaries)
    write_csv(OUT / "phase5_paired_differences.csv", paired)
    write_csv(OUT / "phase5_feature_regressions.csv", feature_models)
    write_csv(OUT / "phase5_parameter_runlength_adjustment.csv", attenuation)
    write_csv(OUT / "phase6a_deadline_pdr_summary.csv", phase6a_deadline_summary())
    ladder = [row for row in records if row["topology"] == "ladder"]
    write_csv(OUT / "ladder_aodv_modes.csv", [
        {"parameter": row["parameter"], "cell": row["cell"], "graph_id": row["graph_id"],
         "aodv_pdr": row["aodv_pdr"], "static_pdr": row["static_pdr"],
         "usable_traffic_uptime": row["usable_traffic_uptime"], "mean_up_run_s": row["mean_up_run_s"],
         "transition_count": row["transition_count"], "path_identity_retention": row["path_identity_retention"],
         "frame0_up": row["frame0_up"]}
        for row in ladder
    ])
    write_csv(OUT / "ladder_aodv_spread.csv", ladder_aodv_spread(records))
    make_strip_plots(records)
    print(f"records={len(records)} cell summaries={len(summaries)} paired cells={len(paired)}")
    print("Every group averages replay epochs within its DG realization before between-realization statistics.")
    print("Parameter-slope attenuation controlling measured mean up-run:")
    for row in attenuation:
        print(row["topology"], row["swept_parameter"], row["protocol"],
              f"beta={row['unadjusted_parameter_slope']:.5f}",
              f"beta|meanUpRun={row['adjusted_parameter_slope_controlling_mean_up_run']:.5f}",
              f"attenuation={row['signed_slope_attenuation_fraction']:.3f}")
    print("Ladder AODV PDR range by sweep:")
    for parameter in PARAMETERS:
        values = [row["aodv_pdr"] for row in ladder
                  if row["parameter"] == parameter and math.isfinite(row["aodv_pdr"])]
        print(parameter, min(values), max(values))


if __name__ == "__main__":
    main()
