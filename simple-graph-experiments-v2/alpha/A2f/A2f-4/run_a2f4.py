#!/usr/bin/env python3
"""A2f-4 read-only A2d audit and preregistered isolated MPC capacity sweep."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ITEM2 = REPO / "alpha" / "A2" / "A2d" / "item2"
CORRECTION = ITEM2 / "results" / "correction_v1"
ORIGINAL_RUNNER = ITEM2 / "run_mpc_probe.py"
SOURCE = REPO / "alpha" / "A0R2" / "YaDyGaGa"
GRAPH = REPO / "alpha" / "A1" / "results" / "edge_lists" / "er_N92_r1.csv"
PREREG = HERE / "prereg.md"
SWEEP = HERE / "sweep"
FRAMES = 120
SEEDS = (11,  29, 47, 71, 89)
TRIALS_GRID = (3000, 10000, 30000)
P_EDGES = (0.3, 0.5, 0.7)
PAIRS = [(0, 1), (2, 3)]
TIMEOUT = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def state_key(state: tuple[bool, ...] | list[bool]) -> str:
    return "|".join("1" if bool(bit) else "0" for bit in state)


def states(m: int) -> list[str]:
    return [state_key(bits) for bits in itertools.product((False, True), repeat=m)]


def parse_state(value: str) -> tuple[bool, ...]:
    parsed = json.loads(value)
    return tuple(bool(bit) for bit in parsed)


def load_original():
    spec = importlib.util.spec_from_file_location("a2f4_original_runner", ORIGINAL_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen A2d item2 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOURCE = SOURCE
    module.PREREG = PREREG
    module.RESULTS = SWEEP
    return module


def corrected_statistics(_generator, timeline):
    statuses = [tuple(value is not None for value in row) for row in timeline]
    if not statuses:
        return {}
    per_pair = []
    for pair_index in range(len(statuses[0])):
        series = [row[pair_index] for row in statuses]
        per_pair.append({
            "pair_index": pair_index,
            "up_count": sum(series),
            "uptime_ratio": sum(series) / len(series),
            "up_blocks": sum(value and (index == 0 or not series[index - 1]) for index, value in enumerate(series)),
            "changes": sum(series[index] != series[index - 1] for index in range(1, len(series))),
        })
    counts: dict[str, int] = {}
    for status in statuses:
        key = state_key(status)
        counts[key] = counts.get(key, 0) + 1
    return {"frames": len(statuses), "pairs": per_pair, "status_tuples": counts}


def operation(config_path: Path) -> int:
    module = load_original()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    module.FRAMES = int(config["frames"])
    module.TRIALS = int(config["frame_pool_trials"])
    module.LIFE = float(config["path_life"])
    module.STABILITY = float(config["stability"])
    module.PERSISTENCY = float(config["pathPersistency"])
    module.TIMEOUT = int(config["timeout_seconds"])
    sys.path.insert(0, str(SOURCE))
    from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
    MPCTimelineBlockGenerator.computeStatistics = corrected_statistics
    # The frozen runner hard-codes p_edge at its one call site; alter only this
    # isolated imported module's constant-free call by wrapping its generator.
    from yadygaga.frameGenerator import FrameGenerator
    original_generate = FrameGenerator.generateMPCFrames

    def generate_with_registered_parameters(self, graph, pairs, trials=1000, p_edge=0.5, seed=None):
        return original_generate(self, graph, pairs, trials=int(config["frame_pool_trials"]), p_edge=float(config["p_edge"]), seed=seed)

    FrameGenerator.generateMPCFrames = generate_with_registered_parameters
    return module.execute(config_path)


def audit_cell(directory: Path) -> dict[str, Any]:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    operation_status = json.loads((directory / "operation_status.json").read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "label": directory.name,
        "arrangement": config["arrangement"],
        "pair_count": int(config["pair_count"]),
        "seed": int(config["timeline_seed"]),
        "operation_status": operation_status.get("status", "missing"),
        "cause": "no_observed_fidelity_failure",
    }
    if operation_status.get("status") != "success":
        result["cause"] = "timeline_quota_invalid"
        result["error"] = operation_status
        return result

    timeline = json.loads((directory / "timeline.json").read_text(encoding="utf-8"))
    requested = [tuple(value is not None for value in row) for row in timeline["timeline"]]
    m = int(config["pair_count"])
    full_states = states(m)
    demand = {key: 0 for key in full_states}
    for status in requested:
        demand[state_key(status)] += 1
    sparse_pool = json.loads((directory / "pool_status_counts.json").read_text(encoding="utf-8"))
    pool = {key: int(sparse_pool.get(key, 0)) for key in full_states}
    requested_missing = [key for key in full_states if demand[key] and pool[key] == 0]
    under_supply = [key for key in full_states if demand[key] and pool[key] < demand[key]]

    up_counts = [sum(row[pair] for row in requested) for pair in range(m)]
    up_runs = [sum(row[pair] and (i == 0 or not requested[i - 1][pair]) for i, row in enumerate(requested)) for pair in range(m)]
    expected_u = round(int(config["frames"]) * float(config["path_life"]))
    quota_valid = (
        len(requested) == int(config["frames"])
        and all(len(row) == m for row in requested)
        and all(value == expected_u for value in up_counts)
    )

    with (directory / "frame_statuses.csv").open(newline="", encoding="utf-8") as stream:
        frames = list(csv.DictReader(stream))
    pool_mismatch = sum(parse_state(row["selected_pool_status"]) != parse_state(row["requested_status"]) for row in frames)
    realized_mismatch = sum(parse_state(row["realized_status"]) != parse_state(row["requested_status"]) for row in frames)
    pair_rows = []
    with (directory / "pair_fidelity.csv").open(newline="", encoding="utf-8") as stream:
        pair_rows = list(csv.DictReader(stream))
    fidelity_failed = [int(row["pair_index"]) for row in pair_rows if not (float(row["absolute_uptime_error"]) <= 0.05)]

    if not quota_valid:
        cause = "timeline_quota_invalid"
    elif requested_missing:
        cause = "requested_joint_state_absent"
    elif under_supply:
        cause = "requested_pool_supply_below_demand"
    elif pool_mismatch or realized_mismatch:
        cause = "observable_status_fallback_or_assembly_mismatch"
    elif fidelity_failed:
        cause = "pair_metric_mismatch"
    else:
        cause = "no_observed_fidelity_failure"
    result.update({
        "cause": cause,
        "frames": len(requested),
        "expected_up_frames_per_pair": expected_u,
        "requested_up_runs_per_pair_descriptive": json.dumps(up_runs),
        "timeline_quota_valid": quota_valid,
        "per_pair_up_frames": json.dumps(up_counts),
        "per_pair_up_runs": json.dumps(up_runs),
        "full_pool_counts": json.dumps(pool, sort_keys=True),
        "requested_joint_counts": json.dumps(demand, sort_keys=True),
        "requested_states_absent": json.dumps(requested_missing),
        "requested_states_below_demand": json.dumps(under_supply),
        "selected_pool_status_mismatch_frames": pool_mismatch,
        "realized_status_mismatch_frames": realized_mismatch,
        "pair_fidelity_failed_indices": json.dumps(fidelity_failed),
        "pair_fidelity": json.dumps(pair_rows, sort_keys=True),
        "selected_frame_reuse_count": json.loads((directory / "trace_metrics.json").read_text(encoding="utf-8")).get("selected_frame_reuse_count"),
        "same_status_pid_relaxation_observable": False,
        "fallback_flags": "selected_pool_status mismatch only; internal same-status PID relaxation not recorded",
    })
    return result


def audit() -> None:
    rows = [audit_cell(CORRECTION / f"{arrangement}_m{m}_seed{seed}")
            for arrangement in ("disjoint", "shared_source")
            for m in (2, 4, 8) for seed in (11, 29, 47)]
    write_csv(HERE / "audit_18_cells_v2.csv", rows, list(dict.fromkeys(key for row in rows for key in row)))
    write_json(HERE / "audit_18_cells_v2.json", rows)


def config_for(trials: int, p_edge: float, seed: int) -> dict[str, Any]:
    module = load_original()
    source_files = {
        "timelineBlockGenerator.py": SOURCE / "yadygaga" / "timelineBlockGenerator.py",
        "frameGenerator.py": SOURCE / "yadygaga" / "frameGenerator.py",
        "dynaGraph.py": SOURCE / "yadygaga" / "dynaGraph.py",
        "run_mpc_probe.py": ORIGINAL_RUNNER,
        "run_a2f4.py": Path(__file__).resolve(),
    }
    return {
        "stage": "A2f-4-sweep", "generator": "yadygaga_mpc_legacy", "behavior": "legacy",
        "graph_id": "er_N92_r1", "graph_edge_sha256": sha256(GRAPH),
        "pairs": [list(pair) for pair in PAIRS], "arrangement": "disjoint", "pair_count": 2,
        "frames": FRAMES, "path_life": 0.5, "stability": 0.5, "mode": "sync",
        "pathPersistency": 0.75, "timeline_seed": seed, "frame_pool_seed": seed + 10000,
        "assembly_seed": seed + 20000, "frame_pool_trials": trials, "p_edge": p_edge,
        "no_double": True, "allow_hamming_fallback": True, "force": True,
        "timeout_seconds": TIMEOUT, "preregistration_sha256": sha256(PREREG),
        "source_sha256": {name: sha256(path) for name, path in source_files.items()},
        "python": sys.version, "networkx": module.nx.__version__,
    }


def parse_count_map(path: Path) -> dict[str, int]:
    sparse = json.loads(path.read_text(encoding="utf-8"))
    return {key: int(value) for key, value in sparse.items()}


def run_sweep() -> None:
    SWEEP.mkdir(parents=True, exist_ok=True)
    operation_rows: list[dict[str, Any]] = []
    pair_rows_all: list[dict[str, Any]] = []
    pool_rows: list[dict[str, Any]] = []
    for trials in TRIALS_GRID:
        for p_edge in P_EDGES:
            for seed in SEEDS:
                label = f"disjoint_m2_trials{trials}_p{p_edge:.1f}_seed{seed}"
                out = SWEEP / label
                out.mkdir(parents=True, exist_ok=True)
                config = config_for(trials, p_edge, seed)
                config_path = out / "config.json"
                write_json(config_path, config)
                command = [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)]
                started = time.perf_counter()
                proc = None
                try:
                    proc = subprocess.run(command, cwd=HERE, timeout=TIMEOUT, check=False, capture_output=True, text=True)
                    elapsed = time.perf_counter() - started
                    status_path = out / "operation_status.json"
                    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"status": "failed_missing_status"}
                    if proc.returncode and status.get("status") == "success":
                        status = {"status": "failed_returncode", "returncode": proc.returncode}
                        write_json(status_path, status)
                except subprocess.TimeoutExpired as error:
                    elapsed = time.perf_counter() - started
                    status = {"status": "failed_timeout", "timeout_seconds": TIMEOUT, "stdout_tail": str(error.stdout)[-1000:], "stderr_tail": str(error.stderr)[-1000:]}
                    write_json(out / "operation_status.json", status)
                record: dict[str, Any] = {"label": label, "trials": trials, "p_edge": p_edge, "seed": seed,
                                          "wall_seconds": elapsed, "status": status.get("status"),
                                          "returncode": proc.returncode if proc is not None else ("TIMEOUT" if status.get("status") == "failed_timeout" else "")}
                if status.get("status") == "success":
                    metrics = json.loads((out / "trace_metrics.json").read_text(encoding="utf-8"))
                    timeline = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
                    full = {key: 0 for key in states(2)}
                    full.update(parse_count_map(out / "pool_status_counts.json"))
                    demand: dict[str, int] = {key: 0 for key in states(2)}
                    for row in timeline["requested_statuses"]:
                        demand[state_key(row)] += 1
                    supply_ready = all(full[key] >= demand[key] for key in states(2) if demand[key])
                    with (out / "frame_statuses.csv").open(newline="", encoding="utf-8") as stream:
                        frame_statuses = list(csv.DictReader(stream))
                    status_mismatch = sum(parse_state(row["selected_pool_status"]) != parse_state(row["requested_status"]) for row in frame_statuses)
                    with (out / "pair_fidelity.csv").open(newline="", encoding="utf-8") as stream:
                        pair_results = list(csv.DictReader(stream))
                    for pair_result in pair_results:
                        pair_rows_all.append({"label": label, "trials": trials, "p_edge": p_edge, "seed": seed, **pair_result})
                    record.update({
                        "supply_ready": supply_ready,
                        "minimum_requested_state_count": min((full[key] for key in states(2) if demand[key]), default=0),
                        "minimum_requested_state_demand": min((demand[key] for key in states(2) if demand[key]), default=0),
                        "requested_state_counts": json.dumps({key: full[key] for key in states(2) if demand[key]}, sort_keys=True),
                        "requested_state_demands": json.dumps({key: demand[key] for key in states(2) if demand[key]}, sort_keys=True),
                        "selected_pool_status_mismatch_frames": status_mismatch,
                        "realized_status_mismatch_frames": sum(not json.loads(row["joint_status_exact"].lower()) for row in frame_statuses),
                        "fidelity_pass_count": sum(str(row["fidelity_pass"]).lower() == "true" for row in pair_results),
                        "pair_count": len(pair_results),
                        "assembly_seconds": metrics.get("assembly_seconds"),
                        "pool_generation_seconds": metrics.get("pool_generation_seconds"),
                        "total_operation_seconds": metrics.get("total_operation_seconds"),
                        "selected_frame_reuse_count": metrics.get("selected_frame_reuse_count"),
                    })
                    for key in states(2):
                        pool_rows.append({"label": label, "trials": trials, "p_edge": p_edge, "seed": seed,
                                          "state": key, "pool_count": full[key], "requested_demand": demand[key],
                                          "supply_ready_for_state": full[key] >= demand[key] if demand[key] else "not_requested"})
                    # Add measured internal timings to the operation record.
                    record["status_counts_full"] = json.dumps(full, sort_keys=True)
                    record["timeline_quota_valid"] = (
                        len(timeline["timeline"]) == FRAMES
                        and all(len(frame) == len(PAIRS) for frame in timeline["timeline"])
                        and all(int(pair["up_count"]) == 60 for pair in timeline["statistics"]["pairs"])
                    )
                else:
                    record["error"] = json.dumps(status, sort_keys=True)
                operation_rows.append(record)
                write_csv(SWEEP / "operation_log.csv", operation_rows, list(dict.fromkeys(k for row in operation_rows for k in row)))
                write_csv(SWEEP / "per_operation.csv", operation_rows, list(dict.fromkeys(k for row in operation_rows for k in row)))
                write_csv(SWEEP / "per_pair.csv", pair_rows_all, ["label", "trials", "p_edge", "seed", "pair_index", "source", "destination", "requested_up_frames", "requested_uptime", "measured_up_frames", "measured_uptime", "absolute_uptime_error", "requested_up_runs", "measured_up_runs", "fidelity_pass"])
                write_csv(SWEEP / "pool_counts_full.csv", pool_rows, ["label", "trials", "p_edge", "seed", "state", "pool_count", "requested_demand", "supply_ready_for_state"])
    classify_sweep(operation_rows)


def classify_stratum(rows: list[dict[str, Any]]) -> dict[str, Any]:
    levels: dict[int, dict[str, Any]] = {}
    for trials in TRIALS_GRID:
        selected = [row for row in rows if row["trials"] == trials]
        completed = [row for row in selected if row.get("status") == "success"]
        supply_ready_count = sum(bool(row.get("supply_ready")) for row in completed)
        pair_passes = sum(int(row.get("fidelity_pass_count", 0)) for row in completed)
        mismatch_total = sum(int(row.get("selected_pool_status_mismatch_frames", 0)) for row in completed)
        minima = [int(row["minimum_requested_state_count"]) for row in completed]
        levels[trials] = {
            "attempted": len(selected), "completed": len(completed),
            "supply_ready_operations": supply_ready_count,
            "pair_fidelity_passes": pair_passes, "pair_fidelity_total": 2 * len(completed),
            "selected_status_mismatch_frames": mismatch_total,
            "minimum_requested_state_counts": minima,
            "median_minimum_requested_state_count": statistics.median(minima) if minima else None,
            "mean_runtime_seconds": statistics.mean(float(row["wall_seconds"]) for row in completed) if completed else None,
            "max_runtime_seconds": max((float(row["wall_seconds"]) for row in completed), default=None),
            "resolved": len(completed) == 5 and supply_ready_count >= 4 and pair_passes >= 9 and mismatch_total <= 30,
        }
    label = "inconclusive_or_mixed"
    low, mid, high = (levels[t] for t in TRIALS_GRID)
    if (not low["resolved"] or not mid["resolved"]) and high["resolved"]:
        label = "capacity_resolved"
    else:
        med_low = low["median_minimum_requested_state_count"]
        med_high = high["median_minimum_requested_state_count"]
        ratio = (med_high / max(med_low, 1)) if med_high is not None and med_low is not None else None
        improvement = high["supply_ready_operations"] - low["supply_ready_operations"]
        if ratio is not None and ratio >= 2 and improvement >= 2:
            label = "capacity_sensitive_unresolved"
        else:
            absent_persistently = False
            for state in states(2):
                absent_at_both = True
                for trials in (10000, 30000):
                    seed_rows = [r for r in rows if r["trials"] == trials]
                    requested_any = any(int(json.loads(r["requested_state_demands"]).get(state, 0)) > 0 for r in seed_rows if r.get("status") == "success")
                    zero_count = sum(int(json.loads(r["status_counts_full"]).get(state, 0)) == 0 for r in seed_rows if r.get("status") == "success")
                    absent_at_both &= requested_any and zero_count >= 4
                absent_persistently |= absent_at_both
            if absent_persistently:
                label = "persistent_absence_evidence"
            elif high["completed"] == 5 and high["supply_ready_operations"] == 5 and (high["pair_fidelity_passes"] < 9 or high["selected_status_mismatch_frames"] > 30):
                label = "persistent_assembly_mismatch"
    return {"p_edge": rows[0]["p_edge"], "classification": label, "levels": levels}


def classify_sweep(rows: list[dict[str, Any]]) -> None:
    strata = [classify_stratum([r for r in rows if r["p_edge"] == p]) for p in P_EDGES]
    counts: dict[str, int] = {}
    for item in strata:
        counts[item["classification"]] = counts.get(item["classification"], 0) + 1
    overall = "mixed/inconclusive"
    for label in ("capacity_resolved", "capacity_sensitive_unresolved", "persistent_absence_evidence"):
        if counts.get(label, 0) >= 2:
            overall = label
            break
    write_json(SWEEP / "classification.json", {"overall": overall, "strata": strata, "class_counts": counts})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--operation", type=Path)
    args = parser.parse_args()
    if args.operation:
        raise SystemExit(operation(args.operation))
    if args.audit:
        audit()
    if args.sweep:
        run_sweep()
    if not (args.audit or args.sweep):
        parser.error("choose --audit and/or --sweep, or provide --operation")


if __name__ == "__main__":
    main()
