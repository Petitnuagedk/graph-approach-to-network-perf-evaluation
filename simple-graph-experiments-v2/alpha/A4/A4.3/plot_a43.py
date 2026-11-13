#!/usr/bin/env python3
"""Create the A4.2-style figure set for the corrected A4.3 N=42 results.

The scope is deliberately N=42 only: no N=92/N=162 performance or architecture
figures are synthesized. Outputs are grouped into three versioned directories.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

FAMILIES = ["ba", "er", "geodesic", "rgg", "ws"]
PROTOCOLS = ["aodv", "olsr"]
PHIS = [1, 2, 3, 4, 5]
COLORS = {"ba": "#0072B2", "er": "#009E73", "geodesic": "#D55E00", "rgg": "#CC79A7", "ws": "#E69F00"}


def finite(row: dict[str, Any], field: str) -> float:
    value = float(row[field])
    if not np.isfinite(value):
        raise ValueError
    return value


def samples(rows: list[dict[str, Any]], field: str) -> list[float]:
    values = []
    for row in rows:
        try:
            values.append(finite(row, field))
        except (KeyError, TypeError, ValueError):
            pass
    return values


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = [dict(row) for row in csv.DictReader(stream)]
    rows = [row for row in rows if row.get("status") in {"success", "reused"}]
    if len(rows) != 50 or any(row.get("N") != "42" for row in rows):
        raise SystemExit(f"Expected 50 corrected N=42 rows, found {len(rows)}")
    return rows


def trend(rows: list[dict[str, Any]], field: str, ylabel: str, output: Path, log_y: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    for protocol in PROTOCOLS:
        for family in FAMILIES:
            means, spreads = [], []
            for phi in PHIS:
                sample = samples([row for row in rows if row["protocol"] == protocol and row["family"] == family and int(row["phi_pct"]) == phi], field)
                means.append(float(np.mean(sample)) if sample else np.nan)
                spreads.append(float(np.std(sample, ddof=1)) if len(sample) > 1 else 0.0)
            ax.errorbar(PHIS, means, yerr=spreads, marker="o", capsize=3, linewidth=1.8,
                        color=COLORS[family], linestyle="-" if protocol == "aodv" else "--",
                        label=f"{family} {protocol.upper()}")
    ax.set_xlabel("Background load φ (%)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(PHIS)
    ax.grid(axis="y", alpha=0.25)
    if log_y:
        ax.set_yscale("log")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.set_title(f"A4.3 N=42: {ylabel} (color = architecture; line = protocol)")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def pdr(rows: list[dict[str, Any]], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    for protocol in PROTOCOLS:
        for family in FAMILIES:
            values = []
            for phi in PHIS:
                sample = samples([row for row in rows if row["protocol"] == protocol and row["family"] == family and int(row["phi_pct"]) == phi], "background_pdr_median")
                values.append(float(np.mean(sample)) if sample else np.nan)
            ax.plot(PHIS, values, marker="o", linewidth=1.8, color=COLORS[family],
                    linestyle="-" if protocol == "aodv" else "--", label=f"{family} {protocol.upper()}")
    ax.set(xlabel="Background load φ (%)", ylabel="Background median PDR", ylim=(0, 1.05), xticks=PHIS)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.set_title("A4.3 N=42 background PDR by graph architecture")
    fig.tight_layout(); fig.savefig(output, dpi=160); plt.close(fig)


def pass_rate(rows: list[dict[str, Any]], output: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 6))
    for protocol in PROTOCOLS:
        for family in FAMILIES:
            rates = []
            for phi in PHIS:
                sample = [row for row in rows if row["protocol"] == protocol and row["family"] == family and int(row["phi_pct"]) == phi]
                rates.append(100 * sum(row.get("pass_criterion") == "pass" for row in sample) / len(sample) if sample else np.nan)
            ax.plot(PHIS, rates, marker="o", linewidth=1.8, color=COLORS[family],
                    linestyle="-" if protocol == "aodv" else "--", label=f"{family} {protocol.upper()}")
    ax.set(xlabel="Background load φ (%)", ylabel="PDR gate pass rate (%)", ylim=(0, 105), xticks=PHIS)
    ax.grid(axis="y", alpha=0.25); ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.set_title("A4.3 N=42 PDR gate pass rate")
    fig.tight_layout(); fig.savefig(output, dpi=160); plt.close(fig)


def read_graph(path: Path) -> nx.Graph:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream); labels = next(reader)
        matrix = np.asarray([[int(value) for value in next(reader)] for _ in labels], dtype=int)
    graph = nx.Graph(); graph.add_nodes_from(range(len(labels)))
    graph.add_edges_from((i, j) for i in range(len(labels)) for j in range(i + 1, len(labels)) if matrix[i, j])
    if matrix.shape != (len(labels), len(labels)) or not np.array_equal(matrix, matrix.T) or not nx.is_connected(graph):
        raise ValueError(f"Invalid connected adjacency matrix: {path}")
    return graph


def gini(values: list[float]) -> float:
    a = np.sort(np.asarray(values, dtype=float)); total = a.sum()
    return float(np.sum((2 * np.arange(1, len(a) + 1) - len(a) - 1) * a) / (len(a) * total)) if len(a) and total else 0.0


def graph_metrics(graph: nx.Graph) -> dict[str, float]:
    degrees = [float(value) for _, value in graph.degree()]
    maximum = max(degrees); denominator = (len(degrees) - 1) * (len(degrees) - 2)
    return {"diameter": float(nx.diameter(graph)), "mean_shortest_path": float(nx.average_shortest_path_length(graph)),
            "clustering": float(nx.average_clustering(graph)), "degree_centralization": float(sum(maximum - x for x in degrees) / denominator) if denominator else 0.0,
            "node_connectivity": float(nx.node_connectivity(graph))}


def characteristics(rows: list[dict[str, Any]], inputs: Path, output_dir: Path) -> None:
    metrics = {family: graph_metrics(read_graph(inputs / f"{family}_N42_r1__F120.csv")) for family in FAMILIES}
    for row in rows: row.update(metrics[row["family"]])
    specs = [("diameter", "Static diameter", "background_pdr_median", "Background median PDR", False, "01_diameter_vs_pdr.png"),
             ("mean_shortest_path", "Mean shortest-path length", "probe_delay_median_s", "Probe delay median (s)", True, "02_path_length_vs_delay.png"),
             ("clustering", "Clustering coefficient", "background_pdr_median", "Background median PDR", False, "03_clustering_vs_pdr.png"),
             ("degree_centralization", "Degree centralization", "control_packets_mean", "Mean control packets", True, "04_centralization_vs_control.png"),
             ("node_connectivity", "Node connectivity", "background_pdr_median", "Background median PDR", False, "05_connectivity_vs_pdr.png")]
    for xfield, xlabel, yfield, ylabel, log_y, filename in specs:
        fig, ax = plt.subplots(figsize=(9, 6))
        for row in rows:
            try: x, y = finite(row, xfield), finite(row, yfield)
            except (KeyError, ValueError): continue
            ax.scatter(x, y, s=54, color=COLORS[row["family"]], marker="o" if row["protocol"] == "aodv" else "s", alpha=0.45 + 0.1 * (int(row["phi_pct"]) == 1), edgecolor="white", linewidth=0.4)
        ax.set(xlabel=xlabel, ylabel=ylabel); ax.grid(alpha=0.25)
        if log_y: ax.set_yscale("log")
        ax.set_title(f"A4.3 N=42 performance versus {xlabel}")
        ax.legend([plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLORS[f], label=f) for f in FAMILIES], FAMILIES, frameon=False, fontsize=8)
        fig.tight_layout(); fig.savefig(output_dir / filename, dpi=160); plt.close(fig)
    with (output_dir / "graph_characteristics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["family", "N", *metrics[FAMILIES[0]].keys()]); writer.writeheader()
        for family in FAMILIES: writer.writerow({"family": family, "N": 42, **metrics[family]})


def architecture(inputs: Path, output_dir: Path) -> None:
    graphs = {family: read_graph(inputs / f"{family}_N42_r1__F120.csv") for family in FAMILIES}
    positions = {family: nx.spring_layout(graph, seed=42, k=1.4 / np.sqrt(42), iterations=250) for family, graph in graphs.items()}
    fig, axes = plt.subplots(1, len(FAMILIES), figsize=(20, 4.4), constrained_layout=True)
    for ax, family in zip(axes, FAMILIES):
        graph = graphs[family]; degrees = np.asarray([graph.degree(node) for node in graph], dtype=float)
        sizes = 16 + 30 * (degrees - degrees.min()) / max(1, degrees.max() - degrees.min())
        nx.draw_networkx_edges(graph, positions[family], ax=ax, edge_color="#7f8c8d", alpha=0.28, width=0.45)
        nx.draw_networkx_nodes(graph, positions[family], ax=ax, node_color=COLORS[family], node_size=sizes, linewidths=0.25, edgecolors="white")
        ax.set_title(f"{family}\nN=42, E={graph.number_of_edges()}"); ax.set_axis_off()
    fig.suptitle("A4.3 static graph architectures, N=42"); fig.savefig(output_dir / "architecture_overview_N42.png", dpi=180, bbox_inches="tight"); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(); root = Path(__file__).resolve().parent
    parser.add_argument("--data", type=Path, default=root / "per_run_amendment_1.csv")
    parser.add_argument("--inputs", type=Path, default=root / "inputs")
    parser.add_argument("--output-dir", type=Path, default=root / "plots_amendment_1")
    args = parser.parse_args(); rows = read_rows(args.data)
    trends = args.output_dir / "plots"; chars = args.output_dir / "graph_characteristic_plots"; arch = args.output_dir / "architecture_plots"
    for directory in (trends, chars, arch): directory.mkdir(parents=True, exist_ok=True)
    pdr(rows, trends / "01_pdr_post_readiness.png")
    trend(rows, "probe_delay_median_s", "Probe delay median (s)", trends / "02_probe_delay_median.png", log_y=True)
    trend(rows, "control_packets_mean", "Mean control packets", trends / "03_control_packets.png")
    trend(rows, "readiness_s", "Readiness time (s)", trends / "04_readiness_time.png")
    pass_rate(rows, trends / "05_pdr_gate_pass_rate.png")
    characteristics(rows, args.inputs, chars); architecture(args.inputs, arch)
    print(f"Read {len(rows)} rows; wrote 11 in-scope A4.3 plots to {args.output_dir}")


if __name__ == "__main__": main()
