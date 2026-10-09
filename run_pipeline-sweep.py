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

The (a, b) pair the DG is constrained on (SPC) is written to
<dg-csv>/pair.json in stage 2 and handed to graph-run as its only flow
(--flows=a:b) in stage 3, so the network tests the very path constraint
the DG was generated for.
"""

import argparse
import csv
import copy
import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import networkx as nx
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


def _write_pair(args, a, b):
    """Record which pair the DG(s) under args.dg_csv were constrained on.
    Written after saveDGmatrices, which clears files in its entry dir."""
    args.dg_csv.mkdir(parents=True, exist_ok=True)
    (args.dg_csv / "pair.json").write_text(json.dumps({"pair": [a, b]}))


def _read_pair(args):
    manifest = args.dg_csv / "pair.json"
    if not manifest.exists():
        raise FileNotFoundError(
            f"{manifest} not found: cannot tell which pair the DG was built for. "
            f"Re-run the 'dg' stage."
        )
    a, b = json.loads(manifest.read_text())["pair"]
    return a, b


def _write_case_config(args, directory: Path, extra=None):
    config = dict(args.config_metadata)
    config["case_metadata"] = {
        **(extra or {}),
        "written_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "config.json").write_text(json.dumps(config, indent=2) + "\n")


class _DynamicGraphView:
    """Thin wrapper so a raw DynamicGraph frame list can be passed to
    toolbox.saveDGmatrices(), which expects an object exposing
    .DynamicGraph (like an SPCDynamicGraph instance), not a bare list.
    sweep_spc_generate()'s results store the raw list per point (same
    convention as sweep.py's sweep_mpc_generate()), so this bridges the
    two without changing either saveDGmatrices or sweep_spc_generate."""
    def __init__(self, dynamic_graph):
        self.DynamicGraph = dynamic_graph


def _dynamic_graph_properties(graphs, source, destination):
    """Measure achieved path uptime, up/down runs, and shortest-route retention."""
    route_by_frame = []
    for graph in graphs:
        try:
            route_by_frame.append(tuple(map(str, nx.shortest_path(graph, source, destination))))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            route_by_frame.append(None)

    up_runs, down_runs = [], []
    current_state = None
    run_length = 0
    for route in route_by_frame:
        state = route is not None
        if current_state is None:
            current_state = state
            run_length = 1
        elif state == current_state:
            run_length += 1
        else:
            (up_runs if current_state else down_runs).append(run_length)
            current_state = state
            run_length = 1
    if current_state is not None:
        (up_runs if current_state else down_runs).append(run_length)

    route_comparisons = 0
    route_repeats = 0
    has_alternative_path = False
    for graph, route in zip(graphs, route_by_frame):
        if route is None:
            continue
        for left, right in zip(route, route[1:]):
            alternate = graph.copy()
            alternate.remove_edge(left, right)
            if nx.has_path(alternate, source, destination):
                has_alternative_path = True
                break
        if has_alternative_path:
            break
    route_changes = 0
    for previous, current in zip(route_by_frame, route_by_frame[1:]):
        if previous is not None and current is not None:
            route_comparisons += 1
            if previous == current:
                route_repeats += 1
            else:
                route_changes += 1

    up_frames = sum(route is not None for route in route_by_frame)
    return {
        "frames": len(graphs),
        "up_frames": up_frames,
        "uptime_ratio": up_frames / len(graphs) if graphs else "",
        "up_runs": len(up_runs),
        "mean_up_run_frames": sum(up_runs) / len(up_runs) if up_runs else "",
        "max_up_run_frames": max(up_runs) if up_runs else "",
        "down_runs": len(down_runs),
        "path_identity_retention": (route_repeats / route_comparisons
                        if has_alternative_path and route_comparisons else float("nan")),
        "route_changes": route_changes,
        "distinct_routes": len({route for route in route_by_frame if route is not None}),
    }


def _read_dynamic_graph_frames(frames_csv: Path):
    """Reconstruct graphs from the exact serialized trace sent to ns-3."""
    with frames_csv.open(newline="") as stream:
        rows = list(csv.reader(stream))
    labels = [label.strip() for label in rows[0]]
    frames = []
    matrix_rows = []

    def append_frame():
        if not matrix_rows:
            return
        graph = nx.Graph()
        graph.add_nodes_from(labels)
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                if int(matrix_rows[i][j]):
                    graph.add_edge(labels[i], labels[j])
        frames.append(graph)
        matrix_rows.clear()

    for row in rows[1:]:
        if not row or not any(cell.strip() for cell in row):
            append_frame()
            continue
        matrix_rows.append([int(cell) for cell in row])
    append_frame()
    return frames


def _write_dynamic_graph_properties(directory, graphs, source, destination,
                                    param_name="run", param_value=0.0,
                                    requested_parameters=None):
    properties = _dynamic_graph_properties(graphs, source, destination)
    row = {
        "param_name": param_name,
        "param_value": param_value,
        "source": source,
        "destination": destination,
        **{f"requested_{key}": value for key, value in (requested_parameters or {}).items()},
        **properties,
    }
    output = directory / "properties.csv"
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return properties


# ----------------------------------------------------------------------
# Stage 1: static graph G
# ----------------------------------------------------------------------
def stage_generate_graph(args) -> Path:
    gen_dir = str(args.generator_script.resolve().parent)
    if gen_dir not in sys.path:
        sys.path.insert(0, gen_dir)

    if args.topology == "geodesic":
        generator_mod = load_module(args.generator_script, "geodesic_generator_exemple")
        from icosahedral_geodesic import create_icosahedral_geodesic_graph
        G = create_icosahedral_geodesic_graph(args.geo_m, args.geo_n)
        nodes = list(G.nodes())
        labels = [f"Node_{i}" for i in range(len(nodes))]
    else:
        ladder_mod = load_module(args.ladder_script, "ladder_maker")
        builders = {
            "ladder": ladder_mod.build_ladder_with_terminals,
            "diagonal-ladder": ladder_mod.build_diagonal_ladder_with_terminals,
            "two-lines": ladder_mod.build_two_lines_with_terminals,
            "line": ladder_mod.build_line_with_terminals,
        }
        G = builders[args.topology](args.topology_length)
        nodes = list(G.nodes())
        labels = [str(node) for node in nodes]

    # Make sure the output directory exists
    args.graph_csv.parent.mkdir(parents=True, exist_ok=True)

    adjacency = __import__("networkx").to_numpy_array(G, nodelist=nodes, dtype=int)
    import csv
    with args.graph_csv.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(labels)
        writer.writerows(adjacency.tolist())

    print(
        f"[1/4] Graph G (topology={args.topology}): "
        f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges -> "
        f"{args.graph_csv}"
    )
    return args.graph_csv


# ----------------------------------------------------------------------
# Stage 2: dynamic graph DG
# ----------------------------------------------------------------------
def _stage_generate_one_dynamic_graph(args, graph_csv: Path):
    """
    Returns a list of (label, dg_dir) pairs: one entry ("dg", args.dg_csv)
    for a single DG, or one entry per sweep point when --sweep is set.
    dg_dir is the directory frames.csv/nodes.txt were written into, so
    stage_run_ns3 can build --framesCsv=<dg_dir>/frames.csv from it
    directly, for every entry, the same way regardless of sweep mode.
    """
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

    args.dg_csv.parent.mkdir(parents=True, exist_ok=True)

    if not args.sweep:
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

        # entry_name is an absolute path here, which makes saveDGmatrices'
        # out_dir argument a no-op (os.path.join discards everything before
        # an absolute component) -- entry_dir ends up being args.dg_csv
        # itself. Left exactly as before; only the sweep branch below is new.
        toolbox.saveDGmatrices(DynaGA, "J2/Graph/", entry_name=str(args.dg_csv), overwrite=True, file_format="csv")
        serialized_graphs = _read_dynamic_graph_frames(args.dg_csv / "frames.csv")
        achieved = _write_dynamic_graph_properties(
            args.dg_csv, serialized_graphs, a, b,
            param_name="run", param_value=0.0,
            requested_parameters={
                "path_life": args.path_life,
                "stability": args.stability,
                "path_persistency": args.path_persistency,
            },
        )
        print(f"      Exported {stats['dyn_len']} frames -> {args.dg_csv}")
        print(f"      Achieved DG properties: {achieved}")
        _write_case_config(args, args.dg_csv, {"dg_seed": args.seed, "pair": [a, b]})
        _write_pair(args, a, b)
        # Fixed label ("dg"), not pair-derived: if 'dg' is later skipped via
        # --stages, we won't know which pair produced the file on disk, so
        # both the fresh-run and resumed-run label must be the same
        # constant or ns3-results ends up split across two paths for what
        # is really the same DG.
        return [("dg", args.dg_csv)]

    # --- sweep branch: one DG per step of --sweep-param ---
    fixed = {
        "path_life": args.path_life,
        "stability": args.stability,
        "pathPersistency": args.path_persistency,
    }
    fixed[args.sweep_param] = None  # the swept one

    sweep_results = dg_mod.sweep_spc_generate(
        G, a, b, frames=args.dg_frames, step=args.sweep_step,
        trials=args.trials, p_edge=args.p_edge, seed=args.seed,
        **fixed,
    )
    if not sweep_results:
        raise RuntimeError(
            f"Sweep over {args.sweep_param} for pair ({a}, {b}) produced no points "
            f"(no up/down frames, or no feasible range for {args.sweep_param} at the "
            f"fixed value given); try a different --seed, --pair-a/--pair-b, or --p_edge"
        )
    print(f"[2/4] DG sweep for pair ({a}, {b}) over {args.sweep_param}: "
          f"{len(sweep_results)} points")

    # Saved via saveDGmatrices per point (not toolbox.saveSweepMatrices):
    # stage_run_ns3 needs a predictable path per point to build
    # --framesCsv from, and saveSweepMatrices' own on-disk layout isn't
    # known here. entry_name is relative this time, so out_dir is
    # respected and each point lands at args.dg_csv/<label>/frames.csv.
    entries = []
    for point in sweep_results:
        label = f"{point['param_name']}_{point['param_value']:.4f}"
        point_dir = args.dg_csv / label
        toolbox.saveDGmatrices(_DynamicGraphView(point["dynamic_graph"]), str(args.dg_csv),
                                entry_name=label, overwrite=True, file_format="csv")
        serialized_graphs = _read_dynamic_graph_frames(point_dir / "frames.csv")
        achieved = _write_dynamic_graph_properties(
            point_dir, serialized_graphs, a, b,
            param_name=point["param_name"], param_value=point["param_value"],
            requested_parameters={
                "path_life": (point["param_value"] if point["param_name"] == "path_life"
                              else args.path_life),
                "stability": (point["param_value"] if point["param_name"] == "stability"
                              else args.stability),
                "path_persistency": (point["param_value"] if point["param_name"] == "pathPersistency"
                                     else args.path_persistency),
            },
        )
        print(f"      Exported {len(point['dynamic_graph'])} frames "
              f"({point['param_name']}={point['param_value']:.4f}) -> {point_dir}")
        print(f"      Achieved DG properties: {achieved}")
        _write_case_config(args, point_dir, {
            "dg_seed": args.seed,
            "pair": [a, b],
            "sweep_parameter": point["param_name"],
            "sweep_value": point["param_value"],
        })
        entries.append((label, point_dir))
    _write_pair(args, a, b)
    return entries


def stage_generate_dynamic_graph(args, graph_csv: Path):
    """Generate ``args.epoch`` independent DGs, preserving one SPC pair.

    Each graph uses its own derived timeline seed. The same pair is used for
    every graph so the resulting DGs and all replay runs test the same flow.
    """
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
        a, b = random.Random(args.seed).sample(node_list, 2)

    entries = []
    for graph_epoch in range(1, args.epoch + 1):
        graph_args = copy.copy(args)
        graph_args.dg_csv = args.dg_csv / f"graph_{graph_epoch:04d}"
        graph_args.pair_a, graph_args.pair_b = a, b
        graph_args.seed = args.seed + graph_epoch - 1
        for label, dg_dir in _stage_generate_one_dynamic_graph(graph_args, graph_csv):
            combined_label = f"graph_{graph_epoch:04d}__{label}"
            entries.append((combined_label, dg_dir))

    _write_pair(args, a, b)
    return entries


# ----------------------------------------------------------------------
# Stage 3: ns-3 replay
# ----------------------------------------------------------------------
def stage_run_ns3(args, dg_entries):
    """
    dg_entries: list of (label, dg_dir) pairs from stage_generate_dynamic_graph.

    Runs ``--epoch`` independent ns-3 replays per generated DG. Each graph
    epoch gets its own DG, and each replay epoch gets its own results directory,
    yielding ``args.epoch ** 2`` simulations per sweep point. Raw results remain available for statistical
    analysis::

        ns3-results/<label>/epoch_0001/trace_replay_results.csv
        ns3-results/<label>/epoch_0002/trace_replay_results.csv
        ...

    The first epoch is also copied to ``<label>/trace_replay_results.csv`` for
    backwards compatibility with the existing plotting script.

    The DG is reused across epochs; the ns-3 seed is advanced by the epoch
    number so the simulation runs are independent while testing the same DG.
    """
    if args.ns3_dir is None:
        raise SystemExit("--ns3-dir is required to run the 'sim' stage")

    a, b = _read_pair(args)
    print(f"[3/4] Flow under test (DG's SPC pair): {a} -> {b}")
    print(f"[3/4] Running {args.epoch} epoch(s) per DG/sweep point")

    results = []
    for label, dg_dir in dg_entries:
        results_root = args.work_dir / "ns3-results" / label
        results_root.mkdir(parents=True, exist_ok=True)

        for epoch in range(1, args.epoch + 1):
            epoch_dir = results_root / f"epoch_{epoch:04d}"
            epoch_dir.mkdir(parents=True, exist_ok=True)
            graph_epoch = int(label.split("__", 1)[0].split("_")[1])
            epoch_seed = args.seed + (graph_epoch - 1) * args.epoch + epoch - 1

            routing_arg = args.routing
            if args.include_static_baseline and "static" not in routing_arg.split(","):
                routing_arg = ("olsr,aodv,dsdv,static" if routing_arg == "all"
                               else f"{routing_arg},static")
            ns3_args = (
                f"graph-run --framesCsv={dg_dir}/frames.csv --outDir={epoch_dir} "
                f"--routing={routing_arg} --flows={a}:{b} "
                f"--dataRate={args.data_rate} --packetSize={args.packet_size} "
                f"--lossThresholdDb={args.loss_threshold_db} "
                f"--interpolate={'true' if args.interpolate else 'false'} "
                f"--defaultLossDb={args.default_loss_db} --txPowerDbm={args.tx_power_dbm} "
                f"--linkUpLossDb={args.link_up_loss_db} --linkDownLossDb={args.link_down_loss_db} "
                f"--fps={args.fps} "
                f"--seed={epoch_seed}"
            )
            if args.warmup > 0:
                ns3_args += f" --warmup={args.warmup} --warmupMode={args.warmup_mode}"
            if args.dump_routes:
                ns3_args += " --dumpRoutes=true"
            source_hash = args.config_metadata.get("source_git_hash")
            ns3_commit = args.config_metadata.get("ns3_commit")
            if source_hash:
                ns3_args += f" --sourceGitHash={source_hash}"
            if ns3_commit:
                ns3_args += f" --ns3Commit={ns3_commit}"
            replay_config = dict(args.config_metadata)
            replay_config.update({
                "graph_label": label,
                "replay_epoch": epoch,
                "ns3_seed": epoch_seed,
                "flow_pair": [a, b],
                "routing_arg": routing_arg,
                "replay_timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            })
            (epoch_dir / "config.json").write_text(json.dumps(replay_config, indent=2) + "\n")
            print(
                f'[3/4] Running ({label}, epoch {epoch}/{args.epoch}, seed={epoch_seed}): '
                f'./ns3 run "{ns3_args}"  (cwd={args.ns3_dir})'
            )
            subprocess.run(["./ns3", "run", ns3_args], cwd=str(args.ns3_dir), check=True)

            results_csv = epoch_dir / "trace_replay_results.csv"
            if not results_csv.exists():
                raise RuntimeError(f"ns-3 run finished but {results_csv} was not produced")
            replay_config["replay_finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            (epoch_dir / "config.json").write_text(json.dumps(replay_config, indent=2) + "\n")

            if epoch == 1:
                shutil.copy2(results_csv, results_root / "trace_replay_results.csv")

        results.append((label, results_root / "trace_replay_results.csv"))
    return results


# ----------------------------------------------------------------------
# Stage 4: plots
#
# plot.py expects --results to be the directory containing the individual
# sweep-point directories. stage_run_ns3 keeps a backwards-compatible
# trace_replay_results.csv at that level while storing every epoch below it:
#
#   ns3-results/
#       stability_0.1000/
#           trace_replay_results.csv       # epoch 1, for plot.py
#           epoch_0001/trace_replay_results.csv
#           epoch_0002/trace_replay_results.csv
#           ...
#
# This keeps plotting compatible while making all epochs available for
# statistical analysis.
# ----------------------------------------------------------------------
def stage_plot_results(args, label: str, results_csv: Path):
    if not args.plot_script.exists():
        print(f"[4/4] Skipping plots ({label}): "
              f"{args.plot_script} does not exist yet")
        return None

    # results_csv is something like:
    #
    #   <work_dir>/ns3-results/stability_0.3000/trace_replay_results.csv
    #
    # plot.py needs:
    #
    #   <work_dir>/ns3-results/
    #
    # so it can discover ALL sweep points.
    results_root = results_csv.parent.parent

    # Put all plots for the sweep in one directory rather than creating
    # a separate plot directory for every individual sweep point.
    plot_out_dir = args.work_dir / "plots"
    plot_out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[4/4] Running ({label}): "
        f"python3 {args.plot_script} "
        f"--results {results_root} "
        f"--outDir {plot_out_dir} "
        f"--dg-properties {args.dg_csv}"
    )

    subprocess.run(
        [
            sys.executable,
            str(args.plot_script),
            "--results", str(results_root),
            "--outDir", str(plot_out_dir),
            "--dg-properties", str(args.dg_csv),
        ],
        check=True,
    )

    return plot_out_dir

# ----------------------------------------------------------------------
# Resuming a skipped stage: there's no saved manifest of dg_entries /
# results to read back, so these reconstruct the same (label, path)
# lists from whatever's already on disk, keyed the same way the stages
# above wrote them.
# ----------------------------------------------------------------------
def _discover_dg_entries(args):
    if args.sweep:
        entries = sorted(
            ("__".join(p.parent.relative_to(args.dg_csv).parts), p.parent)
            for p in args.dg_csv.rglob("frames.csv")
        )
        if not entries:
            raise FileNotFoundError(
                f"--stages skips 'dg' but no sweep points with frames.csv were found "
                f"under {args.dg_csv}"
            )
        return entries
    entries = sorted(
        (p.parent.name, p.parent)
        for p in args.dg_csv.glob("graph_*/frames.csv")
    )
    if not entries:
        raise FileNotFoundError(
            f"--stages skips 'dg' but no graph_*/frames.csv files were found under {args.dg_csv}"
        )
    return entries


def _discover_results(args, dg_entries):
    results = []
    for label, _ in dg_entries:
        results_root = args.work_dir / "ns3-results" / label
        results_csv = results_root / "trace_replay_results.csv"
        if not results_csv.exists():
            raise FileNotFoundError(
                f"--stages skips 'sim' but {results_csv} does not exist"
            )

        for epoch in range(1, args.epoch + 1):
            epoch_csv = results_root / f"epoch_{epoch:04d}" / "trace_replay_results.csv"
            if not epoch_csv.exists():
                raise FileNotFoundError(
                    f"--stages skips 'sim' but epoch {epoch} result "
                    f"{epoch_csv} does not exist"
                )

        results.append((label, results_csv))
    return results


# ----------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="G -> DG -> ns-3 replay -> plots supervisor")
    p.add_argument("--work-dir", type=Path, default=None,
                   help="Root output directory for every stage's files")
    p.add_argument("--stages", default="graph,dg,sim,plot",
                   help="Comma list of stages to run: graph,dg,sim,plot")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--epoch", type=int, default=1,
                   help="Number of independent DGs and ns-3 runs per DG/sweep point "
                        "(default: 1), giving epoch squared simulations. DG and ns-3 "
                        "seeds are derived from --seed; results are stored under "
                        "ns3-results/<graph-and-point-label>/epoch_NNNN/")

    # stage 1: graph
    g = p.add_argument_group("stage 1: static graph")
    g.add_argument("--generator-script",type=Path,default=Path("J2/geodesic-generator-exemple.py"))
    g.add_argument("--ladder-script", type=Path, default=Path("J2/ladder-maker.py"),
                   help="Module containing the ladder topology builders")
    g.add_argument("--topology", choices=["geodesic", "ladder", "diagonal-ladder", "two-lines", "line"],
                   default="geodesic", help="Static graph topology for stage 1")
    g.add_argument("--topology-length", type=int, default=7,
                   help="Length parameter for ladder-maker topologies")
    g.add_argument("--geo-m", type=int, default=2, help="Class-I/III geodesic parameter m")
    g.add_argument("--geo-n", type=int, default=0, help="Class-II/III geodesic parameter n")
    g.add_argument("--graph-csv", type=Path, default=None,
                   help="Defaults to <work-dir>/graph.csv")

    # stage 2: dynamic graph
    d = p.add_argument_group("stage 2: dynamic graph")
    d.add_argument("--dg-script",type=Path,default=Path("J2/G2DG-SPC.py"))
    d.add_argument("--dg-csv", type=Path, default=None,
                   help="Defaults to <work-dir>/dynamic_frames")
    d.add_argument("--pair-a", default=None, help="Sender node label, e.g. Node_3")
    d.add_argument("--pair-b", default=None, help="Receiver node label, e.g. Node_17")
    d.add_argument("--trials", type=int, default=500)
    d.add_argument("--p_edge", type=float, default=0.5)
    d.add_argument("--path-persistency", type=float, default=1.0)
    d.add_argument("--dg-frames", type=int, default=60)
    d.add_argument("--path-life", type=float, default=1.0)
    d.add_argument("--stability", type=float, default=0.8)
    d.add_argument("--fps", type=float, default=1.0,
                   help="DynamicGraph frames per second -> maps frame index to seconds")
    d.add_argument("--link-loss-db", type=float, default=40.0,
                   help="Loss (dB) written for an edge present in a DG frame; "
                        "must be below --loss-threshold-db to count as in range")
    d.add_argument("--sweep", action="store_true",
                   help="Instead of one DG, sweep --sweep-param over its feasible range "
                        "(see G2DG-SPC's sweep_spc_generate) and run the ns-3 replay once "
                        "per point")
    d.add_argument("--sweep-param", choices=["path_life", "stability", "pathPersistency"],
                   default="stability",
                   help="Which parameter to sweep; the other two are held fixed at their "
                        "--path-life/--stability/--path-persistency values (default: sweep "
                        "stability, path_life and path_persistency fixed)")
    d.add_argument("--sweep-step", type=float, default=0.1,
                   help="Step size for the swept parameter")

    # stage 3: ns-3
    n = p.add_argument_group("stage 3: ns-3 replay")
    n.add_argument("--ns3-dir", type=Path, default=None,
                   help="ns-3 root directory containing ./ns3, with graph-run.cc "
                        "registered as a program (e.g. under scratch/)")
    n.add_argument("--routing", default="all", help="olsr|aodv|dsdv|all, or a comma list")
    n.add_argument("--data-rate", default="50kbps")
    n.add_argument("--packet-size", type=int, default=1024)
    n.add_argument("--loss-threshold-db", dest="loss_threshold_db", type=float, default=150.0)
    n.add_argument("--interpolate", dest="interpolate", action="store_true", default=True)
    n.add_argument("--no-interpolate", dest="interpolate", action="store_false")
    n.add_argument("--default-loss-db", dest="default_loss_db", type=float, default=1e6)
    n.add_argument("--tx-power-dbm", dest="tx_power_dbm", type=float, default=20.0)
    n.add_argument("--link-up-loss-db", dest="link_up_loss_db", type=float, default=10.0,
                   help="Loss (dB) passed to graph-run.cc for a 1 in the adjacency matrix")
    n.add_argument("--link-down-loss-db", dest="link_down_loss_db", type=float, default=125.0,
                   help="Loss (dB) passed to graph-run.cc for a 0 in the adjacency matrix")
    n.add_argument("--warmup", type=float, default=0.0,
                   help="Seconds of warm-up before the trace (traffic starts after it, topology "
                        "held up). Defaults to 0 for legacy behavior; the v2 campaign runner "
                        "passes 45 s by default")
    n.add_argument("--warmup-mode", choices=["first", "union"], default="first",
                   help="Warm-up topology: 'first' = trace frame 0 (recommended), 'union' = every "
                        "link ever up (can pre-build routes that the trace then breaks)")
    n.add_argument("--dump-routes", action="store_true",
                   help="Write 1 Hz routing tables and tx/rx times per epoch (diagnostics)")
    n.add_argument("--include-static-baseline", action="store_true",
                   help="Add the protocol-free oracle-path static routing ceiling run")

    # stage 4: plots
    pl = p.add_argument_group("stage 4: plots")
    pl.add_argument("--plot-script", type=Path, default=Path("J2/plot.py"))

    args = p.parse_args()
    # Resolve every path argument to absolute *before* any stage runs.
    if args.work_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        args.work_dir = Path("J2") / f"run_{stamp}"
    args.work_dir = args.work_dir.resolve()
    script_root = Path(__file__).resolve().parent
    def resolve_script(path):
        resolved = path.resolve()
        return resolved if resolved.exists() else script_root / path.name
    args.generator_script = resolve_script(args.generator_script)
    args.ladder_script = resolve_script(args.ladder_script)
    args.dg_script = resolve_script(args.dg_script)
    args.plot_script = resolve_script(args.plot_script)
    if args.ns3_dir is not None:
        args.ns3_dir = args.ns3_dir.resolve()
    if args.epoch < 1:
        p.error("--epoch must be >= 1")
    if args.warmup < 0:
        p.error("--warmup must be >= 0")

    args.work_dir.mkdir(parents=True, exist_ok=True)
    if args.graph_csv is None:
        args.graph_csv = args.work_dir / "graph.csv"
    else:
        args.graph_csv = args.graph_csv.resolve()
    if args.dg_csv is None:
        args.dg_csv = args.work_dir / "dynamic_frames"
    else:
        args.dg_csv = args.dg_csv.resolve()
    args.dg_csv.mkdir(parents=True, exist_ok=True)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    metadata = {key: str(value) if isinstance(value, Path) else value
                for key, value in vars(args).items()}
    metadata["run_timestamp"] = datetime.now().astimezone().isoformat(timespec="seconds")
    def git_revision(directory):
        if not directory:
            return None
        result = subprocess.run(["git", "-C", str(directory), "rev-parse", "HEAD"],
                                capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    def git_dirty(directory):
        if not directory:
            return None
        result = subprocess.run(["git", "-C", str(directory), "status", "--porcelain"],
                                capture_output=True, text=True)
        return bool(result.stdout.strip()) if result.returncode == 0 else None
    def file_sha256(path):
        if not path or not Path(path).is_file():
            return None
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    ns3_version = None
    if args.ns3_dir is not None and (args.ns3_dir / "VERSION").is_file():
        ns3_version = (args.ns3_dir / "VERSION").read_text().strip()
    args.config_metadata = {
        "parameters": metadata,
        "source_git_hash": git_revision(Path(__file__).resolve().parent),
        "source_git_dirty": git_dirty(Path(__file__).resolve().parent),
        "ns3_commit": git_revision(args.ns3_dir) if args.ns3_dir else None,
        "ns3_version": ns3_version,
        "source_hashes_sha256": {
            "pipeline": file_sha256(Path(__file__).resolve()),
            "dg_generator": file_sha256(args.dg_script),
            "topology_generator": file_sha256(args.generator_script),
            "ladder_generator": file_sha256(args.ladder_script),
            "graph_run_cc": file_sha256(args.ns3_dir / "scratch" / "graph-run.cc")
                            if args.ns3_dir else None,
        },
        "config_created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    (args.work_dir / "config.json").write_text(json.dumps(args.config_metadata, indent=2) + "\n")
    (args.work_dir / "run_args.txt").write_text(
        "Pipeline run configuration\n"
        + "=" * 28 + "\n"
        + "\n".join(f"{key}: {value}" for key, value in metadata.items())
        + "\n"
    )
    return args



def main():
    args = parse_args()
    stages = {s.strip() for s in args.stages.split(",") if s.strip()}

    graph_csv = args.graph_csv

    if "graph" in stages:
        graph_csv = stage_generate_graph(args)
    elif not graph_csv.exists():
        raise FileNotFoundError(f"--stages skips 'graph' but {graph_csv} does not exist")

    if "dg" in stages:
        dg_entries = stage_generate_dynamic_graph(args, graph_csv)
    else:
        dg_entries = _discover_dg_entries(args)

    if "sim" in stages:
        results = stage_run_ns3(args, dg_entries)
    elif "plot" in stages:
        results = _discover_results(args, dg_entries)
    else:
        results = []

    if "plot" in stages:
        if results:
            stage_plot_results(args, "aggregate", results[0][1])

    print("\nPipeline complete.")
    print(f"  graph: {graph_csv}")
    for label, dg_dir in dg_entries:
        print(f"  dg[{label}]:      {dg_dir}")
    for label, results_csv in results:
        print(f"  results[{label}]: {results_csv}")


if __name__ == "__main__":
    main()