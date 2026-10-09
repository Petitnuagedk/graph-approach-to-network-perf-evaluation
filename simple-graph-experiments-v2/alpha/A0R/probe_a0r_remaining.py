#!/usr/bin/env python3
"""Preregistered A0-R MPC, invalid-input, and infeasibility probes."""
from __future__ import annotations

import base64
import json
import random
import subprocess
import sys
import typing
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "YaDyGaGa"
RESULTS = HERE / "results"
REVISION = "51b01ac7faa78a494c3baedc560d658f384afe09"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE))
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator, SPCTimelineBlockGenerator
from yadygaga.dynaGraph import MPCDynamicGraph
from icosahedral_geodesic import create_icosahedral_geodesic_graph


def graph_and_pairs():
    graph = nx.relabel_nodes(
        create_icosahedral_geodesic_graph(3, 0),
        lambda node: f"Node_{node}",
    )
    nodes = sorted(graph, key=lambda node: int(node.rpartition("_")[2]))
    diameter = (-1, None, None)
    for index, source in enumerate(nodes):
        distances = nx.single_source_shortest_path_length(graph, source)
        for destination in nodes[index + 1 :]:
            if distances[destination] > diameter[0]:
                diameter = (distances[destination], source, destination)
    _, source, destination = diameter
    others = [node for node in nodes if node not in (source, destination)]
    return graph, {
        "disjoint": [(source, destination), (others[0], others[-1])],
        "shared_source": [(source, destination), (source, others[0])],
    }


def mpc_probe(graph, label, pairs):
    frame_set = FrameGenerator().generateMPCFrames(
        graph, pairs, trials=1000, p_edge=0.5, seed=42
    )
    timeline = MPCTimelineBlockGenerator(
        frames=120,
        n_pairs=2,
        path_life=0.5,
        stability=0.8,
        mode="indep",
        seed=42,
        pathPersistency=0.9,
    ).generate()
    dynamic = MPCDynamicGraph()
    assembled = dynamic.buildDynaGraph(timeline, frame_set, seed=43)
    return {
        "relation": label,
        "pairs": pairs,
        "N": graph.number_of_nodes(),
        "frames_sampled": 1000,
        "p_edge": 0.5,
        "frame_seed": 42,
        "timeline_frames": 120,
        "timeline_path_life": 0.5,
        "timeline_stability": 0.8,
        "timeline_mode": "indep",
        "timeline_seed": 42,
        "assembly_seed": 43,
        "status_counts": {str(key): value for key, value in frame_set["counts"].items()},
        "per_pair_up_frame_counts": [len(pair["up_indices"]) for pair in frame_set["per_pair"]],
        "per_pair_down_frame_counts": [len(pair["down_indices"]) for pair in frame_set["per_pair"]],
        "timeline_status_patterns": len({tuple(value is not None for value in row) for row in timeline}),
        "assembled_frame_count": len(assembled),
        "selected_status_counts": {
            str(key): dynamic.selected_statuses.count(key)
            for key in sorted(set(dynamic.selected_statuses))
        },
    }


def probe_out_of_range():
    requests = [
        ("path_life_below_range", -0.1, 0.8),
        ("path_life_above_range", 1.1, 0.8),
        ("stability_below_range", 0.5, -0.2),
        ("stability_above_range", 0.5, 1.2),
    ]
    results = []
    clean_text = subprocess.check_output(
        ["git", "-C", "/home/hledirach/Documents/YaDyGaGa", "show", f"{REVISION}:yadygaga/timelineBlockGenerator.py"],
        text=True,
    )
    namespace = {"__name__": "clean_timeline_probe", "List": typing.List,
                 "Tuple": typing.Tuple, "random": random}
    exec(compile(clean_text, "clean_HEAD_timelineBlockGenerator.py", "exec"), namespace)
    clean_generator = namespace["SPCTimelineBlockGenerator"]
    for name, life, stability in requests:
        for source_label, cls in (("clean_HEAD", clean_generator), ("patched_A0R", SPCTimelineBlockGenerator)):
            try:
                timeline = cls(120, life, stability, 42, pathPersistency=0.9).generate_blocks()["timeline"]
                results.append({
                    "request": name, "source": source_label, "path_life": life,
                    "stability": stability, "outcome": "returned",
                    "frames": len(timeline), "realized_up_count": sum(timeline),
                    "realized_uptime": sum(timeline) / len(timeline),
                })
            except Exception as error:
                results.append({
                    "request": name, "source": source_label, "path_life": life,
                    "stability": stability, "outcome": type(error).__name__,
                    "message": str(error),
                })
    return results


def clean_infeasible_probe():
    clean_text = subprocess.check_output(
        ["git", "-C", "/home/hledirach/Documents/YaDyGaGa", "show", f"{REVISION}:yadygaga/timelineBlockGenerator.py"],
        text=True,
    )
    payload = base64.b64encode(clean_text.encode()).decode()
    child_code = (
        "import base64,random,typing; ns={'__name__':'clean_probe','List':typing.List,"
        "'Tuple':typing.Tuple,'random':random}; source=base64.b64decode('" + payload + "').decode(); "
        "exec(compile(source,'clean_HEAD_timelineBlockGenerator.py','exec'),ns); "
        "ns['SPCTimelineBlockGenerator'](120,.7,.4,42).generate_blocks()"
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", child_code], capture_output=True, text=True,
            timeout=2, check=False,
        )
        clean_outcome = {
            "outcome": "returned" if completed.returncode == 0 else "process_error",
            "returncode": completed.returncode,
            "stderr_tail": completed.stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        clean_outcome = {"outcome": "timeout_after_2s", "safety_timeout": True}
    try:
        SPCTimelineBlockGenerator(120, 0.7, 0.4, 42).generate_blocks()
        patched_outcome = {"outcome": "returned"}
    except Exception as error:
        patched_outcome = {"outcome": type(error).__name__, "message": str(error)}
    return {
        "request": {"frames": 120, "path_life": 0.7, "stability": 0.4},
        "clean_HEAD": clean_outcome,
        "patched_A0R": patched_outcome,
    }


def main():
    RESULTS.mkdir(exist_ok=True)
    graph, pair_sets = graph_and_pairs()
    mpc = [mpc_probe(graph, label, pairs) for label, pairs in pair_sets.items()]
    inputs = probe_out_of_range()
    infeasible = clean_infeasible_probe()
    data = {
        "source_revision": REVISION,
        "mpc_probes": mpc,
        "out_of_range_probes": inputs,
        "infeasible_request_probe": infeasible,
        "protocol_variants": 0,
    }
    (RESULTS / "remaining_capabilities.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
