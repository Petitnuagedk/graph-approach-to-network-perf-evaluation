#!/usr/bin/env python3
"""A4.2 serial, guarded execution and offline reduction. Never retries a run."""
from __future__ import annotations

import bisect
import csv
import gzip
import hashlib
import json
import math
import os
import re
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
A4 = HERE.parent
STUDY = A4.parents[1]
A1 = STUDY / "alpha" / "A1"
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
PYTHON = Path("/home/hledirach/Documents/J2/.venv/bin/python")
PREREG_HASH = "5ab4e85f5b335afabe89147e30e445bf409429c3bb8353876607719bfa5bae06"
RUN_TIMEOUT_S = 3600
FRAME_RATE = 1.0
WARMUP_FRAMES = 120
MEASUREMENT_FRAMES = 120
FIRST_TX = 120.1
INTERVAL = 1024 * 8 / 50_000
TOL = 2e-8
PROTOCOLS = ("aodv", "olsr")
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
SIZES = (42, 92, 162)
LOADS = (("phi1", 0.01), ("phi5", 0.05), ("phi10", 0.10))

sys.path.insert(0, str(A4))
import a4  # noqa: E402  # source helpers only; runner's stage entry point is not invoked


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def append_csv(path: Path, row: dict[str, object]) -> None:
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n", extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def num(value: object, default: float = math.nan) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def fmt(x: float) -> str:
    return "nan" if not math.isfinite(x) else f"{x:.9g}"


def boolstr(x: bool) -> str:
    return "true" if x else "false"


def load_graphs() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, str]]]:
    manifest = json.loads((A1 / "results" / "graph_manifest.json").read_text(encoding="utf-8"))
    covs = {r["graph_id"]: r for r in read_csv(A1 / "results" / "graph_covariates.csv")}
    graphs: dict[str, dict[str, object]] = {}
    for item in manifest:
        edge_path = A1 / item["edge_list"]
        if sha(edge_path) != item["edge_sha256"]:
            raise RuntimeError(f"A1 edge hash mismatch for {item['graph_id']}")
        c = covs[item["graph_id"]]
        graphs[item["graph_id"]] = {**item, "family": c["family"], "realization": int(c["realization"]),
            "probe_source": int(c["probe_S"]), "probe_destination": int(c["probe_R"]),
            "diameter": float(c["diameter"]), "edge_file": edge_path, "max_degree": int(c["max_degree"])}
    return graphs, covs


def write_frames(graph: dict[str, object]) -> tuple[Path, str]:
    p = HERE / "inputs" / f"{graph['graph_id']}__F120.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    edges, _ = a4.graph_edges(graph)
    n = int(graph["N"])
    with p.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(f"Node_{i}" for i in range(n)) + "\n")
        for frame in range(MEASUREMENT_FRAMES):
            for i in range(n):
                f.write(",".join("1" if (min(i, j), max(i, j)) in edges else "0" for j in range(n)) + "\n")
            if frame + 1 < MEASUREMENT_FRAMES:
                f.write("\n")
    return p, sha(p)


def plan_variants(graphs: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    p41 = {r["run_id"]: r for r in read_csv(A4 / "runs.csv") if r.get("stage") == "4.1"}
    classes = [graphs[f"{family}_N{n}_r1"] for n in SIZES for family in FAMILIES]
    costs = {}
    for graph in classes:
        values = [num(p41.get(f"41_{graph['graph_id']}_{p}_probe", {}).get("process_wall_s")) for p in PROTOCOLS]
        finite = [x for x in values if math.isfinite(x)]
        costs[str(graph["graph_id"])] = sum(finite) / len(finite) if finite else math.inf
    classes.sort(key=lambda g: (costs[str(g["graph_id"])], str(g["graph_id"])))
    items: list[tuple[dict[str, object], str, float, int]] = []
    for graph in classes[:5]:
        for role, phi in (LOADS[0],):
            count = a4.llround(phi * int(graph["N"])*(int(graph["N"])-1)/2)
            for protocol in PROTOCOLS:
                items.append((graph, protocol, phi, count))
    for index, graph in enumerate(classes):
        first_role = 1 if index < 5 else 0
        for role, phi in LOADS[first_role:]:
            count = a4.llround(phi * int(graph["N"])*(int(graph["N"])-1)/2)
            for protocol in PROTOCOLS:
                items.append((graph, protocol, phi, count))
    output = []
    for sequence, (g, protocol, phi, count) in enumerate(items, start=1):
        role = next(name for name, value in LOADS if value == phi)
        output.append({"sequence": sequence, "graph_id": g["graph_id"], "family": g["family"], "N": g["N"],
            "protocol": protocol, "load_role": role, "phi": fmt(phi), "n_background": count,
            "n_total": count + 1,
            "flow_seed": int(hashlib.sha256(f"A4|{g['graph_id']}|{phi:g}".encode()).hexdigest()[:8], 16),
            "routing_seed": 42, "warmup_frames": WARMUP_FRAMES, "measurement_frames": MEASUREMENT_FRAMES,
            "status": "planned", "run_id": f"42_{g['graph_id']}_{protocol}_{role}", "error": ""})
    if len(output) != 90:
        raise RuntimeError(f"Expected 90 planned variants, got {len(output)}")
    return output


def projection_tables(plan: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[float]]:
    p41 = {r["run_id"]: r for r in read_csv(A4 / "runs.csv") if r.get("stage") == "4.1"}
    p40 = {(r["protocol"], r["load_role"]): r for r in read_csv(A4 / "runs.csv") if r.get("stage") == "4.0A" and r.get("status") == "success"}
    p41_rows = []
    estimates = []
    for item in plan:
        rid = f"41_{item['graph_id']}_{item['protocol']}_probe"
        base = num(p41.get(rid, {}).get("process_wall_s"))
        low = num(p40.get((item["protocol"], "phi1"), {}).get("process_wall_s"))
        high = num(p40.get((item["protocol"], "phi10"), {}).get("process_wall_s"))
        n = int(item["N"])
        f1, f10 = a4.llround(.01*n*(n-1)/2), a4.llround(.10*n*(n-1)/2)
        count = int(item["n_background"])
        missing = []
        if not math.isfinite(base):
            missing.append("A4.1 baseline")
        if not math.isfinite(low):
            missing.append("successful A4.0A phi1 pilot")
        if not math.isfinite(high):
            missing.append("successful A4.0A phi10 pilot")
        if not all(math.isfinite(x) for x in (base, low, high)) or low <= 0:
            estimate = math.inf
            projection_status = "unavailable: " + "; ".join(missing)
        else:
            frac = (count-f1)/max(1, f10-f1)
            multiplier = max(1.0, 1.0 + frac * (high/low - 1.0))
            estimate = max(0.0, base) * multiplier # fixed 240 total frames: multiplier 240/240
            projection_status = "estimated"
        estimates.append(estimate)
        p41_rows.append({"sequence": item["sequence"], "run_id": item["run_id"], "baseline_4_1_process_wall_s": fmt(base),
            "pilot_phi1_s": fmt(low), "pilot_phi10_s": fmt(high), "load_multiplier": fmt(estimate/base) if math.isfinite(estimate) and base > 0 else "nan",
            "projected_wall_s": fmt(estimate), "projection_status": projection_status})
    return p41_rows, estimates


def guard() -> tuple[bool, int, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.replace(":", "").split()[:2]
        if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
            values[key] = int(value)
    available = values["MemAvailable"]
    swap = values["SwapTotal"] - values["SwapFree"]
    return available >= 8*1024*1024 and swap == 0, available, swap


def phase_map(nflows: int) -> tuple[list[float], list[int]]:
    phases = [((i/nflows) % INTERVAL) for i in range(nflows)]
    order = sorted(range(nflows), key=phases.__getitem__)
    return [phases[i] for i in order], order


def assign_flow(tx_time: float, phases: list[float], order: list[int]) -> tuple[int, int] | None:
    phase = (tx_time - FIRST_TX) % INTERVAL
    pos = bisect.bisect_left(phases, phase)
    candidates = {order[j % len(order)] for j in (pos-1, pos, pos+1)}
    matches = []
    for i in candidates:
        q = round((tx_time - (FIRST_TX + i/len(phases))) / INTERVAL)
        expected = FIRST_TX + i/len(phases) + q*INTERVAL
        if q >= 0 and abs(tx_time-expected) <= TOL:
            matches.append((i, q))
    return matches[0] if len(matches) == 1 else None


def calculate_readiness(rx: list[float], first_tx: float) -> float:
    delivered = sorted(set(round(t, 9) for t in rx))
    states: list[tuple[float, bool]] = []
    for t in delivered:
        if t + 1e-12 < first_tx + 10.0:
            continue
        left = t - 10.0
        vals = [x for x in delivered if left-1e-10 <= x <= t+1e-10]
        ready = bool(vals) and vals[0]-left <= 1.0+1e-10
        ready = ready and all(b-a <= 1.0+1e-10 for a,b in zip(vals, vals[1:]))
        states.append((t, ready))
    last_bad = max((i for i, (_, ok) in enumerate(states) if not ok), default=-1)
    suffix = states[last_bad+1:]
    return suffix[0][0] if suffix else math.nan


def packet_windows(out: Path, protocol: str, flow_rows: list[dict[str, str]]) -> tuple[float, float, list[dict[str, object]], str]:
    packet_path = out / f"packets_{protocol}.csv"
    nflows = len(flow_rows)
    if not packet_path.is_file() or not nflows:
        return math.nan, math.nan, [], "not_derivable_missing_packet_data"
    phases, order = phase_map(nflows)
    tx: dict[tuple[int, int], float] = {}
    rx: dict[tuple[int, int], float] = {}
    ambiguous = 0
    for event in a4.read_csv(packet_path):
        app_tx = num(event.get("app_tx_time_s"))
        if not math.isfinite(app_tx):
            continue
        assigned = assign_flow(app_tx, phases, order)
        if assigned is None:
            ambiguous += 1
            continue
        flow_i, seq = assigned
        key = (flow_i, seq)
        if event.get("event") == "tx":
            tx[key] = app_tx
        elif event.get("event") == "rx":
            event_time = num(event.get("event_time_s"))
            rx_seq = int(num(event.get("sequence"), -1))
            if math.isfinite(event_time) and rx_seq >= 0 and rx_seq == seq:
                rx_key = (flow_i, rx_seq)
                rx[rx_key] = min(event_time, rx.get(rx_key, math.inf))
    unknown_probe = next((i for i, r in enumerate(flow_rows) if r.get("is_probe") == "1"), None)
    if unknown_probe is None:
        return math.nan, math.nan, [], "not_derivable_no_probe_flow"
    probe_tx_keys = {k for k in tx if k[0] == unknown_probe}
    probe_rx = [rx[k] for k in probe_tx_keys if k in rx]
    readiness = calculate_readiness(probe_rx, FIRST_TX)
    if ambiguous:
        return readiness, math.nan, [], f"not_derivable_{ambiguous}_ambiguous_packet_events"
    stop_time = WARMUP_FRAMES + MEASUREMENT_FRAMES - 1
    ready_begin = max(FIRST_TX, readiness) if math.isfinite(readiness) else math.nan
    if not math.isfinite(ready_begin) or ready_begin >= stop_time:
        return readiness, math.nan, [], "no_nonempty_post_readiness_window"
    flow_metrics = []
    pdrs_probe: list[float] = []
    pdrs_bg: list[float] = []
    for i, flow in enumerate(flow_rows):
        full_keys = {k for k, t in tx.items() if k[0] == i and FIRST_TX <= t < stop_time}
        post_keys = {k for k in full_keys if tx[k] >= ready_begin}
        full_delivered = sum(k in rx for k in full_keys)
        post_delivered = sum(k in rx for k in post_keys)
        full_pdr = full_delivered/len(full_keys) if full_keys else math.nan
        post_pdr = post_delivered/len(post_keys) if post_keys else math.nan
        is_probe = flow.get("is_probe") == "1"
        flow_metrics.append({"flow_index": i, "flow_id": flow.get("flow_id", ""), "source": flow.get("source", ""),
            "destination": flow.get("destination", ""), "is_probe": flow.get("is_probe", ""),
            "full_tx_n": len(full_keys), "full_rx_n": full_delivered, "full_pdr_from_packet_log": fmt(full_pdr),
            "post_ready_tx_n": len(post_keys), "post_ready_rx_n": post_delivered, "post_ready_pdr": fmt(post_pdr),
            "readiness_s": fmt(readiness), "post_window_start_s": fmt(ready_begin), "post_window_stop_s": fmt(stop_time)})
        (pdrs_probe if is_probe else pdrs_bg).append(post_pdr)
    probe_post = pdrs_probe[0] if pdrs_probe else math.nan
    bg_post_median = a4.type7(pdrs_bg, .5)
    bg_post_p10 = a4.type7(pdrs_bg, .10)
    # Per-flow post-ready aggregates are appended to each flow row; run aggregate is returned via attributes.
    for row in flow_metrics:
        row["post_ready_probe_pdr_run"] = fmt(probe_post)
        row["post_ready_background_median_pdr_run"] = fmt(bg_post_median)
        row["post_ready_background_p10_pdr_run"] = fmt(bg_post_p10)
    status = "matched" if ambiguous == 0 else f"matched_with_{ambiguous}_unassigned_packet_events"
    return readiness, probe_post, flow_metrics, status


def invoke(item: dict[str, object], graph: dict[str, object], frame_path: Path, frame_hash: str) -> dict[str, object]:
    run_id = str(item["run_id"])
    out = HERE / "runs" / run_id
    if out.exists():
        raise RuntimeError(f"Refusing existing stage run output {run_id}")
    ok, available, swap = guard()
    if not ok:
        return {**item, "status": "resource_guard_blocked", "error": f"MemAvailable={available}; SwapUsed={swap}",
                "resource_guard_available_kb": available, "resource_guard_swap_used_kb": swap,
                "process_wall_s": "nan", "peak_rss_kb": "nan", "output_dir": ""}
    out.mkdir(parents=True)
    (out / "resource_guard.json").write_text(json.dumps({"mem_available_kb": available, "swap_used_kb": swap,
        "passed": True, "worker_count": 1}, indent=2)+"\n", encoding="utf-8")
    (out / "input.sha256").write_text(f"{frame_hash}  {frame_path.name}\n", encoding="utf-8")
    count = int(item["n_background"])
    n = int(item["N"])
    frac = count / (n*(n-1)/2)
    flow_arg = f"Node_{graph['probe_source']}:Node_{graph['probe_destination']}"
    argv = ["./ns3", "run", "scratch/graph-run "
        f"--framesCsv={frame_path} --outDir={out} --routing={item['protocol']} --flows={flow_arg} "
        "--dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=true "
        "--defaultLossDb=1000000 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 "
        f"--fps=1 --seed=42 --warmup={WARMUP_FRAMES} --warmupMode=first --instrumentation=true "
        f"--flowFraction={frac:.17g} --flowSeed={item['flow_seed']} --a3bForwardLog=false --dumpRoutes=true"]
    (out / "command.txt").write_text(shlex.join(["/usr/bin/time", "-v", "-o", str(out/"time.txt"), *argv])+"\n", encoding="utf-8")
    started = time.monotonic()
    process = None
    status, code, error = "failed", None, ""
    with (out/"ns3.log").open("w", encoding="utf-8") as log:
        try:
            process = subprocess.Popen(["/usr/bin/time", "-v", "-o", str(out/"time.txt"), *argv], cwd=NS3,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True, text=True)
            try:
                code = process.wait(timeout=RUN_TIMEOUT_S)
                status = "success" if code == 0 else "failed"
                if code != 0:
                    error = f"ns-3 returned {code}"
            except subprocess.TimeoutExpired:
                status, error = "timeout", f"exceeded {RUN_TIMEOUT_S}s; no retry"
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
        except OSError as exc:
            status, code, error = "failed", -1, f"{type(exc).__name__}: {exc}"
    process_wall = time.monotonic() - started
    ttext = (out/"time.txt").read_text(encoding="utf-8", errors="replace") if (out/"time.txt").exists() else ""
    rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", ttext)
    record = {**item, "status": status, "exit_code": code, "error": error, "process_wall_s": fmt(process_wall),
              "peak_rss_kb": int(rss.group(1)) if rss else "nan", "output_dir": str(out.relative_to(HERE)),
              "resource_guard_available_kb": available, "resource_guard_swap_used_kb": swap,
              "frame_sha256": frame_hash, "command": shlex.join(argv)}
    if status == "success":
        required = [out/"flows.csv", out/"node_diagnostics.csv", out/"trace_replay_results.csv",
                    out/f"packets_{item['protocol']}.csv", out/f"routes_{item['protocol']}.txt", out/f"times_{item['protocol']}.csv"]
        missing = [p.name for p in required if not p.is_file()]
        if missing:
            record["status"] = "malformed_output"
            record["error"] = f"missing A3-registered dumpRoutes/instrumentation output: {missing}"
        else:
            route = out/f"routes_{item['protocol']}.txt"
            with route.open("rb") as src, (out/(route.name+".gz")).open("wb") as dst:
                with gzip.GzipFile(fileobj=dst, mode="wb", mtime=0) as gz:
                    while block := src.read(1024*1024):
                        gz.write(block)
            route.unlink()
    return record


def write_projection_stop(plan: list[dict[str, object]], estimates: list[float], reason: str) -> None:
    for row in plan:
        row["status"] = "not_attempted_projection_gate"
        row["error"] = reason
    write_csv(HERE/"planned_cells.csv", plan)
    write_csv(HERE/"per_run.csv", [], ["run_id", "graph_id", "family", "N", "protocol", "load_role", "status",
        "error", "process_wall_s", "readiness_s", "readiness_after_warmup", "probe_pdr_full",
        "background_pdr_median_full", "pdr_gate_full_window"])
    write_csv(HERE/"per_flow_post_readiness.csv", [], ["run_id", "flow_index", "flow_id", "is_probe",
        "full_tx_n", "full_rx_n", "post_ready_tx_n", "post_ready_rx_n", "post_ready_pdr"])
    miss_rows = [{"protocol": protocol, "N": n, "load_role": role, "family_cells": 5,
        "flagged_n": "not_measured", "flagged_fraction": "not_measured",
        "readiness_gt_120_n": "not_measured", "readiness_gt_120_fraction": "not_measured",
        "readiness_undefined_n": "not_measured"}
        for protocol in PROTOCOLS for n in SIZES for role, _ in LOADS]
    write_csv(HERE/"miss_table.csv", miss_rows)
    status_rows = [{"family": family, "N": n, "protocol": protocol,
        "phi1_status": "not_attempted_projection_gate", "phi5_status": "not_attempted_projection_gate",
        "phi10_status": "not_attempted_projection_gate", "per_cell_highest_passing_phi": "not_measured"}
        for family in FAMILIES for n in SIZES for protocol in PROTOCOLS]
    write_csv(HERE/"status_matrix.csv", status_rows)
    write_csv(HERE/"operating_candidates.csv", [{"N": n, "lowest_load_passed_family_protocol_cells": "not_measured",
        "common_operating_role": "not_measured", "common_operating_phi": "not_measured"} for n in SIZES])
    finite = all(math.isfinite(x) for x in estimates)
    total = sum(estimates) if finite else None
    (HERE/"projection_initial.json").write_text(json.dumps({"planned_variants": 90,
        "projection_complete": finite, "projected_total_s": total,
        "projected_total_h": total/3600 if total is not None else None,
        "limit_h": 24, "pass": bool(finite and total <= 24*3600), "stop_reason": reason},
        indent=2, allow_nan=False)+"\n", encoding="utf-8")
    successful_pilots = [r for r in read_csv(A4/"runs.csv") if r.get("stage") == "4.0A" and r.get("status") == "success"]
    report = ["# A4.2 — fixed 120-s warm-up load sweep", "",
        "**Written after prelaunch audit; no A4.2 simulator variants were launched.** The frozen preregistration requires a complete runtime projection at or below 24 hours before the first run. The projection is not estimable from the registered baseline inputs, so the mandatory stop gate failed closed.",
        "", f"Preregistration SHA-256: `{PREREG_HASH}`. G0 PASS: source `FRAME_RATE=1.0`, so one frame is one second. The 90-cell grid was planned but 0/90 variants were attempted or charged; Alpha accounting remains 70/300.",
        "", f"Missing projection inputs: only {len(successful_pilots)} A4.0A pilot records have successful status. A4.0A successful pilots are: " +
        (", ".join(f"{r['protocol']} {r['load_role']} ({r['process_wall_s']} s)" for r in successful_pilots) or "none") +
        ". The registered 1%-to-10% per-protocol interpolation requires successful phi1 and phi10 pilot times for both AODV and OLSR. Those pairs are incomplete, making all 90 per-run projections unavailable; no substitute model or pilot was introduced.",
        "", "No resource-guard launch check was needed because the projection gate stopped the campaign before any simulator invocation. There were no timeouts, retries, readiness observations, or PDR measurements.",
        "", "## Planned status", "", "All 90 planned combinations are marked `not_attempted_projection_gate` in [planned_cells.csv](planned_cells.csv). The complete per-run table is intentionally empty: [per_run.csv](per_run.csv).", "",
        "| Protocol | N | Load | Family cells | Readiness misses |", "|---|---:|---:|---:|---:|"]
    report.extend(f"| {r['protocol']} | {r['N']} | {r['load_role']} | 5 | not measured |" for r in miss_rows)
    report += ["", "All status-matrix cells and operating candidates are unmeasured, not failures: [status_matrix.csv](status_matrix.csv), [operating_candidates.csv](operating_candidates.csv). No routing, readiness, or load verdict is drawn.",
        "", "## Decision and stop", "", "The missing A4.0A OLSR baselines and AODV phi10 baseline prevent demonstrating that the planned campaign is within the preregistered 24-hour ceiling. Stop before launch; this does not claim that actual runtime would exceed 24 hours. A revised projection method or new pilot requires a separately registered/user-authorized disposition before any A4.2 run.",
        "", "DSDV remains excluded by user direction, not a measured routing verdict; rationale placeholder: `[user to state]`. No A4.3, detector/warm-up change, 2% run, or DSDV reinstatement."]
    (HERE/"report.md").write_text("\n".join(report)+"\n", encoding="utf-8")
    if len(report) > 150:
        raise RuntimeError(f"Report exceeds 150 lines ({len(report)})")
    gates = A4.parent/"gates.md"
    gates_text = gates.read_text(encoding="utf-8")
    if "### A4.2 fixed-window load sweep" in gates_text:
        raise RuntimeError("A4.2 gate entry already exists; refusing duplicate append")
    entry = ("\n\n### A4.2 fixed-window load sweep — projection gate stop\n\n"
        f"**A4.2 authorized; stopped before launch under the frozen 24-hour projection gate.** [Report](A4/A4.2/report.md); preregistration SHA-256 `{PREREG_HASH}`. G0 PASS (`FRAME_RATE=1.0`). Planned 90 AODV/OLSR cells; 0/90 attempted or charged, cumulative Alpha remains 70/300. The preregistered A4.0A per-protocol phi1-to-phi10 projection cannot be calculated: successful pilot coverage lacks AODV phi10 and both OLSR pilot levels. No substitute or new pilot was used. Readiness misses/PDR outcomes are unmeasured, not zero or failures. DSDV excluded by user direction (not a measured verdict); rationale: `[user to state]`. **STOP: no A4.3, detector/warm-up change, 2% run, or DSDV reinstatement.**\n")
    with gates.open("a", encoding="utf-8") as f:
        f.write(entry)
    create_manifest()


def create_manifest() -> None:
    manifest = HERE/"MANIFEST.sha256"
    paths: list[tuple[Path, str]] = []
    for path in sorted(HERE.rglob("*")):
        if path.is_file() and path != manifest:
            paths.append((path, str(path.relative_to(HERE))))
    sources = [A4/"a4.py", A4/"runs.csv", A4/"A4_0d"/"runs.csv",
        A1/"results"/"graph_manifest.json", A1/"results"/"graph_covariates.csv",
        NS3/"scratch"/"graph-run.cc", NS3/"VERSION", NS3/"build"/"scratch"/"ns3.46.1-graph-run-default"]
    graphs, _ = load_graphs()
    sources.extend(Path(graphs[f"{family}_N{n}_r1"]["edge_file"])
                   for family in FAMILIES for n in SIZES)
    sources.append(A4.parent/"gates.md")
    for path in sources:
        if path.is_file():
            paths.append((path, os.path.relpath(path, HERE)))
    manifest.write_text("".join(f"{sha(path)}  {label}\n" for path, label in paths), encoding="utf-8")


def run_and_analyze() -> None:
    prereg = HERE/"prereg.md"
    if sha(prereg) != PREREG_HASH:
        raise SystemExit("A4.2 preregistration hash mismatch; refusing launch")
    source_path = A4/"a4.py"
    if "FRAME_RATE = 1.0" not in source_path.read_text(encoding="utf-8"):
        raise SystemExit("G0 source definition changed; refuse launch")
    if (HERE/"per_run.csv").exists() or (HERE/"planned_cells.csv").exists():
        raise SystemExit("A4.2 run metadata exists; refusing any rerun")
    # Enforce the stated budget using authoritative existing A4 and 4.0d attempt ledgers.
    old_a4 = read_csv(A4/"runs.csv")
    old_4d = read_csv(A4/"A4_0d"/"runs.csv")
    already_spent = 12 + len(old_a4) + len(old_4d)
    if already_spent != 70 or already_spent+90 > 300:
        raise SystemExit(f"Expected 70 spent and room for 90; found {already_spent}/300")
    graphs, _ = load_graphs()
    plan = plan_variants(graphs)
    write_csv(HERE/"planned_cells.csv", plan)
    initial_rows, estimates = projection_tables(plan)
    projection = sum(estimates)
    write_csv(HERE/"runtime_projection_initial.csv", initial_rows)
    if not math.isfinite(projection):
        reason = "incomplete projection: successful A4.0A phi1 and phi10 pilot baselines are unavailable for both retained protocols"
        write_projection_stop(plan, estimates, reason)
        raise SystemExit(reason)
    (HERE/"projection_initial.json").write_text(json.dumps({"planned_variants": 90, "projection_complete": True,
        "projected_total_s": projection, "projected_total_h": projection/3600, "limit_h": 24,
        "pass": projection <= 24*3600}, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(f"G0 PASS: FRAME_RATE=1.0 frame/s; initial 90-run projection={projection/3600:.3f} h", flush=True)
    if projection > 24*3600:
        reason = f"projected total {projection/3600:.3f} h exceeds frozen 24-hour gate"
        write_projection_stop(plan, estimates, reason)
        raise SystemExit(reason)
    frame_hashes: dict[str, tuple[Path, str]] = {}
    for item in plan:
        gid = str(item["graph_id"])
        if gid not in frame_hashes:
            frame_hashes[gid] = write_frames(graphs[gid])
    per_runs: list[dict[str, object]] = []
    per_flow_rows: list[dict[str, object]] = []
    run_records: dict[str, dict[str, object]] = {}
    elapsed_wall = 0.0
    actual_to_projected: list[float] = []
    for index, item in enumerate(plan):
        graph = graphs[str(item["graph_id"])]
        frame_path, frame_hash = frame_hashes[str(item["graph_id"])]
        record = invoke(item, graph, frame_path, frame_hash)
        run_records[str(item["run_id"])] = record
        if record["status"] == "resource_guard_blocked":
            item["status"], item["error"] = record["status"], record["error"]
            for rest in plan[index+1:]:
                rest["status"], rest["error"] = "not_attempted_guard_stop", "resource guard prevented launch; no retry"
            write_csv(HERE/"planned_cells.csv", plan)
            write_csv(HERE/"per_run.csv", per_runs + [record])
            raise SystemExit("Resource guard failed; remaining planned runs not launched")
        if record["status"] in ("success", "failed", "timeout", "malformed_output"):
            item["status"], item["error"] = record["status"], record.get("error", "")
        else:
            item["status"], item["error"] = record["status"], record.get("error", "")
        elapsed_wall += num(record.get("process_wall_s"), 0.0)
        if record["status"] == "success":
            out = HERE/str(record["output_dir"])
            flow_rows = [r for r in read_csv(out/"flows.csv") if r.get("protocol") == item["protocol"]]
            metrics = a4.summarize_run(out, graph, str(item["protocol"]),
                                       (WARMUP_FRAMES+MEASUREMENT_FRAMES-1)/FRAME_RATE,
                                       WARMUP_FRAMES)
            ready, post_probe_pdr, per_flow, timing_status = packet_windows(out, str(item["protocol"]), flow_rows)
            for row in per_flow:
                row.update({"run_id": item["run_id"], "family": item["family"], "N": item["N"],
                            "protocol": item["protocol"], "load_role": item["load_role"], "phi": item["phi"]})
            per_flow_rows.extend(per_flow)
            miss = not math.isfinite(ready) or ready > WARMUP_FRAMES
            probe_pdr = num(metrics.get("probe_pdr"))
            bg_med = num(metrics.get("background_pdr_median"))
            bg_p10 = num(metrics.get("background_pdr_p10"))
            passed = math.isfinite(probe_pdr) and math.isfinite(bg_med) and probe_pdr >= .99 and bg_med >= .95
            # MAC/PHY measurements are whole-run, including warm-up (PHY counters are not timestamped).
            run_row = {**record, "readiness_s": fmt(ready), "readiness_after_warmup": boolstr(miss),
                "post_readiness_status": timing_status,
                "measurement_stop_s": WARMUP_FRAMES+MEASUREMENT_FRAMES-1,
                "probe_pdr_full": fmt(probe_pdr), "background_pdr_median_full": fmt(bg_med),
                "background_pdr_p10_full": fmt(bg_p10), "probe_pdr_post_readiness": fmt(post_probe_pdr),
                "background_pdr_median_post_readiness": per_flow[0].get("post_ready_background_median_pdr_run", "nan") if per_flow else "nan",
                "background_pdr_p10_post_readiness": per_flow[0].get("post_ready_background_p10_pdr_run", "nan") if per_flow else "nan",
                "pdr_gate_full_window": "pass" if passed else "fail",
                "probe_delay_median_s": fmt(num(metrics.get("probe_delay_median_s"))),
                "probe_delay_p95_s": fmt(num(metrics.get("probe_delay_p95_s"))),
                "background_delay_median_s": fmt(num(metrics.get("background_delay_median_s"))),
                "background_delay_p95_s": fmt(num(metrics.get("background_delay_p95_s"))),
                "control_packets_mean": fmt(num(metrics.get("control_packets_mean"))),
                "control_packets_max": fmt(num(metrics.get("control_packets_max"))),
                "control_packets_gini": fmt(num(metrics.get("control_packets_gini"))),
                "control_bytes_mean": fmt(num(metrics.get("control_bytes_mean"))),
                "control_bytes_max": fmt(num(metrics.get("control_bytes_max"))),
                "control_bytes_gini": fmt(num(metrics.get("control_bytes_gini"))),
                "forwarded_load_gini": fmt(num(metrics.get("forwarded_load_gini"))),
                "mac_retry_max_node_count": fmt(num(metrics.get("retry_callbacks_max"))),
                "max_degree_node": metrics.get("max_degree_node", ""),
                "max_degree_node_retry_ratio": fmt(num(metrics.get("retry_ratio_max_degree"))),
                "phy_collision_max_node_rate_per_s": fmt(num(metrics.get("collision_drops_per_s_max"))),
                "phy_collision_max_node_count": "",
                "borderline": boolstr((math.isfinite(probe_pdr) and abs(probe_pdr-.99)<=.02) or
                                       (math.isfinite(bg_med) and abs(bg_med-.95)<=.02)),
                "full_window_failure_cause_initial": "pass" if passed else "cause_pending_same_load_unflagged_comparison"}
            node_metrics = a4.load_node_metrics(out/"node_diagnostics.csv", str(item["protocol"]))
            coll = {node: sum(v for (m, _, reason), v in d.items() if m == "phy_rx_drop_class" and reason == "collision_interference")
                    for node, d in node_metrics.items()}
            run_row["phy_collision_max_node_count"] = max(coll.values(), default=0)
            run_row["mac_retry_max_node_id"] = max((node for node, d in node_metrics.items()
                if sum(v for (m, _, _), v in d.items() if m == "mac_data_failed_events") == num(metrics.get("retry_callbacks_max"))), default="")
            run_row["post_readiness_background_pdr_all_flows_count"] = sum(r.get("is_probe") != "1" for r in per_flow)
            run_row["packet_time_assignment_status"] = timing_status
            # The existing helper readiness is deliberately replaced by the preregistered warmup-aware A4.1 detector output above.
            per_runs.append(run_row)
            # Store projected runtime and progress after every invocation for auditability.
            pred = estimates[index]
            if math.isfinite(pred) and pred > 0 and math.isfinite(num(record.get("process_wall_s"))):
                actual_to_projected.append(num(record["process_wall_s"])/pred)
        else:
            per_runs.append({**record, "readiness_s": "nan", "readiness_after_warmup": "true",
                "post_readiness_status": "not_derivable_failed_run", "probe_pdr_full": "nan",
                "background_pdr_median_full": "nan", "background_pdr_p10_full": "nan",
                "probe_pdr_post_readiness": "nan", "background_pdr_median_post_readiness": "nan",
                "background_pdr_p10_post_readiness": "nan", "pdr_gate_full_window": "not_evaluable",
                "full_window_failure_cause_initial": "run_not_successful"})
        write_csv(HERE/"per_run.csv", per_runs)
        write_csv(HERE/"per_flow_post_readiness.csv", per_flow_rows or [{"status": "no successful runs yet"}])
        write_csv(HERE/"planned_cells.csv", plan)
        if len(per_runs) in (15, 60):
            correction = a4.type7(actual_to_projected, .5) if actual_to_projected else 1.0
            remaining = sum(estimates[index+1:]) * correction
            projected_total = elapsed_wall + remaining
            checkpoint = {"completed": len(per_runs), "actual_elapsed_wall_s": elapsed_wall,
                "median_actual_projected_correction": correction, "projected_total_s": projected_total,
                "projected_total_h": projected_total/3600, "limit_h": 24, "pass": projected_total <= 24*3600}
            write_csv(HERE/f"runtime_projection_after_{len(per_runs)}.csv", [{"sequence": len(per_runs), **checkpoint}])
            if projected_total > 24*3600:
                raise SystemExit(f"Updated total projection exceeds 24h after {len(per_runs)} attempts")
        print(f"[{len(per_runs):02d}/90] {item['run_id']} {record['status']} wall={record.get('process_wall_s')} s", flush=True)
    analyze_results(per_runs)


def analyze_results(rows: list[dict[str, object]]) -> None:
    # Flagged PDR shortfalls use the frozen same-protocol x N x phi unflagged comparator.
    groups: dict[tuple[str, int, str], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault((str(row.get("protocol")), int(row.get("N")), str(row.get("load_role"))), []).append(row)
    for group in groups.values():
        unflagged_fail = [r for r in group if r.get("readiness_after_warmup") == "false" and r.get("pdr_gate_full_window") == "fail"]
        for row in group:
            if row.get("pdr_gate_full_window") != "fail":
                row["failure_cause_classification"] = "pass" if row.get("pdr_gate_full_window") == "pass" else "not_evaluable"
            elif row.get("readiness_after_warmup") == "true" and not unflagged_fail:
                row["failure_cause_classification"] = "convergence-affected"
            elif row.get("readiness_after_warmup") == "true":
                row["failure_cause_classification"] = "shared-load-shortfall; unflagged comparator exists"
            else:
                row["failure_cause_classification"] = classify_unflagged(row)
    write_csv(HERE/"per_run.csv", rows)
    miss_rows = []
    for protocol in PROTOCOLS:
        for n in SIZES:
            for role, _ in LOADS:
                group = [r for r in rows if r.get("protocol") == protocol and int(r.get("N")) == n
                         and r.get("load_role") == role]
                flag_n = sum(r.get("readiness_after_warmup") == "true" for r in group)
                gt120 = sum(math.isfinite(num(r.get("readiness_s"))) and num(r.get("readiness_s")) > 120 for r in group)
                undefined = sum(not math.isfinite(num(r.get("readiness_s"))) for r in group)
                miss_rows.append({"protocol": protocol, "N": n, "load_role": role, "family_cells": len(group),
                    "flagged_n": flag_n, "flagged_fraction": fmt(flag_n/len(group) if group else math.nan),
                    "readiness_gt_120_n": gt120, "readiness_gt_120_fraction": fmt(gt120/len(group) if group else math.nan),
                    "readiness_undefined_n": undefined})
    write_csv(HERE/"miss_table.csv", miss_rows)
    status_rows = []
    for family in FAMILIES:
        for n in SIZES:
            for protocol in PROTOCOLS:
                group = sorted([r for r in rows if r.get("family")==family and int(r.get("N"))==n and r.get("protocol")==protocol],
                               key=lambda r: float(r.get("phi", 0)))
                by_role = {r["load_role"]: r for r in group}
                cell = {"family": family, "N": n, "protocol": protocol}
                passing = []
                for role, _ in LOADS:
                    r = by_role.get(role, {})
                    flag = r.get("readiness_after_warmup", "not_run")
                    pass_gate = r.get("pdr_gate_full_window") == "pass"
                    label = ("flagged-transient-pass" if flag == "true" and pass_gate else
                             "flagged-transient-fail" if flag == "true" and r.get("pdr_gate_full_window")=="fail" else
                             "pass" if pass_gate else r.get("failure_cause_classification", r.get("status", "not_run")))
                    cell[role+"_status"] = label
                    if pass_gate:
                        passing.append(float(r["phi"]))
                cell["per_cell_highest_passing_phi"] = fmt(max(passing)) if passing else "none"
                status_rows.append(cell)
    # Common per-size role: every protocol/family passing at 1% must pass at selected phi.
    common_rows = []
    for n in SIZES:
        low_pass = {(r["family"], r["protocol"]) for r in rows if int(r["N"])==n and r["load_role"]=="phi1" and r.get("pdr_gate_full_window")=="pass"}
        selected = None
        for role, phi in reversed(LOADS):
            if low_pass and all(any(r["family"]==fam and r["protocol"]==p and int(r["N"])==n and r["load_role"]==role and r.get("pdr_gate_full_window")=="pass" for r in rows) for fam,p in low_pass):
                selected = (role, phi)
                break
        common_rows.append({"N": n, "lowest_load_passed_family_protocol_cells": len(low_pass),
            "common_operating_role": selected[0] if selected else "none",
            "common_operating_phi": fmt(selected[1]) if selected else "none"})
    write_csv(HERE/"status_matrix.csv", status_rows)
    write_csv(HERE/"operating_candidates.csv", common_rows)
    make_report(rows, miss_rows, common_rows)


def classify_unflagged(row: dict[str, object]) -> str:
    # Fixed campaign rules use max-degree-node retry ratio and max collision rate relative to phi1.
    if num(row.get("no_route_or_route_error_drops"), 0) > 0:
        return "no-route/route-error evidence"
    if num(row.get("queue_drop_callbacks"), 0) > 0:
        return "queue-drop evidence"
    ratio = num(row.get("max_degree_node_retry_ratio"))
    collision = num(row.get("phy_collision_max_node_rate_per_s"))
    return "MAC/collision threshold not supported by cell-local diagnostic" if ratio <= .20 and collision < 1 else "MAC/collision evidence; baseline comparison required"


def make_report(rows: list[dict[str, object]], misses: list[dict[str, object]], common: list[dict[str, object]]) -> None:
    attempted = sum(r.get("status") in ("success", "failed", "timeout", "malformed_output") for r in rows)
    failed = sum(r.get("status") != "success" for r in rows)
    miss_total = sum(int(r["flagged_n"]) for r in misses)
    lines = ["# A4.2 — fixed 120-s warm-up load sweep", "",
        "**Written after A4.2 results.** 90 planned AODV/OLSR variants; no DSDV. DSDV removal is user-directed (not a measured verdict); rationale: `[user to state]`. Phase 6D DSDV outage question not tested. No A4.0*/A4.1/A4.1b/A4.1c artifacts edited.",
        "", f"Prereg SHA-256 `{PREREG_HASH}`; source [A4 runner](../a4.py#L27) defines 1 frame=1 s. G0 PASS. Fixed 120 warm-up frames +120 measurement frames; 240 frames total, simulation stop at t=239 s per A3 source last-frame stop convention.",
        "", f"**Gate/attempt summary:** G0 PASS; attempted {attempted}/90, {failed} unsuccessful/malformed/timeout. Budget 70+{attempted}={70+attempted}/300. Readiness misses: {miss_total}/90 flags; misses never gated a launch. All 90 grid cells and detailed per-run metrics: [per_run.csv](per_run.csv). Window-only per-flow denominator/counters: [per_flow_post_readiness.csv](per_flow_post_readiness.csv).",
        "", "## Per-run results", "",
        "The complete 90-row per-run dataset contains full-window and post-readiness PDR, delay, control/load distribution, retry/collision diagnostics, wall/CPU time and attribution: [per_run.csv](per_run.csv). Scheduled-packet denominators and per-flow post-readiness counters are in [per_flow_post_readiness.csv](per_flow_post_readiness.csv). MAC/PHY counts are whole-run, including warm-up.",
        "", "## Misses", "", "The denominator is the five family cells per protocol×N×load; undefined readiness is separate.",
        "", "| Protocol | N | Load | Flagged / 5 | >120 s / 5 | Undefined |", "|---|---:|---|---:|---:|---:|"]
    for r in misses:
        lines.append(f"| {r['protocol']} | {r['N']} | {r['load_role']} | {r['flagged_n']}/5 | {r['readiness_gt_120_n']}/5 | {r['readiness_undefined_n']} |")
    lines += ["", "All 30 family×size×protocol statuses, including `pass`, `fail` with cause or `flagged-transient`, and per-cell highest tested passing load: [status_matrix.csv](status_matrix.csv). No untested 2% is inferred.",
        "", "## Operating candidates", "", "The per-size common candidate is the highest tested load passed by every family×protocol cell passing at 1%; `none` means no common tested level.",
        "", "| N | Lowest-load passing family×protocol cells | Common candidate |", "|---:|---:|---|"]
    for r in common:
        lines.append(f"| {r['N']} | {r['lowest_load_passed_family_protocol_cells']} | {r['common_operating_role']} ({r['common_operating_phi']}) |")
    lines += ["", "## Interpretation and stop", "",
        "A flagged run’s PDR shortfall is classified convergence-affected unless an unflagged shortfall exists at the same protocol×N×phi; otherwise load effects are labeled transient-affected, not routing/MAC. Unflagged MAC attribution requires the registered ratio/rate thresholds versus the same max-degree node’s phi=1% baseline. Collision counters have no event timestamps; reported as whole-run. No ranking or ceiling inference.",
        "", "Proposal only: A4.3 would need matched readiness and per-flow PDR windows (including after-readiness denominators), unflagged same-load comparators, and fixed-window PDR in independent graph realizations. Miss-affected cells are not clean load-effect estimates. No A4.3 run here.",
        "", f"**STOP.** No detector/warm-up change, 2% run, DSDV reinstatement, A4.3, or further cell disposition. See [Alpha limitations](../../LIMITATIONS.md)."]
    (HERE/"report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    if len(lines) > 150:
        raise RuntimeError(f"Report exceeds 150 lines ({len(lines)})")


def main() -> None:
    run_and_analyze()


if __name__ == "__main__":
    main()
