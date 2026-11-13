#!/usr/bin/env python3
"""Aggregate A2g-3 operation outputs without launching or changing workers."""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import run_a2g3 as study

ROOT = study.ROOT
OUT = study.OUT
LOG = OUT / "operation_log.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else None


def main() -> None:
    rows = read_csv(LOG)
    expected = study.all_jobs()
    if len(rows) != 90 or len({row["operation"] for row in rows}) != 90:
        raise RuntimeError(f"expected 90 unique operation rows, found {len(rows)}")
    expected_by_name = {
        study.op_name(job["family"], job["life"], job["pi"], job["L"], job["seed"]): job
        for job in expected
    }
    if set(row["operation"] for row in rows) != set(expected_by_name):
        raise RuntimeError("operation ledger does not match frozen 90-cell grid")

    per_seed: list[dict[str, Any]] = []
    raw_metrics: dict[str, dict[str, Any]] = {}
    successful = 0
    max_elapsed = 0.0
    for row in rows:
        name = row["operation"]
        job = expected_by_name[name]
        op_dir = OUT / "operations" / name
        config_path = op_dir / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if hashlib.sha256(config_path.read_bytes()).hexdigest() != row["config_sha256"]:
            raise RuntimeError(f"config hash mismatch: {name}")
        if config["preregistration_sha256"] != study.sha256(study.PREREG):
            raise RuntimeError(f"preregistration provenance mismatch: {name}")
        if config["runner_sha256"] != study.sha256(Path(study.__file__).resolve()):
            raise RuntimeError(f"runner provenance mismatch: {name}")
        if config["graph_edge_sha256"] != job["graph_sha256"]:
            raise RuntimeError(f"graph identity mismatch: {name}")
        elapsed = float(row["elapsed_seconds"])
        max_elapsed = max(max_elapsed, elapsed)
        metrics: dict[str, Any] = {}
        if row["status"] == "success":
            metrics = json.loads((op_dir / "trace_metrics.json").read_text(encoding="utf-8"))
            successful += 1
            raw_metrics[name] = metrics
        elif row["status"] not in {"failed_exception", "failed_timeout", "missing_status"}:
            raise RuntimeError(f"unexpected status in operation ledger: {name} {row['status']}")
        per_seed.append({
            "operation": name, "family": job["family"], "graph_id": job["graph_id"],
            "life": job["life"], "U": job["U"], "K": job["K"], "pi": job["pi"],
            "L": job["L"], "seed": job["seed"], "status": row["status"],
            "elapsed_seconds": elapsed, **metrics,
        })

    cell_groups: dict[tuple[str, float, float, float], list[dict[str, Any]]] = defaultdict(list)
    parameter_groups: dict[tuple[float, float, float], list[dict[str, Any]]] = defaultdict(list)
    for item in per_seed:
        key = (item["family"], float(item["life"]), float(item["pi"]), float(item["L"]))
        cell_groups[key].append(item)
        parameter_groups[(float(item["life"]), float(item["pi"]), float(item["L"]))].append(item)

    cell_rows = []
    for family in study.FAMILIES:
        for life, _, _ in study.LIVES:
            for pi, duration in study.PARAMETERS:
                group = cell_groups[(family, life, pi, duration)]
                good = [item for item in group if item["status"] == "success" and item.get("operation_qualifies", False)]
                cell_rows.append({
                    "family": family, "life": life, "pi": pi, "L": duration,
                    "expected_seeds": 3, "observed_rows": len(group),
                    "successful_operations": sum(item["status"] == "success" for item in group),
                    "qualifying_seeds": len(good), "cell_qualifies": len(good) == 3,
                    "mean_projection_fraction": mean_sd([float(x["projection_changed_edge_time_fraction"]) for x in group if x["status"] == "success"])[0],
                    "mean_projected_pi": mean_sd([float(x["projected_empirical_pi"]) for x in group if x["status"] == "success"])[0],
                    "mean_projected_L": mean_sd([float(x["projected_mean_up_duration"]) for x in group if x["status"] == "success"])[0],
                })

    parameter_rows = []
    for life in (0.5, 0.9):
        for pi, duration in study.PARAMETERS:
            group = parameter_groups[(life, pi, duration)]
            successful_group = [item for item in group if item["status"] == "success"]
            record: dict[str, Any] = {
                "life": life, "U": 60 if life == 0.5 else 108,
                "K": 5 if life == 0.5 else 9, "pi": pi, "L": duration,
                "n_registered": len(group), "n_success": len(successful_group),
                "n_qualifying": sum(bool(item.get("operation_qualifies", False)) for item in successful_group),
            }
            for field in ("raw_empirical_pi", "raw_mean_up_duration", "projected_empirical_pi",
                          "projected_mean_up_duration", "projection_changed_edge_time_fraction"):
                avg, sd = mean_sd([float(item[field]) for item in successful_group])
                record[field + "_mean"] = avg
                record[field + "_sample_sd_ddof1"] = sd
            parameter_rows.append(record)

    qualifying_cells = sum(bool(row["cell_qualifies"]) for row in cell_rows)
    h3_threshold = qualifying_cells >= 27
    all_success = successful == 90 and all(row["status"] == "success" for row in rows)
    h3_pass = all_success and h3_threshold
    criterion_counts = {
        key: sum(bool(item.get(key, False)) for item in per_seed if item["status"] == "success")
        for key in ("uk_exact_UK", "sr_mask_exact", "all_edges_in_skeleton", "projection_fraction_pass", "projected_pi_pass", "projected_duration_pass", "operation_qualifies")
    }
    summary = {
        "stage": "A2g-3", "status": "PASS" if h3_pass else "FAIL",
        "operations_registered": 90, "operations_successful": successful,
        "all_operations_successful": all_success,
        "cell_count": 30, "qualifying_cells": qualifying_cells,
        "required_qualifying_cells": 27, "qualifying_cell_fraction": qualifying_cells / 30,
        "cell_gate": h3_threshold, "criterion_pass_counts_among_successful": criterion_counts,
        "longest_parent_operation_seconds": max_elapsed,
        "infeasible_unrun": {"pi": 0.8, "L": 2, "p01": 2.0, "status": "mathematically_infeasible_not_run"},
        "per_parameter_strata": parameter_rows,
        "limitations": [
            "one graph realization per family/size",
            "patched non-upstream sampler",
            "timeline diversity family-independent by construction",
            "fixed structural-rule probe pairs",
            "projection may shift edge marginal and up-duration statistics",
        ],
    }
    write_csv(OUT / "per_seed_results.csv", per_seed)
    write_csv(OUT / "cell_summary.csv", cell_rows)
    write_csv(OUT / "parameter_summary.csv", parameter_rows)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.csv":
            manifest_rows.append({
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": study.sha256(path),
            })
    write_csv(OUT / "artifact_manifest.csv", manifest_rows, ["path", "size_bytes", "sha256"])
    print(json.dumps({key: summary[key] for key in (
        "status", "operations_registered", "operations_successful", "qualifying_cells",
        "required_qualifying_cells", "criterion_pass_counts_among_successful",
        "longest_parent_operation_seconds",
    )}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
