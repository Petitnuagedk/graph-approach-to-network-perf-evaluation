#!/usr/bin/env python3
"""Resume A4.2 after continuation-v2 without rerunning consumed attempts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent / "continuation_v2"
REPAIR = HERE.parent
A42 = REPAIR.parent
NS3 = Path("/home/hledirach/Documents/sp1-sp2")

PREREG_SHA256 = "9d930ed156a83b787e89279507bc0084fe019e4ef4cc6f48c70c5aa24575afc8"
FROZEN_RUNNER_SHA256 = "a189cb06c224dbaff84c79626ae5736f703f5e843ade7e35aad47827bbbe11ec"
V2_RUNNER_SHA256 = "2757a611c9b54354f5603ba8cb269896760474a2cb0d789cc67a63de22f23e16"
AODV_SOURCE_SHA256 = "e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e"
AODV_LIBRARY_SHA256 = "31eca374d5d519ea348ed500bf9a263ba40cacac259bbd79ac264078f55ca79a"
GRAPH_SOURCE_SHA256 = "9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433"
GRAPH_BINARY_SHA256 = "4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def verify_identity(path: Path, expected: str) -> None:
    if not path.is_file() or sha(path) != expected:
        raise SystemExit(f"identity mismatch: {path}")


def verify_runner_checksum() -> None:
    fields = (HERE / "RUNNER.sha256").read_text(encoding="utf-8").split()
    if not fields or fields[0] != sha(HERE / "resume_from_v2_corrected.py"):
        raise SystemExit("runner checksum mismatch")


def load_stage():
    source_path = A42 / "run_stage.py"
    source = source_path.read_text(encoding="utf-8")
    # The user-authorized continuation supersedes the frozen 24-hour checkpoint.
    source = source.replace(
        "        if len(per_runs) in (15, 60):",
        "        if False and len(per_runs) in (15, 60):",
        1,
    )
    # Make reuse and new launches unambiguous in stdout.
    source = source.replace(
        '        print(f"[{len(per_runs):02d}/90] {item[\'run_id\']} {record[\'status\']} wall={record.get(\'process_wall_s\')} s", flush=True)',
        '        seq = index + 1\n'
        '        label = f"reused {seq:02d}/63" if seq <= 63 else f"new {seq - 63:02d}/27 (plan {seq:02d}/90)"\n'
        '        print(f"[{label}] {item[\'run_id\']} {record[\'status\']} wall={record.get(\'process_wall_s\')} s", flush=True)',
        1,
    )
    if "        if len(per_runs) in (15, 60):" in source:
        raise SystemExit("failed to disable frozen checkpoint")
    if '        print(f"[{len(per_runs):02d}/90]' in source:
        raise SystemExit("failed to replace frozen progress output")
    module = types.ModuleType("a42_continuation_v4_stage")
    module.__file__ = str(source_path)
    exec(compile(source, str(source_path), "exec"), module.__dict__)
    module.HERE = HERE
    module.PREREG_HASH = PREREG_SHA256
    return module


def validate_v2(plan: list[dict[str, str]], runs: list[dict[str, str]]) -> None:
    if len(plan) != 90 or len(runs) != 64:
        raise SystemExit("unexpected continuation-v2 row counts")
    by_seq = {int(row["sequence"]): row for row in plan}
    if any(by_seq[seq]["status"] != "success" for seq in range(1, 61)):
        raise SystemExit("continuation-v2 first 60 rows not all successful")
    if any(by_seq[seq]["status"] != "timeout" for seq in (61, 62, 63)):
        raise SystemExit("continuation-v2 expected timeouts at rows 61-63")
    if by_seq[64]["status"] != "resource_guard_blocked":
        raise SystemExit("continuation-v2 expected guard block at row 64")
    if any(by_seq[seq]["status"] != "not_attempted_guard_stop" for seq in range(65, 91)):
        raise SystemExit("continuation-v2 expected guard-stop marks at rows 65-90")


def main() -> None:
    verify_runner_checksum()
    verify_identity(A42 / "run_stage.py", FROZEN_RUNNER_SHA256)
    verify_identity(V2 / "continue_remaining.py", V2_RUNNER_SHA256)
    verify_identity(NS3 / "src/aodv/model/aodv-routing-protocol.cc", AODV_SOURCE_SHA256)
    verify_identity(NS3 / "build/lib/libns3.46.1-aodv-default.so", AODV_LIBRARY_SHA256)
    verify_identity(NS3 / "scratch/graph-run.cc", GRAPH_SOURCE_SHA256)
    verify_identity(NS3 / "build/scratch/ns3.46.1-graph-run-default", GRAPH_BINARY_SHA256)

    if any((HERE / name).exists() for name in ("planned_cells.csv", "per_run.csv", "MANIFEST.sha256")):
        raise SystemExit("continuation-v4 outputs already exist")

    v2_plan = load_csv(V2 / "planned_cells.csv")
    v2_runs = load_csv(V2 / "per_run.csv")
    validate_v2(v2_plan, v2_runs)
    projection_rows = load_csv(V2 / "runtime_projection_initial.csv")
    projection_meta = json.loads((V2 / "projection_initial.json").read_text(encoding="utf-8"))
    if len(projection_rows) != 90 or not projection_meta.get("pass"):
        raise SystemExit("missing valid initial projection data")

    stage = load_stage()
    graphs, _ = stage.load_graphs()
    plan = stage.plan_variants(graphs)
    v2_plan_by_seq = {int(row["sequence"]): row for row in v2_plan}
    if [item["run_id"] for item in plan] != [v2_plan_by_seq[i]["run_id"] for i in range(1, 91)]:
        raise SystemExit("frozen plan mismatch versus continuation-v2")

    estimates_by_seq = {int(row["sequence"]): float(row["projected_wall_s"]) for row in projection_rows}
    if set(estimates_by_seq) != set(range(1, 91)) or not all(math.isfinite(value) for value in estimates_by_seq.values()):
        raise SystemExit("invalid projection table")
    stage.projection_tables = lambda rows: (projection_rows, [estimates_by_seq[i] for i in range(1, 91)])

    v2_run_by_id = {row["run_id"]: row for row in v2_runs}
    original_invoke = stage.invoke

    def invoke_or_reuse(item, graph, frame_path, frame_hash):
        seq = int(item["sequence"])
        if seq <= 63:
            prior = dict(v2_run_by_id[item["run_id"]])
            prior["output_dir"] = str((V2 / prior.get("output_dir", "")).resolve()) if prior.get("output_dir") else ""
            return prior
        # Row 64 is deliberately eligible now: it was guard-blocked, not launched.
        return original_invoke(item, graph, frame_path, frame_hash)

    stage.invoke = invoke_or_reuse
    print("A4.2 continuation-v4: reusing rows 1-63; launching only unlaunched rows 64-90.", flush=True)
    stage.run_and_analyze()


if __name__ == "__main__":
    main()
