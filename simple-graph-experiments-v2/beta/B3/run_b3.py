#!/usr/bin/env python3
"""B3 ledger materialization and non-simulator preflight.

The run phase is intentionally guarded: this script first freezes the complete
absolute ledger and validates the pinned generator. No ns-3 process is started
by ``plan`` or ``smoke``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import resource
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
A1 = ROOT / "alpha" / "A1" / "results"
B0 = OUT.parent / "B0"
PIN = B0 / "pinned_A0R2_5a497f5"
FEAS = B0 / "feasibility_F300.csv"

sys.path.insert(0, str(PIN))
from yadygaga.frameGenerator import FrameGenerator  # noqa: E402
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator  # noqa: E402
from yadygaga.dynaGraph import SPCDynamicGraph  # noqa: E402

F = 300
PHI = 0.05
WARMUP = 120
POST = 300
POOL_EDGE = 0.5
POOL_TRIALS = 10000
POOL_SEED = 11
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
PROTOCOLS = ("aodv", "olsr")
SEEDS = (42, 43, 44, 45, 46)
LEVELS = tuple(round(i / 10, 1) for i in range(1, 11))
FIELDS = [
    "row_id", "family", "graph_id", "N", "protocol", "seed", "axis", "level",
    "path_life", "stability", "persistency", "U", "D", "K",
    "feasibility_status", "phi", "warmup_s", "sim_time_s", "window_start_s",
    "window_end_s", "p_edge", "trials", "pool_seed", "pool_realization",
    "charged_to", "status",
]
RUN_FIELDS = FIELDS + [
    "status", "start_utc", "end_utc", "elapsed_s", "exit_code", "error",
    "probe_pdr", "background_pdr_median", "background_pdr_p10",
    "raw_output_dir",
]


def rows(path: Path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def feasibility():
    return {(float(r["path_life"]), float(r["stability"])): r for r in rows(FEAS)}


def graph_covariates():
    return {r["graph_id"]: r for r in rows(A1 / "graph_covariates.csv")}


def row_id(family, protocol, seed, axis, level):
    return f"b3_{family}_N42_{protocol}_s{seed}_{axis}_{level:.1f}"


def parameters(axis, level):
    if axis == "life":
        return level, 0.9, 1.0
    if axis == "stability":
        return 0.8, level, 1.0
    if axis == "persistency":
        return 0.8, 0.9, level
    raise ValueError(axis)


def make_plan():
    lookup = feasibility()
    result = []
    for family in FAMILIES:
        graph_id = f"{family}_N42_r1"
        for protocol in PROTOCOLS:
            for seed in SEEDS:
                for axis in ("life", "stability", "persistency"):
                    for level in LEVELS:
                        life, stability, persistency = parameters(axis, level)
                        f = lookup[(life, stability)]
                        is_static = axis == "life" and level == 1.0
                        status = "static_reference" if is_static else f["feasibility_status"]
                        charged = "A4.5" if is_static else "Beta-B3"
                        result.append({
                            "row_id": row_id(family, protocol, seed, axis, level),
                            "family": family, "graph_id": graph_id, "N": 42,
                            "protocol": protocol, "seed": seed, "axis": axis,
                            "level": f"{level:.1f}", "path_life": f"{life:.1f}",
                            "stability": f"{stability:.1f}", "persistency": f"{persistency:.1f}",
                            "U": f["U"], "D": f["D"], "K": f["K"],
                            "feasibility_status": status, "phi": PHI,
                            "warmup_s": WARMUP, "sim_time_s": POST,
                            "window_start_s": WARMUP, "window_end_s": WARMUP + POST,
                            "p_edge": POOL_EDGE, "trials": POOL_TRIALS,
                            "pool_seed": POOL_SEED,
                            "pool_realization": "a0r2_5a497f5_pedge0.5_trials10000_seed11",
                            "charged_to": charged, "status": status,
                        })
    return result


def write_plan(plan):
    path = OUT / "plan_b3.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(plan)
    return path


def load_graph(graph_id):
    graph = nx.Graph()
    graph.add_nodes_from(range(42))
    for r in rows(A1 / "edge_lists" / f"{graph_id}.csv"):
        graph.add_edge(int(r["u"]), int(r["v"]))
    return graph


def smoke(plan):
    cov = graph_covariates()
    assert len(plan) == 1500, len(plan)
    assert sum(r["status"] == "infeasible_not_run" for r in plan) == 350
    assert sum(r["status"] == "static_reference" for r in plan) == 50
    assert sum(r["status"] == "feasible" for r in plan) == 1100
    assert all(float(r["p_edge"]) == POOL_EDGE and int(r["trials"]) == POOL_TRIALS for r in plan)
    assert set(r["family"] for r in plan) == set(FAMILIES)
    for family in FAMILIES:
        graph_id = f"{family}_N42_r1"
        c = cov[graph_id]
        graph = load_graph(graph_id)
        s, d = int(c["probe_S"]), int(c["probe_R"])
        generator = FrameGenerator()
        generator.generateSPCFrames(graph, s, d, trials=POOL_TRIALS, p_edge=POOL_EDGE, seed=POOL_SEED)
        assert generator.path_up_frames and generator.path_down_frames
    # Verify both a feasible and an infeasible exact timeline request.
    feasible = next(r for r in plan if r["status"] == "feasible" and r["axis"] == "life")
    tl = SPCTimelineBlockGenerator(
        F, float(feasible["path_life"]), float(feasible["stability"]), int(feasible["seed"]),
        pathPersistency=float(feasible["persistency"]), behavior="patched",
    ).generate_blocks()
    assert len(tl["timeline"]) == F
    blocked = next(r for r in plan if r["status"] == "infeasible_not_run")
    try:
        SPCTimelineBlockGenerator(
            F, float(blocked["path_life"]), float(blocked["stability"]), int(blocked["seed"]),
            pathPersistency=float(blocked["persistency"]), behavior="patched",
        ).generate_blocks()
    except ValueError:
        pass
    else:
        raise AssertionError("registered infeasible timeline unexpectedly generated")
    return {"status": "smoke_pass", "absolute_rows": len(plan), "feasible_dynamic_rows": 1100, "static_reference_rows": 50, "infeasible_rows": 350, "ns3_started": False}


def utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def memory_guard():
    info = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        info[key] = int(value.strip().split()[0])
    swap_used = info.get("SwapTotal", 0) - info.get("SwapFree", 0)
    if info.get("MemAvailable", 0) < 8 * 1024 * 1024 or swap_used != 0:
        raise RuntimeError(f"memory guard failed: MemAvailable={info.get('MemAvailable')} KiB, swap_used={swap_used} KiB")


def write_frames(graphs, path):
    n = 42
    with path.open("w") as handle:
        handle.write(",".join(f"Node_{i}" for i in range(n)) + "\n")
        for frame_index, graph in enumerate(graphs):
            for i in range(n):
                handle.write(",".join("1" if graph.has_edge(i, j) else "0" for j in range(n)) + "\n")
            if frame_index + 1 < len(graphs):
                handle.write("\n")


def generate_frames(row, cov, cache):
    family = row["family"]
    if family not in cache:
        gid = row["graph_id"]
        graph = load_graph(gid)
        c = cov[gid]
        fg = FrameGenerator()
        fg.generateSPCFrames(graph, int(c["probe_S"]), int(c["probe_R"]), trials=POOL_TRIALS, p_edge=POOL_EDGE, seed=POOL_SEED)
        cache[family] = (fg.path_up_frames, fg.path_down_frames)
    up_pool, down_pool = cache[family]
    timeline = SPCTimelineBlockGenerator(
        F, float(row["path_life"]), float(row["stability"]), int(row["seed"]),
        pathPersistency=float(row["persistency"]), behavior="patched",
    ).generate_blocks()
    dynamic = SPCDynamicGraph().buildDynaGraph(timeline, up_pool, down_pool, seed=int(row["seed"]))
    # A4.5 uses a 120-second warm-up followed by the registered F=300 window.
    warm_graph = load_graph(row["graph_id"])
    return [warm_graph] * WARMUP + dynamic


def run_one(row, cov, cache, worker):
    memory_guard()
    run_id = row["row_id"]
    out = OUT / "runs" / run_id
    if out.exists():
        if (out / "trace_replay_results.csv").is_file() and (out / "flows.csv").is_file():
            # Preserve a completed validation/run; do not charge or rerun it.
            return {**row, "status": "success_existing", "start_utc": "", "end_utc": "",
                    "elapsed_s": "", "exit_code": 0, "error": "",
                    "probe_pdr": "", "background_pdr_median": "", "background_pdr_p10": "",
                    "raw_output_dir": str(out), "worker": worker}
        existing = {p.name for p in out.iterdir()}
        if existing <= {"command.txt", "process.log"}:
            shutil.rmtree(out)
        else:
            raise FileExistsError(f"refusing to overwrite existing run directory: {out}")
    out.mkdir(parents=True, exist_ok=False)
    frame_path = OUT / "frames" / f"{run_id}.csv"
    frame_path.parent.mkdir(exist_ok=True)
    write_frames(generate_frames(row, cov, cache), frame_path)
    c = cov[row["graph_id"]]
    flow_seed = int(hashlib.sha256(f"B3|{row['graph_id']}|{row['seed']}|{row['level']}".encode()).hexdigest()[:8], 16)
    command = ["./ns3", "run", "scratch/graph-run", "--", f"--framesCsv={frame_path}", f"--outDir={out}",
               f"--routing={row['protocol']}", f"--flows=Node_{c['probe_S']}:Node_{c['probe_R']}",
               "--dataRate=50kbps", "--packetSize=1024", "--lossThresholdDb=150", "--interpolate=false",
               "--defaultLossDb=1000000", "--txPowerDbm=20", "--linkUpLossDb=10", "--linkDownLossDb=125",
               "--fps=1", "--seed=42", "--warmup=0", "--warmupMode=first", "--instrumentation=true",
               f"--flowFraction={PHI:.17g}", f"--flowSeed={flow_seed}", "--a3bForwardLog=false", "--dumpRoutes=true"]
    (out / "command.txt").write_text(" ".join(command) + "\n")
    start = utc(); began = time.monotonic()
    with (out / "process.log").open("w") as log:
        completed = subprocess.run(command, cwd="/home/hledirach/Documents/sp1-sp2", stdout=log, stderr=subprocess.STDOUT, check=False)
    elapsed = time.monotonic() - began
    result = dict(row)
    result.update({"status": "success" if completed.returncode == 0 else "failed", "start_utc": start,
                   "end_utc": utc(), "elapsed_s": f"{elapsed:.3f}", "exit_code": completed.returncode,
                   "error": "" if completed.returncode == 0 else f"ns-3 returned {completed.returncode}",
                   "probe_pdr": "", "background_pdr_median": "", "background_pdr_p10": "",
                   "raw_output_dir": str(out), "worker": worker})
    return result


def run_experiments(plan):
    runnable = [r for r in plan if r["status"] == "feasible"]
    cov = graph_covariates()
    cache = {}
    results = []
    # Pool generation is shared only within this process; workers are kept at two.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(run_one, row, cov, cache, i % 2 + 1): row for i, row in enumerate(runnable)}
        for future in as_completed(futures):
            results.append(future.result())
            print(f"completed {results[-1]['row_id']} {results[-1]['status']}", flush=True)
    results.sort(key=lambda r: r["row_id"])
    with (OUT / "per_run.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_FIELDS, extrasaction="ignore")
        writer.writeheader(); writer.writerows(results)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "smoke", "run"))
    parser.add_argument("--limit", type=int, default=None, help="run only the first N feasible rows")
    args = parser.parse_args()
    plan = make_plan()
    path = write_plan(plan)
    if args.command == "plan":
        print(json.dumps({"plan": str(path), "absolute_rows": len(plan), "feasible_dynamic_rows": 1100, "static_reference_rows": 50, "infeasible_rows": 350, "ns3_started": False}, indent=2))
        return
    if args.command == "smoke":
        result = smoke(plan)
        (OUT / "preflight.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return
    if args.limit is not None:
        plan = [r for r in plan if r["status"] == "feasible"][:args.limit]
    results = run_experiments(plan)
    print(json.dumps({"status": "complete", "rows": len(results), "success": sum(r["status"] == "success" for r in results), "ns3_started": True}, indent=2))


if __name__ == "__main__":
    main()
