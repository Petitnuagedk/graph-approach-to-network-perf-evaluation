#!/usr/bin/env python3
"""Run preregistered Alpha A0 generator-only checks against clean YaDyGaGa HEAD.

The existing generator sources are not modified. Supply --clean-source pointing
at an isolated checkout/archive of the preregistered commit. Each trace runs in
its own child process so peak RSS is a per-trace process high-water mark.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import networkx as nx

ROOT = Path(__file__).resolve().parents[3]
A0_DIR = Path(__file__).resolve().parent
RESULTS_DIR = A0_DIR / "results"
SOURCE_REVISION = "51b01ac7faa78a494c3baedc560d658f384afe09"
DEFAULT_TRIALS = 500
DEFAULT_P_EDGE = 0.5
DEFAULT_STABILITY = 0.8
DEFAULT_PERSISTENCY = 0.9


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build_geodesic(frequency: int) -> tuple[nx.Graph, str, str, int]:
    """Build one Class-I graph, relabel nodes like the J2 pipeline, choose diameter pair."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from icosahedral_geodesic import create_icosahedral_geodesic_graph

    raw = create_icosahedral_geodesic_graph(frequency, 0)
    relabel = {node: f"Node_{node}" for node in raw.nodes()}
    graph = nx.relabel_nodes(raw, relabel, copy=True)
    ordered = sorted(graph.nodes(), key=lambda label: int(label.rpartition("_")[2]))
    best_distance = -1
    best_pair: tuple[str, str] | None = None
    for i, source in enumerate(ordered):
        distances = nx.single_source_shortest_path_length(graph, source)
        for destination in ordered[i + 1 :]:
            distance = distances[destination]
            if distance > best_distance:
                best_distance = distance
                best_pair = (source, destination)
    if best_pair is None:
        raise RuntimeError("Could not select a deterministic S-R pair")
    return graph, best_pair[0], best_pair[1], best_distance


def worker(args: argparse.Namespace) -> dict[str, Any]:
    """Generate and assemble one trace; write its complete serialized output."""
    clean_source = Path(args.clean_source).resolve()
    if not (clean_source / "yadygaga" / "frameGenerator.py").is_file():
        raise FileNotFoundError(f"No YaDyGaGa source package under {clean_source}")
    sys.path.insert(0, str(clean_source))

    from yadygaga.dynaGraph import SPCDynamicGraph
    from yadygaga.frameGenerator import FrameGenerator
    from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

    frequency = args.frequency
    graph, source, destination, baseline_hops = build_geodesic(frequency)
    if graph.number_of_nodes() != 10 * frequency * frequency + 2:
        raise AssertionError("Geodesic size formula did not match the preregistration")

    start = time.perf_counter()
    random.seed(args.seed)
    frame_generator = FrameGenerator()
    frame_generator.generateSPCFrames(
        graph,
        source,
        destination,
        trials=DEFAULT_TRIALS,
        p_edge=DEFAULT_P_EDGE,
        pathPersistency=DEFAULT_PERSISTENCY,
    )
    timeline_generator = SPCTimelineBlockGenerator(
        frames=args.frames,
        path_life=args.path_life,
        stability=DEFAULT_STABILITY,
        seed=args.seed,
        mode="blocks",
        pathPersistency=DEFAULT_PERSISTENCY,
    )
    timeline = timeline_generator.generate_blocks()
    dynamic_graph = SPCDynamicGraph()
    dynamic_graph.buildDynaGraph(
        timeline,
        frame_generator.path_up_frames,
        frame_generator.path_down_frames,
    )
    generation_seconds = time.perf_counter() - start
    peak_rss_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    bits: list[bool] = []
    hops: list[int | None] = []
    for frame in dynamic_graph.DynamicGraph:
        try:
            route = nx.shortest_path(frame, source, destination)
            bits.append(True)
            hops.append(len(route) - 1)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            bits.append(False)
            hops.append(None)

    requested_count = sum(bool(value) for value in timeline["timeline"])
    realized_count = sum(bits)
    transitions = sum(left != right for left, right in zip(bits, bits[1:]))
    up_runs: list[int] = []
    current_run = 0
    for bit in bits:
        if bit:
            current_run += 1
        elif current_run:
            up_runs.append(current_run)
            current_run = 0
    if current_run:
        up_runs.append(current_run)
    shortcut_count = sum(hop is not None and hop < baseline_hops for hop in hops)

    graph_edges = []
    for frame in dynamic_graph.DynamicGraph:
        graph_edges.append(
            sorted([sorted((str(u), str(v))) for u, v in frame.edges()])
        )
    trace = {
        "source_revision": SOURCE_REVISION,
        "frequency": frequency,
        "nodes": sorted(graph.nodes(), key=lambda label: int(label.rpartition("_")[2])),
        "source": source,
        "destination": destination,
        "baseline_hops": baseline_hops,
        "frames": graph_edges,
        "sr_connectivity_bits": "".join("1" if bit else "0" for bit in bits),
    }
    trace_bytes = json.dumps(trace, sort_keys=True, separators=(",", ":")).encode()
    trace_name = (
        f"N{graph.number_of_nodes()}_F{args.frames}_life{args.path_life:.1f}"
        f"_seed{args.seed}.trace.json"
    )
    trace_path = RESULTS_DIR / trace_name
    trace_path.write_bytes(trace_bytes)

    source_files = {
        "frameGenerator.py": clean_source / "yadygaga" / "frameGenerator.py",
        "timelineBlockGenerator.py": clean_source / "yadygaga" / "timelineBlockGenerator.py",
        "dynaGraph.py": clean_source / "yadygaga" / "dynaGraph.py",
    }
    return {
        "trace_file": trace_name,
        "trace_sha256": sha256_bytes(trace_bytes),
        "trace_bytes": len(trace_bytes),
        "source_revision": SOURCE_REVISION,
        "source_hashes": {name: sha256_file(path) for name, path in source_files.items()},
        "wrapper_sha256": sha256_file(Path(__file__).resolve()),
        "N": graph.number_of_nodes(),
        "frequency": frequency,
        "frames": args.frames,
        "source": source,
        "destination": destination,
        "baseline_hops": baseline_hops,
        "seed": args.seed,
        "trials": DEFAULT_TRIALS,
        "p_edge": DEFAULT_P_EDGE,
        "stability": DEFAULT_STABILITY,
        "pathPersistency": DEFAULT_PERSISTENCY,
        "path_life_requested": args.path_life,
        "timeline_up_count_requested": requested_count,
        "timeline_up_ratio": requested_count / args.frames if args.frames else 0.0,
        "realized_up_count": realized_count,
        "realized_uptime": realized_count / len(bits) if bits else 0.0,
        "connectivity_bits": trace["sr_connectivity_bits"],
        "path_up_pool_groups": len(frame_generator.path_up_frames),
        "path_up_pool_frames": sum(map(len, frame_generator.path_up_frames)),
        "path_down_pool_frames": len(frame_generator.path_down_frames),
        "transitions": transitions,
        "up_runs": up_runs,
        "mean_up_run_frames": statistics.mean(up_runs) if up_runs else None,
        "mean_hops_when_up": statistics.mean(hop for hop in hops if hop is not None)
        if any(hop is not None for hop in hops)
        else None,
        "shorter_than_skeleton_path_frames": shortcut_count,
        "generation_wall_seconds": generation_seconds,
        "process_peak_rss_kib": peak_rss_kib,
        "process_peak_rss_bytes": peak_rss_kib * 1024,
    }


def run_parent(args: argparse.Namespace) -> None:
    clean_source = Path(args.clean_source).resolve()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    cases: dict[tuple[int, int, float, int], dict[str, Any]] = {}
    for frequency in (2, 3, 4):
        n = 10 * frequency * frequency + 2
        for frames in (60, 120):
            for seed in (42, 43, 44):
                key = (frequency, frames, 0.5, seed)
                cases[key] = {"roles": ["scale_timing"], "frequency": frequency}
    for seed in range(42, 47):
        for life in (0.3, 0.5, 0.7):
            key = (3, 120, life, seed)
            case = cases.setdefault(key, {"roles": [], "frequency": 3})
            if "life_fidelity" not in case["roles"]:
                case["roles"].append("life_fidelity")
            if life == 0.5 and "seed_diversity" not in case["roles"]:
                case["roles"].append("seed_diversity")

    worker_script = Path(__file__).resolve()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(clean_source)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    summaries: list[dict[str, Any]] = []
    ordered_cases = sorted(cases.items())
    for index, ((frequency, frames, life, seed), metadata) in enumerate(ordered_cases, 1):
        n = 10 * frequency * frequency + 2
        print(
            f"[{index}/{len(ordered_cases)}] N={n} frames={frames} life={life:.1f} seed={seed}",
            flush=True,
        )
        command = [
            sys.executable,
            str(worker_script),
            "--worker",
            "--clean-source",
            str(clean_source),
            "--frequency",
            str(frequency),
            "--frames",
            str(frames),
            "--path-life",
            str(life),
            "--seed",
            str(seed),
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        record = json.loads(completed.stdout)
        record["roles"] = metadata["roles"]
        record["run_index"] = index
        record_path = RESULTS_DIR / record["trace_file"].replace(".trace.json", ".record.json")
        record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        summaries.append(record)

    write_tables(summaries)
    (RESULTS_DIR / "run_manifest.json").write_text(
        json.dumps(
            {
                "source_revision": SOURCE_REVISION,
                "clean_source": str(clean_source),
                    "generation_wrapper_sha256": summaries[0]["wrapper_sha256"],
                    "aggregation_wrapper_sha256": sha256_file(worker_script),
                "measurement_count": len(summaries),
                "protocol_variants": 0,
                "records": [row["trace_file"].replace(".trace.json", ".record.json") for row in summaries],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_tables(rows: list[dict[str, Any]]) -> None:
    records = RESULTS_DIR / "measurements.csv"
    fieldnames = [
        "run_index", "N", "frequency", "frames", "path_life_requested", "seed", "roles",
        "generation_wall_seconds", "process_peak_rss_kib", "process_peak_rss_bytes",
        "trace_bytes", "trace_sha256", "timeline_up_ratio", "realized_uptime",
        "realized_up_count", "transitions", "path_up_pool_groups", "path_up_pool_frames",
        "path_down_pool_frames", "mean_up_run_frames", "mean_hops_when_up",
        "shorter_than_skeleton_path_frames", "source", "destination", "baseline_hops",
    ]
    with records.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "roles": ";".join(row["roles"]), "trace_bytes": row["trace_bytes"]})

    timing_groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        if "scale_timing" in row["roles"]:
            timing_groups.setdefault((row["N"], row["frames"]), []).append(row)
    aggregates = RESULTS_DIR / "timing_aggregates.csv"
    with aggregates.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "N", "frames", "repetitions", "wall_mean_seconds", "wall_median_seconds", "wall_max_seconds",
                "rss_mean_kib", "rss_median_kib", "rss_max_kib",
            ],
        )
        writer.writeheader()
        for (n, frames), group in sorted(timing_groups.items()):
            walls = [row["generation_wall_seconds"] for row in group]
            rss = [row["process_peak_rss_kib"] for row in group]
            writer.writerow(
                {
                    "N": n,
                    "frames": frames,
                    "repetitions": len(group),
                    "wall_mean_seconds": statistics.mean(walls),
                    "wall_median_seconds": statistics.median(walls),
                    "wall_max_seconds": max(walls),
                    "rss_mean_kib": statistics.mean(rss),
                    "rss_median_kib": statistics.median(rss),
                    "rss_max_kib": max(rss),
                }
            )

    fidelity = [row for row in rows if "life_fidelity" in row["roles"]]
    bits = [row["connectivity_bits"] for row in fidelity if row["path_life_requested"] == 0.5]
    pair_distances = [
        sum(a != b for a, b in zip(bits[i], bits[j])) / len(bits[i])
        for i in range(len(bits))
        for j in range(i + 1, len(bits))
    ] if bits else []
    diversity = {
        "condition": {"N": 92, "frames": 120, "path_life": 0.5, "seeds": [42, 43, 44, 45, 46]},
        "unique_s_r_bit_timelines": len(set(bits)),
        "mean_pairwise_hamming_fraction": statistics.mean(pair_distances) if pair_distances else None,
        "pairwise_comparisons": len(pair_distances),
        "required_unique": 5,
        "required_mean_hamming_strictly_greater_than": 0.10,
        "passed": len(set(bits)) >= 5 and bool(pair_distances) and statistics.mean(pair_distances) > 0.10,
    }
    (RESULTS_DIR / "seed_diversity.json").write_text(json.dumps(diversity, indent=2, sort_keys=True) + "\n")

    fidelity_rows = []
    for row in fidelity:
        error = abs(row["realized_uptime"] - row["path_life_requested"])
        fidelity_rows.append({
            "N": row["N"],
            "frames": row["frames"],
            "path_life_requested": row["path_life_requested"],
            "seed": row["seed"],
            "realized_uptime": row["realized_uptime"],
            "absolute_error": error,
            "passed_le_0_05": error <= 0.05,
        })
    (RESULTS_DIR / "path_life_fidelity.json").write_text(json.dumps(fidelity_rows, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean-source", required=True)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--frequency", type=int)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--path-life", type=float)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    if args.worker:
        result = worker(args)
        print(json.dumps(result, sort_keys=True))
    elif args.aggregate_only:
        records = [json.loads(path.read_text()) for path in sorted(RESULTS_DIR.glob("*.record.json"))]
        if len(records) != 30:
            raise RuntimeError(f"Expected 30 completed trace records, found {len(records)}")
        write_tables(records)
        (RESULTS_DIR / "run_manifest.json").write_text(
            json.dumps(
                {
                    "source_revision": SOURCE_REVISION,
                    "clean_source": str(Path(args.clean_source).resolve()),
                    "generation_wrapper_sha256": records[0]["wrapper_sha256"],
                    "aggregation_wrapper_sha256": sha256_file(Path(__file__).resolve()),
                    "measurement_count": len(records),
                    "protocol_variants": 0,
                    "records": [row["trace_file"].replace(".trace.json", ".record.json") for row in records],
                    "aggregated_without_rerunning": True,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    else:
        run_parent(args)


if __name__ == "__main__":
    main()
