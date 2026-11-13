#!/usr/bin/env python3
"""Execute the preregistered A2f-3 generator-only decoupling study."""
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
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
A2 = ROOT / "alpha" / "A2"
A1 = ROOT / "alpha" / "A1"
A2F2_SOURCE = ROOT / "alpha" / "A2f" / "A2f-2" / "source"
DONOR = A2 / "A2d" / "item1" / "source"
RESULTS = HERE / "results"
FAMILIES = {
    "geodesic": ("geodesic_N92_r1", 0, 31),
    "rgg": ("rgg_N92_r1", 14, 47),
    "ws": ("ws_N92_r1", 49, 85),
    "er": ("er_N92_r1", 5, 82),
    "ba": ("ba_N92_r1", 5, 72),
}
LIVES = (0.3, 0.5, 0.7, 0.9)
U_COUNTS = {0.3: 36, 0.5: 60, 0.7: 84, 0.9: 108}
SEEDS = {
    0.3: (42, 63, 178, 107, 56),
    0.5: (42, 98, 90, 126, 236),
    0.7: (42, 228, 199, 235, 44),
    0.9: (42, 44, 58, 112, 191),
}
K_GRID = {
    0.3: {"shortest_common": 4, "geometric_midpoint": 3, "longest_common_cap30": 2},
    0.5: {"shortest_common": 7, "geometric_midpoint": 5, "longest_common_cap30": 4},
    0.7: {"shortest_common": 10, "geometric_midpoint": 7, "longest_common_cap30": 5},
    0.9: {"shortest_common": 13, "geometric_midpoint": 9, "longest_common_cap30": 6},
}
PERSISTENCY = 0.75
P_EDGE = 0.5
TRIALS = 3000
TIMEOUT = 60


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def graph_path(family: str) -> Path:
    graph_id = FAMILIES[family][0]
    return A1 / "results" / "edge_lists" / f"{graph_id}.csv"


def load_skeleton(family: str) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    with graph_path(family).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def up_runs(bits: list[bool]) -> int:
    return sum(state and (i == 0 or not bits[i - 1]) for i, state in enumerate(bits))


def transition_count(bits: list[bool]) -> int:
    return sum(bits[i] != bits[i - 1] for i in range(1, len(bits)))


def lexicographic_shortest_path(graph: nx.Graph, source: int, target: int) -> list[int] | None:
    if source not in graph or target not in graph or not nx.has_path(graph, source, target):
        return None
    from_source = nx.single_source_shortest_path_length(graph, source)
    to_target = nx.single_source_shortest_path_length(graph, target)
    distance = from_source[target]
    path = [source]
    current = source
    while current != target:
        choices = [
            node for node in graph.neighbors(current)
            if from_source.get(node) == from_source[current] + 1
            and from_source[node] + to_target.get(node, math.inf) == distance
        ]
        if not choices:
            raise RuntimeError("canonical shortest-path reconstruction failed")
        current = min(choices, key=str)
        path.append(current)
    return path


def store_carry_forward_reachability(frames: list[nx.Graph], source: int, target: int) -> float:
    successes = 0
    for start_layer in range(len(frames)):
        reachable = {source}
        for frame_index in range(start_layer, len(frames)):
            following = set(reachable)  # waiting is always permitted
            for node in reachable:
                following.update(frames[frame_index].neighbors(node))
            reachable = following
        successes += target in reachable
    return successes / len(frames) if frames else 0.0


def config_for(family: str, life: float, target_class: str, seed: int) -> dict:
    graph_id, source, destination = FAMILIES[family]
    U = U_COUNTS[life]
    K = K_GRID[life][target_class]
    return {
        "stage": "A2f-3",
        "preregistration_sha256": sha256(HERE / "prereg.md"),
        "family": family,
        "graph_id": graph_id,
        "graph_edge_list": graph_path(family).relative_to(ROOT).as_posix(),
        "graph_edge_sha256": sha256(graph_path(family)),
        "nodes": 92,
        "source_node": source,
        "destination_node": destination,
        "frames": 120,
        "life": life,
        "U_requested": U,
        "target_class": target_class,
        "K_requested": K,
        "mean_up_duration_requested": U / K,
        "timeline_behavior": "uk",
        "frame_behavior": "patched-v3",
        "persistency": PERSISTENCY,
        "p_edge_pi": P_EDGE,
        "frame_pool_trials": TRIALS,
        "base_seed": seed,
        "timeline_seed": seed,
        "frame_pool_seed": seed + 10000,
        "assembly_seed": seed + 20000,
        "timeout_seconds": TIMEOUT,
        "source_sha256": {
            "a2f2_overlay_timeline": sha256(A2F2_SOURCE / "yadygaga" / "timelineBlockGenerator.py"),
            "a2f2_overlay_init": sha256(A2F2_SOURCE / "yadygaga" / "__init__.py"),
            "a2d1_donor_timeline": sha256(DONOR / "yadygaga" / "timelineBlockGenerator.py"),
            "a2d1_donor_frameGenerator": sha256(DONOR / "yadygaga" / "frameGenerator.py"),
            "a2d1_donor_dynaGraph": sha256(DONOR / "yadygaga" / "dynaGraph.py"),
            "study_runner": sha256(Path(__file__).resolve()),
        },
        "python": sys.version,
        "networkx": nx.__version__,
    }


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def worker(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out_dir = config_path.parent
    try:
        sys.path.insert(0, str(A2F2_SOURCE))
        from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
        from yadygaga.frameGenerator import FrameGenerator
        from yadygaga.dynaGraph import SPCDynamicGraph

        family = config["family"]
        source, destination = config["source_node"], config["destination_node"]
        U, K, seed = config["U_requested"], config["K_requested"], config["timeline_seed"]
        skeleton = load_skeleton(family)
        static_hops = nx.shortest_path_length(skeleton, source, destination)
        generated = SPCTimelineBlockGenerator(
            frames=120,
            seed=seed,
            mode="blocks",
            pathPersistency=PERSISTENCY,
            behavior="uk",
            up_count=U,
            up_runs=K,
        ).generate_blocks()
        bits, path_ids = generated["timeline"], generated["path_ids"]
        realized_U, realized_K = sum(bits), up_runs(bits)
        transitions = transition_count(bits)
        bitstring = "".join("1" if bit else "0" for bit in bits)
        write_json(out_dir / "timeline.json", {
            "bits": bitstring,
            "path_ids": path_ids,
            "sha256": hashlib.sha256(bitstring.encode()).hexdigest(),
            "U_realized": realized_U,
            "K_realized": realized_K,
            "transitions": transitions,
        })

        frame_generator = FrameGenerator()
        frame_generator.generateSPCFrames(
            limited_G=skeleton,
            s=source,
            d=destination,
            trials=TRIALS,
            p_edge=P_EDGE,
            pathPersistency=PERSISTENCY,
            seed=seed + 10000,
            behavior="patched-v3",
            timeline=bits,
            mean_up_duration=U / K,
        )
        up_pool = frame_generator.path_up_frames
        down_pool = frame_generator.path_down_frames
        up_frame_count = sum(len(group) for group in up_pool)
        down_frame_count = len(down_pool)
        write_json(out_dir / "pool_counts.json", {
            "up_group_count": len(up_pool), "up_frame_count": up_frame_count,
            "down_frame_count": down_frame_count,
        })
        if not up_pool or not down_pool or up_frame_count == 0 or down_frame_count == 0:
            raise RuntimeError("required up or down frame pool is empty")

        frames = SPCDynamicGraph().buildDynaGraph(
            generated, up_pool, down_pool, seed=seed + 20000
        )
        if len(frames) != 120:
            raise RuntimeError(f"assembled {len(frames)} frames instead of 120")
        skeleton_edges = {frozenset(edge) for edge in skeleton.edges()}
        frame_rows: list[dict] = []
        edge_rows: list[dict] = []
        connectivity: list[bool] = []
        canonical_routes: list[list[int] | None] = []
        nx_routes: list[list[int] | None] = []
        hop_counts: list[int | None] = []
        all_edges_in_skeleton = True
        for index, graph in enumerate(frames):
            edges = {frozenset(edge) for edge in graph.edges()}
            all_edges_in_skeleton &= edges <= skeleton_edges
            if not edges <= skeleton_edges:
                raise RuntimeError(f"frame {index} contains edge outside A1 skeleton")
            try:
                nx_route = nx.shortest_path(graph, source, destination)
                connected = True
                hops = len(nx_route) - 1
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                nx_route = None
                connected = False
                hops = None
            canonical = lexicographic_shortest_path(graph, source, destination)
            if connected != bool(bits[index]):
                raise RuntimeError(f"timeline/connectivity mask mismatch at frame {index}")
            shortcut = connected and hops < static_hops
            connectivity.append(connected)
            canonical_routes.append(canonical)
            nx_routes.append(nx_route)
            hop_counts.append(hops)
            frame_rows.append({
                "frame": index,
                "timeline_up": bool(bits[index]),
                "instantaneous_sr_connected": connected,
                "hop_count": "NA" if hops is None else hops,
                "shortcut": bool(shortcut),
                "canonical_route": json.dumps(canonical, separators=(",", ":")),
                "networkx_route": json.dumps(nx_route, separators=(",", ":")),
                "edge_count": len(edges),
                "edge_sha256": hashlib.sha256(json.dumps(sorted(tuple(sorted(e)) for e in edges)).encode()).hexdigest(),
            })
            for u, v in sorted((min(edge), max(edge)) for edge in graph.edges()):
                edge_rows.append({"frame": index, "u": u, "v": v})
        write_csv(
            out_dir / "frames.csv", frame_rows,
            ["frame", "timeline_up", "instantaneous_sr_connected", "hop_count", "shortcut", "canonical_route", "networkx_route", "edge_count", "edge_sha256"],
        )
        write_csv(out_dir / "edges.csv", edge_rows, ["frame", "u", "v"])
        uptime = sum(connectivity) / 120
        shortcut_fraction = sum(bool(row["shortcut"]) for row in frame_rows) / 120
        temporal = store_carry_forward_reachability(frames, source, destination)
        up_lengths: list[int] = []
        current = 0
        for state in bits:
            if state:
                current += 1
            elif current:
                up_lengths.append(current)
                current = 0
        if current:
            up_lengths.append(current)
        metrics = {
            **{key: config[key] for key in (
                "family", "graph_id", "life", "U_requested", "target_class",
                "K_requested", "mean_up_duration_requested", "timeline_seed",
                "frame_pool_seed", "assembly_seed",
            )},
            "status": "success",
            "timeline_sha256": hashlib.sha256(bitstring.encode()).hexdigest(),
            "U_realized": realized_U,
            "K_realized": realized_K,
            "mean_up_duration_realized": realized_U / realized_K,
            "up_run_lengths": up_lengths,
            "transition_count": transitions,
            "static_sr_hops": static_hops,
            "instantaneous_sr_uptime_fraction": uptime,
            "instantaneous_sr_mask_exact": connectivity == bits,
            "absolute_life_error": abs(uptime - config["life"]),
            "shortcut_fraction": shortcut_fraction,
            "shortcut_count": sum(bool(row["shortcut"]) for row in frame_rows),
            "time_respecting_reachability_store_carry_forward": temporal,
            "dilution_life_minus_store_carry_forward": config["life"] - temporal,
            "time_respecting_definition": "waiting permitted at each node; descriptive store-carry-forward only",
            "hop_counts_by_frame": hop_counts,
            "canonical_route_sequence": canonical_routes,
            "networkx_route_sequence": nx_routes,
            "canonical_route_sha256": hashlib.sha256(json.dumps(canonical_routes, separators=(",", ":")).encode()).hexdigest(),
            "networkx_route_sha256": hashlib.sha256(json.dumps(nx_routes, separators=(",", ":")).encode()).hexdigest(),
            "up_pool_groups": len(up_pool),
            "up_pool_frame_count": up_frame_count,
            "down_pool_frame_count": down_frame_count,
            "all_edges_in_skeleton": all_edges_in_skeleton,
            "all_frame_shortcuts_zero": shortcut_fraction == 0.0,
            "all_frame_connectivity_matches_timeline": connectivity == bits,
        }
        write_json(out_dir / "trace_metrics.json", metrics)
        write_json(out_dir / "operation_status.json", {"status": "success"})
        return 0
    except Exception as error:
        write_json(out_dir / "operation_status.json", {
            "status": "failed_exception", "exception": repr(error),
            "traceback": traceback.format_exc(),
        })
        return 1


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = ((start + 1) + end) / 2.0
        for pos in range(start, end):
            ranks[order[pos]] = average
        start = end
    return ranks


def spearman_average_ties(x: list[float], y: list[float]) -> float:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("Spearman inputs must have matching length >=2")
    rx, ry = average_ranks(x), average_ranks(y)
    mean_x, mean_y = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(rx, ry))
    denominator = math.sqrt(
        sum((a - mean_x) ** 2 for a in rx) * sum((b - mean_y) ** 2 for b in ry)
    )
    return numerator / denominator


def summarize() -> dict:
    operation_rows: list[dict] = []
    values_by_cell: dict[tuple, list[dict]] = {}
    missing: list[str] = []
    for trace_dir in sorted(path for path in RESULTS.iterdir() if path.is_dir() and path.name.startswith("trace__")):
        config = json.loads((trace_dir / "config.json").read_text())
        status = json.loads((trace_dir / "operation_status.json").read_text()) if (trace_dir / "operation_status.json").exists() else {"status": "missing"}
        metric_file = trace_dir / "trace_metrics.json"
        if status.get("status") != "success" or not metric_file.exists():
            missing.append(trace_dir.name)
            operation_rows.append({"trace": trace_dir.name, "status": status.get("status"), "family": config["family"], "life": config["life"], "target_class": config["target_class"], "seed": config["base_seed"]})
            continue
        metric = json.loads(metric_file.read_text())
        row = {
            "trace": trace_dir.name,
            "status": status["status"],
            "family": config["family"],
            "life": config["life"],
            "target_class": config["target_class"],
            "seed": config["base_seed"],
            "U_requested": config["U_requested"],
            "U_realized": metric["U_realized"],
            "K_requested": config["K_requested"],
            "K_realized": metric["K_realized"],
            "mean_up_duration_requested": config["mean_up_duration_requested"],
            "mean_up_duration_realized": metric["mean_up_duration_realized"],
            "transition_count": metric["transition_count"],
            "instantaneous_sr_uptime_fraction": metric["instantaneous_sr_uptime_fraction"],
            "absolute_life_error": metric["absolute_life_error"],
            "shortcut_fraction": metric["shortcut_fraction"],
            "store_carry_forward_reachability": metric["time_respecting_reachability_store_carry_forward"],
            "dilution": metric["dilution_life_minus_store_carry_forward"],
            "static_sr_hops": metric["static_sr_hops"],
            "up_run_lengths": json.dumps(metric["up_run_lengths"], separators=(",", ":")),
            "timeline_sha256": metric["timeline_sha256"],
            "canonical_route_sha256": metric["canonical_route_sha256"],
            "all_edges_in_skeleton": metric["all_edges_in_skeleton"],
        }
        operation_rows.append(row)
        cell_key = (config["family"], config["life"], config["target_class"])
        values_by_cell.setdefault(cell_key, []).append(row)

    per_trace_fields = list(dict.fromkeys(key for row in operation_rows for key in row))
    write_csv(RESULTS / "per_trace.csv", operation_rows, per_trace_fields)
    cell_rows = []
    numeric = (
        "U_realized", "K_realized", "mean_up_duration_realized", "transition_count",
        "instantaneous_sr_uptime_fraction", "absolute_life_error", "shortcut_fraction",
        "store_carry_forward_reachability", "dilution", "static_sr_hops",
    )
    for key, rows in sorted(values_by_cell.items()):
        entry = {"family": key[0], "life": key[1], "target_class": key[2], "n": len(rows)}
        for field in numeric:
            vals = [float(row[field]) for row in rows]
            entry[f"{field}_mean"] = statistics.mean(vals)
            entry[f"{field}_sd_ddof1"] = statistics.stdev(vals) if len(vals) > 1 else ""
        cell_rows.append(entry)
    cell_fields = list(dict.fromkeys(key for row in cell_rows for key in row))
    write_csv(RESULTS / "cell_summary.csv", cell_rows, cell_fields)

    lives = list(LIVES)
    design_life: list[float] = []
    design_mean: list[float] = []
    for life in lives:
        U = U_COUNTS[life]
        for target_class in ("shortest_common", "geometric_midpoint", "longest_common_cap30"):
            design_life.append(life)
            design_mean.append(U / K_GRID[life][target_class])
    a2a_means = []
    for life in lives:
        U = U_COUNTS[life]
        K = round(1 + (1 - life) * (U - 1))
        a2a_means.append(U / K)
    correlation = {
        "method": "Pearson correlation of average-tie Spearman ranks; independent design cells only",
        "uk_n_unique_cells": len(design_life),
        "uk_life_mean_up_pairs": list(zip(design_life, design_mean)),
        "uk_spearman_life_mean_up": spearman_average_ties(design_life, design_mean),
        "uk_abs_rho_gate": 0.30,
        "uk_gate_pass": abs(spearman_average_ties(design_life, design_mean)) <= 0.30,
        "a2a_n_unique_life_cells": len(lives),
        "a2a_stability_equals_life_K": [round(1 + (1 - life) * (U_COUNTS[life] - 1)) for life in lives],
        "a2a_mean_up_by_life": a2a_means,
        "a2a_spearman_life_mean_up": spearman_average_ties(lives, a2a_means),
        "note": "No family or seed replication is treated as an independent correlation unit.",
    }
    write_json(RESULTS / "spearman.json", correlation)

    success = len([row for row in operation_rows if row.get("status") == "success"])
    all_quota = success == 300 and all(row["U_requested"] == row["U_realized"] and row["K_requested"] == row["K_realized"] for row in operation_rows if row.get("status") == "success")
    all_shortcut_zero = success == 300 and all(float(row["shortcut_fraction"]) == 0.0 for row in operation_rows if row.get("status") == "success")
    all_fidelity = success == 300 and all(float(row["absolute_life_error"]) <= 0.05 for row in operation_rows if row.get("status") == "success")
    summary = {
        "expected_operations": 300,
        "completed_successfully": success,
        "missing_or_failed": missing,
        "all_exact_UK": all_quota,
        "all_shortcut_fractions_zero": all_shortcut_zero,
        "all_life_errors_le_0_05": all_fidelity,
        "uk_spearman": correlation["uk_spearman_life_mean_up"],
        "uk_spearman_gate_pass": correlation["uk_gate_pass"],
        "a2a_spearman": correlation["a2a_spearman_life_mean_up"],
        "operational_pass": success == 300 and all_quota and all_shortcut_zero and all_fidelity and correlation["uk_gate_pass"],
    }
    write_json(RESULTS / "summary.json", summary)
    return summary


def run_parent() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    operation_specs = [
        (family, life, target_class, seed)
        for family in FAMILIES
        for life in LIVES
        for target_class in ("shortest_common", "geometric_midpoint", "longest_common_cap30")
        for seed in SEEDS[life]
    ]
    for family, life, target_class, seed in operation_specs:
        label = f"trace__{family}__life_{life:.1f}__{target_class}__seed_{seed}"
        trace_dir = RESULTS / label
        trace_dir.mkdir(exist_ok=True)
        cfg = config_for(family, life, target_class, seed)
        write_json(trace_dir / "config.json", cfg)
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(trace_dir / "config.json")]
        try:
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT, check=False)
            if completed.returncode != 0:
                if not (trace_dir / "operation_status.json").exists():
                    write_json(trace_dir / "operation_status.json", {
                        "status": "failed_worker", "returncode": completed.returncode,
                        "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:],
                    })
        except subprocess.TimeoutExpired as error:
            write_json(trace_dir / "operation_status.json", {
                "status": "timeout", "timeout_seconds": TIMEOUT,
                "stdout_tail": (error.stdout or b"").decode(errors="replace")[-4000:] if isinstance(error.stdout, bytes) else str(error.stdout or "")[-4000:],
                "stderr_tail": (error.stderr or b"").decode(errors="replace")[-4000:] if isinstance(error.stderr, bytes) else str(error.stderr or "")[-4000:],
            })
        print(f"{label}: {json.loads((trace_dir / 'operation_status.json').read_text()).get('status')}", flush=True)
    summary = summarize()
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["operational_pass"]:
        raise SystemExit("A2f-3 registered gate failed or is incomplete")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        raise SystemExit(worker(args.worker))
    run_parent()


if __name__ == "__main__":
    main()
