#!/usr/bin/env python3
"""Summarize the focused Phase 6D DSDV replay/plain ladder runs."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNS = Path(__file__).resolve().parent / "runs"
OUT = Path(__file__).resolve().parent


def route_snapshots(path: Path, source_node: int, destination: str):
    snapshots = []
    now = None
    in_source_table = False
    for line in path.read_text(errors="replace").splitlines():
        match = re.search(r"Node:\s*(\d+),\s*Time:\s*\+?([0-9.eE+-]+)s", line)
        if match:
            in_source_table = int(match.group(1)) == source_node
            now = float(match.group(2))
            continue
        if not in_source_table or now is None:
            continue
        fields = line.split()
        if fields and fields[0] == destination:
            snapshots.append((now, fields[1], int(fields[3]), int(fields[4])))
        if line.startswith("Node:"):
            continue
    return snapshots


def outage_intervals(samples):
    missing = [(t, row is None) for t, row in samples]
    result = []
    start = None
    last = None
    for t, is_missing in missing:
        if is_missing and start is None:
            start = t
        if is_missing:
            last = t
        elif start is not None:
            result.append((start, last))
            start = last = None
    if start is not None:
        result.append((start, last))
    return result


def read_csv(path: Path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    summary = []
    timeline_rows = []
    for mode in ("replay", "plain"):
        for warmup in (0, 30, 45, 60, 90):
            directory = RUNS / mode / f"warmup_{warmup}"
            if mode == "replay":
                packet_rows = read_csv(directory / "packets_dsdv.csv")
                diagnostics = read_csv(directory / "packet_diagnostics_dsdv.csv")[0]
                results = read_csv(directory / "trace_replay_results.csv")[0]
                route_file = directory / "routes_dsdv.txt"
                tx = {int(row["sequence"]): float(row["event_time_s"])
                      for row in packet_rows if row["event"] == "tx"}
                rx = {int(row["sequence"]): float(row["event_time_s"])
                      for row in packet_rows if row["event"] == "rx"}
                pdr = float(results["pdr"])
                no_route = int(diagnostics["app_ip_no_route_drops"])
                phy_rx_drop = int(diagnostics["phy_rx_drop_callbacks"])
            else:
                results = read_csv(directory / "summary.csv")[0]
                route_file = directory / "routes.txt"
                tx_count, rx_count = int(results["tx_packets"]), int(results["rx_packets"])
                pdr = float(results["pdr"])
                tx, rx = {}, {}
                no_route = phy_rx_drop = -1
            samples = route_snapshots(route_file, 6, "10.1.0.8")
            lookup = {int(t): (gateway, hops, seq) for t, gateway, hops, seq in samples}
            t_start = warmup
            t_stop = warmup + 59
            for t in range(t_start, t_stop + 1):
                row = lookup.get(t)
                timeline_rows.append({
                    "mode": mode, "warmup_s": warmup, "time_s": t,
                    "route_present": row is not None,
                    "gateway": row[0] if row else "",
                    "hop_count": row[1] if row else "",
                    "destination_sequence": row[2] if row else "",
                    "tx_packets_in_second": sum(t <= event_t < t + 1 for event_t in tx.values()) if mode == "replay" else "",
                    "rx_packets_in_second": sum(t <= event_t < t + 1 for event_t in rx.values()) if mode == "replay" else "",
                })
            missing = [(t, lookup.get(t)) for t in range(t_start, t_stop + 1)]
            absent_runs = outage_intervals(missing)
            received_gaps = []
            if mode == "replay":
                times = sorted(rx.values())
                received_gaps = [(a, b) for a, b in zip(times, times[1:]) if b - a >= 2.0]
                tx_count, rx_count = len(tx), len(rx)
            summary.append({
                "mode": mode, "warmup_s": warmup, "tx_packets": tx_count,
                "rx_packets": rx_count, "pdr": pdr,
                "app_ip_no_route_drops": no_route, "phy_rx_drop_callbacks": phy_rx_drop,
                "source_route_snapshots": len(samples),
                "source_route_absent_snapshots": sum(t not in lookup for t in range(t_start, t_stop + 1)),
                "source_route_absent_intervals_s": ";".join(f"{a}-{b}" for a, b in absent_runs),
                "rx_gaps_ge_2s": ";".join(f"{a:.3f}-{b:.3f}" for a, b in received_gaps),
            })

    for name, rows in (("dsdv_summary.csv", summary), ("dsdv_timeline.csv", timeline_rows)):
        with (OUT / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    for row in summary:
        print(row)


if __name__ == "__main__":
    main()
