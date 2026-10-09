#!/usr/bin/env python3
"""Read-only Phase 5 S-R timeline diversity audit for Phase 6C."""
from __future__ import annotations

import csv
import itertools
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE5 = ROOT / "simple-graph-experiments-v2" / "phase5"
OUT = Path(__file__).resolve().parent
TOPOLOGIES = ("line", "ladder", "two-lines")
PARAMS = ("pathPersistency", "path_life", "stability")


def load_timeline(path: Path) -> tuple[list[str], list[bool]]:
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    header_index = next(i for i, row in enumerate(rows) if row and any(v.strip() for v in row))
    labels = [value.strip() for value in rows[header_index]]
    s_idx, r_idx = labels.index("S"), labels.index("R")
    matrices: list[list[list[int]]] = []
    matrix: list[list[int]] = []
    for row in rows[header_index + 1 :]:
        if not row or not any(value.strip() for value in row):
            if matrix:
                matrices.append(matrix)
                matrix = []
        else:
            matrix.append([int(value) for value in row])
    if matrix:
        matrices.append(matrix)

    connected: list[bool] = []
    for graph in matrices:
        seen = {s_idx}
        todo = [s_idx]
        while todo:
            node = todo.pop()
            for neighbor, is_up in enumerate(graph[node]):
                if is_up and neighbor not in seen:
                    seen.add(neighbor)
                    todo.append(neighbor)
        connected.append(r_idx in seen)
    return labels, connected


def runs(bits: list[bool], value: bool) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    start = None
    for i, bit in enumerate(bits + [not value]):
        if bit == value and start is None:
            start = i
        elif bit != value and start is not None:
            result.append((start, i - start))
            start = None
    return result


def variance(values: list[float]) -> float:
    return statistics.variance(values) if len(values) > 1 else float("nan")


def main() -> None:
    timelines: dict[tuple[str, str, str, str], list[bool]] = {}
    detail_rows = []
    for topology in TOPOLOGIES:
        for parameter in PARAMS:
            base = PHASE5 / topology / parameter / "dynamic_frames"
            for graph_id in sorted(p.name for p in base.iterdir() if p.is_dir() and p.name.startswith("graph_")):
                graph_dir = base / graph_id
                for trace_dir in sorted(p for p in graph_dir.iterdir() if p.is_dir()):
                    frames_path = trace_dir / "frames.csv"
                    labels, bits = load_timeline(frames_path)
                    timeline_key = (topology, parameter, graph_id, trace_dir.name)
                    timelines[timeline_key] = bits
                    ups, downs = runs(bits, True), runs(bits, False)
                    detail_rows.append({
                        "topology": topology, "parameter": parameter,
                        "cell": trace_dir.name, "graph_id": graph_id,
                        "frame_count": len(bits), "node_count": len(labels),
                        "sr_up_frames": sum(bits), "sr_uptime": sum(bits) / len(bits),
                        "distinct_timeline_cell_pending": "",
                        "up_run_count": len(ups), "outage_count": len(downs),
                        "up_run_lengths_frames": ";".join(str(length) for _, length in ups),
                        "outage_start_frames": ";".join(str(start) for start, _ in downs),
                        "frames_path": str(frames_path.relative_to(ROOT)),
                    })

    by_cell: dict[tuple[str, str, str], list[list[bool]]] = {}
    for (topology, parameter, graph_id, cell), bits in timelines.items():
        by_cell.setdefault((topology, parameter, cell), []).append(bits)
    summary_rows = []
    for (topology, parameter, cell), traces in sorted(by_cell.items()):
        unique = len({tuple(bits) for bits in traces})
        hamming = [sum(a != b for a, b in zip(left, right)) / len(left)
                   for left, right in itertools.combinations(traces, 2)]
        up_runs = [length for bits in traces for _, length in runs(bits, True)]
        outage_starts = [start for bits in traces for start, _ in runs(bits, False)]
        per_trace_up_means = [statistics.mean(length for _, length in runs(bits, True))
                              if runs(bits, True) else float("nan") for bits in traces]
        per_trace_outage_means = [statistics.mean(start for start, _ in runs(bits, False))
                                  if runs(bits, False) else float("nan") for bits in traces]
        up_counts = [sum(bits) for bits in traces]
        summary_rows.append({
            "topology": topology, "parameter": parameter, "cell": cell,
            "realizations": len(traces), "distinct_timelines": unique,
            "mean_pairwise_hamming_frames": statistics.mean(hamming) if hamming else 0,
            "uptime_frames_min": min(up_counts), "uptime_frames_max": max(up_counts),
            "uptime_frames_sample_sd": statistics.stdev(up_counts) if len(up_counts) > 1 else 0,
            "pooled_up_run_length_variance_frames2": variance(up_runs),
            "pooled_outage_start_variance_frames2": variance(outage_starts),
            "per_realization_mean_up_run_variance_frames2": variance([x for x in per_trace_up_means if x == x]),
            "per_realization_mean_outage_start_variance_frames2": variance([x for x in per_trace_outage_means if x == x]),
        })

    comparisons = []
    groups: dict[tuple[str, str, str], dict[str, list[bool]]] = {}
    for (topology, parameter, graph_id, cell), bits in timelines.items():
        groups.setdefault((parameter, cell, graph_id), {})[topology] = bits
    for (parameter, cell, graph_id), values in sorted(groups.items()):
        for left, right in itertools.combinations(TOPOLOGIES, 2):
            a, b = values.get(left), values.get(right)
            comparisons.append({
                "parameter": parameter, "cell": cell, "graph_id": graph_id,
                "topology_a": left, "topology_b": right,
                "both_present": a is not None and b is not None,
                "exactly_equal": a == b if a is not None and b is not None else "NA",
                "hamming_frames": sum(x != y for x, y in zip(a, b)) if a is not None and b is not None else "NA",
            })

    with (OUT / "timeline_details.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail_rows[0]))
        writer.writeheader()
        writer.writerows(detail_rows)
    with (OUT / "cell_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    with (OUT / "cross_topology_seed_equality.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)

    print(f"traces={len(detail_rows)} cells={len(summary_rows)} cross-topology-pairs={len(comparisons)}")
    print(f"exact_equal={sum(row['exactly_equal'] is True for row in comparisons)} / "
          f"{sum(row['both_present'] for row in comparisons)} present comparisons")
    print("Cell diversity summary (topology, parameter, cell, distinct, mean Hamming, uptime min/max):")
    for row in summary_rows:
        print(row["topology"], row["parameter"], row["cell"], row["distinct_timelines"],
              f"{row['mean_pairwise_hamming_frames']:.3f}",
              row["uptime_frames_min"], row["uptime_frames_max"])


if __name__ == "__main__":
    main()
