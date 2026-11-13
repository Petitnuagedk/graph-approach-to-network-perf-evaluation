#!/usr/bin/env python3
"""Compute exact-quota up/down run and protocol timer-ratio supports."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREREG = HERE / "prereg.md"
FRAMES = (60, 120, 240)
LIVES = tuple(i / 10 for i in range(1, 10))
FPS_VALUES = (0.5, 1.0, 2.0, 4.0)
TIMERS = {
    "OLSR_Hello": 2.0,
    "OLSR_TC": 5.0,
    "AODV_Hello": 1.0,
    "AODV_ActiveRouteTimeout": 3.0,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    boundary_rows: list[dict] = []
    rho_rows: list[dict] = []
    for frames in FRAMES:
        for life in LIVES:
            up = round(frames * life)
            down = frames - up
            k_max = min(up, down + 1)
            k_values = list(range(1, k_max + 1))
            mean_up = [up / k for k in k_values]
            down_values_by_k = {
                k: [down / j for j in range(max(1, k - 1), min(down, k + 1) + 1)]
                for k in k_values
            }
            all_down = [value for values in down_values_by_k.values() for value in values]
            j_min_extreme = list(range(max(1, 1 - 1), min(down, 1 + 1) + 1))
            j_max_extreme = list(range(max(1, k_max - 1), min(down, k_max + 1) + 1))
            row = {
                "F": frames,
                "life": f"{life:.1f}",
                "U": up,
                "D": down,
                "K_min": 1,
                "K_max": k_max,
                "K_feasible": ";".join(map(str, k_values)),
                "mean_up_min_frames": min(mean_up),
                "mean_up_max_frames": max(mean_up),
                "mean_up_exact_support_frames": ";".join(f"{up}/{k}" for k in k_values),
                "K1_J_range": f"{min(j_min_extreme)}..{max(j_min_extreme)}",
                "K1_mean_down_range_frames": f"{min(down / j for j in j_min_extreme):.12g}..{max(down / j for j in j_min_extreme):.12g}",
                "Kmax_J_range": f"{min(j_max_extreme)}..{max(j_max_extreme)}",
                "Kmax_mean_down_range_frames": f"{min(down / j for j in j_max_extreme):.12g}..{max(down / j for j in j_max_extreme):.12g}",
                "overall_mean_down_min_frames": min(all_down),
                "overall_mean_down_max_frames": max(all_down),
                "overall_J_min": min(j for k in k_values for j in range(max(1, k - 1), min(down, k + 1) + 1)),
                "overall_J_max": max(j for k in k_values for j in range(max(1, k - 1), min(down, k + 1) + 1)),
            }
            boundary_rows.append(row)
            for fps in FPS_VALUES:
                for timer_name, timer_seconds in TIMERS.items():
                    ratios = [((up / k) / fps) / timer_seconds for k in k_values]
                    rho_rows.append({
                        "F": frames,
                        "life": f"{life:.1f}",
                        "U": up,
                        "D": down,
                        "K_max": k_max,
                        "fps": fps,
                        "protocol_timer": timer_name,
                        "timer_seconds": timer_seconds,
                        "rho_min": min(ratios),
                        "rho_max": max(ratios),
                        "rho_exact_support": ";".join(f"{((up / k) / fps) / timer_seconds:.12g}" for k in k_values),
                        "unreachable_rule": "rho must correspond to one K in 1..K_max; all off-support values are unreachable",
                    })

    out_boundary = HERE / "boundary_table.csv"
    out_rho = HERE / "rho_reachability.csv"
    write_csv(out_boundary, boundary_rows, list(boundary_rows[0]))
    write_csv(out_rho, rho_rows, list(rho_rows[0]))
    expected_checks = {
        (60, "0.5"): (30, 30, 30, 1.0, 30.0),
        (120, "0.9"): (108, 12, 13, 108 / 13, 108.0),
        (240, "0.1"): (24, 216, 24, 1.0, 24.0),
    }
    checked = 0
    for (frames, life), expected in expected_checks.items():
        row = next(item for item in boundary_rows if item["F"] == frames and item["life"] == life)
        actual = (row["U"], row["D"], row["K_max"], row["mean_up_min_frames"], row["mean_up_max_frames"])
        if actual != expected:
            raise AssertionError(f"hand-check mismatch {(frames, life)}: {actual} != {expected}")
        checked += 1
    if len(boundary_rows) != 27 or len(rho_rows) != 432 or checked != 3:
        raise AssertionError("row-count or hand-check gate failed")
    for row in boundary_rows:
        if len(row["K_feasible"].split(";")) != row["K_max"]:
            raise AssertionError("K support size mismatch")
        if not math.isclose(row["mean_up_min_frames"], row["U"] / row["K_max"]):
            raise AssertionError("mean-up minimum identity failed")
    summary = {
        "boundary_rows": len(boundary_rows),
        "rho_rows": len(rho_rows),
        "hand_checks_passed": checked,
        "all_formula_identities_pass": True,
        "preregistration_sha256": sha256(PREREG),
        "boundary_table_sha256": sha256(out_boundary),
        "rho_reachability_sha256": sha256(out_rho),
        "python_rounding": "built-in round-to-even",
        "fps_values": FPS_VALUES,
        "timers_seconds": TIMERS,
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
