"""Generate and audit the preregistered Phase 7D offline trace set."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PHASE5 = ROOT / "simple-graph-experiments-v2" / "phase5"
OUT = HERE / "traces"
sys.path.insert(0, str(HERE))

from generator_v2 import (  # noqa: E402
    FRAME_COUNT,
    STABILITY_VALUES,
    TOPOLOGIES,
    GraphPools,
    _route,
    dump_metadata,
    generate_trace,
    generate_timeline,
    quota_for,
    read_trace,
    run_count_for,
)


def _tuple_for(family: str, value: float) -> tuple[float, float, float]:
    if family == "path_life":
        return value, 0.8, 0.75
    if family == "stability":
        return 0.5, value, 0.75
    if family == "pathPersistency":
        return 0.5, 0.8, value
    raise ValueError(f"unknown Phase 5 sweep family: {family}")


def discover_cells(topology: str) -> list[tuple[tuple[float, float, float], Path]]:
    roots = PHASE5 / topology
    by_tuple: dict[tuple[float, float, float], Path] = {}
    for family in ("path_life", "stability", "pathPersistency"):
        for path in sorted((roots / family / "dynamic_frames" / "graph_0001").glob("*/frames.csv")):
            value = float(path.parent.name.rsplit("_", 1)[1])
            params = _tuple_for(family, value)
            by_tuple.setdefault(params, path)
    return sorted(by_tuple.items())


def _bits(labels: list[str], matrices):
    source, destination = labels.index("S"), labels.index("R")
    return [bool(_route(matrix, source, destination)) for matrix in matrices]


def _hamming(left, right):
    return sum(a != b for a, b in zip(left, right))


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cell_rows: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []
    timelines: dict[tuple[str, tuple[float, float, float], int], list[bool]] = {}
    summaries: dict[tuple[str, tuple[float, float, float]], dict[str, object]] = {}
    failures: list[str] = []

    for topology in TOPOLOGIES:
        graph_paths = sorted((PHASE5 / topology).glob("*/dynamic_frames/graph_*/**/frames.csv"))
        pools = GraphPools.from_paths(graph_paths)
        cells = discover_cells(topology)
        if len(cells) != 13:
            failures.append(f"{topology}: expected 13 unique parameter tuples, found {len(cells)}")
        for params, representative in cells:
            p, stability, persistency = params
            cell_key = (topology, params)
            generated_bits = []
            metadata_rows = []
            name = f"pathlife_{p:.2f}__stability_{stability:.2f}__persistency_{persistency:.2f}"
            for realization_id in range(1, 6):
                trace_bytes, metadata = generate_trace(pools, topology, params, realization_id)
                repeat_bytes, repeat_metadata = generate_trace(pools, topology, params, realization_id)
                deterministic = (trace_bytes == repeat_bytes and dump_metadata(metadata) == dump_metadata(repeat_metadata))
                trace_dir = OUT / topology / name / f"realization_{realization_id:02d}"
                trace_dir.mkdir(parents=True, exist_ok=True)
                (trace_dir / "frames.csv").write_bytes(trace_bytes)
                (trace_dir / "metadata.json").write_bytes(dump_metadata(metadata))
                labels, matrices = read_trace(trace_dir / "frames.csv")
                bits = _bits(labels, matrices)
                timelines[(topology, params, realization_id)] = bits
                generated_bits.append(bits)
                metadata_rows.append(metadata)
                measured = sum(bits)
                transitions = sum(a != b for a, b in zip(bits, bits[1:]))
                requested_up = quota_for(p, FRAME_COUNT)
                exact_quota = measured == requested_up == metadata["up_quota"]
                if not exact_quota:
                    failures.append(f"{topology} {params} realization {realization_id}: quota mismatch")
                if not deterministic:
                    failures.append(f"{topology} {params} realization {realization_id}: repeat not byte-identical")
                trace_rows.append({
                    "topology": topology,
                    "path_life": p,
                    "stability": stability,
                    "pathPersistency": persistency,
                    "realization_id": realization_id,
                    "timeline_sha256": metadata["timeline_sha256"],
                    "frames_sha256": metadata["frames_sha256"],
                    "requested_up_frames": requested_up,
                    "measured_up_frames": measured,
                    "quota_error_frames": measured - requested_up,
                    "measured_uptime": measured / FRAME_COUNT,
                    "requested_path_life": p,
                    "run_count": len(metadata["up_run_lengths_frames"]),
                    "mean_up_run_frames": metadata["mean_up_run_frames"],
                    "up_run_cv": metadata["up_run_cv"],
                    "transition_count": transitions,
                    "endpoint_pattern": json.dumps(metadata["endpoint_pattern_first_last_up"]),
                    "deterministic_repeat": deterministic,
                    "source_trace_count": len(pools.source_hashes),
                    "source_pool_hash": hashlib.sha256(
                        "".join(sorted(pools.source_hashes.values())).encode("ascii")
                    ).hexdigest(),
                    "representative_source": str(representative.relative_to(ROOT)),
                })

            unique_count = len({tuple(bits) for bits in generated_bits})
            pair_distances = [_hamming(left, right) / FRAME_COUNT
                              for left, right in itertools.combinations(generated_bits, 2)]
            mean_pairwise = statistics.mean(pair_distances) if pair_distances else 0.0
            requested_up = quota_for(p, FRAME_COUNT)
            eligible = 0 < requested_up < FRAME_COUNT
            if eligible and unique_count < 5:
                failures.append(f"{topology} {params}: only {unique_count}/5 unique timelines")
            if eligible and mean_pairwise < 0.10:
                failures.append(f"{topology} {params}: mean normalized Hamming {mean_pairwise:.6f} < 0.10")
            if not eligible and unique_count != 1:
                failures.append(f"{topology} {params}: degenerate quota should have one timeline")
            summary = {
                "topology": topology,
                "path_life": p,
                "stability": stability,
                "pathPersistency": persistency,
                "representative_source": str(representative.relative_to(ROOT)),
                "requested_up_frames": requested_up,
                "mean_measured_uptime": statistics.mean(sum(bits) / FRAME_COUNT for bits in generated_bits),
                "uptime_error_frames_max_abs": max(abs(sum(bits) - requested_up) for bits in generated_bits),
                "unique_timelines_of_5": unique_count,
                "diversity_eligible": eligible,
                "mean_pairwise_hamming_fraction": mean_pairwise,
                "min_pairwise_hamming_frames": min((_hamming(a, b) for a, b in itertools.combinations(generated_bits, 2)), default=0),
                "run_count_K": run_count_for(requested_up, FRAME_COUNT),
                "mean_up_run_frames_expected": (requested_up / run_count_for(requested_up, FRAME_COUNT)
                                                if run_count_for(requested_up, FRAME_COUNT) else 0.0),
                "mean_measured_up_run_cv": statistics.mean(float(row["up_run_cv"]) for row in metadata_rows),
                "endpoint_pattern": json.dumps(metadata_rows[0]["endpoint_pattern_first_last_up"]),
                "pass": (unique_count >= 5 and mean_pairwise >= 0.10) if eligible else unique_count == 1,
            }
            summaries[cell_key] = summary
            cell_rows.append(summary)

    # Stability semantics: same U/K/mean/boundary/transitions for matched IDs;
    # CV monotone in stability with the preregistered tolerance and endpoint gap.
    stability_rows: list[dict[str, object]] = []
    for topology in TOPOLOGIES:
        cv_means = []
        for value in STABILITY_VALUES:
            params = (0.5, value, 0.75)
            records = [summaries[(topology, params)]]
            per_id = [
                next(row for row in trace_rows if row["topology"] == topology
                     and row["path_life"] == 0.5 and row["stability"] == value
                     and row["pathPersistency"] == 0.75 and row["realization_id"] == realization)
                for realization in range(1, 6)
            ]
            cvs = [float(row["up_run_cv"]) for row in per_id]
            cv_means.append(statistics.mean(cvs))
            invariant = all(
                row["requested_up_frames"] == 30
                and row["run_count"] == per_id[0]["run_count"]
                and row["mean_up_run_frames"] == per_id[0]["mean_up_run_frames"]
                and row["endpoint_pattern"] == per_id[0]["endpoint_pattern"]
                and row["transition_count"] == per_id[0]["transition_count"]
                for row in per_id
            )
            if not invariant:
                failures.append(f"{topology}: U/K/mean/endpoints/transitions vary across IDs at stability={value}")
            stability_rows.append({
                "topology": topology,
                "stability": value,
                "mean_up_run_cv": cv_means[-1],
                "mean_transition_count": statistics.mean(int(row["transition_count"]) for row in per_id),
                "invariants_across_ids": invariant,
            })
        for lower, higher in zip(cv_means, cv_means[1:]):
            if higher - lower > 0.05:
                failures.append(f"{topology}: stability CV adjacent reversal {higher-lower:.6f} > 0.05")
        if cv_means[0] - cv_means[-1] < 0.10:
            failures.append(f"{topology}: stability 0-to-0.8 CV difference {cv_means[0]-cv_means[-1]:.6f} < 0.10")

    # Persistency-only changes must preserve S-R state for every matched ID.
    for topology in TOPOLOGIES:
        reference = (0.5, 0.8, 0.0)
        for persistency in (0.25, 0.5, 0.75, 1.0):
            current = (0.5, 0.8, persistency)
            for realization in range(1, 6):
                if timelines[(topology, reference, realization)] != timelines[(topology, current, realization)]:
                    failures.append(f"{topology}: persistency {persistency} changed realization {realization} timeline")

    _write_csv(HERE / "per_trace_metrics.csv", trace_rows)
    _write_csv(HERE / "cell_summary.csv", cell_rows)
    _write_csv(HERE / "stability_check.csv", stability_rows)
    result = {
        "generator_version": "j2-sr-timeline-v2.1",
        "frames": FRAME_COUNT,
        "topologies": list(TOPOLOGIES),
        "unique_cells": len(cell_rows),
        "generated_traces": len(trace_rows),
        "protocol_variants": 0,
        "failures": failures,
        "passed": not failures,
    }
    (HERE / "validation_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())