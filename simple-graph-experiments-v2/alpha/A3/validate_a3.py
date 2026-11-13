#!/usr/bin/env python3
"""Offline A3 acceptance checks over the registered outputs; launches no simulator."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
J2 = STUDY.parent


def read_dicts(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def normalized_csv(path: Path) -> tuple[list[bytes], list[list[bytes]]]:
    lines = path.read_bytes().splitlines()
    if not lines:
        raise ValueError(f"empty CSV: {path}")
    header = lines[0].split(b",")
    drop = {header.index(b"wall_time_s"), header.index(b"cpu_time_s")}
    kept_header = [value for index, value in enumerate(header) if index not in drop]
    rows = []
    for line in lines[1:]:
        if not line:
            continue
        fields = line.split(b",")
        if len(fields) != len(header):
            raise ValueError(f"malformed CSV row in {path}: expected {len(header)}, got {len(fields)}")
        rows.append([value for index, value in enumerate(fields) if index not in drop])
    return kept_header, rows


def main() -> None:
    t1_flow_rows = read_dicts(HERE / "T1" / "flows.csv")
    t1_node_rows = read_dicts(HERE / "T1" / "node_diagnostics.csv")
    t1 = {}
    for protocol in ("olsr", "aodv"):
        flow = next(row for row in t1_flow_rows if row["protocol"] == protocol and row["is_probe"] == "1")
        forwarded = {
            int(row["node_id"]): int(row["value"])
            for row in t1_node_rows
            if row["protocol"] == protocol and row["metric"] == "forwarded_app_packets_ipv4"
        }
        offered = int(flow["offered_packets"])
        delivered = int(flow["delivered_unique_packets"])
        hops = int(flow["static_hop_distance"])
        expected = delivered * max(hops - 1, 0)
        endpoints_zero = forwarded.get(0, 0) == 0 and forwarded.get(3, 0) == 0
        interiors_exact = forwarded.get(1, 0) == delivered and forwarded.get(2, 0) == delivered
        total = sum(forwarded.values())
        t1[protocol] = {
            "offered": offered,
            "delivered_unique": delivered,
            "static_hops": hops,
            "forwarded_by_node": {str(k): v for k, v in sorted(forwarded.items())},
            "forwarded_total": total,
            "expected_delivered_router_forwards": expected,
            "offered_equals_delivered": offered == delivered,
            "endpoints_zero": endpoints_zero,
            "interiors_exact": interiors_exact,
            "forwarded_total_exact": total == expected,
            "pass": offered == delivered and endpoints_zero and interiors_exact and total == expected,
        }
    t1_pass = all(row["pass"] for row in t1.values())

    selftest = json.loads((HERE / "T2" / "a3_selftest.json").read_text(encoding="utf-8"))
    graph_path = J2 / "SG" / "geodesic_adjacency_matrix.csv"
    distance_path = HERE / "T2" / "static_hop_distances.csv"
    with graph_path.open(newline="", encoding="utf-8") as stream:
        matrix = list(csv.reader(stream))
    labels = matrix[0]
    graph = nx.Graph()
    graph.add_nodes_from(labels)
    for i, row in enumerate(matrix[1:]):
        for j in range(i + 1, len(row)):
            if int(row[j]):
                graph.add_edge(labels[i], labels[j])
    distances = dict(nx.all_pairs_shortest_path_length(graph))
    pairs_checked = 0
    for row in read_dicts(distance_path):
        source, destination = row["source"], row["destination"]
        actual = int(row["static_hop_distance"])
        if actual != distances[source][destination]:
            raise AssertionError((source, destination, actual, distances[source][destination]))
        pairs_checked += 1
    expected_pairs = len(labels) * (len(labels) - 1) // 2
    t2_pass = bool(selftest["flow_selection_pass"] and selftest["reverse_direction_observed"]
                   and pairs_checked == expected_pairs)
    t3_pass = bool(selftest["probe_convergence_pass"]
                   and float(selftest["immediate_convergence_s"]) == 10.0
                   and float(selftest["delayed_convergence_s"]) == 24.0
                   and selftest["never_convergence_is_nan"])

    t4_paths = {
        "phase1": STUDY / "phase1" / "static_warm0" / "trace_replay_results.csv",
        "flags_off": HERE / "T4" / "flags_off" / "trace_replay_results.csv",
        "instrumentation_zero": HERE / "T4" / "instrumentation_zero" / "trace_replay_results.csv",
    }
    t4_data = {name: normalized_csv(path) for name, path in t4_paths.items()}
    t4 = {}
    for left, right in (("phase1", "flags_off"), ("phase1", "instrumentation_zero"),
                        ("flags_off", "instrumentation_zero")):
        t4[f"{left}_vs_{right}"] = {
            "identical_after_dropping_only_timing_columns": t4_data[left] == t4_data[right],
            "left_non_timing_columns": len(t4_data[left][0]),
            "right_non_timing_columns": len(t4_data[right][0]),
            "left_rows": len(t4_data[left][1]),
            "right_rows": len(t4_data[right][1]),
        }
    t4_pass = all(item["identical_after_dropping_only_timing_columns"] for item in t4.values())
    summary = {
        "stage": "A3",
        "t1": {"pass": t1_pass, "protocols": t1},
        "t2": {"pass": t2_pass, "flow_selection_pass": selftest["flow_selection_pass"],
              "reverse_direction_observed": selftest["reverse_direction_observed"],
              "networkx_pairs_checked": pairs_checked, "expected_pairs": expected_pairs},
        "t3": {"pass": t3_pass, "immediate_convergence_s": selftest["immediate_convergence_s"],
              "delayed_convergence_s": selftest["delayed_convergence_s"],
              "never_convergence_is_nan": selftest["never_convergence_is_nan"]},
        "t4": {"pass": t4_pass, "comparisons": t4},
        "exact_forwarded_total_gate": all(row["forwarded_total_exact"] for row in t1.values()),
        "overall_pass": t1_pass and t2_pass and t3_pass and t4_pass
                        and all(row["forwarded_total_exact"] for row in t1.values()),
        "protocol_variants_attempted": 8,
        "protocol_variant_cap": 12,
    }
    (HERE / "validation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                                  encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
