"""
Entry point for the YaDyGaGa application.

This module orchestrates the overall functionality of the project by utilizing
the classes defined in the other modules. It may include example usage of
the FrameGenerator, PropertiesChecker, TimelineBlockGenerator, TimelineAssembler,
and TimelineVisualizer classes.
"""

import networkx as nx
import numpy as np

import toolbox as toolbox
from sourceGraphAugmenter import SourceGraphAugmenter
from frameGenerator import FrameGenerator
from timelineBlockGenerator import SPCTimelineBlockGenerator, MPCTimelineBlockGenerator
from dynaGraph import dynamicGraph, SPCDynamicGraph, MPCDynamicGraph
from dyCoDeTa import DynaGraphCommuDetection, AnalyzerDynaCommu, visualizer
from visualizer import Visualizer
from propertiesChecker import PropertiesChecker


def main(test: str = "SPC", viz: bool = False):

    G = nx.Graph()
    G.add_edges_from([("A", "C"), ("B", "C"), ("C", "E"), ("D", "B"), ("E", "F")])

    print(
        "\n This is a demo case for YADYGAGA, a path constraint Dynamic graph generator\n"
    )
    print("\n The demonstration will be made on the following graph:\n")
    print("         A         ")
    print("          \        ")
    print("       B---C       ")
    print("       |   |       ")
    print("       D   E       ")
    print("          /        ")
    print("         F         \n")
    print(
        "Where the, in the case of SPC test, the constraint path is bewteen the pair A-F"
    )
    print("and in the case of MPC test, pairs constraints are A-F and C-F\n")

    # Options: "SPC" (Single Path Constraint), "MPC" (Multi Path Constraint),
    # "Dynamic community detection" (self explanatory), "sweep" (parameter sweep example),
    # "batch" (load previously saved batch data and visualize)
    test = "MPC"
    viz = True
    verbose = False

    parameters = toolbox.timelineFeasibleParams(frames=600, stability=0.8)
    print(
        "Feasible parameters for 600 frames and stability 0.8: ",
        parameters["feasible_path_life"],
    )

    # Single path constraint exemple
    if test == "SPC":

        frames = 50  # need to change name to make it more clear, this is number of timeline frames
        InversepathLength = (
            1  # TODO : enforce geometric path length constraint in timeline generation
        )
        path_life = 0.5  # DONE : enforce path lifetime over time
        stability = 0.8  # DONE : enforce path stability over time
        pathPersistency = (
            1  # DONE : enforce that a given path remains the same when alive
        )
        mode = "blocks"

        print("Single Path Constraint Test")
        S = "A"  # source
        D = "F"  # destination
        pair = [(S, D)]
        limitedSPC = SourceGraphAugmenter.augmentBaseGraph(
            G, pair, seed=1, verbose=False
        )
        print("Original Graph edges: ", G.edges())
        print("Limited Graph edges: ", limitedSPC.edges())

        frame_generator = FrameGenerator()
        frame_generator.generateSPCFrames(
            limitedSPC, S, D, trials=3000, p_edge=0.5, pathPersistency=pathPersistency
        )

        pathUpFrames = frame_generator.path_up_frames
        pathDownFrames = frame_generator.path_down_frames

        if verbose:
            print("Number of path up frames groups: ", len(pathUpFrames))
            for i, group in enumerate(pathUpFrames):
                print(
                    f" Path {i} (nodes {frame_generator.path_up_keys[i]}): {len(group)} frames"
                )
            print("Number of path down frames: ", len(pathDownFrames))

        timeline_block_generator = SPCTimelineBlockGenerator(
            frames, path_life, stability, mode, pathPersistency=pathPersistency
        )
        timeLine = timeline_block_generator.generate_blocks()

        print("Time line : ", timeLine)

        DynaGA = SPCDynamicGraph()
        DynaGA.buildDynaGraph(timeLine, pathUpFrames, pathDownFrames)
        DynaGAset = DynaGA.generateUniqueSet(
            timeLine,
            pathUpFrames,
            pathDownFrames,
            target_count=5,
            seed=42,
            max_enumeration=1000,
        )

        path_lifetime = PropertiesChecker.path_lifetime(
            graphs=DynaGA.DynamicGraph, source=S, destination=D, fps=1
        )
        path_stability = PropertiesChecker.path_stability(
            graphs=DynaGA.DynamicGraph, source=S, destination=D
        )
        path_length = PropertiesChecker.path_length(
            graphs=DynaGA.DynamicGraph, source=S, destination=D
        )

        # detector = DynaGraphCommuDetection(DynaGA.DynamicGraph, method="louvain", seed = 444)
        # communities = detector.detectStatCommunities()
        # comm_mapper = detector.unitCirclePlacement()

        if verbose:
            print("Path lifetime properties: ", path_lifetime)
            print("Path stability properties: ", path_stability)
            print("Path length properties: ", path_length)
            print("Dynamic Graph length: ", len(DynaGA.DynamicGraph))
            print("Detected communities fro frame 1: ", communities[0])
            print("Community based node placement for frame 1: ", comm_mapper)
            print(
                "Community positions in H space for frame 1: ", detector.HspaceMapper[0]
            )

        if viz == True:
            timeline_visualizer = Visualizer(timeLine)
            timeline_visualizer.visualize_dynamic_graph(
                DynaGA.DynamicGraph, target_pairs=pair
            )
            timeline_visualizer.animate_random_dynamics(
                DynaGAset, n=2, interval=1000, target_pairs=pair
            )

            # detector.plotCommuMapper()
            # detector.HspacePlacement(frame_index=0)
            # detector.plotHspacePlacement(frame_index=0)

        return

    # -----------------------------
    # Multi path constraint exemple
    if test == "MPC":
        frames = 20
        pairs = [("A", "D"), ("C", "F")]
        nPairs = len(pairs)
        pathLifeTime = 0.5
        stability = 0.8
        pathPersistency = 1  # test path persistency (0.0..1.0)
        mode = "indep"  # options: "sync" (default) or "indep"

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
        MPCDynaGAset = MPCDynaGA.generateUniqueSet(
            timeLine, MPCFrameSet, target_count=2, seed=42, max_enumeration=10000
        )
        if viz == True:
            timeline_visualizer = Visualizer(timeLine)
            timeline_visualizer.visualize_dynamic_graph(
                MPCDynaGA.DynamicGraph, target_pairs=pairs
            )
            timeline_visualizer.animate_random_dynamics(
                MPCDynaGAset, n=2, interval=1000, target_pairs=pairs
            )
        return

    if test == "Dynamic community detection":
        DynaGa = dynamicGraph()
        G1 = nx.Graph()
        G1.add_edges_from(
            [
                ("A", "D"),
                ("A", "E"),
                ("A", "B"),
                ("D", "B"),
                ("D", "E"),
                ("B", "E"),
                ("B", "F"),
                ("B", "C"),
                ("C", "F"),
                ("C", "E"),
                ("E", "F"),
                ("E", "G"),
                ("G", "H"),
                ("G", "J"),
                ("G", "I"),
                ("H", "I"),
                ("I", "J"),
                ("H", "J"),
                ("K", "L"),
                ("K", "M"),
                ("K", "N"),
                ("K", "O"),
                ("L", "M"),
                ("M", "N"),
                ("N", "O"),
                ("O", "L"),
                ("L", "N"),
                ("M", "O"),
                ("K", "C"),
                ("N", "J"),
            ]
        )
        G2 = nx.Graph()
        G2.add_edges_from(
            [
                ("A", "D"),
                ("A", "E"),
                ("A", "B"),
                ("D", "B"),
                ("D", "E"),
                ("B", "E"),
                ("B", "F"),
                ("B", "C"),
                ("C", "F"),
                ("C", "E"),
                ("E", "F"),
                ("E", "G"),
                ("G", "H"),
                ("G", "J"),
                ("G", "I"),
                ("H", "I"),
                ("I", "J"),
                ("H", "J"),
                ("K", "L"),
                ("K", "M"),
                ("K", "N"),
                ("K", "O"),
                ("L", "M"),
                ("M", "N"),
                ("N", "O"),
                ("O", "L"),
                ("L", "N"),
                ("M", "O"),
                ("K", "C"),
                ("N", "J"),
            ]
        )
        G3 = nx.Graph()
        G3.add_edges_from(
            [
                ("A", "D"),
                ("A", "E"),
                ("A", "B"),
                ("D", "B"),
                ("D", "E"),
                ("B", "E"),
                ("B", "F"),
                ("B", "C"),
                ("C", "F"),
                ("C", "E"),
                ("E", "F"),
                ("E", "G"),
                ("G", "H"),
                ("O", "J"),
                ("G", "I"),
                ("H", "I"),
                ("L", "J"),
                ("M", "J"),
                ("K", "L"),
                ("K", "M"),
                ("K", "N"),
                ("K", "O"),
                ("L", "M"),
                ("M", "N"),
                ("N", "O"),
                ("O", "L"),
                ("L", "N"),
                ("M", "O"),
                ("K", "C"),
                ("N", "J"),
            ]
        )
        G4 = nx.Graph()
        G4.add_edges_from(
            [
                ("A", "D"),
                ("A", "E"),
                ("A", "B"),
                ("D", "B"),
                ("D", "E"),
                ("B", "E"),
                ("B", "F"),
                ("B", "C"),
                ("C", "F"),
                ("C", "E"),
                ("E", "F"),
                ("E", "G"),
                ("G", "H"),
                ("G", "J"),
                ("G", "I"),
                ("H", "I"),
                ("I", "J"),
                ("H", "J"),
                ("K", "L"),
                ("K", "M"),
                ("K", "N"),
                ("K", "O"),
                ("L", "M"),
                ("M", "N"),
                ("N", "O"),
                ("O", "L"),
                ("L", "N"),
                ("M", "O"),
                ("K", "C"),
                ("N", "J"),
            ]
        )
        DynaGa.appendGraph(G1)
        DynaGa.appendGraph(G2)
        DynaGa.appendGraph(G3)
        DynaGa.appendGraph(G4)

        print("Dynamic Community Detection Test")
        # Using the SPCDynamicGraph from the previous SPC test
        detector = DynaGraphCommuDetection(
            DynaGa.DynamicGraph, method="louvain", seed=444
        )
        communities = detector.detectStatCommunities()
        print("Detected communities for frame 1: ", communities[0])
        comm_mapper = detector.unitCirclePlacement()
        print("Community based node placement for frame 1: ", comm_mapper)
        if viz == True:
            detector.plotCommuMapper()
        detector.HspacePlacement(frame_index=0)
        print("Community positions in H space for frame 1: ", detector.HspaceMapper[0])
        if viz == True:
            detector.plotHspacePlacement(frame_index=0)
        detector.HspacePropagation(threshold=0.5)
        if viz == True:
            detector.plotDynaCommunity()

        # Exemple of usage of AnalyzerDynaCommu
        analyzer = AnalyzerDynaCommu(detector.dynaCommunity)
        dynaCommulifetime = analyzer.commuLifeTime()
        print("Dynamic community lifetime: ", dynaCommulifetime)
        flexibilityScores = analyzer.flexibility()
        print("Flexibility scores: ", flexibilityScores)
        if viz == True:
            vizu = visualizer(DynaGa.DynamicGraph, flexibilityScores)
            vizu.flexibilityVisualization()

        return

    if test == "sweep":
        pairs = [("A", "F"), ("C", "F")]
        sweepResults = sweep_mpc_generate(
            dynamic_graph_base=G,
            pairs=pairs,
            frames=100,
            path_life=0.5,
            step=0.1,
            mode="indep",
            trials=1000,
            p_edge=0.5,
            seed=42,
        )
        print("Sweep done")
        toolbox.saveSweepMatrices(sweepResults, out_dir="./sweep_results/")
        return

    if test == "batch":
        # Batch example: load previously saved data and visualize
        pairs = [("A", "F"), ("C", "F")]
        limitedMPC = SourceGraphAugmenter.augmentBaseGraph(
            G, pairs, seed=1, verbose=False
        )
        frame_generator = FrameGenerator()
        MPCFrameSet = frame_generator.generateMPCFrames(
            limitedMPC, pairs, trials=1000, p_edge=0.5, seed=1
        )
        frames = 50
        nPairs = len(pairs)
        pathLifeTime = 0.5
        stability = 1
        mode = "indep"  # options: "sync" (default) or "indep"
        timelineGen = MPCTimelineBlockGenerator(
            frames, nPairs, pathLifeTime, stability, mode, seed=40
        )
        timeLine = timelineGen.generate()
        MPCDynaGA = MPCDynamicGraph()
        MPCDynaGAset = MPCDynaGA.generateUniqueSet(
            timeLine, MPCFrameSet, target_count=5, seed=42, max_enumeration=1000
        )
        # print("MPCDynaGAset first entry dynamic graph length: ", len(MPCDynaGAset[0].DynamicGraph))
        toolbox.saveDGbatch(MPCDynaGAset, out_dir="./batchExample/")

        path = "./batchExample/"
        loaded = toolbox.loadFromDirectory(path)
        viz = Visualizer(timeLine)
        viz.plotLoadedData(loaded=loaded, n_display=3, interval=800, loop=True)

    print("No test selected. Exiting.")
    return


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

    params_info = toolbox.timeline_feasible_params(
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
    main()
