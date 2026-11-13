import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yadygaga"))

import networkx as nx
from yadygaga.sourceGraphAugmenter import SourceGraphAugmenter
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
from yadygaga.dynaGraph import MPCDynamicGraph
from yadygaga.visualizer import Visualizer


def main():
    print(
        "\n This is a demo case for YADYGAGA, a path constraint Dynamic graph generator\n"
    )
    print("\n The demonstration will be made on the following graph:\n")
    print("         S       Z    ")
    print("        / \     / \   ")
    print("       B   C   K   L  ")
    print("       |   |   |   |  ")
    print("       D   E   M   N  ")
    print("        \ /     \ /   ")
    print("         F       Y  \n")
    print("In this demo case, the constraint path is bewteen the pair S-F and Z-Y")
    viz = True
    augment = False
    G = nx.Graph()
    G.add_edges_from(
        [
            ("S", "C"),
            ("B", "S"),
            ("C", "E"),
            ("D", "B"),
            ("E", "F"),
            ("D", "F"),
            ("Z", "K"),
            ("K", "M"),
            ("M", "Y"),
            ("L", "Z"),
            ("L", "N"),
            ("N", "Y"),
        ]
    )
    verbose = True

    frames = 20
    pairs = [("S", "F"), ("Z", "Y")]
    nPairs = len(pairs)
    pathLifeTime = 1
    stability = 1
    pathPersistency = 1  # test path persistency (0.0..1.0)
    mode = "indep"  # options: "sync" (default) or "indep"
    limitedMPC = G
    if augment == True:
        limitedMPC = SourceGraphAugmenter.augmentBaseGraph(
            G, pairs, seed=1, verbose=False
        )

    print("\n", "Original Graph edges: ", G.edges())
    print("Limited Graph edges: ", limitedMPC.edges(), "\n")

    frame_generator = FrameGenerator()
    MPCFrameSet = frame_generator.generateMPCFrames(
        limitedMPC,
        pairs,
        trials=3000,
        p_edge=0.5,
        seed=1,
    )

    # Timeline with per-pair path ids (None for down, int id for up)
    timelineGen = MPCTimelineBlockGenerator(
        frames,
        nPairs,
        pathLifeTime,
        stability,
        mode,
        seed=40,
        pathPersistency=pathPersistency,
    )
    timeLine = timelineGen.generate()
    print("Generated MPC timeline (None=int down / ints = path ids):")
    print(timeLine, "\n")

    # Build a greedy MPC dynamic graph honoring pid persistence (force=True to fallback if needed)
    MPCDynaGA = MPCDynamicGraph()
    MPCDynaGA.buildDynaGraph(
        timeLine,
        MPCFrameSet,
        seed=1,
        no_double=True,
        allow_hamming_fallback=True,
        force=True,
    )

    print("Selected frame indices for built dynamic graph:")
    print(getattr(MPCDynaGA, "selected_frame_indices", None))

    # Inspect per-pair path keys for selected frames to check persistence behavior
    per_pair = MPCFrameSet.get("per_pair", [])
    sel_idxs = getattr(MPCDynaGA, "selected_frame_indices", [])

    if per_pair and sel_idxs and verbose:
        print("\nPer-frame selected path keys for each pair (None => down):")
        for fi, idx in enumerate(sel_idxs):
            row = []
            for pi in range(len(per_pair)):
                idx_to_path = per_pair[pi].get("idx_to_path", {})
                row.append(idx_to_path.get(idx, None))
            print(
                f"frame {fi}: timeline ids={timeLine[fi]}  selected_paths={tuple(row)}"
            )

    MPCDynaGA = MPCDynamicGraph()
    MPCDynaGA.buildDynaGraph(timeLine, MPCFrameSet)
    
    if viz == True:
        timeline_visualizer = Visualizer(timeLine)
        timeline_visualizer.visualize_dynamic_graph(
            MPCDynaGA.DynamicGraph, target_pairs=pairs
        )


if __name__ == "__main__":
    main()
