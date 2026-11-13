#!/usr/bin/env python3
"""Offline correction of A4.1 probe delivery gaps using app-timestamp identity.

Tx callback sequence values are global counters, not per-flow packet indices.
This script therefore identifies the single probe flow by its frozen Tx schedule
(first Tx at 0.1 s, one packet every 0.16384 s) and joins Rx rows to unique Tx
rows by app_tx_time_s. It does not launch or modify any simulation.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

A4 = Path(__file__).resolve().parent
TOLERANCE_S = 2e-8
FIRST_TX_S = 0.1
INTERVAL_S = 1024 * 8 / 50_000
STAGE = "4.1"
AUDIT_PATH = A4 / "all_up_gap_recompute.csv"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def atomic_write(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def schedule_index(app_tx_time: float) -> int | None:
    index = round((app_tx_time - FIRST_TX_S) / INTERVAL_S)
    expected = FIRST_TX_S + index * INTERVAL_S
    if index < 0 or abs(app_tx_time - expected) > TOLERANCE_S:
        return None
    return index


def analyze_packet_log(path: Path) -> dict[str, object]:
    tx_by_index: dict[int, float] = {}
    rx_by_index: dict[int, float] = {}
    duplicate_tx = duplicate_rx = unmatched_rx = malformed = 0
    for row in read_rows(path):
        try:
            app_tx = float(row["app_tx_time_s"])
            event_time = float(row["event_time_s"])
        except (KeyError, TypeError, ValueError):
            malformed += 1
            continue
        if not math.isfinite(app_tx) or not math.isfinite(event_time):
            malformed += 1
            continue
        index = schedule_index(app_tx)
        if index is None:
            malformed += 1
            continue
        if row.get("event") == "tx":
            if index in tx_by_index:
                duplicate_tx += 1
            else:
                tx_by_index[index] = app_tx
        elif row.get("event") == "rx":
            # Deliberately ignore sequence: it is not a per-flow packet identity.
            if index in rx_by_index:
                duplicate_rx += 1
                rx_by_index[index] = min(rx_by_index[index], event_time)
            else:
                rx_by_index[index] = event_time
        else:
            malformed += 1

    delivered_times: list[float] = []
    for index, event_time in rx_by_index.items():
        if index not in tx_by_index:
            unmatched_rx += 1
        elif event_time + TOLERANCE_S < tx_by_index[index]:
            malformed += 1
        else:
            delivered_times.append(event_time)
    delivered_times.sort()
    intervals = [(b - a, a, b) for a, b in zip(delivered_times, delivered_times[1:])]
    gap, gap_start, gap_end = max(intervals, default=(math.nan, math.nan, math.nan))
    return {
        "scheduled_tx_packets": len(tx_by_index),
        "unique_rx_packets": len(delivered_times),
        "duplicate_tx_rows": duplicate_tx,
        "duplicate_rx_rows": duplicate_rx,
        "unmatched_rx_rows": unmatched_rx,
        "malformed_or_off_schedule_rows": malformed,
        "gap_start_rx_s": "nan" if not math.isfinite(gap_start) else f"{gap_start:.9g}",
        "gap_end_rx_s": "nan" if not math.isfinite(gap_end) else f"{gap_end:.9g}",
        "intervals_gt_5s": sum(interval[0] > 5.0 for interval in intervals),
        "intervals_gt_15s": sum(interval[0] > 15.0 for interval in intervals),
        "all_up_gap_s": "nan" if not math.isfinite(gap) else f"{gap:.9g}",
        "packet_log": str(path.relative_to(A4)),
    }


def main() -> None:
    ledger_path = A4 / "runs.csv"
    ledger = read_rows(ledger_path)
    prior_audit = {row["run_id"]: row for row in read_rows(AUDIT_PATH)} if AUDIT_PATH.exists() else {}
    target_rows = [row for row in ledger if row.get("stage") == STAGE]
    if len(target_rows) != 45 or any(row.get("status") != "success" for row in target_rows):
        raise SystemExit(f"Expected 45 successful A4.1 rows; found {len(target_rows)}")

    audit_rows: list[dict[str, object]] = []
    gaps_by_run: dict[str, str] = {}
    for row in target_rows:
        packet_path = A4 / row["output_dir"] / f"packets_{row['protocol']}.csv"
        if not packet_path.is_file():
            raise SystemExit(f"Missing packet log: {packet_path}")
        result = analyze_packet_log(packet_path)
        result.update({
            "run_id": row["run_id"],
            "protocol": row["protocol"],
            "N": row["N"],
            "recorded_gap_before_correction_s": prior_audit.get(row["run_id"], {}).get(
                "recorded_gap_before_correction_s", row["all_up_gap_s"]
            ),
        })
        if result["duplicate_tx_rows"] or result["unmatched_rx_rows"] or result["malformed_or_off_schedule_rows"]:
            raise SystemExit(f"Packet identity validation failed for {row['run_id']}: {result}")
        if result["scheduled_tx_packets"] < 2 or result["unique_rx_packets"] < 2:
            raise SystemExit(f"Insufficient Tx/Rx observations for {row['run_id']}: {result}")
        audit_rows.append(result)
        gaps_by_run[row["run_id"]] = str(result["all_up_gap_s"])

    audit_fields = [
        "run_id", "protocol", "N", "packet_log", "scheduled_tx_packets", "unique_rx_packets",
        "duplicate_tx_rows", "duplicate_rx_rows", "unmatched_rx_rows",
        "malformed_or_off_schedule_rows", "gap_start_rx_s", "gap_end_rx_s",
        "intervals_gt_5s", "intervals_gt_15s", "recorded_gap_before_correction_s", "all_up_gap_s",
    ]
    atomic_write(AUDIT_PATH, audit_fields, audit_rows)

    for row in ledger:
        if row.get("stage") == STAGE:
            row["all_up_gap_s"] = gaps_by_run[row["run_id"]]
    atomic_write(ledger_path, list(ledger[0]), ledger)

    derived_runs_path = A4 / "derived_4.1_runs.csv"
    derived_runs = read_rows(derived_runs_path)
    if len(derived_runs) != 45:
        raise SystemExit(f"Expected 45 derived A4.1 rows; found {len(derived_runs)}")
    for row in derived_runs:
        row["all_up_gap_s"] = gaps_by_run[row["output_dir"].split("/")[-1]]
        row["dsdv_outage_drop"] = str(
            row["protocol"] == "dsdv" and float(row["all_up_gap_s"]) > 5
        ).lower()
    atomic_write(derived_runs_path, list(derived_runs[0]), derived_runs)

    summary_path = A4 / "derived_4.1.csv"
    summaries = read_rows(summary_path)
    if len(summaries) != 9:
        raise SystemExit(f"Expected 9 A4.1 summary rows; found {len(summaries)}")
    for summary in summaries:
        relevant = [
            float(row["all_up_gap_s"]) for row in derived_runs
            if row["protocol"] == summary["protocol"] and row["N"] == summary["N"]
        ]
        summary["gap_max_s"] = f"{max(relevant):.9g}" if relevant else "nan"
        summary["dsdv_any_gap_gt_5s"] = str(
            summary["protocol"] == "dsdv" and any(gap > 5 for gap in relevant)
        ).lower()
    atomic_write(summary_path, list(summaries[0]), summaries)

    print(f"Recomputed schedule-matched gaps for {len(audit_rows)} successful A4.1 runs.")
    print("protocol N max_gap_s dsdv_any_gap_gt_5s")
    for row in summaries:
        print(row["protocol"], row["N"], row["gap_max_s"], row["dsdv_any_gap_gt_5s"])
    print(f"Audit: {AUDIT_PATH.name}")


if __name__ == "__main__":
    main()
