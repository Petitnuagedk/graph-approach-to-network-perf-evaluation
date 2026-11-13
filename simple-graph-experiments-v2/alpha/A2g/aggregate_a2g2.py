#!/usr/bin/env python3
"""Aggregation-only repair for A2g-2 frozen pool outputs.

Does not launch workers or modify the operation ledger. Bridges the frozen
summarizer's expected endpoint degree key names to graph_records()'s actual keys.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import run_a2g2 as study

ROOT = study.ROOT
OUT = study.OUT
LOG = OUT / "operation_log.csv"


def read_log() -> list[dict[str, str]]:
    with LOG.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    rows = read_log()
    expected_jobs = 810
    names = [row["operation"] for row in rows]
    if len(rows) != expected_jobs or len(set(names)) != expected_jobs:
        raise RuntimeError(f"expected {expected_jobs} unique ledger rows; found {len(rows)}")
    dirs = {name: OUT / "operations" / name for name in names}
    for row in rows:
        op_dir = dirs[row["operation"]]
        config_path = op_dir / "config.json"
        if not config_path.exists():
            raise RuntimeError(f"missing frozen config for {row['operation']}")
        expected_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
        if row["config_sha256"] != expected_hash:
            raise RuntimeError(f"config hash mismatch for {row['operation']}")
        if row["status"] == "success":
            if not (op_dir / "pool_metrics.json").exists():
                raise RuntimeError(f"successful cell missing metrics: {row['operation']}")
        elif row["status"] == "failed_external_interruption":
            if (op_dir / "pool_metrics.json").exists():
                raise RuntimeError("interrupted cell unexpectedly has metrics")
        else:
            raise RuntimeError(f"unexpected failed-cell status: {row['operation']}={row['status']}")

    original_graph_records = study.graph_records

    def graph_records_with_degree_aliases():
        records = original_graph_records()
        for graph in records:
            graph["endpoint_degree_S"] = graph["degree_s"]
            graph["endpoint_degree_R"] = graph["degree_r"]
        return records

    study.graph_records = graph_records_with_degree_aliases
    study.summarize(rows, dirs)
    print(f"aggregated {len(rows)} operations; successful={sum(r['status'] == 'success' for r in rows)}; failures={sum(r['status'] != 'success' for r in rows)}")
    print(f"operation ledger: {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
