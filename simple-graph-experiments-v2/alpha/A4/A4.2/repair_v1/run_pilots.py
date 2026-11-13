#!/usr/bin/env python3
"""Once-only execution of the three preregistered missing A4.0A pilots."""
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
A4 = HERE.parents[1]
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
PYTHON = Path("/home/hledirach/Documents/J2/.venv/bin/python")
PREREG_SHA = "5d203dc1f1201f2d5f06512d1653d6eb2ba3a77cb6226f6af35eaf378ce3058e"
SOURCE_SHA = "9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433"
BINARY_SHA = "4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c"
FRAME_SHA = "5c090a758d0ffdb3cc7e6fc4739dbddf4c7d389d7d52594fb1bf90586512795d"
TIMEOUT_S = 3600

PILOTS = (
    ("repair_v1_olsr_phi1", "olsr", "phi1", 0.01, 162343213),
    ("repair_v1_olsr_phi10", "olsr", "phi10", 0.10, 3717987640),
    ("repair_v1_aodv_phi10", "aodv", "phi10", 0.10, 3717987640),
)
FIELDS = ["run_id", "protocol", "load_role", "phi", "status", "exit_code", "process_wall_s",
          "peak_rss_kb", "resource_guard_available_kb", "resource_guard_swap_used_kb", "output_dir",
          "source_sha256", "binary_sha256", "frame_sha256", "command", "error"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_rows(rows: list[dict[str, object]]) -> None:
    with (HERE / "repair_pilots.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def resource_guard() -> tuple[bool, int, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        parts = line.replace(":", "").split()
        if parts[0] in {"MemAvailable", "SwapTotal", "SwapFree"}:
            values[parts[0]] = int(parts[1])
    available = values["MemAvailable"]
    swap_used = values["SwapTotal"] - values["SwapFree"]
    return available >= 8 * 1024 * 1024 and swap_used == 0, available, swap_used


def main() -> None:
    prereg = HERE / "prereg.md"
    frames = A4 / "inputs" / "geodesic_N162_r1__F120.csv"
    binary = NS3 / "build" / "scratch" / "ns3.46.1-graph-run-default"
    source = NS3 / "scratch" / "graph-run.cc"
    if sha(prereg) != PREREG_SHA:
        raise SystemExit("repair-v1 preregistration hash mismatch; refusing simulator invocation")
    for path, expected, label in ((source, SOURCE_SHA, "source"), (binary, BINARY_SHA, "binary"),
                                  (frames, FRAME_SHA, "frame input")):
        if not path.is_file() or sha(path) != expected:
            raise SystemExit(f"{label} identity mismatch; refusing simulator invocation")
    if (HERE / "repair_pilots.csv").exists() or (HERE / "runs").exists():
        raise SystemExit("repair-pilot outputs already exist; no rerun")
    (HERE / "runs").mkdir(parents=True)
    rows: list[dict[str, object]] = []
    write_rows(rows)
    for run_id, protocol, role, phi, flow_seed in PILOTS:
        allowed, available, swap = resource_guard()
        out = HERE / "runs" / run_id
        if out.exists():
            raise SystemExit(f"pre-existing pilot output path: {out}")
        if not allowed:
            rows.append({"run_id": run_id, "protocol": protocol, "load_role": role, "phi": phi,
                "status": "resource_guard_blocked", "exit_code": "", "process_wall_s": "",
                "peak_rss_kb": "", "resource_guard_available_kb": available,
                "resource_guard_swap_used_kb": swap, "output_dir": str(out.relative_to(HERE)),
                "source_sha256": SOURCE_SHA, "binary_sha256": BINARY_SHA, "frame_sha256": FRAME_SHA,
                "command": "", "error": "guard failed; not launched; stop pilot block"})
            write_rows(rows)
            return
        out.mkdir(parents=True)
        argv = [str(binary), f"--framesCsv={frames}", f"--outDir={out}", f"--routing={protocol}",
            "--flows=Node_0:Node_51", "--dataRate=50kbps", "--packetSize=1024", "--lossThresholdDb=150",
            "--interpolate=true", "--defaultLossDb=1000000", "--txPowerDbm=20", "--linkUpLossDb=10",
            "--linkDownLossDb=125", "--fps=1", "--seed=42", "--warmup=0", "--warmupMode=first",
            "--instrumentation=true", f"--flowFraction={phi:.17g}", f"--flowSeed={flow_seed}",
            "--a3bForwardLog=false", "--dumpRoutes=false"]
        command = ["/usr/bin/time", "-v", "-o", str(out / "time.txt"), *argv]
        (out / "command.txt").write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")
        started = time.monotonic()
        status, exit_code, error = "failed", None, ""
        with (out / "ns3.log").open("w", encoding="utf-8") as log:
            try:
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
            except OSError as exc:
                status, exit_code, error = "failed", -1, f"{type(exc).__name__}: {exc}"
        wall = time.monotonic() - started
        time_text = (out / "time.txt").read_text(encoding="utf-8", errors="replace") if (out / "time.txt").exists() else ""
        rss = ""
        for line in time_text.splitlines():
            if line.startswith("Maximum resident set size (kbytes):"):
                rss = line.split(":", 1)[1].strip()
                break
        rows.append({"run_id": run_id, "protocol": protocol, "load_role": role, "phi": phi,
            "status": status, "exit_code": exit_code, "process_wall_s": f"{wall:.9g}", "peak_rss_kb": rss,
            "resource_guard_available_kb": available, "resource_guard_swap_used_kb": swap,
            "output_dir": str(out.relative_to(HERE)), "source_sha256": SOURCE_SHA, "binary_sha256": BINARY_SHA,
            "frame_sha256": FRAME_SHA, "command": json.dumps(command), "error": error})
        write_rows(rows)
        print(f"{len(rows)}/3 {run_id}: {status}, wall={wall:.3f}s", flush=True)


if __name__ == "__main__":
    main()
