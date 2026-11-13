#!/usr/bin/env python3
"""Execute A2c's preregistered, isolated YaDyGaGa trace grid."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
A2 = HERE.parent
ROOT = HERE.parents[3]
RESULTS = HERE / "results"
A1 = A2.parent / "A1"
SOURCE = A2.parent / "A0R2" / "YaDyGaGa"
TIMELINE_SOURCE = SOURCE / "yadygaga" / "timelineBlockGenerator.py"
FRAME_SOURCE = SOURCE / "yadygaga" / "frameGenerator.py"
ASSEMBLY_SOURCE = SOURCE / "yadygaga" / "dynaGraph.py"
PREREG = HERE / "prereg.md"
ADDENDUM = HERE / "prereg_addendum_1.md"
FAMILIES = {
    "geodesic": ("geodesic_N92_r1", 0, 31),
    "rgg": ("rgg_N92_r1", 14, 47),
    "ws": ("ws_N92_r1", 49, 85),
    "er": ("er_N92_r1", 5, 82),
    "ba": ("ba_N92_r1", 5, 72),
}
LIVES = (0.3, 0.5, 0.7, 0.9)
STABILITY = {0.3: 0.3, 0.5: 0.5, 0.7: 0.7, 0.9: 0.9}
SEEDS = {
    0.3: (42, 63, 178, 107, 56),
    0.5: (42, 98, 90, 126, 236),
    0.7: (42, 228, 199, 235, 44),
    0.9: (42, 44, 58, 112, 191),
}
P_EDGES = (0.3, 0.5, 0.7)
TRIALS = 3000
PERSISTENCY = 0.75
TIMEOUT = 60
GENERATOR = "yadygaga_patched"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_path(family: str) -> Path:
    graph_id = FAMILIES[family][0]
    return A1 / "results" / "edge_lists" / f"{graph_id}.csv"


def read_graph(family: str) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    with graph_path(family).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def config_for(family: str, life: float, seed: int, p_edge: float) -> dict:
    graph_id, source, destination = FAMILIES[family]
    return {
        "stage": "A2c",
        "generator": GENERATOR,
        "behavior": "patched",
        "family": family,
        "graph_id": graph_id,
        "graph_edge_list": str(graph_path(family).relative_to(ROOT)),
        "graph_edge_sha256": sha256(graph_path(family)),
        "nodes": 92,
        "source_node": source,
        "destination_node": destination,
        "frames": 120,
        "life": life,
        "stability": STABILITY[life],
        "up_count_expected": round(120 * life),
        "up_runs_expected": round(1 + (1 - STABILITY[life]) * (round(120 * life) - 1)),
        "timeline_seed": seed,
        "frame_pool_seed": seed + 10000,
        "assembly_seed": seed + 20000,
        "mode": "blocks",
        "pathPersistency": PERSISTENCY,
        "frame_pool_trials": TRIALS,
        "p_edge": p_edge,
        "timeout_seconds": TIMEOUT,
        "generator_label": GENERATOR,
        "preregistration_sha256": sha256(PREREG),
        "preregistration_addendum_1_sha256": sha256(ADDENDUM),
        "source_tree": "32b243bc84b587f1782ead0d0ac56382a57425e5",
        "source_sha256": {
            "timelineBlockGenerator.py": sha256(TIMELINE_SOURCE),
            "frameGenerator.py": sha256(FRAME_SOURCE),
            "dynaGraph.py": sha256(ASSEMBLY_SOURCE),
            "run_trace_grid.py": sha256(Path(__file__).resolve()),
        },
        "python": sys.version,
        "networkx": nx.__version__,
    }


def lexicographic_shortest_path(graph: nx.Graph, source: int, target: int) -> list[int] | None:
    if source not in graph or target not in graph or not nx.has_path(graph, source, target):
        return None
    from_source = nx.single_source_shortest_path_length(graph, source)
    to_target = nx.single_source_shortest_path_length(graph, target)
    total = from_source[target]
    path = [source]
    current = source
    while current != target:
        options = [
            node for node in graph.neighbors(current)
            if from_source.get(node) == from_source[current] + 1
            and from_source[node] + to_target.get(node, math.inf) == total
        ]
        if not options:
            raise RuntimeError("Unable to reconstruct canonical shortest path")
        current = min(options)
        path.append(current)
    return path


def run_temporal_reachability(frames: list[nx.Graph], source: int, target: int) -> float:
    successes = 0
    for start in range(len(frames)):
        reachable = {source}
        for index in range(start, len(frames)):
            following = set(reachable)  # waiting edges at every node
            for node in reachable:
                following.update(frames[index].neighbors(node))
            reachable = following
        successes += target in reachable
    return successes / len(frames) if frames else 0.0


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def execute_operation(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out_dir = config_path.parent
    try:
        sys.path.insert(0, str(SOURCE))
        from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
        from yadygaga.frameGenerator import FrameGenerator
        from yadygaga.dynaGraph import SPCDynamicGraph

        family = config["family"]
        source, destination = config["source_node"], config["destination_node"]
        life, stability, seed = config["life"], config["stability"], config["timeline_seed"]
        result = SPCTimelineBlockGenerator(
            frames=120,
            path_life=life,
            stability=stability,
            seed=seed,
            mode="blocks",
            pathPersistency=PERSISTENCY,
            behavior="patched",
        ).generate_blocks()
        timeline = result["timeline"]
        path_ids = result["path_ids"]
        expected_u = round(120 * life)
        expected_k = round(1 + (1 - stability) * (expected_u - 1))
        actual_k = sum(is_up and (index == 0 or not timeline[index - 1]) for index, is_up in enumerate(timeline))
        transitions = sum(timeline[index] != timeline[index - 1] for index in range(1, len(timeline)))
        timeline_bits = "".join("1" if bit else "0" for bit in timeline)
        timeline_hash = hashlib.sha256(timeline_bits.encode()).hexdigest()
        a2b_candidate_path = A2 / "A2b" / "results" / f"life_{life:.1f}" / "candidate_timelines.csv"
        with a2b_candidate_path.open(newline="", encoding="utf-8") as stream:
            a2b_timeline = next(row["timeline_sha256"] for row in csv.DictReader(stream) if int(row["seed"]) == seed)
        schedule_identity_match = timeline_hash == a2b_timeline
        write_json(out_dir / "timeline.json", {"bits": timeline_bits, "sha256": timeline_hash, "a2b_sha256": a2b_timeline, "a2b_identity_match": schedule_identity_match, "path_ids": path_ids, "up_count": sum(timeline), "up_runs": actual_k, "transitions": transitions})
        if not schedule_identity_match:
            raise RuntimeError("A2c Boolean schedule hash differs from the frozen A2b candidate")

        skeleton = read_graph(family)
        static_hops = nx.shortest_path_length(skeleton, source, destination)
        frame_generator = FrameGenerator()
        frame_generator.generateSPCFrames(
            limited_G=skeleton,
            s=source,
            d=destination,
            trials=TRIALS,
            p_edge=config["p_edge"],
            pathPersistency=PERSISTENCY,
            seed=seed + 10000,
        )
        up_pool = frame_generator.path_up_frames
        down_pool = frame_generator.path_down_frames
        up_pool_count = sum(len(group) for group in up_pool)
        down_pool_count = len(down_pool)
        write_json(out_dir / "pool_counts.json", {"up_group_count": len(up_pool), "up_frame_count": up_pool_count, "down_frame_count": down_pool_count, "path_up_keys": [list(key) for key in frame_generator.path_up_keys]})
        if up_pool_count == 0 or down_pool_count == 0:
            write_json(out_dir / "operation_status.json", {"status": "failed_empty_pool", "up_pool_count": up_pool_count, "down_pool_count": down_pool_count})
            return 2

        dynamic = SPCDynamicGraph().buildDynaGraph(result, up_pool, down_pool, seed=seed + 20000)
        if len(dynamic) != 120:
            raise RuntimeError(f"assembled frame count {len(dynamic)} != 120")
        skeleton_edges = {frozenset(edge) for edge in skeleton.edges()}
        timeline_usable = []
        frame_rows = []
        edge_rows = []
        canonical_routes = []
        nx_routes = []
        hops = []
        graph_fingerprint_rows = []
        for index, frame in enumerate(dynamic):
            frame_edges = {frozenset(edge) for edge in frame.edges()}
            if not frame_edges <= skeleton_edges:
                raise RuntimeError(f"frame {index} contains an edge outside the skeleton")
            try:
                nx_route = nx.shortest_path(frame, source, destination)
                connected = True
                hop_count = len(nx_route) - 1
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                nx_route = None
                connected = False
                hop_count = None
            canonical = lexicographic_shortest_path(frame, source, destination)
            timeline_usable.append(connected)
            canonical_routes.append(canonical)
            nx_routes.append(nx_route)
            hops.append(hop_count)
            shorter = connected and hop_count < static_hops
            frame_rows.append({
                "frame": index,
                "timeline_up": bool(timeline[index]),
                "s_r_usable": connected,
                "hop_count": "NA" if hop_count is None else hop_count,
                "shortcut": bool(shorter),
                "canonical_route": json.dumps(canonical, separators=(",", ":")),
                "networkx_route": json.dumps(nx_route, separators=(",", ":")),
                "edge_count": len(frame_edges),
            })
            for u, v in sorted((min(edge), max(edge)) for edge in frame.edges()):
                edge_rows.append({"frame": index, "u": u, "v": v})
            graph_fingerprint_rows.append(hashlib.sha256(json.dumps(sorted(tuple(sorted(e)) for e in frame_edges)).encode()).hexdigest())

        uptime = sum(timeline_usable) / 120
        time_reachability = run_temporal_reachability(dynamic, source, destination)
        runs = []
        count = 0
        for state in timeline:
            if state:
                count += 1
            elif count:
                runs.append(count)
                count = 0
        if count:
            runs.append(count)
        run_distribution = {str(length): runs.count(length) / len(runs) for length in range(1, 121)}
        canonical_json = json.dumps(canonical_routes, separators=(",", ":"))
        nx_json = json.dumps(nx_routes, separators=(",", ":"))
        metrics = {
            "status": "success",
            "generator": GENERATOR,
            "family": family,
            "graph_id": config["graph_id"],
            "life": life,
            "stability": stability,
            "p_edge": config["p_edge"],
            "seed": seed,
            "timeline_sha256": hashlib.sha256(timeline_bits.encode()).hexdigest(),
            "a2b_schedule_identity_match": schedule_identity_match,
            "timeline_up_count": sum(timeline),
            "timeline_up_runs": actual_k,
            "expected_up_runs": expected_k,
            "transition_count": transitions,
            "mean_up_run": statistics.mean(runs) if runs else 0.0,
            "max_up_run": max(runs) if runs else 0,
            "up_run_lengths": runs,
            "run_length_distribution": run_distribution,
            "up_pool_group_count": len(up_pool),
            "up_pool_frame_count": up_pool_count,
            "down_pool_frame_count": down_pool_count,
            "measured_usable_fraction": uptime,
            "absolute_fidelity_error": abs(uptime - life),
            "static_hops": static_hops,
            "hop_counts_by_frame": hops,
            "shortcut_fraction": sum(row["shortcut"] for row in frame_rows) / 120,
            "time_respecting_reachability": time_reachability,
            "dilution": life - time_reachability,
            "canonical_route_sequence_sha256": hashlib.sha256(canonical_json.encode()).hexdigest(),
            "networkx_route_sequence_sha256": hashlib.sha256(nx_json.encode()).hexdigest(),
            "networkx_vs_canonical_sequence_equal": canonical_routes == nx_routes,
            "frame_fingerprints": graph_fingerprint_rows,
            "fidelity_mask_exact": timeline_usable == timeline,
            "all_edges_in_skeleton": True,
        }
        write_json(out_dir / "trace_metrics.json", metrics)
        write_csv(out_dir / "frame_metrics.csv", frame_rows, ["frame", "timeline_up", "s_r_usable", "hop_count", "shortcut", "canonical_route", "networkx_route", "edge_count"])
        write_csv(out_dir / "frame_edges.csv", edge_rows, ["frame", "u", "v"])
        write_json(out_dir / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(out_dir / "operation_status.json", {"status": "failed_exception", "exception": repr(error), "traceback": traceback.format_exc()})
        return 1


def expected_transition_range(life: float) -> tuple[int, int]:
    return {0.3: (50, 52), 0.5: (58, 60), 0.7: (50, 52), 0.9: (22, 23)}[life]


def verify_a2b_l1(life: float) -> tuple[bool, dict]:
    path = A2 / "A2b" / "results" / f"life_{life:.1f}" / "diversity_summary.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    row = next(row for row in rows if row["family"] == "geodesic" and row["selection"] == "greedy5")
    passed = int(row["unique"]) == 5 and float(row["mean_D"]) >= 0.90 * float(row["exact_uniform_mean_D"]) and int(row["largest_duplicate_group"]) <= 20
    return passed, row


def parent_run() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    run_rows = []
    operation_specs = [
        (family, life, seed, p_edge)
        for family in FAMILIES
        for life in LIVES
        for seed in SEEDS[life]
        for p_edge in P_EDGES
    ]
    for family, life, seed, p_edge in operation_specs:
        output = RESULTS / f"{family}__life_{life:.1f}__seed_{seed}__p_{p_edge:.1f}"
        output.mkdir(parents=True, exist_ok=True)
        config = config_for(family, life, seed, p_edge)
        config_path = output / "config.json"
        write_json(config_path, config)
        command = [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)]
        try:
            completed = subprocess.run(command, check=False, timeout=TIMEOUT, cwd=HERE, env=os.environ.copy())
            status = json.loads((output / "operation_status.json").read_text(encoding="utf-8")) if (output / "operation_status.json").exists() else {"status": "failed_missing_status"}
            run_rows.append({"family": family, "life": life, "seed": seed, "p_edge": p_edge, "returncode": completed.returncode, "status": status.get("status"), "output_dir": output.name})
        except subprocess.TimeoutExpired:
            write_json(output / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": TIMEOUT})
            run_rows.append({"family": family, "life": life, "seed": seed, "p_edge": p_edge, "returncode": "TIMEOUT", "status": "failed_timeout", "output_dir": output.name})
    write_csv(RESULTS / "operation_log.csv", run_rows, ["family", "life", "seed", "p_edge", "returncode", "status", "output_dir"])
    summarize()


def summarize() -> None:
    metrics = []
    failures = []
    for operation_dir in sorted(RESULTS.glob("*__life_*__seed_*__p_*")):
        metric_path = operation_dir / "trace_metrics.json"
        status_path = operation_dir / "operation_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"status": "failed_missing_status"}
        if metric_path.exists():
            metrics.append(json.loads(metric_path.read_text(encoding="utf-8")))
        if status.get("status") != "success":
            failures.append({"output_dir": operation_dir.name, **status})
    write_json(RESULTS / "failures.json", failures)
    write_csv(RESULTS / "per_trace_metrics.csv", metrics, [
        "status", "generator", "family", "graph_id", "life", "stability", "p_edge", "seed", "timeline_sha256", "a2b_schedule_identity_match", "timeline_up_count", "timeline_up_runs", "expected_up_runs", "transition_count", "mean_up_run", "max_up_run", "up_pool_group_count", "up_pool_frame_count", "down_pool_frame_count", "measured_usable_fraction", "absolute_fidelity_error", "static_hops", "shortcut_fraction", "time_respecting_reachability", "dilution", "canonical_route_sequence_sha256", "networkx_route_sequence_sha256", "networkx_vs_canonical_sequence_equal", "fidelity_mask_exact", "all_edges_in_skeleton", "up_run_lengths", "run_length_distribution", "hop_counts_by_frame", "frame_fingerprints",
    ])

    cell_rows = []
    run_distribution_rows = []
    for family in FAMILIES:
        for life in LIVES:
            for p_edge in P_EDGES:
                cell = [m for m in metrics if m["family"] == family and m["life"] == life and m["p_edge"] == p_edge]
                row = {"family": family, "life": life, "stability": STABILITY[life], "p_edge": p_edge, "n_success": len(cell), "n_expected": 5}
                for field in ("timeline_up_count", "timeline_up_runs", "transition_count", "mean_up_run", "max_up_run", "up_pool_group_count", "up_pool_frame_count", "down_pool_frame_count", "measured_usable_fraction", "absolute_fidelity_error", "static_hops", "shortcut_fraction", "time_respecting_reachability", "dilution"):
                    values = [float(m[field]) for m in cell]
                    row[f"{field}_mean"] = statistics.mean(values) if values else "NA"
                    row[f"{field}_sd_ddof1"] = statistics.stdev(values) if len(values) > 1 else "NA"
                row["all_exact_timeline_quota"] = len(cell) == 5 and all(m["timeline_up_count"] == round(120 * life) and m["timeline_up_runs"] == m["expected_up_runs"] for m in cell)
                low, high = expected_transition_range(life)
                row["all_transitions_in_A2a_range"] = len(cell) == 5 and all(low <= m["transition_count"] <= high for m in cell)
                row["all_fidelity_masks_exact"] = len(cell) == 5 and all(m["fidelity_mask_exact"] for m in cell)
                row["all_fidelity_error_le_0_05"] = len(cell) == 5 and all(m["absolute_fidelity_error"] <= 0.05 for m in cell)
                row["all_shortcut_fraction_zero"] = len(cell) == 5 and all(m["shortcut_fraction"] == 0 for m in cell)
                row["all_pools_nonempty"] = len(cell) == 5 and all(m["up_pool_frame_count"] > 0 and m["down_pool_frame_count"] > 0 for m in cell)
                row["all_skeleton_edges_only"] = len(cell) == 5 and all(m["all_edges_in_skeleton"] for m in cell)
                cell_rows.append(row)
                for length in range(1, 121):
                    bin_values = [m["run_length_distribution"].get(str(length), 0.0) for m in cell]
                    run_distribution_rows.append({"family": family, "life": life, "p_edge": p_edge, "run_length": length, "mean_fraction": statistics.mean(bin_values) if bin_values else "NA", "sd_fraction_ddof1": statistics.stdev(bin_values) if len(bin_values) > 1 else "NA", "n_seeds": len(bin_values)})
    write_csv(RESULTS / "cell_summary.csv", cell_rows, list(cell_rows[0]) if cell_rows else ["family", "life", "p_edge"])
    write_csv(RESULTS / "run_length_distribution_summary.csv", run_distribution_rows, ["family", "life", "p_edge", "run_length", "mean_fraction", "sd_fraction_ddof1", "n_seeds"])

    identity_rows = []
    for life in LIVES:
        for seed in SEEDS[life]:
            cell = [m for m in metrics if m["life"] == life and m["seed"] == seed]
            hashes = {m["timeline_sha256"] for m in cell}
            expected_operations = len(FAMILIES) * len(P_EDGES)
            identity_rows.append({"life": life, "seed": seed, "successful_operation_count": len(cell), "expected_operation_count": expected_operations, "distinct_timeline_hashes": len(hashes), "matches_a2b_for_all": len(cell) == expected_operations and all(m["a2b_schedule_identity_match"] for m in cell), "family_and_p_edge_independent": len(cell) == expected_operations and len(hashes) == 1, "timeline_sha256": next(iter(hashes)) if len(hashes) == 1 else "MISMATCH"})
    write_csv(RESULTS / "cross_family_schedule_identity.csv", identity_rows, ["life", "seed", "successful_operation_count", "expected_operation_count", "distinct_timeline_hashes", "matches_a2b_for_all", "family_and_p_edge_independent", "timeline_sha256"])

    route_rows = []
    for family in FAMILIES:
        for life in LIVES:
            cell = [m for m in metrics if m["family"] == family and m["life"] == life and m["p_edge"] == 0.5]
            by_seed = {m["seed"]: m["canonical_route_sequence_sha256"] for m in cell}
            networkx_by_seed = {m["seed"]: m["networkx_route_sequence_sha256"] for m in cell}
            distinct_pairs = sum(by_seed[a] != by_seed[b] for i, a in enumerate(SEEDS[life]) for b in SEEDS[life][i + 1:] if a in by_seed and b in by_seed)
            networkx_distinct_pairs = sum(networkx_by_seed[a] != networkx_by_seed[b] for i, a in enumerate(SEEDS[life]) for b in SEEDS[life][i + 1:] if a in networkx_by_seed and b in networkx_by_seed)
            level1_pass, a2brow = verify_a2b_l1(life)
            route_threshold = 9
            route_pass = len(cell) == 5 and distinct_pairs >= route_threshold
            route_rows.append({"generator": GENERATOR, "family": family, "life": life, "p_edge_primary": 0.5, "n_success": len(cell), "canonical_distinct_pairs_of_10": distinct_pairs, "registered_route_threshold": route_threshold, "route_level2_pass": route_pass, "a2b_level1_pass": level1_pass, "overall_diversity_pass": route_pass and level1_pass, "a2b_mean_D": a2brow["mean_D"], "a2b_exact_uniform_mean_D": a2brow["exact_uniform_mean_D"], "networkx_vs_canonical_equal_trace_count": sum(bool(m["networkx_vs_canonical_sequence_equal"]) for m in cell), "networkx_insertion_order_distinct_pairs_of_10": networkx_distinct_pairs})
    write_csv(RESULTS / "route_diversity_summary.csv", route_rows, list(route_rows[0]) if route_rows else ["family", "life"])
    manifest_rows = []
    for artifact in sorted(path for path in RESULTS.rglob("*") if path.is_file() and path.name != "artifact_manifest.csv"):
        manifest_rows.append({"path": artifact.relative_to(RESULTS).as_posix(), "bytes": artifact.stat().st_size, "sha256": sha256(artifact)})
    write_csv(RESULTS / "artifact_manifest.csv", manifest_rows, ["path", "bytes", "sha256"])
    print(json.dumps({"operations": 300, "successful_traces": len(metrics), "failed_operations": len(failures), "schedule_identity_rows": len(identity_rows), "schedule_identity_pass": all(row["matches_a2b_for_all"] and row["family_and_p_edge_independent"] for row in identity_rows), "route_diversity_cells": len(route_rows), "all_route_cells_pass": all(row["overall_diversity_pass"] for row in route_rows)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path)
    parser.add_argument("--summarize", action="store_true", help="Recompute reports from existing trace artifacts without running generators")
    args = parser.parse_args()
    if args.operation:
        raise SystemExit(execute_operation(args.operation))
    if args.summarize:
        summarize()
    else:
        parent_run()


if __name__ == "__main__":
    main()
