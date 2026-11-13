#!/usr/bin/env python3
"""Continue only never-started A2g-2 cells after an external interruption.

Existing operations are never re-run. A config without a result/status is recorded
as interrupted and remains a failed registered cell.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import run_a2g2 as study

ROOT = study.ROOT
OUT = study.OUT
LOG = OUT / "operation_log.csv"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def append_row(path: Path, row: dict[str, object]) -> None:
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writerow(row)


def make_row(name: str, status: str, returncode: object, elapsed: float,
             graph: dict, p_edge: float, trials: int, seed: int,
             config_path: Path) -> dict[str, object]:
    return {
        "operation": name,
        "status": status,
        "returncode": returncode,
        "elapsed_seconds": elapsed,
        "family": graph["family"],
        "graph_id": graph["graph_id"],
        "N": graph["N"],
        "p_edge": p_edge,
        "trials": trials,
        "seed": seed,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "config_path": config_path.relative_to(ROOT).as_posix(),
        "stdout": "",
        "stderr": "",
    }


def main() -> int:
    graphs = study.graph_records()
    jobs = [
        (graph, p_edge, trials, seed)
        for graph in graphs
        for p_edge in study.P_GRID
        for trials in study.TRIAL_GRID
        for seed in study.SEEDS
    ]
    rows = read_rows(LOG)
    if len(rows) != 311 or len({row["operation"] for row in rows}) != 311:
        raise RuntimeError("expected exactly 311 unique, already-logged operations; refusing to retry")
    if any(row["status"] != "success" for row in rows):
        raise RuntimeError("unexpected existing failure; inspect manually before continuation")

    # The 312th config was written before interruption, but no worker status/result exists.
    graph, p_edge, trials, seed = jobs[311]
    name = study.op_name(graph, p_edge, trials, seed)
    out_dir = OUT / "operations" / name
    config_path = out_dir / "config.json"
    status_path = out_dir / "operation_status.json"
    metrics_path = out_dir / "pool_metrics.json"
    if not config_path.exists() or status_path.exists() or metrics_path.exists():
        raise RuntimeError("interrupted-cell artifacts do not match the expected untouched attempt")
    expected_config = study.build_config(graph, p_edge, trials, seed)
    if json.loads(config_path.read_text(encoding="utf-8")) != expected_config:
        raise RuntimeError("interrupted-cell config differs from the frozen runner config")
    study.write_json(status_path, {
        "status": "failed_external_interruption",
        "detail": "parent sweep ended after config creation; no result/status was present; not retried",
    })
    interrupted = make_row(name, "failed_external_interruption", "INTERRUPTED", 0.0,
                           graph, p_edge, trials, seed, config_path)
    append_row(LOG, interrupted)
    rows.append({key: str(value) for key, value in interrupted.items()})
    print(f"Recorded {name} as interrupted; it will not be retried.", flush=True)

    started_index = 312  # zero-based job index; next cell is operation 313.
    for index, (graph, p_edge, trials, seed) in enumerate(jobs[started_index:], start=started_index + 1):
        name = study.op_name(graph, p_edge, trials, seed)
        out_dir = OUT / "operations" / name
        out_dir.mkdir(parents=True, exist_ok=True)
        config_path = out_dir / "config.json"
        if config_path.exists() or (out_dir / "operation_status.json").exists() or (out_dir / "pool_metrics.json").exists():
            raise RuntimeError(f"future cell already has artifacts; refusing to retry: {name}")
        config = study.build_config(graph, p_edge, trials, seed)
        study.write_json(config_path, config)
        command = [sys.executable, str(Path(study.__file__).resolve()), "--operation", str(config_path)]
        began = time.perf_counter()
        try:
            process = subprocess.run(command, cwd=study.HERE, timeout=study.TIMEOUT,
                                     capture_output=True, text=True, check=False)
            elapsed = time.perf_counter() - began
            status_doc = json.loads((out_dir / "operation_status.json").read_text(encoding="utf-8")) if (out_dir / "operation_status.json").exists() else {"status": "missing_status"}
            status = str(status_doc.get("status", "missing_status"))
            row = make_row(name, status, process.returncode, elapsed, graph, p_edge, trials, seed, config_path)
            row["stdout"] = process.stdout[-1000:]
            row["stderr"] = process.stderr[-1000:]
        except subprocess.TimeoutExpired as error:
            elapsed = time.perf_counter() - began
            study.write_json(out_dir / "operation_status.json", {
                "status": "failed_timeout", "timeout_seconds": study.TIMEOUT,
                "elapsed_seconds": elapsed, "detail": "continuation run; no retry",
            })
            row = make_row(name, "failed_timeout", "TIMEOUT", elapsed, graph, p_edge, trials, seed, config_path)
            row["stdout"] = str(error.stdout or "")[-1000:]
            row["stderr"] = str(error.stderr or "")[-1000:]
        append_row(LOG, row)
        rows.append({key: str(value) for key, value in row.items()})
        if index % 10 == 0 or index == len(jobs):
            print(f"[{index}/{len(jobs)}] {name}: {row['status']} ({float(row['elapsed_seconds']):.2f}s)", flush=True)

    if len(rows) != 810 or len({row["operation"] for row in rows}) != 810:
        raise RuntimeError("operation log does not cover the 810 unique preregistered cells")
    operation_dirs = {
        row["operation"]: OUT / "operations" / row["operation"]
        for row in rows
    }
    study.summarize(rows, operation_dirs)
    return 0 if all(row["status"] == "success" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
