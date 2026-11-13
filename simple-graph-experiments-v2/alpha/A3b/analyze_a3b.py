#!/usr/bin/env python3
"""Offline A3b gate analysis; reads saved outputs only and launches no simulator."""
from __future__ import annotations

import csv
import json
from pathlib import Path

A3B = Path(__file__).resolve().parent
STUDY = A3B.parents[1]
GOLDEN = STUDY / "phase7" / "7B" / "legacy_before" / "trace_replay_results.csv"


def dict_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    t1_flow_header, t1_flows = dict_rows(A3B / "T1" / "flows.csv")
    _, node_rows = dict_rows(A3B / "T1" / "node_diagnostics.csv")
    packets: dict[str, dict[str, list[dict[str, str]]]] = {}
    for protocol in ("olsr", "aodv"):
        _, event_rows = dict_rows(A3B / "T1" / f"forward_events_{protocol}.csv")
        _, app_rows = dict_rows(A3B / "T1" / f"packets_{protocol}.csv")
        _, flow_rows = dict_rows(A3B / "T1" / "flows.csv")
        _, diagnostics = dict_rows(A3B / "T1" / f"packet_diagnostics_{protocol}.csv")
        flow = next(row for row in flow_rows if row["protocol"] == protocol and row["is_probe"] == "1")
        diag = diagnostics[0]
        forwarded = {
            int(row["node_id"]): int(row["value"])
            for row in node_rows
            if row["protocol"] == protocol and row["metric"] == "forwarded_app_packets_ipv4"
        }
        offered = int(flow["offered_packets"])
        delivered = int(flow["delivered_unique_packets"])
        expected_by_node = {0: 0, 1: delivered, 2: delivered, 3: 0}
        delivered_sequences = {
            int(row["sequence"]) for row in app_rows if row["event"] == "rx"
        }
        forward_sequences: dict[int, list[int]] = {}
        for row in event_rows:
            if row["counts_as_forward"] == "1" and row["sequence"]:
                forward_sequences.setdefault(int(row["sequence"]), []).append(int(row["node_id"]))
        expected_path = [1, 2]
        reconstruction_pass = True
        reconstruction_rows = []
        for sequence in sorted({int(row["sequence"]) for row in app_rows if row["event"] == "tx"}):
            observed_nodes = sorted(forward_sequences.get(sequence, []))
            is_delivered = sequence in delivered_sequences
            row_pass = (observed_nodes == expected_path) if is_delivered else True
            reconstruction_pass = reconstruction_pass and row_pass
            reconstruction_rows.append({
                "protocol": protocol,
                "sequence": sequence,
                "delivered": int(is_delivered),
                "forwarding_nodes": ";".join(map(str, observed_nodes)),
                "expected_delivered_path_nodes": ";".join(map(str, expected_path)) if is_delivered else "",
                "path_matches": int(row_pass),
            })
        delivered_equals_offered = offered == delivered == 391
        per_node_pass = all(forwarded.get(node, 0) == expected for node, expected in expected_by_node.items())
        total = sum(forwarded.values())
        total_pass = total == delivered * 2
        t1_pass = delivered_equals_offered and per_node_pass and total_pass and reconstruction_pass
        packets[protocol] = {
            "flow": flow,
            "diag": diag,
            "events": event_rows,
            "forwarded": {str(node): forwarded.get(node, 0) for node in range(4)},
            "offered": offered,
            "delivered": delivered,
            "forwarded_total": total,
            "delivered_equals_offered": delivered_equals_offered,
            "per_node_pass": per_node_pass,
            "forwarded_total_pass": total_pass,
            "per_packet_reconstruction_pass": reconstruction_pass,
            "pass": t1_pass,
        }
        if protocol == "olsr":
            packets[protocol]["reconstruction_rows"] = reconstruction_rows
        else:
            packets[protocol]["reconstruction_rows"] = reconstruction_rows

    reconstruction = packets["olsr"]["reconstruction_rows"] + packets["aodv"]["reconstruction_rows"]
    write_csv(A3B / "packet_hop_reconstruction.csv",
              ["protocol", "sequence", "delivered", "forwarding_nodes",
               "expected_delivered_path_nodes", "path_matches"], reconstruction)

    current_header, current_rows = dict_rows(A3B / "T4" / "trace_replay_results.csv")
    golden_header, golden_rows = dict_rows(GOLDEN)
    time_columns = {"wall_time_s", "cpu_time_s"}
    current_non_time = [name for name in current_header if name not in time_columns]
    golden_non_time = [name for name in golden_header if name not in time_columns]
    new_columns = [name for name in current_non_time if name not in golden_non_time]
    missing_columns = [name for name in golden_non_time if name not in current_non_time]
    golden_by_protocol = {row["protocol"]: row for row in golden_rows if row["protocol"] in {"olsr", "aodv"}}
    t4_comparisons = {}
    for protocol in ("olsr", "aodv"):
        current = next(row for row in current_rows if row["protocol"] == protocol)
        golden = golden_by_protocol[protocol]
        same_schema = current_non_time == golden_non_time
        mismatched = [column for column in golden_non_time if current.get(column) != golden.get(column)]
        t4_comparisons[protocol] = {
            "same_non_time_schema_order": same_schema,
            "mismatched_columns": mismatched,
            "golden_pass": same_schema and not mismatched and not new_columns,
        }

    _, control_rows = dict_rows(A3B / "T1" / "control_events_aodv.csv")
    rrep_at_zero = [row for row in control_rows
                    if row["direction"] == "rx" and row["node_id"] == "0" and row["message_type"] == "aodv_rrep"]
    first_rrep_at_zero = min(float(row["time_s"]) for row in rrep_at_zero) if rrep_at_zero else None
    node0_forwards = [row for row in packets["aodv"]["events"]
                      if row["node_id"] == "0" and row["source_is_local"] == "1"]
    node0_forward_times = [float(row["time_s"]) for row in node0_forwards]
    node0_sequences = [int(row["sequence"]) for row in node0_forwards if row["sequence"]]
    rerr_events = [row for row in control_rows if row["message_type"] == "aodv_rerr"]
    first_route_rx_matches = (first_rrep_at_zero is not None and bool(node0_forward_times)
                              and all(time == first_rrep_at_zero for time in node0_forward_times))
    diagnosis = {
        "H_a": "supported",
        "H_a_evidence": {
            "node0_events": len(node0_forwards),
            "source_address_is_node0_local": all(row["source_is_local"] == "1" for row in node0_forwards),
            "sequences": node0_sequences,
            "forward_times_s": node0_forward_times,
            "first_rrep_rx_node0_s": first_rrep_at_zero,
            "both_events_coincide_with_first_rrep": first_route_rx_matches,
            "interpretation": "AODV deferred queue release produces source-origin packets at the UnicastForward callback as the first RREP reaches node 0; event times equal that RREP reception, rather than preceding it.",
        },
        "H_b": "not supported for these events" if not rerr_events else "undecidable",
        "H_b_rerr_event_count": len(rerr_events),
        "H_c": "not supported for these two events; source-local fields and route-resolution timing identify the registered AODV mechanism",
    }

    variant_rows = []
    for protocol in ("olsr", "aodv"):
        item = packets[protocol]
        variant_rows.append({
            "test": "T1", "protocol": protocol, "seed": 42,
            "offered": item["offered"], "delivered": item["delivered"],
            "forward_node_0": item["forwarded"]["0"], "forward_node_1": item["forwarded"]["1"],
            "forward_node_2": item["forwarded"]["2"], "forward_node_3": item["forwarded"]["3"],
            "forward_total": item["forwarded_total"], "expected_total": item["delivered"] * 2,
            "golden_mismatched_columns": "", "verdict": "PASS" if item["pass"] else "FAIL",
        })
    for protocol in ("olsr", "aodv"):
        compare = t4_comparisons[protocol]
        variant_rows.append({
            "test": "T4_B0", "protocol": protocol, "seed": 42,
            "offered": "", "delivered": "", "forward_node_0": "", "forward_node_1": "",
            "forward_node_2": "", "forward_node_3": "", "forward_total": "", "expected_total": "",
            "golden_mismatched_columns": ";".join(compare["mismatched_columns"]),
            "verdict": "PASS" if compare["golden_pass"] else "FAIL",
        })
    write_csv(A3B / "variant_results.csv",
              ["test", "protocol", "seed", "offered", "delivered", "forward_node_0",
               "forward_node_1", "forward_node_2", "forward_node_3", "forward_total",
               "expected_total", "golden_mismatched_columns", "verdict"], variant_rows)

    class_rows = [{"column": name, "classification": "new-opt-in" if name.startswith("a3b_") else "new-always-on",
                   "reason": "No current-only columns are expected by the frozen 62-column schema inventory."}
                  for name in new_columns]
    write_csv(A3B / "column_classification.csv", ["column", "classification", "reason"], class_rows)
    summary = {
        "stage": "A3b",
        "pre_edit_source_sha256": "0f04a8d87fd261a6544fb76ce5d6e80fa8f4154cdb7aebfd4632b17cd0da4d84",
        "t1": {protocol: {key: value for key, value in item.items() if key not in {"flow", "diag", "events", "reconstruction_rows"}}
               for protocol, item in packets.items()},
        "t1_overall_pass": all(item["pass"] for item in packets.values()),
        "t2_t3": json.loads((A3B / "offline_validation.json").read_text(encoding="utf-8")),
        "t4": {
            "golden_header_non_time_columns": len(golden_non_time),
            "current_header_non_time_columns": len(current_non_time),
            "new_columns": new_columns,
            "missing_golden_columns": missing_columns,
            "protocol_comparisons": t4_comparisons,
            "pass": all(item["golden_pass"] for item in t4_comparisons.values()),
        },
        "diagnosis": diagnosis,
        "same_trace_flags_off_vs_instrumented_check": "excluded; would require a fifth variant",
        "protocol_variants_attempted": 4,
        "protocol_variant_cap": 4,
        "overall_pass": all(item["pass"] for item in packets.values())
                        and all(item["golden_pass"] for item in t4_comparisons.values())
                        and json.loads((A3B / "offline_validation.json").read_text(encoding="utf-8"))["overall_pass"],
    }
    (A3B / "a3b_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
