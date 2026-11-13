#!/usr/bin/env python3
"""Run the preregistered A2d item 3 end-to-end seed reproducibility audit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
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
SOURCE = HERE.parent / "item1" / "source"
SOURCE_PKG = SOURCE / "yadygaga"
RESULTS = HERE / "results"
PREREG = HERE / "prereg.md"
GRAPH_PATH = A1 / "results" / "edge_lists" / "er_N92_r1.csv"
BASE_SEEDS = (11, 29, 47, 71, 97)
TIMEOUT = 60
FRAMES = 120
TRIALS = 3000
SOURCE_FILES = {
    "frameGenerator.py": SOURCE_PKG / "frameGenerator.py",
    "timelineBlockGenerator.py": SOURCE_PKG / "timelineBlockGenerator.py",
    "dynaGraph.py": SOURCE_PKG / "dynaGraph.py",
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def graph_edges(graph: nx.Graph) -> list[list[int]]:
    return [list(edge) for edge in sorted((tuple(sorted((int(u), int(v)))) for u, v in graph.edges()))]


def frame_fingerprint(graph: nx.Graph) -> str:
    return sha256_bytes(canonical_json(graph_edges(graph)))


def load_graph() -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    with GRAPH_PATH.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def run_operation(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output = config_path.parent
    try:
        sys.path.insert(0, str(SOURCE))
        from yadygaga.frameGenerator import FrameGenerator
        from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
        from yadygaga.dynaGraph import SPCDynamicGraph

        graph = load_graph()
        start = time.perf_counter()
        timeline_generator = SPCTimelineBlockGenerator(
            frames=FRAMES,
            path_life=0.5,
            stability=0.5,
            seed=config["timeline_seed"],
            mode="blocks",
            pathPersistency=0.75,
            behavior="patched",
        )
        timeline_data = timeline_generator.generate_blocks()
        timeline_seconds = time.perf_counter() - start

        frame_generator = FrameGenerator()
        start = time.perf_counter()
        frame_generator.generateSPCFrames(
            graph,
            5,
            82,
            trials=TRIALS,
            p_edge=0.5,
            pathPersistency=0.75,
            seed=config["frame_pool_seed"],
            behavior="legacy",
        )
        pool_seconds = time.perf_counter() - start

        pool_up_fingerprints = [
            [frame_fingerprint(frame) for frame in group]
            for group in frame_generator.path_up_frames
        ]
        pool_down_fingerprints = [frame_fingerprint(frame) for frame in frame_generator.path_down_frames]
        pool_payload = {"up": pool_up_fingerprints, "down": pool_down_fingerprints}
        pool_hash = sha256_bytes(canonical_json(pool_payload))

        assembler = SPCDynamicGraph()
        start = time.perf_counter()
        assembled = assembler.buildDynaGraph(
            timeline_data,
            frame_generator.path_up_frames,
            frame_generator.path_down_frames,
            seed=config["assembly_seed"],
        )
        assembly_seconds = time.perf_counter() - start

        assembled_fingerprints = [frame_fingerprint(frame) for frame in assembled]
        assembled_payload = {"frames": assembled_fingerprints}
        assembly_hash = sha256_bytes(canonical_json(assembled_payload))
        timeline_payload = {
            "timeline": timeline_data["timeline"],
            "path_ids": timeline_data["path_ids"],
        }
        timeline_hash = sha256_bytes(canonical_json(timeline_payload))
        target_mask = [bool(state) for state in timeline_data["timeline"]]
        actual_mask = [nx.has_path(frame, 5, 82) for frame in assembled]
        mask_exact = actual_mask == target_mask
        skeleton = {frozenset((u, v)) for u, v in graph.edges()}
        edges_subset = all(
            frozenset((u, v)) in skeleton
            for frame in assembled
            for u, v in frame.edges()
        )
        pools_nonempty = bool(frame_generator.path_up_frames) and bool(frame_generator.path_down_frames)
        result = {
            "status": "success",
            "run_id": config["run_id"],
            "base_seed": config["base_seed"],
            "repeat": config["repeat"],
            "timeline_seconds": timeline_seconds,
            "frame_pool_seconds": pool_seconds,
            "assembly_seconds": assembly_seconds,
            "total_stage_seconds": timeline_seconds + pool_seconds + assembly_seconds,
            "timeline_sha256": timeline_hash,
            "frame_pool_sha256": pool_hash,
            "assembly_sha256": assembly_hash,
            "up_group_sizes": [len(group) for group in frame_generator.path_up_frames],
            "down_pool_size": len(frame_generator.path_down_frames),
            "frame_pool_up_fingerprints": pool_up_fingerprints,
            "frame_pool_down_fingerprints": pool_down_fingerprints,
            "assembled_frame_fingerprints": assembled_fingerprints,
            "requested_mask": target_mask,
            "actual_mask": actual_mask,
            "assembly_mask_exact": mask_exact,
            "pools_nonempty": pools_nonempty,
            "all_edges_in_skeleton": edges_subset,
        }
        write_json(output / "timeline_and_paths.json", timeline_payload)
        write_json(output / "frame_pool_fingerprints.json", pool_payload)
        write_json(output / "assembly_fingerprints.json", assembled_payload)
        write_json(output / "operation_result.json", result)
        write_json(output / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(output / "operation_status.json", {
            "status": "failed_exception",
            "exception": repr(error),
            "traceback": traceback.format_exc(),
        })
        return 1


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def summarize() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    operations = []
    for output in sorted(path for path in RESULTS.iterdir() if path.is_dir()):
        result_path = output / "operation_result.json"
        status_path = output / "operation_status.json"
        if result_path.exists():
            operations.append(json.loads(result_path.read_text(encoding="utf-8")))
        elif status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            operations.append({"run_id": output.name, "status": status.get("status")})

    comparisons = []
    for seed in BASE_SEEDS:
        first = next((row for row in operations if row.get("base_seed") == seed and row.get("repeat") == 1), None)
        second = next((row for row in operations if row.get("base_seed") == seed and row.get("repeat") == 2), None)
        for stage, key in (("timeline", "timeline_sha256"), ("frame_pool", "frame_pool_sha256"), ("assembly", "assembly_sha256")):
            match = bool(first and second and first.get(key) == second.get(key))
            comparisons.append({"base_seed": seed, "stage": stage, "hash_match": match})

    successful = [row for row in operations if row.get("status") == "success"]
    runtimes = {}
    for stage, key in (("timeline", "timeline_seconds"), ("frame_pool", "frame_pool_seconds"), ("assembly", "assembly_seconds"), ("total", "total_stage_seconds")):
        values = [float(row[key]) for row in successful if key in row]
        runtimes[stage] = {
            "n": len(values),
            "mean_seconds": statistics.mean(values) if values else "NA",
            "sd_seconds_ddof1": statistics.stdev(values) if len(values) > 1 else "NA",
            "max_seconds": max(values) if values else "NA",
        }
    summary = {
        "operations": len(operations),
        "completed": len(successful),
        "repeat_comparisons": len(comparisons),
        "repeat_hash_matches": sum(row["hash_match"] for row in comparisons),
        "all_reproducibility_matches": len(comparisons) == 15 and all(row["hash_match"] for row in comparisons),
        "all_assembly_masks_exact": len(successful) == 10 and all(row.get("assembly_mask_exact") for row in successful),
        "all_pools_nonempty": len(successful) == 10 and all(row.get("pools_nonempty") for row in successful),
        "all_edges_in_skeleton": len(successful) == 10 and all(row.get("all_edges_in_skeleton") for row in successful),
        "runtimes": runtimes,
    }
    write_json(RESULTS / "summary.json", summary)
    write_csv(RESULTS / "repeat_comparisons.csv", comparisons, ["base_seed", "stage", "hash_match"])
    write_csv(RESULTS / "operation_summary.csv", operations, ["run_id", "status", "base_seed", "repeat", "timeline_seconds", "frame_pool_seconds", "assembly_seconds", "total_stage_seconds", "timeline_sha256", "frame_pool_sha256", "assembly_sha256", "up_group_sizes", "down_pool_size", "assembly_mask_exact", "pools_nonempty", "all_edges_in_skeleton"])
    print(json.dumps(summary, indent=2))


def parent() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    runner_hash = sha256_file(Path(__file__).resolve())
    for seed in BASE_SEEDS:
        for repeat in (1, 2):
            run_id = f"seed{seed}_repeat{repeat}"
            output = RESULTS / run_id
            output.mkdir(parents=True, exist_ok=True)
            config = {
                "run_id": run_id,
                "base_seed": seed,
                "repeat": repeat,
                "timeline_seed": seed,
                "frame_pool_seed": seed + 10000,
                "assembly_seed": seed + 20000,
                "graph_id": "er_N92_r1",
                "graph_edge_sha256": sha256_file(GRAPH_PATH),
                "pairs": [[5, 82]],
                "frames": FRAMES,
                "path_life": 0.5,
                "stability": 0.5,
                "pathPersistency": 0.75,
                "mode": "blocks",
                "pool_trials": TRIALS,
                "p_edge": 0.5,
                "behavior_timeline": "patched",
                "behavior_frame_pool": "legacy",
                "assembler": "seeded-active-SPCDynamicGraph",
                "timeout_seconds": TIMEOUT,
                "preregistration_sha256": sha256_file(PREREG),
                "runner_sha256": runner_hash,
                "source_sha256": {name: sha256_file(path) for name, path in SOURCE_FILES.items()},
                "python": sys.version,
                "networkx": nx.__version__,
            }
            config_path = output / "config.json"
            write_json(config_path, config)
            command = [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)]
            try:
                completed = subprocess.run(command, cwd=HERE, timeout=TIMEOUT, check=False)
                if completed.returncode != 0:
                    continue
            except subprocess.TimeoutExpired:
                write_json(output / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": TIMEOUT})
    summarize()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    if args.operation:
        raise SystemExit(run_operation(args.operation))
    if args.summarize:
        summarize()
    else:
        parent()


if __name__ == "__main__":
    main()
