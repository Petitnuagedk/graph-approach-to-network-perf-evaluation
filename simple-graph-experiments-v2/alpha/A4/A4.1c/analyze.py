#!/usr/bin/env python3
"""A4.1c offline-only readiness and event audit; never invokes a simulator."""
from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
A4 = HERE.parent
ROOT = A4.parents[1]
PREREG_HASH = "66d4f765650d668ce01df786bd89996f018f70f05f8e5119bb7e9a73d538f548"
FIRST_TX = 0.1
INTERVAL = 1024 * 8 / 50_000
TOL = 2e-8
PROTOCOLS = {"aodv", "olsr"}
SIZES = (42, 92, 162)
CENSOR = 180.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(rows[0]) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def num(x: object) -> float:
    try:
        y = float(x)
        return y if math.isfinite(y) else math.nan
    except (ValueError, TypeError):
        return math.nan


def fmt(x: float) -> str:
    return "nan" if not math.isfinite(x) else f"{x:.9g}"


def median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.nan
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def schedule_index(t: float) -> int | None:
    i = round((t - FIRST_TX) / INTERVAL)
    return i if i >= 0 and abs(t - (FIRST_TX + i * INTERVAL)) <= TOL else None


def packet_data(path: Path) -> tuple[list[dict[str, float]], list[float], list[float], list[float]]:
    """Return matched Tx/Rx pairs, all Tx schedule times, unique Rx event times, unmatched Tx times."""
    tx: set[float] = set()
    rx_by_tx: dict[float, float] = {}
    for row in read_csv(path):
        try:
            seq = int(row.get("sequence", "-1"))
        except ValueError:
            continue
        app_tx, event = num(row.get("app_tx_time_s")), num(row.get("event_time_s"))
        if seq < 0 or not math.isfinite(app_tx) or schedule_index(app_tx) is None:
            continue
        key = round(app_tx, 9)
        if row.get("event") == "tx":
            tx.add(key)
        elif row.get("event") == "rx" and math.isfinite(event):
            rx_by_tx[key] = min(event, rx_by_tx.get(key, math.inf))
    all_tx = sorted(tx)
    pairs = [{"tx": t, "rx": rx_by_tx[t], "latency": rx_by_tx[t] - t}
             for t in all_tx if t in rx_by_tx]
    pairs.sort(key=lambda p: (p["rx"], p["tx"]))
    rx_events = sorted({p["rx"] for p in pairs})
    return pairs, all_tx, rx_events, [t for t in all_tx if t not in rx_by_tx]


def readiness(rx_events: list[float]) -> float:
    states: list[tuple[float, bool]] = []
    for t in rx_events:
        if t < FIRST_TX + 10.0 - 1e-12:
            continue
        left = t - 10.0
        values = [x for x in rx_events if left - 1e-10 <= x <= t + 1e-10]
        ok = bool(values) and values[0] - left <= 1.0 + 1e-10
        ok = ok and all(b - a <= 1.0 + 1e-10 for a, b in zip(values, values[1:]))
        states.append((t, ok))
    last_bad = max((i for i, (_, ok) in enumerate(states) if not ok), default=-1)
    suffix = states[last_bad + 1:]
    return suffix[0][0] if suffix else math.nan


def main() -> None:
    if sha(HERE / "prereg.md") != PREREG_HASH:
        raise SystemExit("A4.1c prereg hash mismatch; refusing analysis")
    source = (A4 / "a4.py").read_text(encoding="utf-8")
    frame_match = re.search(r"^FRAME_RATE\s*=\s*([0-9.]+)\s*$", source, re.M)
    frame_rate = float(frame_match.group(1)) if frame_match else math.nan
    g0 = frame_rate == 1.0

    ledger = [r for r in read_csv(A4 / "runs.csv") if r.get("stage") == "4.1"]
    if len(ledger) != 45 or any(r.get("status") != "success" for r in ledger):
        raise SystemExit(f"Expected 45 successful A4.1 runs; found {len(ledger)}")
    derived = read_csv(A4 / "derived_4.1_runs.csv")
    derived_by_dir = {r["output_dir"]: r for r in derived}
    prior_cluster = read_csv(A4 / "A4.1b" / "aodv_113s_cluster.csv")
    expected_cluster_ids = {
        r["run_id"] for r in prior_cluster
        if r.get("protocol") == "aodv" and 100 <= num(r.get("first_delivery_s")) <= 110
    }
    prior_warm = {(r["protocol"], int(r["N"])): r for r in read_csv(A4 / "A4.1b" / "warmup_gate.csv")}

    cache: dict[str, dict[str, object]] = {}
    membership_ids: set[str] = set()
    per_run: list[dict[str, object]] = []
    first5_rows: list[dict[str, object]] = []
    failure_records: list[dict[str, object]] = []
    late_aodv_records: list[dict[str, object]] = []
    for rec in ledger:
        run_id, protocol = rec["run_id"], rec["protocol"]
        out = A4 / rec["output_dir"]
        packet = out / f"packets_{protocol}.csv"
        pairs, txs, rx_events, unmatched = packet_data(packet)
        ready = readiness(rx_events)
        first = rx_events[0] if rx_events else math.nan
        gaps = [(b-a, a, b) for a, b in zip(rx_events, rx_events[1:])]
        max_gap, gap_start, gap_end = max(gaps, default=(math.nan, math.nan, math.nan))
        cluster = protocol == "aodv" and math.isfinite(first) and 100 <= first <= 110
        if cluster:
            membership_ids.add(run_id)
        is_active = protocol in PROTOCOLS
        g4_eligible = is_active and math.isfinite(max_gap) and max_gap <= 1.0
        offset = ready - first if math.isfinite(ready) and math.isfinite(first) else math.nan
        censored = not math.isfinite(ready) or ready > CENSOR
        derived_row = derived_by_dir[rec["output_dir"]]
        values = pairs[:5]
        if is_active:
            for k, p in enumerate(values, start=1):
                first5_rows.append({"run_id": run_id, "family": rec["family"], "N": rec["N"], "protocol": protocol,
                                    "rx_order": k, "matched_tx_s": fmt(p["tx"]), "rx_s": fmt(p["rx"]), "latency_s": fmt(p["latency"])})
        five_pass = len(values) == 5 and all(p["latency"] <= 100.0 for p in values)
        first5_text = ";".join(fmt(p["latency"]) for p in values)
        r = {"run_id": run_id, "family": rec["family"], "N": rec["N"], "protocol": protocol,
             "first_delivery_s": fmt(first), "first5_latency_s_semicolon": first5_text,
             "first5_count": len(values), "G5_first5_all_le_100s": str(five_pass).lower() if is_active else "not_tested",
             "recorded_readiness_s": derived_row.get("convergence_s", ""), "recomputed_readiness_s": fmt(ready),
             "offset_readiness_minus_first_s": fmt(offset), "max_gap_s": fmt(max_gap),
             "G4_eligible_gap_le_1s": str(g4_eligible).lower(), "censored_gt_180_or_nan": str(censored).lower(),
             "G8_AODV_first_delivery_100_110s": str(cluster).lower() if protocol == "aodv" else "not_applicable"}
        if is_active:
            per_run.append(r)
            if not five_pass:
                tx_head = txs[:10]
                rx_head = sorted(rx_events)[:10]
                tx_without_rx_early = [t for t in unmatched if t <= (rx_head[-1] if rx_head else math.inf)][:10]
                failure_records.append({"run_id": run_id, "first10_tx_s": ";".join(map(fmt, tx_head),),
                                        "first10_rx_s": ";".join(map(fmt, rx_head)),
                                        "unmatched_early_tx_s": ";".join(map(fmt, tx_without_rx_early))})
        cache[run_id] = {"record": rec, "pairs": pairs, "txs": txs, "rx": rx_events,
                         "unmatched_txs": unmatched,
                         "ready": ready, "first": first, "gaps": gaps, "max_gap": max_gap,
                         "gap_start": gap_start, "gap_end": gap_end, "censored": censored}
        if cluster:
            early_unmatched = [t for t in unmatched if t < first]
            late_aodv_records.append({"run_id": run_id, "family": rec["family"], "N": rec["N"],
                                      "first_delivery_s": fmt(first), "first10_scheduled_tx_s": ";".join(map(fmt, txs[:10])),
                                      "first10_rx_event_s": ";".join(map(fmt, rx_events[:10])),
                                      "unmatched_tx_before_first_delivery_n": len(early_unmatched),
                                      "first10_unmatched_tx_before_first_delivery_s": ";".join(map(fmt, early_unmatched[:10]))})

    eligible = [r for r in per_run if r["G4_eligible_gap_le_1s"] == "true"]
    offsets = [num(r["offset_readiness_minus_first_s"]) for r in eligible]
    in_band = [x for x in offsets if math.isfinite(x) and 9.0 <= x <= 10.0]
    g4_pass = bool(eligible) and len(in_band) / len(eligible) >= 0.8
    readiness_105 = sum(math.isfinite(num(r["recomputed_readiness_s"])) and num(r["recomputed_readiness_s"]) <= 10.5 for r in eligible)
    g5_bad = [r for r in per_run if r["G5_first5_all_le_100s"] != "true"]
    g5_pass = not g5_bad
    g8_pass = membership_ids == expected_cluster_ids
    g8_rows = []
    for rec in ledger:
        run_id = rec["run_id"]
        is_aodv = rec["protocol"] == "aodv"
        g8_rows.append({"run_id": run_id, "protocol": rec["protocol"],
                        "in_recomputed_AODV_first_delivery_100_110s": str(run_id in membership_ids).lower() if is_aodv else "not_applicable",
                        "in_A4_1b_first_delivery_membership": str(run_id in expected_cluster_ids).lower() if is_aodv else "not_applicable",
                        "membership_match": str((run_id in membership_ids) == (run_id in expected_cluster_ids)).lower() if is_aodv else "not_applicable"})
    write_csv(HERE / "per_run_aodv_olsr.csv", per_run)
    write_csv(HERE / "first5_latencies.csv", first5_rows)
    write_csv(HERE / "g5_failures.csv", failure_records or [{"status": "none"}])
    write_csv(HERE / "aodv_late_first_delivery.csv", late_aodv_records or [{"status": "none"}])
    write_csv(HERE / "g8_membership.csv", g8_rows or [{"status": "both sets empty"}])

    g4_summary: list[dict[str, object]] = []
    for protocol in ("aodv", "olsr"):
        for n in SIZES:
            xs = [num(r["offset_readiness_minus_first_s"]) for r in eligible if r["protocol"] == protocol and int(r["N"]) == n]
            finite = sorted(x for x in xs if math.isfinite(x))
            g4_summary.append({"protocol": protocol, "N": n, "eligible_n": len(finite),
                               "offset_min_s": fmt(finite[0]) if finite else "nan",
                               "offset_median_s": fmt(median(finite)),
                               "offset_max_s": fmt(finite[-1]) if finite else "nan",
                               "offsets_9_to_10_n": sum(9 <= x <= 10 for x in finite),
                               "readiness_le_10_5_n": sum(num(r["recomputed_readiness_s"]) <= 10.5 for r in eligible
                                   if r["protocol"] == protocol and int(r["N"]) == n)})
    write_csv(HERE / "g4_offset_distribution.csv", g4_summary)
    write_csv(HERE / "gate_results.csv", [
        {"gate": "G0", "pass": str(g0).lower(), "n_tested": 1, "n_fail": 0 if g0 else 1,
         "basis": f"a4.py source FRAME_RATE={frame_rate}; frame_duration_s={1/frame_rate if frame_rate else 'unknown'}"},
        {"gate": "G4", "pass": str(g4_pass).lower(), "n_tested": len(eligible), "n_fail": len(eligible)-len(in_band),
         "basis": f"offset in [9,10] s: {len(in_band)}/{len(eligible)}; readiness <=10.5 s: {readiness_105}"},
        {"gate": "G5", "pass": str(g5_pass).lower(), "n_tested": len(per_run), "n_fail": len(g5_bad),
         "basis": "all first five unique Rx latencies <=100 s and 5 available per run"},
        {"gate": "G8", "pass": str(g8_pass).lower(), "n_tested": 45, "n_fail": len(membership_ids ^ expected_cluster_ids),
         "basis": f"all 45 records scanned; AODV-only set over 15 AODV runs; exact A4.1b first-delivery [100,110] s match, {len(membership_ids)} IDs"},
    ])

    g7_rows: list[dict[str, object]] = []
    g7_events: list[dict[str, object]] = []
    for n in (92, 162):
        rec = next(r for r in ledger if r["family"] == "ba" and int(r["N"]) == n and r["protocol"] == "olsr")
        d = cache[rec["run_id"]]
        start, end = num(d["gap_start"]), num(d["gap_end"])
        duration = end - start if math.isfinite(start) and math.isfinite(end) else math.nan
        bounds = [("preceding_equal", start-duration, start), ("gap", start, end), ("following_equal", end, end+duration)]
        for label, lo, hi in bounds:
            lo2 = max(0.0, lo)
            window_txs = [t for t in d["txs"] if lo2 <= t < hi]
            tx_count = len(window_txs)
            rx_count = sum(lo2 <= p["rx"] < hi for p in d["pairs"])
            matched_tx = {p["tx"] for p in d["pairs"]}
            g7_rows.append({"run_id": rec["run_id"], "N": n, "window": label, "start_s": fmt(lo2), "end_s": fmt(hi),
                            "actual_duration_s": fmt(max(0, hi-lo2)), "scheduled_tx_n": tx_count,
                            "unique_rx_n": rx_count, "unmatched_tx_n": sum(t not in matched_tx for t in window_txs)})
        after_rx = [p for p in d["pairs"] if p["tx"] > end and p["rx"] > end] if math.isfinite(end) else []
        first_sec_rx = sum(end <= p["rx"] < end+1.0 for p in d["pairs"]) if math.isfinite(end) else 0
        g7_events.append({"run_id": rec["run_id"], "N": n, "max_gap_start_rx_s": fmt(start), "max_gap_end_rx_s": fmt(end),
                          "max_gap_s": fmt(duration), "probe_tx_received_after_gap": bool(after_rx),
                          "first_post_gap_tx_s": fmt(after_rx[0]["tx"]) if after_rx else "nan",
                          "first_post_gap_rx_s": fmt(after_rx[0]["rx"]) if after_rx else "nan",
                          "rx_in_first_second_after_gap_end": first_sec_rx})
    write_csv(HERE / "g7_olsr_windows.csv", g7_rows)
    write_csv(HERE / "g7_olsr_gap_events.csv", g7_events)

    # G9 for OLSR; AODV status is explicitly carried from the prior reconciliation only.
    warm_rows: list[dict[str, object]] = []
    for protocol in ("aodv", "olsr"):
        for n in SIZES:
            rows = [r for r in per_run if r["protocol"] == protocol and int(r["N"]) == n]
            censored_count = sum(r["censored_gt_180_or_nan"] == "true" for r in rows)
            if protocol == "olsr":
                verdict = "invalid_pending_detector" if not (g0 and g4_pass) else "not_derivable_censored" if censored_count else "valid"
                reason = "G0 or G4 failed" if not (g0 and g4_pass) else f"{censored_count} censored contributor(s)" if censored_count else "G0/G4 pass; no censored contributors"
            else:
                previous = prior_warm.get((protocol, n), {})
                verdict = previous.get("G3_warmup_status", "not_available_in_A4.1b")
                reason = "carried from A4.1b; not a new G9 verdict"
            warm_rows.append({"protocol": protocol, "N": n, "contributing_runs": len(rows), "censored_runs": censored_count,
                              "G9_or_carried_status": verdict,
                              "existing_A4_1_warmup_frames_not_recomputed": prior_warm.get((protocol, n), {}).get("registered_warmup_frames", ""),
                              "reason": reason})
    write_csv(HERE / "warmup_status.csv", warm_rows)

    classification = "indeterminate" if not (g0 and g5_pass) else "window-fill" if g4_pass else "convergence"
    aodv_offsets = [num(r["offset_readiness_minus_first_s"]) for r in eligible if r["protocol"] == "aodv"]
    olsr_offsets = [num(r["offset_readiness_minus_first_s"]) for r in eligible if r["protocol"] == "olsr"]
    report = [
        "# A4.1c — offline readiness validity and event audit", "",
        "**Written after A4.1c results.** Offline only: 0 variants, no ns-3, simulator, or reruns. A4.0*/A4.1/A4.1b artifacts remain read-only. Budget 70/300. Retained protocols: AODV/OLSR. DSDV is excluded only by user direction, not a routing finding; rationale remains `[user to state]`. Phase 6D's DSDV outage question is untested in Alpha.",
        "", f"Frozen preregistration SHA-256: `{PREREG_HASH}`. G0 source: [a4.py](../a4.py#L27). `FRAME_RATE={frame_rate}` frame/s means {1/frame_rate if frame_rate else 'unknown'} s/frame.",
        "", "## Gate outcomes", "",
        f"- **G0 {'PASS' if g0 else 'FAIL'}:** frame mapping is source-stated as {1/frame_rate if frame_rate else 'unknown'} s/frame.",
        f"- **G4 {'PASS' if g4_pass else 'FAIL'}:** {len(in_band)}/{len(eligible)} eligible AODV/OLSR runs have readiness-minus-first-delivery in [9,10] s ({len(in_band)/len(eligible)*100:.1f}%); threshold 80%. Eligible runs with absolute readiness ≤10.5 s: {readiness_105}/{len(eligible)}.",
        f"- **G5 {'PASS' if g5_pass else 'FAIL'}:** {len(g5_bad)} of 30 runs fail first-five latency ≤100 s / five receptions. Full rows: [first5_latencies.csv](first5_latencies.csv); failing run first-10 Tx/Rx and unmatched early Tx: [g5_failures.csv](g5_failures.csv).",
        f"- **G8 {'PASS' if g8_pass else 'FAIL'}:** all 45 A4.1 records scanned; membership is AODV-only across 15 AODV runs. Recomputed first-delivery 100–110-s set has {len(membership_ids)} runs; A4.1b set has {len(expected_cluster_ids)}; symmetric difference {len(membership_ids ^ expected_cluster_ids)}. See [g8_membership.csv](g8_membership.csv).",
        f"- **Detector classification:** **{classification}**, determined only by G0/G4/G5 under the preregistered rule. This is a validity classification, not a revised detector or convergence estimate.",
        "", "### G4 offset summaries (max gap ≤1 s)", "",
        "| Protocol | N | n | min offset (s) | median (s) | max (s) | in [9,10] n | readiness ≤10.5 s |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in g4_summary:
        report.append(f"| {row['protocol']} | {row['N']} | {row['eligible_n']} | {row['offset_min_s']} | {row['offset_median_s']} | {row['offset_max_s']} | {row['offsets_9_to_10_n']} | {row['readiness_le_10_5_n']} |")
    report += ["", "## AODV/OLSR per-run data", "",
               "First-five values are ordered by reception event; exact matched Tx/Rx timestamps and every latency are in [first5_latencies.csv](first5_latencies.csv). Cluster membership is the 100–110-s AODV first-delivery membership check.",
               "", "| Family | N | Protocol | First delivery (s) | First 5 latencies (s) | Readiness (s) | Offset (s) | Max gap (s) | G4 eligible | G8 member |",
               "|---|---:|---|---:|---|---:|---:|---:|---|---|"]
    for r in per_run:
        report.append(f"| {r['family']} | {r['N']} | {r['protocol']} | {r['first_delivery_s']} | {r['first5_latency_s_semicolon']} | {r['recomputed_readiness_s']} | {r['offset_readiness_minus_first_s']} | {r['max_gap_s']} | {r['G4_eligible_gap_le_1s']} | {r['G8_AODV_first_delivery_100_110s']} |")
    report += ["", "## G7 — BA/OLSR N=92 and N=162 event structure", "",
               "| N | Max-gap interval (s) | Gap (s) | Tx received after gap? | Rx in first 1 s after end |",
               "|---:|---|---:|---|---:|"]
    for r in g7_events:
        report.append(f"| {r['N']} | {r['max_gap_start_rx_s']}–{r['max_gap_end_rx_s']} | {r['max_gap_s']} | {r['probe_tx_received_after_gap']} | {r['rx_in_first_second_after_gap_end']} |")
    report += ["", "| N | Window | Scheduled Tx | Rx arrivals | Unmatched scheduled Tx |",
               "|---:|---|---:|---:|---:|"]
    for r in g7_rows:
        report.append(f"| {r['N']} | {r['window']} | {r['scheduled_tx_n']} | {r['unique_rx_n']} | {r['unmatched_tx_n']} |")
    report += ["", "First matched Tx/Rx after the gap: " + "; ".join(
                   f"N={r['N']} Tx {r['first_post_gap_tx_s']} s → Rx {r['first_post_gap_rx_s']} s" for r in g7_events) + ".",
               "These packet timestamps establish event ordering, not cause; counters are not time-resolved and no causal inference is claimed.",
               "", "### AODV late-first-delivery packet evidence — written after A4.1c results", "",
               "The five G8 members, including WS N=92 at 106.120712 s, have matched first-five latency values above. Their early unmatched Tx counts and first packet times are in [aodv_late_first_delivery.csv](aodv_late_first_delivery.csv). This localizes the symptom to absence of an early matched app Rx in these logs; it does not distinguish route discovery, forwarding, or another cause.",
               "", "## Warm-up status and proposal-only policy options", "",
               "No warm-up value is recomputed and no option is selected. AODV statuses are carried from A4.1b; OLSR uses G9. OLSR G9 validity does not inherit or automatically adopt any A4.1 warm-up value; policy remains an explicit decision.",
               "", "| Protocol | N | G9 / carried status | Reason |",
               "|---|---:|---|---|"]
    for r in warm_rows:
        suffix = f"; existing A4.1 value {r['existing_A4_1_warmup_frames_not_recomputed']} frames (not inherited)" if r["protocol"] == "olsr" and r["existing_A4_1_warmup_frames_not_recomputed"] not in ("", "not_derivable") else ""
        report.append(f"| {r['protocol']} | {r['N']} | {r['G9_or_carried_status']} | {r['reason']}{suffix} |")
    report += ["", "| Option (not selected) | Run-length implication | Variant cost / effect |",
               "|---|---|---|"]
    report += [
        "| (a) Keep A4.1 AODV warm-ups; OLSR unresolved | AODV totals at N=42/92/162 remain 291/293/139 s (171/173/19 warm-up +120 measured); OLSR run length unresolved | 0 added; reserve 4.2=90 and 4.3=48; OLSR N92/162 counts conditional on G4/G9 |",
        "| (b) Fixed OLSR warm-up chosen from noncensored observations | Each 4.2 run is W_N+120 s; existing N=42 32-frame value would imply 152 s only if separately selected; W_92/W_162 not selected | 0 added if replacing cells; 90+48 retained; transfer assumption requires separate registration |",
        "| (c) Per-run readiness-gated measured window | Each run is observed readiness W_i+120 s; variable and may exceed 240 s, so elapsed cost is unbounded here | 0 added variants; 90+48 retained; requires separate design authorization |",
        "| (d) Drop OLSR N=92/162 cells | Removes 15 4.2 load runs per N and 8 4.3 variants per N | Frees 30 of 90 4.2 and 16 of 48 4.3; remaining 4.2=60, 4.3=32; separate future decision |",
    ]
    report += ["", "## Budget and stop", "",
               "Retained-protocol design: 4.2 = AODV 45 + OLSR 45 = 90; 4.3 = AODV 24 + OLSR 24 = 48. With 70 spent, planned total is 208/300, leaving 92. The OLSR N=92/162 4.2=30 and 4.3=16 counts depend on unresolved G4/G9; under option (d) those counts are freed, while options (a)–(c) retain them and add 0 variants. No budget counts include DSDV.",
               "", "### Decisions (maximum five; none selected)", "",
               "1. State the rationale to replace `[user to state]` for the user-directed DSDV drop.",
               "2. Decide whether OLSR warm-up remains unresolved, uses a separately authorized fixed policy, or is handled with readiness-gated measurement.",
               "3. Decide whether OLSR N=92/162 cells should be retained or separately proposed for removal.",
               "4. Confirm whether this A4.1c validity classification is sufficient to close the detector question; no detector change is made here.",
               "", "**STOP.** No reruns, detector change, cell disposition beyond the stated DSDV user decision, A4.2, or A4.3 were performed or authorized."]
    (HERE / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    if len(report) > 150:
        raise SystemExit(f"Report exceeds 150 lines: {len(report)}")
    print(f"A4.1c complete: G0={g0}, G4={g4_pass} ({len(in_band)}/{len(eligible)}), G5={g5_pass} ({len(g5_bad)} failing), G8={g8_pass}; classification={classification}; report_lines={len(report)}")
    print("G7:", g7_events)


if __name__ == "__main__":
    main()
