#!/usr/bin/env python3
"""Registered A0-R2 support, draw, and uniformity measurements."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "YaDyGaGa"
RESULTS = HERE / "results"
sys.path.insert(0, str(SOURCE))
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

SEEDS = range(42, 242)
LIVES = (0.1, 0.3, 0.5, 0.7, 0.9)
STABILITIES = (0.0, 0.4, 0.8)
F = 120
N_NULL = 99_999


def quota_runs(frames: int, life: float, stability: float) -> tuple[int, int, int]:
    up = max(0, min(frames, int(round(frames * life))))
    down = frames - up
    if up in (0, frames):
        runs = 0 if up == 0 else 1
    else:
        runs = max(1, min(up, int(round(1 + (1 - stability) * (up - 1)))))
    return up, down, runs


def category_counts(up: int, down: int, runs: int) -> dict[int, int]:
    if up == 0 or down == 0:
        return {0: 1}
    lower = max(1, runs - 1)
    upper = min(down, runs + 1)
    result = {}
    for down_runs in range(lower, upper + 1):
        if down_runs == runs:
            boundaries = 2
        elif abs(down_runs - runs) == 1:
            boundaries = 1
        else:
            boundaries = 0
        if down_runs <= down and boundaries:
            result[down_runs] = (
                boundaries
                * math.comb(up - 1, runs - 1)
                * math.comb(down - 1, down_runs - 1)
            )
    return result


def support_size(up: int, down: int, runs: int) -> int:
    if up == 0 or down == 0:
        return 1
    if runs > down + 1:
        return 0
    return sum(category_counts(up, down, runs).values())


def brute_count(frames: int, life: float, stability: float) -> int:
    up, down, runs = quota_runs(frames, life, stability)
    wanted = support_size(up, down, runs)
    count = 0
    for mask in range(1 << frames):
        bits = [(mask >> index) & 1 for index in range(frames)]
        actual_runs = sum(bits[i] and (i == 0 or not bits[i - 1]) for i in range(frames))
        if sum(bits) == up and (actual_runs == runs if up not in (0, frames) else True):
            count += 1
    assert count == wanted, (frames, life, stability, count, wanted)
    return count


def timeline_string(seed: int, life: float, stability: float) -> str:
    generated = SPCTimelineBlockGenerator(
        frames=F,
        path_life=life,
        stability=stability,
        seed=seed,
        mode="blocks",
        pathPersistency=0.9,
    ).generate_blocks()
    return "".join("1" if bit else "0" for bit in generated["timeline"])


def uniform_unique_p01(m: int, rng: np.random.Generator) -> tuple[int, str]:
    n = len(SEEDS)
    if m <= 100_000:
        reps = 20_000
        occupancies = rng.multinomial(n, np.full(m, 1 / m), size=reps)
        unique_counts = np.count_nonzero(occupancies, axis=1)
        return int(np.quantile(unique_counts, 0.01, method="inverted_cdf")), "20k exact multinomial replicates"
    lam = n * (n - 1) / (2 * m)
    # At these large M the 99th percentile of birthday collisions is 0 or 1.
    return n - (1 if lam >= -math.log(0.99) else 0), "Poisson birthday approximation"


def run():
    RESULTS.mkdir(exist_ok=True)
    small_checks = []
    for life in LIVES:
        for stability in STABILITIES:
            small_checks.append({
                "frames": 8,
                "life": life,
                "stability": stability,
                "M": brute_count(8, life, stability),
            })

    rng = np.random.default_rng(20261009)
    rows = []
    draw_rows = []
    summary_rows = []
    for life in LIVES:
        for stability in STABILITIES:
            up, down, runs = quota_runs(F, life, stability)
            groups = category_counts(up, down, runs)
            M = sum(groups.values()) if runs <= down + 1 or up in (0, F) else 0
            strings = []
            errors = 0
            observed_js = []
            for seed in SEEDS:
                try:
                    bits = timeline_string(seed, life, stability)
                    strings.append(bits)
                    actual_up = bits.count("1")
                    actual_runs = sum(bits[i] == "1" and (i == 0 or bits[i - 1] == "0") for i in range(F))
                    down_runs = sum(bits[i] == "0" and (i == 0 or bits[i - 1] == "1") for i in range(F))
                    observed_js.append(down_runs)
                    draw_rows.append({
                        "life": life, "stability": stability, "seed": seed,
                        "bits": bits, "up_count": actual_up,
                        "up_runs": actual_runs, "down_runs": down_runs,
                        "sha256": hashlib.sha256(bits.encode()).hexdigest(),
                    })
                except ValueError:
                    errors += 1
            unique_count = len(set(strings))
            multiplicities = Counter(strings)
            duplicate_group = max(multiplicities.values(), default=0)
            pairs = list(itertools.combinations(strings, 2))
            distances = [sum(a != b for a, b in zip(x, y)) / F for x, y in pairs]
            q = up / F
            norm_d = [x / (2 * min(q, 1 - q)) for x in distances] if 0 < q < 1 else []
            expected_unique = M * (-math.expm1(len(SEEDS) * math.log1p(-1 / M))) if M > 1 else (1 if M else 0)
            expected_collisions = len(SEEDS) * (len(SEEDS) - 1) / (2 * M) if M else None
            unique_p01, p01_method = uniform_unique_p01(M, rng) if M else (None, "not applicable")

            valid_js = sorted(groups)
            chi_stat = None
            chi_p = None
            null_category_probabilities = []
            category_observed = []
            if M and len(valid_js) > 1 and observed_js:
                null_category_probabilities = [groups[j] / M for j in valid_js]
                category_observed = [observed_js.count(j) for j in valid_js]
                expected = np.asarray(null_category_probabilities) * len(SEEDS)
                observed = np.asarray(category_observed)
                chi_stat = float(np.sum((observed - expected) ** 2 / expected))
                simulated = rng.multinomial(len(SEEDS), null_category_probabilities, size=N_NULL)
                null_stats = np.sum((simulated - expected) ** 2 / expected, axis=1)
                chi_p = float((1 + np.count_nonzero(null_stats >= chi_stat)) / (N_NULL + 1))
            row = {
                "frames": F, "life": life, "stability": stability,
                "up_count": up, "down_count": down, "requested_up_runs": runs,
                "M": M, "valid_down_run_categories": json.dumps(valid_js),
                "category_counts_by_down_runs": json.dumps(groups, sort_keys=True),
                "attempted_seeds": len(SEEDS), "raised_count": errors,
                "successful_draws": len(strings), "unique_timelines": unique_count,
                "mean_pairwise_hamming": statistics.mean(distances) if distances else None,
                "min_pairwise_hamming": min(distances) if distances else None,
                "max_pairwise_hamming": max(distances) if distances else None,
                "mean_normalized_D": statistics.mean(norm_d) if norm_d else None,
                "largest_duplicate_group": duplicate_group,
                "uniform_expected_unique": expected_unique,
                "uniform_expected_collision_pairs": expected_collisions,
                "uniform_unique_p01": unique_p01,
                "uniform_unique_p01_method": p01_method,
                "observed_down_run_category_counts": json.dumps(dict(Counter(observed_js)), sort_keys=True),
                "uniform_null_down_run_probabilities": json.dumps(dict(zip(valid_js, null_category_probabilities)), sort_keys=True),
                "pearson_chi_square": chi_stat,
                "uniformity_monte_carlo_p": chi_p,
                "uniformity_partition": "uninformative" if M and len(valid_js) <= 1 else "down-run-count marginal",
            }
            rows.append(row)
            summary_rows.append({"life": life, "stability": stability, "M": M, "unique": unique_count, "mean_hamming": row["mean_pairwise_hamming"], "mean_D": row["mean_normalized_D"], "largest_duplicate_group": duplicate_group, "uniformity_p": chi_p, "raises": errors})

    for name, data in (("sampler_uniform_cells.csv", rows), ("sampler_uniform_draws.csv", draw_rows), ("small_frames_bruteforce_uniform.csv", small_checks)):
        if not data:
            continue
        with (RESULTS / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    (RESULTS / "sampler_uniform_summary.json").write_text(json.dumps({"cells": summary_rows, "small_frames_checks": small_checks, "seeds": [SEEDS.start, SEEDS.stop - 1], "uniformity_null_replicates": N_NULL, "diagnostic_rng_seed": 20261009}, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary_rows, indent=2))


if __name__ == "__main__":
    run()
