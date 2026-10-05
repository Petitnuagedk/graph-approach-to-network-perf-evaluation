# python3 -m exemple.spc_example
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yadygaga"))

import networkx as nx
from yadygaga.sourceGraphAugmenter import SourceGraphAugmenter
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
from yadygaga.dynaGraph import SPCDynamicGraph
from yadygaga.propertiesChecker import PropertiesChecker
from yadygaga.visualizer import Visualizer
import yadygaga.toolbox as toolbox

import argparse
import csv
import random
import time


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


def test_pair_on_graph(G, a, b, trials=500, p_edge=0.5, pathPersistency=0.9,
                       frames=40, path_life=0.4, stability=0.8, seed=42, viz=False,
                       output_csv=None, fps=1.0, link_loss_db=40.0):
    pair = [(a, b)]
    #limited = SourceGraphAugmenter.augmentBaseGraph(G, pair, seed=seed, verbose=False)
    limited = G
    fg = FrameGenerator()
    t0 = time.perf_counter()
    fg.generateSPCFrames(limited, a, b, trials=trials, p_edge=p_edge, pathPersistency=pathPersistency)
    t_frames = time.perf_counter() - t0
    up = fg.path_up_frames
    down = fg.path_down_frames
    print(f"Pair ({a},{b}): up_frames={len(up)} down_frames={len(down)} (frames_time={t_frames:.3f}s)")

    if len(up) == 0 or len(down) == 0:
        print("  -> No up/down frames found for this pair.")
        return None

    timeline_gen = SPCTimelineBlockGenerator(frames=frames, path_life=path_life,
                                             stability=stability, seed=seed, mode="blocks",
                                             pathPersistency=pathPersistency)
    timeLine = timeline_gen.generate_blocks()

    DynaGA = SPCDynamicGraph()
    t1 = time.perf_counter()
    DynaGA.buildDynaGraph(timeLine, up, down)
    t_build = time.perf_counter() - t1
    print("  DynamicGraph length:", len(DynaGA.DynamicGraph), f"(build_time={t_build:.3f}s)")

    if output_csv:
        out_dir = os.path.dirname(output_csv)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        node_list = list(G.nodes())
        toolbox.saveDGmatrices(DynaGA, out_dir, entry_name=os.path.basename(output_csv), overwrite=True, file_format="csv")
        # export_dynamic_graph_to_trace_csv(DynaGA, node_list, output_csv,
        #                                   fps=fps, link_loss_db=link_loss_db)
        print(f"  Exported dynamic graph trace CSV: {output_csv}")

    try:
        DynaGAset = DynaGA.generateUniqueSet(timeLine, up, down, target_count=3, seed=seed, max_enumeration=2000)
        print("  Unique SPC dynamics found:", len(DynaGAset))
        if DynaGAset:
            lif = PropertiesChecker.path_lifetime(graphs=DynaGAset[0].DynamicGraph, source=a, destination=b, fps=1)
            print("  Example path lifetime (first DG):", lif)
    except Exception as e:
        print("  generateUniqueSet/properties check failed:", e)

    if viz:
        try:
            timeline_visualizer = Visualizer(timeLine)
            timeline_visualizer.visualize_dynamic_graph(DynaGA.DynamicGraph, target_pairs=[(a, b)])
        except Exception as e:
            print("  visualization failed:", e)

    total_time = t_frames + t_build
    return {
        "pair": (a, b),
        "up": len(up),
        "down": len(down),
        "dyn_len": len(DynaGA.DynamicGraph),
        "time_frames_s": t_frames,
        "time_build_s": t_build,
        "time_total_s": total_time,
        "output_csv": str(output_csv) if output_csv else None,
    }


def build_dynamic_graph(G, a, b, trials=500, p_edge=0.5, pathPersistency=0.9,
                        frames=40, path_life=0.4, stability=0.8, seed=42):
    """
    Same pipeline as test_pair_on_graph(), but returns the built
    SPCDynamicGraph object itself instead of only a stats dict, so a
    caller can export DynaGA.DynamicGraph (the per-frame network state)
    elsewhere -- e.g. to the trace CSV consumed by graph-run.cc.

    Left as a separate function rather than a refactor of
    test_pair_on_graph() so the existing CLI/demo behavior is untouched.

    Returns (DynaGA, stats) on success, or (None, None) if no up/down
    frames were found for this pair (mirrors test_pair_on_graph's own
    "No up/down frames found" case).
    """
    #limited = SourceGraphAugmenter.augmentBaseGraph(G, [(a, b)], seed=seed, verbose=False)
    limited = G
    fg = FrameGenerator()
    fg.generateSPCFrames(limited, a, b, trials=trials, p_edge=p_edge, pathPersistency=pathPersistency)
    up = fg.path_up_frames
    down = fg.path_down_frames
    if len(up) == 0 or len(down) == 0:
        return None, None

    timeline_gen = SPCTimelineBlockGenerator(frames=frames, path_life=path_life,
                                             stability=stability, seed=seed, mode="blocks",
                                             pathPersistency=pathPersistency)
    timeLine = timeline_gen.generate_blocks()

    DynaGA = SPCDynamicGraph()
    DynaGA.buildDynaGraph(timeLine, up, down)

    stats = {
        "pair": (a, b),
        "up": len(up),
        "down": len(down),
        "dyn_len": len(DynaGA.DynamicGraph),
    }
    return DynaGA, stats


def main():
    parser = argparse.ArgumentParser(description="Test SPC dynamic graph generation from adjacency-matrix CSV")
    parser.add_argument("-a", "--adjacency-csv", dest="adj_csv", help="Path to adjacency matrix CSV (optional). If omitted, runs small demo graph.")
    parser.add_argument("--attempts", type=int, default=1, help="Number of random terminal pairs to try")
    parser.add_argument("--trials", type=int, default=1000, help="Sampling trials per pair")
    parser.add_argument("--p_edge", type=float, default=0.5)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--path-persistency", type=float, default=0.5)
    parser.add_argument("--path-life", type=float, default=1.0)
    parser.add_argument("--stability", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--viz", action="store_true", help="Enable visualization (may be heavy for large graphs)")
    parser.add_argument("-o", "--output-csv", dest="output_csv", default=None,
                        help="Write the dynamic graph as a trace-frame CSV (the format graph-run.cc "
                             "reads) to this path. With --attempts > 1, the pair is appended to the "
                             "filename per attempt, e.g. dg.csv -> dg_Node_3_Node_17.csv")
    parser.add_argument("--fps", type=float, default=1.0,
                        help="DynamicGraph frames per second, only used with --output-csv "
                             "(maps frame index to seconds in the written CSV)")
    parser.add_argument("--link-loss-db", dest="link_loss_db", type=float, default=40.0,
                        help="Loss (dB) written for an edge present in a DG frame, only used "
                             "with --output-csv")
    args = parser.parse_args()

    if args.adj_csv:
        t_load0 = time.perf_counter()
        G = load_graph_from_adj_csv(args.adj_csv)
        t_load = time.perf_counter() - t_load0
        node_list = list(G.nodes())
        if len(node_list) < 2:
            print("Graph must contain at least two nodes.")
            return
        print(f"Loaded graph from adjacency CSV: nodes={len(node_list)} edges={G.number_of_edges()} (load_time={t_load:.3f}s)")
        rnd = random.Random(args.seed)
        results = []
        for i in range(args.attempts):
            a, b = rnd.sample(node_list, 2)
            print(f"\nAttempt {i+1}/{args.attempts} -> testing pair: {a}, {b}")
            out_csv = None
            if args.output_csv:
                if args.attempts == 1:
                    out_csv = args.output_csv
                else:
                    stem, ext = os.path.splitext(args.output_csv)
                    out_csv = f"{stem}_{a}_{b}{ext or '.csv'}"
            res = test_pair_on_graph(G, a, b, trials=args.trials, p_edge=args.p_edge,
                                     pathPersistency=args.path_persistency, frames=args.frames,
                                     path_life=args.path_life, stability=args.stability,
                                     seed=args.seed + i, viz=args.viz,
                                     output_csv=out_csv, fps=args.fps, link_loss_db=args.link_loss_db)
            results.append(res)
        print("\nSummary (None means no up/down frames found):")
        for r in results:
            print(" ", r)
    else:
        # original small demo
        print("\n Using embedded small demo graph")
        G = nx.Graph()
        G.add_edges_from([("A", "C"), ("B", "C"), ("C", "E"), ("D", "B"), ("E", "F")])
        pair = [("A", "F")]
        limited = SourceGraphAugmenter.augmentBaseGraph(G, pair, seed=1, verbose=False)
        fg = FrameGenerator()
        fg.generateSPCFrames(limited, "A", "D", trials=500, p_edge=0.5, pathPersistency=0.9)
        up = fg.path_up_frames
        down = fg.path_down_frames
        print("up/down frames:", len(up), len(down))
        timeline_gen = SPCTimelineBlockGenerator(frames=40, path_life=0.4, stability=0.8, seed=42, mode="blocks", pathPersistency=0.9)
        timeLine = timeline_gen.generate_blocks()
        DynaGA = SPCDynamicGraph()
        DynaGA.buildDynaGraph(timeLine, up, down)
        print("Built single SPC DynamicGraph length:", len(DynaGA.DynamicGraph))


if __name__ == "__main__":
    main()