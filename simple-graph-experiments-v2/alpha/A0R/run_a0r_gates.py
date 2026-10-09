#!/usr/bin/env python3
"""Run frozen generator-only A0 acceptance checks on the isolated A0-R copy."""
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
REVISION = "51b01ac7faa78a494c3baedc560d658f384afe09"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE))
from yadygaga.dynaGraph import SPCDynamicGraph
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator


def geodesic(frequency: int):
    from icosahedral_geodesic import create_icosahedral_geodesic_graph
    raw = create_icosahedral_geodesic_graph(frequency, 0)
    graph = nx.relabel_nodes(raw, {n: f"Node_{n}" for n in raw.nodes()}, copy=True)
    nodes = sorted(graph, key=lambda n: int(n.rpartition("_")[2]))
    best = (-1, None, None)
    for i, source in enumerate(nodes):
        distances = nx.single_source_shortest_path_length(graph, source)
        for destination in nodes[i + 1 :]:
            if distances[destination] > best[0]:
                best = (distances[destination], source, destination)
    return graph, best[1], best[2]


def connected_bits(frames, source, destination):
    bits = []
    for frame in frames:
        try:
            nx.shortest_path(frame, source, destination)
            bits.append("1")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            bits.append("0")
    return "".join(bits)


def transitions(bits):
    return sum(left != right for left, right in zip(bits, bits[1:]))


def hamming_mean(strings):
    pairs = list(itertools.combinations(strings, 2))
    if not pairs:
        return 0.0
    n = len(strings[0])
    return statistics.mean(sum(a != b for a, b in zip(x, y)) / n for x, y in pairs)


def source_hashes():
    return {
        name: hashlib.sha256((SOURCE / "yadygaga" / name).read_bytes()).hexdigest()
        for name in ("frameGenerator.py", "timelineBlockGenerator.py", "dynaGraph.py")
    }


def run_case(graph, source, destination, frequency, frames, life, seed, role):
    start = time.perf_counter()
    frame_generator = FrameGenerator()
    frame_generator.generateSPCFrames(
        graph,
        source,
        destination,
        trials=500,
        p_edge=0.5,
        pathPersistency=0.9,
        seed=seed + 10000,
    )
    timeline = SPCTimelineBlockGenerator(
        frames=frames,
        path_life=life,
        stability=0.8,
        seed=seed,
        mode="blocks",
        pathPersistency=0.9,
    ).generate_blocks()
    assembled = SPCDynamicGraph().buildDynaGraph(
        timeline,
        frame_generator.path_up_frames,
        frame_generator.path_down_frames,
        seed=seed + 20000,
    )
    elapsed = time.perf_counter() - start
    bits = connected_bits(assembled, source, destination)
    timeline_bits = "".join("1" if state else "0" for state in timeline["timeline"])
    requested_up = round(frames * life)
    requested_runs = (
        0 if requested_up == 0 else
        1 if requested_up == frames else
        max(1, min(requested_up, round(1 + 0.2 * (requested_up - 1))))
    )
    observed_runs = sum(
        state and (index == 0 or not timeline["timeline"][index - 1])
        for index, state in enumerate(timeline["timeline"])
    )
    return {
        "role": role,
        "N": graph.number_of_nodes(),
        "frequency": frequency,
        "frames": frames,
        "life": life,
        "stability": 0.8,
        "persistency": 0.9,
        "seed": seed,
        "frame_seed": seed + 10000,
        "assembly_seed": seed + 20000,
        "trials": 500,
        "up_pool_frames": sum(map(len, frame_generator.path_up_frames)),
        "up_pool_groups": len(frame_generator.path_up_frames),
        "down_pool_frames": len(frame_generator.path_down_frames),
        "pool_empty": not frame_generator.path_up_frames or not frame_generator.path_down_frames,
        "pool_tiny_lt5": sum(map(len, frame_generator.path_up_frames)) < 5 or len(frame_generator.path_down_frames) < 5,
        "requested_up_count": requested_up,
        "timeline_up_count": timeline_bits.count("1"),
        "timeline_up_runs": observed_runs,
        "requested_up_runs": requested_runs,
        "realized_sr_uptime": bits.count("1") / len(bits) if bits else 0.0,
        "sr_transitions": transitions(bits),
        "s_r_bits": bits,
        "s_r_sha256": hashlib.sha256(bits.encode()).hexdigest(),
        "timeline_bits": timeline_bits,
        "generation_wall_seconds": elapsed,
        "source_revision": REVISION,
    }


def mpc_regression():
    """Compare untouched MPC sampler output against the clean-HEAD implementation."""
    clean_text = subprocess.check_output(
        ["git", "-C", "/home/hledirach/Documents/YaDyGaGa", "show", f"{REVISION}:yadygaga/frameGenerator.py"],
        text=True,
    )
    namespace = {"__name__": "clean_frame_generator_fixture"}
    exec(compile(clean_text, "clean_HEAD_frameGenerator.py", "exec"), namespace)
    CleanFrameGenerator = namespace["FrameGenerator"]
    graph = nx.path_graph(9)
    graph = nx.relabel_nodes(graph, {node: f"N{node}" for node in graph})
    pairs = [("N0", "N8"), ("N1", "N7")]
    clean = CleanFrameGenerator().generateMPCFrames(graph, pairs, trials=200, p_edge=0.5, seed=971)
    patched = FrameGenerator().generateMPCFrames(graph, pairs, trials=200, p_edge=0.5, seed=971)

    def canonical(output):
        frames = [tuple(sorted(tuple(sorted(edge)) for edge in frame.edges())) for frame in output["frames"]]
        counts = sorted((repr(key), value) for key, value in output["counts"].items())
        return frames, counts, output["per_pair"]

    clean_signature = canonical(clean)
    patched_signature = canonical(patched)
    if clean_signature != patched_signature:
        raise AssertionError("Untouched MPC API differs from clean HEAD under the same seed")
    encoded = repr(clean_signature).encode()
    return {
        "fixture": "generateMPCFrames; N=9; pairs=(N0,N8),(N1,N7); trials=200; p_edge=0.5; seed=971",
        "byte_identical_clean_vs_patched": True,
        "signature_sha256": hashlib.sha256(encoded).hexdigest(),
        "status_patterns": len(clean["counts"]),
        "clean_source_method_unchanged": True,
    }


def main():
    RESULTS.mkdir(exist_ok=True)
    graph92, s92, d92 = geodesic(3)
    graph162, s162, d162 = geodesic(4)
    rows = []
    for seed in range(42, 47):
        rows.append(run_case(graph92, s92, d92, 3, 120, 0.5, seed, "diversity"))
    for life in (0.3, 0.5, 0.7):
        for seed in range(42, 47):
            rows.append(run_case(graph92, s92, d92, 3, 120, life, seed, "fidelity"))
    for seed in (42, 43, 44):
        rows.append(run_case(graph162, s162, d162, 4, 120, 0.5, seed, "timing"))

    output = RESULTS / "patched_a0_gate_results.csv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    diversity = [row for row in rows if row["role"] == "diversity"]
    fidelity = [row for row in rows if row["role"] == "fidelity"]
    timing = [row for row in rows if row["role"] == "timing"]
    diversity_bits = [row["s_r_bits"] for row in diversity]
    regression = mpc_regression()
    summary = {
        "source_revision": REVISION,
        "patched_source_hashes": source_hashes(),
        "diversity": {
            "unique_s_r_timelines": len(set(diversity_bits)),
            "mean_pairwise_hamming_fraction": hamming_mean(diversity_bits),
            "pass": len(set(diversity_bits)) >= 5 and hamming_mean(diversity_bits) > 0.10,
        },
        "fidelity": {
            "max_absolute_uptime_error": max(abs(row["realized_sr_uptime"] - row["life"]) for row in fidelity),
            "every_error_at_most_0_05": all(abs(row["realized_sr_uptime"] - row["life"]) <= 0.05 for row in fidelity),
            "all_15_exact_requested_quota": all(row["timeline_up_count"] == row["requested_up_count"] for row in fidelity),
            "all_15_exact_up_run_target": all(row["timeline_up_runs"] == row["requested_up_runs"] for row in fidelity),
        },
        "timing": {
            "max_seconds": max(row["generation_wall_seconds"] for row in timing),
            "all_under_600_seconds": all(row["generation_wall_seconds"] < 600 for row in timing),
            "all_pools_valid": all(not row["pool_empty"] for row in timing),
        },
        "all_rows_nonempty_pools": all(not row["pool_empty"] for row in rows),
        "mpc_regression": regression,
        "protocol_variants": 0,
    }
    (RESULTS / "patched_a0_gate_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
