"""Compute post-B1 exploratory B1-prime metrics on frozen saved runs only."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXTURE = HERE / "B1" / "fixtures" / "alternating_sr_60.csv"
RUNS = HERE / "B1" / "runs"
TAU_S = 0.050
TOLERANCE = 0.05
TIMESTAMP_RESOLUTION_S = 1e-6
sys.path[:0] = [str(ROOT), str(ROOT / "simple-graph-experiments-v2" / "phase7" / "7D")]

from generator_v2 import read_trace  # noqa: E402
from oracle_metrics import compute_traffic_window_usable_uptime  # noqa: E402


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def rounded_stream(rows: list[dict[str, str]], kind: str, time_column: str) -> list[float]:
    return [round(float(row[time_column]) / TIMESTAMP_RESOLUTION_S) * TIMESTAMP_RESOLUTION_S
            for row in rows if row["kind"] == kind]


def main() -> int:
    _, frames = read_trace(FIXTURE)
    results: list[dict[str, object]] = []
    for loss in (125, 200, 1_000_000):
        run_name = f"downloss_{loss}"
        run_dir = RUNS / run_name
        packet_rows = read_rows(run_dir / "packets_static.csv")
        time_rows = read_rows(run_dir / "times_static.csv")
        tx_rows = [row for row in packet_rows if row["event"] == "tx"]
        rx_rows = [row for row in packet_rows if row["event"] == "rx"]
        tx_ids = [int(row["sequence"]) for row in tx_rows]
        rx_ids = [int(row["sequence"]) for row in rx_rows]
        tx_by_id = {int(row["sequence"]): row for row in tx_rows}
        duplicate_tx_ids = len(tx_ids) - len(set(tx_ids))
        duplicate_rx_ids = len(rx_ids) - len(set(rx_ids))
        orphan_rx_ids = sum(sequence not in tx_by_id for sequence in rx_ids)

        time_tx = rounded_stream(time_rows, "tx", "t")
        time_rx = rounded_stream(time_rows, "rx", "t")
        packet_tx = [round(float(row["event_time_s"]) / TIMESTAMP_RESOLUTION_S)
                     * TIMESTAMP_RESOLUTION_S for row in tx_rows]
        packet_rx = [round(float(row["event_time_s"]) / TIMESTAMP_RESOLUTION_S)
                     * TIMESTAMP_RESOLUTION_S for row in rx_rows]
        tx_stream_match = time_tx == packet_tx
        rx_stream_match = time_rx == packet_rx

        rx_by_id = {int(row["sequence"]): row for row in rx_rows}
        timely_up_sequences: list[int] = []
        late_up_sequences: list[int] = []
        negative_delay_sequences: list[int] = []
        missing_up_sequences: list[int] = []
        for tx in tx_rows:
            sequence = int(tx["sequence"])
            if tx["usable_connected"] != "1":
                continue
            rx = rx_by_id.get(sequence)
            if rx is None:
                missing_up_sequences.append(sequence)
                continue
            delay = float(rx["event_time_s"]) - float(tx["event_time_s"])
            if delay < 0:
                negative_delay_sequences.append(sequence)
            elif delay <= TAU_S:
                timely_up_sequences.append(sequence)
            else:
                late_up_sequences.append(sequence)

        numerator = len(timely_up_sequences)
        denominator = len(tx_rows)
        q_tau = numerator / denominator if denominator else float("nan")
        oracle = read_rows(run_dir / "oracle_diagnostics_static.csv")[0]
        usable_uptime = float(oracle["traffic_usable_uptime"])
        labels, _ = read_trace(FIXTURE)
        source, destination = labels.index("S"), labels.index("R")
        python_oracle = compute_traffic_window_usable_uptime(
            frames, source, destination, 0.1, 59.0, frame_duration_s=1.0,
            link_up_loss_db=10.0, link_down_loss_db=float(loss),
            tx_power_dbm=20.0, rx_sensitivity_dbm=-101.0,
            sparse_threshold_db=150.0, default_loss_db=1e6, interpolate=False)
        python_usable = float(python_oracle["usable_uptime_ratio"])
        abs_error = abs(q_tau - usable_uptime)
        integrity = {
            "times_tx_stream_count_matches": len(time_tx) == len(tx_rows),
            "times_rx_stream_count_matches": len(time_rx) == len(rx_rows),
            "times_tx_stream_matches_packet_log_at_1us": tx_stream_match,
            "times_rx_stream_matches_packet_log_at_1us": rx_stream_match,
            "tx_sequence_ids_unique": duplicate_tx_ids == 0,
            "rx_sequence_ids_unique": duplicate_rx_ids == 0,
            "rx_sequences_have_tx": orphan_rx_ids == 0,
            "qualifying_delays_nonnegative": len(negative_delay_sequences) == 0,
            "cpp_python_usable_uptime_abs_error_le_1e_9": abs(usable_uptime - python_usable) <= 1e-9,
        }
        results.append({
            "run": run_name,
            "down_loss_db": loss,
            "tau_s": TAU_S,
            "numerator_timely_usable_up_rx": numerator,
            "denominator_all_offered_tx": denominator,
            "timely_usable_up_delivery_fraction": q_tau,
            "cpp_usable_uptime": usable_uptime,
            "python_usable_uptime": python_usable,
            "abs_q_tau_minus_cpp_usable_uptime": abs_error,
            "late_usable_up_rx_count": len(late_up_sequences),
            "missing_usable_up_rx_count": len(missing_up_sequences),
            "negative_usable_up_delay_count": len(negative_delay_sequences),
            "usable_up_tx_count": sum(row["usable_connected"] == "1" for row in tx_rows),
            "all_integrity_checks_pass": all(integrity.values()),
            "within_frozen_0_05_tolerance": abs_error <= TOLERANCE,
            **integrity,
        })

    summary = {
        "status": "exploratory_post_B1_offline_only",
        "written_after_inspection_of_B1": True,
        "simulator_variants_consumed_by_this_analysis": 0,
        "tau_s": TAU_S,
        "tolerance": TOLERANCE,
        "runs": results,
        "offline_all_runs_pass": all(row["within_frozen_0_05_tolerance"]
                                      and row["all_integrity_checks_pass"] for row in results),
        "fresh_three_variant_confirmation_required": True,
        "counts_as_passed_gate": False,
    }
    out_dir = HERE / "B1prime"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "offline_exploratory_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (out_dir / "offline_exploratory_results.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["offline_all_runs_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
