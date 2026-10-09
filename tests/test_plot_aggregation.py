#!/usr/bin/env python3
"""Verify replay epochs are averaged within realizations before CI estimation."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plot import write_aggregate


class PlotAggregationTest(unittest.TestCase):
    def test_epoch_average_then_realization_bootstrap(self):
        rows = [
            {"param_name": "rho", "param_value": 1.0, "protocol": "olsr",
             "realization_id": "graph_0001", "pdr": "0.2", "routing_efficiency": "0.2"},
            {"param_name": "rho", "param_value": 1.0, "protocol": "olsr",
             "realization_id": "graph_0001", "pdr": "0.4", "routing_efficiency": "0.4"},
            {"param_name": "rho", "param_value": 1.0, "protocol": "olsr",
             "realization_id": "graph_0002", "pdr": "0.8", "routing_efficiency": "0.8"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            groups = write_aggregate(rows, output)
            with (output / "aggregate.csv").open(newline="") as stream:
                aggregate = next(csv.DictReader(stream))

        self.assertEqual(aggregate["n_realizations"], "2")
        self.assertEqual(aggregate["n_epochs"], "3")
        self.assertAlmostEqual(float(aggregate["pdr_mean"]), 0.55)
        self.assertEqual(len(groups[("rho", 1.0, "olsr")]["pdr"]), 2)


if __name__ == "__main__":
    unittest.main()
