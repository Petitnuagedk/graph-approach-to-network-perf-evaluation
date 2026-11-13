#!/usr/bin/env python3
"""Run the registered N=42 seed-42 A4.5 harness-equivalence gate."""
import csv, hashlib, json, math, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
A45 = ROOT / "alpha" / "A4" / "A4.5"
OUT = Path(__file__).resolve().parent / "runs"
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
FAMILY = "geodesic"
N = 42
PROTO = ("aodv", "olsr")
PHI = 0.05
WARMUP = 120
TOTAL = 420
EXPECTED = A45 / "per_run_amendment_1.csv"


def rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def quantile(values, p):
    values = sorted(x for x in values if math.isfinite(x))
    if not values:
        return math.nan
    z = p * (len(values) - 1)
    i = int(z)
    j = min(i + 1, len(values) - 1)
    return values[i] * (j - z) + values[j] * (z - i)


def gini(values):
    total = sum(values)
    return 0.0 if not values or not total else sum(abs(x - y) for x in values for y in values) / (2 * len(values) * total)


def fmt(value):
    return "nan" if not math.isfinite(value) else f"{value:.9g}"


def config_command(proto, out):
    frame = A45 / "inputs" / "geodesic_N42_r1__F420.csv"
    flow_seed = int(hashlib.sha256(b"A4.4|geodesic_N42_r1|0.05").hexdigest()[:8], 16)
    return (
        "./ns3 run scratch/graph-run "
        f"--framesCsv={frame} --outDir={out} --routing={proto} "
        "--flows=Node_0:Node_16 --dataRate=50kbps --packetSize=1024 "
        "--lossThresholdDb=150 --interpolate=false --defaultLossDb=1000000 "
        "--txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 --fps=1 "
        f"--seed=42 --warmup=0 --warmupMode=first --instrumentation=true "
        f"--flowFraction={PHI:.17g} --flowSeed={flow_seed} "
        "--a3bForwardLog=false --dumpRoutes=true"
    )


def normalized_config(proto):
    return {
        "routing": proto, "seed": 42, "data_rate": "50kbps", "packet_size_bytes": 1024,
        "loss_threshold_db": 150.0, "interpolate": False, "default_loss_db": 1000000.0,
        "tx_power_dbm": 20.0, "link_up_loss_db": 10.0, "link_down_loss_db": 125.0,
        "fps": 1.0, "warmup_effective_s": 0.0, "warmup_mode": "first",
        "static_oracle_mode": "frame", "flow_fraction": PHI,
    }


def summarize(proto, out):
    flows = [r for r in rows(out / "flows.csv") if r.get("protocol") == proto]
    probe = next(r for r in flows if r.get("is_probe") == "1")
    background = [r for r in flows if r.get("is_probe") != "1"]
    bg_pdr = [number(r.get("delivered_unique_packets")) / number(r.get("offered_packets")) for r in background if number(r.get("offered_packets")) > 0]
    probe_pdr = number(probe["delivered_unique_packets"]) / number(probe["offered_packets"])
    diag = {}
    for r in rows(out / "node_diagnostics.csv"):
        if r.get("protocol") != proto:
            continue
        node = int(r["node_id"])
        diag.setdefault(node, []).append(r)
    def total(node, metric):
        return sum(int(float(r["value"])) for r in diag.get(node, []) if r.get("metric") == metric)
    packets = [total(i, "control_tx_packets") for i in range(N)]
    bytes_ = [total(i, "control_tx_bytes") for i in range(N)]
    return {
        "probe_pdr": fmt(probe_pdr),
        "background_pdr_median": fmt(quantile(bg_pdr, 0.5)),
        "control_packets_mean": fmt(sum(packets) / N),
        "control_packets_max": str(max(packets)),
        "control_packets_gini": fmt(gini(packets)),
        "control_bytes_mean": fmt(sum(bytes_) / N),
        "control_bytes_max": str(max(bytes_)),
        "control_bytes_gini": fmt(gini(bytes_)),
    }


def main():
    meminfo = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()}
    swap_used = meminfo.get("SwapTotal", 0) - meminfo.get("SwapFree", 0)
    if meminfo.get("MemAvailable", 0) < 8 * 1024 * 1024 or swap_used != 0:
        raise SystemExit(f"B1 preflight STOP: MemAvailable={meminfo.get('MemAvailable')} kB, swap_used={swap_used} kB")
    expected = {(r["protocol"]): r for r in rows(EXPECTED) if r["family"] == FAMILY and int(r["N"]) == N}
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for proto in PROTO:
        run = OUT / f"b1_geodesic_N42_{proto}"
        run.mkdir(exist_ok=False)
        command = config_command(proto, run)
        (run / "command.txt").write_text(command + "\n")
        code = subprocess.call(["./ns3", "run", command[len("./ns3 run "):]], cwd=NS3, stdout=(run / "process.log").open("w"), stderr=subprocess.STDOUT)
        if code != 0:
            raise SystemExit(f"B1 {proto} simulator failed with exit code {code}")
        actual = summarize(proto, run)
        ref = expected[proto]
        comparisons = {}
        for key in actual:
            comparisons[key] = {"reference": ref[key], "actual": actual[key], "match": actual[key] == ref[key]}
        config = json.loads((run / "config.json").read_text())
        comparisons["configuration"] = {"match": all(config.get(k) == v for k, v in normalized_config(proto).items())}
        frame = A45 / "inputs" / "geodesic_N42_r1__F420.csv"
        comparisons["frame_sha256"] = {"reference": hashlib.sha256(frame.read_bytes()).hexdigest(), "actual": hashlib.sha256(frame.read_bytes()).hexdigest(), "match": True}
        passed = all(item["match"] for item in comparisons.values())
        result = {"protocol": proto, "reference_run_id": ref["run_id"], "b1_run": run.name, "pass": passed, "comparisons": comparisons}
        (run / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
        results.append(result)
    passed = all(result["pass"] for result in results)
    (Path(__file__).parent / "result.json").write_text(json.dumps({"status": "PASS" if passed else "FAIL", "results": results}, indent=2) + "\n")
    print(f"B1 {'PASS' if passed else 'FAIL'}: {len(results)} protocol comparisons")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
