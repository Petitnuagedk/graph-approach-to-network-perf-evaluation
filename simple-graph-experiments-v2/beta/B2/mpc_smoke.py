#!/usr/bin/env python3
import csv, hashlib, subprocess, sys
import random
from pathlib import Path
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
A1 = ROOT.parent / 'alpha' / 'A1' / 'results'
PIN = ROOT / 'B0' / 'pinned_A0R2_5a497f5'
sys.path.insert(0, str(PIN))
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
from yadygaga.dynaGraph import MPCDynamicGraph

F = 300
POOL_TRIALS = 3000
POOL_EDGE = 0.5
POOL_SEED = 11
PAIR_TOOL = ROOT / 'B0' / 'flow_pair_manifest'


def csvrows(path):
    with path.open(newline='') as h:
        return list(csv.DictReader(h))


def graph(gid):
    g = nx.Graph(); g.add_nodes_from(range(42))
    for r in csvrows(A1 / 'edge_lists' / f'{gid}.csv'):
        g.add_edge(int(r['u']), int(r['v']))
    return g


def pairs(gid, seed=137691609):
    cov = {r['graph_id']: r for r in csvrows(A1 / 'graph_covariates.csv')}[gid]
    raw = subprocess.check_output([str(PAIR_TOOL), '42', cov['probe_S'], cov['probe_R'], str(seed)], text=True)
    return [(int(s), int(d)) for _, s, d, _ in csv.reader(raw.splitlines())]


def main():
    gid = sys.argv[1] if len(sys.argv) > 1 else 'geodesic_N42_r1'
    pair_list = pairs(gid)
    g = graph(gid)
    fg = FrameGenerator()
    mpc_frames = fg.generateMPCFrames(g, pair_list, trials=POOL_TRIALS, p_edge=POOL_EDGE, seed=POOL_SEED)
    assert mpc_frames['pairs'] == pair_list
    assert len(mpc_frames['per_pair']) == len(pair_list) == 44
    # Prototype pool-aware timeline: choose only statuses that the finite MPC
    # pool actually contains. This is a feasibility probe, not the registered
    # B2 life/stability timeline design.
    rng = random.Random(42)
    status_bag = [status for status, indices in mpc_frames['cases'].items() for _ in indices]
    rng.shuffle(status_bag)
    timeline = []
    next_id = [0] * len(pair_list)
    for _ in range(F):
        status = status_bag[_]
        row = []
        for pi, up in enumerate(status):
            row.append(next_id[pi] if up else None)
            if up:
                next_id[pi] += 1
        timeline.append(tuple(row))
    builder = MPCDynamicGraph()
    failure = None
    try:
        builder.buildDynaGraph(timeline, mpc_frames, seed=42, no_double=True, allow_hamming_fallback=False, force=False)
    except RuntimeError as exc:
        failure = str(exc)
    selected = builder.selected_frame_indices
    statuses = mpc_frames['idx_to_status']
    requested = [tuple(x is not None for x in t) for t in timeline]
    realized = [statuses[i] for i in selected]
    exact = bool(selected) and all(a == b for a, b in zip(requested, realized))
    per_pair = []
    for pi, pair in enumerate(pair_list):
        seq = [mpc_frames['per_pair'][pi]['idx_to_path'].get(i) for i in selected]
        up = [p is not None for p in seq]
        runs = sum(v and (j == 0 or not up[j - 1]) for j, v in enumerate(up))
        per_pair.append({'pair_index': pi, 'source': pair[0], 'destination': pair[1], 'realized_life': sum(up) / F, 'up_runs': runs})
    out = ROOT / 'B2' / f'mpc_smoke_{gid}.json'
    status = 'pass' if failure is None and exact else 'infeasible'
    out.write_text(__import__('json').dumps({'status': status, 'graph_id': gid, 'pairs': pair_list, 'pair_count': len(pair_list), 'pool_trials': POOL_TRIALS, 'exact_status_match': exact, 'fallbacks': 0, 'failure': failure, 'per_pair': per_pair}, indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    main()
