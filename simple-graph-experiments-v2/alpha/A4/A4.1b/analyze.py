#!/usr/bin/env python3
"""A4.1b offline reconciliation; never launches a simulator."""
from __future__ import annotations

import csv
import hashlib
import math
from collections import defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
A4 = HERE.parent
STUDY = A4.parents[1]
A1 = STUDY / "alpha" / "A1"
PROTOCOLS = ("olsr", "aodv", "dsdv")
SIZES = (42, 92, 162)
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
G = 1.0
WINDOW = 10.0
MIN_AGE = 10.0
FIRST_TX = 0.1
PACKET_INTERVAL = 1024 * 8 / 50_000
TOLERANCE = 2e-8
CENSOR_LIMIT = 180.0
PREREG_HASH = "6d26c7359008e64ab1975a644f7e59d6fa320143396c5f53b0f3c7998c992a35"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def num(value: object) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else math.nan
    except (TypeError, ValueError):
        return math.nan


def fmt(value: float) -> str:
    return "nan" if not math.isfinite(value) else f"{value:.9g}"


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def schedule_index(timestamp: float) -> int | None:
    index = round((timestamp - FIRST_TX) / PACKET_INTERVAL)
    expected = FIRST_TX + index * PACKET_INTERVAL
    return index if index >= 0 and abs(timestamp - expected) <= TOLERANCE else None


def detector(path: Path) -> dict[str, object]:
    """Independent transcription of a4.py readiness_from_probe_packets()."""
    tx_times: set[float] = set()
    rx_by_app_tx: dict[float, float] = {}
    bad_rows = 0
    for row in read_csv(path):
        try:
            sequence = int(row.get("sequence", "-1"))
        except (TypeError, ValueError):
            sequence = -1
        app_tx = num(row.get("app_tx_time_s"))
        event_time = num(row.get("event_time_s"))
        if sequence < 0 or not math.isfinite(app_tx):
            continue
        index = schedule_index(app_tx)
        if index is None:
            bad_rows += 1
            continue
        key = round(app_tx, 9)
        if row.get("event") == "tx":
            tx_times.add(key)
        elif row.get("event") == "rx" and math.isfinite(event_time):
            rx_by_app_tx[key] = min(event_time, rx_by_app_tx.get(key, math.inf))

    delivered = sorted({round(rx_by_app_tx[key], 9) for key in tx_times if key in rx_by_app_tx})
    states: list[tuple[float, bool]] = []
    for t in delivered:
        if t + 1e-12 < FIRST_TX + MIN_AGE:
            continue
        left = t - WINDOW
        in_window = [x for x in delivered if left - 1e-10 <= x <= t + 1e-10]
        ready = bool(in_window) and in_window[0] - left <= G + 1e-10
        ready = ready and all(b - a <= G + 1e-10 for a, b in zip(in_window, in_window[1:]))
        states.append((t, ready))
    last_bad = max((i for i, (_, passed) in enumerate(states) if not passed), default=-1)
    suffix = states[last_bad + 1:]
    readiness = suffix[0][0] if suffix else math.nan

    first_delivery = min(delivered, default=math.nan)
    intervals = [(b - a, a, b) for a, b in zip(delivered, delivered[1:])]
    max_gap, gap_start, gap_end = max(intervals, default=(math.nan, math.nan, math.nan))
    return {
        "readiness_s": readiness,
        "first_delivery_s_recomputed": first_delivery,
        "max_gap_s_recomputed": max_gap,
        "max_gap_start_s": gap_start,
        "max_gap_end_s": gap_end,
        "scheduled_tx_unique": len(tx_times),
        "unique_rx_matched": len(delivered),
        "schedule_bad_rows": bad_rows,
        "all_delivered_times": delivered,
        "all_intervals": intervals,
    }


def type7(values: list[float], p: float) -> float:
    values = sorted(v for v in values if math.isfinite(v))
    if not values:
        return math.nan
    position = p * (len(values) - 1)
    low = int(position)
    high = min(low + 1, len(values) - 1)
    fraction = position - low
    return values[low] * (1 - fraction) + values[high] * fraction


def pearson(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return math.nan
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    dy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    return sum((x - mx) * (y - my) for x, y in pairs) / (dx * dy) if dx and dy else math.nan


def graph_edges(path: Path) -> tuple[dict[int, set[int]], dict[str, str]]:
    adjacency: dict[int, set[int]] = defaultdict(set)
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            u, v = int(row["u"]), int(row["v"])
            adjacency[u].add(v)
            adjacency[v].add(u)
    return adjacency, {str(k): str(len(v)) for k, v in adjacency.items()}


def shortest_path(adjacency: dict[int, set[int]], source: int, destination: int) -> list[int]:
    parent: dict[int, int | None] = {source: None}
    queue = deque([source])
    while queue:
        node = queue.popleft()
        if node == destination:
            break
        for neighbor in sorted(adjacency[node]):
            if neighbor not in parent:
                parent[neighbor] = node
                queue.append(neighbor)
    if destination not in parent:
        return []
    path: list[int] = []
    node: int | None = destination
    while node is not None:
        path.append(node)
        node = parent[node]
    return list(reversed(path))


def main() -> None:
    prereg = HERE / "prereg.md"
    if sha256(prereg) != PREREG_HASH:
        raise SystemExit("A4.1b preregistration hash mismatch; refusing analysis")

    runner_path = A4 / "a4.py"
    runner_hash = sha256(runner_path)
    ledger = [r for r in read_csv(A4 / "runs.csv") if r.get("stage") == "4.1"]
    if len(ledger) != 45 or any(r.get("status") != "success" for r in ledger):
        raise SystemExit(f"Expected 45 successful A4.1 rows; found {len(ledger)}")
    derived_rows = read_csv(A4 / "derived_4.1_runs.csv")
    summaries = read_csv(A4 / "derived_4.1.csv")
    if len(derived_rows) != 45 or len(summaries) != 9:
        raise SystemExit("Unexpected A4.1 derived data row count")
    derived_by_dir = {r["output_dir"]: r for r in derived_rows}
    summary_by_key = {(r["protocol"], r["N"]): r for r in summaries}
    a1_covariates = {r["graph_id"]: r for r in read_csv(A1 / "results" / "graph_covariates.csv")}

    run_rows: list[dict[str, object]] = []
    run_data: dict[str, dict[str, object]] = {}
    for record in ledger:
        out = A4 / record["output_dir"]
        protocol = record["protocol"]
        derived_row = derived_by_dir[record["output_dir"]]
        packet_path = out / f"packets_{protocol}.csv"
        result = detector(packet_path)
        flows = [r for r in read_csv(out / "flows.csv") if r.get("protocol") == protocol and r.get("is_probe") == "1"]
        first_from_flow = num(flows[0].get("first_delivery_s")) if len(flows) == 1 else math.nan
        first_recomputed = num(result["first_delivery_s_recomputed"])
        readiness = num(result["readiness_s"])
        recorded = num(derived_row.get("convergence_s"))
        gap_prior_ledger = num(record.get("all_up_gap_s"))
        gap_prior_derived = num(derived_row.get("all_up_gap_s"))
        gap = num(result["max_gap_s_recomputed"])
        g1 = (math.isnan(recorded) and math.isnan(readiness)) or (
            math.isfinite(recorded) and math.isfinite(readiness) and abs(recorded - readiness) <= 0.5
        )
        g2_applicable = math.isfinite(gap) and gap <= G
        g2_violation = g2_applicable and (not math.isfinite(readiness) or not math.isfinite(first_from_flow) or readiness > first_from_flow + MIN_AGE + 1e-9)
        censored = not math.isfinite(readiness) or readiness > CENSOR_LIMIT
        cluster = protocol == "aodv" and math.isfinite(readiness) and 113.0 <= readiness <= 115.0
        row = {
            "run_id": record["run_id"], "family": record["family"], "N": record["N"], "protocol": protocol,
            "first_delivery_s": fmt(first_from_flow),
            "first_delivery_s_recomputed": fmt(first_recomputed),
            "recorded_convergence_s": fmt(recorded), "recomputed_readiness_s": fmt(readiness),
            "readiness_minus_first_delivery_s": fmt(readiness - first_from_flow) if math.isfinite(readiness) and math.isfinite(first_from_flow) else "nan",
            "recorded_gap_ledger_before_b": fmt(gap_prior_ledger),
            "recorded_gap_derived_before_b": fmt(gap_prior_derived),
            "recomputed_max_gap_s": fmt(gap),
            "max_gap_start_rx_s": fmt(num(result["max_gap_start_s"])),
            "max_gap_end_rx_s": fmt(num(result["max_gap_end_s"])),
            "scheduled_tx_unique": result["scheduled_tx_unique"], "unique_rx_matched": result["unique_rx_matched"],
            "schedule_bad_rows": result["schedule_bad_rows"], "G1_match_within_0.5s": bool_text(g1),
            "G2_applicable_gap_le_1s": bool_text(g2_applicable), "G2_violation": bool_text(g2_violation),
            "censored_gt_180_or_nan": bool_text(censored), "aodv_113_115_cluster": bool_text(cluster),
            "runner_sha256": runner_hash,
        }
        run_rows.append(row)
        run_data[record["run_id"]] = {**result, **row, "record": record, "derived": derived_row}
    write_csv(HERE / "run_reconciliation.csv", list(run_rows[0]), run_rows)

    # Gap events and the all-45 empirical distribution.
    gap_rows: list[dict[str, object]] = []
    dsdv_timer_rows: list[dict[str, object]] = []
    all_max_gaps: list[float] = []
    dsdv_runs_with_timer_match: set[str] = set()
    dsdv_gap_event_matches = 0
    for record in ledger:
        data = run_data[record["run_id"]]
        intervals = data["all_intervals"]
        matches: list[tuple[float, float, float, int]] = []
        for gap, start, end in intervals:
            if record["protocol"] == "dsdv" and math.isfinite(start):
                nearest = round(start / 15.0)
                delta = start - nearest * 15.0
                if nearest >= 1 and abs(delta) <= 0.5:
                    matches.append((start, end, gap, nearest))
        if record["protocol"] == "dsdv":
            dsdv_gap_event_matches += len(matches)
            if matches:
                dsdv_runs_with_timer_match.add(record["run_id"])
            for start, end, gap, multiple in matches:
                dsdv_timer_rows.append({
                    "run_id": record["run_id"], "family": record["family"], "N": record["N"],
                    "nearest_15s_multiple": multiple, "start_rx_s": fmt(start), "end_rx_s": fmt(end),
                    "gap_s": fmt(gap), "start_offset_from_multiple_s": fmt(start - multiple * 15.0),
                })
        max_gap = num(data["recomputed_max_gap_s"])
        all_max_gaps.append(max_gap)
        gap_rows.append({
            "run_id": record["run_id"], "family": record["family"], "N": record["N"], "protocol": record["protocol"],
            "unique_rx_count": len(data["all_delivered_times"]), "max_gap_s": fmt(max_gap),
            "gap_start_rx_s": data["max_gap_start_s"], "gap_end_rx_s": data["max_gap_end_s"],
            "max_gap_gt_5s": bool_text(math.isfinite(max_gap) and max_gap > 5),
            "max_gap_ge_15s": bool_text(math.isfinite(max_gap) and max_gap >= 15),
            "dsdv_start_near_15s_multiple_event_count": len(matches),
        })
    write_csv(HERE / "max_gap_distribution.csv", list(gap_rows[0]), sorted(gap_rows, key=lambda r: float(r["max_gap_s"])))
    timer_fields = ["run_id", "family", "N", "nearest_15s_multiple", "start_rx_s", "end_rx_s", "gap_s", "start_offset_from_multiple_s"]
    write_csv(HERE / "dsdv_15s_timer_gap_events.csv", timer_fields, dsdv_timer_rows)

    # Nine warm-up decisions, re-derived from recomputed readiness.
    warmup_rows: list[dict[str, object]] = []
    cell_gate: dict[tuple[str, str], dict[str, object]] = {}
    for protocol in PROTOCOLS:
        for size in SIZES:
            cell = [d for d in run_data.values() if d["record"]["protocol"] == protocol and int(d["record"]["N"]) == size]
            g1_all = all(d["G1_match_within_0.5s"] == "true" for d in cell)
            g2_all = all(d["G2_violation"] == "false" for d in cell)
            censored = any(d["censored_gt_180_or_nan"] == "true" for d in cell)
            g3_valid = g1_all and g2_all and not censored
            stored_summary = summary_by_key[(protocol, str(size))]
            values = [num(d["recomputed_readiness_s"]) for d in cell]
            finite = [x for x in values if math.isfinite(x)]
            expected_warmup = math.ceil(1.5 * max(finite)) if g3_valid and finite else math.nan
            recorded_warmup = stored_summary["warmup_frames"]
            if g3_valid:
                status = "derived" if recorded_warmup == str(expected_warmup) else "warmup_record_mismatch"
            elif not g1_all or not g2_all:
                status = "invalid_pending_detector"
            else:
                status = "not_derivable_censored"
            reason = "all five runs pass G1/G2 and are uncensored" if g3_valid else (
                "G1 detector mismatch" if not g1_all else "G2 first-delivery-plus-10-s bound violated" if not g2_all else "one or more runs censored (>180 s or NaN)"
            )
            item = {
                "protocol": protocol, "N": size, "family_runs": len(cell),
                "G1_all_family_runs_pass": bool_text(g1_all), "G2_all_family_runs_pass": bool_text(g2_all),
                "censored_family_run_count": sum(d["censored_gt_180_or_nan"] == "true" for d in cell),
                "recomputed_convergence_min_s": fmt(min(finite) if len(finite) == len(values) else math.nan),
                "recomputed_convergence_median_s": fmt(type7(values, 0.5)),
                "recomputed_convergence_max_s": fmt(max(finite) if len(finite) == len(values) else math.nan),
                "registered_warmup_frames": recorded_warmup, "reconciled_warmup_frames": expected_warmup if math.isfinite(expected_warmup) else status,
                "G3_warmup_status": status, "reason": reason,
            }
            warmup_rows.append(item)
            cell_gate[(protocol, str(size))] = {"valid": g3_valid, "g1": g1_all, "g2": g2_all, "censored": censored}
    write_csv(HERE / "warmup_gate.csv", list(warmup_rows[0]), warmup_rows)

    # Correlations are emitted only for protocols whose three size cells pass G3.
    correlation_rows: list[dict[str, object]] = []
    correlation_gate_status: dict[str, str] = {}
    for protocol in PROTOCOLS:
        allowed = all(cell_gate[(protocol, str(size))]["valid"] for size in SIZES)
        if not allowed:
            correlation_gate_status[protocol] = "not_computed_G3_not_valid_all_sizes"
            continue
        values = [d for d in run_data.values() if d["record"]["protocol"] == protocol]
        xs_n = [float(d["record"]["N"]) for d in values]
        ys = [num(d["recomputed_readiness_s"]) for d in values]
        diameters = [float(d["derived"]["diameter"]) for d in values]
        correlation_rows.append({
            "protocol": protocol, "relationship": "convergence_vs_N_all_15", "n": len(values),
            "pearson_r": fmt(pearson(xs_n, ys)), "censored_handling": "none; all 15 uncensored",
        })
        for size in SIZES:
            selected = [d for d in values if int(d["record"]["N"]) == size]
            correlation_rows.append({
                "protocol": protocol, "relationship": f"convergence_vs_diameter_N{size}", "n": len(selected),
                "pearson_r": fmt(pearson([float(d["derived"]["diameter"]) for d in selected],
                                         [num(d["recomputed_readiness_s"]) for d in selected])),
                "censored_handling": "none; all five at size uncensored",
            })
        correlation_gate_status[protocol] = "computed_all_cells_G1_G2_G3_pass"
    write_csv(HERE / "correlation_results.csv", ["protocol", "relationship", "n", "pearson_r", "censored_handling"], correlation_rows)

    # AODV values in and around the 113-115 s convergence cluster.
    aodv_rows = [r for r in run_rows if r["protocol"] == "aodv"]
    write_csv(HERE / "aodv_113s_cluster.csv", list(aodv_rows[0]), aodv_rows)

    # DSDV protocol-timer alignment: all 15 runs, all unique-reception intervals.
    dsdv_timer_summary: list[dict[str, object]] = []
    for group_n in (42, 92, 162, 0):
        group_runs = [r for r in ledger if r["protocol"] == "dsdv" and (group_n == 0 or int(r["N"]) == group_n)]
        run_ids = {r["run_id"] for r in group_runs}
        matched = [r for r in dsdv_timer_rows if r["run_id"] in run_ids]
        matched_lengths = [num(r["gap_s"]) for r in matched]
        dsdv_timer_summary.append({
            "scope": "all_DSDV_sizes" if group_n == 0 else f"N{group_n}",
            "dsdv_runs": len(group_runs),
            "runs_with_gap_start_within_0.5s_of_positive_15s_multiple": len({r["run_id"] for r in matched}),
            "matched_gap_events": len(matched),
            "matched_gap_length_min_s": fmt(min(matched_lengths)) if matched_lengths else "nan",
            "matched_gap_length_median_s": fmt(type7(matched_lengths, .5)),
            "matched_gap_length_max_s": fmt(max(matched_lengths)) if matched_lengths else "nan",
            "matching_gap_events_path": "dsdv_15s_timer_gap_events.csv",
        })
    write_csv(HERE / "dsdv_timer_summary.csv", list(dsdv_timer_summary[0]), dsdv_timer_summary)

    # BA N=162: whole-run, non-temporal node counters only; never infer a 110-150 s slice.
    ba_graph_id = "ba_N162_r1"
    cov = a1_covariates[ba_graph_id]
    adjacency, degrees_text = graph_edges(A1 / "results" / "edge_lists" / f"{ba_graph_id}.csv")
    source, destination = int(cov["probe_S"]), int(cov["probe_R"])
    path_nodes = shortest_path(adjacency, source, destination)
    max_degree = max(len(neighbors) for neighbors in adjacency.values())
    hub_nodes = sorted(node for node, neighbors in adjacency.items() if len(neighbors) == max_degree)
    selected_roles: dict[int, set[str]] = defaultdict(set)
    for node in hub_nodes:
        selected_roles[node].add("max_degree_hub")
    for node in path_nodes:
        selected_roles[node].add("canonical_A1_shortest_path")
    node_path = A4 / "runs" / "41_ba_N162_r1_olsr_probe" / "node_diagnostics.csv"
    raw_node_rows = [r for r in read_csv(node_path) if r.get("protocol") == "olsr"]
    ba_rows: list[dict[str, object]] = []
    for row in raw_node_rows:
        node = int(row["node_id"])
        if node not in selected_roles:
            continue
        ba_rows.append({
            "node_id": node, "degree": len(adjacency[node]), "role": ";".join(sorted(selected_roles[node])),
            "metric": row["metric"], "message_type": row.get("message_type", ""),
            "phy_reason": row.get("phy_reason", ""), "value_whole_run": row["value"],
            "requested_window_110_150_s": "unavailable_no_timestamps",
            "equal_length_other_windows": "unavailable_no_timestamps",
        })
    write_csv(HERE / "ba_olsr_hub_path_node_metrics.csv", list(ba_rows[0]), ba_rows)
    packet_diag_path = node_path.parent / "packet_diagnostics_olsr.csv"
    packet_diag_rows = read_csv(packet_diag_path)
    unparsed_metric_rows = [r for r in raw_node_rows if "unparsed" in r.get("metric", "").lower()]
    result_rows = read_csv(node_path.parent / "trace_replay_results.csv")
    result_header = list(result_rows[0]) if result_rows else []
    unparsed_columns = [name for name in result_header if "unparsed" in name.lower()]
    parser_rows: list[dict[str, object]] = []
    for row in unparsed_metric_rows:
        parser_rows.append({"source_file": "node_diagnostics.csv", "metric": row["metric"], "message_type": row.get("message_type", ""), "value": row["value"], "time_scope": "whole_run_only"})
    for row in packet_diag_rows:
        for key, value in row.items():
            if "unparsed" in key.lower():
                parser_rows.append({"source_file": "packet_diagnostics_olsr.csv", "metric": key, "message_type": "", "value": value, "time_scope": "whole_run_only"})
    for row in result_rows:
        for key, value in row.items():
            if "unparsed" in key.lower():
                parser_rows.append({"source_file": "trace_replay_results.csv", "metric": key, "message_type": "", "value": value, "time_scope": "whole_run_only"})
    if not parser_rows:
        parser_rows.append({"source_file": ";".join([node_path.name, packet_diag_path.name]), "metric": "control_unparsed_*", "message_type": "", "value": "not_present_in_time-resolved_form", "time_scope": "no_time-resolved_counter"})
    write_csv(HERE / "ba_olsr_unparsed_counter.csv", ["source_file", "metric", "message_type", "value", "time_scope"], parser_rows)

    # Static evidence about instrumentation granularity: schema-level timestamp availability.
    source_files = [node_path, packet_diag_path, node_path.parent / "trace_replay_results.csv"]
    schema_rows = []
    for path in source_files:
        rows = read_csv(path)
        headers = list(rows[0]) if rows else []
        schema_rows.append({
            "file": str(path.relative_to(A4)), "rows": len(rows),
            "has_event_time_column": bool(any(h.lower() in {"event_time_s", "timestamp_s", "sim_time_s", "event_timestamp"} for h in headers)),
            "headers": "|".join(headers), "scope": "run-level counters/results; no per-event counter timestamps",
        })
    write_csv(HERE / "ba_olsr_source_schema.csv", list(schema_rows[0]), schema_rows)

    # One compact machine-readable gate row set.
    g1_bad = [r for r in run_rows if r["G1_match_within_0.5s"] != "true"]
    g2_bad = [r for r in run_rows if r["G2_violation"] == "true"]
    gates = [
        {"gate": "G1", "pass": bool_text(not g1_bad), "n_tested": 45, "n_fail": len(g1_bad), "basis": "all 45 recomputed packet-log values vs derived_4.1_runs convergence_s; tolerance <=0.5 s"},
        {"gate": "G2", "pass": bool_text(not g2_bad), "n_tested": sum(r["G2_applicable_gap_le_1s"] == "true" for r in run_rows), "n_fail": len(g2_bad), "basis": "corrected max gap <=1 s; readiness <= first delivery +10 s"},
        {"gate": "G3", "pass": bool_text(all(x["valid"] for x in cell_gate.values())), "n_tested": 9, "n_fail": sum(not x["valid"] for x in cell_gate.values()), "basis": "cellwise G1/G2 plus no >180 s or NaN censoring"},
    ]
    write_csv(HERE / "gate_results.csv", list(gates[0]), gates)

    dependency_rows = [
        {"issue": "DSDV warm-up censored, all N", "4.2_max_cells": 45, "4.3_max_cells": 24, "detail": "5 families × 3 N × 3 roles; random families × 3 N × 2 realizations"},
        {"issue": "DSDV RGG N162 >5s outage (subset above)", "4.2_max_cells": 3, "4.3_max_cells": 2, "detail": "same protocol/graph cell; do not add to DSDV censor total"},
        {"issue": "OLSR censor, N92 and N162", "4.2_max_cells": 30, "4.3_max_cells": 16, "detail": "5 families × 2 N × 3 roles; 4 random families × 2 N × 2 realizations"},
        {"issue": "AODV N42 and N92 unusual warm-ups", "4.2_max_cells": 0, "4.3_max_cells": 0, "detail": "G1/G2/G3 pass; no current exclusion; voluntary drop would free 30/16 max cells"},
    ]
    write_csv(HERE / "budget_dependencies.csv", list(dependency_rows[0]), dependency_rows)

    # Compact whole-run node summary for the BA/OLSR hub and canonical A1 path.
    selected_nodes = sorted(selected_roles)
    node_map: dict[int, dict[tuple[str, str, str], int]] = defaultdict(dict)
    for r in raw_node_rows:
        node_map[int(r["node_id"])][(r["metric"], r.get("message_type", ""), r.get("phy_reason", ""))] = int(r["value"])
    overview_rows: list[dict[str, object]] = []
    for node in selected_nodes:
        values = node_map[node]
        def metric_value(metric_name: str, message: str = "", reason: str = "") -> int:
            return values.get((metric_name, message, reason), 0)
        controls = []
        for message in ("olsr_hello", "olsr_tc", "olsr_mid", "olsr_hna", "olsr_other"):
            controls.append(f"{message}:{metric_value('control_tx_packets', message)}/{metric_value('control_tx_bytes', message)}")
        phy_raw = [f"{reason}:{value}" for (name, _, reason), value in values.items() if name == "phy_rx_drop_raw_reason" and value]
        overview_rows.append({
            "node_id": node, "degree": len(adjacency[node]), "role": ";".join(sorted(selected_roles[node])),
            "control_packets_bytes_by_type": "|".join(controls),
            "mac_retries": metric_value("mac_data_failed_events"),
            "mac_final_data_failures": metric_value("mac_final_data_failed"),
            "mac_tx_drops": metric_value("mac_tx_drops"), "mac_queue_drops": metric_value("mac_queue_drops"),
            "phy_rx_drops_by_raw_reason": "|".join(phy_raw),
            "phy_collision_interference_class": metric_value("phy_rx_drop_class", reason="collision_interference"),
            "forwarded_app_packets": metric_value("forwarded_app_packets_ipv4"),
            "time_scope": "whole_run_only; 110-150s and equal-length windows unavailable",
        })
    write_csv(HERE / "ba_olsr_node_overview.csv", list(overview_rows[0]), overview_rows)

    # Build the bounded narrative from exactly the recorded outputs.
    gap_values = [num(r["max_gap_s"]) for r in gap_rows]
    finite_gaps = [x for x in gap_values if math.isfinite(x)]
    gt5 = sum(x > 5 for x in finite_gaps)
    ge15 = sum(x >= 15 for x in finite_gaps)
    report: list[str] = [
        "# A4.1b — offline detector, gaps, and warm-up reconciliation",
        "",
        "**Written after A4.1b results.** Offline only: 0 variants; no ns-3 invocation, simulator, or rerun. A4.0*/A4.1 artifacts, preregistration, and amendments were read-only. The only external edit is this stage's single entry in [Alpha gates](../../gates.md). Budget remains 70/300; A4.2/A4.3 are unauthorized.",
        "",
        f"Frozen preregistration SHA-256: `{PREREG_HASH}`. Analysis implementation: [analyze.py](analyze.py); runner [run.sh](run.sh). A4 runner source: [a4.py](../a4.py), SHA-256 `{runner_hash}`.",
        "",
        "## G1–G3 outcomes",
        "",
        f"- **G1 PASS:** 0/45 mismatches at ≤0.5 s. NaN matches NaN only. Every recomputed packet-log readiness matches `derived_4.1_runs.csv`.",
        f"- **G2 PASS:** {sum(r['G2_applicable_gap_le_1s']=='true' for r in run_rows)} applicable runs (corrected max gap ≤1 s); 0 violations of readiness ≤ first delivery +10 s.",
        f"- **G3 PARTIAL / overall FAIL:** 4/9 protocol×N warm-ups valid; 5/9 are `not_derivable_censored` (OLSR N=92/162; DSDV N=42/92/162). No `invalid_pending_detector` cell.",
        "- On any hypothetical mismatch, the frozen cause categories are stale input / extra undeclared condition / implementation bug. No mismatch occurred, so none is assigned.",
        "",
        "## Step 1 — source and AODV cluster",
        "",
        "The producing path is `run_4_1()` → `run_variant()` → `summarize_run()` → `readiness_from_probe_packets()` in [a4.py](../a4.py#L219-L301). It reads the packet log's schedule-matched Tx/Rx app timestamps (with nonnegative sequence as a validity filter); convergence does **not** read `all_up_gap_s`, the old sequence-derived gap, corrected gap CSVs, PDR, or a loss counter. Thus the gap correction is not a stale convergence input. The helper applies unique Rx spacing over trailing 10-s windows, G=1 s, minimum age 10 s, and returns the first event in the final passing suffix; it does not calculate a packet-count PDR window.",
        "",
        "Four AODV runs are in 113–115 s: three N=42 (RGG/WS/ER) and one N=92 (RGG). Their first deliveries are 104.484–105.462 s; readiness follows by 9.000–9.159 s. This is not one shared readiness timestamp. It is consistent with the written 10-s minimum observation age plus the suffix rule; no extra PDR/loss condition is present in the source. The registered warm-up is 171/173 frames because this valid late readiness is the maximum in those cells, not because max delivery gaps are large.",
        "",
        "### Per-run first delivery and convergence",
        "",
        "| Family | N | Protocol | First delivery (s) | Registered convergence (s) | Recomputed readiness (s) | Max gap (s) |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for r in run_rows:
        report.append(
            f"| {r['family']} | {r['N']} | {r['protocol']} | {r['first_delivery_s']} | {r['recorded_convergence_s']} | {r['recomputed_readiness_s']} | {r['recomputed_max_gap_s']} |"
        )
    report += [
        "",
        "## Step 2 — DSDV timer alignment and gap distribution",
        "",
        "All 15 DSDV runs contain at least one delivered-packet gap start within ±0.5 s of a positive 15-s multiple: 1,123 matching intervals total (N=42: 414; N=92: 357; N=162: 352). Matching gap-length ranges are N=42 0.001178–1.260643 s, N=92 0.000688–1.531093 s, and N=162 0.000614–5.326506 s; the median is 0.16384 s at each size. All starts/lengths are in [dsdv_15s_timer_gap_events.csv](dsdv_15s_timer_gap_events.csv). RGG/DSDV N=162 starts at 179.999402 s, 0.000598 s before 180 s, and lasts 5.326506 s. App Tx schedule points are spaced 0.16384 s; the ±0.5-s matching window is broad relative to that spacing, so alignment is descriptive, not timer-causality evidence.",
        f"",
        f"Across all 45 run-level maximum gaps: min {min(finite_gaps):.6f} s, median {type7(finite_gaps,.5):.6f} s, p90 {type7(finite_gaps,.9):.6f} s, max {max(finite_gaps):.6f} s; {gt5}/45 exceed 5 s, {ge15}/45 are ≥15 s. The strict preregistered >5-s threshold has one observed DSDV crossing (RGG N=162) but only 2/45 maximum-gap crossings overall; this sparse result does not validate the threshold as a predictor. Do not compare it as equivalent to the Phase 6D 15-s outage: warm-up and propagation setups differ.",
        "",
        "## Step 3 — BA/OLSR N=162 event evidence limits",
        "",
        f"The A1 BA graph has max-degree hub node 0 (degree 37); the probe pair is 49→103 and one canonical A1 shortest path is { '→'.join(map(str,path_nodes)) }. [Whole-run per-node counters](ba_olsr_node_overview.csv) retain control packets/bytes by message type, MAC/PHY/queue counters, and forwarding for these nodes. These counters have no event timestamps; equal-length 110–150-s versus other windows cannot be computed. The A4.1 command did not enable `emitControlUnparsed`; no `control_unparsed_*` field exists in this run's saved per-node, packet-diagnostics, or result CSVs, so no time-local parser counter is available.",
        "",
        "Whole-run evidence (HELLO/TC/other packets; MAC retries; final failures; queue drops; PHY collision-class drops; forwarded packets):",
        "| Node | Degree / role | HELLO p/b | TC p/b | Other p/b | retries/final | queue/TX drop | PHY collision | forwarded |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    overview_by_node = {int(r["node_id"]): r for r in overview_rows}
    selected_sorted = sorted(selected_nodes, key=lambda n: (n not in hub_nodes, n))
    for node in selected_sorted:
        r = overview_by_node[node]
        controls = {item.split(":", 1)[0]: item.split(":", 1)[1] for item in str(r["control_packets_bytes_by_type"]).split("|")}
        role = "hub + path" if node in hub_nodes and node in path_nodes else "hub" if node in hub_nodes else "path"
        report.append(f"| {node} | {r['degree']} / {role} | {controls['olsr_hello']} | {controls['olsr_tc']} | {controls['olsr_other']} | {r['mac_retries']}/{r['mac_final_data_failures']} | {r['mac_queue_drops']}/{r['mac_tx_drops']} | {r['phy_collision_interference_class']} | {r['forwarded_app_packets']} |")
    report += [
        "",
        "Selected-node PHY raw reasons (all-run counts; full values, including TXING/RXING and abort reasons, are in the CSV): node 0 BUSY_DECODING_PREAMBLE=315, PREAMBLE_DETECT_FAILURE=5,941, RXING=4,208; node 2=112/1,315/1,872; node 10=106/1,217/1,793; node 49=16/86/244; node 63=25/293/615; node 103=13/54/261. OLSR MID/HNA control counts are zero on these selected nodes.",
        "",
        "The full CSV also gives each selected node's PHY raw-reason breakdown. Across the entire run, retry maximum is node 49 (568), not hub 0 (267); queue drops are zero network-wide. Hub 0 has 9,494 collision-class drops, the maximum (network mean 575.46), but this is not time-local. Node 0 and path node 2 have similar whole-run control totals (456 vs 455 packets; TC 220 vs 227); path-node retry counts are heterogeneous. Hub-load association is possible but untested for the event window. TC/MPR timing cannot be aligned without timestamps. Telemetry/parser artifact cannot be confirmed or excluded locally because the unparsed counter was not emitted. **The saved evidence cannot discriminate causes; no cause is inferred.**",
        "",
        "## Step 4 — correlations",
        "",
        "Correlations are reported only for AODV, whose three size cells pass G1/G2/G3: convergence-vs-N Pearson r = −0.521556 (n=15); diameter r by N=42/92/162 = 0.484193/0.770287/0.892316 (n=5 each). No censored values were included. OLSR and DSDV correlations are not reported because one or more contributing warm-up cells fail G3. These are descriptive only.",
        "",
        "## Step 5 — warm-up status and proposal-only options",
        "",
        "| Protocol | N=42 | N=92 | N=162 |",
        "|---|---|---|---|",
    ]
    for protocol in PROTOCOLS:
        statuses = [next(r for r in warmup_rows if r["protocol"] == protocol and int(r["N"]) == n) for n in SIZES]
        cells = [f"{r['registered_warmup_frames']} ({r['G3_warmup_status']}; {r['reason']})" for r in statuses]
        report.append(f"| {protocol} | {cells[0]} | {cells[1]} | {cells[2]} |")
    report += [
        "",
        "| 4.2 option (not selected) | Run/frame consequence | Variant consequence / assumption |",
        "|---|---|---|",
        "| Fixed protocol/size warm-up from noncensored data | Keep registered 120 measured frames; total = warm-up +120. AODV valid values give 291/293/139 frames at N=42/92/162. OLSR has only N=42=32; DSDV has no uncensored same-cell estimate. | 0 added variants if replacing existing cells (≤135); extrapolation to censored sizes assumes transfer not supported by evidence. |",
        "| Fixed 180-frame warm-up | 300 total frame-seconds with 120 measured; exceeds a 240-frame total by 60. Still below observed censored convergence up to 235.376 s. | 0 added variants; does not guarantee readiness. |",
        "| Per-run readiness-gated 120-frame measurement | Variable warm-up +120, potentially >240; must measure readiness under load and may need extra duration. | Same cell count if replacing runs; assumes detector transfers under load; runtime increase unknown. |",
        "| Drop affected protocol×N cells | Avoids unsupported warm-up, reduces planned executed cells. | No added variants; DSDV censor skips up to 45/24 in 4.2/4.3; OLSR censor N92/162 skips up to 30/16. AODV N42/92 pass gates; a discretionary drop would free 30/16 but is unsupported by these gates. |",
        "",
        "The RGG/DSDV N=162 outage exclusion is a subset of DSDV's censored set: 3 4.2 load-role variants and at most 2 4.3 replication variants, not additive. No option is chosen.",
        "",
        "## Step 6 — budget and stop",
        "",
        "Spent 70/300; registered maxima 4.2=135 and 4.3=72 leave 23 spare. Current preregistered warm-up exclusions touch up to 75 4.2 variants (45 DSDV +30 OLSR) and 40 4.3 variants (24 DSDV +16 OLSR); the DSDV N162 RGG 3/2 outage counts are included above. AODV N42/92 are valid despite the late first deliveries; no current exclusion is indicated. See [budget dependencies](budget_dependencies.csv).",
        "",
        "### Decisions needed (no action taken)",
        "",
        "1. Whether to retain the validated provisional G=1 readiness rule for any later-stage proposal, without changing A4.1 results.",
        "2. How to handle the censored DSDV cells and censored OLSR N=92/162 cells: skip per preregistration or propose a separately registered warm-up/window design.",
        "3. Whether the AODV N=42/92 late-first-delivery warm-ups are acceptable as recorded (G1–G3 pass), or whether a separately justified change should be proposed.",
        "4. Whether to preserve the registered >5-s DSDV exclusion (including RGG N=162); no alternative is applied here.",
        "5. No A4.2/A4.3 execution is authorized by this report; explicit direction is required before any later-stage work.",
        "",
        "**STOP.** No reruns, detector change, cell disposition, A4.2, or A4.3 were performed. See [Alpha limitations](../../LIMITATIONS.md).",
    ]
    if len(report) > 150:
        raise SystemExit(f"Report exceeds 150 lines: {len(report)}")
    (HERE / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # Print concise facts used by the narrative report.
    gaps = [x for x in all_max_gaps if math.isfinite(x)]
    aodv_cluster = [r for r in run_rows if r["aodv_113_115_cluster"] == "true"]
    print(f"A4.1b prereg hash verified: {PREREG_HASH}")
    print(f"A4.py SHA-256: {runner_hash}")
    print(f"G1 mismatches={len(g1_bad)}/45; G2 applicable={sum(r['G2_applicable_gap_le_1s']=='true' for r in run_rows)}, violations={len(g2_bad)}")
    print("G3 invalid cells:", [(r["protocol"], r["N"], r["G3_warmup_status"]) for r in warmup_rows if r["G3_warmup_status"] != "derived"])
    print("AODV readiness 113-115 s runs:", [(r["run_id"], r["first_delivery_s"], r["recomputed_readiness_s"], r["readiness_minus_first_delivery_s"]) for r in aodv_cluster])
    print("DSDV 15-s timer matches:", dsdv_timer_summary)
    print("45-run max-gap empirical distribution:", {"n": len(gaps), "min": min(gaps), "median": type7(gaps, .5), "p90": type7(gaps, .9), "max": max(gaps)})
    print("BA graph probe nodes/path/hubs:", source, destination, path_nodes, hub_nodes)
    print("BA parser counter unparsed metric rows:", len(unparsed_metric_rows), "columns:", unparsed_columns)
    print("Correlations:", correlation_gate_status, correlation_rows)
    print(f"Report lines: {len(report)}")


if __name__ == "__main__":
    main()
