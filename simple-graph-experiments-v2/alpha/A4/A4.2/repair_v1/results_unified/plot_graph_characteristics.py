#!/usr/bin/env python3
"""Relate A4.2 performance to static graph characteristics.

The first frame of each stored graph trace is treated as the static skeleton.
This produces four plots, keeping the total A4.2 plot count below ten when
combined with plot_trends.py's five plots.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

FAMILIES = ["ba", "er", "geodesic", "rgg", "ws"]
FAMILY_COLORS = {
    "ba": "#0072B2",
    "er": "#009E73",
    "geodesic": "#D55E00",
    "rgg": "#CC79A7",
    "ws": "#E69F00",
}
LOADS = ["phi1", "phi5", "phi10"]
LOAD_ALPHA = {"phi1": 1.0, "phi5": 0.72, "phi10": 0.45}


def first_frame_graph(path: Path) -> nx.Graph:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        labels = next(reader)
        # The trace stores one adjacency matrix per frame, stacked vertically.
        # The first matrix is the static skeleton used for these covariates.
        matrix_rows = []
        for _ in labels:
            matrix_rows.append([int(value) for value in next(reader)])
        matrix = np.asarray(matrix_rows, dtype=int)
    if matrix.shape != (len(labels), len(labels)):
        raise ValueError(f"{path}: expected square matrix, got {matrix.shape}")
    if not np.array_equal(matrix, matrix.T):
        raise ValueError(f"{path}: adjacency matrix is not symmetric")
    graph = nx.Graph()
    graph.add_nodes_from(range(len(labels)))
    graph.add_edges_from((i, j) for i in range(len(labels)) for j in range(i + 1, len(labels)) if matrix[i, j])
    if not nx.is_connected(graph):
        raise ValueError(f"{path}: static skeleton is disconnected")
    return graph


def gini(values: list[float]) -> float:
    array = np.sort(np.asarray(values, dtype=float))
    if not len(array) or np.sum(array) == 0:
        return 0.0
    index = np.arange(1, len(array) + 1)
    return float((np.sum((2 * index - len(array) - 1) * array)) / (len(array) * np.sum(array)))


def degree_centralization(graph: nx.Graph) -> float:
    degrees = [float(value) for _, value in graph.degree()]
    maximum = max(degrees)
    numerator = sum(maximum - value for value in degrees)
    n = graph.number_of_nodes()
    denominator = (n - 1) * (n - 2)
    return float(numerator / denominator) if denominator else 0.0


def graph_metrics(graph: nx.Graph) -> dict[str, float]:
    degrees = [float(value) for _, value in graph.degree()]
    betweenness = list(nx.betweenness_centrality(graph, normalized=True).values())
    return {
        "nodes": float(graph.number_of_nodes()),
        "edges": float(graph.number_of_edges()),
        "mean_degree": float(np.mean(degrees)),
        "degree_gini": gini(degrees),
        "diameter": float(nx.diameter(graph)),
        "mean_shortest_path": float(nx.average_shortest_path_length(graph)),
        "clustering": float(nx.average_clustering(graph)),
        "degree_centralization": degree_centralization(graph),
        "mean_betweenness": float(np.mean(betweenness)),
        "node_connectivity": float(nx.node_connectivity(graph)),
    }


def read_results(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("status") == "success"]
    for row in rows:
        row["N"] = int(row["N"])
        row["phi"] = float(row["phi"])
    return rows


def numeric(row: dict[str, Any], field: str) -> float:
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError
    return value


def performance(row: dict[str, Any], field: str) -> tuple[float, bool]:
    """Return value and whether it is a full-window fallback."""
    try:
        return numeric(row, field), False
    except (KeyError, ValueError):
        fallback = {
            "background_pdr_median_post_readiness": "background_pdr_median_full",
            "probe_pdr_post_readiness": "probe_pdr_full",
        }.get(field)
        if fallback is None:
            raise
        return numeric(row, fallback), True


def scatter_plot(
    rows: list[dict[str, Any]],
    metric: str,
    xlabel: str,
    output: Path,
    *,
    y_field: str,
    ylabel: str,
    log_y: bool = False,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    for ax, size in zip(axes, (42, 92, 162)):
        subset = [row for row in rows if row["N"] == size]
        for row in subset:
            try:
                x = row[metric]
                y, fallback = performance(row, y_field)
                x_value = float(x)
            except (KeyError, ValueError):
                continue
            color = FAMILY_COLORS[row["family"]]
            marker = "o" if row["protocol"] == "aodv" else "s"
            ax.scatter(
                x_value,
                y,
                s=54,
                color=color if not fallback else "white",
                edgecolor=color,
                marker=marker,
                alpha=LOAD_ALPHA[row["load_role"]],
                linewidth=1.4,
            )
        ax.set_title(f"N = {size}")
        ax.grid(alpha=0.25)
        if log_y:
            ax.set_yscale("log")
    axes[0].set_ylabel(ylabel)
    axes[1].set_xlabel(xlabel)
    family_handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=FAMILY_COLORS[f], markeredgecolor=FAMILY_COLORS[f], markersize=8, label=f) for f in FAMILIES]
    protocol_handles = [plt.Line2D([0], [0], marker=m, color="black", linestyle="none", markersize=7, label=p.upper()) for p, m in (("aodv", "o"), ("olsr", "s"))]
    load_handles = [plt.Line2D([0], [0], marker="o", color="black", linestyle="none", alpha=alpha, markersize=7, label=load) for load, alpha in LOAD_ALPHA.items()]
    fallback_handle = plt.Line2D([0], [0], marker="o", color="black", markerfacecolor="white", linestyle="none", label="open = full-window fallback")
    axes[-1].legend(handles=family_handles + protocol_handles + load_handles + [fallback_handle], fontsize=7, frameon=False, ncol=2)
    fig.suptitle(f"A4.2 performance versus {xlabel}\ncolor = architecture; marker = protocol; opacity = load")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parent
    parser.add_argument("--data", type=Path, default=default_root / "per_run.csv")
    parser.add_argument("--inputs", type=Path, default=default_root.parent / "inputs")
    parser.add_argument("--output-dir", type=Path, default=default_root / "graph_characteristic_plots")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_results(args.data)
    if len(rows) != 90:
        raise SystemExit(f"Expected 90 successful rows, found {len(rows)}")

    metrics: dict[tuple[str, int], dict[str, float]] = {}
    for family in FAMILIES:
        for size in (42, 92, 162):
            graph = first_frame_graph(args.inputs / f"{family}_N{size}_r1__F120.csv")
            metrics[(family, size)] = graph_metrics(graph)
    fieldnames = ["family", "N", *next(iter(metrics.values())).keys()]
    with (args.output_dir / "graph_characteristics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for (family, size), values in metrics.items():
            writer.writerow({"family": family, "N": size, **values})
    for row in rows:
        row.update(metrics[(row["family"], row["N"])])

    scatter_plot(rows, "diameter", "Static diameter", args.output_dir / "01_diameter_vs_pdr.png", y_field="background_pdr_median_post_readiness", ylabel="Background median PDR")
    scatter_plot(rows, "mean_shortest_path", "Mean shortest-path length", args.output_dir / "02_path_length_vs_delay.png", y_field="probe_delay_median_s", ylabel="Probe delay median (s)", log_y=True)
    scatter_plot(rows, "clustering", "Clustering coefficient", args.output_dir / "03_clustering_vs_pdr.png", y_field="background_pdr_median_post_readiness", ylabel="Background median PDR")
    scatter_plot(rows, "degree_centralization", "Degree centralization", args.output_dir / "04_centralization_vs_control.png", y_field="control_packets_mean", ylabel="Mean control packets", log_y=True)
    scatter_plot(rows, "node_connectivity", "Node connectivity", args.output_dir / "05_connectivity_vs_pdr.png", y_field="background_pdr_median_post_readiness", ylabel="Background median PDR")
    print(f"Read {len(rows)} successful runs; wrote 5 characteristic plots and graph_characteristics.csv to {args.output_dir}")


if __name__ == "__main__":
    main()
