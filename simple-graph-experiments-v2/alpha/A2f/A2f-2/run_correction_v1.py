from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[2]
sys.path.insert(0, str(STAGE / "source"))
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator  # noqa: E402

OUT = STAGE / "results" / "correction_v1"
FAMILY = ROOT / "alpha" / "A2" / "A2d" / "item1" / "source" / "yadygaga" / "timelineBlockGenerator.py"
FRAME = ROOT / "alpha" / "A2" / "A2d" / "item1" / "source" / "yadygaga" / "frameGenerator.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def up_runs(bits: list[bool]) -> int:
    return sum(state and (i == 0 or not bits[i - 1]) for i, state in enumerate(bits))


def down_runs(bits: list[bool]) -> int:
    return sum((not state) and (i == 0 or bits[i - 1]) for i, state in enumerate(bits))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configs = OUT / "configs"
    configs.mkdir(exist_ok=True)
    hist: Counter[int] = Counter()
    rows = []
    code_hashes = {
        "baseline_timelineBlockGenerator.py": digest(FAMILY),
        "baseline_frameGenerator.py": digest(FRAME),
        "a2f_timelineBlockGenerator.py": digest(STAGE / "source/yadygaga/timelineBlockGenerator.py"),
        "a2f_package_init.py": digest(STAGE / "source/yadygaga/__init__.py"),
        "test_runner.py": digest(Path(__file__).resolve()),
    }
    for seed in range(42, 242):
        started = time.perf_counter()
        generator = SPCTimelineBlockGenerator(
            120, seed=seed, behavior="uk", up_count=84, up_runs=11,
            pathPersistency=0.75,
        )
        trace = generator.generate_blocks()
        bits = trace["timeline"]
        realized_u, realized_k, realized_j = sum(bits), up_runs(bits), down_runs(bits)
        elapsed = time.perf_counter() - started
        hist[realized_j] += 1
        config = {
            "stage": "A2f-2-correction-v1", "frames": 120, "life": 0.7,
            "U_requested": 84, "K_requested": 11, "pathPersistency": 0.75,
            "base_seed": seed, "timeline_seed": seed,
            "pool_seed": seed + 10000, "assembly_seed": seed + 20000,
            "source_sha256": code_hashes,
        }
        config_path = configs / f"seed_{seed}.json"
        config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
        rows.append({
            "seed": seed, "U_requested": 84, "K_requested": 11,
            "U_realized": realized_u, "K_realized": realized_k,
            "down_runs_realized": realized_j, "elapsed_seconds": elapsed,
            "config": config_path.relative_to(OUT).as_posix(),
        })
    Js = [10, 11, 12]
    weights = [
        (2 if J == 11 else 1) * math.comb(83, 10) * math.comb(35, J - 1)
        for J in Js
    ]
    weight_array = np.asarray(weights, dtype=np.float64)
    probs = weight_array / weight_array.sum()
    observed = np.asarray([hist[J] for J in Js], dtype=float)
    expected = 200 * probs
    observed_chi = float(np.sum((observed - expected) ** 2 / expected))
    simulated = np.random.default_rng(20261010).multinomial(200, probs, size=99999)
    simulated_chi = np.sum((simulated - expected) ** 2 / expected, axis=1)
    p_value = float((1 + np.count_nonzero(simulated_chi >= observed_chi)) / 100000)
    summary = {
        "status": "PASS" if all(r["U_realized"] == 84 and r["K_realized"] == 11 and r["elapsed_seconds"] < 60 for r in rows) and p_value >= 0.01 else "FAIL",
        "life": 0.7, "F": 120, "U": 84, "K": 11,
        "mean_up_frames": 84 / 11, "traces": len(rows),
        "exact_UK": sum(r["U_realized"] == 84 and r["K_realized"] == 11 for r in rows),
        "down_run_counts": dict(sorted(hist.items())),
        "chi_square_mc_p": p_value, "chi_square_mc_draws": 99999,
        "diagnostic_seed": 20261010,
        "max_operation_seconds": max(row["elapsed_seconds"] for row in rows),
        "source_sha256": code_hashes,
    }
    (OUT / "per_seed.jsonl").write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "PASS":
        raise SystemExit("corrective cell failed")


if __name__ == "__main__":
    main()
