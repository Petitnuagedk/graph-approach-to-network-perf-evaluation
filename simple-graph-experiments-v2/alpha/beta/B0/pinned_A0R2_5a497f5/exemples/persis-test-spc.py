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


def main():
    print(
        "\n This is a demo case for YADYGAGA, a path constraint Dynamic graph generator\n"
    )
    print("\n The demonstration will be made on the following graph:\n")
    print("         A         ")
    print("        / \        ")
    print("       B   C       ")
    print("       |   |       ")
    print("       D   E       ")
    print("        \ /        ")
    print("         F         \n")
    print("In this demo case, the constraint path is bewteen the pair A-F")
    viz = True
    augment = False
    G = nx.Graph()
    G.add_edges_from(
        [("A", "C"), ("B", "A"), ("C", "E"), ("D", "B"), ("E", "F"), ("D", "F")]
    )

    pair = [("A", "F")]
    limited = G
    if augment == True:
        limited = SourceGraphAugmenter.augmentBaseGraph(G, pair, seed=1, verbose=False)

    fg = FrameGenerator()
    fg.generateSPCFrames(limited, "A", "F", trials=500, p_edge=0.5, pathPersistency=1)
    up = fg.path_up_frames
    down = fg.path_down_frames

    timeline_gen = SPCTimelineBlockGenerator(
        frames=40, path_life=1, stability=1, seed=42, mode="blocks", pathPersistency=1
    )
    timeLine = timeline_gen.generate_blocks()

    DynaGA = SPCDynamicGraph()
    DynaGA.buildDynaGraph(timeLine, up, down)
    print("Built single SPC DynamicGraph length:", len(DynaGA.DynamicGraph))

    # try to build a small unique set
    DynaGAset = DynaGA.generateUniqueSet(
        timeLine, up, down, target_count=3, seed=42, max_enumeration=2000
    )
    print("Unique SPC dynamics found:", len(DynaGAset))
    if DynaGAset:
        lif = PropertiesChecker.path_lifetime(
            graphs=DynaGAset[0].DynamicGraph, source="A", destination="F", fps=1
        )
        print("Example path lifetime (first DG):", lif)

    if viz == True:
        timeline_visualizer = Visualizer(timeLine)
        timeline_visualizer.visualize_dynamic_graph(
            DynaGA.DynamicGraph, target_pairs=pair, layout="spectral"
        )
        timeline_visualizer.animate_random_dynamics(
            DynaGAset, n=2, interval=1000, target_pairs=pair, layout="spectral"
        )


if __name__ == "__main__":
    main()
