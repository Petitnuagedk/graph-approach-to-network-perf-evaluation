#!/usr/bin/env python3
"""Single registered failure-path diagnostic for AODV phi10; no retries."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
A4 = HERE.parents[1]
ADDENDUM_SHA = "694e28b61ab2a026aed07f15c56c98749d31b2b175df04a07d58048d247efb9f"
SOURCE_SHA = "fb1a98f54aeb02be10dc6e4a7715dafad24769add20d1b59e4812e52b2a1883e"
AODV_LIB_SHA = "b1ed4efd90aa1ccd0e55fae2913369cfd9f876098f6b139640a9a75e6900325f"
GRAPH_SOURCE_SHA = "9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433"
GRAPH_BINARY_SHA = "4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c"
FRAME_SHA = "5c090a758d0ffdb3cc7e6fc4739dbddf4c7d389d7d52594fb1bf90586512795d"
TIMEOUT_S = 3600


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def guard() -> tuple[bool, int, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        fields = line.replace(":", "").split()
        if fields[0] in {"MemAvailable", "SwapTotal", "SwapFree"}:
            values[fields[0]] = int(fields[1])
    avail = values["MemAvailable"]
    swap = values["SwapTotal"] - values["SwapFree"]
    return avail >= 8 * 1024 * 1024 and swap == 0, avail, swap


def main() -> None:
    source = NS3 / "src/aodv/model/aodv-routing-protocol.cc"
    lib = NS3 / "build/lib/libns3.46.1-aodv-default.so"
    graph_source = NS3 / "scratch/graph-run.cc"
    binary = NS3 / "build/scratch/ns3.46.1-graph-run-default"
    frames = A4 / "inputs/geodesic_N162_r1__F120.csv"
    checks = ((HERE / "addendum_2.md", ADDENDUM_SHA, "addendum"),
              (source, SOURCE_SHA, "diagnostic AODV source"), (lib, AODV_LIB_SHA, "AODV library"),
              (graph_source, GRAPH_SOURCE_SHA, "graph-run source"),
              (binary, GRAPH_BINARY_SHA, "graph-run executable"), (frames, FRAME_SHA, "frame input"))
    for path, expected, label in checks:
        if not path.is_file() or sha(path) != expected:
            raise SystemExit(f"{label} SHA-256 mismatch; refusing invocation")
    out = HERE / "runs" / "diagnostic_aodv_phi10"
    ledger = HERE / "diagnostic_attempt.csv"
    if out.exists() or ledger.exists():
        raise SystemExit("diagnostic output already exists; no retry")
    allowed, avail, swap = guard()
    out.mkdir(parents=True)
    if not allowed:
        with ledger.open("w", newline="", encoding="utf-8") as stream:
            w = csv.writer(stream, lineterminator="\n")
            w.writerow(["run_id", "status", "resource_guard_available_kb", "resource_guard_swap_used_kb", "error"])
            w.writerow(["diagnostic_aodv_phi10", "resource_guard_blocked", avail, swap, "not launched; no retry"])
        return
    argv = [str(binary), f"--framesCsv={frames}", f"--outDir={out}", "--routing=aodv",
            "--flows=Node_0:Node_51", "--dataRate=50kbps", "--packetSize=1024",
            "--lossThresholdDb=150", "--interpolate=true", "--defaultLossDb=1000000",
            "--txPowerDbm=20", "--linkUpLossDb=10", "--linkDownLossDb=125", "--fps=1",
            "--seed=42", "--warmup=0", "--warmupMode=first", "--instrumentation=true",
            "--flowFraction=0.10000000000000001", "--flowSeed=3717987640",
            "--a3bForwardLog=false", "--dumpRoutes=false"]
    command = ["/usr/bin/time", "-v", "-o", str(out / "time.txt"), *argv]
    (out / "command.json").write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")
    start = time.monotonic()
    exit_code = None
    status = "failed"
    error = ""
    with (out / "ns3.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, cwd=NS3, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True, text=True)
        try:
            exit_code = proc.wait(timeout=TIMEOUT_S)
            status = "success" if exit_code == 0 else "failed"
            if exit_code:
                error = f"simulator returned {exit_code}"
        except subprocess.TimeoutExpired:
            status, error = "timeout", f"exceeded {TIMEOUT_S}s; no retry"
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait()
    wall = time.monotonic() - start
    fields = ["run_id", "status", "exit_code", "process_wall_s", "resource_guard_available_kb",
              "resource_guard_swap_used_kb", "source_sha256", "aodv_library_sha256",
              "graph_source_sha256", "graph_binary_sha256", "frame_sha256", "output_dir", "error"]
    with ledger.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerow({"run_id": "diagnostic_aodv_phi10", "status": status, "exit_code": exit_code,
            "process_wall_s": f"{wall:.9g}", "resource_guard_available_kb": avail,
            "resource_guard_swap_used_kb": swap, "source_sha256": SOURCE_SHA,
            "aodv_library_sha256": AODV_LIB_SHA, "graph_source_sha256": GRAPH_SOURCE_SHA,
            "graph_binary_sha256": GRAPH_BINARY_SHA, "frame_sha256": FRAME_SHA,
            "output_dir": str(out.relative_to(HERE)), "error": error})
    print(f"diagnostic_aodv_phi10: {status}, exit={exit_code}, wall={wall:.3f}s", flush=True)


if __name__ == "__main__":
    main()
