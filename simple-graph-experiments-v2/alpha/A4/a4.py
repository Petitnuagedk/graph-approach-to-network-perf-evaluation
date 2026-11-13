#!/usr/bin/env python3
"""Reproducible A4 runner and frozen-rule derivation; no simulator source edits."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import re
import signal
import shlex
import subprocess
import sys
import time
from pathlib import Path

A4 = Path(__file__).resolve().parent
STUDY = A4.parents[1]
A1 = STUDY / "alpha" / "A1"
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
NS3_BIN = NS3 / "ns3"
PROTOCOLS = ("olsr", "aodv", "dsdv")
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
SIZES = (42, 92, 162)
FRAME_RATE = 1.0
RATE_BPS = 50_000
PACKET_BYTES = 1024
RUN_TIMEOUT_S = 3600
LOADS = (("phi1", 0.01), ("phi5", 0.05), ("phi10", 0.10))
PAIR_SEED = 24681357
RUN_FIELDS = [
    "stage", "run_id", "graph_id", "family", "N", "realization", "protocol",
    "load_role", "phi", "kappa", "n_background", "n_total", "flows_per_node",
    "flow_endpoints_per_node_mean",
    "offered_load_kbps_per_node", "probe_source", "probe_destination", "flow_seed",
    "routing_seed", "input_frames", "warmup_frames", "warmup_s", "output_dir",
    "status", "exit_code", "process_wall_s", "sim_wall_s", "cpu_s", "peak_rss_kb",
    "first_delivery_s", "convergence_s", "probe_pdr", "background_pdr_median",
    "background_pdr_p10", "probe_delay_median_s", "probe_delay_p95_s",
    "background_delay_median_s", "background_delay_p95_s", "all_up_gap_s",
    "max_degree_node", "max_degree", "retry_callbacks_max", "retry_ratio_max_degree",
    "collision_drops_per_s_max", "control_packets_mean", "control_packets_max",
    "control_packets_gini", "control_bytes_mean", "control_bytes_max", "control_bytes_gini",
    "forwarded_load_gini", "borderline", "error"
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, fields: list[str], row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        if new_file:
            writer.writeheader()
        writer.writerow(row)


def number(value: object, default: float = math.nan) -> float:
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def fstr(value: float) -> str:
    return "nan" if not math.isfinite(value) else f"{value:.9g}"


def type7(values: list[float], probability: float) -> float:
    values = sorted(v for v in values if math.isfinite(v))
    if not values:
        return math.nan
    position = probability * (len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def gini(values: list[float]) -> float:
    n = len(values)
    total = sum(values)
    if not n or total == 0:
        return 0.0
    return sum(abs(a - b) for a in values for b in values) / (2 * n * total)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def llround(value: float) -> int:
    if value < 0:
        return -math.floor(-value + 0.5)
    return math.floor(value + 0.5)


def load_a1() -> tuple[dict[str, dict[str, object]], dict[str, dict[str, str]]]:
    manifest = json.loads((A1 / "results" / "graph_manifest.json").read_text(encoding="utf-8"))
    covariates = {row["graph_id"]: row for row in read_csv(A1 / "results" / "graph_covariates.csv")}
    graphs: dict[str, dict[str, object]] = {}
    for item in manifest:
        edge_file = A1 / item["edge_list"]
        if sha256(edge_file) != item["edge_sha256"]:
            raise RuntimeError(f"A1 edge-list hash mismatch: {item['graph_id']}")
        cov = covariates[item["graph_id"]]
        graphs[item["graph_id"]] = {
            **item,
            "family": cov["family"],
            "realization": int(cov["realization"]),
            "probe_source": int(cov["probe_S"]),
            "probe_destination": int(cov["probe_R"]),
            "probe_hops": int(cov["probe_hops"]),
            "diameter": float(cov["diameter"]),
            "edge_file": edge_file,
            "max_degree": int(cov["max_degree"]),
        }
    return graphs, covariates


def graph_edges(graph: dict[str, object]) -> tuple[set[tuple[int, int]], list[int]]:
    edges: set[tuple[int, int]] = set()
    edge_file = Path(graph["edge_file"])
    with edge_file.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            a, b = int(row["u"]), int(row["v"])
            edges.add((min(a, b), max(a, b)))
    n = int(graph["N"])
    degrees = [0] * n
    for a, b in edges:
        degrees[a] += 1
        degrees[b] += 1
    return edges, degrees


def allup_matrix(graph: dict[str, object], frame_count: int) -> tuple[Path, str]:
    path = A4 / "inputs" / f"{graph['graph_id']}__F{frame_count}.csv"
    if path.exists():
        return path, sha256(path)
    n = int(graph["N"])
    edges, _ = graph_edges(graph)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as stream:
        stream.write(",".join(f"Node_{i}" for i in range(n)) + "\n")
        for frame in range(frame_count):
            for i in range(n):
                stream.write(",".join("1" if (min(i, j), max(i, j)) in edges else "0" for j in range(n)) + "\n")
            if frame + 1 != frame_count:
                stream.write("\n")
    tmp.replace(path)
    return path, sha256(path)


def ip_node(address: str) -> int:
    return int(address.rsplit(".", 1)[1]) - 1


def load_node_metrics(path: Path, protocol: str) -> dict[int, dict[tuple[str, str, str], int]]:
    result: dict[int, dict[tuple[str, str, str], int]] = {}
    for row in read_csv(path):
        if row.get("protocol") != protocol:
            continue
        node = int(row["node_id"])
        key = (row["metric"], row.get("message_type", ""), row.get("phy_reason", ""))
        result.setdefault(node, {})[key] = int(row["value"])
    return result


def gap_from_packets(path: Path, warmup_frames: int) -> float:
    interval = PACKET_BYTES * 8 / RATE_BPS
    probe_start = warmup_frames / FRAME_RATE + .1
    unique_rx: dict[tuple[int, float], float] = {}
    for row in read_csv(path):
        if row.get("event") != "rx":
            continue
        seq = int(number(row.get("sequence"), -1))
        app_tx = number(row.get("app_tx_time_s"))
        event_time = number(row.get("event_time_s"))
        if seq < 0 or not math.isfinite(app_tx) or not math.isfinite(event_time):
            continue
        expected = probe_start + seq * interval
        if abs(app_tx - expected) <= 2e-8:
            key = (seq, round(app_tx, 9))
            unique_rx[key] = min(event_time, unique_rx.get(key, math.inf))
    times = sorted(unique_rx.values())
    if len(times) < 2:
        return math.nan
    return max(b - a for a, b in zip(times, times[1:]))


def readiness_from_probe_packets(path: Path, flow_count: int = 1, first_tx_s: float = 0.1) -> float:
    """Apply the provisionally adopted A4.0d G=1 s, trailing-10 s detector."""
    interval = PACKET_BYTES * 8 / RATE_BPS
    tx_times: set[float] = set()
    rx_times: dict[float, float] = {}
    for row in read_csv(path):
        try:
            sequence = int(row.get("sequence", "-1"))
            app_tx = number(row.get("app_tx_time_s"))
            event_time = number(row.get("event_time_s"))
        except (TypeError, ValueError):
            continue
        if sequence < 0 or not math.isfinite(app_tx):
            continue
        matches = []
        for flow_index in range(flow_count):
            start = first_tx_s + flow_index / flow_count
            packet_index = round((app_tx - start) / interval)
            if packet_index >= 0 and abs(app_tx - (start + packet_index * interval)) <= 2e-8:
                matches.append(flow_index)
        if matches != [0]:
            continue
        key = round(app_tx, 9)
        if row.get("event") == "tx":
            tx_times.add(key)
        elif row.get("event") == "rx" and math.isfinite(event_time):
            rx_times[key] = min(event_time, rx_times.get(key, math.inf))

    delivered = sorted({round(rx_times[key], 9) for key in tx_times if key in rx_times})
    states: list[tuple[float, bool]] = []
    for event_time in delivered:
        if event_time + 1e-12 < first_tx_s + 10.0:
            continue
        left = event_time - 10.0
        in_window = [value for value in delivered if left - 1e-10 <= value <= event_time + 1e-10]
        ready = bool(in_window) and in_window[0] - left <= 1.0 + 1e-10
        ready = ready and all(b - a <= 1.0 + 1e-10 for a, b in zip(in_window, in_window[1:]))
        states.append((event_time, ready))
    last_bad = max((i for i, (_, ready) in enumerate(states) if not ready), default=-1)
    suffix = states[last_bad + 1:]
    return suffix[0][0] if suffix else math.nan


def summarize_run(out: Path, graph: dict[str, object], protocol: str, duration_s: float,
                  warmup_frames: int) -> dict[str, object]:
    result_rows = [r for r in read_csv(out / "trace_replay_results.csv") if r.get("protocol") == protocol]
    result = result_rows[-1] if result_rows else {}
    flows = [r for r in read_csv(out / "flows.csv") if r.get("protocol") == protocol]
    probe_rows = [r for r in flows if r.get("is_probe") == "1"]
    probe = probe_rows[0] if probe_rows else {}
    background = [r for r in flows if r.get("is_probe") != "1"]
    pdrs = [number(r.get("delivered_unique_packets")) / number(r.get("offered_packets"))
            for r in flows if number(r.get("offered_packets")) > 0]
    bg_pdrs = [number(r.get("delivered_unique_packets")) / number(r.get("offered_packets"))
               for r in background if number(r.get("offered_packets")) > 0]
    _, degrees = graph_edges(graph)
    max_degree = max(degrees) if degrees else 0
    max_degree_node = min(i for i, degree in enumerate(degrees) if degree == max_degree) if degrees else -1
    node_metrics = load_node_metrics(out / "node_diagnostics.csv", protocol)
    def metric(node: int, name: str) -> int:
        return sum(v for (m, _, _), v in node_metrics.get(node, {}).items() if m == name)
    offered_by_source: dict[int, int] = {}
    for row in flows:
        source_node = int(row["source"].split("_")[-1])
        offered_by_source[source_node] = offered_by_source.get(source_node, 0) + int(row["offered_packets"])
    node_ids = list(range(int(graph["N"])))
    retries = [metric(n, "mac_data_failed_events") for n in node_ids]
    data_frames = [offered_by_source.get(n, 0) + metric(n, "forwarded_app_packets_ipv4") for n in node_ids]
    ratios = [retries[n] / data_frames[n] if data_frames[n] else math.nan for n in node_ids]
    collision_counts = [sum(v for (m, _, reason), v in node_metrics.get(n, {}).items()
                            if m == "phy_rx_drop_class" and reason == "collision_interference")
                        for n in node_ids]
    collision_rates = [v / duration_s if duration_s > 0 else math.nan for v in collision_counts]
    control_packets = [sum(v for (m, _, _), v in node_metrics.get(n, {}).items() if m == "control_tx_packets") for n in node_ids]
    control_bytes = [sum(v for (m, _, _), v in node_metrics.get(n, {}).items() if m == "control_tx_bytes") for n in node_ids]
    forwarded = [metric(n, "forwarded_app_packets_ipv4") for n in node_ids]
    convergence = number(probe.get("probe_convergence_s"))
    packet_path = out / f"packets_{protocol}.csv"
    if len(probe_rows) == 1 and packet_path.is_file():
        convergence = readiness_from_probe_packets(packet_path, flow_count=len(flows))
    return {
        "sim_wall_s": number(result.get("wall_time_s")),
        "cpu_s": number(result.get("cpu_time_s")),
        "first_delivery_s": number(probe.get("first_delivery_s")),
        "convergence_s": convergence,
        "probe_pdr": number(probe.get("delivered_unique_packets")) / number(probe.get("offered_packets"))
            if number(probe.get("offered_packets")) > 0 else math.nan,
        "background_pdr_median": type7(bg_pdrs, 0.5),
        "background_pdr_p10": type7(bg_pdrs, 0.10),
        "probe_delay_median_s": number(probe.get("median_delay_s")),
        "probe_delay_p95_s": number(probe.get("p95_delay_s")),
        "background_delay_median_s": type7([number(r.get("median_delay_s")) for r in background], 0.5),
        "background_delay_p95_s": type7([number(r.get("p95_delay_s")) for r in background], 0.95),
        "all_up_gap_s": gap_from_packets(out / f"packets_{protocol}.csv", warmup_frames)
            if (out / f"packets_{protocol}.csv").exists() else math.nan,
        "max_degree_node": max_degree_node,
        "max_degree": max_degree,
        "retry_callbacks_max": max(retries, default=0),
        "retry_ratio_max_degree": ratios[max_degree_node] if max_degree_node >= 0 else math.nan,
        "collision_drops_per_s_max": max(collision_rates, default=math.nan),
        "control_packets_mean": mean(control_packets),
        "control_packets_max": max(control_packets, default=0),
        "control_packets_gini": gini(control_packets),
        "control_bytes_mean": mean(control_bytes),
        "control_bytes_max": max(control_bytes, default=0),
        "control_bytes_gini": gini(control_bytes),
        "forwarded_load_gini": gini(forwarded),
        "result_pdr": number(result.get("pdr")),
        "app_tx_pkts": number(result.get("app_tx_pkts")),
        "app_rx_pkts": number(result.get("app_rx_pkts")),
    }


def ledger_rows() -> list[dict[str, str]]:
    return read_csv(A4 / "runs.csv")


def append_run_row(row: dict[str, object]) -> None:
    append_csv(A4 / "runs.csv", RUN_FIELDS, row)


def refresh_budget_accounting() -> None:
    budget = STUDY / "alpha" / "budget.md"
    text = budget.read_text(encoding="utf-8")
    marker = "### A4 live execution accounting\n"
    prefix = text.split(marker, 1)[0] if marker in text else text.rstrip() + "\n\n"
    rows = ledger_rows()
    a4d_rows = read_csv(A4 / "A4_0d" / "runs.csv")
    by_stage: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_stage.setdefault(row.get("stage", "unknown"), []).append(row)
    total_attempts = len(rows) + len(a4d_rows)
    spent_alpha = 12 + total_attempts
    lines = [marker.rstrip(),
             f"- A4 attempted protocol variants: **{total_attempts}**; cumulative Alpha spend: **{spent_alpha}/300**."]
    for stage in ("4.0A", "4.0B", "4.1", "4.2", "4.2_phi2", "4.3"):
        stage_rows = by_stage.get(stage, [])
        failures = sum(row.get("status") != "success" for row in stage_rows)
        lines.append(f"- {stage}: {len(stage_rows)} attempted; {failures} failed/timeout/malformed/unknown.")
    a4d_failures = sum(row.get("status") != "success" for row in a4d_rows)
    lines.insert(3, f"- 4.0d: {len(a4d_rows)} attempted; {a4d_failures} failed/timeout/malformed/unknown.")
    phi2_count = len(by_stage.get("4.2_phi2", []))
    replication_count = len(by_stage.get("4.3", []))
    lines.append(f"- 4.3 allowance used: {phi2_count} φ=2% charges + {replication_count} replication attempts = {phi2_count + replication_count}/72.")
    for filename in ("projection_initial.json", "projection_after_15.json", "projection_after_60.json",
                     "projection_after_105.json", "projection_phi2.json"):
        path = A4 / filename
        if path.is_file():
            try:
                projection = json.loads(path.read_text(encoding="utf-8"))
                hours = number(projection.get("projected_total_h"), number(projection.get("projected_total_s")) / 3600)
                lines.append(f"- Runtime projection {filename}: {hours:.3f} h.")
            except (OSError, json.JSONDecodeError, TypeError):
                lines.append(f"- Runtime projection {filename}: unreadable; inspect artifact.")
    budget.write_text(prefix + "\n".join(lines) + "\n", encoding="utf-8")


def existing_run(run_id: str) -> dict[str, str] | None:
    for row in ledger_rows():
        if row.get("run_id") == run_id:
            return row
    return None


def run_variant(*, stage: str, run_id: str, graph: dict[str, object], protocol: str,
                frame_count: int, warmup_frames: int, flow_seed: int, phi: float,
                load_role: str, kappa: float, n_background: int, explicit_flows: str | None,
                forward_log: bool = False, dump_routes: bool = False) -> dict[str, object]:
    prior = existing_run(run_id)
    if prior:
        if prior["status"] == "success":
            return prior
        raise RuntimeError(f"Refusing to retry prior {prior['status']} attempt {run_id}")
    if 12 + len(ledger_rows()) >= 300:
        raise RuntimeError("Refusing A4 protocol variant that would exceed the 300-variant Alpha cap")
    out = A4 / "runs" / run_id
    if out.exists():
        raise RuntimeError(f"Output exists without ledger row; refusing to rerun {run_id}")
    meminfo: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.replace(":", "").split()[:2]
        if key in {"MemAvailable", "SwapTotal", "SwapFree"}:
            meminfo[key] = int(value)
    available_kb = meminfo["MemAvailable"]
    swap_used_kb = meminfo["SwapTotal"] - meminfo["SwapFree"]
    if available_kb < 8 * 1024 * 1024 or swap_used_kb != 0:
        raise RuntimeError(f"resource guard blocked {run_id}: MemAvailable={available_kb}kB, SwapUsed={swap_used_kb}kB")
    out.mkdir(parents=True)
    (out / "resource_guard.json").write_text(json.dumps({
        "mem_available_kb": available_kb, "swap_used_kb": swap_used_kb,
        "worker_count": 1, "worker_cap": 4,
        "passed": True,
    }, indent=2) + "\n", encoding="utf-8")
    frames, frames_hash = allup_matrix(graph, frame_count)
    source = int(graph["probe_source"])
    destination = int(graph["probe_destination"])
    flows_arg = explicit_flows or f"Node_{source}:Node_{destination}"
    flow_fraction = (float(n_background) / (int(graph["N"]) * (int(graph["N"]) - 1) / 2)
                     if load_role.startswith("node") else phi)
    argv = [
        "./ns3", "run",
        "scratch/graph-run "
        f"--framesCsv={frames} --outDir={out} --routing={protocol} "
        f"--flows={flows_arg} --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 "
        "--interpolate=true --defaultLossDb=1000000 --txPowerDbm=20 "
        "--linkUpLossDb=10 --linkDownLossDb=125 --fps=1 --seed=42 "
        f"--warmup={warmup_frames} --warmupMode=first --instrumentation=true "
        f"--flowFraction={flow_fraction:.17g} --flowSeed={flow_seed} "
        f"--a3bForwardLog={'true' if forward_log else 'false'} "
        f"--dumpRoutes={'true' if dump_routes else 'false'}"
    ]
    exact = ["/usr/bin/time", "-v", "-o", str(out / "time.txt"), *argv]
    (out / "command.txt").write_text(shlex.join(exact) + "\n", encoding="utf-8")
    (out / "input.sha256").write_text(f"{frames_hash}  {frames.name}\n", encoding="utf-8")
    started = time.monotonic()
    status = "failed"
    code: int | None = None
    error = ""
    try:
        with (out / "ns3.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(exact, cwd=NS3, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, text=True)
            try:
                code = process.wait(timeout=RUN_TIMEOUT_S)
                status = "success" if code == 0 else "failed"
                if code != 0:
                    error = f"ns-3 returned {code}"
            except subprocess.TimeoutExpired:
                status = "timeout"
                error = f"exceeded {RUN_TIMEOUT_S}s; no retry"
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
        status = "failed"
        code = -1
        error = f"could not launch simulator command: {type(exc).__name__}: {exc}; no retry"
    process_wall = time.monotonic() - started
    time_text = (out / "time.txt").read_text(encoding="utf-8", errors="replace") if (out / "time.txt").exists() else ""
    rss_match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", time_text)
    peak_rss = int(rss_match.group(1)) if rss_match else math.nan
    metrics: dict[str, object] = {}
    if status == "success":
        try:
            duration = (frame_count - 1 + warmup_frames) / FRAME_RATE
            metrics = summarize_run(out, graph, protocol, duration, warmup_frames)
            if not math.isfinite(number(metrics.get("sim_wall_s"))):
                raise ValueError("missing simulator result row")
            if dump_routes:
                route_file = out / f"routes_{protocol}.txt"
                required = (route_file, out / f"packets_{protocol}.csv", out / f"times_{protocol}.csv")
                missing = [path.name for path in required if not path.is_file()]
                if missing:
                    raise ValueError(f"dumpRoutes artifacts missing: {missing}")
                with route_file.open("rb") as source_stream, open(str(route_file) + ".gz", "wb") as compressed_stream:
                    with gzip.GzipFile(fileobj=compressed_stream, mode="wb", mtime=0) as target_stream:
                        while block := source_stream.read(1024 * 1024):
                            target_stream.write(block)
                route_file.unlink()
        except Exception as exc:  # preserve successful process as malformed output, not retryable
            status = "malformed_output"
            error = f"{type(exc).__name__}: {exc}"
    n = int(graph["N"])
    flows_total = n_background + 1
    flows_per_node = flows_total / n
    flow_endpoints_per_node_mean = 2 * flows_total / n
    offered_kbps = flows_total * 50.0 / n
    warmup_s = warmup_frames / FRAME_RATE
    record: dict[str, object] = {
        "stage": stage, "run_id": run_id, "graph_id": graph["graph_id"], "family": graph["family"],
        "N": n, "realization": graph["realization"], "protocol": protocol,
        "load_role": load_role, "phi": fstr(phi), "kappa": fstr(kappa),
        "n_background": n_background, "n_total": flows_total,
        "flows_per_node": fstr(flows_per_node),
        "flow_endpoints_per_node_mean": fstr(flow_endpoints_per_node_mean),
        "offered_load_kbps_per_node": fstr(offered_kbps),
        "probe_source": graph["probe_source"], "probe_destination": graph["probe_destination"],
        "flow_seed": flow_seed, "routing_seed": 42, "input_frames": frame_count,
        "warmup_frames": warmup_frames, "warmup_s": fstr(warmup_s),
        "output_dir": str(out.relative_to(A4)), "status": status, "exit_code": code,
        "process_wall_s": fstr(process_wall), "peak_rss_kb": peak_rss, "error": error,
    }
    for key in ("sim_wall_s", "cpu_s", "first_delivery_s", "convergence_s", "probe_pdr",
                "background_pdr_median", "background_pdr_p10", "probe_delay_median_s",
                "probe_delay_p95_s", "background_delay_median_s", "background_delay_p95_s",
                "all_up_gap_s", "max_degree_node", "max_degree", "retry_callbacks_max",
                "retry_ratio_max_degree", "collision_drops_per_s_max", "control_packets_mean",
                "control_packets_max", "control_packets_gini", "control_bytes_mean",
                "control_bytes_max", "control_bytes_gini", "forwarded_load_gini"):
        record[key] = fstr(number(metrics.get(key))) if key in metrics else "nan"
    probe_pdr = number(metrics.get("probe_pdr"))
    bg_median = number(metrics.get("background_pdr_median"))
    record["borderline"] = bool((math.isfinite(probe_pdr) and abs(probe_pdr - .99) <= .02) or
                                 (math.isfinite(bg_median) and abs(bg_median - .95) <= .02))
    append_run_row(record)
    refresh_budget_accounting()
    return record


def successful_rows(stage: str | None = None) -> list[dict[str, str]]:
    rows = [r for r in ledger_rows() if r.get("status") == "success"]
    return [r for r in rows if stage is None or r.get("stage") == stage]


def row_by_id(run_id: str) -> dict[str, str]:
    for row in ledger_rows():
        if row.get("run_id") == run_id:
            return row
    raise KeyError(run_id)


def bool_csv(value: bool) -> str:
    return "true" if value else "false"


def validate_v1(out: Path, protocol: str, graph: dict[str, object], warmup_frames: int = 0) -> dict[str, object]:
    flows = [r for r in read_csv(out / "flows.csv") if r.get("protocol") == protocol]
    packet_rows = read_csv(out / f"packets_{protocol}.csv")
    forward_rows = read_csv(out / f"forward_events_{protocol}.csv")
    node_rows = load_node_metrics(out / "node_diagnostics.csv", protocol)
    expected_start: dict[tuple[int, int], int] = {}
    interval = PACKET_BYTES * 8 / RATE_BPS
    nflows = len(flows)
    for i, flow in enumerate(flows):
        source = int(flow["source"].split("_")[-1])
        dest = int(flow["destination"].split("_")[-1])
        expected_start[(source, dest)] = i
    tx_keys: dict[tuple[int, float], int] = {}
    for event in packet_rows:
        if event.get("event") != "tx":
            continue
        seq = int(event["sequence"])
        app_time = round(number(event["app_tx_time_s"]), 9)
        match = None
        for (source, dest), i in expected_start.items():
            expected_time = round(warmup_frames / FRAME_RATE + 0.1 + i / nflows + seq * interval, 9)
            if abs(app_time - expected_time) <= 2e-8:
                match = i
                break
        if match is None:
            return {"pass": False, "reason": f"TX packet cannot be assigned to flow: {seq}@{app_time}"}
        key = (seq, app_time)
        if key in tx_keys:
            return {"pass": False, "reason": f"ambiguous per-packet key {key}"}
        tx_keys[key] = match
    delivered_keys: set[tuple[int, float]] = set()
    for event in packet_rows:
        if event.get("event") == "rx":
            delivered_keys.add((int(event["sequence"]), round(number(event["app_tx_time_s"]), 9)))
    if not delivered_keys.issubset(tx_keys):
        return {"pass": False, "reason": "receive packet lacks a unique matching transmit"}
    edges, _ = graph_edges(graph)
    grouped: dict[tuple[int, float], list[dict[str, str]]] = {}
    for event in forward_rows:
        if event.get("counts_as_forward") != "1":
            continue
        key = (int(event["sequence"]), round(number(event["app_timestamp_s"]), 9))
        grouped.setdefault(key, []).append(event)
    total_events = sum(len(items) for items in grouped.values())
    matched_events = sum(len(grouped.get(key, [])) for key in tx_keys)
    delivered_packets_checked = 0
    for key in delivered_keys:
        flow_index = tx_keys[key]
        flow = flows[flow_index]
        source = int(flow["source"].split("_")[-1])
        dest = int(flow["destination"].split("_")[-1])
        events = sorted(grouped.get(key, []), key=lambda e: number(e["time_s"]))
        path = [source] + [int(e["node_id"]) for e in events] + [dest]
        if any(a == b or (min(a, b), max(a, b)) not in edges for a, b in zip(path, path[1:])):
            return {"pass": False, "reason": f"invalid reconstructed graph path for {key}: {path}"}
        reconstructed_hops = len(path) - 1
        if len(events) != reconstructed_hops - 1:
            return {"pass": False, "reason": f"forward/hop mismatch for {key}"}
        delivered_packets_checked += 1
    counter_total = sum(values.get(("forwarded_app_packets_ipv4", "", ""), 0)
                        for values in node_rows.values())
    delivered_event_count = sum(len(grouped.get(key, [])) for key in delivered_keys)
    undelivered_event_count = sum(len(grouped.get(key, [])) for key in tx_keys.keys() - delivered_keys)
    all_logged_match = matched_events == total_events
    exact_total = counter_total == delivered_event_count + undelivered_event_count == total_events
    offered = sum(int(flow["offered_packets"]) for flow in flows)
    delivered_by_flows = sum(int(flow["delivered_unique_packets"]) for flow in flows)
    passed = (delivered_packets_checked == delivered_by_flows and offered == len(tx_keys) and
              all_logged_match and exact_total)
    return {
        "pass": passed, "offered": offered, "delivered_unique": delivered_by_flows,
        "delivered_packets_path_checked": delivered_packets_checked,
        "forwarded_counter_total": counter_total, "delivered_forward_events": delivered_event_count,
        "undelivered_forward_events": undelivered_event_count, "all_forward_events_match_tx": all_logged_match,
        "exact_total": exact_total, "reason": "pass" if passed else "per-packet/counter conservation mismatch",
    }


def validate_v2(out: Path, protocol: str) -> dict[str, object]:
    node_rows = load_node_metrics(out / "node_diagnostics.csv", protocol)
    retry_failures = 0
    drop_callbacks = 0
    phy_raw = 0
    phy_classes = 0
    control_by_type = 0
    for metrics in node_rows.values():
        get = lambda name: sum(v for (m, _, _), v in metrics.items() if m == name)
        retries = get("mac_data_failed_events")
        drops = get("mac_final_data_failed") + get("mac_tx_drops") + get("mac_queue_drops")
        if retries < drops:
            return {"pass": False, "reason": "MAC retry callbacks below terminal/MAC/queue drops"}
        retry_failures += retries
        drop_callbacks += drops
        raw = get("phy_rx_drop_raw_reason")
        classes = get("phy_rx_drop_class")
        if raw != classes:
            return {"pass": False, "reason": "per-node PHY raw reason and class totals differ"}
        phy_raw += raw
        phy_classes += classes
        control_by_type += get("control_tx_packets")
    packet_diag = read_csv(out / f"packet_diagnostics_{protocol}.csv")
    diag = packet_diag[-1] if packet_diag else {}
    result = [r for r in read_csv(out / "trace_replay_results.csv") if r.get("protocol") == protocol]
    control_total = int(number(result[-1].get("control_packets"), -1)) if result else -1
    phy_total = int(number(diag.get("phy_rx_drop_callbacks"), -1)) if diag else -1
    passed = phy_raw == phy_classes == phy_total and control_by_type == control_total
    return {"pass": passed, "retry_failures": retry_failures, "terminal_and_drop_callbacks": drop_callbacks,
            "phy_raw_total": phy_raw, "phy_class_total": phy_classes, "phy_callback_total": phy_total,
            "control_by_type_total": control_by_type, "control_result_total": control_total,
            "reason": "pass" if passed else "PHY/control counter reconciliation mismatch"}


def validate_v3(out: Path, protocol: str) -> dict[str, object]:
    flows = [r for r in read_csv(out / "flows.csv") if r.get("protocol") == protocol]
    results = []
    for flow in flows:
        offered = int(flow["offered_packets"])
        delivered = int(flow["delivered_unique_packets"])
        median_delay = number(flow["median_delay_s"])
        p95 = number(flow["p95_delay_s"])
        passed = offered >= delivered and delivered > 0 and math.isfinite(median_delay) and math.isfinite(p95) and median_delay <= p95
        results.append({"flow_id": flow["flow_id"], "pass": passed, "offered": offered,
                        "delivered": delivered, "median_delay_s": median_delay, "p95_delay_s": p95})
    return {"pass": bool(results) and all(r["pass"] for r in results), "flows": results}


def endpoint_incidence(out: Path, protocol: str, graph: dict[str, object], run_id: str) -> list[dict[str, object]]:
    flows = [r for r in read_csv(out / "flows.csv") if r.get("protocol") == protocol]
    counts = [0] * int(graph["N"])
    for row in flows:
        counts[int(row["source"].rsplit("_", 1)[1])] += 1
        counts[int(row["destination"].rsplit("_", 1)[1])] += 1
    return [{"run_id": run_id, "graph_id": graph["graph_id"], "protocol": protocol,
             "N": graph["N"], "node_id": node, "flow_endpoint_incidence": count,
             "actual_flow_count": len(flows)} for node, count in enumerate(counts)]


def run_4_0(graphs: dict[str, dict[str, object]]) -> None:
    ge162 = graphs["geodesic_N162_r1"]
    pilot: list[dict[str, object]] = []
    all_pairs_162 = 162 * 161 / 2
    for role, phi in (("phi1", .01), ("phi10", .10)):
        count = llround(phi * all_pairs_162)
        for protocol in PROTOCOLS:
            rid = f"40A_geodesic_N162_r1_{protocol}_{role}"
            pilot.append(run_variant(stage="4.0A", run_id=rid, graph=ge162, protocol=protocol,
                                     frame_count=120, warmup_frames=0,
                                     flow_seed=int(hashlib.sha256(f"A4|{ge162['graph_id']}|{phi}".encode()).hexdigest()[:8], 16),
                                     phi=phi, load_role=role, kappa=math.nan, n_background=count,
                                     explicit_flows=None, dump_routes=False))
    ge42 = graphs["geodesic_N42_r1"]
    validation: list[dict[str, object]] = []
    for protocol in PROTOCOLS:
        rid = f"40B_geodesic_N42_r1_{protocol}_validation"
        validation.append(run_variant(stage="4.0B", run_id=rid, graph=ge42, protocol=protocol,
                                      frame_count=240, warmup_frames=0, flow_seed=PAIR_SEED,
                                      phi=2 / 861, load_role="validation_2_background", kappa=math.nan,
                                      n_background=2, explicit_flows="Node_0:Node_16", forward_log=True,
                                      dump_routes=True))
    endpoint_rows: list[dict[str, object]] = []
    flow_count_checks: list[dict[str, object]] = []
    for record in pilot + validation:
        if record["status"] != "success":
            continue
        out = A4 / str(record["output_dir"])
        graph = ge162 if str(record["run_id"]).startswith("40A_") else ge42
        protocol = str(record["protocol"])
        endpoint_rows.extend(endpoint_incidence(out, protocol, graph, str(record["run_id"])))
        flow_rows = [r for r in read_csv(out / "flows.csv") if r.get("protocol") == protocol]
        expected = int(record["n_total"])
        pair_set: set[str] = set()
        for flow in flow_rows:
            endpoints = sorted((flow["source"], flow["destination"]),
                               key=lambda label: int(label.rsplit("_", 1)[1]))
            pair_set.add(f"{endpoints[0]}:{endpoints[1]}")
        expected_pairs = ({"Node_0:Node_16", "Node_34:Node_39", "Node_4:Node_13"}
                  if str(record["run_id"]).startswith("40B_") else None)
        pair_pass = expected_pairs is None or pair_set == expected_pairs
        flow_count_checks.append({"run_id": record["run_id"], "expected_flows": expected,
                      "observed_flows": len(flow_rows), "count_pass": bool_csv(len(flow_rows) == expected),
                      "fixed_validation_pairs_pass": bool_csv(pair_pass),
                      "observed_pairs": ";".join(sorted(pair_set))})
    write_csv(A4 / "endpoint_incidence_4.0.csv",
              ["run_id", "graph_id", "protocol", "N", "node_id", "flow_endpoint_incidence", "actual_flow_count"], endpoint_rows)
    write_csv(A4 / "flow_count_checks_4.0.csv",
              ["run_id", "expected_flows", "observed_flows", "count_pass", "fixed_validation_pairs_pass", "observed_pairs"], flow_count_checks)
    failed_runs = [r["run_id"] for r in pilot + validation if r["status"] != "success"]
    validation_detail: dict[str, dict[str, object]] = {}
    for protocol in PROTOCOLS:
        run_id = f"40B_geodesic_N42_r1_{protocol}_validation"
        out = A4 / row_by_id(run_id)["output_dir"]
        v1 = validate_v1(out, protocol, ge42, warmup_frames=0)
        v2 = validate_v2(out, protocol)
        v3 = validate_v3(out, protocol)
        validation_detail[protocol] = {"V1": v1, "V2": v2, "V3": v3,
                                       "pass": bool(v1["pass"] and v2["pass"] and v3["pass"])}
    pilot_by_key = {(r["protocol"], r["load_role"]): r for r in pilot}
    projected_pair = preliminary_projection(pilot_by_key, per_node=False)
    projected_node = preliminary_projection(pilot_by_key, per_node=True)
    trigger_rows = []
    for protocol in PROTOCOLS:
        low = pilot_by_key[(protocol, "phi1")]
        high = pilot_by_key[(protocol, "phi10")]
        median_bg = number(high.get("background_pdr_median"))
        retry = number(high.get("retry_ratio_max_degree"))
        trigger_rows.append({
            "protocol": protocol, "phi10_background_median_pdr": fstr(median_bg),
            "phi10_max_degree_retry_ratio": fstr(retry),
            "trigger_background_median_lt_0_5": bool_csv(math.isfinite(median_bg) and median_bg < .5),
            "trigger_retry_ratio_gt_0_3": bool_csv(math.isfinite(retry) and retry > .3),
            "pilot_phi1_wall_s": low.get("process_wall_s"), "pilot_phi10_wall_s": high.get("process_wall_s"),
        })
    saturation = any(number(r["background_pdr_median"]) < .5 for r in (pilot_by_key[(p, "phi10")] for p in PROTOCOLS)) or \
                 any(number(r["retry_ratio_max_degree"]) > .3 for r in (pilot_by_key[(p, "phi10")] for p in PROTOCOLS)) or projected_pair > 24 * 3600
    load_unit = "per_node" if saturation else "per_pair"
    projection = projected_node if load_unit == "per_node" else projected_pair
    for item in trigger_rows:
        item["trigger_preliminary_projection_gt_24h"] = bool_csv(projected_pair > 24 * 3600)
        item["saturation_trigger_fired"] = bool_csv(saturation)
        item["selected_load_unit"] = load_unit
        item["projected_4_2_pair_s"] = fstr(projected_pair)
        item["projected_4_2_fallback_s"] = fstr(projected_node)
        item["selected_projected_4_2_s"] = fstr(projection)
    write_csv(A4 / "derived_4.0.csv", list(trigger_rows[0].keys()), trigger_rows)
    (A4 / "validation_4.0.json").write_text(json.dumps(validation_detail, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gate_olsr_aodv = all(validation_detail[p]["pass"] for p in ("olsr", "aodv"))
    if failed_runs:
        raise RuntimeError(f"A4.0 has failed/interrupted runs: {failed_runs}; no retry")
    bad_flow_checks = [row for row in flow_count_checks
                       if row["count_pass"] != "true" or row["fixed_validation_pairs_pass"] != "true"]
    if bad_flow_checks:
        raise RuntimeError(f"A4.0 observed flow selector/count differs from registration: {bad_flow_checks}")
    if not gate_olsr_aodv:
        raise RuntimeError("A4.0 stop-critical V1-V3 failure for OLSR/AODV; inspect validation_4.0.json before continuing")
    print(f"A4.0 attempted {len(pilot)+len(validation)} protocol variants; load_unit={load_unit}; projected_4.2_s={projection:.3f}")
    print("A4.0 validation:", json.dumps({p: validation_detail[p]["pass"] for p in PROTOCOLS}))
    refresh_budget_accounting()


def preliminary_projection(pilot: dict[tuple[str, str], dict[str, object]], per_node: bool) -> float:
    total = 0.0
    for n in SIZES:
        for family in FAMILIES:
            graph = next(g for g in load_a1()[0].values() if g["family"] == family and g["N"] == n and g["realization"] == 1)
            all_pairs = n * (n - 1) / 2
            for protocol in PROTOCOLS:
                t1 = number(pilot[(protocol, "phi1")].get("process_wall_s"))
                t10 = number(pilot[(protocol, "phi10")].get("process_wall_s"))
                if not math.isfinite(t1) or not math.isfinite(t10):
                    return math.inf
                f1, f10 = llround(.01 * all_pairs), llround(.10 * all_pairs)
                for role, phi in LOADS:
                    if per_node:
                        kappa = {"phi1": .25, "phi5": .5, "phi10": 1.0}[role]
                        flows = llround(kappa * n)
                    else:
                        flows = llround(phi * all_pairs)
                    if flows <= f1:
                        t = t1
                    else:
                        fraction = (flows - f1) / max(1, f10 - f1)
                        t = t1 + fraction * (t10 - t1)
                    total += max(t, 0.0) * (n / 162) ** 2 * (300 / 120)
    return total


def pearson(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return math.nan
    mx = mean([x for x, _ in pairs])
    my = mean([y for _, y in pairs])
    numerator = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    dy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    return numerator / (dx * dy) if dx and dy else math.nan


def run_4_1(graphs: dict[str, dict[str, object]]) -> None:
    graph_classes = [graphs[f"{family}_N{n}_r1"] for n in SIZES for family in FAMILIES]
    per_run: list[dict[str, object]] = []
    for graph in graph_classes:
        for protocol in PROTOCOLS:
            run_id = f"41_{graph['graph_id']}_{protocol}_probe"
            flow_seed = int(hashlib.sha256(f"A4|{graph['graph_id']}|probe".encode()).hexdigest()[:8], 16)
            record = run_variant(stage="4.1", run_id=run_id, graph=graph, protocol=protocol,
                                 frame_count=240, warmup_frames=0, flow_seed=flow_seed,
                                 phi=0.0, load_role="probe_only", kappa=math.nan,
                                 n_background=0, explicit_flows=None, dump_routes=True)
            per_run.append({
                "graph_id": graph["graph_id"], "family": graph["family"], "N": graph["N"],
                "diameter": graph["diameter"], "protocol": protocol, "status": record["status"],
                "first_delivery_s": record["first_delivery_s"], "convergence_s": record["convergence_s"],
                "censored": bool_csv((not math.isfinite(number(record["convergence_s"]))) or
                                     number(record["convergence_s"]) > 180),
                "all_up_gap_s": record["all_up_gap_s"],
                "dsdv_outage_drop": bool_csv(protocol == "dsdv" and number(record["all_up_gap_s"]) > 5),
                "process_wall_s": record["process_wall_s"], "sim_wall_s": record["sim_wall_s"],
                "output_dir": record["output_dir"],
            })
    write_csv(A4 / "derived_4.1_runs.csv", list(per_run[0].keys()), per_run)
    summaries: list[dict[str, object]] = []
    correlation_rows: list[dict[str, object]] = []
    for protocol in PROTOCOLS:
        all_rows = [row for row in per_run if row["protocol"] == protocol and row["status"] == "success"]
        overall_corr_n = pearson([number(row["N"]) for row in all_rows],
                                 [number(row["convergence_s"]) for row in all_rows])
        for n in SIZES:
            rows = [row for row in all_rows if int(row["N"]) == n]
            values = [number(row["convergence_s"]) for row in rows]
            censored = any(row["censored"] == "true" for row in rows)
            complete_five = len(rows) == 5
            derivable = complete_five and not censored
            maximum = max(values) if values and all(math.isfinite(x) for x in values) else math.nan
            warmup = math.ceil(1.5 * maximum) if derivable else math.nan
            corr_d = pearson([number(row["diameter"]) for row in rows], values)
            gaps = [number(row["all_up_gap_s"]) for row in rows]
            summaries.append({
                "protocol": protocol, "N": n, "successful_family_runs": len(rows),
                "convergence_min_s": fstr(min(values)) if values and all(math.isfinite(x) for x in values) else "nan",
                "convergence_median_s": fstr(type7(values, .5)),
                "convergence_max_s": fstr(maximum), "warmup_frames": warmup if derivable else "not_derivable",
                "censored_contributing_run": bool_csv(censored), "warmup_derivable": bool_csv(derivable),
                "gap_max_s": fstr(max(gaps)) if gaps and all(math.isfinite(x) for x in gaps) else "nan",
                "dsdv_any_gap_gt_5s": bool_csv(protocol == "dsdv" and any(x > 5 for x in gaps if math.isfinite(x))),
                "correlation_convergence_N_n15": fstr(overall_corr_n),
                "correlation_convergence_diameter_n5": fstr(corr_d),
            })
            correlation_rows.append({
                "protocol": protocol, "N": n, "n_family_r1": len(rows),
                "pearson_convergence_diameter": fstr(corr_d),
                "pearson_convergence_N_all_sizes_n15": fstr(overall_corr_n),
                "interpretation": "descriptive; five family-r1 graphs per size",
            })
    write_csv(A4 / "derived_4.1.csv", list(summaries[0].keys()), summaries)
    write_csv(A4 / "convergence_correlations.csv", list(correlation_rows[0].keys()), correlation_rows)
    failed = [r for r in per_run if r["status"] != "success"]
    print(f"A4.1 attempted {len(per_run)} protocol variants; failed={len(failed)}")
    for row in summaries:
        print(row["protocol"], row["N"], row["convergence_min_s"], row["convergence_median_s"],
              row["convergence_max_s"], row["warmup_frames"], "gap_max", row["gap_max_s"])
    refresh_budget_accounting()


def load_role_plan(n: int, per_node: bool) -> list[tuple[str, float, float, int]]:
    total_pairs = n * (n - 1) / 2
    if per_node:
        return [("node_k25", .01, .25, llround(.25 * n)),
                ("node_k50", .05, .50, llround(.50 * n)),
                ("node_k100", .10, 1.00, llround(1.00 * n))]
    return [(role, phi, math.nan, llround(phi * total_pairs)) for role, phi in LOADS]


def load_multiplier(protocol: str, n_background: int, n: int) -> float:
    pilots = {(r["protocol"], r["load_role"]): r for r in successful_rows("4.0A")}
    low = pilots.get((protocol, "phi1"))
    high = pilots.get((protocol, "phi10"))
    if not low or not high:
        return math.inf
    t1 = number(low["process_wall_s"])
    t10 = number(high["process_wall_s"])
    if not math.isfinite(t1) or not math.isfinite(t10) or t1 <= 0:
        return math.inf
    f1 = llround(.01 * n * (n - 1) / 2)
    f10 = llround(.10 * n * (n - 1) / 2)
    fraction = (n_background - f1) / max(1, f10 - f1)
    multiplier = 1 + fraction * (t10 / t1 - 1)
    return max(1.0, multiplier)


def warmup_map() -> dict[tuple[str, int], int | None]:
    result: dict[tuple[str, int], int | None] = {}
    for row in read_csv(A4 / "derived_4.1.csv"):
        value = row["warmup_frames"]
        result[(row["protocol"], int(row["N"]))] = int(value) if value.isdigit() else None
    return result


def dsdv_dropped_cells() -> set[str]:
    return {row["graph_id"] for row in read_csv(A4 / "derived_4.1_runs.csv")
            if row["protocol"] == "dsdv" and row["status"] == "success" and number(row["all_up_gap_s"]) > 5}


def estimate_42(graph: dict[str, object], protocol: str, warmup: int,
                n_background: int) -> float:
    base = existing_run(f"41_{graph['graph_id']}_{protocol}_probe")
    if not base or base["status"] != "success":
        return math.inf
    t = number(base["process_wall_s"])
    factor = load_multiplier(protocol, n_background, int(graph["N"]))
    return t * factor * (warmup + 120) / 240


def classify_failure(out: Path, protocol: str, graph: dict[str, object], run: dict[str, object]) -> str:
    if protocol == "dsdv" and number(run.get("all_up_gap_s")) > 5:
        return "all_up_outage"
    result_rows = [r for r in read_csv(out / "trace_replay_results.csv") if r.get("protocol") == protocol]
    result = result_rows[-1] if result_rows else {}
    if number(result.get("ip_drop_no_route"), 0) + number(result.get("ip_drop_route_err"), 0) > 0:
        return "no_route_or_route_error"
    nodes = load_node_metrics(out / "node_diagnostics.csv", protocol)
    queue = sum(v for metrics in nodes.values() for (m, _, _), v in metrics.items() if m == "mac_queue_drops")
    mac_final = sum(v for metrics in nodes.values() for (m, _, _), v in metrics.items() if m == "mac_final_data_failed")
    if queue:
        return "queue_drops"
    if mac_final or number(run.get("retry_ratio_max_degree")) > .3:
        return "MAC_saturation"
    if number(run.get("collision_drops_per_s_max")) >= 1:
        return "PHY_collision_interference"
    return "other"


def contention_drop(previous: dict[str, object], current: dict[str, object]) -> bool:
    retry = number(current.get("retry_ratio_max_degree"))
    previous_retry = number(previous.get("retry_ratio_max_degree"))
    collision = number(current.get("collision_drops_per_s_max"))
    previous_collision = number(previous.get("collision_drops_per_s_max"))
    retry_trigger = retry > .2 and (retry > 0 if previous_retry == 0 else retry >= 3 * previous_retry)
    collision_trigger = collision >= 1 and (collision > 0 if previous_collision == 0 else collision >= 3 * previous_collision)
    return retry_trigger or collision_trigger


def drop_attribution(previous: dict[str, object] | None, current: dict[str, object]) -> str:
    if previous is None:
        return "not_a_consecutive_load_drop"
    dropped = (number(current.get("probe_pdr")) < number(previous.get("probe_pdr")) or
               number(current.get("background_pdr_median")) < number(previous.get("background_pdr_median")))
    if not dropped:
        return "no_PDR_drop"
    return "MAC_contention_associated" if contention_drop(previous, current) else "not_attributed_to_MAC_by_frozen_rule"


def write_42_rows(rows_by_key: dict[tuple[str, str, str], dict[str, object]]) -> None:
    ordered = [rows_by_key[key] for key in sorted(rows_by_key, key=lambda k: (k[0], k[1], k[2]))]
    fields = list(dict.fromkeys(key for row in ordered for key in row)) if ordered else ["graph_id", "protocol", "load_role", "status"]
    write_csv(A4 / "derived_4.2_cells.csv", fields, ordered)


def run_4_2(graphs: dict[str, dict[str, object]]) -> None:
    a40 = read_csv(A4 / "derived_4.0.csv")
    if not a40:
        raise RuntimeError("A4.0 derived decision is missing")
    per_node = a40[0]["selected_load_unit"] == "per_node"
    warmups = warmup_map()
    dropped_dsdv = dsdv_dropped_cells()
    class_graphs = [graphs[f"{family}_N{n}_r1"] for n in SIZES for family in FAMILIES]
    class_costs: dict[str, float] = {}
    for graph in class_graphs:
        times = [number((existing_run(f"41_{graph['graph_id']}_{p}_probe") or {}).get("process_wall_s")) for p in PROTOCOLS]
        finite = [x for x in times if math.isfinite(x)]
        class_costs[str(graph["graph_id"])] = mean(finite) if finite else math.inf
    class_graphs.sort(key=lambda g: (class_costs[str(g["graph_id"])], str(g["graph_id"])))
    roles_by_n = {n: load_role_plan(n, per_node) for n in SIZES}
    plan: list[tuple[dict[str, object], str, str, float, float, int]] = []
    # The registered first batch is the lowest load for the five cheapest classes.
    for graph in class_graphs[:5]:
        role, nominal_phi, kappa, count = roles_by_n[int(graph["N"])][0]
        for protocol in PROTOCOLS:
            plan.append((graph, protocol, role, nominal_phi, kappa, count))
    # Continue class-by-class in cost order, with increasing loads inside each class.
    for graph_index, graph in enumerate(class_graphs):
        first_role_index = 1 if graph_index < 5 else 0
        for role_index in range(first_role_index, 3):
            role, nominal_phi, kappa, count = roles_by_n[int(graph["N"])][role_index]
            for protocol in PROTOCOLS:
                plan.append((graph, protocol, role, nominal_phi, kappa, count))
    status_rows: dict[tuple[str, str, str], dict[str, object]] = {}
    run_metrics: dict[tuple[str, str, str], dict[str, object]] = {}
    for graph, protocol, role, nominal_phi, kappa, count in plan:
        key = (str(graph["graph_id"]), protocol, role)
        warmup = warmups.get((protocol, int(graph["N"])))
        if warmup is None:
            status_rows[key] = {"graph_id": graph["graph_id"], "family": graph["family"], "N": graph["N"],
                                "protocol": protocol, "load_role": role, "phi_nominal": nominal_phi,
                                "n_background": count, "status": "skipped", "reason": "warmup_not_derivable"}
        elif protocol == "dsdv" and str(graph["graph_id"]) in dropped_dsdv:
            status_rows[key] = {"graph_id": graph["graph_id"], "family": graph["family"], "N": graph["N"],
                                "protocol": protocol, "load_role": role, "phi_nominal": nominal_phi,
                                "n_background": count, "status": "skipped", "reason": "dsdv_all_up_outage_gt_5s"}

    candidates = [(g, p, role, phi, kappa, count) for g, p, role, phi, kappa, count in plan
                  if (str(g["graph_id"]), p, role) not in status_rows]
    initial_projection = sum(estimate_42(g, p, warmups[(p, int(g["N"]))], count)
                             for g, p, _, _, _, count in candidates)
    (A4 / "projection_initial.json").write_text(json.dumps({
        "planned_candidates": len(candidates), "projected_total_s": initial_projection,
        "projected_total_h": initial_projection / 3600,
        "stop_if_over_24h": initial_projection > 24 * 3600}, indent=2) + "\n", encoding="utf-8")
    if initial_projection > 24 * 3600:
        refresh_budget_accounting()
        raise RuntimeError(f"A4.2 preregistered projection exceeds 24h before launch: {initial_projection:.1f}s")
    print(f"A4.2 initial projected wall time: {initial_projection:.1f}s ({initial_projection/3600:.2f}h)")
    attempt_count = 0
    correction = 1.0
    for graph, protocol, role, nominal_phi, kappa, count in plan:
        key = (str(graph["graph_id"]), protocol, role)
        if key in status_rows:
            continue
        n = int(graph["N"])
        lower_roles = roles_by_n[n]
        role_position = next(i for i, r in enumerate(lower_roles) if r[0] == role)
        dropped_lower = False
        for lower_role, _, _, _ in lower_roles[:role_position]:
            lower = status_rows.get((str(graph["graph_id"]), protocol, lower_role))
            if lower and lower.get("status") == "failed_lowest_or_lower_load":
                dropped_lower = True
                break
            if lower and lower.get("status") == "pass":
                continue
            if lower and lower.get("status") in ("skipped", "failed"):
                dropped_lower = True
                break
        if dropped_lower:
            status_rows[key] = {"graph_id": graph["graph_id"], "family": graph["family"], "N": n,
                                "protocol": protocol, "load_role": role, "phi_nominal": nominal_phi,
                                "n_background": count, "status": "skipped", "reason": "lower_load_failed_or_skipped"}
            continue
        run_id = f"42_{graph['graph_id']}_{protocol}_{role}"
        role_seed = f"A4|{graph['graph_id']}|{nominal_phi:g}"
        flow_seed = int(hashlib.sha256(role_seed.encode()).hexdigest()[:8], 16)
        record = run_variant(stage="4.2", run_id=run_id, graph=graph, protocol=protocol,
                             frame_count=120, warmup_frames=warmups[(protocol, n)],
                             flow_seed=flow_seed, phi=nominal_phi, load_role=role,
                             kappa=kappa, n_background=count, explicit_flows=None,
                             dump_routes=False)
        attempt_count += 1
        out = A4 / record["output_dir"]
        pdr_pass = number(record["probe_pdr"]) >= .99 and number(record["background_pdr_median"]) >= .95
        previous = None
        if role_position > 0:
            prev_role = lower_roles[role_position - 1][0]
            prev_key = (str(graph["graph_id"]), protocol, prev_role)
            if prev_key in run_metrics:
                previous = run_metrics[prev_key]
        attribution = drop_attribution(previous, record)
        cause = "pass" if pdr_pass else classify_failure(out, protocol, graph, record)
        status = "pass" if pdr_pass else ("failed_lowest_or_lower_load" if role_position == 0 else "failed")
        cell = {"graph_id": graph["graph_id"], "family": graph["family"], "N": n,
                "protocol": protocol, "load_role": role, "phi_nominal": nominal_phi,
                "kappa": kappa, "n_background": count, "status": status,
                "reason": cause, "probe_pdr": record["probe_pdr"],
                "background_pdr_median": record["background_pdr_median"],
                "background_pdr_p10": record["background_pdr_p10"],
                "probe_delay_median_s": record["probe_delay_median_s"],
                "probe_delay_p95_s": record["probe_delay_p95_s"],
                "background_delay_median_s": record["background_delay_median_s"],
                "background_delay_p95_s": record["background_delay_p95_s"],
                "control_packets_mean": record["control_packets_mean"], "control_packets_max": record["control_packets_max"],
                "control_packets_gini": record["control_packets_gini"],
                "control_bytes_mean": record["control_bytes_mean"], "control_bytes_max": record["control_bytes_max"],
                "control_bytes_gini": record["control_bytes_gini"], "forwarded_load_gini": record["forwarded_load_gini"],
                "retry_callbacks_max": record["retry_callbacks_max"],
                "retry_ratio_max_degree": record["retry_ratio_max_degree"],
                "collision_drops_per_s_max": record["collision_drops_per_s_max"],
                "all_up_gap_s": record["all_up_gap_s"], "borderline": record["borderline"],
                "drop_attribution": attribution, "run_id": run_id,
                "process_wall_s": record["process_wall_s"], "warmup_frames": warmups[(protocol, n)]}
        status_rows[key] = cell
        run_metrics[key] = record
        if attempt_count in (15, 60, 105):
            ratios: list[float] = []
            for (gid, completed_protocol, completed_role), actual_row in run_metrics.items():
                completed_graph = graphs[gid]
                completed_count = next((item[5] for item in plan
                                        if str(item[0]["graph_id"]) == gid
                                        and item[1] == completed_protocol and item[2] == completed_role), 0)
                predicted_one = estimate_42(completed_graph, completed_protocol,
                                            warmups[(completed_protocol, int(completed_graph["N"]))],
                                            completed_count)
                actual_one = number(actual_row.get("process_wall_s"))
                if math.isfinite(actual_one) and math.isfinite(predicted_one) and predicted_one > 0:
                    ratios.append(actual_one / predicted_one)
            correction = type7(ratios, .5) if ratios else 1.0
            remaining_items = [(g, p, r, phi, kap, cnt) for g, p, r, phi, kap, cnt in candidates
                               if (str(g["graph_id"]), p, r) not in status_rows]
            projected_remaining = sum(estimate_42(g, p, warmups[(p, int(g["N"]))], cnt)
                                      for g, p, _, _, _, cnt in remaining_items)
            actual_elapsed = sum(number(row.get("process_wall_s")) for row in run_metrics.values()
                                 if math.isfinite(number(row.get("process_wall_s"))))
            projected_total = actual_elapsed + projected_remaining * correction
            checkpoint = {"attempts_completed": attempt_count,
                          "median_actual_to_projected_correction": correction,
                          "projected_total_s": projected_total,
                          "projected_total_h": projected_total / 3600,
                          "stop_if_over_24h": projected_total > 24 * 3600}
            checkpoint_path = A4 / f"projection_after_{attempt_count}.json"
            checkpoint_path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
            print(f"A4.2 projection after {attempt_count} attempts: {projected_total:.1f}s ({projected_total/3600:.2f}h)")
            if projected_total > 24 * 3600:
                write_42_rows(status_rows)
                refresh_budget_accounting()
                raise RuntimeError(f"A4.2 updated projection exceeds 24 h after {attempt_count} attempts; stop and ask")
    # Optional 2% sensitivity grid is conditional only on the frozen common-load rule.
    role_load = {role: phi for role, phi in LOADS}
    operable_sizes: dict[int, float | None] = {}
    for n in SIZES:
        retained = []
        for graph in class_graphs:
            if int(graph["N"]) != n:
                continue
            for protocol in PROTOCOLS:
                if protocol == "dsdv" and str(graph["graph_id"]) in dropped_dsdv:
                    continue
                low = status_rows.get((str(graph["graph_id"]), protocol, roles_by_n[n][0][0]))
                if low and low.get("status") == "pass":
                    retained.append((str(graph["graph_id"]), protocol))
        candidates_phi = [.10, .05, .01]
        selected = None
        for phi in candidates_phi:
            role = next(name for name, value in role_load.items() if value == phi)
            if retained and all((status_rows.get((gid, proto, role)) or {}).get("status") == "pass"
                                for gid, proto in retained):
                selected = phi
                break
        if selected is None and retained:
            phi5_role = next(name for name, value in role_load.items() if value == .05)
            phi1_role = next(name for name, value in role_load.items() if value == .01)
            if not all((status_rows.get((gid, proto, phi5_role)) or {}).get("status") == "pass"
                       for gid, proto in retained) and any(
                       (status_rows.get((gid, proto, phi1_role)) or {}).get("status") == "pass"
                       for gid, proto in retained):
                selected = None  # the 2% grid may establish the next common level below
        operable_sizes[n] = selected

    phi2_rows: list[dict[str, object]] = []
    if not per_node:
        phi2_candidates: list[tuple[dict[str, object], str, int]] = []
        for n in SIZES:
            retained = [(str(graph["graph_id"]), protocol) for graph in class_graphs if int(graph["N"]) == n
                        for protocol in PROTOCOLS
                        if not (protocol == "dsdv" and str(graph["graph_id"]) in dropped_dsdv)
                        and (status_rows.get((str(graph["graph_id"]), protocol, "phi1")) or {}).get("status") == "pass"]
            phi1_pass = bool(retained)
            phi5_pass = phi1_pass and all((status_rows.get((gid, p, "phi5")) or {}).get("status") == "pass"
                                          for gid, p in retained)
            if phi1_pass and not phi5_pass:
                for graph in class_graphs:
                    if int(graph["N"]) != n:
                        continue
                    for protocol in PROTOCOLS:
                        low = status_rows.get((str(graph["graph_id"]), protocol, "phi1"))
                        if protocol == "dsdv" and str(graph["graph_id"]) in dropped_dsdv:
                            continue
                        if not low or low.get("status") != "pass":
                            continue
                        warmup = warmups.get((protocol, n))
                        if warmup is None:
                            continue
                        phi2_candidates.append((graph, protocol, llround(.02 * n * (n - 1) / 2)))
        phi2_projected = sum(estimate_42(graph, protocol, warmups[(protocol, int(graph["N"]))], count)
                             for graph, protocol, count in phi2_candidates)
        base_elapsed = sum(number(r.get("process_wall_s")) for r in ledger_rows()
                           if r.get("stage") == "4.2" and math.isfinite(number(r.get("process_wall_s"))))
        phi2_total_projection = base_elapsed + phi2_projected
        (A4 / "projection_phi2.json").write_text(json.dumps({
            "eligible_phi2_variants": len(phi2_candidates), "projected_phi2_s": phi2_projected,
            "base_elapsed_s": base_elapsed, "projected_total_s": phi2_total_projection,
            "projected_total_h": phi2_total_projection / 3600,
            "stop_if_over_24h": phi2_total_projection > 24 * 3600}, indent=2) + "\n", encoding="utf-8")
        print(f"A4.2 projected base + optional 2% runtime: {phi2_total_projection:.1f}s ({phi2_total_projection/3600:.2f}h)")
        if phi2_total_projection > 24 * 3600:
            write_42_rows(status_rows)
            refresh_budget_accounting()
            raise RuntimeError("A4.2 optional 2% projection exceeds 24 h; no 2% variants launched")
        phi2_candidate_keys = {(str(graph["graph_id"]), protocol) for graph, protocol, _ in phi2_candidates}
        for n in SIZES:
            retained = [(str(graph["graph_id"]), protocol) for graph in class_graphs if int(graph["N"]) == n
                        for protocol in PROTOCOLS
                        if (str(graph["graph_id"]), protocol) in phi2_candidate_keys]
            phi1_pass = bool(retained)
            phi5_pass = phi1_pass and all((status_rows.get((gid, p, "phi5")) or {}).get("status") == "pass"
                                          for gid, p in retained)
            if phi1_pass and not phi5_pass:
                for graph in class_graphs:
                    if int(graph["N"]) != n:
                        continue
                    for protocol in PROTOCOLS:
                        key = (str(graph["graph_id"]), protocol, "phi2")
                        if protocol == "dsdv" and str(graph["graph_id"]) in dropped_dsdv:
                            status_rows[key] = {"graph_id": graph["graph_id"], "family": graph["family"],
                                                "N": n, "protocol": protocol, "load_role": "phi2",
                                                "phi_nominal": .02, "n_background": llround(.02 * n * (n - 1) / 2),
                                                "status": "skipped", "reason": "dsdv_all_up_outage_gt_5s"}
                            continue
                        low = status_rows.get((str(graph["graph_id"]), protocol, "phi1"))
                        if not low or low.get("status") != "pass":
                            status_rows[key] = {"graph_id": graph["graph_id"], "family": graph["family"],
                                                "N": n, "protocol": protocol, "load_role": "phi2",
                                                "phi_nominal": .02, "n_background": llround(.02 * n * (n - 1) / 2),
                                                "status": "skipped", "reason": "lowest_load_failed_or_skipped"}
                            continue
                        warmup = warmups.get((protocol, n))
                        if warmup is None:
                            status_rows[key] = {"graph_id": graph["graph_id"], "family": graph["family"],
                                                "N": n, "protocol": protocol, "load_role": "phi2",
                                                "phi_nominal": .02, "n_background": llround(.02 * n * (n - 1) / 2),
                                                "status": "skipped", "reason": "warmup_not_derivable"}
                            continue
                        if (str(graph["graph_id"]), protocol) not in phi2_candidate_keys:
                            continue
                        run_id = f"42_{graph['graph_id']}_{protocol}_phi2"
                        flow_seed = int(hashlib.sha256(f"A4|{graph['graph_id']}|0.02".encode()).hexdigest()[:8], 16)
                        count = llround(.02 * n * (n - 1) / 2)
                        record = run_variant(stage="4.2_phi2", run_id=run_id, graph=graph, protocol=protocol,
                                             frame_count=120, warmup_frames=warmup, flow_seed=flow_seed,
                                             phi=.02, load_role="phi2", kappa=math.nan,
                                             n_background=count, explicit_flows=None, dump_routes=False)
                        out = A4 / record["output_dir"]
                        passed = number(record["probe_pdr"]) >= .99 and number(record["background_pdr_median"]) >= .95
                        cell = {"graph_id": graph["graph_id"], "family": graph["family"], "N": n,
                                "protocol": protocol, "load_role": "phi2", "phi_nominal": .02,
                                "kappa": math.nan, "n_background": count,
                                "status": "pass" if passed else "failed", "reason": "pass" if passed else classify_failure(out, protocol, graph, record),
                                "probe_pdr": record["probe_pdr"], "background_pdr_median": record["background_pdr_median"],
                                "background_pdr_p10": record["background_pdr_p10"],
                                "probe_delay_median_s": record["probe_delay_median_s"], "probe_delay_p95_s": record["probe_delay_p95_s"],
                                "background_delay_median_s": record["background_delay_median_s"], "background_delay_p95_s": record["background_delay_p95_s"],
                                "control_packets_mean": record["control_packets_mean"], "control_packets_max": record["control_packets_max"],
                                "control_packets_gini": record["control_packets_gini"], "control_bytes_mean": record["control_bytes_mean"],
                                "control_bytes_max": record["control_bytes_max"], "control_bytes_gini": record["control_bytes_gini"],
                                "forwarded_load_gini": record["forwarded_load_gini"], "retry_callbacks_max": record["retry_callbacks_max"],
                                "retry_ratio_max_degree": record["retry_ratio_max_degree"],
                                "collision_drops_per_s_max": record["collision_drops_per_s_max"],
                                "all_up_gap_s": record["all_up_gap_s"], "borderline": record["borderline"],
                                "drop_attribution": "not_applicable_for_added_phi2", "run_id": run_id,
                                "process_wall_s": record["process_wall_s"], "warmup_frames": warmup,
                                "charged_to_4_3_allowance": 1}
                        status_rows[key] = cell
                        phi2_rows.append(cell)
                        run_metrics[key] = record
                        cell["drop_attribution"] = drop_attribution(
                            run_metrics.get((str(graph["graph_id"]), protocol, "phi1")), record)
                        five_key = (str(graph["graph_id"]), protocol, "phi5")
                        if five_key in status_rows:
                            status_rows[five_key]["drop_attribution"] = drop_attribution(
                                record, run_metrics.get(five_key, status_rows[five_key]))

    # Formal N=162 protocol drops and common operating role are derived mechanically.
    formal_drop_by: dict[tuple[int, str], bool] = {}
    for n in SIZES:
        for protocol in PROTOCOLS:
            fam_low = [status_rows.get((str(g["graph_id"]), protocol, roles_by_n[n][0][0]))
                       for g in class_graphs if int(g["N"]) == n]
            failed_all = len(fam_low) == 5 and all(
                r and r.get("status") in {"failed_lowest_or_lower_load", "failed"} for r in fam_low)
            formal_drop_by[(n, protocol)] = bool(n == 162 and failed_all)
    write_42_rows(status_rows)
    op_rows: list[dict[str, object]] = []
    for n in SIZES:
        retained = [(str(g["graph_id"]), p) for g in class_graphs if int(g["N"]) == n
                    for p in PROTOCOLS
                    if not (p == "dsdv" and str(g["graph_id"]) in dropped_dsdv)
                    and (status_rows.get((str(g["graph_id"]), p, roles_by_n[n][0][0])) or {}).get("status") == "pass"]
        possible: list[tuple[str, float, float]] = []
        role_names = ([ ("phi1", .01, .01), ("phi2", .02, .02), ("phi5", .05, .05), ("phi10", .10, .10) ]
                      if not per_node else
                      [("node_k25", .01, .25), ("node_k50", .05, .50), ("node_k100", .10, 1.0)])
        for role, level, reported_value in role_names:
            if retained and all((status_rows.get((gid, proto, role)) or {}).get("status") == "pass" for gid, proto in retained):
                possible.append((role, level, reported_value))
        selected = max(possible, key=lambda v: v[1]) if possible else ("none", math.nan, math.nan)
        bg_flows = 0
        if selected[0] != "none":
            bg_flows = llround(selected[2] * n) if per_node else llround(selected[2] * n * (n - 1) / 2)
            if per_node:
                bg_flows = llround(selected[2] * n)
        op_rows.append({"N": n, "load_unit": "per_node" if per_node else "per_pair",
                        "operating_role": selected[0], "operating_phi_or_kappa": fstr(selected[2]),
                        "background_flows": bg_flows, "probe_additional": 1,
                        "flows_per_node_endpoints_including_probe": fstr(2 * (bg_flows + 1) / n),
                        "retained_graph_protocol_cells": len(retained),
                        "families_used": ";".join(sorted({gid.split("_N")[0] for gid, _ in retained})) if retained else "none"})
    write_csv(A4 / "derived_4.2.csv", list(op_rows[0].keys()), op_rows)
    operating_by_n = {int(row["N"]): row for row in op_rows}
    matrix_rows: list[dict[str, object]] = []
    for graph in class_graphs:
        n = int(graph["N"])
        lowest_role = roles_by_n[n][0][0]
        operating_role = str(operating_by_n[n]["operating_role"])
        for protocol in PROTOCOLS:
            low = status_rows.get((str(graph["graph_id"]), protocol, lowest_role))
            at_operating = status_rows.get((str(graph["graph_id"]), protocol, operating_role)) if operating_role != "none" else None
            matrix_rows.append({"graph_id": graph["graph_id"], "family": graph["family"], "N": n,
                                "protocol": protocol, "lowest_load_role": lowest_role,
                                "lowest_load_status": low.get("status") if low else "missing",
                                "operating_role": operating_role,
                                "operating_cell_status": at_operating.get("status") if at_operating else "none_or_unavailable",
                                "operating_cell_reason": at_operating.get("reason", "") if at_operating else "",
                                "formal_protocol_drop_at_N162": bool_csv(formal_drop_by[(n, protocol)]),
                                "dsdv_all_up_outage": bool_csv(protocol == "dsdv" and str(graph["graph_id"]) in dropped_dsdv)})
    write_csv(A4 / "status_matrix_4.2.csv", list(matrix_rows[0].keys()), matrix_rows)
    refresh_budget_accounting()
    print(f"A4.2 attempted {attempt_count + len(phi2_rows)} base/phi2 variants; load_unit={'per_node' if per_node else 'per_pair'}")
    for row in op_rows:
        print("A4.2 operating load", row["N"], row["operating_role"], row["background_flows"])


def sample_sd(values: list[float]) -> float:
    finite = [v for v in values if math.isfinite(v)]
    if len(finite) < 2:
        return math.nan
    center = mean(finite)
    return math.sqrt(sum((v - center) ** 2 for v in finite) / (len(finite) - 1))


def run_4_3(graphs: dict[str, dict[str, object]]) -> None:
    operating = {int(r["N"]): r for r in read_csv(A4 / "derived_4.2.csv")}
    formal_drops = {(int(r["N"]), r["protocol"]): r["formal_protocol_drop_at_N162"] == "true"
                    for r in read_csv(A4 / "status_matrix_4.2.csv")}
    dsdv_outages = dsdv_dropped_cells()
    phi2_charge = sum(1 for r in ledger_rows() if r.get("stage") == "4.2_phi2")
    replicate_capacity = max(0, 72 - phi2_charge)
    family_order = {name: i for i, name in enumerate(("rgg", "ws", "er", "ba"))}
    protocol_order = {name: i for i, name in enumerate(PROTOCOLS)}
    all_cells: list[dict[str, object]] = []
    eligible: list[dict[str, object]] = []
    for realization in (2, 3):
        for family in ("rgg", "ws", "er", "ba"):
            for n in SIZES:
                r1 = graphs[f"{family}_N{n}_r1"]
                role = str(operating[n]["operating_role"])
                unit = str(operating[n]["load_unit"])
                if unit == "per_node":
                    role_map = {"node_k25": .25, "node_k50": .50, "node_k100": 1.0}
                    phi_map = {"node_k25": .01, "node_k50": .05, "node_k100": .10}
                    kappa = role_map.get(role, math.nan)
                    phi = phi_map.get(role, math.nan)
                    count = llround(kappa * n) if math.isfinite(kappa) else 0
                else:
                    kappa = math.nan
                    phi_map = {"phi1": .01, "phi2": .02, "phi5": .05, "phi10": .10}
                    phi = phi_map.get(role, math.nan)
                    count = llround(phi * n * (n - 1) / 2) if math.isfinite(phi) else 0
                for protocol in PROTOCOLS:
                    key_r1 = (str(r1["graph_id"]), protocol, role)
                    base = next((r for r in read_csv(A4 / "derived_4.2_cells.csv")
                                 if (r.get("graph_id"), r.get("protocol"), r.get("load_role")) == key_r1), None)
                    eligible_cell = (role != "none" and not formal_drops.get((n, protocol), False)
                                     and not (protocol == "dsdv" and str(r1["graph_id"]) in dsdv_outages)
                                     and base is not None and base.get("status") == "pass")
                    for graph_realization in (realization,):
                        graph = graphs[f"{family}_N{n}_r{graph_realization}"]
                        cut_rank = (0 if realization == 3 else 1,
                                    0 if any(r.get("N") == str(n) and r.get("load_role") == "phi2"
                                             for r in read_csv(A4 / "derived_4.2_cells.csv")) else 1,
                                    family_order[family], protocol_order[protocol], SIZES.index(n))
                        cell = {"graph": graph, "r1": base, "family": family, "N": n,
                                "protocol": protocol, "realization": realization,
                                "role": role, "unit": unit, "phi": phi, "kappa": kappa,
                                "n_background": count, "eligible": eligible_cell,
                                "cut_rank": cut_rank}
                        all_cells.append(cell)
                        if eligible_cell:
                            eligible.append(cell)
    eligible.sort(key=lambda item: item["cut_rank"])
    cut_count = max(0, len(eligible) - replicate_capacity)
    cut_ids = {f"{c['family']}_N{c['N']}_r{c['realization']}|{c['protocol']}" for c in eligible[:cut_count]}
    run_cells = [c for c in eligible if f"{c['family']}_N{c['N']}_r{c['realization']}|{c['protocol']}" not in cut_ids]
    skipped: list[dict[str, object]] = []
    for cell in all_cells:
        key = f"{cell['family']}_N{cell['N']}_r{cell['realization']}|{cell['protocol']}"
        reason = None
        if not cell["eligible"]:
            reason = "no_operating_load" if cell["role"] == "none" else "r1_cell_not_passed_or_protocol_dropped"
        elif key in cut_ids:
            reason = "cut_for_phi2_budget; preregistered_replication_cut_order"
        if reason:
            skipped.append({"graph_id": cell["graph"]["graph_id"], "family": cell["family"],
                            "N": cell["N"], "protocol": cell["protocol"],
                            "realization": cell["realization"], "load_role": cell["role"],
                            "status": "skipped", "reason": reason, "phi2_charge": phi2_charge,
                            "replication_capacity": replicate_capacity})
    observed_rows: list[dict[str, object]] = []
    attempted = 0
    for cell in run_cells:
        graph = cell["graph"]
        protocol = str(cell["protocol"])
        realization = int(cell["realization"])
        n = int(cell["N"])
        warmup = warmup_map().get((protocol, n))
        if warmup is None:
            skipped.append({"graph_id": graph["graph_id"], "family": cell["family"], "N": n,
                            "protocol": protocol, "realization": realization,
                            "load_role": cell["role"], "status": "skipped",
                            "reason": "warmup_not_derivable", "phi2_charge": phi2_charge,
                            "replication_capacity": replicate_capacity})
            continue
        phi = number(cell["phi"])
        phi_text = f"{phi:g}"
        flow_seed = int(hashlib.sha256(
            f"A4|{graph['graph_id']}|{phi_text}|{realization}".encode()).hexdigest()[:8], 16)
        run_id = f"43_{graph['graph_id']}_{protocol}_{cell['role']}"
        record = run_variant(stage="4.3", run_id=run_id, graph=graph, protocol=protocol,
                             frame_count=120, warmup_frames=warmup, flow_seed=flow_seed,
                             phi=phi, load_role=str(cell["role"]), kappa=number(cell["kappa"]),
                             n_background=int(cell["n_background"]), explicit_flows=None,
                             dump_routes=False)
        attempted += 1
        pass_cell = number(record["probe_pdr"]) >= .99 and number(record["background_pdr_median"]) >= .95
        convergence = number(record["convergence_s"])
        first_tx_s = warmup + .1
        convergence_after_tx = convergence - first_tx_s if math.isfinite(convergence) else math.nan
        observed_rows.append({
            "graph_id": graph["graph_id"], "family": cell["family"], "N": n,
            "protocol": protocol, "realization": realization,
            "load_role": cell["role"], "load_unit": cell["unit"],
            "phi": fstr(phi), "kappa": fstr(number(cell["kappa"])),
            "n_background": cell["n_background"], "n_total": int(cell["n_background"]) + 1,
            "status": record["status"], "pdr_gate": "pass" if pass_cell else "fail",
            "probe_pdr": record["probe_pdr"], "background_pdr_median": record["background_pdr_median"],
            "probe_delay_median_s": record["probe_delay_median_s"],
            "probe_delay_p95_s": record["probe_delay_p95_s"],
            "background_delay_median_s": record["background_delay_median_s"],
            "background_delay_p95_s": record["background_delay_p95_s"],
            "first_probe_tx_s": fstr(first_tx_s), "convergence_s_sim_clock": record["convergence_s"],
            "convergence_after_first_tx_s": fstr(convergence_after_tx),
            "convergence_within_10s_after_first_tx": bool_csv(math.isfinite(convergence_after_tx) and
                                                                  convergence_after_tx <= 10),
            "convergence_observable_before_warmup_end": "not_observable_by_design",
            "warmup_frames": warmup, "run_id": run_id,
            "process_wall_s": record["process_wall_s"], "all_up_gap_s": record["all_up_gap_s"],
            "control_packets_mean": record["control_packets_mean"],
            "control_packets_max": record["control_packets_max"],
            "control_packets_gini": record["control_packets_gini"],
            "control_bytes_mean": record["control_bytes_mean"],
            "control_bytes_max": record["control_bytes_max"],
            "control_bytes_gini": record["control_bytes_gini"],
            "forwarded_load_gini": record["forwarded_load_gini"],
            "retry_callbacks_max": record["retry_callbacks_max"],
            "retry_ratio_max_degree": record["retry_ratio_max_degree"],
            "collision_drops_per_s_max": record["collision_drops_per_s_max"],
            "borderline": record["borderline"],
        })
    all_outcomes: dict[tuple[str, int, str], dict[int, dict[str, object]]] = {}
    for row in observed_rows:
        all_outcomes.setdefault((str(row["family"]), int(row["N"]), str(row["protocol"])), {})[
            int(row["realization"])] = row
    for cell in all_cells:
        base = cell["r1"]
        if base is None:
            continue
        key = (str(cell["family"]), int(cell["N"]), str(cell["protocol"]))
        outcome = all_outcomes.setdefault(key, {})
        outcome.setdefault(1, {
            "realization": 1, "status": "success" if base.get("status") == "pass" else "failed",
            "pdr_gate": "pass" if base.get("status") == "pass" else "fail",
            "probe_pdr": base.get("probe_pdr"),
            "background_pdr_median": base.get("background_pdr_median"), "run_id": base.get("run_id", ""),
        })
    summary_rows: list[dict[str, object]] = []
    for family in ("rgg", "ws", "er", "ba"):
        for n in SIZES:
            for protocol in PROTOCOLS:
                values = all_outcomes.get((family, n, protocol), {})
                probes = [number(row.get("probe_pdr")) for row in values.values()]
                backgrounds = [number(row.get("background_pdr_median")) for row in values.values()]
                statuses = {str(row.get("pdr_gate", "fail")) for row in values.values()}
                summary_rows.append({
                    "family": family, "N": n, "protocol": protocol,
                    "operating_role": operating[n]["operating_role"],
                    "available_realizations": len(values),
                    "r1_probe_pdr": fstr(number(values.get(1, {}).get("probe_pdr"))),
                    "r2_probe_pdr": fstr(number(values.get(2, {}).get("probe_pdr"))),
                    "r3_probe_pdr": fstr(number(values.get(3, {}).get("probe_pdr"))),
                    "probe_pdr_sample_sd_ddof1": fstr(sample_sd(probes)),
                    "r1_background_median_pdr": fstr(number(values.get(1, {}).get("background_pdr_median"))),
                    "r2_background_median_pdr": fstr(number(values.get(2, {}).get("background_pdr_median"))),
                    "r3_background_median_pdr": fstr(number(values.get(3, {}).get("background_pdr_median"))),
                    "background_median_pdr_sample_sd_ddof1": fstr(sample_sd(backgrounds)),
                    "pass_fail_disagreement": bool_csv("pass" in statuses and "fail" in statuses),
                    "realization_statuses": ";".join(f"r{k}:{values[k].get('pdr_gate', 'unavailable')}"
                                                       for k in (1, 2, 3) if k in values),
                    "sample_sd_scope": "graph realizations only; not replay seeds",
                })
    write_csv(A4 / "derived_4.3_realizations.csv",
              list(observed_rows[0].keys()) if observed_rows else ["graph_id", "family", "N", "protocol", "realization", "status"],
              observed_rows)
    write_csv(A4 / "derived_4.3_skipped.csv",
              list(skipped[0].keys()) if skipped else ["graph_id", "family", "N", "protocol", "realization", "status", "reason"], skipped)
    write_csv(A4 / "derived_4.3.csv", list(summary_rows[0].keys()), summary_rows)
    refresh_budget_accounting()
    print(f"A4.3 attempted {attempted} replication variants; charged 2% variants={phi2_charge}; cap=72")
    print(f"A4.3 cut {cut_count} eligible replications by preregistered order; sample SD uses available graph realizations only")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: a4.py {4.0|4.1|4.2|4.3}", file=sys.stderr)
        return 2
    graphs, _ = load_a1()
    stage = sys.argv[1]
    try:
        refresh_budget_accounting()
        if stage == "4.0":
            run_4_0(graphs)
        elif stage == "4.1":
            run_4_1(graphs)
        elif stage == "4.2":
            run_4_2(graphs)
        elif stage == "4.3":
            run_4_3(graphs)
        else:
            print(f"Unknown stage: {stage}", file=sys.stderr)
            return 2
    except Exception as exc:
        print(f"A4 {stage} stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
