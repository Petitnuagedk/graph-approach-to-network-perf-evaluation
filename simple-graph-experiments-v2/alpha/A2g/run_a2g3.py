#!/usr/bin/env python3
"""Run the frozen A2g-3 memory-sampler / uk-timeline integration grid."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A1 = ROOT / "alpha" / "A1"
DONOR = ROOT / "alpha" / "A2" / "A2d" / "item1" / "source"
OVERLAY = ROOT / "alpha" / "A2f" / "A2f-2" / "source"
PREREG = HERE / "a2g3_prereg.md"
OUT = HERE / "A2g-3"
FAMILIES = {
    "geodesic": ("geodesic_N92_r1", 0, 31),
    "rgg": ("rgg_N92_r1", 14, 47),
    "ws": ("ws_N92_r1", 49, 85),
    "er": ("er_N92_r1", 5, 82),
    "ba": ("ba_N92_r1", 5, 72),
}
LIVES = ((0.5, 60, 5), (0.9, 108, 9))
PARAMETERS = ((0.5, 2.0), (0.5, 8.0), (0.8, 8.0))
SEEDS = (11, 29, 47)
FRAMES = 120
PERSISTENCY = 0.75
TIMEOUT = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def edge_path(graph_id: str) -> Path:
    return A1 / "results" / "edge_lists" / f"{graph_id}.csv"


def load_skeleton(graph_id: str) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    with edge_path(graph_id).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def op_name(family: str, life: float, pi: float, duration: float, seed: int) -> str:
    return f"{family}__life{life:.1f}__pi{pi:.1f}__L{duration:.0f}__seed{seed}"


def all_jobs() -> list[dict[str, Any]]:
    jobs = []
    for family, (graph_id, source, destination) in FAMILIES.items():
        graph_file = edge_path(graph_id)
        graph = load_skeleton(graph_id)
        if not nx.has_path(graph, source, destination):
            raise RuntimeError(f"registered pair disconnected in skeleton: {graph_id}")
        for life, up_count, up_runs in LIVES:
            for pi, duration in PARAMETERS:
                for seed in SEEDS:
                    jobs.append({
                        "family": family, "graph_id": graph_id, "source": source,
                        "destination": destination, "graph_file": graph_file,
                        "graph_sha256": sha256(graph_file), "N": 92,
                        "life": life, "U": up_count, "K": up_runs,
                        "mean_up_duration": up_count / up_runs,
                        "pi": pi, "L": duration, "seed": seed,
                    })
    if len(jobs) != 90:
        raise RuntimeError(f"expected 90 jobs, got {len(jobs)}")
    return jobs


def build_config(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "stage": "A2g-3", "preregistration_sha256": sha256(PREREG),
        "runner_sha256": sha256(Path(__file__).resolve()),
        "family": job["family"], "graph_id": job["graph_id"], "N": job["N"],
        "graph_edge_list": job["graph_file"].relative_to(ROOT).as_posix(),
        "graph_edge_sha256": job["graph_sha256"],
        "source_node": job["source"], "destination_node": job["destination"],
        "life": job["life"], "frames": FRAMES, "U_requested": job["U"],
        "K_requested": job["K"], "mean_up_duration_timeline": job["mean_up_duration"],
        "timeline_behavior": "uk", "timeline_seed": job["seed"],
        "pathPersistency": PERSISTENCY,
        "edge_sampler_behavior": "patched-v3", "pi": job["pi"],
        "mean_up_duration_edge_L": job["L"], "sampler_seed": job["seed"] + 10000,
        "timeout_seconds": TIMEOUT,
        "source_sha256": {
            "a2d_item1_frameGenerator": sha256(DONOR / "yadygaga" / "frameGenerator.py"),
            "a2d_item1_timelineBlockGenerator": sha256(DONOR / "yadygaga" / "timelineBlockGenerator.py"),
            "a2d_item1_dynaGraph": sha256(DONOR / "yadygaga" / "dynaGraph.py"),
            "a2f_uk_timeline_overlay": sha256(OVERLAY / "yadygaga" / "timelineBlockGenerator.py"),
            "a2f_overlay_init": sha256(OVERLAY / "yadygaga" / "__init__.py"),
        },
        "python": sys.version, "networkx": nx.__version__,
    }


def up_runs(bits: list[bool]) -> list[int]:
    values: list[int] = []
    current = 0
    for state in bits:
        if state:
            current += 1
        elif current:
            values.append(current)
            current = 0
    if current:
        values.append(current)
    return values


def worker(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out_dir = config_path.parent
    started = time.perf_counter()
    try:
        expected_sources = {
            "a2d_item1_frameGenerator": DONOR / "yadygaga" / "frameGenerator.py",
            "a2d_item1_timelineBlockGenerator": DONOR / "yadygaga" / "timelineBlockGenerator.py",
            "a2d_item1_dynaGraph": DONOR / "yadygaga" / "dynaGraph.py",
            "a2f_uk_timeline_overlay": OVERLAY / "yadygaga" / "timelineBlockGenerator.py",
            "a2f_overlay_init": OVERLAY / "yadygaga" / "__init__.py",
        }
        for key, source_file in expected_sources.items():
            if sha256(source_file) != config["source_sha256"][key]:
                raise RuntimeError(f"source hash changed: {key}")
        if sha256(ROOT / config["graph_edge_list"]) != config["graph_edge_sha256"]:
            raise RuntimeError("A1 graph edge-list hash mismatch")

        sys.path.insert(0, str(OVERLAY))
        from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
        from yadygaga.frameGenerator import FrameGenerator

        graph = load_skeleton(config["graph_id"])
        source, destination = int(config["source_node"]), int(config["destination_node"])
        timeline_data = SPCTimelineBlockGenerator(
            frames=FRAMES, seed=int(config["timeline_seed"]), mode="blocks",
            pathPersistency=float(config["pathPersistency"]), behavior="uk",
            up_count=int(config["U_requested"]), up_runs=int(config["K_requested"]),
        ).generate_blocks()
        bits = [bool(value) for value in timeline_data["timeline"]]
        path_ids = timeline_data["path_ids"]
        realized_u = sum(bits)
        realized_k = sum(state and (index == 0 or not bits[index - 1]) for index, state in enumerate(bits))
        if realized_u != config["U_requested"] or realized_k != config["K_requested"]:
            raise RuntimeError("uk timeline failed exact U/K invariant")
        bitstring = "".join("1" if bit else "0" for bit in bits)
        write_json(out_dir / "timeline.json", {
            "bits": bitstring, "path_ids": path_ids,
            "sha256": hashlib.sha256(bitstring.encode()).hexdigest(),
            "U_realized": realized_u, "K_realized": realized_k,
        })

        generator = FrameGenerator()
        temporal = generator.generateSPCFrames(
            limited_G=graph, s=source, d=destination, trials=0,
            p_edge=float(config["pi"]), seed=int(config["sampler_seed"]),
            behavior="patched-v3", timeline=bits,
            mean_up_duration=float(config["mean_up_duration_edge_L"]),
        )
        # The dispatch stores this complete result as temporal_result; legacy output is untouched.
        temporal = generator.temporal_result
        raw_frames = temporal["raw_frames"]
        projected_frames = temporal["frames"]
        edge_order = sorted(
            (tuple(sorted(edge, key=str)) for edge in graph.edges()),
            key=lambda edge: (str(edge[0]), str(edge[1])),
        )
        raw_bits = {edge: [frame.has_edge(*edge) for frame in raw_frames] for edge in edge_order}
        projected_bits = {edge: [frame.has_edge(*edge) for frame in projected_frames] for edge in edge_order}
        raw_pi = sum(sum(states) for states in raw_bits.values()) / (len(edge_order) * FRAMES)
        projected_pi = sum(sum(states) for states in projected_bits.values()) / (len(edge_order) * FRAMES)
        raw_durations = [duration for states in raw_bits.values() for duration in up_runs(states)]
        projected_durations = [duration for states in projected_bits.values() for duration in up_runs(states)]
        raw_lhat = statistics.mean(raw_durations) if raw_durations else math.nan
        projected_lhat = statistics.mean(projected_durations) if projected_durations else math.nan
        changed_count = sum(
            raw_bits[edge][frame] != projected_bits[edge][frame]
            for edge in edge_order for frame in range(FRAMES)
        )
        projection_fraction = changed_count / (len(edge_order) * FRAMES)
        skeleton_edges = {frozenset(edge) for edge in graph.edges()}
        mask = [nx.has_path(frame, source, destination) for frame in projected_frames]
        all_edges_inside = all(
            frozenset(edge) in skeleton_edges
            for frame in (*raw_frames, *projected_frames) for edge in frame.edges()
        )
        exact_mask = mask == bits
        exact_up_count = sum(mask) == int(config["U_requested"])
        projection_gate = projection_fraction <= 0.05
        pi_gate = abs(projected_pi - float(config["pi"])) <= 0.05
        duration_gate = abs(projected_lhat - float(config["mean_up_duration_edge_L"])) / float(config["mean_up_duration_edge_L"]) <= 0.20
        metrics = {
            "status": "success", "family": config["family"], "graph_id": config["graph_id"],
            "life": config["life"], "U_requested": config["U_requested"], "K_requested": config["K_requested"],
            "timeline_mean_up_duration": config["mean_up_duration_timeline"], "pi": config["pi"],
            "L": config["mean_up_duration_edge_L"], "seed": config["timeline_seed"],
            "sampler_seed": config["sampler_seed"], "timeline_sha256": hashlib.sha256(bitstring.encode()).hexdigest(),
            "raw_empirical_pi": raw_pi, "raw_mean_up_duration": raw_lhat,
            "projected_empirical_pi": projected_pi, "projected_mean_up_duration": projected_lhat,
            "projection_changed_edge_time_fraction": projection_fraction,
            "changed_edge_time_count": changed_count, "skeleton_edge_time_count": len(edge_order) * FRAMES,
            "target_up_count": realized_u, "projected_up_count": sum(mask),
            "uk_exact_UK": realized_u == config["U_requested"] and realized_k == config["K_requested"],
            "sr_mask_exact": exact_mask, "all_edges_in_skeleton": all_edges_inside,
            "projection_fraction_pass": projection_gate, "projected_pi_abs_error": abs(projected_pi - float(config["pi"])),
            "projected_pi_pass": pi_gate,
            "projected_duration_relative_error": abs(projected_lhat - float(config["mean_up_duration_edge_L"])) / float(config["mean_up_duration_edge_L"]),
            "projected_duration_pass": duration_gate,
            "operation_qualifies": exact_mask and exact_up_count and all_edges_inside and projection_gate and pi_gate and duration_gate,
            "elapsed_worker_seconds": time.perf_counter() - started,
        }
        write_json(out_dir / "trace_metrics.json", metrics)
        with gzip.open(out_dir / "edge_states.csv.gz", "wt", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["u", "v", "frame", "timeline_up", "raw_up", "projected_up", "projection_changed"])
            writer.writeheader()
            for edge in edge_order:
                for frame_index in range(FRAMES):
                    raw_up, projected_up = raw_bits[edge][frame_index], projected_bits[edge][frame_index]
                    writer.writerow({
                        "u": edge[0], "v": edge[1], "frame": frame_index,
                        "timeline_up": bits[frame_index], "raw_up": raw_up,
                        "projected_up": projected_up, "projection_changed": raw_up != projected_up,
                    })
        correction_rows = [
            {"frame": frame_index, "u": edge[0], "v": edge[1]}
            for frame_index, changes in enumerate(temporal["corrections"])
            for edge in changes
        ]
        write_csv(out_dir / "projection_changes.csv", correction_rows, ["frame", "u", "v"])
        with gzip.open(out_dir / "frames.csv.gz", "wt", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["frame", "timeline_up", "connected", "edge_count", "edges_json"])
            writer.writeheader()
            for frame_index, frame in enumerate(projected_frames):
                edges = sorted(tuple(sorted(edge)) for edge in frame.edges())
                writer.writerow({
                    "frame": frame_index, "timeline_up": bits[frame_index],
                    "connected": mask[frame_index], "edge_count": len(edges),
                    "edges_json": json.dumps(edges, separators=(",", ":")),
                })
        write_json(out_dir / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(out_dir / "operation_status.json", {
            "status": "failed_exception", "exception": repr(error),
            "elapsed_worker_seconds": time.perf_counter() - started,
        })
        return 1


def run_grid() -> int:
    jobs = all_jobs()
    OUT.mkdir(parents=True, exist_ok=True)
    log_path = OUT / "operation_log.csv"
    if log_path.exists():
        raise RuntimeError("A2g-3 operation ledger already exists; refusing to rerun any cell")
    rows: list[dict[str, Any]] = []
    fields = ["operation", "status", "returncode", "elapsed_seconds", "family", "graph_id", "life", "U", "K", "pi", "L", "seed", "config_sha256", "config_path", "stdout", "stderr"]
    for index, job in enumerate(jobs, 1):
        name = op_name(job["family"], job["life"], job["pi"], job["L"], job["seed"])
        out_dir = OUT / "operations" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        config_path = out_dir / "config.json"
        config = build_config(job)
        write_json(config_path, config)
        started = time.perf_counter()
        try:
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)],
                cwd=HERE, timeout=TIMEOUT, capture_output=True, text=True, check=False,
            )
            elapsed = time.perf_counter() - started
            status_doc = json.loads((out_dir / "operation_status.json").read_text(encoding="utf-8")) if (out_dir / "operation_status.json").exists() else {"status": "missing_status"}
            status = status_doc.get("status", "missing_status")
            stdout, stderr, returncode = process.stdout[-1000:], process.stderr[-1000:], process.returncode
        except subprocess.TimeoutExpired as error:
            elapsed = time.perf_counter() - started
            write_json(out_dir / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": TIMEOUT, "elapsed_seconds": elapsed})
            status, returncode = "failed_timeout", "TIMEOUT"
            stdout, stderr = str(error.stdout or "")[-1000:], str(error.stderr or "")[-1000:]
        rows.append({
            "operation": name, "status": status, "returncode": returncode,
            "elapsed_seconds": elapsed, "family": job["family"], "graph_id": job["graph_id"],
            "life": job["life"], "U": job["U"], "K": job["K"], "pi": job["pi"],
            "L": job["L"], "seed": job["seed"],
            "config_sha256": sha256(config_path), "config_path": config_path.relative_to(ROOT).as_posix(),
            "stdout": stdout, "stderr": stderr,
        })
        write_csv(log_path, rows, fields)
        print(f"[{index}/{len(jobs)}] {name}: {status} ({elapsed:.2f}s)", flush=True)
    return 0 if all(row["status"] == "success" for row in rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path)
    args = parser.parse_args()
    if args.operation:
        return worker(args.operation.resolve())
    return run_grid()


if __name__ == "__main__":
    raise SystemExit(main())
