"""Verify the fresh, preregistered B1-prime confirmation batch."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = HERE / "B1prime" / "runs"
OUTPUT = HERE / "B1prime"
TAU_S = 0.050
TOLERANCE = 0.05
RESOLUTION = 1e-6
sys.path[:0] = [str(ROOT), str(ROOT / "simple-graph-experiments-v2" / "phase7" / "7D")]

from generator_v2 import read_trace  # noqa: E402
from oracle_metrics import compute_traffic_window_usable_uptime  # noqa: E402


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def rounded_times(events: list[dict[str, str]], kind_column: str, kind: str,
                  time_column: str) -> list[float]:
    return [round(float(row[time_column]) / RESOLUTION) * RESOLUTION
            for row in events if row[kind_column] == kind]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    results = []
    hashes: dict[str, str] = {}
    labels, frames = read_trace(HERE / "B1" / "fixtures" / "alternating_sr_60.csv")
    source, destination = labels.index("S"), labels.index("R")
    for loss in (125, 200, 1_000_000):
        name = f"downloss_{loss}"
        run = RUNS / name
        packets = rows(run / "packets_static.csv")
        times = rows(run / "times_static.csv")
        tx = [row for row in packets if row["event"] == "tx"]
        rx = [row for row in packets if row["event"] == "rx"]
        tx_by_id = {int(row["sequence"]): row for row in tx}
        rx_by_id = {int(row["sequence"]): row for row in rx}
        tx_ids = [int(row["sequence"]) for row in tx]
        rx_ids = [int(row["sequence"]) for row in rx]
        tx_time_match = rounded_times(times, "kind", "tx", "t") == [
            round(float(row["event_time_s"]) / RESOLUTION) * RESOLUTION for row in tx]
        rx_time_match = rounded_times(times, "kind", "rx", "t") == [
            round(float(row["event_time_s"]) / RESOLUTION) * RESOLUTION for row in rx]
        timely = 0
        late = 0
        missing_usable_up = 0
        negative_delay = 0
        for tx_row in tx:
            sequence = int(tx_row["sequence"])
            if tx_row["usable_connected"] != "1":
                continue
            rx_row = rx_by_id.get(sequence)
            if rx_row is None:
                missing_usable_up += 1
                continue
            delay = float(rx_row["event_time_s"]) - float(tx_row["event_time_s"])
            if delay < 0:
                negative_delay += 1
            elif delay <= TAU_S:
                timely += 1
            else:
                late += 1

        denominator = len(tx)
        q_tau = timely / denominator
        oracle = rows(run / "oracle_diagnostics_static.csv")[0]
        result_row = rows(run / "trace_replay_results.csv")[0]
        config = json.loads((run / "config.json").read_text(encoding="utf-8"))
        uptime = float(oracle["traffic_usable_uptime"])
        python_oracle = compute_traffic_window_usable_uptime(
            frames, source, destination, 0.1, 59.0, frame_duration_s=1.0,
            link_up_loss_db=10.0, link_down_loss_db=float(loss),
            tx_power_dbm=20.0, rx_sensitivity_dbm=-101.0,
            sparse_threshold_db=150.0, default_loss_db=1e6, interpolate=False)
        python_uptime = float(python_oracle["usable_uptime_ratio"])
        checks = {
            "resolved_v2_no_interpolation": config["channel_profile"] == "v2"
                and config["interpolate"] is False,
            "zero_effective_warmup": float(config["warmup_effective_s"]) == 0.0,
            "60_frames_applied": int(result_row["frame_apply_calls"]) == 60,
            "times_tx_stream_matches_packet_log_at_1us": tx_time_match,
            "times_rx_stream_matches_packet_log_at_1us": rx_time_match,
            "tx_sequence_ids_unique": len(tx_ids) == len(set(tx_ids)),
            "rx_sequence_ids_unique": len(rx_ids) == len(set(rx_ids)),
            "rx_ids_have_tx": all(sequence in tx_by_id for sequence in rx_ids),
            "qualifying_delays_nonnegative": negative_delay == 0,
            "app_tx_matches_log_count": int(result_row["app_tx_pkts"]) == denominator,
            "app_rx_matches_log_count": int(result_row["app_rx_pkts"]) == len(rx),
        }
        old_oracle_path = HERE / "B1" / "runs" / name / "oracle_diagnostics_static.csv"
        old_uptime = float(rows(old_oracle_path)[0]["traffic_usable_uptime"])
        checks["fresh_cpp_uptime_matches_saved_b1_at_1e_9"] = abs(uptime - old_uptime) <= 1e-9
        checks["cpp_python_usable_uptime_abs_error_le_1e_9"] = abs(uptime - python_uptime) <= 1e-9
        checks["within_frozen_0_05_tolerance"] = abs(q_tau - uptime) <= TOLERANCE
        results.append({
            "run": name,
            "down_loss_db": loss,
            "tau_s": TAU_S,
            "timely_usable_up_rx_numerator": timely,
            "all_offered_tx_denominator": denominator,
            "q_tau": q_tau,
            "cpp_usable_uptime": uptime,
            "python_usable_uptime": python_uptime,
            "abs_q_tau_minus_usable_uptime": abs(q_tau - uptime),
            "late_usable_up_rx_count": late,
            "missing_usable_up_rx_count": missing_usable_up,
            "negative_usable_up_delay_count": negative_delay,
            "all_checks_pass": all(checks.values()),
            **checks,
        })
        for filename in ("config.json", "oracle_diagnostics_static.csv",
                         "packet_diagnostics_static.csv", "packets_static.csv",
                         "routes_static.txt", "times_static.csv", "trace_replay_results.csv"):
            path = run / filename
            hashes[str(path.relative_to(ROOT))] = sha256(path)

    invocation_path = OUTPUT / "confirmation_invocations.json"
    prereg_path = HERE / "B1prime_prereg.md"
    source_path = Path("/home/hledirach/Documents/sp1-sp2/scratch/graph-run.cc")
    fixture_path = HERE / "B1" / "fixtures" / "alternating_sr_60.csv"
    for path in (invocation_path, prereg_path, source_path, fixture_path, Path(__file__)):
        hashes[str(path)] = sha256(path)
    summary = {
        "status": "fresh_confirmation_after_exploratory_offline_pass",
        "written_after_inspection_of_original_B1": True,
        "tau_s": TAU_S,
        "tolerance": TOLERANCE,
        "protocol_variants_consumed": 3,
        "total_phase7_spend": 11,
        "runs": results,
        "b1prime_pass": all(result["all_checks_pass"] for result in results),
        "original_b1_aggregate_pdr_gate_status": "failed; unchanged",
    }
    (OUTPUT / "confirmation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (OUTPUT / "confirmation_results.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    (OUTPUT / "confirmation_sha256_manifest.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["b1prime_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
