#!/usr/bin/env python3
"""Deterministic MPC B0 acceptance preflight for the registered N=42 r1 case."""
import csv, hashlib, json, random, subprocess
from pathlib import Path
import networkx as nx

B0 = Path(__file__).resolve().parent
CAMPAIGN = B0.parent
A1 = CAMPAIGN.parent / "alpha" / "A1" / "results"
PIN = B0 / "pinned_A0R2_5a497f5"
PAIR_TOOL = B0 / "flow_pair_manifest"
PYTHON = "/home/hledirach/Documents/J2/.venv/bin/python"
FRAMES = 300
TRIALS = 1000000 # 1 000 000 
P_EDGE = 0.5
POOL_SEED = 11
TIMELINE_SEED = 42
REPETITIONS = 2
GRAPH_ID = "geodesic_N42_r1"
FLOW_SEED = 137691609
TARGET_LIFE = 0.5
TARGET_STABILITY = 0.8

import sys
sys.path.insert(0, str(PIN))
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.dynaGraph import MPCDynamicGraph


def rows(path):
    with path.open(newline="") as h:
        return list(csv.DictReader(h))


def load_graph():
    g = nx.Graph()
    g.add_nodes_from(range(42))
    for row in rows(A1 / "edge_lists" / f"{GRAPH_ID}.csv"):
        g.add_edge(int(row["u"]), int(row["v"]))
    return g


def load_pairs():
    cov = {r["graph_id"]: r for r in rows(A1 / "graph_covariates.csv")}[GRAPH_ID]
    raw = subprocess.check_output(
        [str(PAIR_TOOL), "42", cov["probe_S"], cov["probe_R"], str(FLOW_SEED)], text=True
    )
    return [(int(s), int(d)) for _, s, d, _ in csv.reader(raw.splitlines())]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_once():
    pairs = load_pairs()
    graph = load_graph()
    pool = FrameGenerator().generateMPCFrames(
        graph, pairs, trials=TRIALS, p_edge=P_EDGE, seed=POOL_SEED
    )
    if pool["pairs"] != pairs or len(pairs) != 44:
        raise AssertionError("MPC pair list does not equal the frozen ns-3 pair manifest")

    # Pool-aware exact feasibility timeline. Each selected status consumes one
    # available pool multiplicity; no status or path fallback is permitted.
    bag = [status for status, indices in pool["cases"].items() for _ in indices]
    rng = random.Random(TIMELINE_SEED)
    rng.shuffle(bag)
    if len(bag) < FRAMES:
        raise RuntimeError(f"MPC pool contains only {len(bag)} usable status instances")
    timeline = []
    next_id = [0] * len(pairs)
    for status in bag[:FRAMES]:
        entry = []
        for pi, up in enumerate(status):
            entry.append(next_id[pi] if up else None)
            if up:
                next_id[pi] += 1
        timeline.append(tuple(entry))

    builder = MPCDynamicGraph()
    builder.buildDynaGraph(
        timeline, pool, seed=TIMELINE_SEED, no_double=True,
        allow_hamming_fallback=False, force=False,
    )
    selected = builder.selected_frame_indices
    realized = [pool["idx_to_status"][idx] for idx in selected]
    requested = [tuple(x is not None for x in row) for row in timeline]
    if requested != realized:
        raise AssertionError("selected MPC statuses are not exactly equal to requested statuses")

    per_pair = []
    for pi, pair in enumerate(pairs):
        paths = [pool["per_pair"][pi]["idx_to_path"].get(idx) for idx in selected]
        up = [path is not None for path in paths]
        per_pair.append({
            "pair_index": pi, "source": pair[0], "destination": pair[1],
            "up_count": sum(up), "realized_life": sum(up) / FRAMES,
            "up_runs": sum(v and (i == 0 or not up[i - 1]) for i, v in enumerate(up)),
            "path_changes": sum(paths[i] != paths[i - 1] for i in range(1, len(paths)) if paths[i] is not None and paths[i - 1] is not None),
        })
    expected_up = round(FRAMES * TARGET_LIFE)
    expected_runs = round(1 + (1 - TARGET_STABILITY) * (expected_up - 1))
    target_ok = all(
        item["up_count"] == expected_up and item["up_runs"] == expected_runs
        for item in per_pair
    )
    return {
        "graph_id": GRAPH_ID, "pairs": pairs, "pair_count": len(pairs),
        "flow_seed": FLOW_SEED, "frames": FRAMES, "trials": TRIALS,
        "p_edge": P_EDGE, "pool_seed": POOL_SEED, "timeline_seed": TIMELINE_SEED,
        "target_life": TARGET_LIFE, "target_stability": TARGET_STABILITY,
        "expected_up_count": expected_up, "expected_up_runs": expected_runs,
        "life_stability_target_match": target_ok,
        "selected_frame_indices": selected, "exact_status_match": True,
        "fallbacks": 0, "pair_manifest_sha256": digest(pairs),
        "timeline_sha256": digest(timeline), "selected_frames_sha256": digest(selected),
        "per_pair": per_pair,
    }


def main():
    results = [run_once() for _ in range(REPETITIONS)]
    reproducible = [digest(result) for result in results]
    output = {
        "status": "PASS" if len(set(reproducible)) == 1 and all(r["life_stability_target_match"] for r in results) else "FAIL",
        "repetitions": REPETITIONS,
        "reproducible": len(set(reproducible)) == 1,
        "runs": results,
    }
    out = B0 / "mpc_b0_acceptance.json"
    out.write_text(json.dumps(output, indent=2) + "\n")
    print(out)
    print(output["status"])


if __name__ == "__main__":
    main()
