#!/usr/bin/env python3
"""Run isolated, preregistered edge-Markovian generator validation only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
A1 = ROOT / "simple-graph-experiments-v2" / "alpha" / "A1"
GRAPH_PATH = A1 / "results" / "edge_lists" / "er_N92_r1.csv"
PREREG_PATH = HERE / "prereg.md"
RESULTS = HERE / "results"
GRAPH_SHA256 = "443ea3ecb243798fb3a6fb97f71a83fc93b8606638d17e7882cd827fafb5ce2b"
N = 92
SOURCE = 5
DESTINATION = 82
FRAMES = 120
PIS = (0.5, 0.8)
DURATIONS = (2.0, 8.0)
SEEDS = (11, 29, 47, 71, 97)
TIMEOUT_SECONDS = 60
GENERATOR = "edge_markovian"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_skeleton() -> tuple[nx.Graph, list[tuple[int, int]]]:
    if sha256_file(GRAPH_PATH) != GRAPH_SHA256:
        raise RuntimeError("registered ER N=92 realization-1 edge-list hash mismatch")
    graph = nx.Graph()
    graph.add_nodes_from(range(N))
    with GRAPH_PATH.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    edges = sorted((min(u, v), max(u, v)) for u, v in graph.edges())
    if graph.number_of_nodes() != N or SOURCE not in graph or DESTINATION not in graph:
        raise RuntimeError("registered graph or probe pair is invalid")
    if not nx.is_connected(graph):
        raise RuntimeError("registered ER skeleton must be connected")
    return graph, edges


def run_lengths(bits: list[bool]) -> list[tuple[int, int, int, bool]]:
    """Return (start, stop-exclusive, length, fully-bounded) up runs."""
    result: list[tuple[int, int, int, bool]] = []
    start: int | None = None
    for index, bit in enumerate(bits):
        if bit and start is None:
            start = index
        elif not bit and start is not None:
            result.append((start, index, index - start, start > 0 and index < len(bits)))
            start = None
    if start is not None:
        result.append((start, len(bits), len(bits) - start, False))
    return result


def sample_chain(frames: int, pi: float, mean_up_duration: float, seed: int) -> list[bool]:
    p10 = 1.0 / mean_up_duration
    p01 = pi / ((1.0 - pi) * mean_up_duration)
    if frames <= 0 or not 0.0 < pi < 1.0 or p10 > 1.0 or p01 > 1.0:
        raise ValueError("infeasible or invalid edge-Markovian parameters")
    rng = random.Random(seed)
    state = rng.random() < pi
    values: list[bool] = []
    for _ in range(frames):
        values.append(state)
        state = (rng.random() >= p10) if state else (rng.random() < p01)
    return values


def canonical_route(graph: nx.Graph, source: int, destination: int) -> list[int] | None:
    if not nx.has_path(graph, source, destination):
        return None
    from_source = nx.single_source_shortest_path_length(graph, source)
    to_destination = nx.single_source_shortest_path_length(graph, destination)
    distance = from_source[destination]
    route = [source]
    current = source
    while current != destination:
        choices = [
            node for node in graph.neighbors(current)
            if from_source.get(node) == from_source[current] + 1
            and from_source[node] + to_destination.get(node, math.inf) == distance
        ]
        if not choices:
            raise RuntimeError("canonical shortest-path reconstruction failed")
        current = min(choices)
        route.append(current)
    return route


def child(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out = config_path.parent
    graph, edges = load_skeleton()
    pi = float(config["pi"])
    duration = float(config["mean_up_duration"])
    base_seed = int(config["base_seed"])
    p10 = 1.0 / duration
    p01 = pi / ((1.0 - pi) * duration)
    edge_bits = [sample_chain(FRAMES, pi, duration, base_seed + 104729 * i) for i in range(len(edges))]
    frames: list[nx.Graph] = []
    for _ in range(FRAMES):
        frame = nx.Graph()
        frame.add_nodes_from(range(N))
        frames.append(frame)
    edge_rows: list[dict] = []
    edge_completed_runs: list[int] = []
    total_edge_ups = 0
    total_edge_transitions = 0
    for (u, v), bits in zip(edges, edge_bits):
        completed = [length for _, _, length, is_complete in run_lengths(bits) if is_complete]
        transitions = sum(left != right for left, right in zip(bits, bits[1:]))
        total_edge_ups += sum(bits)
        total_edge_transitions += transitions
        edge_completed_runs.extend(completed)
        edge_rows.append({
            "generator": GENERATOR,
            "u": u,
            "v": v,
            "edge_seed": base_seed + 104729 * len(edge_rows),
            "states": "".join("1" if value else "0" for value in bits),
            "transitions": transitions,
            "completed_up_run_lengths": ";".join(map(str, completed)),
            "completed_up_run_count": len(completed),
            "censored_up_run_lengths": ";".join(str(length) for _, _, length, complete in run_lengths(bits) if not complete),
        })
        for frame_index, is_up in enumerate(bits):
            if is_up:
                frames[frame_index].add_edge(u, v)
    if len(frames) != FRAMES:
        raise RuntimeError("wrong number of assembled frames")

    frame_rows: list[dict] = []
    sr_mask: list[bool] = []
    sr_routes: list[list[int] | None] = []
    sr_hops: list[int | None] = []
    for index, frame in enumerate(frames):
        route = canonical_route(frame, SOURCE, DESTINATION)
        up = route is not None
        sr_mask.append(up)
        sr_routes.append(route)
        sr_hops.append(len(route) - 1 if route else None)
        frame_edges = sorted((min(u, v), max(u, v)) for u, v in frame.edges())
        payload = json.dumps({"nodes": list(range(N)), "edges": frame_edges}, separators=(",", ":")).encode()
        frame_rows.append({
            "generator": GENERATOR,
            "frame": index,
            "edge_count": len(frame_edges),
            "edge_fingerprint_sha256": sha256_bytes(payload),
            "edges": frame_edges,
            "sr_up": up,
            "sr_route": route,
            "sr_hops": sr_hops[-1],
        })
    skeleton_edges = {frozenset(edge) for edge in graph.edges()}
    if any(any(frozenset(edge) not in skeleton_edges for edge in frame.edges()) for frame in frames):
        raise RuntimeError("assembled frame contains an edge outside the skeleton")

    sr_runs = run_lengths(sr_mask)
    completed_sr = [length for _, _, length, complete in sr_runs if complete]
    sr_transitions = sum(left != right for left, right in zip(sr_mask, sr_mask[1:]))
    first_outage = next((index for index, value in enumerate(sr_mask) if not value), None)
    empirical_pi = total_edge_ups / (len(edges) * FRAMES)
    completed_mean = statistics.mean(edge_completed_runs) if edge_completed_runs else math.nan
    metrics = {
        "generator": GENERATOR,
        "graph_id": "er_N92_r1",
        "graph_sha256": GRAPH_SHA256,
        "node_count": N,
        "edge_count": len(edges),
        "source": SOURCE,
        "destination": DESTINATION,
        "base_seed": base_seed,
        "pi_target": pi,
        "mean_up_duration_target": duration,
        "p_down_given_up": p10,
        "p_up_given_down": p01,
        "edge_pooled_up_fraction": empirical_pi,
        "edge_up_fraction_abs_error": abs(empirical_pi - pi),
        "edge_mean_completed_up_run_duration": completed_mean,
        "edge_mean_completed_up_run_relative_error": abs(completed_mean - duration) / duration,
        "edge_total_transitions": total_edge_transitions,
        "edge_completed_up_run_count": len(edge_completed_runs),
        "edge_censored_up_run_count": sum(not complete for bits in edge_bits for _, _, _, complete in run_lengths(bits)),
        "edge_marginal_pass": abs(empirical_pi - pi) <= 0.02,
        "edge_persistence_pass": abs(completed_mean - duration) / duration <= 0.05,
        "sr_uptime": sum(sr_mask) / FRAMES,
        "sr_up_count": sum(sr_mask),
        "sr_up_run_lengths": [length for _, _, length, _ in sr_runs],
        "sr_completed_up_run_lengths": completed_sr,
        "sr_transitions": sr_transitions,
        "sr_first_outage_frame": first_outage,
        "sr_hop_counts": sr_hops,
        "sr_routes": sr_routes,
        "all_edges_in_skeleton": True,
        "reporting_integrity_pass": all(row["generator"] == GENERATOR for row in edge_rows + frame_rows),
    }
    metrics["operation_pass"] = metrics["edge_marginal_pass"] and metrics["edge_persistence_pass"] and metrics["all_edges_in_skeleton"] and metrics["reporting_integrity_pass"]
    write_json(out / "trace_metrics.json", metrics)
    write_csv(out / "edge_states.csv", edge_rows, [
        "generator", "u", "v", "edge_seed", "states", "transitions",
        "completed_up_run_lengths", "completed_up_run_count", "censored_up_run_lengths",
    ])
    with (out / "frames.jsonl").open("w", encoding="utf-8") as stream:
        for row in frame_rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    write_json(out / "operation_status.json", {"generator": GENERATOR, "status": "success"})
    return 0


def condition_cell_is_feasible(pi: float, duration: float) -> bool:
    return 0.0 <= 1.0 / duration <= 1.0 and 0.0 <= pi / ((1.0 - pi) * duration) <= 1.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", type=Path)
    args = parser.parse_args()
    if args.child:
        try:
            return child(args.child)
        except Exception as exc:
            write_json(args.child.parent / "operation_status.json", {
                "generator": GENERATOR,
                "status": "failed_exception",
                "exception": repr(exc),
                "traceback": traceback.format_exc(),
            })
            return 1

    RESULTS.mkdir(parents=True, exist_ok=True)
    if sha256_file(PREREG_PATH) != "7d0363b2b74ca247acf4fbbf3cfe5f8be03fda0adf3e1766d2c3a7471983a408":
        raise RuntimeError("registered preregistration hash mismatch")
    graph, edges = load_skeleton()
    runner_hash = sha256_file(Path(__file__).resolve())
    prereg_hash = sha256_file(PREREG_PATH)
    records: list[dict] = []
    execution_rows: list[dict] = []
    for pi in PIS:
        for duration in DURATIONS:
            feasible = condition_cell_is_feasible(pi, duration)
            for seed in SEEDS:
                key = f"pi_{pi:.1f}_L_{duration:.0f}_seed_{seed}"
                out = RESULTS / "operations" / key
                config_path = out / "config.json"
                config = {
                    "generator": GENERATOR,
                    "kind": "edge_markovian_generator_only",
                    "graph_id": "er_N92_r1",
                    "graph_path_relative": "../A1/results/edge_lists/er_N92_r1.csv",
                    "graph_sha256": GRAPH_SHA256,
                    "node_count": N,
                    "edge_count": len(edges),
                    "source": SOURCE,
                    "destination": DESTINATION,
                    "frames": FRAMES,
                    "pi": pi,
                    "mean_up_duration": duration,
                    "base_seed": seed,
                    "edge_seed_rule": "base_seed + 104729*edge_index; lexicographically sorted integer endpoints",
                    "timeout_seconds": TIMEOUT_SECONDS,
                    "retry_policy": "no retries or replacements",
                    "runner_sha256": runner_hash,
                    "preregistration_sha256": prereg_hash,
                    "python_version": sys.version,
                    "networkx_version": nx.__version__,
                    "status": "scheduled" if feasible else "not_run_infeasible",
                }
                write_json(config_path, config)
                row = {
                    "generator": GENERATOR,
                    "condition_id": key,
                    "pi_target": pi,
                    "mean_up_duration_target": duration,
                    "base_seed": seed,
                    "analytic_feasible": feasible,
                    "status": "scheduled" if feasible else "not_run_infeasible",
                    "runtime_seconds": "",
                    "operation_pass": False,
                    "config_sha256": sha256_file(config_path),
                }
                if not feasible:
                    row["status"] = "not_run_infeasible"
                    write_json(out / "operation_status.json", {
                        "generator": GENERATOR,
                        "status": "not_run_infeasible",
                        "p_up_given_down": pi / ((1.0 - pi) * duration),
                        "reason": "transition probability lies outside [0,1]; no random generation attempted",
                    })
                    records.append(row)
                    continue
                start = time.perf_counter()
                try:
                    completed = subprocess.run(
                        [sys.executable, str(Path(__file__).resolve()), "--child", str(config_path)],
                        cwd=HERE,
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_SECONDS,
                        check=False,
                    )
                    runtime = time.perf_counter() - start
                    row["runtime_seconds"] = runtime
                    if completed.returncode == 0:
                        metrics = json.loads((out / "trace_metrics.json").read_text(encoding="utf-8"))
                        row.update({
                            "status": "success",
                            "operation_pass": metrics["operation_pass"],
                            "edge_pooled_up_fraction": metrics["edge_pooled_up_fraction"],
                            "edge_up_fraction_abs_error": metrics["edge_up_fraction_abs_error"],
                            "edge_mean_completed_up_run_duration": metrics["edge_mean_completed_up_run_duration"],
                            "edge_mean_completed_up_run_relative_error": metrics["edge_mean_completed_up_run_relative_error"],
                            "edge_total_transitions": metrics["edge_total_transitions"],
                            "sr_uptime": metrics["sr_uptime"],
                            "sr_up_count": metrics["sr_up_count"],
                            "sr_transitions": metrics["sr_transitions"],
                            "sr_first_outage_frame": metrics["sr_first_outage_frame"],
                            "all_edges_in_skeleton": metrics["all_edges_in_skeleton"],
                            "reporting_integrity_pass": metrics["reporting_integrity_pass"],
                        })
                        failure = "" if metrics["operation_pass"] else "one or more registered per-operation numeric gates failed"
                    else:
                        row["status"] = "failed_exit"
                        failure = f"exit={completed.returncode}; stderr={completed.stderr[-2000:]}"
                except subprocess.TimeoutExpired:
                    runtime = time.perf_counter() - start
                    row.update({"status": "timeout", "runtime_seconds": runtime})
                    failure = "60-second timeout; no retry"
                except Exception as exc:
                    runtime = time.perf_counter() - start
                    row.update({"status": "runner_error", "runtime_seconds": runtime})
                    failure = repr(exc)
                write_json(out / "parent_status.json", {
                    "generator": GENERATOR,
                    "status": row["status"],
                    "runtime_seconds": row["runtime_seconds"],
                    "failure": failure,
                })
                if row["status"] != "success":
                    write_json(out / "operation_status.json", {
                        "generator": GENERATOR,
                        "status": row["status"],
                        "failure": failure,
                    })
                records.append(row)
                execution_rows.append({"condition_id": key, "status": row["status"], "runtime_seconds": row["runtime_seconds"], "failure": failure})

    fields = [
        "generator", "condition_id", "pi_target", "mean_up_duration_target", "base_seed",
        "analytic_feasible", "status", "runtime_seconds", "operation_pass", "config_sha256",
        "edge_pooled_up_fraction", "edge_up_fraction_abs_error", "edge_mean_completed_up_run_duration",
        "edge_mean_completed_up_run_relative_error", "edge_total_transitions", "sr_uptime", "sr_up_count",
        "sr_transitions", "sr_first_outage_frame", "all_edges_in_skeleton", "reporting_integrity_pass",
    ]
    write_csv(RESULTS / "operation_summary.csv", records, fields)
    write_csv(RESULTS / "execution_log.csv", execution_rows, ["condition_id", "status", "runtime_seconds", "failure"])

    feasible_rows = [row for row in records if row["analytic_feasible"]]
    condition_rows = []
    for pi in PIS:
        for duration in DURATIONS:
            cell = [row for row in feasible_rows if row["pi_target"] == pi and row["mean_up_duration_target"] == duration]
            if not cell:
                continue
            condition_rows.append({
                "generator": GENERATOR,
                "pi_target": pi,
                "mean_up_duration_target": duration,
                "n": len(cell),
                "edge_pooled_up_fraction_mean": statistics.mean(float(row["edge_pooled_up_fraction"]) for row in cell),
                "edge_pooled_up_fraction_sample_sd_ddof1": statistics.stdev(float(row["edge_pooled_up_fraction"]) for row in cell),
                "edge_mean_completed_up_run_duration_mean": statistics.mean(float(row["edge_mean_completed_up_run_duration"]) for row in cell),
                "edge_mean_completed_up_run_duration_sample_sd_ddof1": statistics.stdev(float(row["edge_mean_completed_up_run_duration"]) for row in cell),
                "sr_uptime_mean": statistics.mean(float(row["sr_uptime"]) for row in cell),
                "sr_uptime_sample_sd_ddof1": statistics.stdev(float(row["sr_uptime"]) for row in cell),
                "sr_transitions_mean": statistics.mean(float(row["sr_transitions"]) for row in cell),
                "sr_transitions_sample_sd_ddof1": statistics.stdev(float(row["sr_transitions"]) for row in cell),
            })
    write_csv(RESULTS / "condition_summary.csv", condition_rows, list(condition_rows[0]) if condition_rows else ["generator", "pi_target", "mean_up_duration_target", "n"])

    feasibility_pass = len(records) == 20 and sum(bool(row["analytic_feasible"]) for row in records) == 15 and sum(row["status"] == "not_run_infeasible" for row in records) == 5
    completion_pass = len(feasible_rows) == 15 and all(row["status"] == "success" and float(row["runtime_seconds"]) <= TIMEOUT_SECONDS for row in feasible_rows)
    edge_provenance_pass = all(row.get("all_edges_in_skeleton") is True for row in feasible_rows)
    marginal_pass = all(float(row.get("edge_up_fraction_abs_error", math.inf)) <= 0.02 for row in feasible_rows)
    persistence_pass = all(float(row.get("edge_mean_completed_up_run_relative_error", math.inf)) <= 0.05 for row in feasible_rows)
    reporting_pass = all(row.get("reporting_integrity_pass") is True for row in records) and all(
        (RESULTS / "operations" / row["condition_id"] / "frames.jsonl").is_file()
        and (RESULTS / "operations" / row["condition_id"] / "edge_states.csv").is_file()
        for row in feasible_rows
    )
    gates = {
        "generator": GENERATOR,
        "preregistration_sha256": prereg_hash,
        "runner_sha256": runner_hash,
        "graph_sha256": GRAPH_SHA256,
        "registered_rows": len(records),
        "feasible_operations": sum(bool(row["analytic_feasible"]) for row in records),
        "infeasible_not_run_rows": sum(row["status"] == "not_run_infeasible" for row in records),
        "analytic_feasibility_pass": feasibility_pass,
        "completion_and_provenance_pass": completion_pass and edge_provenance_pass,
        "edge_marginal_gate_pass": marginal_pass,
        "edge_persistence_gate_pass": persistence_pass,
        "reporting_integrity_pass": reporting_pass,
        "overall_pass": feasibility_pass and completion_pass and edge_provenance_pass and marginal_pass and persistence_pass and reporting_pass,
        "sample_sd_ddof": 1,
        "protocol_variants": 0,
        "ns3_executed": False,
        "yadygaga_pooled": False,
    }
    write_json(RESULTS / "gate_summary.json", gates)
    write_result_report(records, gates, condition_rows)
    manifest_rows = []
    for path in sorted(RESULTS.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.sha256":
            manifest_rows.append(f"{sha256_file(path)}  {path.relative_to(RESULTS).as_posix()}")
    (RESULTS / "artifact_manifest.sha256").write_text("\n".join(manifest_rows) + "\n", encoding="utf-8")
    print(json.dumps(gates, indent=2, sort_keys=True))
    return 0 if gates["overall_pass"] else 2


def write_result_report(records: list[dict], gates: dict, conditions: list[dict]) -> None:
    lines = [
        "# A2e result — isolated edge-Markovian fallback validation",
        "",
        "**Generator label:** `edge_markovian` only. This is a generator-only validation, isolated under `alpha/EM/`; it is not a YaDyGaGa modification or comparison. No rows, plots, or inferential summaries are pooled with YaDyGaGa.",
        "",
        f"**Outcome:** {'PASS' if gates['overall_pass'] else 'FAIL under frozen preregistered gates'}.",
        "",
        f"Preregistration SHA-256: `{gates['preregistration_sha256']}`. Runner SHA-256: `{gates['runner_sha256']}`. Graph SHA-256: `{gates['graph_sha256']}`.",
        "",
        "## Frozen gates and outcomes",
        "",
        f"- Analytic feasibility: {'PASS' if gates['analytic_feasibility_pass'] else 'FAIL'}; {gates['feasible_operations']} feasible operations and {gates['infeasible_not_run_rows']} infeasible rows marked not run.",
        f"- Completion and provenance: {'PASS' if gates['completion_and_provenance_pass'] else 'FAIL'}; separate-process operations use a 60-second no-retry limit and frames are skeleton subgraphs.",
        f"- Edge marginal absolute error <=.02: {'PASS' if gates['edge_marginal_gate_pass'] else 'FAIL'}.",
        f"- Pooled completed edge up-run relative error <=.05: {'PASS' if gates['edge_persistence_gate_pass'] else 'FAIL'}.",
        f"- `edge_markovian` labeling and required per-frame/per-edge outputs: {'PASS' if gates['reporting_integrity_pass'] else 'FAIL'}.",
        "",
        "The edge persistence estimator excludes up-runs censored by either boundary; censored run lengths and counts are retained in edge-level outputs. S–R uptime, routes, first outage, run lengths, transitions, and hop counts are descriptive only. The requested edge π is not interpreted as a target S–R uptime.",
        "",
        "Condition-level means and sample standard deviations use five seed-level observations and `ddof=1`; details are in `condition_summary.csv`.",
        "",
        "## Condition summary",
        "",
        "| π | L | n | Edge up fraction mean (sample SD) | Completed up-run mean (sample SD) | S–R uptime mean (sample SD) |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in conditions:
        lines.append(
            f"| {row['pi_target']:.1f} | {row['mean_up_duration_target']:.0f} | {row['n']} | {row['edge_pooled_up_fraction_mean']:.6f} ({row['edge_pooled_up_fraction_sample_sd_ddof1']:.6f}) | {row['edge_mean_completed_up_run_duration_mean']:.6f} ({row['edge_mean_completed_up_run_duration_sample_sd_ddof1']:.6f}) | {row['sr_uptime_mean']:.6f} ({row['sr_uptime_sample_sd_ddof1']:.6f}) |"
        )
    lines += [
        "",
        "## Scope and stop boundary",
        "",
        "Only ER N=92 realization 1, pair (5,82), 120 frames, the preregistered π/L cells, and five seeds were tested. The infeasible π=.8,L=2 rows were not sampled or substituted. Results do not establish broad EM capability, routing/protocol performance, or equivalence to YaDyGaGa. No ns-3, 0 protocol variants, no A3.",
        "",
        "All operation configs, seed-specific edge strings, frame edge lists/fingerprints, routes/hops, and per-operation status are retained under `operations/`. Artifact hashes are in `artifact_manifest.sha256`; the manifest does not hash itself.",
    ]
    (RESULTS / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
