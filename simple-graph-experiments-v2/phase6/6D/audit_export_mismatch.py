#!/usr/bin/env python3
"""Rebuild Phase 2 DG with its recorded seed and diff every pre-export frame."""
from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path
import sys

import networkx as nx

ROOT = Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "simple-graph-experiments-v2" / "phase2" / "final"
DG_SCRIPT = ROOT / "G2DG-SPC.py"
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from oracle_metrics import _shortest_path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def serialized_frames(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    labels = [label.strip() for label in rows[0]]
    frames = []
    matrix = []
    for row in rows[1:]:
        if not row or not any(value.strip() for value in row):
            if matrix:
                frames.append(matrix)
                matrix = []
        else:
            matrix.append([int(value) for value in row])
    if matrix:
        frames.append(matrix)
    return labels, frames


def shortest_route(graph: nx.Graph, source: str, destination: str):
    try:
        return tuple(nx.shortest_path(graph, source, destination))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def main() -> None:
    dg = load_module(DG_SCRIPT, "phase6_reproduce_spc")
    base_graph = dg.load_graph_from_adj_csv(str(PHASE2 / "graph.csv"))
    generated, stats = dg.build_dynamic_graph(
        base_graph, "S", "R", trials=1000, p_edge=0.5,
        pathPersistency=0.75, frames=60, path_life=0.9,
        stability=0.8, seed=42,
    )
    if generated is None:
        raise RuntimeError("Seed-42 DG reproduction returned no graph")
    graphs = generated.DynamicGraph
    csv_labels, matrices = serialized_frames(PHASE2 / "dynamic_frames/graph_0001/frames.csv")
    differences = []
    serialized_routes = []
    for index, (graph, matrix) in enumerate(zip(graphs, matrices)):
        changed = []
        for i, left in enumerate(csv_labels):
            for j in range(i + 1, len(csv_labels)):
                right = csv_labels[j]
                in_memory = int(graph.has_edge(left, right))
                exported = matrix[i][j]
                if in_memory != exported:
                    changed.append((left, right, in_memory, exported))
        if changed:
            differences.append((index, changed))
        serialized_routes.append(_shortest_path(matrix, csv_labels.index("S"), csv_labels.index("R")))

    routes = [shortest_route(graph, "S", "R") for graph in graphs]
    changes = sum(a is not None and b is not None and a != b
                  for a, b in zip(routes, routes[1:]))
    comparisons = [(a, b) for a, b in zip(routes, routes[1:])
                   if a is not None and b is not None]
    retention = (sum(a == b for a, b in comparisons) / len(comparisons)
                 if comparisons else float("nan"))
    serialized_paths = [tuple(csv_labels[node] for node in path) if path is not None else None
                        for path in serialized_routes]
    serialized_comparisons = [(a, b) for a, b in zip(serialized_paths, serialized_paths[1:])
                              if a is not None and b is not None]
    serialized_changes = sum(a != b for a, b in serialized_comparisons)
    serialized_retention = (sum(a == b for a, b in serialized_comparisons) /
                            len(serialized_comparisons) if serialized_comparisons else float("nan"))
    route_choice_differences = [
        (index, route, serialized_paths[index])
        for index, route in enumerate(routes) if route != serialized_paths[index]
    ]
    assert len(graphs) == len(matrices) == 60
    assert not differences, "pre-export graph edges differ from serialized frames"
    assert math.isclose(retention, 0.851063829787234)
    assert changes == 7
    assert math.isclose(serialized_retention, 0.7446808510638298)
    assert serialized_changes == 12
    print("generation_stats", stats)
    print("preexport_frames", len(graphs), "serialized_frames", len(matrices),
          "serialized_node_order", csv_labels)
    print("preexport_retention", retention, "preexport_route_changes", changes)
    print("mismatching_frames", len(differences), "total_edge_cell_differences",
          sum(len(items) for _, items in differences))
    print("serialized_retention", serialized_retention,
          "serialized_route_changes", serialized_changes)
    print("shortest_route_tie_break_differences", len(route_choice_differences))
    for index, before, after in route_choice_differences:
        print("route_choice", index, "generator_order", before, "serialized_label_order", after)
    for index, changed in differences[:10]:
        print("frame", index, "changed_edges", changed)

    output = OUT / "export_frame_diff.csv"
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "node_a", "node_b", "preexport_edge", "serialized_edge"])
        for index, changed in differences:
            for left, right, before, after in changed:
                writer.writerow([index, left, right, before, after])

    with (OUT / "route_choice_diff.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame", "generator_order_shortest_route", "serialized_label_order_shortest_route"])
        for index, before, after in route_choice_differences:
            writer.writerow([index, " -> ".join(before) if before else "",
                             " -> ".join(after) if after else ""])

    summary = {
        "reproduced_seed": 42,
        "frames_preexport": len(graphs),
        "frames_serialized": len(matrices),
        "edge_mismatch_frames": len(differences),
        "edge_cell_differences": sum(len(items) for _, items in differences),
        "generator_order_retention": retention,
        "generator_order_route_changes": changes,
        "serialized_label_order_retention": serialized_retention,
        "serialized_label_order_route_changes": serialized_changes,
        "frames_with_shortest_route_choice_difference": len(route_choice_differences),
        "cause": "Shortest-path tie-breaking depends on node insertion/order; serialization sorts node labels, while generator-side NetworkX traversal follows graph insertion order. The graph edges are identical frame by frame.",
    }
    (OUT / "export_diff_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
