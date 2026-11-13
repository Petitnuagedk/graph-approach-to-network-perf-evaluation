#!/usr/bin/env python3
"""Offline, no-variant A4.0b diagnosis. Reads saved A4.0 outputs only."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
A4 = HERE.parent
STUDY = A4.parents[1]
A1 = STUDY / "alpha" / "A1"
RUNS = A4 / "runs"
PROTOCOLS = ("olsr", "aodv", "dsdv")
RATE = 50_000
PACKET_BYTES = 1024
INTERVAL = PACKET_BYTES * 8 / RATE
STOP_A = 119.0
STOP_B = 239.0
TOL = 2e-8


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def num(v: object, default: float = math.nan) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def bools(v: bool) -> str:
    return "true" if v else "false"


def ip_node(address: str) -> int:
    return int(address.rsplit(".", 1)[1]) - 1


def load_geodesic_edges() -> set[tuple[int, int]]:
    manifest = json.loads((A1 / "results" / "graph_manifest.json").read_text(encoding="utf-8"))
    item = next(x for x in manifest if x["graph_id"] == "geodesic_N42_r1")
    edge_file = A1 / item["edge_list"]
    digest = hashlib.sha256(edge_file.read_bytes()).hexdigest()
    if digest != item["edge_sha256"]:
        raise RuntimeError("A1 geodesic N42 edge-list hash mismatch")
    return {(min(int(r["u"]), int(r["v"])), max(int(r["u"]), int(r["v"])))
            for r in read_csv(edge_file)}


def exact_flow_packet_index(app_time: float, flows: list[dict[str, str]]) -> tuple[int, int] | None:
    """Map by the known ns-3 schedule, not by sequence-number guesses.

    graph-run.cc schedules client i at warmup + .1 + i/nflows and its
    UdpClient interval is PACKET_BYTES*8/RATE. packets_*.csv TX sequence is
    global; the timestamp is the exact schedule key. RX/forward logs instead
    contain the per-client SeqTsHeader sequence.
    """
    matches: list[tuple[int, int]] = []
    for i, _flow in enumerate(flows):
        start = 0.1 + i / len(flows)
        local_seq = round((app_time - start) / INTERVAL)
        if local_seq >= 0 and abs(app_time - (start + local_seq * INTERVAL)) <= TOL:
            matches.append((i, local_seq))
    return matches[0] if len(matches) == 1 else None


def analyze_v1(protocol: str, edges: set[tuple[int, int]]) -> tuple[dict[str, object], list[dict[str, object]]]:
    run_id = f"40B_geodesic_N42_r1_{protocol}_validation"
    out = RUNS / run_id
    flows = read_csv(out / "flows.csv")
    flows = [f for f in flows if f["protocol"] == protocol]
    tx_rows = [r for r in read_csv(out / f"packets_{protocol}.csv") if r["event"] == "tx"]
    rx_rows = [r for r in read_csv(out / f"packets_{protocol}.csv") if r["event"] == "rx"]
    forward_rows = [r for r in read_csv(out / f"forward_events_{protocol}.csv")
                    if r["counts_as_forward"] == "1"]
    node_rows = [r for r in read_csv(out / "node_diagnostics.csv")
                 if r["protocol"] == protocol and r["metric"] == "forwarded_app_packets_ipv4"]
    node_counts = {int(r["node_id"]): int(r["value"]) for r in node_rows}
    tx_keys: dict[float, tuple[int, int, dict[str, object]]] = {}
    tx_map_failures: list[dict[str, object]] = []
    tx_count_by_flow = [0] * len(flows)
    for row in tx_rows:
        app_time = num(row["app_tx_time_s"])
        mapped = exact_flow_packet_index(app_time, flows)
        if mapped is None:
            tx_map_failures.append({"protocol": protocol, "event": "tx", "global_sequence": row["sequence"],
                                    "app_timestamp_s": row["app_tx_time_s"], "reason": "not exactly one scheduled flow match"})
            continue
        fi, local_seq = mapped
        key = round(app_time, 9)
        if key in tx_keys:
            tx_map_failures.append({"protocol": protocol, "event": "tx", "global_sequence": row["sequence"],
                                    "app_timestamp_s": row["app_tx_time_s"], "reason": "duplicate scheduled packet key"})
        tx_keys[key] = (fi, local_seq, row)
        tx_count_by_flow[fi] += 1
    rx_keys: set[float] = set()
    rx_sequence_by_time: dict[float, int] = {}
    rx_map_failures: list[dict[str, object]] = []
    rx_duplicates = 0
    for row in rx_rows:
        sequence = int(row["sequence"])
        app_time = num(row["app_tx_time_s"])
        key = round(app_time, 9)
        if sequence < 0 or key not in tx_keys:
            rx_map_failures.append({"protocol": protocol, "event": "rx", "sequence": row["sequence"],
                                    "app_timestamp_s": row["app_tx_time_s"], "reason": "RX timestamp lacks a unique scheduled TX"})
            continue
        if key in rx_keys:
            rx_duplicates += 1
        rx_keys.add(key)
        if key in rx_sequence_by_time and rx_sequence_by_time[key] != sequence:
            rx_map_failures.append({"protocol": protocol, "event": "rx", "sequence": sequence,
                                    "app_timestamp_s": row["app_tx_time_s"], "reason": "conflicting per-flow RX sequence for timestamp"})
        rx_sequence_by_time[key] = sequence
    grouped: dict[float, list[dict[str, str]]] = {}
    forward_sequences: dict[float, set[int]] = {}
    forward_map_failures: list[dict[str, object]] = []
    for row in forward_rows:
        src, dst = ip_node(row["source"]), ip_node(row["destination"])
        app_time = num(row["app_timestamp_s"])
        seq = int(row["sequence"])
        flow_index = next((i for i, f in enumerate(flows)
                           if f["source"] == f"Node_{src}" and f["destination"] == f"Node_{dst}"), None)
        if flow_index is None:
            forward_map_failures.append({"protocol": protocol, "event": "forward", "sequence": seq,
                                         "app_timestamp_s": row["app_timestamp_s"], "reason": "IP endpoints absent from flows.csv"})
            continue
        key = round(app_time, 9)
        if key not in tx_keys or tx_keys[key][0] != flow_index:
            forward_map_failures.append({"protocol": protocol, "event": "forward", "sequence": seq,
                                         "app_timestamp_s": row["app_timestamp_s"], "reason": "forward endpoint/timestamp does not match uniquely scheduled TX"})
            continue
        grouped.setdefault(key, []).append(row)
        forward_sequences.setdefault(key, set()).add(seq)
    offered_by_flow = [int(f["offered_packets"]) for f in flows]
    per_flow_tx_exact = all(tx_count_by_flow[i] == offered_by_flow[i] for i in range(len(flows)))
    rx_subset_tx = rx_keys.issubset(tx_keys.keys())
    unreceived_tx = tx_keys.keys() - rx_keys
    delivered_events = 0
    undelivered_events = 0
    delivered_path_rows: list[dict[str, object]] = []
    bad_edges = 0
    bad_hops = 0
    sequence_identity_failures = 0
    delivered_keys_checked = 0
    for key, (flow_index, local_seq, tx_row) in tx_keys.items():
        event_list = sorted(grouped.get(key, []), key=lambda r: num(r["time_s"]))
        if key in rx_keys:
            delivered_events += len(event_list)
            fi, app_time = flow_index, key
            packet_sequence = rx_sequence_by_time[key]
            observed_forward_sequences = forward_sequences.get(key, set())
            sequence_ok = not observed_forward_sequences or observed_forward_sequences == {packet_sequence}
            sequence_identity_failures += int(not sequence_ok)
            src = int(flows[fi]["source"].split("_")[-1])
            dst = int(flows[fi]["destination"].split("_")[-1])
            path = [src] + [int(e["node_id"]) for e in event_list] + [dst]
            consecutive = all(a != b and (min(a, b), max(a, b)) in edges
                              for a, b in zip(path, path[1:]))
            expected_events = len(path) - 2
            hop_clause = len(event_list) == expected_events
            bad_edges += int(not consecutive)
            bad_hops += int(not hop_clause)
            delivered_keys_checked += 1
            delivered_path_rows.append({"protocol": protocol, "flow_id": flows[fi]["flow_id"],
                                        "sequence": packet_sequence, "app_timestamp_s": f"{app_time:.9f}",
                                        "n_forward_events": len(event_list), "path_nodes": ";".join(map(str, path)),
                                        "consecutive_A1_edges": bools(consecutive),
                                        "events_equal_hops_minus_1": bools(hop_clause),
                                        "rx_forward_sequence_consistent": bools(sequence_ok)})
        else:
            undelivered_events += len(event_list)
    internal_forward_sequence_conflicts = sum(len(sequences) > 1 for sequences in forward_sequences.values())
    sequence_identity_failures += internal_forward_sequence_conflicts
    all_forward_events_matched = (len(forward_rows) == sum(len(v) for v in grouped.values())
                                  and not forward_map_failures and sequence_identity_failures == 0)
    counter_total = sum(node_counts.values())
    log_total = delivered_events + undelivered_events
    counter_equals_partition = counter_total == log_total
    flow_delivery_counts_exact = all(int(f["delivered_unique_packets"]) ==
                                     sum(1 for k in rx_keys if tx_keys[k][0] == i)
                                     for i, f in enumerate(flows))
    all_delivered_paths_ok = bad_edges == 0 and bad_hops == 0 and delivered_keys_checked == sum(
        int(f["delivered_unique_packets"]) for f in flows)
    no_unassigned_packets = not tx_map_failures and not rx_map_failures and not forward_map_failures
    passed = (no_unassigned_packets and per_flow_tx_exact and rx_subset_tx and flow_delivery_counts_exact
              and all_delivered_paths_ok and all_forward_events_matched and counter_equals_partition)
    summary = {
        "protocol": protocol, "run_id": run_id, "V1_pass": bools(passed),
        "tx_log_rows": len(tx_rows), "tx_unique_mapped": len(tx_keys), "tx_mapping_failures": len(tx_map_failures),
        "tx_counts_match_flows_offered": bools(per_flow_tx_exact),
        "rx_log_rows": len(rx_rows), "rx_unique_mapped": len(rx_keys), "rx_duplicates": rx_duplicates,
        "rx_mapping_failures": len(rx_map_failures), "rx_subset_of_tx": bools(rx_subset_tx),
        "per_flow_delivered_matches_unique_rx": bools(flow_delivery_counts_exact),
        "delivered_packets_path_checked": delivered_keys_checked,
        "delivered_packets_with_consecutive_A1_edges": delivered_keys_checked - bad_edges,
        "delivered_packets_with_events_equal_hops_minus_1": delivered_keys_checked - bad_hops,
        "delivered_packet_sequence_identity_failures": sequence_identity_failures,
        "delivered_forward_event_count": delivered_events, "undelivered_forward_event_count": undelivered_events,
        "forward_log_event_count": len(forward_rows), "all_forward_events_mapped_to_tx": bools(all_forward_events_matched),
        "summed_node_forward_counter": counter_total, "counter_equals_delivered_plus_undelivered_events": bools(counter_equals_partition),
        "node_counter_by_node": json.dumps(node_counts, sort_keys=True),
        "tx_mapping_examples": json.dumps(tx_map_failures[:3]),
    }
    return summary, delivered_path_rows


def convergence_evaluation(tx_times: list[float], rx_times: list[float], stop: float,
                            start_time: float, tail_cut: float = 0.0) -> tuple[float, list[dict[str, object]]]:
    horizon = stop - tail_cut
    if horizon < start_time + 10:
        return math.nan, []
    tx = sorted(t for t in tx_times if t <= horizon)
    rx = sorted(t for t in rx_times if t <= horizon)
    first_full = start_time + 10.0
    ends = {first_full, horizon}
    for t in tx + rx:
        if first_full <= t <= horizon:
            ends.add(t)
        if first_full <= t + 10.0 <= horizon:
            ends.add(t + 10.0)
    ordered = sorted(ends)
    evals: list[dict[str, object]] = []
    for end in ordered:
        begin = end - 10.0
        ntx = sum(begin < t <= end for t in tx)
        nrx = sum(begin < t <= end for t in rx)
        ratio = nrx / ntx if ntx else math.nan
        evals.append({"window_end_s": f"{end:.9f}", "window_start_s": f"{begin:.9f}",
                      "offered_tx": ntx, "unique_rx": nrx, "window_pdr": f"{ratio:.9g}" if math.isfinite(ratio) else "nan",
                      "pass_0_99": bools(ntx > 0 and ratio >= .99)})
    suffix = True
    conv = math.nan
    for row in reversed(evals):
        suffix = suffix and row["pass_0_99"] == "true"
        if suffix:
            conv = float(row["window_end_s"])
    return conv, evals[-5:]


def analyze_convergence(protocol: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    summaries: list[dict[str, object]] = []
    last_windows: list[dict[str, object]] = []
    runs = [p for p in sorted(RUNS.iterdir()) if p.is_dir() and p.name.startswith("40")]
    for run_dir in runs:
        run_id = run_dir.name
        rows = read_csv(run_dir / "flows.csv") if (run_dir / "flows.csv").exists() else []
        flow = next((r for r in rows if r.get("protocol") == protocol and r.get("is_probe") == "1"), None)
        if not flow:
            continue
        packet_file = run_dir / f"packets_{protocol}.csv"
        if not packet_file.is_file():
            summaries.append({"run_id": run_id, "protocol": protocol, "source_convergence_s": flow["probe_convergence_s"],
                              "original_replayed_s": "unavailable_no_packet_timing_log",
                              "tail_censored_sensitivity_s": "unavailable_no_packet_timing_log",
                              "tail_cut_s": "", "probe_tx": "", "probe_rx_unique": "",
                              "unreceived_at_stop": "", "candidate_inflight_within_maxdelay": "",
                              "max_observed_oneway_delay_s": "", "last5_original_pass": "unavailable"})
            continue
        flow_list = [r for r in rows if r.get("protocol") == protocol]
        flow_index = int(flow["flow_id"])
        probe_start = 0.1 + flow_index / len(flow_list)
        trows = read_csv(packet_file)
        tx_times: list[float] = []
        for row in trows:
            if row["event"] != "tx":
                continue
            t = num(row["app_tx_time_s"])
            seq = round((t - probe_start) / INTERVAL)
            if seq >= 0 and abs(t - (probe_start + seq * INTERVAL)) <= TOL:
                tx_times.append(t)
        tx_times = sorted(set(tx_times))
        tx_set = {round(t, 9) for t in tx_times}
        rx_events: dict[float, float] = {}
        delays: list[float] = []
        for row in trows:
            if row["event"] != "rx" or int(row["sequence"]) < 0:
                continue
            app_t, event_t = num(row["app_tx_time_s"]), num(row["event_time_s"])
            if round(app_t, 9) in tx_set:
                key = round(app_t, 9)
                rx_events[key] = min(event_t, rx_events.get(key, math.inf))
                delays.append(event_t - app_t)
            rx_times = list(rx_events.values())
        stop = STOP_A if run_id.startswith("40A_") else STOP_B
        conv0, last5 = convergence_evaluation(tx_times, rx_times, stop, probe_start)
        tail_delays = [event_t - key for key, event_t in rx_events.items() if stop - 10.0 <= key <= stop]
        max_delay = max(tail_delays) if tail_delays else math.nan
        # Conservative tail horizon: maximum probe delay in the final 10 seconds
        # plus one packet interval (one maximum inter-packet gap).
        tail_cut = max_delay + INTERVAL if math.isfinite(max_delay) else math.nan
        conv1, _ = convergence_evaluation(tx_times, rx_times, stop, probe_start, tail_cut) if math.isfinite(tail_cut) else (math.nan, [])
        unique_rx_tx_times = set(rx_events)
        unreceived = len(tx_set - unique_rx_tx_times)
        late_rx = sum(1 for t, rx_t in rx_events.items() if rx_t > stop)
        near_tail = sum(1 for t in tx_set - unique_rx_tx_times if stop - 10.0 <= t <= stop)
        source_conv = num(flow["probe_convergence_s"])
        summaries.append({"run_id": run_id, "protocol": protocol,
                          "source_convergence_s": flow["probe_convergence_s"],
                          "original_replayed_s": f"{conv0:.9f}" if math.isfinite(conv0) else "nan",
                          "tail_censored_sensitivity_s": f"{conv1:.9f}" if math.isfinite(conv1) else "nan",
                          "tail_cut_s": f"{tail_cut:.9f}" if math.isfinite(tail_cut) else "nan",
                          "probe_tx": len(tx_times), "probe_rx_unique": len(unique_rx_tx_times),
                          "unreceived_at_stop": unreceived,
                          "observed_rx_after_stop": late_rx,
                          "unreceived_probe_tx_last_10s": near_tail,
                          "max_observed_oneway_delay_s": f"{max_delay:.9f}" if math.isfinite(max_delay) else "nan",
                          "replay_matches_saved": bools(math.isfinite(source_conv) and math.isfinite(conv0) and abs(source_conv-conv0) < 2e-8),
                          "last5_original_pass": ";".join(row["pass_0_99"] for row in last5)})
        for i, row in enumerate(last5, 1):
            last_windows.append({"run_id": run_id, "protocol": protocol, "window_rank_from_end": i,
                                **row, "convergence_original_s": f"{conv0:.9f}" if math.isfinite(conv0) else "nan"})
    return summaries, last_windows


def t3_and_tail_synthetic() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    def make(first_rx: int, alternate: bool = False) -> tuple[list[float], list[float]]:
        tx = [float(t) for t in range(41)]
        rx = [float(t) for t in range(41) if ((t % 2 == 0) if alternate else t >= first_rx)]
        return tx, rx
    for label, first, alternate, expected in (("T3_immediate", 0, False, 10.0),
                                               ("T3_delayed", 15, False, 24.0),
                                               ("T3_never", 0, True, math.nan)):
        tx, rx = make(first, alternate)
        conv, _ = convergence_evaluation(tx, rx, 40.0, 0.0)
        passed = (math.isnan(conv) and math.isnan(expected)) or conv == expected
        rows.append({"case": label, "original_convergence_s": "nan" if math.isnan(conv) else conv,
                     "corrected_convergence_s": "not_applicable", "tail_cut_s": 0,
                     "expected": "nan" if math.isnan(expected) else expected,
                     "gate_pass": bools(passed)})
    # Tail case: a packet sent at stop is not observed received until after stop.
    tx = [float(t) for t in range(41)]
    rx = [float(t) for t in range(40)]
    tail = 0.2 + INTERVAL
    original, _ = convergence_evaluation(tx, rx, 40.0, 0.0)
    corrected, _ = convergence_evaluation(tx, rx, 40.0, 0.0, tail)
    rows.append({"case": "synthetic_inflight_tail_at_stop", "original_convergence_s": "nan" if math.isnan(original) else original,
                 "corrected_convergence_s": "nan" if math.isnan(corrected) else corrected,
                 "tail_cut_s": f"{tail:.9f}", "expected": "corrected finite after truncating unobservable tail",
                 "gate_pass": bools(math.isfinite(corrected))})
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifests() -> None:
    ns3 = Path("/home/hledirach/Documents/sp1-sp2")
    graph_manifest = json.loads((A1 / "results" / "graph_manifest.json").read_text(encoding="utf-8"))
    geodesic = next(item for item in graph_manifest if item["graph_id"] == "geodesic_N42_r1")
    inputs = [
        A4 / "prereg.md", A4 / "a4.py", A4 / "PRE_RUN_IDENTITY.md",
        A4 / "runs.csv", A4 / "validation_4.0.json", A4 / "flow_count_checks_4.0.csv",
        A4 / "endpoint_incidence_4.0.csv", A4 / "derived_4.0.csv",
        A1 / "results" / "graph_manifest.json",
        ns3 / "VERSION", ns3 / "ns3", ns3 / "scratch" / "graph-run.cc",
        ns3 / "src" / "olsr" / "model" / "olsr-header.cc",
        ns3 / "src" / "aodv" / "model" / "aodv-routing-protocol.cc",
        A1 / geodesic["edge_list"],
    ]
    inputs.extend(p for run_dir in sorted(RUNS.glob("40A_*")) + sorted(RUNS.glob("40B_*"))
                  for p in run_dir.rglob("*") if p.is_file())
    rows = []
    for path in sorted(set(inputs), key=str):
        if not path.is_file():
            continue
        try:
            label = path.relative_to(STUDY).as_posix()
        except ValueError:
            label = "EXTERNAL:" + path.as_posix()
        rows.append(f"{sha256_file(path)}  {label}")
    (HERE / "INPUTS.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    artifacts = sorted(
        [p for p in HERE.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256"]
        + [A4 / "amendment_1.md", A4.parent / "gates.md"], key=str)
    output_rows = []
    for path in artifacts:
        label = path.relative_to(STUDY).as_posix()
        output_rows.append(f"{sha256_file(path)}  {label}")
    (HERE / "MANIFEST.sha256").write_text("\n".join(output_rows) + "\n", encoding="utf-8")


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    edges = load_geodesic_edges()
    v1_rows: list[dict[str, object]] = []
    path_rows: list[dict[str, object]] = []
    for protocol in PROTOCOLS:
        summary, paths = analyze_v1(protocol, edges)
        v1_rows.append(summary)
        path_rows.extend(paths)
    write_csv(HERE / "v1_by_protocol.csv", v1_rows)
    write_csv(HERE / "v1_delivered_packet_paths.csv", path_rows)
    convergence: list[dict[str, object]] = []
    windows: list[dict[str, object]] = []
    for protocol in PROTOCOLS:
        summary, last = analyze_convergence(protocol)
        convergence.extend(summary)
        windows.extend(last)
    write_csv(HERE / "convergence_replay.csv", convergence)
    write_csv(HERE / "convergence_last5_windows.csv", windows)
    write_csv(HERE / "synthetic_detector_tests.csv", t3_and_tail_synthetic())
    (HERE / "summary.json").write_text(json.dumps({
        "v1": v1_rows, "convergence_runs": convergence,
        "synthetic_tests": t3_and_tail_synthetic(),
        "analysis_scope": "offline only; zero protocol variants; A4.0 source artifacts unchanged",
    }, indent=2) + "\n", encoding="utf-8")
    write_manifests()
    print("V1:", json.dumps(v1_rows, indent=2))
    print("CONVERGENCE:", json.dumps(convergence, indent=2))
    print("SYNTHETIC:", json.dumps(t3_and_tail_synthetic(), indent=2))


if __name__ == "__main__":
    main()
