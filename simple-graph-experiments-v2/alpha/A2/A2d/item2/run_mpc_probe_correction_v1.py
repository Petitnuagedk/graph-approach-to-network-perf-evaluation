#!/usr/bin/env python3
"""Preregistered correction wrapper for the A2d item 2 MPC probe."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results" / "correction_v1"
ORIGINAL_RUNNER = HERE / "run_mpc_probe.py"
ORIGINAL_PREREG = HERE / "prereg.md"
CORRECTION_PREREG = HERE / "correction_v1_prereg.md"
INITIAL_RUNNER_SHA256 = "e04f604e5973b386829aa5fa83b66b99d8c9615398c98fe745529a0b36cc7929"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_original():
    spec = importlib.util.spec_from_file_location("mpc_probe_original", ORIGINAL_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load original probe implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RESULTS = RESULTS
    return module


def corrected_statistics(_generator, timeline):
    """Compute JSON-safe requested metrics from None/int path-ID tuples."""
    if not timeline:
        return {}
    pair_count = len(timeline[0])
    frame_count = len(timeline)
    statuses = [tuple(value is not None for value in entry) for entry in timeline]
    pairs = []
    for pair_index in range(pair_count):
        series = [status[pair_index] for status in statuses]
        pairs.append({
            "pair_index": pair_index,
            "up_count": sum(series),
            "uptime_ratio": sum(series) / frame_count,
            "up_blocks": sum(value and (index == 0 or not series[index - 1]) for index, value in enumerate(series)),
            "changes": sum(series[index] != series[index - 1] for index in range(1, frame_count)),
        })
    tuple_counts = {}
    for status in statuses:
        key = "|".join("1" if value else "0" for value in status)
        tuple_counts[key] = tuple_counts.get(key, 0) + 1
    return {"frames": frame_count, "pairs": pairs, "status_tuples": tuple_counts}


def operation(config_path: Path) -> int:
    module = load_original()
    source_root = module.SOURCE
    sys.path.insert(0, str(source_root))
    from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator

    MPCTimelineBlockGenerator.computeStatistics = corrected_statistics
    return module.execute(config_path)


def parent() -> None:
    module = load_original()
    RESULTS.mkdir(parents=True, exist_ok=True)
    operation_log = []
    correction_hash = sha256(CORRECTION_PREREG)
    runner_hash = sha256(Path(__file__).resolve())
    for arrangement in ("disjoint", "shared_source"):
        for pair_count in module.PAIR_COUNTS:
            for seed in module.SEEDS:
                label = f"{arrangement}_m{pair_count}_seed{seed}"
                output = RESULTS / label
                output.mkdir(parents=True, exist_ok=True)
                config = module.config_for(arrangement, pair_count, seed)
                config["correction_version"] = 1
                config["original_preregistration_sha256"] = sha256(ORIGINAL_PREREG)
                config["preregistration_sha256"] = correction_hash
                config["source_sha256"]["run_mpc_probe_failed_initial.py"] = INITIAL_RUNNER_SHA256
                config["source_sha256"]["run_mpc_probe_correction_v1.py"] = runner_hash
                config_path = output / "config.json"
                config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                command = [sys.executable, str(Path(__file__).resolve()), "--operation", str(config_path)]
                try:
                    result = subprocess.run(command, timeout=module.TIMEOUT, check=False, cwd=HERE)
                    status_path = output / "operation_status.json"
                    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {"status": "failed_missing_status"}
                    operation_log.append({"label": label, "arrangement": arrangement, "pair_count": pair_count, "seed": seed, "returncode": result.returncode, "status": status.get("status")})
                except subprocess.TimeoutExpired:
                    module.write_json(output / "operation_status.json", {"status": "failed_timeout", "timeout_seconds": module.TIMEOUT})
                    operation_log.append({"label": label, "arrangement": arrangement, "pair_count": pair_count, "seed": seed, "returncode": "TIMEOUT", "status": "failed_timeout"})
    module.write_csv(RESULTS / "operation_log.csv", operation_log, ["label", "arrangement", "pair_count", "seed", "returncode", "status"])
    module.summarize()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", type=Path)
    parser.add_argument("--summarize", action="store_true")
    args = parser.parse_args()
    module = load_original()
    if args.operation:
        raise SystemExit(operation(args.operation))
    if args.summarize:
        module.summarize()
    else:
        parent()


if __name__ == "__main__":
    main()
