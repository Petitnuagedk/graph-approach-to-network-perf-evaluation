import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yadygaga"))

import networkx as nx
from yadygaga.sourceGraphAugmenter import SourceGraphAugmenter
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
from yadygaga.dynaGraph import MPCDynamicGraph
from yadygaga.toolbox import toolbox


def main():
    G = nx.Graph()
    G.add_edges_from([("A", "C"), ("B", "C"), ("C", "E"), ("D", "B"), ("E", "F")])
    pairs = [("A", "F"), ("C", "F")]

    limited = SourceGraphAugmenter.augmentBaseGraph(G, pairs, seed=1, verbose=False)
    fg = FrameGenerator()
    mpc_frames = fg.generateMPCFrames(limited, pairs, trials=1000, p_edge=0.5, seed=1)

    timeline_gen = MPCTimelineBlockGenerator(
        frames=30,
        n_pairs=len(pairs),
        path_life=0.4,
        stability=0.8,
        mode="indep",
        seed=42,
    )
    tl = timeline_gen.generate()

    dyna = MPCDynamicGraph()
    set_ = dyna.generateUniqueSet(
        tl, mpc_frames, target_count=3, seed=42, max_enumeration=2000, force=True
    )
    print("Batch example - saved dynamics count (in-memory):", len(set_))
    toolbox.saveDGbatch(set_, out_dir="./batchExample/", file_format="json")
    for i, dg in enumerate(set_):
        print(f" DG[{i}] length:", len(dg.DynamicGraph))


if __name__ == "__main__":
    main()
