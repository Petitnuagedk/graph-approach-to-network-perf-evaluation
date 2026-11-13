#!/usr/bin/env python3
"""Execute the preregistered offline A0-R follow-up checks."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "YaDyGaGa"
RESULTS = HERE / "results"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE))
from icosahedral_geodesic import create_icosahedral_geodesic_graph
from yadygaga.dynaGraph import SPCDynamicGraph
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator


def graph_pair(frequency: int):
    graph = nx.relabel_nodes(
        create_icosahedral_geodesic_graph(frequency, 0),
        lambda node: f"Node_{node}",
    )
    nodes = sorted(graph, key=lambda node: int(node.rpartition("_")[2]))
    best = (-1, None, None)
    for index, source in enumerate(nodes):
        distances = nx.single_source_shortest_path_length(graph, source)
        for destination in nodes[index + 1 :]:
            if distances[destination] > best[0]:
                best = (distances[destination], source, destination)
    return graph, best[1], best[2]


def bit_metrics(bits: str):
    transitions = sum(left != right for left, right in zip(bits, bits[1:]))
    runs = []
    current = 0
    for bit in bits:
        if bit == "1":
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return transitions, statistics.mean(runs) if runs else 0.0, len(runs)


def mean_hamming(strings):
    pairs = list(itertools.combinations(strings, 2))
    if not pairs:
        return 0.0
    length = len(strings[0])
    return statistics.mean(
        sum(left != right for left, right in zip(a, b)) / length
        for a, b in pairs
    )


def frame_pools(graph, source, destination, seed):
    generator = FrameGenerator()
    generator.generateSPCFrames(
        graph,
        source,
        destination,
        trials=500,
        p_edge=0.5,
        pathPersistency=0.9,
        seed=seed + 10000,
    )
    return generator


def assemble_metrics(timeline, path_ids, pools, source, destination, seed):
    graphs = SPCDynamicGraph().buildDynaGraph(
        {"timeline": timeline, "path_ids": path_ids},
        pools.path_up_frames,
        pools.path_down_frames,
        seed=seed + 20000,
    )
    bits = []
    routes = []
    for graph in graphs:
        try:
            route = tuple(nx.shortest_path(graph, source, destination))
            bits.append("1")
            routes.append(route)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            bits.append("0")
            routes.append(None)
    sr_bits = "".join(bits)
    sr_transitions, sr_mean_run, sr_runs = bit_metrics(sr_bits)
    route_switches = sum(
        routes[index] is not None
        and routes[index - 1] is not None
        and routes[index] != routes[index - 1]
        for index in range(1, len(routes))
    )
    return {
        "s_r_bits": sr_bits,
        "s_r_sha256": hashlib.sha256(sr_bits.encode()).hexdigest(),
        "realized_uptime": sr_bits.count("1") / len(sr_bits) if sr_bits else 0.0,
        "sr_transitions": sr_transitions,
        "sr_up_runs": sr_runs,
        "sr_mean_up_run_frames": sr_mean_run,
        "route_switches_within_contiguous_up": route_switches,
        "assembled_frames": len(graphs),
    }


def write_csv(path: Path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize_metric(rows, key):
    values = [float(row[key]) for row in rows]
    return {"mean": statistics.mean(values), "min": min(values), "max": max(values)}


def main():
    RESULTS.mkdir(exist_ok=True)
    graph92, source92, dest92 = graph_pair(3)
    pool_cache = {}

    # Patched trace stability/persistency measurements.
    stability_rows = []
    for seed in range(42, 52):
        if seed not in pool_cache:
            pool_cache[seed] = frame_pools(graph92, source92, dest92, seed)
        pools = pool_cache[seed]
        for stability in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
            for persistency in (0.0, 0.25, 0.5, 0.75, 1.0):
                generated = SPCTimelineBlockGenerator(
                    frames=120,
                    path_life=0.5,
                    stability=stability,
                    seed=seed,
                    mode="blocks",
                    pathPersistency=persistency,
                ).generate_blocks()
                timeline = generated["timeline"]
                ids = generated["path_ids"]
                boolean_bits = "".join("1" if bit else "0" for bit in timeline)
                boolean_transitions, mean_run, up_runs = bit_metrics(boolean_bits)
                adjacent_up_pairs = 0
                retained_ids = 0
                pid_changes = 0
                for index in range(1, len(timeline)):
                    if timeline[index] and timeline[index - 1]:
                        adjacent_up_pairs += 1
                        if ids[index] == ids[index - 1]:
                            retained_ids += 1
                        else:
                            pid_changes += 1
                assembled = assemble_metrics(
                    timeline, ids, pools, source92, dest92, seed
                )
                stability_rows.append({
                    "seed": seed,
                    "N": 92,
                    "frames": 120,
                    "life": 0.5,
                    "stability": stability,
                    "persistency": persistency,
                    "up_count": sum(timeline),
                    "up_runs": up_runs,
                    "scheduled_transitions": boolean_transitions,
                    "scheduled_mean_up_run_frames": mean_run,
                    "path_id_adjacent_up_pairs": adjacent_up_pairs,
                    "path_id_retained_adjacent_up_pairs": retained_ids,
                    "path_id_changes_within_up_runs": pid_changes,
                    "path_id_retention_fraction": retained_ids / adjacent_up_pairs if adjacent_up_pairs else 0.0,
                    "up_pool_frames": sum(map(len, pools.path_up_frames)),
                    "up_pool_groups": len(pools.path_up_frames),
                    "down_pool_frames": len(pools.path_down_frames),
                    **assembled,
                })
    write_csv(RESULTS / "stability_persistency_traces.csv", stability_rows)

    stability_summary = []
    for stability in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        subset = [row for row in stability_rows if row["stability"] == stability]
        stability_summary.append({
            "stability": stability,
            "persistency_values": "0,.25,.5,.75,1",
            "replicates": len(subset),
            "scheduled_transitions": summarize_metric(subset, "scheduled_transitions"),
            "scheduled_mean_up_run_frames": summarize_metric(subset, "scheduled_mean_up_run_frames"),
            "assembled_sr_transitions": summarize_metric(subset, "sr_transitions"),
            "assembled_sr_mean_up_run_frames": summarize_metric(subset, "sr_mean_up_run_frames"),
        })
    persistency_summary = []
    for persistency in (0.0, 0.25, 0.5, 0.75, 1.0):
        subset = [row for row in stability_rows if row["persistency"] == persistency]
        persistency_summary.append({
            "persistency": persistency,
            "replicates": len(subset),
            "scheduled_transitions": summarize_metric(subset, "scheduled_transitions"),
            "scheduled_mean_up_run_frames": summarize_metric(subset, "scheduled_mean_up_run_frames"),
            "path_id_retention_fraction": summarize_metric(subset, "path_id_retention_fraction"),
            "path_id_changes_within_up_runs": summarize_metric(subset, "path_id_changes_within_up_runs"),
            "assembled_sr_transitions": summarize_metric(subset, "sr_transitions"),
            "assembled_sr_mean_up_run_frames": summarize_metric(subset, "sr_mean_up_run_frames"),
            "route_switches_within_up": summarize_metric(subset, "route_switches_within_contiguous_up"),
        })

    # 50-seed diversity check at five lives.
    diversity_rows = []
    for seed in range(42, 92):
        pools = pool_cache.get(seed)
        if pools is None:
            pools = frame_pools(graph92, source92, dest92, seed)
            pool_cache[seed] = pools
        for life in (0.1, 0.3, 0.5, 0.7, 0.9):
            generated = SPCTimelineBlockGenerator(
                frames=120,
                path_life=life,
                stability=1.0,
                seed=seed,
                mode="blocks",
                pathPersistency=0.9,
            ).generate_blocks()
            assembled = assemble_metrics(
                generated["timeline"], generated["path_ids"], pools,
                source92, dest92, seed,
            )
            diversity_rows.append({
                "seed": seed,
                "N": 92,
                "frames": 120,
                "life": life,
                "stability": 1.0,
                "persistency": 0.9,
                "up_pool_frames": sum(map(len, pools.path_up_frames)),
                "up_pool_groups": len(pools.path_up_frames),
                "down_pool_frames": len(pools.path_down_frames),
                **assembled,
            })
    write_csv(RESULTS / "life_diversity_50seeds.csv", diversity_rows)
    diversity_summary = []
    for life in (0.1, 0.3, 0.5, 0.7, 0.9):
        subset = [row for row in diversity_rows if row["life"] == life]
        strings = [row["s_r_bits"] for row in subset]
        diversity_summary.append({
            "life": life,
            "stability": 1.0,
            "persistency": 0.9,
            "seeds": "42-91",
            "n": len(strings),
            "unique_s_r_timelines": len(set(strings)),
            "mean_pairwise_hamming_fraction": mean_hamming(strings),
            "realized_uptime_mean": statistics.mean(row["realized_uptime"] for row in subset),
            "realized_uptime_min": min(row["realized_uptime"] for row in subset),
            "realized_uptime_max": max(row["realized_uptime"] for row in subset),
        })

    # N=162 pool counts, using same candidate-generation settings and 50 seeds.
    graph162, source162, dest162 = graph_pair(4)
    pool_rows = []
    for seed in range(42, 92):
        started = time.perf_counter()
        pools = frame_pools(graph162, source162, dest162, seed)
        pool_rows.append({
            "seed": seed,
            "N": graph162.number_of_nodes(),
            "frames": 120,
            "candidate_trials": 500,
            "p_edge": 0.5,
            "frame_seed": seed + 10000,
            "source": source162,
            "destination": dest162,
            "up_pool_frames": sum(map(len, pools.path_up_frames)),
            "up_pool_groups": len(pools.path_up_frames),
            "down_pool_frames": len(pools.path_down_frames),
            "pool_empty": not pools.path_up_frames or not pools.path_down_frames,
            "pool_tiny_lt5": sum(map(len, pools.path_up_frames)) < 5 or len(pools.path_down_frames) < 5,
            "elapsed_seconds": time.perf_counter() - started,
        })
    write_csv(RESULTS / "n162_pool_sizes_50seeds.csv", pool_rows)

    result = {
        "protocol_variants": 0,
        "stability_summary": stability_summary,
        "persistency_summary": persistency_summary,
        "life_diversity_summary": diversity_summary,
        "n162_pools": {
            "seed_count": len(pool_rows),
            "empty_pool_rows": sum(row["pool_empty"] for row in pool_rows),
            "tiny_pool_rows": sum(row["pool_tiny_lt5"] for row in pool_rows),
            "up_pool_frames": summarize_metric(pool_rows, "up_pool_frames"),
            "up_pool_groups": summarize_metric(pool_rows, "up_pool_groups"),
            "down_pool_frames": summarize_metric(pool_rows, "down_pool_frames"),
            "elapsed_seconds": summarize_metric(pool_rows, "elapsed_seconds"),
        },
        "settings": {
            "N92_pair": [source92, dest92],
            "N162_pair": [source162, dest162],
            "candidate_trials": 500,
            "p_edge": 0.5,
            "timeline_seed_offset": 0,
            "frame_seed_offset": 10000,
            "assembly_seed_offset": 20000,
            "stability_grid_seeds": "42-51",
            "diversity_seeds": "42-91",
            "n162_pool_seeds": "42-91",
        },
    }
    (RESULTS / "offline_followup_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
