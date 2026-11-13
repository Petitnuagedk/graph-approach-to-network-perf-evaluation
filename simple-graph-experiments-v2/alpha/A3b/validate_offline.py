#!/usr/bin/env python3
"""Verify unchanged A3 T2/T3 offline checks without launching a protocol run."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import networkx as nx

A3B = Path(__file__).resolve().parent
J2 = A3B.parents[2]
INPUT = J2 / "SG" / "geodesic_adjacency_matrix.csv"


def main() -> None:
    with INPUT.open(newline="", encoding="utf-8") as stream:
        matrix = list(csv.reader(stream))
    labels = matrix[0]
    graph = nx.Graph()
    graph.add_nodes_from(labels)
    for source, row in enumerate(matrix[1:]):
        if len(row) != len(labels):
            raise AssertionError(f"matrix row {source} has {len(row)} entries; expected {len(labels)}")
        for destination in range(source + 1, len(labels)):
            if int(row[destination]):
                graph.add_edge(labels[source], labels[destination])
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    distance_file = A3B / "T2T3" / "static_hop_distances.csv"
    with distance_file.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    checked = 0
    for row in rows:
        source, destination = row["source"], row["destination"]
        actual = int(row["static_hop_distance"])
        expected = distances[source][destination]
        if actual != expected:
            raise AssertionError(f"{source}->{destination}: {actual} != {expected}")
        checked += 1
    expected_pairs = len(labels) * (len(labels) - 1) // 2
    if checked != expected_pairs:
        raise AssertionError(f"checked {checked} unique unordered pairs; expected {expected_pairs}")

    selftest = json.loads((A3B / "T2T3" / "a3_selftest.json").read_text(encoding="utf-8"))
    selection_pass = bool(selftest["flow_selection_pass"] and selftest["reverse_direction_observed"])
    convergence_pass = bool(
        selftest["probe_convergence_pass"]
        and float(selftest["immediate_convergence_s"]) == 10.0
        and float(selftest["delayed_convergence_s"]) == 24.0
        and selftest["never_convergence_is_nan"]
    )
    summary = {
        "T2_flow_selection": "PASS" if selection_pass else "FAIL",
        "T2_networkx_distance_pairs": checked,
        "T2_expected_unique_unordered_pairs": expected_pairs,
        "T2_static_distances": "PASS" if checked == expected_pairs else "FAIL",
        "T3_convergence": "PASS" if convergence_pass else "FAIL",
        "T3_immediate_convergence_s": selftest["immediate_convergence_s"],
        "T3_delayed_convergence_s": selftest["delayed_convergence_s"],
        "T3_never_converges_is_nan": selftest["never_convergence_is_nan"],
        "overall_pass": selection_pass and convergence_pass and checked == expected_pairs,
    }
    (A3B / "offline_validation.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
