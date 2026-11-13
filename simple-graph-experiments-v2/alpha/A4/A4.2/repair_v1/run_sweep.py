#!/usr/bin/env python3
"""Run frozen A4.2 logic in repair-v1 outputs with amended pilot endpoints."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "run_stage.py"
PREREG_SHA = "5d203dc1f1201f2d5f06512d1653d6eb2ba3a77cb6226f6af35eaf378ce3058e"
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
EXPECTED_AODV_SOURCE = "e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e"
EXPECTED_AODV_LIBRARY = "31eca374d5d519ea348ed500bf9a263ba40cacac259bbd79ac264078f55ca79a"
EXPECTED_GRAPH_SOURCE = "9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433"
EXPECTED_GRAPH_BINARY = "4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_stage():
    spec = importlib.util.spec_from_file_location("a42_frozen_stage", ORIGINAL)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the frozen A4.2 stage runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    prereg = HERE / "prereg.md"
    if sha(prereg) != PREREG_SHA:
        raise SystemExit("repair-v1 preregistration hash mismatch; refusing A4.2 launch")
    identities = ((NS3 / "src/aodv/model/aodv-routing-protocol.cc", EXPECTED_AODV_SOURCE),
                  (NS3 / "build/lib/libns3.46.1-aodv-default.so", EXPECTED_AODV_LIBRARY),
                  (NS3 / "scratch/graph-run.cc", EXPECTED_GRAPH_SOURCE),
                  (NS3 / "build/scratch/ns3.46.1-graph-run-default", EXPECTED_GRAPH_BINARY))
    for path, expected in identities:
        if not path.is_file() or sha(path) != expected:
            raise SystemExit(f"simulator identity mismatch at {path}; refusing all A4.2 launches")
    with (HERE / "repair_pilots.csv").open(newline="", encoding="utf-8") as stream:
        repair_pilots = list(csv.DictReader(stream))
    with (HERE / "corrected_aodv_pilot.csv").open(newline="", encoding="utf-8") as stream:
        corrected_pilot = list(csv.DictReader(stream))
    required = {("olsr", "phi1"), ("olsr", "phi10")}
    if len(repair_pilots) != 3 or any(row.get("status") != "success" for row in repair_pilots if row["protocol"] == "olsr"):
        raise SystemExit("both once-only OLSR replacement pilots must succeed; A4.2 remains blocked")
    if {(row["protocol"], row["load_role"]) for row in repair_pilots if row["protocol"] == "olsr"} != required:
        raise SystemExit("OLSR replacement pilot ledger does not match registered endpoints")
    if len(corrected_pilot) != 1 or corrected_pilot[0].get("status") != "success":
        raise SystemExit("corrected AODV phi10 pilot must succeed; A4.2 remains blocked")
    if (corrected_pilot[0].get("run_id") != "corrected_aodv_phi10"):
        raise SystemExit("corrected AODV pilot ledger identity mismatch")

    stage = load_stage()
    stage.HERE = HERE
    stage.PREREG_HASH = PREREG_SHA
    original_projection_tables = stage.projection_tables

    def projection_tables(plan):
        # Preserve the frozen A4.1 baseline and formula; override only the three
        # previously missing successful A4.0A protocol/load pilot endpoints.
        pilots = [r for r in repair_pilots if r["protocol"] == "olsr"] + [{
            "protocol": "aodv", "load_role": "phi10", "process_wall_s": corrected_pilot[0]["process_wall_s"]}]
        pilot_by_endpoint = {(r["protocol"], r["load_role"]): r for r in pilots}
        p41 = {r["run_id"]: r for r in stage.read_csv(stage.A4 / "runs.csv")
               if r.get("stage") == "4.1"}
        p40 = {(r["protocol"], r["load_role"]): r for r in stage.read_csv(stage.A4 / "runs.csv")
               if r.get("stage") == "4.0A" and r.get("status") == "success"}
        for key, row in pilot_by_endpoint.items():
            p40[key] = row
        rows = []
        estimates = []
        for item in plan:
            rid = f"41_{item['graph_id']}_{item['protocol']}_probe"
            base = stage.num(p41.get(rid, {}).get("process_wall_s"))
            low = stage.num(p40.get((item["protocol"], "phi1"), {}).get("process_wall_s"))
            high = stage.num(p40.get((item["protocol"], "phi10"), {}).get("process_wall_s"))
            n = int(item["N"])
            f1 = stage.a4.llround(.01 * n * (n - 1) / 2)
            f10 = stage.a4.llround(.10 * n * (n - 1) / 2)
            count = int(item["n_background"])
            missing = []
            if not math.isfinite(base):
                missing.append("A4.1 baseline")
            if not math.isfinite(low):
                missing.append("successful A4.0A/replacement phi1 pilot")
            if not math.isfinite(high):
                missing.append("successful A4.0A/replacement phi10 pilot")
            if not all(math.isfinite(x) for x in (base, low, high)) or low <= 0:
                estimate = math.inf
                status = "unavailable: " + "; ".join(missing)
            else:
                fraction = (count - f1) / max(1, f10 - f1)
                multiplier = max(1.0, 1.0 + fraction * (high / low - 1.0))
                estimate = max(0.0, base) * multiplier
                status = "estimated_with_registered_replacement_pilot"
            estimates.append(estimate)
            rows.append({"sequence": item["sequence"], "run_id": item["run_id"],
                "baseline_4_1_process_wall_s": stage.fmt(base), "pilot_phi1_s": stage.fmt(low),
                "pilot_phi10_s": stage.fmt(high),
                "load_multiplier": stage.fmt(estimate / base) if math.isfinite(estimate) and base > 0 else "nan",
                "projected_wall_s": stage.fmt(estimate), "projection_status": status,
                "phi1_endpoint_source": "A4.0A original success" if (item["protocol"], "phi1") not in pilot_by_endpoint else "repair-v1 replacement",
                "phi10_endpoint_source": "repair-v1 replacement" if (item["protocol"], "phi10") in pilot_by_endpoint else "A4.0A original success"})
        return rows, estimates

    stage.projection_tables = projection_tables
    def versioned_projection_stop(plan, estimates, reason):
        for row in plan:
            row["status"] = "not_attempted_projection_gate"
            row["error"] = reason
        stage.write_csv(HERE / "planned_cells.csv", plan)
        stage.write_csv(HERE / "runtime_projection_initial.csv", [
            {"sequence": row["sequence"], "run_id": row["run_id"],
             "projected_wall_s": stage.fmt(estimates[int(row["sequence"]) - 1]),
             "projection_status": "estimated_or_unavailable"} for row in plan])
        total = sum(estimates) if all(math.isfinite(x) for x in estimates) else None
        (HERE / "projection_initial.json").write_text(json.dumps({"planned_variants": 90,
            "projection_complete": total is not None, "projected_total_s": total,
            "projected_total_h": total / 3600 if total is not None else None,
            "limit_h": 24, "pass": bool(total is not None and total <= 24 * 3600),
            "stop_reason": reason}, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (HERE / "report.md").write_text("# A4.2 repair-v1 projection stop\n\n"
            f"No A4.2 simulator variants were launched. Repair preregistration SHA-256 `{PREREG_SHA}`. "
            f"Projection gate result: {reason}. Planned statuses are preserved in [planned_cells.csv](planned_cells.csv). "
            "Historical stop and all pilot attempts remain preserved. No A4.3 was started.\n", encoding="utf-8")

    stage.write_projection_stop = versioned_projection_stop
    try:
        stage.run_and_analyze()
    except SystemExit:
        if (HERE / "projection_initial.json").is_file() and not (HERE / "MANIFEST.sha256").exists():
            stage.create_manifest()
        raise

    attempted = sum(row.get("status") in ("success", "failed", "timeout", "malformed_output")
                    for row in stage.read_csv(HERE / "per_run.csv"))
    report_path = HERE / "report.md"
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        old = f"Budget 70+{attempted}={70 + attempted}/300"
        new = f"Budget 70+3 replacement pilots+1 diagnostic+1 corrected pilot+{attempted}={75 + attempted}/300"
        report = report.replace(old, new)
        report += ("\n\n## Repair-v1 provenance and accounting\n\n"
            f"This completion uses repair addendum SHA-256 `{PREREG_SHA}`. The historical projection stop remains preserved at `../report.md`; "
            "the two OLSR replacement endpoints are from repair-v1, and the AODV phi10 endpoint is from the separately preregistered bounded-retry correction. "
            "Historical failed attempts remain failed. Ledgers: [repair_pilots.csv](repair_pilots.csv), [corrected_aodv_pilot.csv](corrected_aodv_pilot.csv). "
            f"Repair-v1 replacement attempts: 3/3; diagnostic: 1/1; corrected AODV pilot: 1/1. "
            f"A4.2 sweep attempts: {attempted}/90. Cumulative Alpha charge: {75 + attempted}/300. "
            "The diagnostic measured RREQ count 32 against configured retry limit 2; signed `1 << 31` overflow yielded a negative timer. "
            "The corrected AODV build bounds the backoff exponent and treats counts ≥ the retry limit as terminal; all AODV sweep variants use this build, OLSR remains unchanged. "
            "No A4.3, detector/warm-up change, DSDV reinstatement, or additional cell disposition was started.\n")
        report = report.replace("[Alpha limitations](../../LIMITATIONS.md)", "[Alpha limitations](../../../LIMITATIONS.md)")
        report_path.write_text(report, encoding="utf-8")
    stage.create_manifest()


if __name__ == "__main__":
    main()
