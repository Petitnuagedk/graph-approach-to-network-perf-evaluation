import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yadygaga"))

import networkx as nx
import numpy as np

import yadygaga.toolbox as toolbox
from yadygaga.sourceGraphAugmenter import SourceGraphAugmenter
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
from yadygaga.dynaGraph import MPCDynamicGraph


def load_graph_from_adj_csv(path):
    """
    Load an undirected NetworkX Graph from an adjacency-matrix CSV.
    Accepts optional header row with node labels (e.g. Node_0,Node_1,...)
    and optional row-label first column. Non-zero numeric entries -> edge.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, newline="") as fh:
        reader = csv.reader(fh)
        rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("empty CSV")

    def is_number(s):
        try:
            float(s)
            return True
        except Exception:
            return False

    first = [c.strip() for c in rows[0]]
    # header if all non-numeric
    if all(not is_number(c) for c in first):
        header = first
        data_rows = rows[1:]
        # if row-label column present, drop first column of each data row
        if data_rows and len(data_rows[0]) == len(header) + 1:
            data = [[cell.strip() for cell in row[1:]] for row in data_rows]
        else:
            data = [[cell.strip() for cell in row] for row in data_rows]
        nodes = header
    else:
        data = [[cell.strip() for cell in row] for row in rows]
        n = len(data[0])
        nodes = [f"Node_{i}" for i in range(n)]

    G = nx.Graph()
    G.add_nodes_from(nodes)
    for i, row in enumerate(data):
        for j in range(min(len(row), len(nodes))):
            val = row[j]
            if val == "":
                continue
            try:
                if float(val) != 0.0 and i != j:
                    G.add_edge(nodes[i], nodes[j])
            except Exception:
                continue
    return G

def main():
    G = nx.Graph()
    G.add_edges_from([("A", "C"), ("B", "C"), ("C", "E"), ("D", "B"), ("E", "F")])
    pairs = [("A", "F"), ("C", "F")]

    results = sweep_mpc_generate(
        dynamic_graph_base=G,
        pairs=pairs,
        frames=30,
        path_life=0.4,
        step=0.2,
        mode="indep",
        trials=300,
        p_edge=0.5,
        seed=42,
    )
    toolbox.saveSweepMatrices(results, "J2/sweep_results", overwrite=True, file_format="csv")
    print("Sweep produced entries:", len(results))
    if results:
        print("Example entry keys:", list(results[0].keys()))


def sweep_mpc_generate(
    dynamic_graph_base,
    pairs,
    frames: int,
    path_life: float = None,
    stability: float = None,
    step: float = 0.1,
    mode: str = "indep",
    trials: int = 1000,
    p_edge: float = 0.5,
    seed: int = 42,
):
    """
    Sweep the unspecified parameter (path_life or stability) using timeline_feasible_params,
    build one MPC dynamic graph per step, and return a list of results.

    Returns a list of dicts: {'param_name': 'path_life'|'stability', 'param_value': v, 'timeline': timeline, 'dynamic_graph': dynamic_graph}
    """
    if (path_life is None) == (stability is None):
        raise ValueError("Provide exactly one of path_life or stability")

    params_info = toolbox.timelineFeasibleParams(
        frames=frames, path_life=path_life, stability=stability
    )
    results = []

    # prepare augmented base graph and frame generator once
    limitedMPC = SourceGraphAugmenter.augmentBaseGraph(
        dynamic_graph_base, pairs, seed=seed, verbose=False
    )
    frame_generator = FrameGenerator()

    nPairs = len(pairs)

    if path_life is not None:
        # produce stability values in feasible range
        s_min, s_max = params_info.get("feasible_stability", (0.0, 1.0))
        vals = np.arange(s_min, s_max + 1e-9, step)
        param_name = "stability"
        for v in np.unique(np.round(vals, 6)):
            stability_v = float(np.clip(v, 0.0, 1.0))
            # generate MPC frame set (sampling frames for each pair)
            MPCFrameSet = frame_generator.generateMPCFrames(
                limitedMPC, pairs, trials=trials, p_edge=p_edge, seed=seed
            )
            # generate timeline with current parameters
            timelineGen = MPCTimelineBlockGenerator(
                frames, nPairs, path_life, stability_v, mode, seed=seed
            )
            timeline = timelineGen.generate()
            MPCDynaGA = MPCDynamicGraph()
            MPCDynaGA.buildDynaGraph(timeline, MPCFrameSet)
            results.append(
                {
                    "param_name": param_name,
                    "param_value": stability_v,
                    "timeline": timeline,
                    "dynamic_graph": MPCDynaGA.DynamicGraph,
                }
            )

    else:
        # stability provided -> sweep path_life values in feasible range
        feasible = params_info.get("feasible_path_life")
        if feasible is None:
            return results
        a_min, a_max = feasible
        vals = np.arange(a_min, a_max + 1e-9, step)
        param_name = "path_life"
        for v in np.unique(np.round(vals, 6)):
            path_life_v = float(np.clip(v, 0.0, 1.0))
            MPCFrameSet = frame_generator.generateMPCFrames(
                limitedMPC, pairs, trials=trials, p_edge=p_edge, seed=seed
            )
            timelineGen = MPCTimelineBlockGenerator(
                frames, nPairs, path_life_v, stability, mode, seed=seed
            )
            timeline = timelineGen.generate()
            MPCDynaGA = MPCDynamicGraph()
            MPCDynaGA.buildDynaGraph(timeline, MPCFrameSet)
            results.append(
                {
                    "param_name": param_name,
                    "param_value": path_life_v,
                    "timeline": timeline,
                    "dynamic_graph": MPCDynaGA.DynamicGraph,
                }
            )

    return results


if __name__ == "__main__":
    # intentionally use __name__ != "__main__" to avoid accidental execution in some contexts
    # run main explicitly
    main()
