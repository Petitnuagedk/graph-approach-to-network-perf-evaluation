#!/usr/bin/env python3
"""Enumerate infeasible cells and verify selectable later-upstream behavior."""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "YaDyGaGa"))
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

LIVES = (0.1, 0.3, 0.5, 0.7, 0.9)
STABILITIES = (0.0, 0.4, 0.8)
FRAMES = (60, 120)
rows = []
for frames in FRAMES:
    for life in LIVES:
        for stability in STABILITIES:
            up = max(0, min(frames, int(round(frames * life))))
            down = frames - up
            runs = (0 if up == 0 else 1) if up in (0, frames) else max(
                1, min(up, int(round(1 + (1 - stability) * (up - 1))))
            )
            infeasible = 0 < up < frames and runs > down + 1
            realized = None
            legacy_up = None
            outcome = "not-run: feasible"
            if infeasible:
                try:
                    result = SPCTimelineBlockGenerator(
                        frames, life, stability, 42, behavior="legacy"
                    ).generate_blocks()
                    bits = result["timeline"]
                    realized = sum(
                        bit and (index == 0 or not bits[index - 1])
                        for index, bit in enumerate(bits)
                    )
                    legacy_up = sum(bits)
                    outcome = "returned"
                except Exception as error:
                    outcome = type(error).__name__ + ": " + str(error)
            rows.append({
                "frames": frames, "life": life, "stability": stability,
                "up_count": up, "down_count": down, "requested_up_runs": runs,
                "feasible_exact": not infeasible,
                "later_head_capped_run_target": min(runs, down + 1),
                "later_head_legacy_realized_up_runs": realized,
                "legacy_realized_up_count": legacy_up,
                "legacy_outcome": outcome,
            })
out = HERE / "results"
out.mkdir(exist_ok=True)
with (out / "infeasibility_map.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(out / "infeasibility_map.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps([r for r in rows if not r["feasible_exact"]], indent=2))
