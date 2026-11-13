#!/usr/bin/env python3
"""Create a small, fixed set of trend plots from unified A4.2 results.

Default output is four PNGs. The script never creates more than 10 plots.
Only successful runs are plotted; readiness flags remain visible in the data
and are reported in the plot subtitles.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

LOADS = ["phi1", "phi5", "phi10"]
LOAD_LABELS = {"phi1": "1%", "phi5": "5%", "phi10": "10%"}
COLORS = {"aodv": "#0072B2", "olsr": "#D55E00"}
FAMILY_COLORS = {
    "ba": "#0072B2",
    "er": "#009E73",
    "geodesic": "#D55E00",
    "rgg": "#CC79A7",
    "ws": "#E69F00",
}


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows = [row for row in rows if row.get("status") == "success"]
    for row in rows:
        row["N"] = int(row["N"])
        row["phi"] = float(row["phi"])
        row["load_order"] = LOADS.index(row["load_role"])
    return rows


def values(rows: list[dict[str, Any]], field: str) -> list[float]:
    result = []
    for row in rows:
        try:
            value = float(row[field])
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(value):
            result.append(value)
    return result


def plot_metric(
    rows: list[dict[str, Any]],
    field: str,
    ylabel: str,
    filename: str,
    *,
    log_y: bool = False,
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    families = [family for family in FAMILY_COLORS if any(row["family"] == family for row in rows)]
    for ax, size in zip(axes, (42, 92, 162)):
        subset = [row for row in rows if row["N"] == size]
        for protocol in ("aodv", "olsr"):
            for family in families:
                means: list[float] = []
                spread: list[float] = []
                for load in LOADS:
                    sample = values(
                        [
                            row for row in subset
                            if row["family"] == family
                            and row["protocol"] == protocol
                            and row["load_role"] == load
                        ],
                        field,
                    )
                    means.append(float(np.mean(sample)) if sample else np.nan)
                    spread.append(float(np.std(sample, ddof=1)) if len(sample) > 1 else 0.0)
                ax.errorbar(
                    np.arange(3),
                    means,
                    yerr=spread,
                    marker="o",
                    linewidth=1.8,
                    capsize=3,
                    color=FAMILY_COLORS[family],
                    linestyle="-" if protocol == "aodv" else "--",
                    label=f"{family} {protocol.upper()}",
                )
        ax.set_title(f"N = {size}")
        ax.set_xticks(range(3), [LOAD_LABELS[load] for load in LOADS])
        ax.grid(axis="y", alpha=0.25)
        if log_y:
            ax.set_yscale("log")
    axes[0].set_ylabel(ylabel)
    handles = [
        plt.Line2D([0], [0], color=FAMILY_COLORS[family], linewidth=2, label=family)
        for family in families
    ] + [
        plt.Line2D([0], [0], color="black", linestyle=style, linewidth=2, label=protocol.upper())
        for protocol, style in (("aodv", "-"), ("olsr", "--"))
    ]
    axes[-1].legend(handles=handles, frameon=False, fontsize=8, ncol=2)
    flagged = sum(row.get("readiness_after_warmup") == "true" for row in rows)
    fig.suptitle(f"A4.2 trend: {ylabel} (color = architecture; line = protocol; readiness flags: {flagged}/{len(rows)})")
    fig.tight_layout()
    fig.savefig(Path(filename), dpi=160)
    plt.close(fig)


def plot_pdr_by_family(rows: list[dict[str, Any]], filename: str) -> None:
    """Plot architecture-specific PDR, with an explicit missing-window fallback.

    Post-readiness PDR is preferred. If a run has no post-readiness window,
    its full-window PDR is plotted as an open marker and dashed segment so the
    value is visible without misrepresenting it as post-readiness evidence.
    """
    families = [family for family in FAMILY_COLORS if any(row["family"] == family for row in rows)]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), sharey=True)
    for ax, size in zip(axes, (42, 92, 162)):
        subset = [row for row in rows if row["N"] == size]
        for protocol, linestyle in (("aodv", "-"), ("olsr", "--")):
            for family in families:
                curve = []
                fallback = []
                for load in LOADS:
                    candidates = [
                        row for row in subset
                        if row["family"] == family
                        and row["protocol"] == protocol
                        and row["load_role"] == load
                    ]
                    if not candidates:
                        curve.append(np.nan)
                        fallback.append(False)
                        continue
                    row = candidates[0]
                    try:
                        post = float(row["background_pdr_median_post_readiness"])
                    except (KeyError, TypeError, ValueError):
                        post = np.nan
                    if np.isfinite(post):
                        curve.append(post)
                        fallback.append(False)
                    else:
                        try:
                            full = float(row["background_pdr_median_full"])
                        except (KeyError, TypeError, ValueError):
                            full = np.nan
                        curve.append(full)
                        fallback.append(True)
                x = np.arange(3)
                color = FAMILY_COLORS[family]
                ax.plot(x, curve, color=color, linestyle=linestyle, linewidth=1.8, marker="o", markersize=4)
                for index, value in enumerate(curve):
                    if fallback[index] and np.isfinite(value):
                        ax.plot(
                            index,
                            value,
                            marker="o",
                            markersize=7,
                            markerfacecolor="white",
                            markeredgecolor=color,
                            markeredgewidth=1.5,
                            linestyle="none",
                        )
        ax.set_title(f"N = {size}")
        ax.set_xticks(range(3), [LOAD_LABELS[load] for load in LOADS])
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Background median PDR")
    family_handles = [
        plt.Line2D([0], [0], color=FAMILY_COLORS[family], marker="o", linewidth=2, label=family)
        for family in families
    ]
    protocol_handles = [
        plt.Line2D([0], [0], color="black", linestyle=style, linewidth=2, label=protocol.upper())
        for protocol, style in (("aodv", "-"), ("olsr", "--"))
    ]
    fallback_handle = plt.Line2D(
        [0], [0], color="black", marker="o", markerfacecolor="white", linestyle="none",
        label="open marker = full-window fallback",
    )
    axes[-1].legend(handles=family_handles + protocol_handles + [fallback_handle], fontsize=8, frameon=False)
    fig.suptitle(
        "A4.2 background PDR by graph architecture\n"
        "Post-readiness values preferred; open markers use full-window PDR when readiness window is empty"
    )
    fig.tight_layout()
    fig.savefig(Path(filename), dpi=160)
    plt.close(fig)


def plot_pass_rate(rows: list[dict[str, Any]], filename: str) -> None:
    families = [family for family in FAMILY_COLORS if any(row["family"] == family for row in rows)]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
    for ax, size in zip(axes, (42, 92, 162)):
        for protocol in ("aodv", "olsr"):
            for family in families:
                rates = []
                for load in LOADS:
                    sample = [
                        row for row in rows
                        if row["N"] == size
                        and row["family"] == family
                        and row["protocol"] == protocol
                        and row["load_role"] == load
                    ]
                    passed = sum(row.get("pdr_gate_full_window") == "pass" for row in sample)
                    rates.append(100 * passed / len(sample) if sample else np.nan)
                ax.plot(
                    np.arange(3), rates, marker="o", linewidth=1.8,
                    color=FAMILY_COLORS[family],
                    linestyle="-" if protocol == "aodv" else "--",
                )
        ax.set_title(f"N = {size}")
        ax.set_xticks(range(3), [LOAD_LABELS[load] for load in LOADS])
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("Full-window PDR gate pass rate (%)")
    axes[0].set_xlabel("Background load")
    handles = [
        plt.Line2D([0], [0], color=FAMILY_COLORS[family], linewidth=2, label=family)
        for family in families
    ] + [
        plt.Line2D([0], [0], color="black", linestyle=style, linewidth=2, label=protocol.upper())
        for protocol, style in (("aodv", "-"), ("olsr", "--"))
    ]
    axes[-1].legend(handles=handles, fontsize=8, frameon=False, ncol=2)
    fig.suptitle("A4.2 PDR gate pass rate (color = architecture; line = protocol)")
    fig.tight_layout()
    fig.savefig(Path(filename), dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("per_run.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("plots"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.data)
    if len(rows) != 90:
        raise SystemExit(f"Expected 90 successful rows, found {len(rows)}")
    plot_pdr_by_family(rows, args.output_dir / "01_pdr_post_readiness.png")
    plot_metric(rows, "probe_delay_median_s", "Probe delay median (s)", args.output_dir / "02_probe_delay_median.png", log_y=True)
    plot_metric(rows, "control_packets_mean", "Mean control packets", args.output_dir / "03_control_packets.png")
    plot_metric(rows, "readiness_s", "Readiness time (s)", args.output_dir / "04_readiness_time.png")
    plot_pass_rate(rows, args.output_dir / "05_pdr_gate_pass_rate.png")
    print(f"Read {len(rows)} successful rows; wrote 5 plots to {args.output_dir}")


if __name__ == "__main__":
    main()
