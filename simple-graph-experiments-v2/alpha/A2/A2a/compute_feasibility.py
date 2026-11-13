#!/usr/bin/env python3
"""Compute registered exact timeline feasibility/support map without sampling."""
from __future__ import annotations

import csv
import hashlib
import itertools
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FRAMES = (60, 120, 240)
LIVES = tuple(i / 10 for i in range(1, 10))
STABILITIES = tuple(i / 20 for i in range(21))
UPRUN_THRESHOLD = 30


def choose(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def timeline_support(f: int, q: float, s: float) -> dict[str, int | float | bool | str]:
    u = round(f * q)
    d = f - u
    k = max(1, min(u, round(1 + (1 - s) * (u - 1)))) if u else 0
    feasible = (u == 0 or u == f or k <= d + 1)
    if u == 0 or u == f:
        m = 1
        j_min = j_max = 0
        t_min = t_max = 0
    elif not feasible:
        m = 0
        j_min = j_max = 0
        t_min = t_max = 0
    else:
        j_min = max(1, k - 1)
        j_max = min(d, k + 1)
        m = choose(u - 1, k - 1) * sum(
            (2 if j == k else 1) * choose(d - 1, j - 1)
            for j in range(j_min, j_max + 1)
        )
        t_min, t_max = k + j_min - 1, k + j_max - 1
    return {
        "F": f,
        "life": q,
        "stability": s,
        "U": u,
        "D": d,
        "K": k,
        "feasible": feasible,
        "M": m,
        "log10_M": math.log10(m) if m else "-inf",
        "J_min": j_min,
        "J_max": j_max,
        "transitions_min": t_min,
        "transitions_max": t_max,
    }


def crosscheck_support(row: dict[str, int | float | bool | str]) -> int:
    """Independent factorial/recurrence evaluation of the same composition count."""
    u, d, k = int(row["U"]), int(row["D"]), int(row["K"])
    if u == 0 or u == int(row["F"]):
        return 1
    if not row["feasible"]:
        return 0
    up_compositions = math.factorial(u - 1) // (
        math.factorial(k - 1) * math.factorial(u - k)
    )
    down_count = 0
    for j in range(int(row["J_min"]), int(row["J_max"]) + 1):
        down_compositions = math.factorial(d - 1) // (
            math.factorial(j - 1) * math.factorial(d - j)
        )
        boundary_arrangements = 2 if j == k else 1
        down_count += boundary_arrangements * down_compositions
    return up_compositions * down_count


def csv_write(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    map_rows = [timeline_support(f, q, s) for f, q, s in itertools.product(FRAMES, LIVES, STABILITIES)]
    assert len(map_rows) == 567
    for row in map_rows:
        assert int(row["M"]) == crosscheck_support(row), row
    map_fields = ["F", "life", "stability", "U", "D", "K", "feasible", "M", "log10_M", "J_min", "J_max", "transitions_min", "transitions_max"]
    csv_write(RESULTS / "feasibility_map.csv", map_rows, map_fields)

    rules = []
    life_summaries = []
    for f in FRAMES:
        for q in LIVES:
            cell = [r for r in map_rows if int(r["F"]) == f and float(r["life"]) == q]
            feasible = [r for r in cell if r["feasible"]]
            candidates: dict[str, dict | None] = {}
            candidates["s_min"] = min(feasible, key=lambda r: float(r["stability"])) if feasible else None
            candidates["s_div"] = max(feasible, key=lambda r: (float(r["log10_M"]), -float(r["stability"]))) if feasible else None
            stable_rows = [r for r in cell if int(r["K"]) == 1 and r["feasible"]]
            candidates["s_max_K1"] = max(stable_rows, key=lambda r: float(r["stability"])) if stable_rows else None
            div = candidates["s_div"]
            minimum = candidates["s_min"]
            if div is None:
                default_rule = "NONE"
            elif float(div["U"]) / int(div["K"]) > UPRUN_THRESHOLD:
                default_rule = "s_min"
            else:
                default_rule = "s_div"
            for name, candidate in candidates.items():
                if candidate is None:
                    rules.append({"F": f, "life": q, "rule": name, "stability": "NONE", "U": round(f*q), "D": f-round(f*q), "K": "", "feasible": False, "M": 0, "log10_M": "-inf", "mean_up_run": "", "J_min": "", "J_max": "", "transitions_min": "", "transitions_max": "", "default_rule": default_rule})
                else:
                    rules.append({"F": f, "life": q, "rule": name, **{key: candidate[key] for key in ("stability", "U", "D", "K", "feasible", "M", "log10_M", "J_min", "J_max", "transitions_min", "transitions_max")}, "mean_up_run": (float(candidate["U"]) / int(candidate["K"])) if int(candidate["K"]) else "", "default_rule": default_rule})
            life_summaries.append({
                "F": f,
                "life": q,
                "any_feasible": bool(feasible),
                "lowest_feasible_stability": float(minimum["stability"]) if minimum else "NONE",
                "highest_feasible_stability": max(float(r["stability"]) for r in feasible) if feasible else "NONE",
                "highest_feasible_K": max(int(r["K"]) for r in feasible) if feasible else "NONE",
                "infeasible_stabilities": ";".join(str(r["stability"]) for r in cell if not r["feasible"]),
                "default_rule": default_rule,
            })
    rule_fields = ["F", "life", "rule", "stability", "U", "D", "K", "feasible", "M", "log10_M", "mean_up_run", "J_min", "J_max", "transitions_min", "transitions_max", "default_rule"]
    csv_write(RESULTS / "stability_rule_comparison.csv", rules, rule_fields)
    csv_write(RESULTS / "life_feasibility_summary.csv", life_summaries, ["F", "life", "any_feasible", "lowest_feasible_stability", "highest_feasible_stability", "highest_feasible_K", "infeasible_stabilities", "default_rule"])
    expected_lives = (0.3, 0.5, 0.7, 0.9)
    assert all(any(r["F"] == 120 and r["life"] == q and r["any_feasible"] for r in life_summaries) for q in expected_lives)
    hashes = {}
    for file in sorted(RESULTS.glob("*.csv")):
        hashes[file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
    print({"map_rows": len(map_rows), "rule_rows": len(rules), "crosscheck": "all exact M matched factorial implementation", "hashes": hashes})


if __name__ == "__main__":
    main()
