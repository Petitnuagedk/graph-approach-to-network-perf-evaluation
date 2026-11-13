from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import time
import csv
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE / "source"))
from yadygaga.timelineBlockGenerator import (  # noqa: E402
    InfeasibleTimeline,
    SPCTimelineBlockGenerator,
)

FAMILY = ROOT / "alpha" / "A2" / "A2d" / "item1" / "source" / "yadygaga" / "timelineBlockGenerator.py"
BASE_FRAME = ROOT / "alpha" / "A2" / "A2d" / "item1" / "source" / "yadygaga" / "frameGenerator.py"
OVERLAY_TIMELINE = STAGE / "source" / "yadygaga" / "timelineBlockGenerator.py"
OVERLAY_INIT = STAGE / "source" / "yadygaga" / "__init__.py"
A2C = ROOT / "alpha" / "A2" / "A2c" / "results"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_original():
    spec = importlib.util.spec_from_file_location("a2d1_original_timeline", FAMILY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SPCTimelineBlockGenerator


def up_runs(bits: list[bool]) -> int:
    return sum(state and (i == 0 or not bits[i - 1]) for i, state in enumerate(bits))


def support_count(F: int, U: int, K: int) -> int:
    D = F - U
    if U == 0:
        return int(K == 0)
    if D == 0:
        return int(K == 1)
    if K < 1 or K > min(U, D + 1):
        return 0
    total = 0
    for J in range(max(1, K - 1), min(D, K + 1) + 1):
        boundaries = 2 if J == K else 1
        total += boundaries * math.comb(U - 1, K - 1) * math.comb(D - 1, J - 1)
    return total


def run_enumeration() -> dict:
    observed: Counter[tuple[int, int]] = Counter()
    for mask in range(1 << 8):
        bits = [(mask >> i) & 1 == 1 for i in range(8)]
        U = sum(bits)
        observed[(U, up_runs(bits))] += 1
    checks = 0
    for U in range(9):
        for K in range(9):
            assert observed[(U, K)] == support_count(8, U, K), (U, K, observed[(U, K)], support_count(8, U, K))
            checks += 1
    return {"status": "PASS", "pairs_checked": checks, "strings_enumerated": 256}


def frozen_grid() -> list[tuple[float, int, int]]:
    return [
        (0.3, 36, 36), (0.3, 36, 8), (0.3, 36, 2),
        (0.5, 60, 60), (0.5, 60, 11), (0.5, 60, 2),
        (0.7, 84, 37), (0.7, 84, 16), (0.7, 84, 3),
        (0.9, 108, 13), (0.9, 108, 7), (0.9, 108, 4),
    ]


def down_run_category(bits: list[bool]) -> int:
    return sum((not state) and (i == 0 or bits[i - 1]) for i, state in enumerate(bits))


def category_probabilities(U: int, D: int, K: int) -> tuple[list[int], list[float]]:
    Js = list(range(max(1, K - 1), min(D, K + 1) + 1))
    weights = [
        (2 if J == K else 1) * math.comb(U - 1, K - 1) * math.comb(D - 1, J - 1)
        for J in Js
    ]
    total = sum(weights)
    return Js, [weight / total for weight in weights]


def run_sampler_grid() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    seed_rows: list[dict] = []
    diagnostic_rng = np.random.default_rng(20261010)
    for life, U, K in frozen_grid():
        started = time.perf_counter()
        operation_times: list[float] = []
        hist: Counter[int] = Counter()
        exact = True
        for seed in range(42, 242):
            trace_started = time.perf_counter()
            gen = SPCTimelineBlockGenerator(
                120, seed=seed, behavior="uk", up_count=U, up_runs=K,
                pathPersistency=0.75,
            )
            result = gen.generate_blocks()
            bits = result["timeline"]
            realized_U = sum(bits)
            realized_K = up_runs(bits)
            exact &= realized_U == U and realized_K == K
            hist[down_run_category(bits)] += 1
            operation_elapsed = time.perf_counter() - trace_started
            operation_times.append(operation_elapsed)
            seed_rows.append({
                "life": life, "F": 120, "U_requested": U,
                "K_requested": K, "seed": seed,
                "U_realized": realized_U, "K_realized": realized_K,
                "down_runs_realized": down_run_category(bits),
                "elapsed_seconds": operation_elapsed,
            })
            (STAGE / "results" / "configs").mkdir(parents=True, exist_ok=True)
            config = {
                "stage": "A2f-2", "behavior": "uk", "frames": 120,
                "life": life, "U_requested": U, "K_requested": K,
                "pathPersistency": 0.75, "base_seed": seed,
                "timeline_seed": seed, "pool_seed": seed + 10000,
                "assembly_seed": seed + 20000,
                "source_sha256": {
                    "baseline_timelineBlockGenerator.py": sha256(FAMILY),
                    "baseline_frameGenerator.py": sha256(BASE_FRAME),
                    "a2f_timelineBlockGenerator.py": sha256(OVERLAY_TIMELINE),
                    "a2f_package_init.py": sha256(OVERLAY_INIT),
                    "test_runner.py": sha256(Path(__file__).resolve()),
                },
            }
            path = STAGE / "results" / "configs" / f"life_{life:.1f}_U{U}_K{K}_seed{seed}.json"
            path.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n")
        elapsed = time.perf_counter() - started
        Js, probs = category_probabilities(U, 120 - U, K)
        if len(Js) <= 1:
            p_value = 1.0
            informative = False
        else:
            observed = np.asarray([hist[J] for J in Js], dtype=float)
            expected = 200 * np.asarray(probs, dtype=float)
            chi_observed = float(np.sum((observed - expected) ** 2 / expected))
            simulated = diagnostic_rng.multinomial(200, probs, size=99999)
            chi_simulated = np.sum((simulated - expected) ** 2 / expected, axis=1)
            p_value = float((1 + np.count_nonzero(chi_simulated >= chi_observed)) / 100000)
            informative = True
        rows.append({
            "life": life, "F": 120, "U": U, "K": K,
            "mean_up_frames": U / K, "seeds": 200,
            "exact_UK": bool(exact), "down_run_counts": json.dumps({str(k): hist[k] for k in Js}, sort_keys=True),
            "chi_square_mc_p": p_value, "chi_square_informative": informative,
            "mc_draws": 99999 if informative else 0, "elapsed_seconds": elapsed,
            "max_operation_seconds": max(operation_times),
        })
    (STAGE / "results" / "grid_per_seed.jsonl").write_text("\n".join(
        json.dumps(row, sort_keys=True) for row in seed_rows
    ) + "\n")
    return rows, {
        "cells": len(rows), "traces": sum(r["seeds"] for r in rows),
        "all_exact_UK": all(r["exact_UK"] for r in rows),
        "all_cell_p_ge_0_01": all(r["chi_square_mc_p"] >= 0.01 for r in rows),
        "all_cell_per_trace_under_60s": all(r["max_operation_seconds"] < 60 for r in rows),
        "max_cell_elapsed_seconds": max(r["elapsed_seconds"] for r in rows),
    }


def run_regressions() -> tuple[list[dict], dict]:
    original = load_original()
    seeds = {
        0.3: [42, 63, 178, 107, 56],
        0.5: [42, 98, 90, 126, 236],
        0.7: [42, 228, 199, 235, 44],
    }
    rows = []
    for life, seed_list in seeds.items():
        for seed in seed_list:
            record = A2C / f"er__life_{life:.1f}__seed_{seed}__p_0.5"
            config = json.loads((record / "config.json").read_text())
            trace = json.loads((record / "timeline.json").read_text())
            stored = {"timeline": [c == "1" for c in trace["bits"]], "path_ids": trace["path_ids"]}
            inputs = (config["frames"], config["life"], config["stability"], config["timeline_seed"], config["mode"], config["pathPersistency"])
            comparisons = {}
            for behavior in ("legacy", "patched-v2"):
                got = SPCTimelineBlockGenerator(*inputs, behavior=behavior).generate_blocks()
                direct = original(*inputs, behavior=("legacy" if behavior == "legacy" else "patched")).generate_blocks()
                comparisons[f"{behavior}_matches_original"] = got == direct
                comparisons[f"{behavior}_matches_stored"] = got == stored if behavior == "patched-v2" else None
            U = int(config["up_count_expected"])
            K = int(config["up_runs_expected"])
            exact = SPCTimelineBlockGenerator(
                config["frames"], seed=seed, behavior="uk", up_count=U,
                up_runs=K, pathPersistency=config["pathPersistency"],
            ).generate_blocks()
            equivalent = SPCTimelineBlockGenerator(
                config["frames"], config["life"],
                1 - (K - 1) / (U - 1), seed, config["mode"],
                config["pathPersistency"], "patched-v2",
            ).generate_blocks()
            comparisons["uk_matches_patched_v2"] = exact == equivalent
            rows.append({
                "record": record.name, "life": life, "seed": seed,
                "U": U, "K": K, "p": config["pathPersistency"],
                **comparisons,
            })
    expected = 15
    passed = (
        len(rows) == expected
        and all(r["legacy_matches_original"] and r["patched-v2_matches_original"] for r in rows)
        and all(r["patched-v2_matches_stored"] for r in rows)
        and all(r["uk_matches_patched_v2"] for r in rows)
    )
    return rows, {
        "records": len(rows), "legacy_vs_original": sum(r["legacy_matches_original"] for r in rows),
        "patched_v2_vs_original": sum(r["patched-v2_matches_original"] for r in rows),
        "patched_v2_vs_stored": sum(bool(r["patched-v2_matches_stored"]) for r in rows),
        "uk_vs_patched_v2": sum(r["uk_matches_patched_v2"] for r in rows),
        "status": "PASS" if passed else "FAIL",
    }


def run_infeasibility() -> tuple[list[dict], dict]:
    rows = []
    for frames in (60, 120, 240):
        for life_i in range(1, 10):
            life = life_i / 10
            U = round(frames * life)
            D = frames - U
            K_max = min(U, D + 1)
            K = K_max + 1
            started = time.perf_counter()
            try:
                SPCTimelineBlockGenerator(frames, seed=1, behavior="uk", up_count=U, up_runs=K)
                raise AssertionError("expected InfeasibleTimeline")
            except InfeasibleTimeline as error:
                duration = time.perf_counter() - started
                row = {
                    "F": frames, "life": life, "U": U, "D": D,
                    "K_requested": K, "K_max": K_max,
                    "fields_exact": (error.U, error.D, error.K_requested, error.K_max) == (U, D, K, K_max),
                    "elapsed_seconds": duration,
                }
                rows.append(row)
    started = time.perf_counter()
    try:
        SPCTimelineBlockGenerator(120, path_life=0.9, seed=1, behavior="uk", mean_up_duration=4)
        raise AssertionError("expected mean-derived InfeasibleTimeline")
    except InfeasibleTimeline as error:
        duration = time.perf_counter() - started
        mean_row = {
            "F": 120, "life": 0.9, "U": error.U, "D": error.D,
            "mean_up_duration": 4, "K_requested": error.K_requested,
            "K_max": error.K_max,
            "fields_exact": (error.U, error.D, error.K_requested, error.K_max) == (108, 12, 27, 13),
            "elapsed_seconds": duration,
        }
    rows.append(mean_row)
    passed = len(rows) == 28 and all(r["fields_exact"] and r["elapsed_seconds"] < 1 for r in rows)
    return rows, {"cases": len(rows), "fields_exact": sum(r["fields_exact"] for r in rows), "all_under_1s": all(r["elapsed_seconds"] < 1 for r in rows), "status": "PASS" if passed else "FAIL"}


def main() -> None:
    results = STAGE / "results"
    results.mkdir(exist_ok=True)
    enum = run_enumeration()
    grid_rows, grid_summary = run_sampler_grid()
    regression_rows, regression_summary = run_regressions()
    infeasible_rows, infeasible_summary = run_infeasibility()
    summary = {
        "support_enumeration": enum,
        "sampler_grid": grid_summary,
        "regressions": regression_summary,
        "infeasibility": infeasible_summary,
    }
    (results / "grid_cells.json").write_text(json.dumps(grid_rows, indent=2, sort_keys=True) + "\n")
    (results / "regressions.json").write_text(json.dumps(regression_rows, indent=2, sort_keys=True) + "\n")
    (results / "infeasibility.json").write_text(json.dumps(infeasible_rows, indent=2, sort_keys=True) + "\n")
    (results / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    manifest = results / "artifact_manifest.csv"
    with manifest.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("path", "bytes", "sha256"))
        for artifact in sorted(path for path in results.rglob("*") if path.is_file() and path != manifest):
            writer.writerow((artifact.relative_to(results).as_posix(), artifact.stat().st_size, sha256(artifact)))
    print(json.dumps(summary, indent=2, sort_keys=True))
    if grid_summary["cells"] != 12 or not grid_summary["all_exact_UK"] or not grid_summary["all_cell_p_ge_0_01"] or not grid_summary["all_cell_per_trace_under_60s"]:
        raise SystemExit("sampler-grid gate failed")
    if regression_summary["status"] != "PASS" or infeasible_summary["status"] != "PASS":
        raise SystemExit("regression or infeasibility gate failed")


if __name__ == "__main__":
    main()
