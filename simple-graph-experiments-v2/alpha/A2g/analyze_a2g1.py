#!/usr/bin/env python3
"""Analyze stored A2c/A2f-3 trace provenance and adjacent edge flicker."""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
A2C = ROOT / "alpha" / "A2" / "A2c" / "results"
A2F3 = ROOT / "alpha" / "A2f" / "A2f-3" / "results"
A1 = ROOT / "alpha" / "A1" / "results"
OUT = HERE / "A2g-1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def static_graph(graph_id: str, n: int) -> nx.Graph:
    graph_path = A1 / "edge_lists" / f"{graph_id}.csv"
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    for row in read_csv(graph_path):
        graph.add_edge(int(row["u"]), int(row["v"]))
    return graph


def canonical_path(graph: nx.Graph, source: int, target: int) -> list[int]:
    from_source = nx.single_source_shortest_path_length(graph, source)
    to_target = nx.single_source_shortest_path_length(graph, target)
    distance = from_source[target]
    route = [source]
    while route[-1] != target:
        current = route[-1]
        candidates = [
            node for node in graph.neighbors(current)
            if from_source.get(node) == from_source[current] + 1
            and from_source[node] + to_target.get(node, float("inf")) == distance
        ]
        if not candidates:
            raise RuntimeError(f"canonical route reconstruction failed for {source}-{target}")
        route.append(min(candidates, key=str))
    return route


def edge_states(edge_file: Path, frame_count: int, skeleton_edges: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    frames = [set() for _ in range(frame_count)]
    for row in read_csv(edge_file):
        frame = int(row["frame"])
        edge = tuple(sorted((int(row["u"]), int(row["v"]))))
        if not 0 <= frame < frame_count:
            raise ValueError(f"frame index outside [0,{frame_count}): {frame}")
        if edge not in skeleton_edges:
            raise ValueError(f"non-skeleton edge in {edge_file}: {edge}")
        frames[frame].add(edge)
    return frames


def toggle_rate(frames: list[set[tuple[int, int]]], edge_set: set[tuple[int, int]]) -> float:
    if not edge_set or len(frames) < 2:
        raise ValueError("toggle rate requires nonempty edge set and at least two frames")
    toggles = sum(
        (edge in frames[index]) != (edge in frames[index - 1])
        for index in range(1, len(frames))
        for edge in edge_set
    )
    return toggles / ((len(frames) - 1) * len(edge_set))


def trace_record(config_path: Path, stage: str) -> dict[str, Any]:
    config = read_json(config_path)
    trace_dir = config_path.parent
    status_path = trace_dir / "operation_status.json"
    status = read_json(status_path).get("status") if status_path.exists() else "missing_status"
    record: dict[str, Any] = {
        "stage": stage,
        "trace_dir": trace_dir.relative_to(ROOT).as_posix(),
        "config_sha256": sha256(config_path),
        "operation_status": status,
        "family": config.get("family"),
        "graph_id": config.get("graph_id"),
        "life": config.get("life"),
        "target_class": config.get("target_class", "NA"),
        "seed": config.get("timeline_seed", config.get("base_seed")),
        "frame_count": config.get("frames"),
        "source_node": config.get("source_node"),
        "destination_node": config.get("destination_node"),
        "timeline_behavior": config.get("timeline_behavior", config.get("behavior")),
        "frame_behavior": config.get("frame_behavior", "legacy-iid-frame-pool"),
        "p_edge": config.get("p_edge", config.get("p_edge_pi")),
        "source_sha256": json.dumps(config.get("source_sha256", {}), sort_keys=True),
    }
    if status != "success":
        record["analysis_status"] = "not_successful_operation"
        return record

    n = int(config["nodes"])
    source = int(config["source_node"])
    target = int(config["destination_node"])
    graph = static_graph(str(config["graph_id"]), n)
    graph_path = A1 / "edge_lists" / f"{config['graph_id']}.csv"
    if config.get("graph_edge_sha256") != sha256(graph_path):
        raise ValueError(f"stored graph hash mismatch: {config_path}")
    route = canonical_path(graph, source, target)
    constraint_edges = {tuple(sorted(pair)) for pair in zip(route, route[1:])}
    skeleton_edges = {tuple(sorted(edge)) for edge in graph.edges()}
    frame_count = int(config["frames"])
    edge_file_name = "frame_edges.csv" if stage == "A2c" else "edges.csv"
    edge_file = trace_dir / edge_file_name
    frames = edge_states(edge_file, frame_count, skeleton_edges)
    if not frames:
        raise ValueError(f"empty frame sequence: {edge_file}")
    record.update({
        "analysis_status": "success",
        "graph_edge_sha256": sha256(graph_path),
        "result_edge_file": edge_file.relative_to(ROOT).as_posix(),
        "result_edge_sha256": sha256(edge_file),
        "skeleton_edge_count": len(skeleton_edges),
        "static_canonical_path": json.dumps(route, separators=(",", ":")),
        "constraint_edge_count": len(constraint_edges),
        "nonconstraint_edge_count": len(skeleton_edges - constraint_edges),
        "toggle_all_edges": toggle_rate(frames, skeleton_edges),
        "toggle_constraint_edges": toggle_rate(frames, constraint_edges),
        "toggle_nonconstraint_edges": toggle_rate(frames, skeleton_edges - constraint_edges),
        "source_file_hashes": json.dumps(config.get("source_sha256", {}), sort_keys=True),
    })
    if stage == "A2c":
        p_edge = float(config["p_edge"])
        expected = 2.0 * p_edge * (1.0 - p_edge)
        deviation = abs(float(record["toggle_nonconstraint_edges"]) - expected)
        record["iid_expected_toggle"] = expected
        record["iid_absolute_deviation"] = deviation
        record["h1_row_pass"] = deviation <= 0.05
    else:
        record["iid_expected_toggle"] = "NA"
        record["iid_absolute_deviation"] = "NA"
        record["h1_row_pass"] = "NA"
    return record


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...], value_field: str) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[float]] = defaultdict(list)
    for row in rows:
        if row.get("analysis_status") != "success":
            continue
        groups[tuple(row.get(key) for key in keys)].append(float(row[value_field]))
    out = []
    for key_values, values in sorted(groups.items(), key=lambda item: tuple(map(str, item[0]))):
        out.append({
            **dict(zip(keys, key_values)),
            "n": len(values),
            "mean": statistics.mean(values),
            "sample_sd_ddof1": statistics.stdev(values) if len(values) > 1 else None,
        })
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    a2c_configs = sorted(A2C.glob("*/config.json"))
    a2f3_configs = sorted(A2F3.glob("trace__*/config.json"))
    rows = [trace_record(path, "A2c") for path in a2c_configs]
    rows.extend(trace_record(path, "A2f-3") for path in a2f3_configs)
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "trace_metrics.csv", rows)

    a2c_rows = [row for row in rows if row["stage"] == "A2c"]
    valid_a2c = [row for row in a2c_rows if row.get("analysis_status") == "success"]
    passes = sum(bool(row["h1_row_pass"]) for row in valid_a2c)
    integrity_failures = [row["trace_dir"] for row in a2c_rows if row.get("analysis_status") != "success"]
    h1 = {
        "registered_rows": 300,
        "observed_a2c_configs": len(a2c_configs),
        "valid_rows": len(valid_a2c),
        "row_passes": passes,
        "pass_fraction": passes / len(valid_a2c) if valid_a2c else None,
        "required_fraction": 0.90,
        "row_tolerance": 0.05,
        "integrity_failures": integrity_failures,
        "status": "PASS" if len(valid_a2c) == 300 and passes / 300 >= 0.90 and not integrity_failures else "FAIL",
    }
    summary = {
        "h1": h1,
        "h1_by_p_edge": [
            {
                "p_edge": p_edge,
                "expected_toggle": 2.0 * p_edge * (1.0 - p_edge),
                "n": sum(float(row["p_edge"]) == p_edge for row in valid_a2c),
                "row_passes": sum(
                    float(row["p_edge"]) == p_edge and bool(row["h1_row_pass"])
                    for row in valid_a2c
                ),
            }
            for p_edge in (0.3, 0.5, 0.7)
        ],
        "a2c_overall_nonconstraint_toggle": {
            "mean": statistics.mean(float(row["toggle_nonconstraint_edges"]) for row in valid_a2c),
            "sample_sd_ddof1": statistics.stdev(float(row["toggle_nonconstraint_edges"]) for row in valid_a2c),
        },
        "a2c_by_family_life_p": aggregate(valid_a2c, ("family", "life", "p_edge"), "toggle_nonconstraint_edges"),
        "a2f3_overall_nonconstraint_toggle": {
            "mean": statistics.mean(
                float(row["toggle_nonconstraint_edges"])
                for row in rows if row["stage"] == "A2f-3" and row.get("analysis_status") == "success"
            ),
            "sample_sd_ddof1": statistics.stdev(
                float(row["toggle_nonconstraint_edges"])
                for row in rows if row["stage"] == "A2f-3" and row.get("analysis_status") == "success"
            ),
        },
        "a2f3_by_family_life_target_class": aggregate(
            [row for row in rows if row["stage"] == "A2f-3"],
            ("family", "life", "target_class"),
            "toggle_nonconstraint_edges",
        ),
        "provenance_counts": {
            "A2c_frame_behavior": dict(__import__("collections").Counter(str(row["frame_behavior"]) for row in a2c_rows)),
            "A2f3_frame_behavior": dict(__import__("collections").Counter(str(row["frame_behavior"]) for row in rows if row["stage"] == "A2f-3")),
            "A2f3_timeline_behavior": dict(__import__("collections").Counter(str(row["timeline_behavior"]) for row in rows if row["stage"] == "A2f-3")),
        },
        "a2c_source_hash_sets": sorted({row["source_sha256"] for row in a2c_rows}),
        "a2f3_source_hash_sets": sorted({row["source_sha256"] for row in rows if row["stage"] == "A2f-3"}),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(h1, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
