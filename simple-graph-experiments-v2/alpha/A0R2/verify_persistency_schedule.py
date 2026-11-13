#!/usr/bin/env python3
"""Check preregistered Boolean-schedule invariance to path persistency."""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "YaDyGaGa"))
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator

rows = []
for stability in (0, .2, .4, .6, .8):
    for seed in range(42, 52):
        schedules = {}
        for persistency in (0, .25, .5, .75, 1):
            result = SPCTimelineBlockGenerator(
                120, .5, stability, seed, pathPersistency=persistency
            ).generate_blocks()
            schedule = "".join("1" if bit else "0" for bit in result["timeline"])
            schedules[persistency] = schedule
            rows.append({
                "stability": stability,
                "seed": seed,
                "persistency": persistency,
                "schedule": schedule,
            })
        assert len(set(schedules.values())) == 1, (stability, seed)
output = HERE / "results" / "persistency_schedule_invariance.csv"
with output.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"verified {len(rows)} combinations across 50 seed/stability schedules")
