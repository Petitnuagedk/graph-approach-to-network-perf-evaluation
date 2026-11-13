#!/usr/bin/env python3
"""Run the preregistered A2g-2 single-pair pool supply grid."""
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
from collections import Counter
from pathlib import Path
from typing import Any

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A1 = ROOT / "alpha" / "A1" / "results"
GRAPH_DIR = A1 / "edge_lists"
COVARIATES = A1 / "graph_covariates.csv"
PREREG = HERE / "a2g2_prereg.md"
OUT = HERE / "A2g-2"
P_GRID = tuple(i / 10 for i in range(1, 10))
TRIAL_GRID = (3000, 10000)
SEEDS = (11, 29, 47)
LIVES = (0.3, 0.5, 0.7, 0.9)
F_VALUES = (120, 240)
TIMEOUT = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def graph_records() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in read_csv(COVARIATES):
        if int(row["realization"]) != 1 or int(row["N"]) not in (42, 92, 162):
            continue
        graph = load_graph(row["graph_id"], int(row["N"]))
        source, destination = int(row["probe_S"]), int(row["probe_R"])
        result.append({
            "family": row["family"],
            "graph_id": row["graph_id"],
            "N": int(row["N"]),
            "source": source,
            "destination": destination,
            "degree_s": int(graph.degree[source]),
            "degree_r": int(graph.degree[destination]),
            "endpoint_edge_shared": bool(graph.has_edge(source, destination)),
            "diameter": float(row["diameter"]),
            "mean_degree": float(row["mean_degree"]),
        })
    if len(result) != 15:
        raise RuntimeError(f"expected 15 A1 r1 graphs, found {len(result)}")
    return sorted(result, key=lambda x: (x["family"], x["N"]))


def load_graph(graph_id: str, n: int) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    with (GRAPH_DIR / f"{graph_id}.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def dsu_find(parent: list[int], node: int) -> int:
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node


def dsu_union(parent: list[int], rank: list[int], left: int, right: int) -> None:
    root_left, root_right = dsu_find(parent, left), dsu_find(parent, right)
    if root_left == root_right:
        return
    if rank[root_left] < rank[root_right]:
        root_left, root_right = root_right, root_left
    parent[root_right] = root_left
    if rank[root_left] == rank[root_right]:
        rank[root_left] += 1


def op_name(graph: dict[str, Any], p: float, trials: int, seed: int) -> str:
    return f"{graph['family']}_N{graph['N']}_r1__p{p:.1f}__t{trials}__seed{seed}"


def demands(frames: int, life: float) -> tuple[int, int]:
    up = round(frames * life)
    return up, frames - up


def build_config(graph: dict[str, Any], p: float, trials: int, seed: int) -> dict[str, Any]:
    edge_file = GRAPH_DIR / f"{graph['graph_id']}.csv"
    return {
        "stage": "A2g-2",
        "family": graph["family"],
        "graph_id": graph["graph_id"],
        "N": graph["N"],
        "graph_edge_list": edge_file.relative_to(ROOT).as_posix(),
        "graph_edge_sha256": sha256(edge_file),
        "source_node": graph["source"],
        "destination_node": graph["destination"],
        "endpoint_degree_S": graph["degree_s"],
        "endpoint_degree_R": graph["degree_r"],
        "endpoint_edge_shared": graph["endpoint_edge_shared"],
        "mean_degree": graph["mean_degree"],
        "diameter": graph["diameter"],
        "p_edge": p,
        "frame_pool_trials": trials,
        "pool_seed": seed,
        "timeout_seconds": TIMEOUT,
        "sampler_behavior": "legacy-iid-frame-pool-count-only-equivalent",
        "with_replacement_assembly": True,
        "source_sha256": {
            "A2d_item1_frameGenerator.py": sha256(
                ROOT / "alpha" / "A2" / "A2d" / "item1" / "source" / "yadygaga" / "frameGenerator.py"
            ),
            "A2d_item1_dynaGraph.py": sha256(
                ROOT / "alpha" / "A2" / "A2d" / "item1" / "source" / "yadygaga" / "dynaGraph.py"
            ),
            "runner": sha256(Path(__file__).resolve()),
        },
        "preregistration_sha256": sha256(PREREG),
        "python": sys.version,
        "networkx": nx.__version__,
    }


def worker(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out_dir = config_path.parent
    started = time.perf_counter()
    try:
        if sha256(ROOT / config["graph_edge_list"]) != config["graph_edge_sha256"]:
            raise ValueError("graph edge-list hash mismatch")
        graph = load_graph(config["graph_id"], int(config["N"]))
        source, target = int(config["source_node"]), int(config["destination_node"])
        p_edge, trials, seed = float(config["p_edge"]), int(config["frame_pool_trials"]), int(config["pool_seed"])
        edges = list(graph.edges())
        degree_s, degree_r = graph.degree[source], graph.degree[target]
        endpoint_shared = graph.has_edge(source, target)
        rng = random.Random(seed)
        up_count = 0
        down_count = 0
        connected_count = 0
        shortest_path_groups: Counter[tuple[int, ...]] = Counter()
        for _ in range(trials):
            sampled_edges = []
            parent = list(range(graph.number_of_nodes()))
            rank = [0] * graph.number_of_nodes()
            for left, right in edges:
                if rng.random() < p_edge:
                    sampled_edges.append((left, right))
                    dsu_union(parent, rank, left, right)
            if dsu_find(parent, source) == dsu_find(parent, target):
                connected_count += 1
                sampled = nx.Graph()
                sampled.add_nodes_from(graph.nodes())
                sampled.add_edges_from(sampled_edges)
                path = tuple(nx.shortest_path(sampled, source, target))
                shortest_path_groups[path] += 1
                up_count += 1
            else:
                down_count += 1

        p_s_iso = (1.0 - p_edge) ** degree_s
        p_r_iso = (1.0 - p_edge) ** degree_r
        p_both_iso = (1.0 - p_edge) ** (degree_s + degree_r - int(endpoint_shared))
        isolation_union = p_s_iso + p_r_iso - p_both_iso
        f_down = down_count / trials
        per_life: dict[str, Any] = {}
        for frames in F_VALUES:
            for life in LIVES:
                up_demand, down_demand = demands(frames, life)
                per_life[f"F{frames}_life{life:.1f}"] = {
                    "U_demand": up_demand,
                    "D_demand": down_demand,
                    "up_sufficient": up_count >= up_demand,
                    "down_sufficient": down_count >= down_demand,
                    "supply_ready": up_count >= up_demand and down_count >= down_demand,
                }
        metrics = {
            "status": "success",
            "up_pool_frames": up_count,
            "down_pool_frames": down_count,
            "up_pool_groups": len(shortest_path_groups),
            "up_pool_group_sizes": dict(sorted((json.dumps(path, separators=(",", ":")), count) for path, count in shortest_path_groups.items())),
            "connectivity_fraction": connected_count / trials,
            "observed_down_fraction": f_down,
            "endpoint_degree_S": degree_s,
            "endpoint_degree_R": degree_r,
            "endpoint_edge_shared": endpoint_shared,
            "p_source_isolated_exact": p_s_iso,
            "p_destination_isolated_exact": p_r_iso,
            "p_both_isolated_exact": p_both_iso,
            "p_either_endpoint_isolated_exact": isolation_union,
            "down_to_isolation_ratio": f_down / isolation_union if f_down > 0 else None,
            "positive_down": f_down > 0,
            "supply_by_frame_life": per_life,
            "strict_all_life_F120": up_count >= 108 and down_count >= 84,
            "strict_all_life_F240": up_count >= 216 and down_count >= 168,
            "replacement_assembly_feasible": up_count > 0 and down_count > 0,
            "elapsed_worker_seconds": time.perf_counter() - started,
        }
        write_json(out_dir / "pool_metrics.json", metrics)
        write_json(out_dir / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(out_dir / "operation_status.json", {
            "status": "failed_exception",
            "exception": repr(error),
            "elapsed_worker_seconds": time.perf_counter() - started,
        })
        return 1


def ols_slope(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator if denominator else None


def summarize(op_rows: list[dict[str, Any]], operation_dirs: dict[str, Path]) -> dict[str, Any]:
    successful: list[dict[str, Any]] = []
    for row in op_rows:
        if row["status"] != "success":
            continue
        metrics = json.loads((operation_dirs[row["operation"]] / "pool_metrics.json").read_text(encoding="utf-8"))
        successful.append({**row, **metrics})

    per_seed = []
    for row in successful:
        for frames in F_VALUES:
            for life in LIVES:
                key = f"F{frames}_life{life:.1f}"
                per_seed.append({
                    "operation": row["operation"], "family": row["family"], "graph_id": row["graph_id"],
                    "N": row["N"], "p_edge": row["p_edge"], "trials": row["trials"], "seed": row["seed"],
                    "F": frames, "life": life, **row["supply_by_frame_life"][key],
                })

    pstar_seed_rows = []
    for graph in graph_records():
        graph_id = graph["graph_id"]
        for trials in TRIAL_GRID:
            for seed in SEEDS:
                matching = [
                    row for row in successful
                    if row["graph_id"] == graph_id and int(row["trials"]) == trials
                    and int(row["seed"]) == seed and row["strict_all_life_F120"]
                ]
                pstar = max((float(row["p_edge"]) for row in matching), default=None)
                matching_240 = [
                    row for row in successful
                    if row["graph_id"] == graph_id and int(row["trials"]) == trials
                    and int(row["seed"]) == seed and row["strict_all_life_F240"]
                ]
                pstar240 = max((float(row["p_edge"]) for row in matching_240), default=None)
                pstar_seed_rows.append({
                    "family": graph["family"], "graph_id": graph_id, "N": graph["N"], "trials": trials,
                    "seed": seed, "pstar_F120": pstar, "pstar_F240": pstar240,
                })

    pstar_graph_rows = []
    graph_lookup = {row["graph_id"]: row for row in graph_records()}
    for graph in graph_records():
        for trials in TRIAL_GRID:
            group = [row for row in pstar_seed_rows if row["graph_id"] == graph["graph_id"] and row["trials"] == trials]
            record: dict[str, Any] = {
                **graph, "trials": trials,
                "n_seed_pstar_F120": sum(row["pstar_F120"] is not None for row in group),
                "n_seed_pstar_F240": sum(row["pstar_F240"] is not None for row in group),
            }
            for field in ("pstar_F120", "pstar_F240"):
                values = [float(row[field]) for row in group if row[field] is not None]
                record[field + "_mean"] = statistics.mean(values) if values else None
                record[field + "_sample_sd_ddof1"] = statistics.stdev(values) if len(values) > 1 else None
            pstar_graph_rows.append(record)

    by_stratum: dict[tuple[str, int, float, int], list[dict[str, Any]]] = {}
    for row in successful:
        by_stratum.setdefault((row["graph_id"], int(row["trials"]), float(row["p_edge"]), int(row["N"])), []).append(row)
    stratum_rows = []
    for key, group in sorted(by_stratum.items()):
        graph = graph_lookup[key[0]]
        stratum_rows.append({
            "graph_id": key[0], "family": graph["family"], "N": graph["N"], "trials": key[1], "p_edge": key[2],
            "n_seeds": len(group),
            "up_pool_frames_mean": statistics.mean(row["up_pool_frames"] for row in group),
            "up_pool_frames_sample_sd_ddof1": statistics.stdev(row["up_pool_frames"] for row in group) if len(group) > 1 else None,
            "down_pool_frames_mean": statistics.mean(row["down_pool_frames"] for row in group),
            "down_pool_frames_sample_sd_ddof1": statistics.stdev(row["down_pool_frames"] for row in group) if len(group) > 1 else None,
            "distinct_path_groups_mean": statistics.mean(row["up_pool_groups"] for row in group),
            "connectivity_fraction_mean": statistics.mean(row["connectivity_fraction"] for row in group),
            "observed_down_fraction_mean": statistics.mean(row["observed_down_fraction"] for row in group),
            "F120_all_life_ready_seeds": sum(bool(row["strict_all_life_F120"]) for row in group),
            "F240_all_life_ready_seeds": sum(bool(row["strict_all_life_F240"]) for row in group),
        })

    positive = [row for row in successful if row["positive_down"]]
    ratios = [float(row["down_to_isolation_ratio"]) for row in positive]
    isolation_passes = sum(1.0 <= value <= 3.0 for value in ratios)

    trend_results = []
    for family in sorted({row["family"] for row in pstar_graph_rows}):
        for trials in TRIAL_GRID:
            sequence = sorted(
                [row for row in pstar_graph_rows if row["family"] == family and row["trials"] == trials],
                key=lambda row: row["N"],
            )
            values = [row["pstar_F120_mean"] for row in sequence]
            defined = all(value is not None for value in values)
            nonincreasing = defined and all(values[index] >= values[index + 1] for index in range(len(values) - 1))
            trend_results.append({
                "family": family, "trials": trials, "pstar_by_N": values,
                "all_sizes_defined": defined, "nonincreasing": nonincreasing,
            })

    complete_trend_families = {
        trials: sum(
            all(row["nonincreasing"] for row in trend_results if row["family"] == family and row["trials"] == trials)
            for family in sorted({row["family"] for row in trend_results})
        )
        for trials in TRIAL_GRID
    }
    trend_pass = all(value >= 4 for value in complete_trend_families.values())

    f120_graphs = [row for row in pstar_graph_rows if row["pstar_F120_mean"] is not None]
    slope_ep = ols_slope(
        [(row["endpoint_degree_S"] + row["endpoint_degree_R"]) / 2 for row in f120_graphs],
        [row["pstar_F120_mean"] for row in f120_graphs],
    )
    slope_mean = ols_slope([row["mean_degree"] for row in f120_graphs], [row["pstar_F120_mean"] for row in f120_graphs])
    slope_n = ols_slope([float(row["N"]) for row in f120_graphs], [row["pstar_F120_mean"] for row in f120_graphs])
    slope_diameter = ols_slope([row["diameter"] for row in f120_graphs], [row["pstar_F120_mean"] for row in f120_graphs])
    all_success = len(successful) == 810
    gate_isolation = bool(ratios) and isolation_passes / len(ratios) >= 0.80
    gate_slopes = slope_ep is not None and slope_ep <= 0 and slope_mean is not None and slope_mean <= 0
    h2 = {
        "status": "SUPPORTED" if all_success and gate_isolation and trend_pass and gate_slopes else "NOT_SUPPORTED",
        "operations_registered": 810,
        "operations_successful": len(successful),
        "all_operations_successful": all_success,
        "positive_down_operation_cells": len(positive),
        "isolation_ratio_passes": isolation_passes,
        "isolation_ratio_pass_fraction": isolation_passes / len(ratios) if ratios else None,
        "required_isolation_fraction": 0.80,
        "isolation_ratio_bounds": [1.0, 3.0],
        "isolation_gate": gate_isolation,
        "pstar_monotonic_family_count_by_trials": complete_trend_families,
        "required_monotonic_families_each_trial_count": 4,
        "pstar_trend_gate": trend_pass,
        "ols_slopes_using_defined_F120_graph_trial_rows": {
            "unit_count": len(f120_graphs),
            "mean_endpoint_degree": slope_ep,
            "graph_mean_degree": slope_mean,
            "N": slope_n,
            "diameter_descriptive_only": slope_diameter,
        },
        "slope_gate": gate_slopes,
    }

    write_csv(OUT / "per_operation.csv", op_rows)
    write_csv(OUT / "per_seed_supply.csv", per_seed)
    write_csv(OUT / "pool_summary_by_graph_p_trials.csv", stratum_rows)
    write_csv(OUT / "pstar_per_seed.csv", pstar_seed_rows)
    write_csv(OUT / "pstar_by_graph_trials.csv", pstar_graph_rows)
    write_json(OUT / "summary.json", {
        "h2": h2,
        "pstar_monotonic_sequences": trend_results,
        "positive_down_ratio_summary": {
            "n": len(ratios),
            "mean": statistics.mean(ratios) if ratios else None,
            "sample_sd_ddof1": statistics.stdev(ratios) if len(ratios) > 1 else None,
            "max": max(ratios) if ratios else None,
        },
        "limits": [
            "one graph realization per family and size",
            "fixed structural-rule probe pairs",
            "legacy iid pool baseline differs from adopted uk plus patched-v3 Beta timeline interface",
            "strict quota-capacity counts are conservative relative to with-replacement assembly",
            "time-respecting reachability, if later reported, allows store-carry-forward and is descriptive only",
        ],
    })
    print(json.dumps(h2, indent=2, sort_keys=True))


def run_grid() -> int:
    graphs = graph_records()
    graph_data = []
    graph_data.extend(graphs)

    op_rows: list[dict[str, Any]] = []
    op_dirs: dict[str, Path] = {}
    jobs = [
        (graph, p_edge, trials, seed)
        for graph in graph_data
        for p_edge in P_GRID
        for trials in TRIAL_GRID
        for seed in SEEDS
    ]
    for index, (graph, p_edge, trials, seed) in enumerate(jobs, start=1):
        name = op_name(graph, p_edge, trials, seed)
        out_dir = OUT / "operations" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        config_path = out_dir / "config.json"
        config = build_config(graph, p_edge, trials, seed)
        write_json(config_path, config)
        op_dirs[name] = out_dir
        command = [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)]
        started = time.perf_counter()
        try:
            process = subprocess.run(command, cwd=HERE, timeout=TIMEOUT, capture_output=True, text=True, check=False)
            elapsed = time.perf_counter() - started
            status_doc = json.loads((out_dir / "operation_status.json").read_text(encoding="utf-8")) if (out_dir / "operation_status.json").exists() else {"status": "missing_status"}
            status = status_doc.get("status", "missing_status")
            row = {
                "operation": name, "status": status, "returncode": process.returncode,
                "elapsed_seconds": elapsed, "family": graph["family"], "graph_id": graph["graph_id"],
                "N": graph["N"], "p_edge": p_edge, "trials": trials, "seed": seed,
                "config_sha256": sha256(config_path), "config_path": config_path.relative_to(ROOT).as_posix(),
                "stdout": process.stdout[-1000:], "stderr": process.stderr[-1000:],
            }
        except subprocess.TimeoutExpired as error:
            elapsed = time.perf_counter() - started
            write_json(out_dir / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": TIMEOUT, "elapsed_seconds": elapsed})
            row = {
                "operation": name, "status": "failed_timeout", "returncode": "TIMEOUT",
                "elapsed_seconds": elapsed, "family": graph["family"], "graph_id": graph["graph_id"],
                "N": graph["N"], "p_edge": p_edge, "trials": trials, "seed": seed,
                "config_sha256": sha256(config_path), "config_path": config_path.relative_to(ROOT).as_posix(),
                "stdout": (error.stdout or b"").decode(errors="replace")[-1000:] if isinstance(error.stdout, bytes) else str(error.stdout or "")[-1000:],
                "stderr": (error.stderr or b"").decode(errors="replace")[-1000:] if isinstance(error.stderr, bytes) else str(error.stderr or "")[-1000:],
            }
        op_rows.append(row)
        write_csv(OUT / "operation_log.csv", op_rows)
        print(f"[{index}/{len(jobs)}] {name}: {row['status']} ({elapsed:.2f}s)", flush=True)
    summarize(op_rows, op_dirs)
    return 0 if all(row["status"] == "success" for row in op_rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path)
    args = parser.parse_args()
    if args.operation:
        return worker(args.operation.resolve())
    return run_grid()


if __name__ == "__main__":
    raise SystemExit(main())
