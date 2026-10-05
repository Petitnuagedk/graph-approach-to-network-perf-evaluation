#!/usr/bin/env python3
"""
run_pipeline.py

Supervisor for the full pipeline:

    1. generate a static graph G              (icosahedral_geodesic, via
                                                 geodesic-generator-exemple.py)
    2. generate a dynamic graph DG from G      (G-to-DG-geo.py)
    3. run the ns-3 replay against DG          (graph-run.cc)
    4. turn the ns-3 results into plots        (plot_results.py -- not built yet)

Each stage writes into --work-dir so a later run can skip earlier stages
with --stages and pick up existing files.

Stage scripts are loaded by file path (importlib), not `import`, since
their filenames contain hyphens and can't be imported normally.

TODO : Replace a-b pair with the same flow pairs used in the ns-3 replay stage, so that the DG is built for the same flows that are actually simulated.
"""

import argparse
import importlib.util
import random
import subprocess
import sys
from pathlib import Path
import yadygaga.toolbox as toolbox

def load_module(path: Path, name: str):
    """Load a .py file as a module by path, whatever its filename is."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ----------------------------------------------------------------------
# Stage 1: static graph G
# ----------------------------------------------------------------------
def stage_generate_graph(args) -> Path:
    # All pipeline Python files live in J2/.
    gen_dir = str(args.generator_script.resolve().parent)
    if gen_dir not in sys.path:
        sys.path.insert(0, gen_dir)

    generator_mod = load_module(
        args.generator_script,
        "geodesic_generator_exemple"
    )

    from icosahedral_geodesic import create_icosahedral_geodesic_graph

    G = create_icosahedral_geodesic_graph(args.geo_m, args.geo_n)

    # Make sure the output directory exists
    args.graph_csv.parent.mkdir(parents=True, exist_ok=True)

    generator_mod.save_adjacency_matrix_csv(G, str(args.graph_csv))

    print(
        f"[1/4] Graph G (m={args.geo_m}, n={args.geo_n}): "
        f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges -> "
        f"{args.graph_csv}"
    )
    return args.graph_csv


# ----------------------------------------------------------------------
# Stage 2: dynamic graph DG
# ----------------------------------------------------------------------
def stage_generate_dynamic_graph(args, graph_csv: Path) -> Path:
    dg_mod = load_module(args.dg_script, "J2.G2DG-SPC")

    G = dg_mod.load_graph_from_adj_csv(str(graph_csv))
    node_list = list(G.nodes())
    if len(node_list) < 2:
        raise RuntimeError("Loaded graph has fewer than two nodes; cannot pick a pair")

    if args.pair_a is not None and args.pair_b is not None:
        a, b = args.pair_a, args.pair_b
        if a not in G or b not in G:
            raise ValueError(f"--pair-a/--pair-b ({a}, {b}) are not node labels in {graph_csv}")
    else:
        rnd = random.Random(args.seed)
        a, b = rnd.sample(node_list, 2)

    DynaGA, stats = dg_mod.build_dynamic_graph(
        G, a, b,
        trials=args.trials, p_edge=args.p_edge,
        pathPersistency=args.path_persistency,
        frames=args.dg_frames, path_life=args.path_life,
        stability=args.stability, seed=args.seed,
    )
    if DynaGA is None:
        raise RuntimeError(
            f"No up/down frames found for pair ({a}, {b}) after {args.trials} trials; "
            f"try a different --seed, --pair-a/--pair-b, or --p_edge"
        )
    print(f"[2/4] DG for pair ({a}, {b}): {stats}")

    args.dg_csv.parent.mkdir(parents=True, exist_ok=True)
    toolbox.saveDGmatrices(DynaGA, "J2/Graph/", entry_name=str(args.dg_csv), overwrite=True, file_format="csv")
    # dg_mod.export_dynamic_graph_to_trace_csv(
    #     DynaGA, node_list, str(args.dg_csv),
    #     fps=args.fps, link_loss_db=args.link_loss_db,
    # )
    print(f"      Exported {stats['dyn_len']} frames -> {args.dg_csv}")
    return args.dg_csv


# ----------------------------------------------------------------------
# Stage 3: ns-3 replay
# ----------------------------------------------------------------------
def stage_run_ns3(args, dg_csv: Path) -> Path:
    if args.ns3_dir is None:
        raise SystemExit("--ns3-dir is required to run the 'sim' stage")

    ns3_out_dir = args.work_dir / "ns3-results"
    ns3_out_dir.mkdir(parents=True, exist_ok=True)

    ns3_args = (
        f"graph-run --framesCsv={dg_csv}/frames.csv --outDir={ns3_out_dir} "  #dynamic_frames
        f"--routing={args.routing} --numFlows={args.num_flows} "
        f"--dataRate={args.data_rate} --packetSize={args.packet_size} "
        f"--lossThresholdDb={args.loss_threshold_db} "
        f"--interpolate={'true' if args.interpolate else 'false'} "
        f"--defaultLossDb={args.default_loss_db} --txPowerDbm={args.tx_power_dbm} "
        f"--linkUpLossDb={args.link_up_loss_db} --linkDownLossDb={args.link_down_loss_db} "
        f"--fps={args.fps} "
        f"--seed={args.seed}"
    )
    print(f'[3/4] Running: ./ns3 run "{ns3_args}"  (cwd={args.ns3_dir})')
    subprocess.run(["./ns3", "run", ns3_args], cwd=str(args.ns3_dir), check=True)

    results_csv = ns3_out_dir / "trace_replay_results.csv"
    if not results_csv.exists():
        raise RuntimeError(f"ns-3 run finished but {results_csv} was not produced")
    return results_csv


# ----------------------------------------------------------------------
# Stage 4: plots -- not built yet, this just documents the interface
# stage_plot_results will call once plot_results.py exists:
#
#   python3 plot_results.py --results <trace_replay_results.csv> --outDir <plots dir>
#
# reading the columns graph-run.cc writes: scenario, protocol, wall_time_s,
# cpu_time_s, ip_tx_cb_calls, ip_rx_cb_calls, frame_apply_calls, routing_tx,
# routing_rx, pdr, goodput_mbps, eed_mean_s, app_tx_pkts, app_rx_pkts,
# ip_drop_no_route, ip_drop_route_err, phy_tx_drop, phy_rx_drop.
# ----------------------------------------------------------------------
def stage_plot_results(args, results_csv: Path):
    if not args.plot_script.exists():
        print(f"[4/4] Skipping plots: {args.plot_script} does not exist yet")
        return None
    plot_out_dir = args.work_dir / "plots"
    plot_out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[4/4] Running: python3 {args.plot_script} --results {results_csv} --outDir {plot_out_dir}")
    subprocess.run(
        [sys.executable, str(args.plot_script),
         "--results", str(results_csv), "--outDir", str(plot_out_dir)],
        check=True,
    )
    return plot_out_dir

# ----------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="G -> DG -> ns-3 replay -> plots supervisor")
    p.add_argument("--work-dir", type=Path, default=Path("pipeline-out"),
                   help="Root output directory for every stage's files")
    p.add_argument("--stages", default="graph,dg,sim,plot",
                   help="Comma list of stages to run: graph,dg,sim,plot")
    p.add_argument("--seed", type=int, default=42)

    # stage 1: graph
    g = p.add_argument_group("stage 1: static graph")
    g.add_argument("--generator-script",type=Path,default=Path("J2/geodesic-generator-exemple.py"))
    g.add_argument("--geo-m", type=int, default=3, help="Class-I/III geodesic parameter m")
    g.add_argument("--geo-n", type=int, default=0, help="Class-II/III geodesic parameter n")
    g.add_argument("--graph-csv", type=Path, default="J2/Graph/graph.csv",
                   help="Defaults to J2/Graph/graph.csv")

    # stage 2: dynamic graph
    d = p.add_argument_group("stage 2: dynamic graph")
    d.add_argument("--dg-script",type=Path,default=Path("J2/G2DG-SPC.py"))
    d.add_argument("--dg-csv", type=Path, default="J2/Graph/dynamic_frames",
                   help="Defaults to J2/Graph/dynamic_frames")
    d.add_argument("--pair-a", default=None, help="Sender node label, e.g. Node_3")
    d.add_argument("--pair-b", default=None, help="Receiver node label, e.g. Node_17")
    d.add_argument("--trials", type=int, default=500)
    d.add_argument("--p_edge", type=float, default=0.5)
    d.add_argument("--path-persistency", type=float, default=0.9)
    d.add_argument("--dg-frames", type=int, default=60)
    d.add_argument("--path-life", type=float, default=0.4)
    d.add_argument("--stability", type=float, default=0.8)
    d.add_argument("--fps", type=float, default=1.0,
                   help="DynamicGraph frames per second -> maps frame index to seconds")
    d.add_argument("--link-loss-db", type=float, default=40.0,
                   help="Loss (dB) written for an edge present in a DG frame; "
                        "must be below --loss-threshold-db to count as in range")

    # stage 3: ns-3
    n = p.add_argument_group("stage 3: ns-3 replay")
    n.add_argument("--ns3-dir", type=Path, default=None,
                   help="ns-3 root directory containing ./ns3, with graph-run.cc "
                        "registered as a program (e.g. under scratch/)")
    n.add_argument("--routing", default="all", help="olsr|aodv|dsdv|all, or a comma list")
    n.add_argument("--num-flows", dest="num_flows", type=int, default=10)
    n.add_argument("--data-rate", default="50kbps")
    n.add_argument("--packet-size", type=int, default=1024)
    n.add_argument("--loss-threshold-db", dest="loss_threshold_db", type=float, default=150.0)
    n.add_argument("--interpolate", dest="interpolate", action="store_true", default=True)
    n.add_argument("--no-interpolate", dest="interpolate", action="store_false")
    n.add_argument("--default-loss-db", dest="default_loss_db", type=float, default=1e6)
    n.add_argument("--tx-power-dbm", dest="tx_power_dbm", type=float, default=20.0)
    n.add_argument("--link-up-loss-db", dest="link_up_loss_db", type=float, default=10.0,
                   help="Loss (dB) passed to graph-run.cc for a 1 in the adjacency matrix")
    n.add_argument("--link-down-loss-db", dest="link_down_loss_db", type=float, default=200.0,
                   help="Loss (dB) passed to graph-run.cc for a 0 in the adjacency matrix")

    # stage 4: plots
    pl = p.add_argument_group("stage 4: plots")
    pl.add_argument("--plot-script", type=Path, default=Path("J2/plot.py"))

    args = p.parse_args()
    # Resolve every path argument to absolute *before* any stage runs.
    args.work_dir = args.work_dir.resolve()
    args.generator_script = args.generator_script.resolve()
    args.dg_script = args.dg_script.resolve()
    args.plot_script = args.plot_script.resolve()
    if args.ns3_dir is not None:
        args.ns3_dir = args.ns3_dir.resolve()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    if args.graph_csv is None:
        args.graph_csv = args.work_dir / "graph.csv"
    else:
        args.graph_csv = args.graph_csv.resolve()
    if args.dg_csv is None:
        args.dg_csv = args.work_dir / "dynamic_frames.csv"
    else:
        args.dg_csv = args.dg_csv.resolve()
    return args



def main():
    args = parse_args()
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}

    graph_csv = args.graph_csv
    dg_csv = args.dg_csv
    results_csv = args.work_dir / "J2" / "ns3-results" / "trace_replay_results.csv"

    if "graph" in stages:
        graph_csv = stage_generate_graph(args)
    elif not graph_csv.exists():
        raise FileNotFoundError(f"--stages skips 'graph' but {graph_csv} does not exist")

    if "dg" in stages:
        dg_csv = stage_generate_dynamic_graph(args, graph_csv)
    elif not dg_csv.exists():
        raise FileNotFoundError(f"--stages skips 'dg' but {dg_csv} does not exist")

    if "sim" in stages:
        results_csv = stage_run_ns3(args, dg_csv)
    elif not results_csv.exists():
        raise FileNotFoundError(f"--stages skips 'sim' but {results_csv} does not exist")

    if "plot" in stages:
        stage_plot_results(args, results_csv)

    print("\nPipeline complete.")
    print(f"  graph:   {graph_csv}")
    print(f"  dg:      {dg_csv}")
    print(f"  results: {results_csv}")


if __name__ == "__main__":
    main()
