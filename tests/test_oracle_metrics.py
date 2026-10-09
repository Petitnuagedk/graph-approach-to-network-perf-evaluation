#!/usr/bin/env python3
"""Hand-built oracle-metric regression check with analytically known results."""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from oracle_metrics import (
    compute_deadline_pdr,
    compute_oracle_metrics,
    compute_traffic_window_usable_uptime,
    is_time_connected,
)


def graph_with_edges(node_count, edges):
    matrix = [[0] * node_count for _ in range(node_count)]
    for left, right in edges:
        matrix[left][right] = matrix[right][left] = 1
    return matrix


class OracleMetricsTest(unittest.TestCase):
    def test_known_connectivity_runs_and_alternative_route_retention(self):
        route_a = [(0, 1), (1, 3)]
        route_b = [(0, 2), (2, 3)]
        both = route_a + route_b
        frames = [
            graph_with_edges(4, both),
            graph_with_edges(4, both),
            graph_with_edges(4, []),
            graph_with_edges(4, route_b),
            graph_with_edges(4, route_b),
            graph_with_edges(4, both),
        ]

        metrics = compute_oracle_metrics(frames, source=0, destination=3)

        self.assertAlmostEqual(metrics["uptime_ratio"], 5 / 6)
        self.assertEqual(metrics["up_runs_s"], [2.0, 3.0])
        self.assertEqual(metrics["outage_durations_s"], [1.0])
        self.assertEqual(metrics["transition_count"], 2)
        self.assertTrue(metrics["has_alternative_paths"])
        self.assertAlmostEqual(metrics["path_identity_retention"], 2 / 3)
        self.assertAlmostEqual(metrics["mean_up_run_s"], 2.5)
        self.assertAlmostEqual(metrics["median_up_run_s"], 2.5)
        self.assertAlmostEqual(metrics["p90_up_run_s"], 2.9)

    def test_retention_is_nan_without_alternative_paths(self):
        frames = [graph_with_edges(3, [(0, 1), (1, 2)])] * 2
        metrics = compute_oracle_metrics(frames, source=0, destination=2)
        self.assertFalse(metrics["has_alternative_paths"])
        self.assertTrue(math.isnan(metrics["path_identity_retention"]))

    def test_interpolated_usable_uptime_matches_loss_threshold_crossings(self):
        down = graph_with_edges(2, [])
        up = graph_with_edges(2, [(0, 1)])
        frames = [down, up, down]

        interpolated = compute_traffic_window_usable_uptime(
            frames, source=0, destination=1, traffic_start_s=0.0,
            traffic_stop_s=2.0, interpolate=True,
        )
        held = compute_traffic_window_usable_uptime(
            frames, source=0, destination=1, traffic_start_s=0.0,
            traffic_stop_s=2.0, interpolate=False,
        )

        self.assertAlmostEqual(interpolated["frame_uptime_ratio"], 0.5)
        self.assertAlmostEqual(interpolated["usable_uptime_ratio"], 111 / 115)
        self.assertEqual(len(interpolated["usable_up_intervals_s"]), 1)
        self.assertAlmostEqual(interpolated["usable_up_intervals_s"][0][0], 4 / 115)
        self.assertAlmostEqual(interpolated["usable_up_intervals_s"][0][1], 1 + 111 / 115)
        self.assertAlmostEqual(held["usable_uptime_ratio"], 0.5)

    def test_traffic_window_clips_boundary_frames(self):
        up = graph_with_edges(2, [(0, 1)])
        down = graph_with_edges(2, [])

        metrics = compute_traffic_window_usable_uptime(
            [up, down], source=0, destination=1, traffic_start_s=0.1,
            traffic_stop_s=1.0, interpolate=False,
        )

        self.assertAlmostEqual(metrics["traffic_window_s"], 0.9)
        self.assertAlmostEqual(metrics["frame_uptime_ratio"], 1.0)
        self.assertAlmostEqual(metrics["usable_uptime_ratio"], 1.0)

    def test_packet_state_attribution_uses_half_open_intervals(self):
        intervals = [(0.25, 1.0), (2.0, 3.5)]
        self.assertFalse(is_time_connected(0.249999, intervals))
        self.assertTrue(is_time_connected(0.25, intervals))
        self.assertTrue(is_time_connected(0.999999, intervals))
        self.assertFalse(is_time_connected(1.0, intervals))
        self.assertTrue(is_time_connected(2.0, intervals))
        self.assertFalse(is_time_connected(3.5, intervals))

    def test_deadline_pdr_uses_unique_sequences_and_tx_relative_deadlines(self):
        metrics = compute_deadline_pdr(
            tx_times_by_sequence={1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0},
            rx_times_by_sequence={1: 1.5, 2: 3.1, 3: 3.0, 99: 4.1},
            deadline_s=1.0,
        )
        self.assertEqual(metrics["offered_packets"], 4)
        self.assertEqual(metrics["unique_received_packets"], 3)
        self.assertEqual(metrics["deadline_delivered_packets"], 2)
        self.assertEqual(metrics["deadline_miss_packets"], 2)
        self.assertAlmostEqual(metrics["deadline_pdr"], 0.5)

    def test_deadline_pdr_empty_offered_set_is_nan(self):
        metrics = compute_deadline_pdr({}, {}, deadline_s=1.0)
        self.assertTrue(math.isnan(metrics["deadline_pdr"]))


if __name__ == "__main__":
    unittest.main()
