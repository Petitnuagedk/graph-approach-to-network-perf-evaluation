"""Evaluate the frozen Phase 7B B1 results against preregistered gates."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXTURES = HERE / "B1" / "fixtures"
RUNS = HERE / "B1" / "runs"
sys.path.insert(0, str(ROOT / "simple-graph-experiments-v2" / "phase7" / "7D"))
sys.path.insert(0, str(ROOT))

from generator_v2 import read_trace  # noqa: E402
from oracle_metrics import compute_traffic_window_usable_uptime  # noqa: E402


def _rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _counts_by_frame(events, kind: str, state_column: str | None = None):
    counts = Counter()
    for event in events:
        if event["event"] != kind:
            continue
        if state_column and event[state_column] != "1":
            continue
        counts[int(float(event["event_time_s"]))] += 1
    return counts


def main() -> int:
    labels, frames = read_trace(FIXTURES / "alternating_sr_60.csv")
    source, destination = labels.index("S"), labels.index("R")
    results = []
    case_events = {}
    for loss in (125, 200, 1_000_000):
        name = f"downloss_{loss}"
        out = RUNS / name
        config = json.loads((out / "config.json").read_text())
        result = _rows(out / "trace_replay_results.csv")[0]
        oracle = _rows(out / "oracle_diagnostics_static.csv")[0]
        events = _rows(out / "packets_static.csv")
        case_events[name] = events
        tx = [event for event in events if event["event"] == "tx"]
        rx = [event for event in events if event["event"] == "rx"]
        delivered_down = sum(event["usable_connected"] == "0" for event in rx)
        rx_from_down_tx = 0
        tx_by_sequence = {int(event["sequence"]): event for event in tx}
        for event in rx:
            original = tx_by_sequence.get(int(event["sequence"]))
            if original and original["usable_connected"] == "0":
                rx_from_down_tx += 1
        full_frame_tx_counts = [sum(1 for event in tx if int(float(event["event_time_s"])) == index)
                                for index in range(1, 59)]
        transitions = []
        for previous, current in zip(tx, tx[1:]):
            if previous["usable_connected"] != current["usable_connected"]:
                current_time = float(current["event_time_s"])
                expected_boundary = round(current_time)
                transitions.append(abs(current_time - expected_boundary))
        python_oracle = compute_traffic_window_usable_uptime(
            frames, source, destination, 0.1, 59.0, frame_duration_s=1.0,
            link_up_loss_db=10.0, link_down_loss_db=float(loss),
            tx_power_dbm=20.0, rx_sensitivity_dbm=-101.0,
            sparse_threshold_db=150.0, default_loss_db=1e6, interpolate=False)
        pdr = float(result["pdr"])
        usable = float(oracle["traffic_usable_uptime"])
        results.append({
            "down_loss_db": loss,
            "channel_profile": config["channel_profile"],
            "resolved_interpolate": config["interpolate"],
            "source_frames": len(frames),
            "frame_apply_calls": int(result["frame_apply_calls"]),
            "app_tx": int(result["app_tx_pkts"]),
            "app_rx": int(result["app_rx_pkts"]),
            "pdr": pdr,
            "traffic_frame_uptime_cpp": float(oracle["traffic_frame_uptime"]),
            "traffic_usable_uptime_cpp": usable,
            "traffic_frame_uptime_python": python_oracle["frame_uptime_ratio"],
            "traffic_usable_uptime_python": python_oracle["usable_uptime_ratio"],
            "frame_oracle_rounded9_match": round(float(oracle["traffic_frame_uptime"]), 9)
                == round(python_oracle["frame_uptime_ratio"], 9),
            "usable_oracle_rounded9_match": round(usable, 9)
                == round(python_oracle["usable_uptime_ratio"], 9),
            "abs_pdr_minus_usable_uptime": abs(pdr - usable),
            "within_preregistered_0_05": abs(pdr - usable) <= 0.05,
            "rx_attributed_to_down_frame": delivered_down,
            "rx_from_tx_offered_in_down_frame": rx_from_down_tx,
            "min_tx_packets_per_full_frame_1_to_58": min(full_frame_tx_counts),
            "max_tx_packets_per_full_frame_1_to_58": max(full_frame_tx_counts),
            "observed_tx_state_transition_count": len(transitions),
            "max_tx_state_transition_boundary_error_s": max(transitions, default=0.0),
            "tx_state_boundaries_within_0_010_s": bool(transitions)
                and max(transitions) <= 0.010,
        })

    frame_deliveries = {
        name: _counts_by_frame(events, "rx", "usable_connected")
        for name, events in case_events.items()
    }
    reference = frame_deliveries["downloss_125"]
    max_count_difference = max(
        (abs(reference.get(frame, 0) - frame_deliveries[name].get(frame, 0))
         for name in frame_deliveries for frame in range(60)), default=0)
    for result in results:
        result["max_per_frame_up_delivery_difference_across_losses"] = max_count_difference
        result["all_up_frame_delivery_counts_identical"] = max_count_difference == 0

    all_up = []
    for topology in ("line", "ladder"):
        out = RUNS / f"all_up_{topology}"
        result = _rows(out / "trace_replay_results.csv")[0]
        config = json.loads((out / "config.json").read_text())
        record = {
            "topology": topology,
            "channel_profile": config["channel_profile"],
            "resolved_interpolate": config["interpolate"],
            "source_frames": 60,
            "frame_apply_calls": int(result["frame_apply_calls"]),
            "app_tx": int(result["app_tx_pkts"]),
            "app_rx": int(result["app_rx_pkts"]),
            "pdr": float(result["pdr"]),
            "pass": int(result["frame_apply_calls"]) == 60
                and int(result["app_tx_pkts"]) >= 300
                and int(result["app_rx_pkts"]) >= 297
                and float(result["pdr"]) >= 0.99
                and config["interpolate"] is False,
        }
        all_up.append(record)

    summary = {
        "protocol_variants": 0,
        "down_loss_runs": results,
        "per_frame_rx_counts": {
            name: [frame_deliveries[name].get(frame, 0) for frame in range(60)]
            for name in frame_deliveries
        },
        "all_up_controls": all_up,
        "down_loss_equivalence_and_zero_down_deliveries_pass": (
            max_count_difference == 0
            and all(item["rx_attributed_to_down_frame"] == 0
                    and item["frame_apply_calls"] == 60
                    and item["frame_oracle_rounded9_match"]
                    and item["usable_oracle_rounded9_match"]
                    and item["tx_state_boundaries_within_0_010_s"]
                    and item["min_tx_packets_per_full_frame_1_to_58"] >= 20
                    for item in results)
        ),
        "static_vs_oracle_pass": all(item["within_preregistered_0_05"] for item in results),
        "all_up_controls_pass": all(item["pass"] for item in all_up),
        "b1_pass": (all(item["within_preregistered_0_05"] for item in results)
                    and all(item["pass"] for item in all_up)
                    and max_count_difference == 0
                    and all(item["rx_attributed_to_down_frame"] == 0 for item in results)),
    }
    (HERE / "B1" / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with (HERE / "B1" / "downloss_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    delivery_path = HERE / "B1" / "per_frame_deliveries.csv"
    with delivery_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["frame_index", *case_events.keys()])
        for frame in range(60):
            writer.writerow([frame, *(frame_deliveries[name].get(frame, 0)
                                      for name in case_events)])
    invocation_common = [
        "--routing=static", "--flows=S:R", "--packetSize=1024",
        "--lossThresholdDb=150", "--channelProfile=v2",
        "--defaultLossDb=1000000", "--txPowerDbm=20", "--linkUpLossDb=10",
        "--fps=1", "--seed=42", "--warmup=0", "--warmupMode=first",
        "--dumpRoutes=true", "--staticOracleMode=usable",
    ]
    invocations = []
    for loss in (125, 200, 1_000_000):
        invocations.append({
            "cwd": "/home/hledirach/Documents/sp1-sp2",
            "command_prefix": ["./ns3", "run", "graph-run"],
            "frames_csv": str(FIXTURES / "alternating_sr_60.csv"),
            "out_dir": str(RUNS / f"downloss_{loss}"),
            "arguments": [f"--framesCsv={FIXTURES / 'alternating_sr_60.csv'}",
                          f"--outDir={RUNS / f'downloss_{loss}'}",
                          *invocation_common, f"--linkDownLossDb={loss}",
                          "--dataRate=1Mbps"],
        })
    for topology in ("line", "ladder"):
        invocations.append({
            "cwd": "/home/hledirach/Documents/sp1-sp2",
            "command_prefix": ["./ns3", "run", "graph-run"],
            "frames_csv": str(FIXTURES / f"all_up_{topology}_60.csv"),
            "out_dir": str(RUNS / f"all_up_{topology}"),
            "arguments": [f"--framesCsv={FIXTURES / f'all_up_{topology}_60.csv'}",
                          f"--outDir={RUNS / f'all_up_{topology}' }",
                          *invocation_common, "--linkDownLossDb=125",
                          "--dataRate=50kbps"],
        })
    invocation_path = HERE / "B1" / "invocations.json"
    invocation_path.write_text(json.dumps(invocations, indent=2) + "\n")
    hashed_paths = [FIXTURES / "alternating_sr_60.csv", FIXTURES / "all_up_line_60.csv",
                    FIXTURES / "all_up_ladder_60.csv"]
    for run_dir in RUNS.iterdir():
        if run_dir.is_dir():
            hashed_paths.extend(path for path in run_dir.iterdir() if path.is_file())
    hashed_paths.extend([Path(__file__), ROOT / "scratch" / "graph-run.cc", invocation_path])
    manifest = {
        str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path): hashlib.sha256(
            path.read_bytes()).hexdigest()
        for path in sorted(set(hashed_paths)) if path.is_file()
    }
    (HERE / "B1" / "sha256_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["b1_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())