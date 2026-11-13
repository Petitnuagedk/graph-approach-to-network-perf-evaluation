#!/usr/bin/env python3
"""Run registered A2d item 2 MPC generation/fidelity probes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
A1 = ROOT / "simple-graph-experiments-v2" / "alpha" / "A1"
A0R2 = ROOT / "simple-graph-experiments-v2" / "alpha" / "A0R2"
SOURCE = A0R2 / "YaDyGaGa"
RESULTS = HERE / "results"
PREREG = HERE / "prereg.md"
GRAPH_ID = "er_N92_r1"
PAIRS = {
    "disjoint": [(2 * j, 2 * j + 1) for j in range(8)],
    "shared_source": [(5, 6 + j) for j in range(8)],
}
PAIR_COUNTS = (2, 4, 8)
SEEDS = (11, 29, 47)
FRAMES = 120
TRIALS = 3000
LIFE = 0.5
STABILITY = 0.5
PERSISTENCY = 0.75
TIMEOUT = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def graph_path() -> Path:
    return A1 / "results" / "edge_lists" / f"{GRAPH_ID}.csv"


def read_graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    with graph_path().open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def config_for(arrangement: str, pair_count: int, seed: int) -> dict:
    selected_pairs = PAIRS[arrangement][:pair_count]
    return {
        "stage": "A2d-item2",
        "generator": "yadygaga_mpc_legacy",
        "behavior": "legacy",
        "graph_id": GRAPH_ID,
        "graph_edge_sha256": sha256(graph_path()),
        "pairs": [list(pair) for pair in selected_pairs],
        "arrangement": arrangement,
        "pair_count": pair_count,
        "frames": FRAMES,
        "path_life": LIFE,
        "stability": STABILITY,
        "mode": "sync",
        "pathPersistency": PERSISTENCY,
        "timeline_seed": seed,
        "frame_pool_seed": seed + 10000,
        "assembly_seed": seed + 20000,
        "frame_pool_trials": TRIALS,
        "p_edge": 0.5,
        "no_double": True,
        "allow_hamming_fallback": True,
        "force": True,
        "timeout_seconds": TIMEOUT,
        "source_tree": "32b243bc84b587f1782ead0d0ac56382a57425e5",
        "source_sha256": {
            "timelineBlockGenerator.py": sha256(SOURCE / "yadygaga" / "timelineBlockGenerator.py"),
            "frameGenerator.py": sha256(SOURCE / "yadygaga" / "frameGenerator.py"),
            "dynaGraph.py": sha256(SOURCE / "yadygaga" / "dynaGraph.py"),
            "run_mpc_probe.py": sha256(Path(__file__).resolve()),
        },
        "preregistration_sha256": sha256(PREREG),
        "python": sys.version,
        "networkx": nx.__version__,
    }


def execute(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out = config_path.parent
    try:
        sys.path.insert(0, str(SOURCE))
        from yadygaga.frameGenerator import FrameGenerator
        from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
        from yadygaga.dynaGraph import MPCDynamicGraph

        graph = read_graph()
        pairs = [tuple(pair) for pair in config["pairs"]]
        start = time.perf_counter()
        frame_generator = FrameGenerator()
        frame_pool = frame_generator.generateMPCFrames(
            graph, pairs, trials=TRIALS, p_edge=0.5, seed=config["frame_pool_seed"]
        )
        pool_seconds = time.perf_counter() - start
        timeline_start = time.perf_counter()
        timeline_generator = MPCTimelineBlockGenerator(
            FRAMES, len(pairs), LIFE, STABILITY,
            mode="sync", seed=config["timeline_seed"], pathPersistency=PERSISTENCY,
        )
        timeline = timeline_generator.generate()
        timeline_stats = timeline_generator.computeStatistics(timeline)
        timeline_seconds = time.perf_counter() - timeline_start
        assembly_start = time.perf_counter()
        dynamic = MPCDynamicGraph()
        assembled = dynamic.buildDynaGraph(
            timeline,
            frame_pool,
            seed=config["assembly_seed"],
            no_double=True,
            allow_hamming_fallback=True,
            force=True,
        )
        assembly_seconds = time.perf_counter() - assembly_start
        serialization_start = time.perf_counter()

        requested_statuses = [tuple(value is not None for value in row) for row in timeline]
        requested_counts = {status: requested_statuses.count(status) for status in set(requested_statuses)}
        pool_counts = {status: len(indices) for status, indices in frame_pool["cases"].items()}
        realized_statuses = []
        per_pair_counts = [0] * len(pairs)
        per_pair_runs = [0] * len(pairs)
        previous = [False] * len(pairs)
        frame_rows = []
        edge_rows = []
        route_rows = []
        skeleton_edges = {frozenset(edge) for edge in graph.edges()}
        all_edges_subset = True
        for frame_index, frame in enumerate(assembled):
            status = []
            for pair_index, (source, destination) in enumerate(pairs):
                try:
                    route = nx.shortest_path(frame, source, destination)
                    is_up = True
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    route = None
                    is_up = False
                status.append(is_up)
                per_pair_counts[pair_index] += int(is_up)
                per_pair_runs[pair_index] += int(is_up and not previous[pair_index])
                previous[pair_index] = is_up
                route_rows.append({"frame": frame_index, "pair_index": pair_index, "source": source, "destination": destination, "route": json.dumps(route, separators=(",", ":")), "is_up": is_up})
            status_tuple = tuple(status)
            realized_statuses.append(status_tuple)
            frame_rows.append({
                "frame": frame_index,
                "requested_labeled_state": json.dumps(timeline[frame_index]),
                "requested_status": json.dumps(requested_statuses[frame_index]),
                "realized_status": json.dumps(status_tuple),
                "selected_frame_index": dynamic.selected_frame_indices[frame_index],
                "selected_pool_status": json.dumps(dynamic.selected_statuses[frame_index]),
                "joint_status_exact": status_tuple == requested_statuses[frame_index],
            })
            for u, v in sorted((min(edge), max(edge)) for edge in frame.edges()):
                edge_rows.append({"frame": frame_index, "u": u, "v": v})
            all_edges_subset &= all(frozenset(edge) in skeleton_edges for edge in frame.edges())

        realized_counts = {status: realized_statuses.count(status) for status in set(realized_statuses)}
        all_indices = dynamic.selected_frame_indices
        pair_rows = []
        for i, pair in enumerate(pairs):
            requested_up = sum(status[i] for status in requested_statuses)
            measured_up = per_pair_counts[i]
            pair_rows.append({
                "pair_index": i,
                "source": pair[0],
                "destination": pair[1],
                "requested_up_frames": requested_up,
                "requested_uptime": requested_up / FRAMES,
                "measured_up_frames": measured_up,
                "measured_uptime": measured_up / FRAMES,
                "absolute_uptime_error": abs(measured_up - requested_up) / FRAMES,
                "requested_up_runs": sum(requested_statuses[t][i] and (t == 0 or not requested_statuses[t - 1][i]) for t in range(FRAMES)),
                "measured_up_runs": per_pair_runs[i],
                "fidelity_pass": abs(measured_up - requested_up) / FRAMES <= 0.05,
            })

        missing_statuses = {status: count for status, count in requested_counts.items() if pool_counts.get(status, 0) == 0}
        changed_id_frames = sum(
            any((timeline[i][p] is not None) and not realized_statuses[i][p] for p in range(len(pairs)))
            for i in range(FRAMES)
        )
        unique_indices = len(set(all_indices))
        metrics = {
            "status": "success",
            "arrangement": config["arrangement"],
            "pair_count": len(pairs),
            "seed": config["timeline_seed"],
            "pool_generation_seconds": pool_seconds,
            "timeline_generation_seconds": timeline_seconds,
            "assembly_seconds": assembly_seconds,
            "serialization_seconds": time.perf_counter() - serialization_start,
            "total_operation_seconds": pool_seconds + timeline_seconds + assembly_seconds,
            "pool_status_counts": {"|".join("1" if value else "0" for value in key): value for key, value in pool_counts.items()},
            "requested_joint_status_counts": {"|".join("1" if value else "0" for value in key): value for key, value in requested_counts.items()},
            "realized_joint_status_counts": {"|".join("1" if value else "0" for value in key): value for key, value in realized_counts.items()},
            "missing_requested_statuses": {"|".join("1" if value else "0" for value in key): value for key, value in missing_statuses.items()},
            "selected_frame_reuse_count": FRAMES - unique_indices,
            "requested_up_id_states_realized_down": changed_id_frames,
            "all_edges_in_skeleton": all_edges_subset,
            "all_pair_fidelity_pass": all(row["fidelity_pass"] for row in pair_rows),
            "per_pair": pair_rows,
        }
        write_json(out / "timeline.json", {"timeline": timeline, "requested_statuses": requested_statuses, "statistics": timeline_stats})
        write_json(out / "pool_status_counts.json", metrics["pool_status_counts"])
        write_json(out / "trace_metrics.json", metrics)
        write_csv(out / "pair_fidelity.csv", pair_rows, ["pair_index", "source", "destination", "requested_up_frames", "requested_uptime", "measured_up_frames", "measured_uptime", "absolute_uptime_error", "requested_up_runs", "measured_up_runs", "fidelity_pass"])
        write_csv(out / "frame_statuses.csv", frame_rows, ["frame", "requested_labeled_state", "requested_status", "realized_status", "selected_frame_index", "selected_pool_status", "joint_status_exact"])
        write_csv(out / "routes.csv", route_rows, ["frame", "pair_index", "source", "destination", "route", "is_up"])
        write_csv(out / "assembled_edges.csv", edge_rows, ["frame", "u", "v"])
        write_json(out / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(out / "operation_status.json", {"status": "failed_exception", "exception": repr(error), "traceback": traceback.format_exc()})
        return 1


def parent() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    operation_log = []
    for arrangement in ("disjoint", "shared_source"):
        for pair_count in PAIR_COUNTS:
            for seed in SEEDS:
                label = f"{arrangement}_m{pair_count}_seed{seed}"
                output = RESULTS / label
                output.mkdir(parents=True, exist_ok=True)
                config_path = output / "config.json"
                config_path.write_text(json.dumps(config_for(arrangement, pair_count, seed), indent=2, sort_keys=True) + "\n", encoding="utf-8")
                command = [sys.executable, str(Path(__file__).resolve(),), "--operation", str(config_path)]
                try:
                    result = subprocess.run(command, timeout=TIMEOUT, check=False, cwd=HERE, env=os.environ.copy())
                    status = json.loads((output / "operation_status.json").read_text(encoding="utf-8")) if (output / "operation_status.json").exists() else {"status": "failed_missing_status"}
                    operation_log.append({"label": label, "arrangement": arrangement, "pair_count": pair_count, "seed": seed, "returncode": result.returncode, "status": status.get("status")})
                except subprocess.TimeoutExpired:
                    write_json(output / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": TIMEOUT})
                    operation_log.append({"label": label, "arrangement": arrangement, "pair_count": pair_count, "seed": seed, "returncode": "TIMEOUT", "status": "failed_timeout"})
    write_csv(RESULTS / "operation_log.csv", operation_log, ["label", "arrangement", "pair_count", "seed", "returncode", "status"])
    summarize()


def summarize() -> None:
    operations = []
    pair_rows = []
    for output in sorted(path for path in RESULTS.iterdir() if path.is_dir()):
        metric_path = output / "trace_metrics.json"
        status_path = output / "operation_status.json"
        if not status_path.exists():
            continue
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if metric_path.exists():
            metrics = json.loads(metric_path.read_text(encoding="utf-8"))
            operations.append({**metrics, "label": output.name})
            pair_rows.extend({"label": output.name, **row} for row in metrics["per_pair"])
        else:
            operations.append({"label": output.name, "status": status.get("status")})
    write_csv(RESULTS / "per_operation_summary.csv", operations, ["label", "status", "arrangement", "pair_count", "seed", "pool_generation_seconds", "timeline_generation_seconds", "assembly_seconds", "serialization_seconds", "total_operation_seconds", "selected_frame_reuse_count", "requested_up_id_states_realized_down", "all_edges_in_skeleton", "all_pair_fidelity_pass", "pool_status_counts", "requested_joint_status_counts", "realized_joint_status_counts", "missing_requested_statuses"])
    write_csv(RESULTS / "per_pair_fidelity.csv", pair_rows, ["label", "pair_index", "source", "destination", "requested_up_frames", "requested_uptime", "measured_up_frames", "measured_uptime", "absolute_uptime_error", "requested_up_runs", "measured_up_runs", "fidelity_pass"])
    cells = []
    for arrangement in ("disjoint", "shared_source"):
        for pair_count in PAIR_COUNTS:
            cell = [row for row in operations if row.get("arrangement") == arrangement and row.get("pair_count") == pair_count]
            runtimes = [float(row["total_operation_seconds"]) for row in cell if "total_operation_seconds" in row]
            cell_pairs = [row for row in pair_rows if row["label"].startswith(f"{arrangement}_m{pair_count}_")]
            cells.append({
                "arrangement": arrangement,
                "pair_count": pair_count,
                "n_operations": len(cell),
                "n_completed": sum(row.get("status") == "success" for row in cell),
                "max_total_operation_seconds": max(runtimes) if runtimes else "NA",
                "mean_total_operation_seconds": statistics.mean(runtimes) if runtimes else "NA",
                "sd_total_operation_seconds_ddof1": statistics.stdev(runtimes) if len(runtimes) > 1 else "NA",
                "pair_fidelity_pass_count": sum(row["fidelity_pass"] is True for row in cell_pairs),
                "pair_fidelity_total": len(cell_pairs),
                "all_pair_fidelity_pass": len(cell_pairs) == pair_count * 3 and all(row["fidelity_pass"] is True for row in cell_pairs),
                "all_edge_subsets_pass": len(cell) == 3 and all(row.get("all_edges_in_skeleton") is True for row in cell),
                "tested_m_limit_pass": len(cell) == 3 and all(row.get("status") == "success" and row.get("all_pair_fidelity_pass") is True and row.get("total_operation_seconds", TIMEOUT + 1) < TIMEOUT for row in cell),
            })
    write_csv(RESULTS / "cell_summary.csv", cells, list(cells[0]))
    print(json.dumps({"operations": len(operations), "completed": sum(row.get("status") == "success" for row in operations), "cells": cells}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.operation:
        raise SystemExit(execute(args.operation))
    if args.summarize:
        summarize()
    else:
        parent()


if __name__ == "__main__":
    main()
