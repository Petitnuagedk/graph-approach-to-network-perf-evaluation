#!/usr/bin/env python3
"""Generate Alpha A1 graph-family covariates; no dynamic trace or ns-3 work."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import random
import statistics
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = HERE / "results"
SIZES = (42, 92, 162)
TARGET_DEGREE = 6.0
REJECTION_BUDGET = 1000
WS_P_GRID = (0.01, 0.05, 0.10, 0.20, 0.30, 0.50, 0.80, 1.00)
FAMILY_CODES = {"rgg": 1, "ws": 2, "er": 3, "ba": 4}


class StopCondition(RuntimeError):
    """Raised when a preregistered A1 stop rule is reached."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_geodesic(nu: int) -> nx.Graph:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from icosahedral_geodesic import create_icosahedral_geodesic_graph

    return nx.convert_node_labels_to_integers(
        create_icosahedral_geodesic_graph(nu, 0), ordering="sorted"
    )


def geodesic_verification(graph: nx.Graph, nu: int) -> dict[str, Any]:
    n_expected = 10 * nu * nu + 2
    e_expected = 30 * nu * nu
    degrees = Counter(dict(graph.degree()).values())
    connected = nx.is_connected(graph)
    checks = {
        "N_formula": graph.number_of_nodes() == n_expected,
        "E_formula": graph.number_of_edges() == e_expected,
        "connected": connected,
        "degree_5_exactly_12": degrees[5] == 12,
        "degree_6_all_others": degrees[6] == n_expected - 12,
        "no_other_degrees": sum(degrees.values()) == n_expected
        and set(degrees).issubset({5, 6}),
    }
    return {
        "nu": nu,
        "N_expected": n_expected,
        "N_actual": graph.number_of_nodes(),
        "E_expected": e_expected,
        "E_actual": graph.number_of_edges(),
        "degree_5_vertices": degrees[5],
        "degree_6_vertices": degrees[6],
        "connected": connected,
        "checks": checks,
        "passed": all(checks.values()),
    }


def build_rgg(n: int, seed: int) -> nx.Graph:
    rng = random.Random(seed)
    positions = [(rng.random(), rng.random()) for _ in range(n)]
    radius = math.sqrt(6.0 / (math.pi * (n - 1)))
    graph = nx.Graph()
    graph.add_nodes_from(range(n))
    radius_sq = radius * radius
    for u in range(n):
        x1, y1 = positions[u]
        for v in range(u + 1, n):
            x2, y2 = positions[v]
            dx = min(abs(x1 - x2), 1.0 - abs(x1 - x2))
            dy = min(abs(y1 - y2), 1.0 - abs(y1 - y2))
            if dx * dx + dy * dy <= radius_sq:
                graph.add_edge(u, v)
    graph.graph["radius"] = radius
    return graph


def shortest_path_counts(graph: nx.Graph, source: int) -> tuple[dict[int, int], dict[int, int]]:
    distances = {source: 0}
    counts = {source: 1}
    queue: deque[int] = deque([source])
    while queue:
        node = queue.popleft()
        next_distance = distances[node] + 1
        for neighbor in graph[node]:
            if neighbor not in distances:
                distances[neighbor] = next_distance
                counts[neighbor] = counts[node]
                queue.append(neighbor)
            elif distances[neighbor] == next_distance:
                counts[neighbor] += counts[node]
    return distances, counts


def probe_pair(graph: nx.Graph) -> tuple[int, int, int, int]:
    nodes = sorted(graph.nodes())
    best_key: tuple[int, int] | None = None
    best_pair: tuple[int, int] | None = None
    best_distance = 0
    best_multiplicity = 0
    for index, source in enumerate(nodes[:-1]):
        distances, counts = shortest_path_counts(graph, source)
        for destination in nodes[index + 1 :]:
            distance = distances[destination]
            multiplicity = counts[destination]
            key = (multiplicity, distance)
            if (
                best_key is None
                or key > best_key
                or (key == best_key and (source, destination) < best_pair)
            ):
                best_key = key
                best_pair = (source, destination)
                best_distance = distance
                best_multiplicity = multiplicity
    assert best_pair is not None
    return best_pair[0], best_pair[1], best_distance, best_multiplicity


def degree_gini(degrees: list[int]) -> float:
    n = len(degrees)
    total = sum(degrees)
    if n == 0 or total == 0:
        return 0.0
    abs_sum = sum(abs(a - b) for a in degrees for b in degrees)
    return abs_sum / (2.0 * n * total)


def measure_graph(
    graph: nx.Graph,
    graph_id: str,
    family: str,
    n_target: int,
    realization: int,
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    graph = nx.Graph(graph)
    graph.add_nodes_from(range(n_target))
    connected = nx.is_connected(graph)
    if not connected:
        raise ValueError(f"Cannot measure disconnected accepted graph {graph_id}")
    degrees = [degree for _, degree in graph.degree()]
    source, destination, probe_hops, path_count = probe_pair(graph)
    histogram: Counter[int] = Counter()
    distance_sum = 0
    for node in sorted(graph.nodes()):
        distances, _ = shortest_path_counts(graph, node)
        for other in sorted(graph.nodes()):
            if other > node:
                distance = distances[other]
                histogram[distance] += 1
                distance_sum += distance
    pair_total = n_target * (n_target - 1) // 2
    rows = [
        {
            "graph_id": graph_id,
            "family": family,
            "N_target": n_target,
            "hop_distance": hops,
            "unordered_pair_count": count,
            "pair_fraction": count / pair_total,
        }
        for hops, count in sorted(histogram.items())
    ]
    metadata = dict(metadata)
    mean_degree = sum(degrees) / len(degrees)
    row = {
        "graph_id": graph_id,
        "family": family,
        "N_target": n_target,
        "N": graph.number_of_nodes(),
        "realization": realization,
        "edges": graph.number_of_edges(),
        "mean_degree": mean_degree,
        "max_degree": max(degrees),
        "degree_gini": degree_gini(degrees),
        "diameter": max(histogram),
        "mean_shortest_path_length": distance_sum / pair_total,
        "clustering": nx.average_clustering(graph),
        "connected": connected,
        "probe_S": source,
        "probe_R": destination,
        "probe_hops": probe_hops,
        "probe_equal_shortest_paths": path_count,
        "mean_degree_abs_deviation_from_6": abs(mean_degree - TARGET_DEGREE),
        "flag_mean_degree_deviation_gt_1": abs(mean_degree - TARGET_DEGREE) > 1.0,
        **metadata,
    }
    return row, rows


def make_random_graph(family: str, n: int, seed: int, ws_p: float | None = None) -> nx.Graph:
    if family == "rgg":
        return build_rgg(n, seed)
    if family == "ws":
        if ws_p is None:
            raise ValueError("WS p must be selected before realization generation")
        return nx.watts_strogatz_graph(n, 6, ws_p, seed=seed)
    if family == "er":
        return nx.erdos_renyi_graph(n, 6.0 / (n - 1), seed=seed, directed=False)
    if family == "ba":
        return nx.barabasi_albert_graph(n, 3, seed=seed)
    raise ValueError(f"Unknown random family: {family}")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    geodesics: dict[int, nx.Graph] = {}
    geo_verifications: list[dict[str, Any]] = []
    for nu, n in zip((2, 3, 4), SIZES):
        graph = build_geodesic(nu)
        check = geodesic_verification(graph, nu)
        geo_verifications.append(check)
        if not check["passed"] or graph.number_of_nodes() != n:
            write_csv(
                RESULTS / "geodesic_verification.csv",
                geo_verifications,
                ["nu", "N_expected", "N_actual", "E_expected", "E_actual", "degree_5_vertices", "degree_6_vertices", "connected", "checks", "passed"],
            )
            raise StopCondition(f"Geodesic verification failed at nu={nu}: {check}")
        geodesics[n] = graph
    write_csv(
        RESULTS / "geodesic_verification.csv",
        geo_verifications,
        ["nu", "N_expected", "N_actual", "E_expected", "E_actual", "degree_5_vertices", "degree_6_vertices", "connected", "checks", "passed"],
    )

    ws_calibrations: list[dict[str, Any]] = []
    selected_ws: dict[int, float] = {}
    for n in SIZES:
        geo_diameter = nx.diameter(geodesics[n])
        for grid_index, p in enumerate(WS_P_GRID, start=1):
            seed = 2_000_000 + n * 100 + grid_index
            candidate = nx.watts_strogatz_graph(n, 6, p, seed=seed)
            connected = nx.is_connected(candidate)
            diameter = nx.diameter(candidate) if connected else None
            selected = connected and diameter != geo_diameter
            ws_calibrations.append(
                {
                    "N": n,
                    "nu": SIZES.index(n) + 2,
                    "geodesic_diameter": geo_diameter,
                    "p": p,
                    "grid_index": grid_index,
                    "seed": seed,
                    "connected": connected,
                    "calibration_diameter": diameter,
                    "selected": selected,
                    "status": "selected" if selected else ("disconnected" if not connected else "diameter_matches"),
                }
            )
            if selected:
                selected_ws[n] = p
                break
        if n not in selected_ws:
            write_csv(
                RESULTS / "ws_calibration.csv",
                ws_calibrations,
                ["N", "nu", "geodesic_diameter", "p", "grid_index", "seed", "connected", "calibration_diameter", "selected", "status"],
            )
            raise StopCondition(f"No connected WS candidate with diameter different from geodesic for N={n}")
    write_csv(
        RESULTS / "ws_calibration.csv",
        ws_calibrations,
        ["N", "nu", "geodesic_diameter", "p", "grid_index", "seed", "connected", "calibration_diameter", "selected", "status"],
    )

    covariate_rows: list[dict[str, Any]] = []
    hop_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    attempt_rows: list[dict[str, Any]] = []
    accepted_graphs: list[tuple[str, nx.Graph]] = []
    accepted_seeds: set[int] = set()

    for nu, n in zip((2, 3, 4), SIZES):
        graph = geodesics[n]
        graph_id = f"geodesic_N{n}_r1"
        metadata = {"nu": nu, "seed": "deterministic", "candidate_attempt": 0, "parameter": "class-I"}
        row, histogram = measure_graph(graph, graph_id, "geodesic", n, 1, metadata)
        covariate_rows.append(row)
        hop_rows.extend(histogram)
        accepted_graphs.append((graph_id, graph))
        edge_rows.extend({"graph_id": graph_id, "u": min(u, v), "v": max(u, v)} for u, v in graph.edges())

    for family in ("rgg", "ws", "er", "ba"):
        code = FAMILY_CODES[family]
        for n in SIZES:
            for realization in (1, 2, 3):
                base_seed = 10_000_000 + code * 10_000_000 + n * 10_000 + realization * 1_000
                accepted = False
                for attempt in range(REJECTION_BUDGET):
                    seed = base_seed + attempt
                    p = selected_ws[n] if family == "ws" else None
                    candidate = make_random_graph(family, n, seed, p)
                    connected = nx.is_connected(candidate)
                    attempt_rows.append(
                        {
                            "family": family,
                            "N": n,
                            "realization": realization,
                            "base_seed": base_seed,
                            "attempt": attempt,
                            "candidate_seed": seed,
                            "connected": connected,
                            "accepted": connected,
                            "reason": "accepted" if connected else "disconnected",
                            "parameter": p if family == "ws" else (6.0 / (n - 1) if family == "er" else (math.sqrt(6.0 / (math.pi * (n - 1))) if family == "rgg" else 3)),
                        }
                    )
                    if connected:
                        if seed in accepted_seeds:
                            raise StopCondition(f"Seed collision for accepted graph {family}_N{n}_r{realization}: {seed}")
                        accepted_seeds.add(seed)
                        graph_id = f"{family}_N{n}_r{realization}"
                        metadata = {
                            "nu": "",
                            "seed": seed,
                            "candidate_attempt": attempt,
                            "parameter": p if family == "ws" else (6.0 / (n - 1) if family == "er" else (math.sqrt(6.0 / (math.pi * (n - 1))) if family == "rgg" else 3)),
                        }
                        row, histogram = measure_graph(candidate, graph_id, family, n, realization, metadata)
                        covariate_rows.append(row)
                        hop_rows.extend(histogram)
                        accepted_graphs.append((graph_id, candidate))
                        edge_rows.extend({"graph_id": graph_id, "u": min(u, v), "v": max(u, v)} for u, v in candidate.edges())
                        accepted = True
                        break
                if not accepted:
                    write_csv(
                        RESULTS / "generation_attempts.csv",
                        attempt_rows,
                        ["family", "N", "realization", "base_seed", "attempt", "candidate_seed", "connected", "accepted", "reason", "parameter"],
                    )
                    raise StopCondition(f"Could not generate connected {family} N={n} realization={realization} within {REJECTION_BUDGET} attempts")

    cov_fields = [
        "graph_id", "family", "N_target", "N", "realization", "edges", "mean_degree", "max_degree", "degree_gini", "diameter", "mean_shortest_path_length", "clustering", "connected", "probe_S", "probe_R", "probe_hops", "probe_equal_shortest_paths", "mean_degree_abs_deviation_from_6", "flag_mean_degree_deviation_gt_1", "nu", "seed", "candidate_attempt", "parameter"
    ]
    write_csv(RESULTS / "graph_covariates.csv", covariate_rows, cov_fields)
    write_csv(RESULTS / "hop_distance_distribution.csv", hop_rows, ["graph_id", "family", "N_target", "hop_distance", "unordered_pair_count", "pair_fraction"])
    write_csv(RESULTS / "graph_edges.csv", edge_rows, ["graph_id", "u", "v"])
    write_csv(RESULTS / "generation_attempts.csv", attempt_rows, ["family", "N", "realization", "base_seed", "attempt", "candidate_seed", "connected", "accepted", "reason", "parameter"])

    families = ("geodesic", "rgg", "ws", "er", "ba")
    summary_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []
    family_metrics: dict[tuple[str, int], dict[str, float]] = {}
    for family in families:
        for n in SIZES:
            cell = [row for row in covariate_rows if row["family"] == family and row["N"] == n]
            metric = {
                "mean_degree": statistics.mean(row["mean_degree"] for row in cell),
                "mean_diameter": statistics.mean(row["diameter"] for row in cell),
                "mean_clustering": statistics.mean(row["clustering"] for row in cell),
            }
            family_metrics[(family, n)] = metric
            deviations = [row["mean_degree_abs_deviation_from_6"] for row in cell]
            summary_rows.append(
                {
                    "family": family,
                    "N": n,
                    "realizations": len(cell),
                    "cell_mean_degree": metric["mean_degree"],
                    "cell_degree_min": min(row["mean_degree"] for row in cell),
                    "cell_degree_max": max(row["mean_degree"] for row in cell),
                    "cell_mean_diameter": metric["mean_diameter"],
                    "cell_diameter_min": min(row["diameter"] for row in cell),
                    "cell_diameter_max": max(row["diameter"] for row in cell),
                    "abs_mean_degree_deviation_from_6": abs(metric["mean_degree"] - TARGET_DEGREE),
                    "flag_cell_mean_degree_deviation_gt_1": abs(metric["mean_degree"] - TARGET_DEGREE) > 1.0,
                    "individual_realizations_deviation_gt_1": sum(value > 1.0 for value in deviations),
                    "selected_ws_p": selected_ws[n] if family == "ws" else "",
                }
            )
            flag_rows.append(
                {
                    "family": family,
                    "N": n,
                    "cell_mean_degree": metric["mean_degree"],
                    "absolute_deviation_from_target_6": abs(metric["mean_degree"] - TARGET_DEGREE),
                    "flag_gt_1": abs(metric["mean_degree"] - TARGET_DEGREE) > 1.0,
                    "flagged_graph_ids": ";".join(row["graph_id"] for row in cell if row["mean_degree_abs_deviation_from_6"] > 1.0),
                }
            )
    write_csv(RESULTS / "family_size_summary.csv", summary_rows, ["family", "N", "realizations", "cell_mean_degree", "cell_degree_min", "cell_degree_max", "cell_mean_diameter", "cell_diameter_min", "cell_diameter_max", "abs_mean_degree_deviation_from_6", "flag_cell_mean_degree_deviation_gt_1", "individual_realizations_deviation_gt_1", "selected_ws_p"])
    write_csv(RESULTS / "mean_degree_flags.csv", flag_rows, ["family", "N", "cell_mean_degree", "absolute_deviation_from_target_6", "flag_gt_1", "flagged_graph_ids"])

    mismatch_rows = []
    for n in SIZES:
        for family_a, family_b in itertools.combinations(families, 2):
            a = family_metrics[(family_a, n)]
            b = family_metrics[(family_b, n)]
            mismatch_rows.append(
                {
                    "N": n,
                    "family_a": family_a,
                    "family_b": family_b,
                    "abs_mean_degree_difference": abs(a["mean_degree"] - b["mean_degree"]),
                    "abs_mean_diameter_difference": abs(a["mean_diameter"] - b["mean_diameter"]),
                }
            )
    write_csv(RESULTS / "family_pair_mismatch.csv", mismatch_rows, ["N", "family_a", "family_b", "abs_mean_degree_difference", "abs_mean_diameter_difference"])

    graph_manifest = []
    for graph_id, graph in accepted_graphs:
        edge_path = RESULTS / "edge_lists" / f"{graph_id}.csv"
        write_csv(edge_path, [{"u": min(u, v), "v": max(u, v)} for u, v in graph.edges()], ["u", "v"])
        graph_manifest.append({"graph_id": graph_id, "edge_list": str(edge_path.relative_to(HERE)), "edge_sha256": sha256_file(edge_path), "N": graph.number_of_nodes(), "edges": graph.number_of_edges()})
    (RESULTS / "graph_manifest.json").write_text(json.dumps(graph_manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"accepted_graphs": len(accepted_graphs), "expected_graphs": 39, "ws_p_by_N": selected_ws, "connected_graphs": sum(bool(row["connected"]) for row in covariate_rows), "flags": sum(bool(row["flag_cell_mean_degree_deviation_gt_1"]) for row in summary_rows)}, indent=2))


if __name__ == "__main__":
    main()
