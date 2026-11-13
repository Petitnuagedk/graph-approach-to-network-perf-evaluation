#!/usr/bin/env python3
"""Run the preregistered A2d item 1 chain, integration, and compatibility tests."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import sys
import traceback
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
A1 = ROOT / "simple-graph-experiments-v2" / "alpha" / "A1"
A0R2 = ROOT / "simple-graph-experiments-v2" / "alpha" / "A0R2"
SOURCE = HERE / "source"
BASE_SOURCE = A0R2 / "YaDyGaGa"
RESULTS = HERE / "results"
PREREG = HERE / "prereg.md"
FAMILIES = {
    "geodesic": ("geodesic_N92_r1", 0, 31),
    "rgg": ("rgg_N92_r1", 14, 47),
    "ws": ("ws_N92_r1", 49, 85),
    "er": ("er_N92_r1", 5, 82),
    "ba": ("ba_N92_r1", 5, 72),
}
PIS = (0.3, 0.7)
DURATIONS = (3.0, 8.0)
SEEDS = (11, 29, 47)
TARGET_LIFE = 0.5
TARGET_STABILITY = 0.5
CHAIN_FRAMES = 120_000
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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_graph(family: str) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    graph_id = FAMILIES[family][0]
    path = A1 / "results" / "edge_lists" / f"{graph_id}.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def runs(bits: list[bool]) -> list[int]:
    output = []
    length = 0
    for state in bits:
        if state:
            length += 1
        elif length:
            output.append(length)
            length = 0
    if length:
        output.append(length)
    return output


def chain_metrics(bits: list[bool]) -> tuple[float, float, int, int]:
    durations = runs(bits)
    completed = durations[:]
    if bits and bits[0] and completed:
        completed = completed[1:]
    if bits and bits[-1] and completed:
        completed = completed[:-1]
    return (
        sum(bits) / len(bits),
        statistics.mean(completed) if completed else math.nan,
        sum(bits[index] and not bits[index - 1] for index in range(1, len(bits))) + int(bits[0]),
        sum(not bits[index] and bits[index - 1] for index in range(1, len(bits))),
    )


def frame_fingerprint(graph: nx.Graph) -> tuple:
    nodes = tuple(sorted(graph.nodes(), key=str))
    edges = tuple(sorted((tuple(sorted(edge, key=str)) for edge in graph.edges()), key=lambda edge: (str(edge[0]), str(edge[1]))))
    return nodes, edges


def frame_pool_fingerprint(frame_generator) -> str:
    payload = {
        "up_keys": [list(key) for key in frame_generator.path_up_keys],
        "up_frames": [[frame_fingerprint(g) for g in group] for group in frame_generator.path_up_frames],
        "down_frames": [frame_fingerprint(g) for g in frame_generator.path_down_frames],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def execute(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output = config_path.parent
    try:
        if config["kind"] == "standalone":
            module = load_module("a2d_item1_patched_frame_generator", SOURCE / "yadygaga" / "frameGenerator.py")
            bits = module.FrameGenerator.sample_two_state_chain(
                config["frames"], config["pi"], config["mean_up_duration"], config["seed"]
            )
            pi_hat, duration_hat, up_runs, down_runs = chain_metrics(bits)
            expected_p10 = 1 / config["mean_up_duration"]
            expected_p01 = config["pi"] / ((1 - config["pi"]) * config["mean_up_duration"])
            write_json(output / "chain.json", {
                "bits": "".join("1" if bit else "0" for bit in bits),
                "pi_hat": pi_hat,
                "mean_completed_up_duration_hat": duration_hat,
                "up_run_count": up_runs,
                "down_run_count": down_runs,
                "p_down_given_up": expected_p10,
                "p_up_given_down": expected_p01,
                "pi_abs_error": abs(pi_hat - config["pi"]),
                "duration_relative_error": abs(duration_hat - config["mean_up_duration"]) / config["mean_up_duration"],
                "standalone_pass": abs(pi_hat - config["pi"]) <= 0.02 and abs(duration_hat - config["mean_up_duration"]) / config["mean_up_duration"] <= 0.10,
            })
        elif config["kind"] == "integrated":
            sys.path.insert(0, str(SOURCE))
            from yadygaga.frameGenerator import FrameGenerator
            from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

            family = config["family"]
            graph_id, source, destination = FAMILIES[family]
            graph = load_graph(family)
            timeline_data = SPCTimelineBlockGenerator(
                120, TARGET_LIFE, TARGET_STABILITY, config["seed"], mode="blocks", pathPersistency=0.75, behavior="patched"
            ).generate_blocks()
            target = timeline_data["timeline"]
            output_data = FrameGenerator().generateTemporalSPCFrames(
                graph, source, destination, target, config["pi"], config["mean_up_duration"], config["seed"] + 10000
            )
            raw_frames = output_data["raw_frames"]
            constrained = output_data["frames"]
            edge_order = sorted((tuple(sorted(edge, key=str)) for edge in graph.edges()), key=lambda edge: (str(edge[0]), str(edge[1])))
            raw_bits_by_edge = {edge: [frame.has_edge(*edge) for frame in raw_frames] for edge in edge_order}
            post_bits_by_edge = {edge: [frame.has_edge(*edge) for frame in constrained] for edge in edge_order}
            raw_counts = [sum(bits) for bits in raw_bits_by_edge.values()]
            post_counts = [sum(bits) for bits in post_bits_by_edge.values()]
            raw_runs = [duration for bits in raw_bits_by_edge.values() for duration in runs(bits)]
            post_runs = [duration for bits in post_bits_by_edge.values() for duration in runs(bits)]
            raw_mean_up = statistics.mean(raw_runs) if raw_runs else math.nan
            post_mean_up = statistics.mean(post_runs) if post_runs else math.nan
            changed = sum(
                raw_bits_by_edge[edge][frame_index] != post_bits_by_edge[edge][frame_index]
                for edge in edge_order for frame_index in range(120)
            )
            changed_fraction = changed / (len(edge_order) * 120)
            route_mask = []
            all_edges_subset = True
            skeleton_edges = {frozenset(edge) for edge in graph.edges()}
            for frame in constrained:
                route_mask.append(nx.has_path(frame, source, destination))
                all_edges_subset &= all(frozenset(edge) in skeleton_edges for edge in frame.edges())
            projected_pi = sum(post_counts) / (len(edge_order) * 120)
            metrics = {
                "status": "success",
                "family": family,
                "graph_id": graph_id,
                "seed": config["seed"],
                "pi": config["pi"],
                "mean_up_duration": config["mean_up_duration"],
                "raw_empirical_pi": sum(raw_counts) / (len(edge_order) * 120),
                "raw_mean_up_duration": raw_mean_up,
                "projected_empirical_pi": projected_pi,
                "projected_mean_up_duration": post_mean_up,
                "projection_changed_edge_time_fraction": changed_fraction,
                "target_up_count": sum(target),
                "projected_up_count": sum(route_mask),
                "sr_mask_exact": route_mask == target,
                "all_edges_in_skeleton": all_edges_subset,
                "integrated_pass": route_mask == target and all_edges_subset and changed_fraction <= 0.05 and abs(projected_pi - config["pi"]) <= 0.05 and abs(post_mean_up - config["mean_up_duration"]) / config["mean_up_duration"] <= 0.20,
            }
            write_json(output / "trace_metrics.json", metrics)
            edge_rows = []
            for edge in edge_order:
                raw_pi = sum(raw_bits_by_edge[edge]) / 120
                projected_edge_pi = sum(post_bits_by_edge[edge]) / 120
                edge_rows.append({
                    "u": edge[0], "v": edge[1],
                    "raw_bits": "".join("1" if state else "0" for state in raw_bits_by_edge[edge]),
                    "projected_bits": "".join("1" if state else "0" for state in post_bits_by_edge[edge]),
                    "raw_pi_hat": raw_pi,
                    "projected_pi_hat": projected_edge_pi,
                    "changed_frames": sum(a != b for a, b in zip(raw_bits_by_edge[edge], post_bits_by_edge[edge])),
                })
            write_csv(output / "edge_traces.csv", edge_rows, ["u", "v", "raw_bits", "projected_bits", "raw_pi_hat", "projected_pi_hat", "changed_frames"])
            correction_rows = []
            for frame_index, changes in enumerate(output_data["corrections"]):
                correction_rows.extend({"frame": frame_index, "u": edge[0], "v": edge[1]} for edge in changes)
            write_csv(output / "projection_changes.csv", correction_rows, ["frame", "u", "v"])
        elif config["kind"] == "legacy_compatibility":
            family = "geodesic"
            graph = load_graph(family)
            _, source, destination = FAMILIES[family]
            original_frame = load_module("a2d_item1_original_frame", BASE_SOURCE / "yadygaga" / "frameGenerator.py")
            patched_frame = load_module("a2d_item1_patched_frame", SOURCE / "yadygaga" / "frameGenerator.py")
            original_timeline = load_module("a2d_item1_original_timeline", BASE_SOURCE / "yadygaga" / "timelineBlockGenerator.py")
            patched_timeline = load_module("a2d_item1_patched_timeline", SOURCE / "yadygaga" / "timelineBlockGenerator.py")
            behavior = config["behavior"]
            original_schedule = original_timeline.SPCTimelineBlockGenerator(120, 0.5, config["stability"], config["seed"], pathPersistency=0.75, behavior=behavior).generate_blocks()
            patched_schedule = patched_timeline.SPCTimelineBlockGenerator(120, 0.5, config["stability"], config["seed"], pathPersistency=0.75, behavior=behavior).generate_blocks()
            schedule_bytes_original = json.dumps(original_schedule, separators=(",", ":")).encode()
            schedule_bytes_patched = json.dumps(patched_schedule, separators=(",", ":")).encode()
            original_pool = original_frame.FrameGenerator()
            patched_pool = patched_frame.FrameGenerator()
            pool_args = {"limited_G": graph, "s": source, "d": destination, "trials": 1000, "p_edge": 0.5, "pathPersistency": 0.75, "seed": config["seed"] + 10000}
            original_pool.generateSPCFrames(**pool_args)
            patched_pool.generateSPCFrames(**pool_args)
            timeline_equal = schedule_bytes_original == schedule_bytes_patched
            pool_hash_original = frame_pool_fingerprint(original_pool)
            pool_hash_patched = frame_pool_fingerprint(patched_pool)
            write_json(output / "compatibility.json", {
                "behavior": behavior,
                "timeline_byte_identical": timeline_equal,
                "timeline_original_sha256": hashlib.sha256(schedule_bytes_original).hexdigest(),
                "timeline_patched_sha256": hashlib.sha256(schedule_bytes_patched).hexdigest(),
                "frame_pool_original_sha256": pool_hash_original,
                "frame_pool_patched_sha256": pool_hash_patched,
                "frame_pool_byte_identical": pool_hash_original == pool_hash_patched,
                "compatibility_pass": timeline_equal and pool_hash_original == pool_hash_patched,
            })
        else:
            raise ValueError(f"unknown operation kind {config['kind']}")
        write_json(output / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(output / "operation_status.json", {"status": "failed_exception", "exception": repr(error), "traceback": traceback.format_exc()})
        return 1


def make_config(kind: str, output: Path, **kwargs) -> dict:
    config = {
        "stage": "A2d-item1",
        "kind": kind,
        "timeout_seconds": TIMEOUT,
        "preregistration_sha256": sha256(PREREG),
        "source_tree": "32b243bc84b587f1782ead0d0ac56382a57425e5",
        "source_sha256": {
            "baseline_frameGenerator.py": sha256(BASE_SOURCE / "yadygaga" / "frameGenerator.py"),
            "patched_frameGenerator.py": sha256(SOURCE / "yadygaga" / "frameGenerator.py"),
            "baseline_timelineBlockGenerator.py": sha256(BASE_SOURCE / "yadygaga" / "timelineBlockGenerator.py"),
            "patched_timelineBlockGenerator.py": sha256(SOURCE / "yadygaga" / "timelineBlockGenerator.py"),
            "diagnostic_runner.py": sha256(Path(__file__).resolve()),
        },
        "python": sys.version,
        "networkx": nx.__version__,
        **kwargs,
    }
    if "family" in kwargs:
        family = kwargs["family"]
        config["graph_edge_sha256"] = sha256(A1 / "results" / "edge_lists" / f"{FAMILIES[family][0]}.csv")
        config["graph_id"] = FAMILIES[family][0]
        config["source_node"] = FAMILIES[family][1]
        config["destination_node"] = FAMILIES[family][2]
    return config


def parent() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    specs = []
    for pi in PIS:
        for duration in DURATIONS:
            for seed in SEEDS:
                specs.append(("standalone", f"chain_pi_{pi:.1f}_L_{duration:g}_seed_{seed}", {"pi": pi, "mean_up_duration": duration, "seed": seed, "frames": CHAIN_FRAMES}))
    for family in FAMILIES:
        for pi in PIS:
            for duration in DURATIONS:
                for seed in SEEDS:
                    specs.append(("integrated", f"integrated_{family}_pi_{pi:.1f}_L_{duration:g}_seed_{seed}", {"family": family, "pi": pi, "mean_up_duration": duration, "seed": seed, "frames": 120, "life": TARGET_LIFE, "stability": TARGET_STABILITY, "timeline_seed": seed}))
    for stability in (0.0, 0.2, 0.4, 0.6, 0.8):
        for seed in range(42, 52):
            specs.append(("legacy_compatibility", f"compat_{stability:.1f}_seed_{seed}", {"stability": stability, "seed": seed, "frames": 120, "life": 0.5, "behavior": "patched"}))
    # The legacy behavior is checked on the same frozen parameter points too.
    for stability in (0.0, 0.2, 0.4, 0.6, 0.8):
        for seed in range(42, 52):
            specs.append(("legacy_compatibility", f"compat_legacy_{stability:.1f}_seed_{seed}", {"stability": stability, "seed": seed, "frames": 120, "life": 0.5, "behavior": "legacy"}))

    run_log = []
    for kind, label, kwargs in specs:
        output = RESULTS / label
        output.mkdir(parents=True, exist_ok=True)
        config = make_config(kind, output, **kwargs)
        config_path = output / "config.json"
        write_json(config_path, config)
        command = [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)]
        try:
            completed = subprocess.run(command, timeout=TIMEOUT, check=False, cwd=HERE)
            status_path = output / "operation_status.json"
            status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"status": "failed_missing_status"}
            run_log.append({"label": label, "kind": kind, "returncode": completed.returncode, "status": status.get("status")})
        except subprocess.TimeoutExpired:
            write_json(output / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": TIMEOUT})
            run_log.append({"label": label, "kind": kind, "returncode": "TIMEOUT", "status": "failed_timeout"})

    write_csv(RESULTS / "operation_log.csv", run_log, ["label", "kind", "returncode", "status"])
    summarize()


def summarize() -> None:
    standalone = []
    integrated = []
    compatibility = []
    operation_rows = []
    for output in sorted(path for path in RESULTS.iterdir() if path.is_dir()):
        status_path = output / "operation_status.json"
        if not status_path.exists():
            continue
        status = json.loads(status_path.read_text(encoding="utf-8"))
        config = json.loads((output / "config.json").read_text(encoding="utf-8"))
        operation_rows.append({"label": output.name, "kind": config["kind"], "status": status.get("status")})
        if config["kind"] == "standalone" and (output / "chain.json").exists():
            standalone.append({**config, **json.loads((output / "chain.json").read_text(encoding="utf-8"))})
        elif config["kind"] == "integrated" and (output / "trace_metrics.json").exists():
            integrated.append({**config, **json.loads((output / "trace_metrics.json").read_text(encoding="utf-8"))})
        elif config["kind"] == "legacy_compatibility" and (output / "compatibility.json").exists():
            compatibility.append({**config, **json.loads((output / "compatibility.json").read_text(encoding="utf-8"))})
    write_csv(RESULTS / "operation_log.csv", operation_rows, ["label", "kind", "status"])
    write_csv(RESULTS / "standalone_chain_results.csv", standalone, ["pi", "mean_up_duration", "seed", "frames", "pi_hat", "mean_completed_up_duration_hat", "up_run_count", "down_run_count", "p_down_given_up", "p_up_given_down", "pi_abs_error", "duration_relative_error", "standalone_pass"])
    write_csv(RESULTS / "integrated_results.csv", integrated, ["family", "graph_id", "seed", "pi", "mean_up_duration", "raw_empirical_pi", "raw_mean_up_duration", "projected_empirical_pi", "projected_mean_up_duration", "projection_changed_edge_time_fraction", "target_up_count", "projected_up_count", "sr_mask_exact", "all_edges_in_skeleton", "integrated_pass"])
    write_csv(RESULTS / "compatibility_results.csv", compatibility, ["behavior", "stability", "seed", "timeline_byte_identical", "timeline_original_sha256", "timeline_patched_sha256", "frame_pool_original_sha256", "frame_pool_patched_sha256", "frame_pool_byte_identical", "compatibility_pass"])
    cells = []
    for pi in PIS:
        for duration in DURATIONS:
            rows = [row for row in standalone if row["pi"] == pi and row["mean_up_duration"] == duration]
            cells.append({
                "pi": pi,
                "mean_up_duration": duration,
                "n_seeds": len(rows),
                "pi_hat_mean": statistics.mean(row["pi_hat"] for row in rows) if rows else "NA",
                "pi_hat_sd_ddof1": statistics.stdev(row["pi_hat"] for row in rows) if len(rows) > 1 else "NA",
                "up_duration_hat_mean": statistics.mean(row["mean_completed_up_duration_hat"] for row in rows) if rows else "NA",
                "up_duration_hat_sd_ddof1": statistics.stdev(row["mean_completed_up_duration_hat"] for row in rows) if len(rows) > 1 else "NA",
                "all_seed_gates_pass": len(rows) == 3 and all(row["standalone_pass"] for row in rows),
            })
    write_csv(RESULTS / "standalone_cell_summary.csv", cells, list(cells[0]) if cells else ["pi", "mean_up_duration"])
    print(json.dumps({
        "operations": len(operation_rows),
        "failed_operations": sum(row["status"] != "success" for row in operation_rows),
        "standalone_pass": len(standalone) == 12 and all(row["standalone_pass"] for row in standalone),
        "integrated_pass_count": sum(row["integrated_pass"] for row in integrated),
        "integrated_operations": len(integrated),
        "legacy_compatibility_pass": len(compatibility) == 100 and all(row["compatibility_pass"] for row in compatibility),
    }, indent=2))


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
