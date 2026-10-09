#!/usr/bin/env python3
"""Preregistered A0-R diagnostics against the isolated clean YaDyGaGa copy."""
from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import math
import random
import statistics
import subprocess
import sys
import tarfile
import time
from types import SimpleNamespace
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = Path("/tmp/yadygaga-alpha-a0r-clean")
SOURCE_REPO = Path("/home/hledirach/Documents/YaDyGaGa")
SOURCE_REVISION = "51b01ac7faa78a494c3baedc560d658f384afe09"
if not (SRC / "yadygaga" / "frameGenerator.py").is_file():
    archive = subprocess.check_output(
        ["git", "-C", str(SOURCE_REPO), "archive", SOURCE_REVISION]
    )
    SRC.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source_tar:
        source_tar.extractall(SRC, filter="data")
RESULTS = HERE / "results"
A0_RESULTS = ROOT / "simple-graph-experiments-v2/alpha/A0/results"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))
from yadygaga import frameGenerator as frame_module
from yadygaga import timelineBlockGenerator as timeline_module
from yadygaga import dynaGraph as dyna_module


def geodesic(frequency: int):
    from icosahedral_geodesic import create_icosahedral_geodesic_graph
    raw = create_icosahedral_geodesic_graph(frequency, 0)
    graph = nx.relabel_nodes(raw, {n: f"Node_{n}" for n in raw.nodes()}, copy=True)
    labels = sorted(graph, key=lambda x: int(x.rpartition("_")[2]))
    best = (-1, None, None)
    for i, source in enumerate(labels):
        dist = nx.single_source_shortest_path_length(graph, source)
        for destination in labels[i + 1:]:
            if dist[destination] > best[0]:
                best = (dist[destination], source, destination)
    return graph, best[1], best[2]


def timeline_bits(timeline):
    return "".join("1" if b else "0" for b in timeline["timeline"])


def hamming_mean(bitstrings):
    if len(bitstrings) < 2:
        return 0.0
    n = len(bitstrings[0])
    return statistics.mean(
        sum(x != y for x, y in zip(bitstrings[i], bitstrings[j])) / n
        for i, j in itertools.combinations(range(len(bitstrings)), 2)
    )


def call_frame_sampler(graph, s, d, seed, trials):
    # Isolate the legacy module's `random.random()` calls without editing source
    # or mutating Python's process-global RNG stream.
    original = frame_module.random
    frame_module.random = random.Random(seed)
    try:
        fg = frame_module.FrameGenerator()
        fg.generateSPCFrames(graph, s, d, trials=trials, p_edge=0.5, pathPersistency=0.9)
        return fg
    finally:
        frame_module.random = original


def connected_bits(frames, source, destination):
    bits = []
    for graph in frames:
        try:
            nx.shortest_path(graph, source, destination)
            bits.append("1")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            bits.append("0")
    return "".join(bits)


def transition_count(bits):
    return sum(a != b for a, b in zip(bits, bits[1:]))


def write_csv(name, rows, fields=None):
    path = RESULTS / name
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def random_composition(total, parts, rng):
    if parts == 1:
        return [total]
    cuts = sorted(rng.sample(range(1, total), parts - 1))
    points = [0, *cuts, total]
    return [points[i + 1] - points[i] for i in range(parts)]


def valid_timeline_witness(up, down, runs, seed):
    """Find five exact-quota, exact-run witnesses, without enumerating all strings."""
    if up == 0:
        return ["0" * down] * 5
    if down == 0:
        return ["1" * up] * 5
    rng = random.Random(seed)
    down_run_options = [q for q in (runs - 1, runs, runs + 1) if 1 <= q <= down]
    candidates = set()
    for _ in range(20000):
        down_runs = rng.choice(down_run_options)
        ups = random_composition(up, runs, rng)
        downs = random_composition(down, down_runs, rng)
        start_up = down_runs == runs - 1 or (down_runs == runs and rng.choice((True, False)))
        sequence = []
        ui = di = 0
        state_up = start_up
        while ui < runs or di < down_runs:
            if state_up and ui < runs:
                sequence.extend("1" * ups[ui])
                ui += 1
            elif not state_up and di < down_runs:
                sequence.extend("0" * downs[di])
                di += 1
            state_up = not state_up
        bits = "".join(sequence)
        observed_up_runs = (
            transition_count(bits)
            + int(bits.startswith("1"))
            + int(bits.endswith("1"))
        ) // 2
        if len(bits) == up + down and bits.count("1") == up and observed_up_runs == runs:
            candidates.add(bits)
        if len(candidates) >= 5 and len(candidates) % 5 == 0:
            selection = rng.sample(tuple(candidates), 5)
            mean_h = hamming_mean(selection)
            if mean_h > 0.10:
                return list(selection), mean_h
    return list(sorted(candidates)[:5]), hamming_mean(sorted(candidates)[:5]) if len(candidates) >= 2 else 0.0


def source_identity():
    paths = [SRC / "yadygaga" / name for name in ("frameGenerator.py", "timelineBlockGenerator.py", "dynaGraph.py")]
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    graph92, s92, d92 = geodesic(3)
    direct_rows = []
    direct_bits = []
    direct_ids = []
    for seed in range(42, 47):
        gen = timeline_module.SPCTimelineBlockGenerator(
            frames=120, path_life=0.5, stability=0.8, seed=seed,
            mode="blocks", pathPersistency=0.9,
        )
        result = gen.generate_blocks()
        bits = timeline_bits(result)
        ids = result["path_ids"]
        direct_bits.append(bits)
        direct_ids.append(ids)
        direct_rows.append({
            "seed": seed,
            "N": 92,
            "frames": 120,
            "life": 0.5,
            "stability": 0.8,
            "persistency": 0.9,
            "boolean_bits": bits,
            "boolean_sha256": hashlib.sha256(bits.encode()).hexdigest(),
            "path_ids": json.dumps(ids, separators=(",", ":")),
            "distinct_path_ids": len({x for x in ids if x is not None}),
            "boolean_transitions": transition_count(bits),
            "uptime": bits.count("1") / len(bits),
        })
    write_csv("direct_timeline_seeds.csv", direct_rows)

    horizon_rows = []
    horizon_diversity = []
    for trials in (500, 2000, 10000):
        rows_by_seed = []
        for seed in range(42, 47):
            start = time.perf_counter()
            fg = call_frame_sampler(graph92, s92, d92, seed, trials)
            tg = timeline_module.SPCTimelineBlockGenerator(
                frames=120, path_life=0.5, stability=0.8, seed=seed,
                mode="blocks", pathPersistency=0.9,
            ).generate_blocks()
            dg = dyna_module.SPCDynamicGraph()
            original_random = dyna_module.random
            dyna_module.random = SimpleNamespace(Random=lambda: random.Random(seed + trials * 1000))
            try:
                dg.buildDynaGraph(tg, fg.path_up_frames, fg.path_down_frames)
            finally:
                dyna_module.random = original_random
            elapsed = time.perf_counter() - start
            bits = connected_bits(dg.DynamicGraph, s92, d92)
            row = {
                "trials": trials,
                "seed": seed,
                "N": 92,
                "frames": 120,
                "path_life": 0.5,
                "stability": 0.8,
                "persistency": 0.9,
                "up_pool_frames": sum(map(len, fg.path_up_frames)),
                "up_pool_groups": len(fg.path_up_frames),
                "down_pool_frames": len(fg.path_down_frames),
                "s_r_bits": bits,
                "realized_uptime": bits.count("1") / len(bits),
                "transitions": transition_count(bits),
                "wall_seconds": elapsed,
                "pool_empty": not fg.path_up_frames or not fg.path_down_frames,
                "pool_tiny_lt5": sum(map(len, fg.path_up_frames)) < 5 or len(fg.path_down_frames) < 5,
            }
            horizon_rows.append(row)
            rows_by_seed.append(row)
        strings = [row["s_r_bits"] for row in rows_by_seed]
        horizon_diversity.append({
            "trials": trials,
            "unique_s_r_timelines": len(set(strings)),
            "mean_pairwise_hamming_fraction": hamming_mean(strings),
            "wall_mean_seconds": statistics.mean(r["wall_seconds"] for r in rows_by_seed),
            "wall_max_seconds": max(r["wall_seconds"] for r in rows_by_seed),
            "up_pool_frames_min": min(r["up_pool_frames"] for r in rows_by_seed),
            "up_pool_frames_max": max(r["up_pool_frames"] for r in rows_by_seed),
            "up_pool_groups_min": min(r["up_pool_groups"] for r in rows_by_seed),
            "up_pool_groups_max": max(r["up_pool_groups"] for r in rows_by_seed),
            "down_pool_frames_min": min(r["down_pool_frames"] for r in rows_by_seed),
            "down_pool_frames_max": max(r["down_pool_frames"] for r in rows_by_seed),
        })
    write_csv("horizon_trials.csv", horizon_rows)
    (RESULTS / "horizon_summary.json").write_text(json.dumps(horizon_diversity, indent=2) + "\n")

    coupling_rows = []
    graph_pools = {}
    for seed in range(42, 47):
        fg = call_frame_sampler(graph92, s92, d92, seed, 2000)
        graph_pools[seed] = fg
        for stability in (0.0, 0.4, 0.8):
            for persistency in (0.0, 0.5, 1.0):
                timeline = timeline_module.SPCTimelineBlockGenerator(
                    frames=120, path_life=0.5, stability=stability, seed=seed,
                    mode="blocks", pathPersistency=persistency,
                ).generate_blocks()
                dg = dyna_module.SPCDynamicGraph()
                original_random = dyna_module.random
                dyna_module.random = SimpleNamespace(Random=lambda: random.Random(seed + int(stability * 10) * 100 + int(persistency * 10)))
                try:
                    dg.buildDynaGraph(timeline, fg.path_up_frames, fg.path_down_frames)
                finally:
                    dyna_module.random = original_random
                bits = connected_bits(dg.DynamicGraph, s92, d92)
                timeline_bools = timeline_bits(timeline)
                ids = timeline["path_ids"]
                coupling_rows.append({
                    "seed": seed,
                    "stability": stability,
                    "persistency": persistency,
                    "boolean_bits": timeline_bools,
                    "s_r_bits": bits,
                    "requested_uptime": timeline_bools.count("1") / len(timeline_bools),
                    "realized_uptime": bits.count("1") / len(bits),
                    "s_r_transitions": transition_count(bits),
                    "boolean_transitions": transition_count(timeline_bools),
                    "path_id_changes_within_up": sum(
                        ids[i] != ids[i - 1] for i in range(1, len(ids))
                        if ids[i] is not None and ids[i - 1] is not None
                    ),
                    "up_pool_frames": sum(map(len, fg.path_up_frames)),
                    "up_pool_groups": len(fg.path_up_frames),
                    "down_pool_frames": len(fg.path_down_frames),
                })
    write_csv("parameter_coupling.csv", coupling_rows)

    pool_rows = []
    for frequency in (3, 4):
        graph, source, destination = geodesic(frequency)
        n = graph.number_of_nodes()
        for trials in (500, 2000, 10000):
            for seed in range(42, 47):
                start = time.perf_counter()
                fg = call_frame_sampler(graph, source, destination, seed, trials)
                elapsed = time.perf_counter() - start
                up_frames = sum(map(len, fg.path_up_frames))
                down_frames = len(fg.path_down_frames)
                pool_rows.append({
                    "N": n,
                    "frequency": frequency,
                    "trials": trials,
                    "seed": seed,
                    "p_edge": 0.5,
                    "source": source,
                    "destination": destination,
                    "up_pool_frames": up_frames,
                    "up_pool_groups": len(fg.path_up_frames),
                    "down_pool_frames": down_frames,
                    "wall_seconds": elapsed,
                    "pool_empty": up_frames == 0 or down_frames == 0,
                    "pool_tiny_lt5": up_frames < 5 or down_frames < 5,
                })
    write_csv("pool_validity.csv", pool_rows)

    # Analytic timeline-space counts over the preregistered grid.
    feasibility_rows = []
    for frames in (60, 120):
        for life in (0.3, 0.5, 0.7):
            up = max(0, min(frames, round(frames * life)))
            down = frames - up
            for stability in (0.0, 0.4, 0.8):
                if up == 0 or down == 0:
                    runs = 0 if up == 0 else up
                    count = 1
                else:
                    runs = round(1 + (1 - stability) * (up - 1))
                    runs = max(1, min(up, runs))
                    count = (
                        math.comb(up - 1, runs - 1) * math.comb(down + 1, runs)
                        if runs <= down + 1
                        else 0
                    )
                # Certified upper bound from balanced per-time column occupancy across 5 strings.
                total_ones = 5 * up
                q, r = divmod(total_ones, frames)
                max_pairwise_sum = r * (q + 1) * (5 - q - 1) + (frames - r) * q * (5 - q)
                max_hamming_upper = max_pairwise_sum / (10 * frames)
                if count >= 5:
                    witness, witness_hamming = valid_timeline_witness(
                        up, down, runs, seed=frames * 10000 + up * 100 + runs
                    )
                else:
                    witness, witness_hamming = [], 0.0
                feasibility_rows.append({
                    "frames": frames,
                    "life": life,
                    "stability": stability,
                    "up_count_round": up,
                    "down_count": down,
                    "target_up_runs_clean_head": runs,
                    "distinct_valid_timelines_analytic": str(count),
                    "log10_distinct_count": math.log10(count) if count else float("-inf"),
                    "mean_hamming_certified_upper_bound": max_hamming_upper,
                    "hamming_value_kind": "certified upper bound from quota only; exact maximum not enumerated",
                    "five_valid_timeline_witnesses": json.dumps(witness, separators=(",", ":")),
                    "five_witness_mean_pairwise_hamming": witness_hamming,
                    "witness_exceeds_0_10": witness_hamming > 0.10,
                    "at_least_five_solutions": count >= 5,
                    "hamming_upper_bound_exceeds_0_10": max_hamming_upper > 0.10,
                    "stop_infeasible_by_preregistered_rule": count < 5 or max_hamming_upper <= 0.10,
                    "count_method": "stars-and-bars analytic count; valid strings have exact rounded up quota and exact up-run target",
                    "source_has_down_count_plus_one_cap": False,
                })
    write_csv("feasibility.csv", feasibility_rows)

    # Machine-readable audit of source and diagnostic provenance.
    provenance = {
        "source_revision": "51b01ac7faa78a494c3baedc560d658f384afe09",
        "source_hashes": source_identity(),
        "generator_copy": str(SRC),
        "graph_pair_N92": [s92, d92],
        "python": sys.version.split()[0],
        "protocol_variants": 0,
        "diagnostics_completed": ["direct timeline seed path", "horizon trials", "parameter coupling", "pool validity", "analytic feasibility count"],
    }
    (RESULTS / "diagnostic_manifest.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
