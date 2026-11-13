#!/usr/bin/env python3
"""Visualize the static graph architectures used by A4.2.

The stored inputs contain frame-stacked adjacency matrices. This tool plots
only the first frame (the static skeleton), without changing experiment data.
It creates two 2-D architecture comparisons and one 3-D geodesic view.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401: registers 3-D projection

FAMILIES = ["ba", "er", "geodesic", "rgg", "ws"]
COLORS = {
    "ba": "#0072B2",
    "er": "#009E73",
    "geodesic": "#D55E00",
    "rgg": "#CC79A7",
    "ws": "#E69F00",
}
LABELS = {"ba": "Barabási–Albert", "er": "Erdős–Rényi", "geodesic": "Geodesic", "rgg": "Random geometric", "ws": "Watts–Strogatz"}


def read_graph(path: Path) -> nx.Graph:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        labels = next(reader)
        rows = [[int(value) for value in next(reader)] for _ in labels]
    matrix = np.asarray(rows, dtype=int)
    if matrix.shape != (len(labels), len(labels)) or not np.array_equal(matrix, matrix.T):
        raise ValueError(f"Invalid first-frame adjacency matrix: {path}")
    graph = nx.Graph()
    graph.add_nodes_from(range(len(labels)))
    graph.add_edges_from((i, j) for i in range(len(labels)) for j in range(i + 1, len(labels)) if matrix[i, j])
    if not nx.is_connected(graph):
        raise ValueError(f"Disconnected static graph: {path}")
    return graph


def positions(graphs: dict[str, nx.Graph], seed: int) -> dict[str, dict[int, np.ndarray]]:
    return {family: nx.spring_layout(graph, seed=seed, k=1.4 / np.sqrt(graph.number_of_nodes()), iterations=250) for family, graph in graphs.items()}


def plot_overview(graphs: dict[str, nx.Graph], output: Path, title: str) -> None:
    pos = positions(graphs, seed=42)
    fig, axes = plt.subplots(1, len(FAMILIES), figsize=(20, 4.4), constrained_layout=True)
    for ax, family in zip(axes, FAMILIES):
        graph = graphs[family]
        degrees = np.asarray([graph.degree(node) for node in graph], dtype=float)
        sizes = 16 + 30 * (degrees - degrees.min()) / max(1, degrees.max() - degrees.min())
        nx.draw_networkx_edges(graph, pos[family], ax=ax, edge_color="#7f8c8d", alpha=0.28, width=0.45)
        nx.draw_networkx_nodes(graph, pos[family], ax=ax, node_color=COLORS[family], node_size=sizes, linewidths=0.25, edgecolors="white")
        ax.set_title(f"{LABELS[family]}\nN={graph.number_of_nodes()}, E={graph.number_of_edges()}", fontsize=10)
        ax.set_axis_off()
    fig.suptitle(title, fontsize=15)
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_geodesic_3d(graph: nx.Graph, output: Path) -> None:
    # A force-directed 3-D embedding is used because the CSV contains topology,
    # not geographic coordinates. It is normalized onto a sphere for readability.
    pos = nx.spring_layout(graph, dim=3, seed=42, iterations=500)
    coordinates = np.asarray([pos[node] for node in graph])
    coordinates /= np.maximum(np.linalg.norm(coordinates, axis=1, keepdims=True), 1e-12)
    xyz = {node: coordinates[index] for index, node in enumerate(graph)}
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(111, projection="3d")
    for left, right in graph.edges():
        ax.plot(*zip(xyz[left], xyz[right]), color="#7f8c8d", alpha=0.22, linewidth=0.45)
    degrees = np.asarray([graph.degree(node) for node in graph], dtype=float)
    ax.scatter(coordinates[:, 0], coordinates[:, 1], coordinates[:, 2], c=degrees, cmap="YlOrRd", s=8 + 18 * degrees / degrees.max(), depthshade=True)
    ax.set_title("Geodesic architecture, N=162\n3-D force-directed topology view normalized onto a sphere")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent
    parser.add_argument("--inputs", type=Path, default=root.parent / "inputs")
    parser.add_argument("--output-dir", type=Path, default=root / "architecture_plots")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for size in (42, 162):
        graphs = {family: read_graph(args.inputs / f"{family}_N{size}_r1__F120.csv") for family in FAMILIES}
        plot_overview(graphs, args.output_dir / f"architecture_overview_N{size}.png", f"A4.2 static graph architectures, N={size}")
    geodesic = read_graph(args.inputs / "geodesic_N162_r1__F120.csv")
    plot_geodesic_3d(geodesic, args.output_dir / "geodesic_N162_3d.png")
    print(f"Wrote 3 architecture plots to {args.output_dir}")


if __name__ == "__main__":
    main()
