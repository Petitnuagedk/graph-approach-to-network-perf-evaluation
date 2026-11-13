#!/usr/bin/env python3
"""Continue A4.2 using 60 immutable successes and launching only remaining 30 cells."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
A42 = REPAIR.parent
NS3 = Path("/home/hledirach/Documents/sp1-sp2")
PREREG_SHA256 = "eb13c76136a7c8f9b96377bcccf47ecb2e4c9e5b3a140adac4a76dc12f3104dd"
FROZEN_RUNNER_SHA256 = "a189cb06c224dbaff84c79626ae5736f703f5e843ade7e35aad47827bbbe11ec"
SWEEP_RUNNER_SHA256 = "85f7bd49defd27923793434dd7477573be7d8f4baa4502325f9fa32a14f53aa7"
AODV_SOURCE_SHA256 = "e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e"
AODV_LIBRARY_SHA256 = "31eca374d5d519ea348ed500bf9a263ba40cacac259bbd79ac264078f55ca79a"
GRAPH_SOURCE_SHA256 = "9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433"
GRAPH_BINARY_SHA256 = "4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c"
CHECKPOINT_STOP = '''            if projected_total > 24*3600:\n                raise SystemExit(f"Updated total projection exceeds 24h after {len(per_runs)} attempts")'''
CHECKPOINT_CONTINUE = '''            if projected_total > 24*3600:\n                print(f"AUTHORIZED CONTINUATION: checkpoint projection is {projected_total/3600:.3f} h; continuing under continuation addendum", flush=True)'''


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def verify_identity(path: Path, expected: str) -> None:
    if not path.is_file() or sha(path) != expected:
        raise SystemExit(f"identity mismatch; refusing simulator launch: {path}")


def extend_manifest_with_repair_v1() -> None:
    manifest = HERE / "MANIFEST.sha256"
    lines = manifest.read_text(encoding="utf-8").splitlines()
    prior_manifest = REPAIR / "MANIFEST.sha256"
    lines.append(f"{sha(prior_manifest)}  ../MANIFEST.sha256")
    for row in prior_manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = row.split("  ", 1)
        if relative == "../../../gates.md":
            continue
        lines.append(f"{digest}  ../{relative}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_adapted_stage():
    source_path = A42 / "run_stage.py"
    source = source_path.read_text(encoding="utf-8")
    if source.count(CHECKPOINT_STOP) != 1:
        raise SystemExit("unexpected frozen checkpoint code; refusing continuation")
    adapted = source.replace(CHECKPOINT_STOP, CHECKPOINT_CONTINUE, 1)
    module = types.ModuleType("a42_continuation_stage")
    module.__file__ = str(source_path)
    exec(compile(adapted, str(source_path), "exec"), module.__dict__)
    module.HERE = HERE
    module.PREREG_HASH = PREREG_SHA256
    return module


def main() -> None:
    verify_identity(HERE / "prereg.md", PREREG_SHA256)
    runner_identity = (HERE / "RUNNER.sha256").read_text(encoding="utf-8").strip().split("  ", 1)
    if runner_identity[1] != Path(__file__).name or sha(Path(__file__)) != runner_identity[0]:
        raise SystemExit("continuation runner checksum mismatch; refusing simulator launch")
    verify_identity(A42 / "run_stage.py", FROZEN_RUNNER_SHA256)
    verify_identity(REPAIR / "run_sweep.py", SWEEP_RUNNER_SHA256)
    verify_identity(NS3 / "src/aodv/model/aodv-routing-protocol.cc", AODV_SOURCE_SHA256)
    verify_identity(NS3 / "build/lib/libns3.46.1-aodv-default.so", AODV_LIBRARY_SHA256)
    verify_identity(NS3 / "scratch/graph-run.cc", GRAPH_SOURCE_SHA256)
    verify_identity(NS3 / "build/scratch/ns3.46.1-graph-run-default", GRAPH_BINARY_SHA256)

    if any((HERE / name).exists() for name in ("planned_cells.csv", "per_run.csv", "MANIFEST.sha256")):
        raise SystemExit("continuation outputs already exist; refusing rerun")

    previous_plan = load_csv(REPAIR / "planned_cells.csv")
    previous_runs = load_csv(REPAIR / "per_run.csv")
    projection_rows = load_csv(REPAIR / "runtime_projection_initial.csv")
    projection_meta = json.loads((REPAIR / "projection_initial.json").read_text(encoding="utf-8"))
    if len(previous_plan) != 90 or len(previous_runs) != 60 or len(projection_rows) != 90:
        raise SystemExit("repair-v1 ledgers do not have the expected 90/60/90 row counts")
    if len({r["run_id"] for r in previous_runs}) != 60 or any(r.get("status") != "success" for r in previous_runs):
        raise SystemExit("the 60 prior A4.2 rows must be unique successes")
    if any(r.get("status") != "success" for r in previous_plan[:60]):
        raise SystemExit("prior plan does not mark its first 60 rows successful")
    if any(r.get("status") != "not_attempted_projection_checkpoint_stop" or int(r["N"]) != 162
           for r in previous_plan[60:]):
        raise SystemExit("remaining plan is not exactly the 30 checkpoint-stopped N=162 cells")
    if not projection_meta.get("pass") or not math.isclose(float(projection_meta["projected_total_s"]),
                                                              sum(float(r["projected_wall_s"]) for r in projection_rows),
                                                              rel_tol=0, abs_tol=0.01):
        raise SystemExit("frozen initial projection is missing, failed, or inconsistent")

    stage = load_adapted_stage()
    graphs, _ = stage.load_graphs()
    plan = stage.plan_variants(graphs)
    if [r["run_id"] for r in plan] != [r["run_id"] for r in previous_plan]:
        raise SystemExit("regenerated frozen plan differs from repair-v1 plan")
    if [r["run_id"] for r in previous_runs] != [r["run_id"] for r in previous_plan[:60]]:
        raise SystemExit("prior result order does not match the frozen first 60 cells")

    estimates_by_sequence = {int(r["sequence"]): float(r["projected_wall_s"]) for r in projection_rows}
    if set(estimates_by_sequence) != set(range(1, 91)) or not all(math.isfinite(v) for v in estimates_by_sequence.values()):
        raise SystemExit("the frozen projection table is incomplete or non-finite")
    stage.projection_tables = lambda rows: (projection_rows, [estimates_by_sequence[i] for i in range(1, 91)])
    prior_by_id = {r["run_id"]: r for r in previous_runs}
    original_invoke = stage.invoke

    def invoke_or_reuse(item, graph, frame_path, frame_hash):
        sequence = int(item["sequence"])
        if sequence <= 60:
            old = prior_by_id.get(str(item["run_id"]))
            if old is None or old.get("status") != "success":
                raise RuntimeError(f"missing validated prior success: {item['run_id']}")
            record = dict(old)
            record["output_dir"] = f"../runs/{item['run_id']}"
            return record
        return original_invoke(item, graph, frame_path, frame_hash)

    stage.invoke = invoke_or_reuse
    print("A4.2 continuation authorized: reusing 60 successful cells read-only; only the remaining 30 N=162 cells can launch.", flush=True)
    try:
        stage.run_and_analyze()
    except SystemExit as exc:
        rows = stage.read_csv(HERE / "per_run.csv")
        planned = stage.read_csv(HERE / "planned_cells.csv")
        if rows:
            new_attempts = sum(r.get("status") in ("success", "failed", "timeout", "malformed_output")
                               for r in rows if int(r.get("sequence", 0)) > 60)
            (HERE / "continuation_status.txt").write_text(
                f"Stopped: {exc}\nPrior successful cells reused: 60\nNew continuation attempts: {new_attempts}/30\n"
                f"Total unique plan rows: {len(planned)}\nA4.3: not started\n", encoding="utf-8")
            stage.create_manifest()
            extend_manifest_with_repair_v1()
        raise

    result_rows = stage.read_csv(HERE / "per_run.csv")
    new_attempts = sum(r.get("status") in ("success", "failed", "timeout", "malformed_output")
                       for r in result_rows if int(r.get("sequence", 0)) > 60)
    report = HERE / "report.md"
    text = report.read_text(encoding="utf-8")
    text = text.replace(f"Budget 70+90=160/300", f"Budget 70 prior + 5 repair/diagnostic + 90 unique A4.2 cells = 165/300")
    text = text.replace("[Alpha limitations](../../LIMITATIONS.md)", "[Alpha limitations](../../../../LIMITATIONS.md)")
    text += ("\n\n## Authorized continuation provenance\n\n"
        f"Continuation addendum SHA-256 `{PREREG_SHA256}`. The original 60 successful A4.2 result rows and raw run folders were reused read-only; "
        f"{new_attempts}/30 remaining N=162 cells were newly attempted, with no retries. The 24-hour checkpoint stop was explicitly superseded "
        "for these remaining cells only; the initial projection gate, serial/resource guards, per-run timeout, and all frozen experiment settings remain in force. "
        "Cumulative Alpha charge is 135 plus new continuation attempts; maximum 165/300. A4.3 was not started.\n")
    report.write_text(text, encoding="utf-8")
    stage.create_manifest()
    extend_manifest_with_repair_v1()
    print(f"Continuation finished: {new_attempts}/30 newly attempted; A4.3 not started.", flush=True)


if __name__ == "__main__":
    main()
