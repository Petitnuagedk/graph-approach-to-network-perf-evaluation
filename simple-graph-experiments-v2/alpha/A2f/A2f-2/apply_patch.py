from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[2]
PATCH = json.loads((STAGE / "a2f-2.patch.json").read_text())
BASELINE = ROOT / PATCH["baseline_source"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if sys.argv[1:] not in ([], ["--dry-run"]):
        raise SystemExit("usage: apply_patch.py [--dry-run]")
    if sys.argv[1:] != ["--dry-run"]:
        raise SystemExit("only --dry-run is supported; protected and source trees are immutable")
    before = {rel: digest(BASELINE / rel) for rel in PATCH["baseline_sha256"]}
    if before != PATCH["baseline_sha256"]:
        raise SystemExit(f"baseline hash mismatch: {before}")

    with tempfile.TemporaryDirectory(prefix="a2f2-dryrun-") as temp:
        temp_root = Path(temp)
        copied_baseline = temp_root / "baseline"
        shutil.copytree(BASELINE, copied_baseline)
        overlay_pkg = temp_root / "overlay" / "yadygaga"
        overlay_pkg.mkdir(parents=True)
        for relative in PATCH["overlay_files"]:
            source = STAGE / relative
            shutil.copy2(source, overlay_pkg / Path(relative).name)
        env = os.environ.copy()
        env["A2F_BASELINE_SOURCE"] = str(copied_baseline)
        # Import with the fresh overlay first; compare exact output with its clean donor.
        sys.path.insert(0, str(temp_root / "overlay"))
        os.environ.update({"A2F_BASELINE_SOURCE": str(copied_baseline)})
        try:
            from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

            exact = SPCTimelineBlockGenerator(
                120, seed=42, behavior="uk", up_count=60, up_runs=11,
                pathPersistency=0.75,
            ).generate_blocks()
            patched = SPCTimelineBlockGenerator(
                120, 0.5, 1 - 10 / 59, 42, pathPersistency=0.75,
                behavior="patched-v2",
            ).generate_blocks()
            legacy = SPCTimelineBlockGenerator(
                120, 0.5, 0.3, 42, pathPersistency=0.75,
                behavior="legacy",
            ).generate_blocks()
            assert exact == patched
            assert len(legacy["timeline"]) == 120
        finally:
            os.environ.pop("A2F_BASELINE_SOURCE", None)
            sys.path.remove(str(temp_root / "overlay"))
        after = {rel: digest(BASELINE / rel) for rel in PATCH["baseline_sha256"]}
        if after != before:
            raise SystemExit("protected baseline changed during dry-run")
    print(json.dumps({
        "dry_run": "PASS",
        "baseline_hashes_verified": before,
        "patched_v2_and_uk_identical": True,
        "legacy_mode_generated": True,
        "protected_source_mutated": False,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
