import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "simple-graph-experiments-v2" / "phase7" / "7D"))

from generator_v2 import (  # noqa: E402
    FRAME_COUNT,
    STABILITY_VALUES,
    _up_runs,
    generate_timeline,
    quota_for,
    run_count_for,
)


class GeneratorV2Tests(unittest.TestCase):
    def test_half_up_quota_and_feasible_run_count(self):
        self.assertEqual(quota_for(0.0), 0)
        self.assertEqual(quota_for(0.1), 6)
        self.assertEqual(quota_for(0.5), 30)
        self.assertEqual(quota_for(0.9), 54)
        self.assertEqual(quota_for(1.0), 60)
        for path_life in (0.1, 0.3, 0.5, 0.7, 0.9):
            up = quota_for(path_life)
            runs = run_count_for(up)
            self.assertLessEqual(runs, FRAME_COUNT - up + 1)

    def test_stability_changes_cv_without_changing_fixed_design(self):
        outputs = [
            generate_timeline(0.5, stability, "line", 3)
            for stability in STABILITY_VALUES
        ]
        metadata = [item[1] for item in outputs]
        self.assertEqual({item["measured_up_frames"] for item in metadata}, {30})
        self.assertEqual({item["up_run_count"] for item in metadata}, {6})
        self.assertEqual({item["mean_up_run_frames"] for item in metadata}, {5.0})
        self.assertEqual({item["transition_count"] for item in metadata}, {metadata[0]["transition_count"]})
        cvs = [item["up_run_cv"] for item in metadata]
        self.assertTrue(all(left >= right for left, right in zip(cvs, cvs[1:])))
        self.assertGreaterEqual(cvs[0] - cvs[-1], 0.10)

    def test_realization_changes_schedule_and_repeat_is_deterministic(self):
        first, first_meta = generate_timeline(0.9, 0.8, "ladder", 1)
        repeat, repeat_meta = generate_timeline(0.9, 0.8, "ladder", 1)
        different, _ = generate_timeline(0.9, 0.8, "ladder", 2)
        self.assertEqual(first, repeat)
        self.assertEqual(first_meta, repeat_meta)
        self.assertNotEqual(first, different)
        self.assertEqual(sum(first), 54)
        self.assertEqual(len(_up_runs(first)), run_count_for(54))

    def test_pathlife_endpoints_are_exact_degenerate_timelines(self):
        down, down_meta = generate_timeline(0.0, 0.8, "two-lines", 1)
        up, up_meta = generate_timeline(1.0, 0.8, "two-lines", 1)
        self.assertEqual(down, [False] * FRAME_COUNT)
        self.assertEqual(up, [True] * FRAME_COUNT)
        self.assertEqual(down_meta["measured_uptime"], 0.0)
        self.assertEqual(up_meta["measured_uptime"], 1.0)


if __name__ == "__main__":
    unittest.main()