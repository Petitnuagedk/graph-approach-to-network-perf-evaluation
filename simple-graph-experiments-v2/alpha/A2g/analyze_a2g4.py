#!/usr/bin/env python3
"""Read-only A2g-4 conditioning distortion analysis of stored A2f-3/A2g-3 frames."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A1 = ROOT / "alpha" / "A1" / "results"
A2F3 = ROOT / "alpha" / "A2f" / "A2f-3" / "results"
A2G3 = HERE / "A2g-3"
PREREG = HERE / "a2g4_prereg.md"
OUT = HERE / "A2g-4"
CUTOFF = 0.05
A2F3_PREREG_SHA256 = "b423370340c38840d403941a86f46dc9f78dbd8064bcff76c3928a86b8f4b477"
A2F3_RUNNER_SHA256 = "438f7c7e5ebfb19d39b5cfa7f317d80065c2c92824829c68db04dcfbd8c69ceb"
A2G3_PREREG_SHA256 = "39247091532fdf0107c4fbfc9ff4b1297aa4eae46a1b0254177920357c44ce98"
A2G3_RUNNER_SHA256 = "9660a8c0685332b2f9bf4db892e4583463743c01f075e02079d146b08ba5a209"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_graph(graph_id: str) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(range(92))
    with (A1 / "edge_lists" / f"{graph_id}.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def canonical_shortest_path(graph: nx.Graph, source: int, target: int) -> list[int]:
    from_source = nx.single_source_shortest_path_length(graph, source)
    to_target = nx.single_source_shortest_path_length(graph, target)
    distance = from_source[target]
    path = [source]
    current = source
    while current != target:
        choices = [
            node for node in graph.neighbors(current)
            if from_source.get(node) == from_source[current] + 1
            and from_source[node] + to_target.get(node, float("inf")) == distance
        ]
        if not choices:
            raise RuntimeError("canonical shortest path reconstruction failed")
        current = min(choices, key=str)
        path.append(current)
    return path


def eligible_edges(graph: nx.Graph, source: int, target: int) -> list[tuple[int, int]]:
    path = canonical_shortest_path(graph, source, target)
    path_edges = {frozenset((u, v)) for u, v in zip(path, path[1:])}
    selected = [
        tuple(sorted((int(u), int(v)))) for u, v in graph.edges()
        if source not in (u, v) and target not in (u, v)
        and frozenset((u, v)) not in path_edges
    ]
    selected.sort()
    if not selected:
        raise RuntimeError("registered background-edge set is empty")
    return selected


def edge_effects(
    graph: nx.Graph, source: int, target: int, bits: list[bool],
    observed: dict[tuple[int, int], list[bool]],
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(bits) != 120 or sum(bits) not in (60, 108):
        raise RuntimeError(f"unexpected timeline size/quota for {metadata['trace_id']}")
    up_n, down_n = sum(bits), len(bits) - sum(bits)
    if up_n == 0 or down_n == 0:
        raise RuntimeError("conditional group has zero frames")
    background = eligible_edges(graph, source, target)
    if set(observed) != set(tuple(sorted(edge)) for edge in graph.edges()):
        raise RuntimeError(f"frame edge-state coverage mismatch for {metadata['trace_id']}")

    per_edge: list[dict[str, Any]] = []
    abs_values: list[float] = []
    signed_values: list[float] = []
    for u, v in background:
        states = observed[(u, v)]
        if len(states) != 120:
            raise RuntimeError(f"incomplete edge timeline for {metadata['trace_id']} {(u, v)}")
        up_rates = [float(state) for state, is_up in zip(states, bits) if is_up]
        down_rates = [float(state) for state, is_up in zip(states, bits) if not is_up]
        rate_up = statistics.mean(up_rates)
        rate_down = statistics.mean(down_rates)
        delta = rate_up - rate_down
        abs_delta = abs(delta)
        abs_values.append(abs_delta)
        signed_values.append(delta)
        per_edge.append({
            **metadata, "u": u, "v": v, "n_sr_up": up_n, "n_sr_down": down_n,
            "edge_up_rate_given_sr_up": rate_up,
            "edge_up_rate_given_sr_down": rate_down,
            "delta_up_minus_down": delta,
            "absolute_conditional_difference": abs_delta,
            "exceeds_0_05": abs_delta > CUTOFF,
        })
    ordered_abs = sorted(abs_values)
    q90_index = min(len(ordered_abs) - 1, int(0.9 * len(ordered_abs)))
    trace = {
        **metadata,
        "eligible_background_edges": len(background),
        "n_sr_up": up_n, "n_sr_down": down_n,
        "mean_absolute_conditional_difference": statistics.mean(abs_values),
        "mean_signed_conditional_difference": statistics.mean(signed_values),
        "median_absolute_conditional_difference": statistics.median(abs_values),
        "p90_absolute_conditional_difference_nearest_rank": ordered_abs[q90_index],
        "fraction_edges_abs_difference_gt_0_05": sum(value > CUTOFF for value in abs_values) / len(abs_values),
        "material_effect_at_trace_level": statistics.mean(abs_values) > CUTOFF,
    }
    return trace, per_edge


def read_a2f3_trace(row: dict[str, str], graph: nx.Graph) -> tuple[list[bool], dict[tuple[int, int], list[bool]], dict[str, Any], list[Path]]:
    trace_id = row["trace"]
    trace_dir = A2F3 / trace_id
    config_path = trace_dir / "config.json"
    metrics_path = trace_dir / "trace_metrics.json"
    frame_path = trace_dir / "frames.csv"
    edge_path = trace_dir / "edges.csv"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if row["status"] != "success" or metrics.get("status") != "success":
        raise RuntimeError(f"A2f-3 source trace failed: {trace_id}")
    if row["target_class"] != "geometric_midpoint" or int(row["K_requested"]) not in (5, 9):
        raise RuntimeError(f"unexpected A2f-3 design cell: {trace_id}")
    expected_u = 60 if float(row["life"]) == 0.5 else 108
    if (config.get("timeline_behavior") != "uk" or config.get("frame_behavior") != "patched-v3"
            or int(config.get("U_requested", -1)) != expected_u
            or int(config.get("K_requested", -1)) != int(row["K_requested"])
            or config.get("preregistration_sha256") != A2F3_PREREG_SHA256
            or config.get("source_sha256", {}).get("study_runner") != A2F3_RUNNER_SHA256
            or config.get("source_node") != {"geodesic": 0, "rgg": 14, "ws": 49, "er": 5, "ba": 5}[row["family"]]
            or config.get("destination_node") != {"geodesic": 31, "rgg": 47, "ws": 85, "er": 82, "ba": 72}[row["family"]]
            or config.get("graph_edge_sha256") != sha256(A1 / "edge_lists" / f"{config['graph_id']}.csv")):
        raise RuntimeError(f"A2f-3 provenance/mode/quota mismatch: {trace_id}")
    frame_rows = read_csv(frame_path)
    edge_rows = read_csv(edge_path)
    if len(frame_rows) != 120:
        raise RuntimeError(f"A2f-3 frame count mismatch: {trace_id}")
    bits = [r["timeline_up"].lower() == "true" for r in frame_rows]
    if sum(bits) != int(row["U_requested"]):
        raise RuntimeError(f"A2f-3 timeline quota mismatch: {trace_id}")
    if any((r["instantaneous_sr_connected"].lower() == "true") != bits[index] for index, r in enumerate(frame_rows)):
        raise RuntimeError(f"A2f-3 S-R mask mismatch: {trace_id}")
    if any(r["shortcut"].lower() == "true" for r in frame_rows) or not metrics.get("all_edges_in_skeleton", False):
        raise RuntimeError(f"A2f-3 path/skeleton integrity mismatch: {trace_id}")
    observed = {tuple(sorted((int(u), int(v)))): [False] * 120 for u, v in graph.edges()}
    for row_edge in edge_rows:
        edge = tuple(sorted((int(row_edge["u"]), int(row_edge["v"]))))
        frame = int(row_edge["frame"])
        if edge not in observed:
            raise RuntimeError(f"out-of-skeleton edge in {trace_id}: {edge}")
        observed[edge][frame] = True
    metadata = {
        "source_stage": "A2f-3", "trace_id": trace_id,
        "family": row["family"], "graph_id": config["graph_id"],
        "life": float(row["life"]), "pi": 0.5, "L": 12.0,
        "seed": int(row["seed"]), "target_class": "geometric_midpoint",
        "timeline_sha256": row["timeline_sha256"],
    }
    return bits, observed, metadata, [config_path, metrics_path, frame_path, edge_path]


def read_a2g3_trace(log_row: dict[str, str], graph: nx.Graph) -> tuple[list[bool], dict[tuple[int, int], list[bool]], dict[str, Any], list[Path]]:
    trace_id = log_row["operation"]
    trace_dir = A2G3 / "operations" / trace_id
    config_path = trace_dir / "config.json"
    metrics_path = trace_dir / "trace_metrics.json"
    timeline_path = trace_dir / "timeline.json"
    states_path = trace_dir / "edge_states.csv.gz"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    if log_row["status"] != "success" or metrics.get("status") != "success":
        raise RuntimeError(f"A2g-3 source trace failed: {trace_id}")
    if not metrics.get("sr_mask_exact") or not metrics.get("all_edges_in_skeleton"):
        raise RuntimeError(f"A2g-3 integrity precondition failed: {trace_id}")
    expected_u, expected_k = (60, 5) if float(config["life"]) == 0.5 else (108, 9)
    if (config.get("timeline_behavior") != "uk" or config.get("edge_sampler_behavior") != "patched-v3"
            or int(config.get("U_requested", -1)) != expected_u
            or int(config.get("K_requested", -1)) != expected_k
            or config.get("preregistration_sha256") != A2G3_PREREG_SHA256
            or config.get("runner_sha256") != A2G3_RUNNER_SHA256
            or config.get("source_node") != {"geodesic": 0, "rgg": 14, "ws": 49, "er": 5, "ba": 5}[config["family"]]
            or config.get("destination_node") != {"geodesic": 31, "rgg": 47, "ws": 85, "er": 82, "ba": 72}[config["family"]]
            or config.get("graph_edge_sha256") != sha256(A1 / "edge_lists" / f"{config['graph_id']}.csv")):
        raise RuntimeError(f"A2g-3 provenance/mode/quota mismatch: {trace_id}")
    bits = [char == "1" for char in timeline["bits"]]
    observed = {tuple(sorted((int(u), int(v)))): [False] * 120 for u, v in graph.edges()}
    rows_read = 0
    with gzip.open(states_path, "rt", newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            edge = tuple(sorted((int(item["u"]), int(item["v"]))))
            frame = int(item["frame"])
            if edge not in observed:
                raise RuntimeError(f"out-of-skeleton edge in {trace_id}: {edge}")
            if (item["timeline_up"].lower() == "true") != bits[frame]:
                raise RuntimeError(f"timeline/state mismatch in {trace_id} at {frame}")
            observed[edge][frame] = item["projected_up"].lower() == "true"
            rows_read += 1
    if rows_read != graph.number_of_edges() * 120:
        raise RuntimeError(f"A2g-3 edge-time row count mismatch: {trace_id}")
    metadata = {
        "source_stage": "A2g-3", "trace_id": trace_id,
        "family": config["family"], "graph_id": config["graph_id"],
        "life": float(config["life"]), "pi": float(config["pi"]),
        "L": float(config["mean_up_duration_edge_L"]), "seed": int(config["timeline_seed"]),
        "target_class": "uk_fixed_12_frame_mean_up",
        "timeline_sha256": timeline["sha256"],
    }
    return bits, observed, metadata, [config_path, metrics_path, timeline_path, states_path]


def summarize_group(rows: list[dict[str, Any]], labels: dict[str, Any]) -> dict[str, Any]:
    values = [float(row["mean_absolute_conditional_difference"]) for row in rows]
    return {
        **labels, "n_traces": len(values), "mean_D_trace": statistics.mean(values) if values else None,
        "sample_sd_D_trace_ddof1": statistics.stdev(values) if len(values) > 1 else None,
        "max_D_trace": max(values) if values else None,
        "material_distortion_flag": bool(values) and statistics.mean(values) > CUTOFF,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    edge_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    input_paths: set[Path] = {PREREG}
    graphs: dict[str, nx.Graph] = {}
    pairs = {"geodesic": (0, 31), "rgg": (14, 47), "ws": (49, 85), "er": (5, 82), "ba": (5, 72)}

    a2f3_index = read_csv(A2F3 / "per_trace.csv")
    input_paths.add(A2F3 / "per_trace.csv")
    selected_a2f3 = [
        row for row in a2f3_index
        if row["target_class"] == "geometric_midpoint" and float(row["life"]) in (0.5, 0.9)
    ]
    if len(selected_a2f3) != 50:
        raise RuntimeError(f"expected 50 A2f-3 selected traces, found {len(selected_a2f3)}")
    for row in selected_a2f3:
        family = row["family"]
        graph_id = f"{family}_N92_r1"
        if graph_id not in graphs:
            graphs[graph_id] = load_graph(graph_id)
        input_paths.add(A1 / "edge_lists" / f"{graph_id}.csv")
        graph = graphs[graph_id]
        source, target = pairs[family]
        bits, observed, metadata, paths = read_a2f3_trace(row, graph)
        input_paths.update(paths)
        metrics, by_edge = edge_effects(graph, source, target, bits, observed, metadata)
        trace_rows.append(metrics)
        edge_rows.extend(by_edge)

    a2g3_log = read_csv(A2G3 / "operation_log.csv")
    input_paths.add(A2G3 / "operation_log.csv")
    if len(a2g3_log) != 90 or any(row["status"] != "success" for row in a2g3_log):
        raise RuntimeError("A2g-3 source ledger is incomplete or has a failed cell")
    for row in a2g3_log:
        family = row["family"]
        graph_id = row["graph_id"]
        if graph_id not in graphs:
            graphs[graph_id] = load_graph(graph_id)
        input_paths.add(A1 / "edge_lists" / f"{graph_id}.csv")
        graph = graphs[graph_id]
        source, target = pairs[family]
        bits, observed, metadata, paths = read_a2g3_trace(row, graph)
        input_paths.update(paths)
        metrics, by_edge = edge_effects(graph, source, target, bits, observed, metadata)
        trace_rows.append(metrics)
        edge_rows.extend(by_edge)

    if len(trace_rows) != 140:
        raise RuntimeError(f"expected 140 trace rows, found {len(trace_rows)}")
    a2f_groups: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    a2g_groups: dict[tuple[str, float, float, float], list[dict[str, Any]]] = defaultdict(list)
    broad_groups: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    parameter_groups: dict[tuple[float, float, float], list[dict[str, Any]]] = defaultdict(list)
    for row in trace_rows:
        broad_groups[(row["source_stage"], float(row["life"]))].append(row)
        if row["source_stage"] == "A2f-3":
            a2f_groups[(row["family"], float(row["life"]))].append(row)
        else:
            a2g_groups[(row["family"], float(row["life"]), float(row["pi"]), float(row["L"]))].append(row)
            parameter_groups[(float(row["life"]), float(row["pi"]), float(row["L"]))].append(row)

    fine_rows = []
    for (family, life), group in sorted(a2f_groups.items()):
        fine_rows.append(summarize_group(group, {"source_stage": "A2f-3", "family": family, "life": life, "pi": 0.5, "L": 12.0}))
    for (family, life, pi, duration), group in sorted(a2g_groups.items()):
        fine_rows.append(summarize_group(group, {"source_stage": "A2g-3", "family": family, "life": life, "pi": pi, "L": duration}))
    broad_rows = [
        summarize_group(group, {"source_stage": source, "life": life})
        for (source, life), group in sorted(broad_groups.items())
    ]
    parameter_rows = [
        summarize_group(group, {"source_stage": "A2g-3", "life": life, "pi": pi, "L": duration})
        for (life, pi, duration), group in sorted(parameter_groups.items())
    ]

    write_csv(OUT / "per_edge_conditioning.csv", edge_rows)
    write_csv(OUT / "per_trace_conditioning.csv", trace_rows)
    write_csv(OUT / "fine_stratum_summary.csv", fine_rows)
    write_csv(OUT / "broad_summary.csv", broad_rows)
    write_csv(OUT / "parameter_summary.csv", parameter_rows)
    write_json(OUT / "summary.json", {
        "stage": "A2g-4", "cutoff_absolute_availability": CUTOFF,
        "material_distortion_definition": "fine-stratum mean of per-trace mean absolute edge conditional differences > 0.05",
        "trace_count": len(trace_rows), "a2f3_trace_count": len(selected_a2f3),
        "a2g3_trace_count": len(a2g3_log),
        "eligible_edge_trace_rows": len(edge_rows),
        "flagged_fine_strata": sum(bool(row["material_distortion_flag"]) for row in fine_rows),
        "fine_strata": len(fine_rows), "fine_stratum_results": fine_rows,
        "broad_results": broad_rows,
        "a2g3_parameter_results": parameter_rows,
        "interpretation": "descriptive conditional availability contrast; not causal, inferential, or protocol performance evidence",
    })
    manifest = []
    for path in sorted(input_paths):
        manifest.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "role": "preregistration" if path == PREREG else "input"})
    write_csv(OUT / "input_manifest.csv", manifest)
    output_manifest = []
    for path in sorted(OUT.glob("*")):
        if path.is_file() and path.name != "artifact_manifest.csv":
            output_manifest.append({"path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(OUT / "artifact_manifest.csv", output_manifest)
    print(json.dumps({
        "trace_count": len(trace_rows), "fine_strata": len(fine_rows),
        "flagged_fine_strata": sum(bool(row["material_distortion_flag"]) for row in fine_rows),
        "maximum_trace_mean_absolute_difference": max(float(row["mean_absolute_conditional_difference"]) for row in trace_rows),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
