#!/usr/bin/env python3
"""Build preregistered per-stratum summaries and a hash manifest for A2f-4."""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SWEEP = HERE / "sweep"
STATES = ("0|0", "0|1", "1|0", "1|1")
STRATA = (0.3, 0.5, 0.7)
TRIALS = (3000, 10000, 30000)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize() -> None:
    ops = read_csv(SWEEP / "per_operation.csv")
    strata: list[dict[str, Any]] = []
    for p_edge in STRATA:
        levels = []
        for trials in TRIALS:
            selected = [row for row in ops if float(row["p_edge"]) == p_edge and int(row["trials"]) == trials]
            completed = [row for row in selected if row["status"] == "success"]
            full_counts = {state: 0 for state in STATES}
            requested_demand = {state: 0 for state in STATES}
            per_seed = []
            joint_exact_frames = 0
            for row in completed:
                label = row["label"]
                counts = json.loads(row["status_counts_full"])
                demand = json.loads(row["requested_state_demands"])
                for state in STATES:
                    full_counts[state] += int(counts.get(state, 0))
                    requested_demand[state] += int(demand.get(state, 0))
                ratios = [int(counts[state]) / int(demand[state]) for state in STATES if int(demand.get(state, 0)) > 0]
                with (SWEEP / label / "frame_statuses.csv").open(newline="", encoding="utf-8") as stream:
                    joint_exact_frames += sum(str(frame["joint_status_exact"]).lower() == "true" for frame in csv.DictReader(stream))
                per_seed.append({
                    "seed": int(row["seed"]),
                    "status": row["status"],
                    "pool_status_counts_full": counts,
                    "requested_state_demands": demand,
                    "supply_ready": row["supply_ready"] == "True",
                    "minimum_requested_state_pool_count": int(row["minimum_requested_state_count"]),
                    "minimum_requested_state_count_demand_ratio": min(ratios, default=None),
                    "selected_pool_status_mismatch_frames": int(row["selected_pool_status_mismatch_frames"]),
                    "realized_status_mismatch_frames": int(row["realized_status_mismatch_frames"]),
                    "pair_fidelity_passes": int(row["fidelity_pass_count"]),
                    "pair_fidelity_total": int(row["pair_count"]),
                    "wall_seconds": float(row["wall_seconds"]),
                    "pool_generation_seconds": float(row["pool_generation_seconds"]),
                    "assembly_seconds": float(row["assembly_seconds"]),
                    "timeline_quota_valid": row["timeline_quota_valid"] == "True",
                })
            ratios_per_seed = [record["minimum_requested_state_count_demand_ratio"] for record in per_seed if record["minimum_requested_state_count_demand_ratio"] is not None]
            minima = [record["minimum_requested_state_pool_count"] for record in per_seed]
            mismatch = sum(record["selected_pool_status_mismatch_frames"] for record in per_seed)
            passes = sum(record["pair_fidelity_passes"] for record in per_seed)
            runtimes = [record["wall_seconds"] for record in per_seed]
            levels.append({
                "frame_pool_trials": trials,
                "attempted": len(selected),
                "completed": len(completed),
                "failed_labels": [row["label"] for row in selected if row["status"] != "success"],
                "aggregate_pool_status_counts_all_states": full_counts,
                "aggregate_requested_state_demands_all_states": requested_demand,
                "supply_ready_operations": sum(record["supply_ready"] for record in per_seed),
                "minimum_requested_state_count_per_seed": minima,
                "median_minimum_requested_state_count": statistics.median(minima) if minima else None,
                "minimum_requested_state_count_demand_ratio_per_seed": ratios_per_seed,
                "median_minimum_requested_state_count_demand_ratio": statistics.median(ratios_per_seed) if ratios_per_seed else None,
                "pair_fidelity_passes": passes,
                "pair_fidelity_total": sum(record["pair_fidelity_total"] for record in per_seed),
                "selected_pool_status_mismatch_frames": mismatch,
                "selected_pool_status_mismatch_fraction_of_600": mismatch / 600,
                "realized_status_mismatch_frames": sum(record["realized_status_mismatch_frames"] for record in per_seed),
                "exact_joint_status_frames_of_600": joint_exact_frames,
                "mean_wall_seconds": statistics.mean(runtimes) if runtimes else None,
                "max_wall_seconds": max(runtimes, default=None),
                "per_seed": per_seed,
            })
        strata.append({"p_edge": p_edge, "levels": levels})
    classification = json.loads((SWEEP / "classification.json").read_text(encoding="utf-8"))
    summary = {
        "design": {"operations_expected": 45, "operations_recorded": len(ops), "seeds": [11, 29, 47, 71, 89], "trials": list(TRIALS), "p_edge": list(STRATA)},
        "overall_frozen_classification": classification["overall"],
        "frozen_classification_detail": classification,
        "strata": strata,
        "limitations": [
            "life and mean up-run remain confounded under the A2a stability rule",
            "timeline diversity is family-independent by construction",
            "the generator is patched and non-upstream",
            "the A2b gate is non-binding by greedy max-min construction",
            "Level 2 route diversity is tie-break-sensitive",
            "time-respecting reachability permits waiting and is not an OLSR/AODV/DSDV oracle",
        ],
    }
    (SWEEP / "stratum_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_rows = []
    for stratum in strata:
        for level in stratum["levels"]:
            summary_rows.append({key: value for key, value in level.items() if key != "per_seed"} | {"p_edge": stratum["p_edge"]})
    fields = list(dict.fromkeys(key for row in summary_rows for key in row))
    with (SWEEP / "stratum_summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()} for row in summary_rows)


def manifest() -> None:
    target = HERE / "artifact_manifest.csv"
    excluded = {target.resolve(), (HERE / "result.md").resolve()}
    rows = []
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.resolve() in excluded:
            continue
        rows.append({"path": path.relative_to(HERE).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
    with target.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"entries": len(rows), "manifest_sha256": digest(target)}, sort_keys=True))


if __name__ == "__main__":
    summarize()
    manifest()
