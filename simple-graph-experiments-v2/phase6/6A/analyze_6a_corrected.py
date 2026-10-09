#!/usr/bin/env python3
"""Canonical 6A recomputation from Phase 5 frames and Phase 6A packet logs."""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from oracle_metrics import (
    compute_deadline_pdr,
    compute_oracle_metrics,
    compute_traffic_window_usable_uptime,
    is_time_connected,
)

PHASE5 = ROOT / "simple-graph-experiments-v2" / "phase5" / "line"
RUNS = ROOT / "simple-graph-experiments-v2" / "phase6" / "6A" / "runs"
OUT = Path(__file__).resolve().parent
CONDITIONS = {
    "path_life_0.5_stability_0.0": ("stability", "stability_0.0000"),
    "path_life_0.7_stability_0.8": ("path_life", "path_life_0.7000"),
    "path_life_0.9_stability_0.8": ("path_life", "path_life_0.9000"),
}
PROTOCOLS = ("olsr", "aodv", "static")


def read_frames(path: Path):
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    header_index = next(i for i, row in enumerate(rows) if row and any(x.strip() for x in row))
    labels = [x.strip() for x in rows[header_index]]
    frames, matrix = [], []
    for row in rows[header_index + 1 :]:
        if not row or not any(x.strip() for x in row):
            if matrix:
                frames.append(matrix)
                matrix = []
        else:
            matrix.append([int(value) for value in row])
    if matrix:
        frames.append(matrix)
    return labels, frames


def read_csv(path: Path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def sample_sd(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def main() -> None:
    realization_rows = []
    condition_rows = []
    pooled_h1 = {key: 0 for key in ("aodv_rx", "frame_down_rx", "usable_down_rx", "delay_gt_1_rx", "delay_gt_2_rx", "down_or_delay_gt_1_rx")}
    pooled_h3 = {protocol: {key: 0 for key in ("offered", "sink_rx", "unique_rx", "duplicates", "app_no_route", "app_route_error", "mac_queue", "mac_tx", "phy_tx", "phy_rx")} for protocol in PROTOCOLS}
    pooled_h4 = {"static_lost": 0, "static_usable_lost": 0, "static_first_usable_second_lost": 0}

    for condition, (sweep, label) in CONDITIONS.items():
        cell_rows = []
        for realization in range(1, 6):
            graph_id = f"graph_{realization:04d}"
            frame_path = PHASE5 / sweep / "dynamic_frames" / graph_id / label / "frames.csv"
            labels, frames = read_frames(frame_path)
            source, destination = labels.index("S"), labels.index("R")
            raw = compute_oracle_metrics(frames, source, destination)
            traffic = compute_traffic_window_usable_uptime(
                frames, source, destination, 0.1, (len(frames) - 1),
                frame_duration_s=1.0, link_up_loss_db=10.0,
                link_down_loss_db=125.0, tx_power_dbm=20.0,
                rx_sensitivity_dbm=-101.0, sparse_threshold_db=150.0,
                default_loss_db=1e6, interpolate=True,
            )
            run_dir = RUNS / condition / graph_id
            result_rows = read_csv(run_dir / "trace_replay_results.csv")
            protocol_results = {row["protocol"]: row for row in result_rows}
            pdr = {name: float(protocol_results[name]["pdr"]) for name in PROTOCOLS}
            row = {
                "condition": condition, "graph_id": graph_id,
                "raw_all_frame_uptime": raw["uptime_ratio"],
                "traffic_window_frame_uptime": traffic["frame_uptime_ratio"],
                "traffic_window_usable_uptime": traffic["usable_uptime_ratio"],
                "usable_minus_raw_uptime": traffic["usable_uptime_ratio"] - raw["uptime_ratio"],
                "traffic_start_relative_s": 0.1,
                "traffic_stop_relative_s": len(frames) - 1,
                "traffic_window_s": traffic["traffic_window_s"],
                "aodv_pdr": pdr["aodv"], "olsr_pdr": pdr["olsr"], "static_pdr": pdr["static"],
                "aodv_minus_raw_uptime": pdr["aodv"] - raw["uptime_ratio"],
                "aodv_minus_usable_uptime": pdr["aodv"] - traffic["usable_uptime_ratio"],
                "olsr_minus_usable_uptime": pdr["olsr"] - traffic["usable_uptime_ratio"],
                "static_minus_usable_uptime": pdr["static"] - traffic["usable_uptime_ratio"],
            }
            cell_rows.append(row)

            # Packet evidence: unique AODV receives and the original binary frame-state H1 criterion.
            aodv_events = read_csv(run_dir / "packets_aodv.csv")
            rx_aodv = [item for item in aodv_events if item["event"] == "rx"]
            rx_frame_down = sum(item["frame_connected"] == "0" for item in rx_aodv)
            rx_usable_down = sum(item["usable_connected"] == "0" for item in rx_aodv)
            delay_gt_1 = sum(float(item["delay_s"]) > 1.0 for item in rx_aodv)
            delay_gt_2 = sum(float(item["delay_s"]) > 2.0 for item in rx_aodv)
            frame_down_or_delay = sum(item["frame_connected"] == "0" or float(item["delay_s"]) > 1.0 for item in rx_aodv)
            for key, count in (("aodv_rx", len(rx_aodv)), ("frame_down_rx", rx_frame_down),
                               ("usable_down_rx", rx_usable_down), ("delay_gt_1_rx", delay_gt_1),
                               ("delay_gt_2_rx", delay_gt_2), ("down_or_delay_gt_1_rx", frame_down_or_delay)):
                pooled_h1[key] += count
            row.update({
                "aodv_unique_rx": len(rx_aodv), "aodv_rx_frame_down": rx_frame_down,
                "aodv_rx_usable_down": rx_usable_down, "aodv_delay_gt_1s": delay_gt_1,
                "aodv_delay_gt_2s": delay_gt_2, "aodv_frame_down_or_delay_gt_1s": frame_down_or_delay,
            })

            # Sequence-validated diagnostics totals.
            for protocol in PROTOCOLS:
                diagnostics = read_csv(run_dir / f"packet_diagnostics_{protocol}.csv")[0]
                values = {
                    "offered": int(diagnostics["app_tx_packets"]),
                    "sink_rx": int(diagnostics["sink_rx_total"]),
                    "unique_rx": int(diagnostics["sink_rx_unique"]),
                    "duplicates": int(diagnostics["sink_rx_duplicates"]),
                    "app_no_route": int(diagnostics["app_ip_no_route_drops"]),
                    "app_route_error": int(diagnostics["app_ip_route_error_drops"]),
                    "mac_queue": int(diagnostics["mac_queue_drop_callbacks"]),
                    "mac_tx": int(diagnostics["mac_tx_drop_callbacks"]),
                    "phy_tx": int(diagnostics["phy_tx_drop_callbacks"]),
                    "phy_rx": int(diagnostics["phy_rx_drop_callbacks"]),
                }
                for key, value in values.items():
                    pooled_h3[protocol][key] += value

            # Static unrecovered losses sent in usable periods and first usable second.
            static_events = read_csv(run_dir / "packets_static.csv")
            tx_static = {int(item["sequence"]): item for item in static_events if item["event"] == "tx"}
            rx_static = {int(item["sequence"]) for item in static_events if item["event"] == "rx"}
            usable_runs = [(start + 45.0, stop + 45.0) for start, stop in traffic["usable_up_intervals_s"]]
            lost = set(tx_static) - rx_static
            usable_lost = 0
            first_usable_second_lost = 0
            for sequence in lost:
                sent_at = float(tx_static[sequence]["event_time_s"])
                interval = next(((start, stop) for start, stop in usable_runs
                                 if start - 1e-9 <= sent_at < stop + 1e-9), None)
                if interval is not None:
                    usable_lost += 1
                    if sent_at - interval[0] < 1.0:
                        first_usable_second_lost += 1
            pooled_h4["static_lost"] += len(lost)
            pooled_h4["static_usable_lost"] += usable_lost
            pooled_h4["static_first_usable_second_lost"] += first_usable_second_lost
            row.update({
                "static_offered": len(tx_static), "static_unique_rx": len(rx_static),
                "static_lost": len(lost), "static_usable_lost": usable_lost,
                "static_first_usable_second_lost": first_usable_second_lost,
                "static_usable_lost_fraction": usable_lost / len(lost) if lost else 0.0,
                "static_first_second_fraction_of_usable_losses": first_usable_second_lost / usable_lost if usable_lost else 0.0,
            })
            state_mismatches = 0
            for protocol in PROTOCOLS:
                events = read_csv(run_dir / f"packets_{protocol}.csv")
                tx_times = {int(item["sequence"]): float(item["event_time_s"])
                            for item in events if item["event"] == "tx"}
                rx_times = {int(item["sequence"]): float(item["event_time_s"])
                            for item in events if item["event"] == "rx" and int(item["sequence"]) in tx_times}
                d05 = compute_deadline_pdr(tx_times, rx_times, 0.5)
                d1 = compute_deadline_pdr(tx_times, rx_times, 1.0)
                d2 = compute_deadline_pdr(tx_times, rx_times, 2.0)
                delays = [rx_times[sequence] - tx_times[sequence] for sequence in rx_times]
                row[f"{protocol}_deadline_pdr_0_5s"] = d05["deadline_pdr"]
                row[f"{protocol}_deadline_pdr_1s"] = d1["deadline_pdr"]
                row[f"{protocol}_deadline_pdr_2s"] = d2["deadline_pdr"]
                row[f"{protocol}_mean_delay_s"] = statistics.mean(delays) if delays else "NA"
                row[f"{protocol}_median_delay_s"] = statistics.median(delays) if delays else "NA"
                row[f"{protocol}_unique_received_for_deadline"] = d1["unique_received_packets"]
                state_mismatches += sum(
                    is_time_connected(float(item["event_time_s"]), usable_runs)
                    != (item["usable_connected"] == "1")
                    for item in events if item["event"] in ("tx", "rx")
                )
            row["packet_usable_state_mismatches"] = state_mismatches
            realization_rows.append(row)

        metrics = ("raw_all_frame_uptime", "traffic_window_frame_uptime", "traffic_window_usable_uptime",
                   "aodv_pdr", "olsr_pdr", "static_pdr", "aodv_minus_raw_uptime",
                   "aodv_minus_usable_uptime", "olsr_minus_usable_uptime", "static_minus_usable_uptime",
                   "aodv_deadline_pdr_0_5s", "aodv_deadline_pdr_1s", "aodv_deadline_pdr_2s",
                   "olsr_deadline_pdr_0_5s", "olsr_deadline_pdr_1s",
                   "olsr_deadline_pdr_2s", "static_deadline_pdr_1s", "static_deadline_pdr_2s",
                   "static_deadline_pdr_0_5s", "aodv_mean_delay_s", "olsr_mean_delay_s", "static_mean_delay_s")
        summary = {"condition": condition, "realizations": len(cell_rows)}
        for metric in metrics:
            values = [entry[metric] for entry in cell_rows]
            summary[f"{metric}_mean"] = statistics.mean(values)
            summary[f"{metric}_sample_sd_ddof1"] = sample_sd(values)
        raw_gap = summary["aodv_minus_raw_uptime_mean"]
        adjusted_gap = summary["aodv_minus_usable_uptime_mean"]
        summary["positive_gap_reduction_fraction"] = (raw_gap - adjusted_gap) / raw_gap if raw_gap > 0 else "NA"
        condition_rows.append(summary)

    with (OUT / "corrected_6a_realizations.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(realization_rows[0]))
        writer.writeheader()
        writer.writerows(realization_rows)
    with (OUT / "corrected_6a_condition_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(condition_rows[0]))
        writer.writeheader()
        writer.writerows(condition_rows)

    print("Condition summaries (mean, sample SD ddof=1, positive raw gap reduction):")
    for row in condition_rows:
        print(row["condition"],
              "raw_uptime", f"{row['raw_all_frame_uptime_mean']:.4f} ± {row['raw_all_frame_uptime_sample_sd_ddof1']:.4f}",
              "usable", f"{row['traffic_window_usable_uptime_mean']:.4f} ± {row['traffic_window_usable_uptime_sample_sd_ddof1']:.4f}",
              "AODV", f"{row['aodv_pdr_mean']:.4f} ± {row['aodv_pdr_sample_sd_ddof1']:.4f}",
              "adjusted gap", f"{row['aodv_minus_usable_uptime_mean']:.4f}",
              "reduction", f"{row['positive_gap_reduction_fraction']:.3f}")
    print("H1 pooled counts", pooled_h1)
    for key in ("frame_down_rx", "usable_down_rx", "delay_gt_1_rx", "down_or_delay_gt_1_rx"):
        print("H1", key, pooled_h1[key], "/", pooled_h1["aodv_rx"],
              f"({pooled_h1[key] / pooled_h1['aodv_rx']:.4%})")
    print("H3 totals", pooled_h3)
    print("packet-state mismatches across all packet events:",
          sum(row["packet_usable_state_mismatches"] for row in realization_rows))
    print("H4 pooled", pooled_h4,
          "usable-loss fraction", pooled_h4["static_usable_lost"] / pooled_h4["static_lost"],
          "first-usable-second fraction", pooled_h4["static_first_usable_second_lost"] / pooled_h4["static_usable_lost"])


if __name__ == "__main__":
    main()
