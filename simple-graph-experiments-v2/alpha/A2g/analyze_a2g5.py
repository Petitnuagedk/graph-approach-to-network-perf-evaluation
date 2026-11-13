#!/usr/bin/env python3
"""Deterministic A2g-5 synthesis of A2f exact quotas and A2g-2 pool results."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "alpha" / "A2g" / "A2g-5"
PREREG = ROOT / "alpha" / "A2g" / "a2g5_prereg.md"
PSTAR = ROOT / "alpha" / "A2g" / "A2g-2" / "pstar_per_seed.csv"
SUPPLY = ROOT / "alpha" / "A2g" / "A2g-2" / "per_seed_supply.csv"
LEDGER = ROOT / "alpha" / "A2g" / "A2g-2" / "operation_log.csv"
FPS_VALUES = (1, 2)
LIVES = (0.3, 0.5, 0.7, 0.9)
DURATION_S = 120
MEAN_UP_TARGET_S = 12.0
PACKET_INTERVAL_S = 1024 * 8 / 50_000
PACKET_TWO_INTERVAL_S = 2 * PACKET_INTERVAL_S


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"refusing empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fixed_rows: list[dict[str, object]] = []
    for fps in FPS_VALUES:
        frames = DURATION_S * fps
        frame_s = 1 / fps
        packet_target_frames = PACKET_TWO_INTERVAL_S * fps
        for life in LIVES:
            up = round(frames * life)
            down = frames - up
            kmax = min(up, down + 1)
            target_frames = MEAN_UP_TARGET_S * fps
            raw_k = up / target_frames
            target_k_is_int = math.isclose(raw_k, round(raw_k), rel_tol=0, abs_tol=1e-12)
            target_k = int(round(raw_k)) if target_k_is_int else "NA"
            target_feasible = bool(target_k_is_int and 1 <= int(target_k) <= kmax)
            packet_k_values = [k for k in range(1, kmax + 1) if math.isclose(up / k / fps, PACKET_TWO_INTERVAL_S, rel_tol=0, abs_tol=1e-12)]
            packet_exact = bool(packet_k_values)
            fixed_rows.append({
                "duration_s": DURATION_S,
                "fps": fps,
                "F": frames,
                "frame_duration_s": f"{frame_s:.8f}",
                "life": f"{life:.1f}",
                "U": up,
                "D": down,
                "Kmax": kmax,
                "target_mean_up_s": f"{MEAN_UP_TARGET_S:.2f}",
                "target_mean_up_frames": f"{target_frames:.2f}",
                "target_K": target_k,
                "target_exact_quota_feasible": target_feasible,
                "exact_mean_up_min_s": f"{up / kmax / fps:.8f}",
                "exact_mean_up_max_s": f"{up / fps:.8f}",
                "two_packet_target_s": f"{PACKET_TWO_INTERVAL_S:.8f}",
                "two_packet_target_frames": f"{packet_target_frames:.8f}",
                "two_packet_target_exact_support": packet_exact,
                "two_packet_target_status": "exactly_reachable" if packet_exact else "unreachable_on_exact_quota_support",
                "two_packet_to_frame_duration_ratio": f"{PACKET_TWO_INTERVAL_S / frame_s:.8f}",
                "resolution_screen_pass": frame_s >= PACKET_TWO_INTERVAL_S,
            })

    pstar_rows = load_csv(PSTAR)
    graph_group: dict[tuple[str, str, int, int], list[dict[str, str]]] = defaultdict(list)
    for row in pstar_rows:
        graph_group[(row["family"], row["graph_id"], int(row["N"]), int(row["trials"]))].append(row)
    graph_summary: list[dict[str, object]] = []
    for (family, graph_id, n, trials), group in sorted(graph_group.items()):
        for frames in (120, 240):
            key = f"pstar_F{frames}"
            values = [float(r[key]) for r in group if r[key] not in ("", "NA", "nan")]
            mean = sum(values) / len(values) if values else None
            sd = math.sqrt(sum((x - mean) ** 2 for x in values) / (len(values) - 1)) if len(values) > 1 else None
            graph_summary.append({
                "family": family, "graph_id": graph_id, "N": n, "trials": trials, "F": frames,
                "n_registered_seeds": 3, "n_defined_seed_pstar": len(values),
                "seed_pstar_values": ";".join(f"{float(r[key]):.6g}" if r[key] not in ("", "NA", "nan") else "NA" for r in sorted(group, key=lambda x: int(x["seed"]))),
                "pstar_mean": f"{mean:.8g}" if mean is not None else "NA",
                "pstar_sample_sd_ddof1": f"{sd:.8g}" if sd is not None else "NA",
                "all_seed_pstar_defined": len(values) == 3,
                "status": "successful_pool_data" if len(values) == 3 else "incomplete_or_undefined",
            })

    supply = load_csv(SUPPLY)
    ledger = load_csv(LEDGER)
    ledger_by_id = {row["operation"]: row for row in ledger}
    # Collapse each operation's four life rows to the registered all-life criterion.
    op_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in supply:
        if int(row["F"]) in (120, 240):
            op_rows[row["operation"]].append(row)
    op_meta: dict[str, dict[str, str]] = {}
    for op, rows in op_rows.items():
        first = rows[0]
        op_meta[op] = first
    planned_graph_seeds = sorted({(r["family"], r["graph_id"], int(r["N"]), int(r["trials"]), int(r["seed"])) for r in pstar_rows})
    readiness_rows: list[dict[str, object]] = []
    for trials in (3000, 10000):
        for p in (i / 10 for i in range(1, 10)):
            for frames in (120, 240):
                eligible = 0
                passed = 0
                missing = 0
                for family, graph_id, n, seed_trials, seed in planned_graph_seeds:
                    if seed_trials != trials:
                        continue
                    # Operation identifiers are the authoritative cell IDs; graph IDs distinguish family realizations.
                    found = next((op for op, r in op_meta.items() if r["family"] == family and r["graph_id"] == graph_id and int(r["seed"]) == seed and int(r["trials"]) == trials and math.isclose(float(r["p_edge"]), p, abs_tol=1e-9)), None)
                    eligible += 1
                    if found is None:
                        missing += 1
                        continue
                    rows = [r for r in op_rows[found] if int(r["F"]) == frames]
                    # Four life rows are required; every one must satisfy the strict finite-pool quotas.
                    if len(rows) == 4 and all(r["supply_ready"].strip().lower() == "true" for r in rows):
                        passed += 1
                readiness_rows.append({
                    "trials": trials, "p_edge": f"{p:.1f}", "F": frames,
                    "planned_graph_seed_cells": eligible, "strict_all_life_supply_passes": passed,
                    "missing_or_interrupted": missing, "pass_fraction_of_planned": f"{passed / eligible:.8f}" if eligible else "NA",
                    "status": "observed_cell_summary; missing counts as not established, not imputed",
                })

    write_csv(OUT / "fixed_duration_table.csv", fixed_rows)
    write_csv(OUT / "pool_support_by_graph.csv", graph_summary)
    write_csv(OUT / "pool_readiness_by_p.csv", readiness_rows)
    inputs = [PREREG, PSTAR, SUPPLY, LEDGER]
    manifest = [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in inputs]
    write_csv(OUT / "input_manifest.csv", manifest)
    summary = {
        "stage": "A2g-5", "duration_s": DURATION_S, "fps_values": FPS_VALUES,
        "lives": LIVES, "mean_up_target_s": MEAN_UP_TARGET_S,
        "packet_transmission_s": PACKET_INTERVAL_S, "two_packet_interval_s": PACKET_TWO_INTERVAL_S,
        "fixed_duration_rows": fixed_rows, "graph_pool_support_rows": len(graph_summary),
        "readiness_rows": len(readiness_rows), "input_manifest": manifest,
        "interpretation": "offline descriptive operating-region synthesis; no protocol or performance claim",
    }
    summary_path = OUT / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_rows = [{"path": PREREG.relative_to(ROOT).as_posix(), "sha256": sha256(PREREG), "role": "preregistration"},
                     {"path": Path(__file__).relative_to(ROOT).as_posix(), "sha256": sha256(Path(__file__)), "role": "analyzer"}]
    for path in sorted(OUT.glob("*")):
        if path.is_file() and path.name != "artifact_manifest.csv":
            artifact_rows.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "role": "generated_output"})
    write_csv(OUT / "artifact_manifest.csv", artifact_rows)
    print(json.dumps({
        "fixed_duration_rows": len(fixed_rows), "pool_support_rows": len(graph_summary),
        "pool_readiness_rows": len(readiness_rows), "two_packet_interval_s": PACKET_TWO_INTERVAL_S,
        "fixed_grid_resolution_passes": all(bool(r["resolution_screen_pass"]) for r in fixed_rows),
        "exact_12s_targets_pass": all(bool(r["target_exact_quota_feasible"]) for r in fixed_rows),
        "exact_two_packet_targets_reachable": sum(bool(r["two_packet_target_exact_support"]) for r in fixed_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
