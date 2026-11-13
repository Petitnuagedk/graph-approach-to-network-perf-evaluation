#!/usr/bin/env python3
"""Generate A2b timeline candidates and exact-uniform diversity baselines."""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import random
import statistics
import subprocess
import sys
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
A2 = HERE.parent
ROOT = HERE.parents[3]
RESULTS = HERE / "results"
SOURCE = A2.parent / "A0R2" / "YaDyGaGa"
TIMELINE_SOURCE = SOURCE / "yadygaga" / "timelineBlockGenerator.py"
FRAME_SOURCE = SOURCE / "yadygaga" / "frameGenerator.py"
ASSEMBLY_SOURCE = SOURCE / "yadygaga" / "dynaGraph.py"
GRAPH_MANIFEST = A2.parent / "A1" / "results" / "graph_manifest.json"
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
LIVES = (0.3, 0.5, 0.7, 0.9)
STABILITY = {0.3: 0.3, 0.5: 0.5, 0.7: 0.7, 0.9: 0.9}
CANDIDATE_SEEDS = tuple(range(42, 242))
BASELINE_PAIRS = 100_000
GENERATOR = "yadygaga_patched"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def hamming(a: str, b: str) -> float:
    return sum(x != y for x, y in zip(a, b)) / len(a)


def normalized_d(a: str, b: str, life: float) -> float:
    q = round(120 * life) / 120
    return hamming(a, b) / (2 * min(q, 1 - q))


def pair_stats(schedules: list[str], life: float) -> dict[str, float | int]:
    ds = [normalized_d(a, b, life) for a, b in itertools.combinations(schedules, 2)]
    raw = [hamming(a, b) for a, b in itertools.combinations(schedules, 2)]
    return {
        "n_schedules": len(schedules),
        "unique": len(set(schedules)),
        "pair_count": len(ds),
        "mean_D": statistics.mean(ds) if ds else 0.0,
        "min_D": min(ds) if ds else 0.0,
        "mean_raw_H": statistics.mean(raw) if raw else 0.0,
        "fraction_pairs_D_lt_0_10": sum(d < 0.10 for d in ds) / len(ds) if ds else 0.0,
    }


def load_generator():
    sys.path.insert(0, str(SOURCE))
    from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

    return SPCTimelineBlockGenerator


def one_timeline(generator, life: float, stability: float, seed: int) -> str:
    result = generator(
        frames=120,
        path_life=life,
        stability=stability,
        seed=seed,
        mode="blocks",
        pathPersistency=0.75,
        behavior="patched",
    ).generate_blocks()
    return "".join("1" if state else "0" for state in result["timeline"])


def make_cell_config(life: float) -> dict:
    manifest = json.loads(GRAPH_MANIFEST.read_text(encoding="utf-8"))
    selected_graphs = {
        row["graph_id"]: row["edge_sha256"]
        for row in manifest
        if row["graph_id"].endswith("N92_r1")
    }
    return {
        "stage": "A2b",
        "generator": GENERATOR,
        "behavior": "patched",
        "frames": 120,
        "life": life,
        "stability": STABILITY[life],
        "mode": "blocks",
        "pathPersistency": 0.75,
        "candidate_seeds": list(CANDIDATE_SEEDS),
        "families": list(FAMILIES),
        "graph_ids": list(selected_graphs),
        "graph_edge_sha256": selected_graphs,
        "source_sha256": {
            "timelineBlockGenerator.py": file_hash(TIMELINE_SOURCE),
            "frameGenerator.py": file_hash(FRAME_SOURCE),
            "dynaGraph.py": file_hash(ASSEMBLY_SOURCE),
            "a1_graph_manifest.json": file_hash(GRAPH_MANIFEST),
            "generate_candidates.py": file_hash(Path(__file__).resolve()),
        },
        "a0r2_tree": "32b243bc84b587f1782ead0d0ac56382a57425e5",
        "python": sys.version,
        "networkx": nx.__version__,
        "baseline_pairs": BASELINE_PAIRS,
        "baseline_seed_rule": "left=1000000+2*i, right=1000001+2*i, i=0..99999",
        "timeout_seconds": 60,
    }


def worker(life: float) -> None:
    generator = load_generator()
    stability = STABILITY[life]
    cell_dir = RESULTS / f"life_{life:.1f}"
    cell_dir.mkdir(parents=True, exist_ok=True)
    config = make_cell_config(life)
    (cell_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    schedule_by_seed = {seed: one_timeline(generator, life, stability, seed) for seed in CANDIDATE_SEEDS}
    candidate_rows: list[dict] = []
    duplicate_first: dict[str, int] = {}
    first_five: list[int] = []
    for seed in CANDIDATE_SEEDS:
        bits = schedule_by_seed[seed]
        digest = hashlib.sha256(bits.encode()).hexdigest()
        if bits in duplicate_first:
            status, reason = "discarded", f"duplicate_of:{duplicate_first[bits]}"
        elif len(first_five) < 5:
            status, reason = "selected_first5_distinct", "first_distinct_in_seed_order"
            first_five.append(seed)
            duplicate_first[bits] = seed
        else:
            status, reason = "candidate_after_first5", "after_fifth_distinct"
            duplicate_first[bits] = seed
        for family in FAMILIES:
            candidate_rows.append({
                "generator": GENERATOR,
                "family": family,
                "life": life,
                "stability": stability,
                "seed": seed,
                "timeline_sha256": digest,
                "timeline_bits": bits,
                "candidate_status": status,
                "selection_reason": reason,
            })
    write_csv(cell_dir / "candidate_timelines.csv", candidate_rows, ["generator", "family", "life", "stability", "seed", "timeline_sha256", "timeline_bits", "candidate_status", "selection_reason"])

    # Exact-uniform Monte Carlo expectation, independent of candidate seed pool.
    baseline_values: list[float] = []
    for index in range(BASELINE_PAIRS):
        left = one_timeline(generator, life, stability, 1_000_000 + 2 * index)
        right = one_timeline(generator, life, stability, 1_000_001 + 2 * index)
        baseline_values.append(normalized_d(left, right, life))
    baseline_mean = statistics.mean(baseline_values)
    baseline_sd = statistics.stdev(baseline_values)
    baseline_se = baseline_sd / math.sqrt(BASELINE_PAIRS)

    # One life-level schedule list because Boolean sampler is family-independent.
    unique_schedules = list(dict.fromkeys(schedule_by_seed.values()))
    seed_for_schedule: dict[str, int] = {}
    for seed in CANDIDATE_SEEDS:
        seed_for_schedule.setdefault(schedule_by_seed[seed], seed)
    selected_greedy: list[int] = [42]
    selected_bits: list[str] = [schedule_by_seed[42]]
    while len(selected_greedy) < 10:
        eligible = [seed for seed in CANDIDATE_SEEDS if seed not in selected_greedy]
        best_seed = min(
            eligible,
            key=lambda candidate_seed: (
                -min(normalized_d(schedule_by_seed[candidate_seed], selected, life) for selected in selected_bits),
                candidate_seed,
            ),
        )
        selected_greedy.append(best_seed)
        selected_bits.append(schedule_by_seed[best_seed])

    selected_rows: list[dict] = []
    for family in FAMILIES:
        for label, seeds in (
            ("greedy5", selected_greedy[:5]),
            ("greedy10", selected_greedy),
            ("first5_distinct", first_five),
        ):
            bits = [schedule_by_seed[seed] for seed in seeds]
            stats = pair_stats(bits, life)
            for order, seed in enumerate(seeds, start=1):
                selected_rows.append({
                    "generator": GENERATOR,
                    "family": family,
                    "life": life,
                    "selection": label,
                    "order": order,
                    "seed": seed,
                    "timeline_sha256": hashlib.sha256(schedule_by_seed[seed].encode()).hexdigest(),
                    **stats,
                    "exact_uniform_mean_D": baseline_mean,
                    "exact_uniform_se": baseline_se,
                    "mean_D_over_uniform": stats["mean_D"] / baseline_mean if baseline_mean else "NA",
                    "independent_placement_D": max(life, 1 - life),
                    "mean_D_over_independent": stats["mean_D"] / max(life, 1 - life),
                    "M_exact": exact_support(120, life, stability),
                    "route_distinct_pair_min_5": math.ceil(0.90 * (1 - 1 / exact_support(120, life, stability)) * 10),
                })
    write_csv(cell_dir / "selected_seeds_and_pair_stats.csv", selected_rows, ["generator", "family", "life", "selection", "order", "seed", "timeline_sha256", "n_schedules", "unique", "pair_count", "mean_D", "min_D", "mean_raw_H", "fraction_pairs_D_lt_0_10", "exact_uniform_mean_D", "exact_uniform_se", "mean_D_over_uniform", "independent_placement_D", "mean_D_over_independent", "M_exact", "route_distinct_pair_min_5"])

    summary_rows = []
    candidate_count_by_hash = {}
    for bits in schedule_by_seed.values():
        candidate_count_by_hash[bits] = candidate_count_by_hash.get(bits, 0) + 1
    largest_group = max(candidate_count_by_hash.values())
    exact_m = exact_support(120, life, stability)
    for family in FAMILIES:
        for label, seeds in (("greedy5", selected_greedy[:5]), ("greedy10", selected_greedy), ("first5_distinct", first_five)):
            stats = pair_stats([schedule_by_seed[seed] for seed in seeds], life)
            summary_rows.append({
                "generator": GENERATOR,
                "family": family,
                "life": life,
                "stability": stability,
                "selection": label,
                "selected_seeds": ";".join(map(str, seeds)),
                **stats,
                "candidate_count": len(CANDIDATE_SEEDS),
                "candidate_unique": len(candidate_count_by_hash),
                "largest_duplicate_group": largest_group,
                "exact_support_M": exact_m,
                "exact_uniform_mean_D": baseline_mean,
                "exact_uniform_sd": baseline_sd,
                "exact_uniform_se": baseline_se,
                "mean_D_over_uniform": stats["mean_D"] / baseline_mean if baseline_mean else "NA",
                "independent_placement_D": max(life, 1 - life),
                "mean_D_over_independent": stats["mean_D"] / max(life, 1 - life),
                "selected_5_mean_D_gate": stats["mean_D"] >= 0.90 * baseline_mean if label == "greedy5" else "",
                "duplicate_group_gate": largest_group <= 20,
                "route_distinct_pair_min_5": math.ceil(0.90 * (1 - 1 / exact_m) * 10),
            })
    write_csv(cell_dir / "diversity_summary.csv", summary_rows, ["generator", "family", "life", "stability", "selection", "selected_seeds", "n_schedules", "unique", "pair_count", "mean_D", "min_D", "mean_raw_H", "fraction_pairs_D_lt_0_10", "candidate_count", "candidate_unique", "largest_duplicate_group", "exact_support_M", "exact_uniform_mean_D", "exact_uniform_sd", "exact_uniform_se", "mean_D_over_uniform", "independent_placement_D", "mean_D_over_independent", "selected_5_mean_D_gate", "duplicate_group_gate", "route_distinct_pair_min_5"])


def exact_support(f: int, q: float, s: float) -> int:
    u = round(f * q)
    d = f - u
    k = max(1, min(u, round(1 + (1 - s) * (u - 1))))
    if u == 0 or u == f:
        return 1
    if k > d + 1:
        return 0
    j_min = max(1, k - 1)
    j_max = min(d, k + 1)
    return math.comb(u - 1, k - 1) * sum(
        (2 if j == k else 1) * math.comb(d - 1, j - 1)
        for j in range(j_min, j_max + 1)
    )


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(float(sys.argv[2]))
        return
    for life in LIVES:
        command = [sys.executable, str(Path(__file__).resolve()), "--worker", f"{life:.1f}"]
        try:
            subprocess.run(command, check=True, timeout=60, cwd=HERE)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"A2b life={life:.1f} candidate/baseline operation timed out at 60 seconds; no retry") from error

    cross_family_rows = []
    for life in LIVES:
        path = RESULTS / f"life_{life:.1f}" / "candidate_timelines.csv"
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for seed in CANDIDATE_SEEDS:
            digests = {row["timeline_sha256"] for row in rows if int(row["seed"]) == seed}
            assert len(digests) == 1, (life, seed, digests)
            cross_family_rows.append({"generator": GENERATOR, "life": life, "seed": seed, "family_count": len(FAMILIES), "distinct_hash_count_across_families": len(digests), "family_independent": len(digests) == 1, "timeline_sha256": next(iter(digests))})
    write_csv(RESULTS / "cross_family_timeline_identity.csv", cross_family_rows, ["generator", "life", "seed", "family_count", "distinct_hash_count_across_families", "family_independent", "timeline_sha256"])
    print(json.dumps({"candidate_timelines": 800, "exact_uniform_pairs": 4 * BASELINE_PAIRS, "cross_family_rows": len(cross_family_rows), "cross_family_identity_pass": True}, indent=2))


if __name__ == "__main__":
    main()
