"""Materialize the frozen Phase 7B B1 input traces and their hashes."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PHASE1_LADDER = ROOT / "simple-graph-experiments-v2" / "phase1" / "traces" / "static_ladder.csv"
FIXTURES = HERE / "B1" / "fixtures"
sys.path.insert(0, str(ROOT / "simple-graph-experiments-v2" / "phase7" / "7D"))

from generator_v2 import FRAME_COUNT, read_trace, serialize_trace  # noqa: E402


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)

    # Single-hop trace: 30 repetitions of one up frame then one down frame.
    labels = ["S", "R"]
    up = ((0, 1), (1, 0))
    down = ((0, 0), (0, 0))
    synthetic = [up if index % 2 == 0 else down for index in range(FRAME_COUNT)]
    (FIXTURES / "alternating_sr_60.csv").write_bytes(serialize_trace(labels, synthetic))

    # The five-node line is the ordered chain S-A1-A2-A3-R.
    line_labels = ["A1", "A2", "A3", "R", "S"]
    edges = {frozenset(edge) for edge in (("S", "A1"), ("A1", "A2"),
                                          ("A2", "A3"), ("A3", "R"))}
    line = tuple(tuple(int(frozenset((left, right)) in edges) if left != right else 0
                       for right in line_labels) for left in line_labels)
    line_frames = [line] * FRAME_COUNT
    (FIXTURES / "all_up_line_60.csv").write_bytes(serialize_trace(line_labels, line_frames))

    # Re-serialize the already-frozen Phase 1 all-up ladder matrix 60 times.
    ladder_labels, ladder_frames = read_trace(PHASE1_LADDER)
    if len(ladder_frames) != FRAME_COUNT or len(set(ladder_frames)) != 1:
        raise ValueError("Phase 1 ladder input is no longer 60 copies of one matrix")
    ladder_bytes = serialize_trace(ladder_labels, [ladder_frames[0]] * FRAME_COUNT)
    (FIXTURES / "all_up_ladder_60.csv").write_bytes(ladder_bytes)

    source_hash = hashlib.sha256(PHASE1_LADDER.read_bytes()).hexdigest()
    records = {}
    for name in ("alternating_sr_60.csv", "all_up_line_60.csv", "all_up_ladder_60.csv"):
        data = (FIXTURES / name).read_bytes()
        labels_in, matrices = read_trace(FIXTURES / name)
        records[name] = {
            "sha256": hashlib.sha256(data).hexdigest(),
            "source_frame_matrices": len(matrices),
            "node_count": len(labels_in),
            "fps_for_replay": 1.0,
            "warmup_s": 0.0,
        }
    records["all_up_ladder_60.csv"]["source_phase1_ladder_sha256"] = source_hash
    records["all_up_ladder_60.csv"]["source_phase1_path"] = str(PHASE1_LADDER.relative_to(ROOT))
    manifest = {
        "purpose": "Phase 7B B1 frozen inputs",
        "protocol_variants": 0,
        "synthetic_schedule": "30 repetitions: frame 0 up, frame 1 down, alternating",
        "all_up_line_edges": [list(edge) for edge in sorted(edges, key=lambda e: sorted(e))],
        "fixtures": records,
    }
    (FIXTURES / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()