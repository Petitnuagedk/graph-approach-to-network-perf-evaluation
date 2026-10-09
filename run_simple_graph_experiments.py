#!/usr/bin/env python3
"""Run the starter SPC experiment matrix on small, interpretable graphs.

By default this generates DGs and records their achieved properties. Pass
``--ns3-dir`` to run simulations and plots at the same time. A later simulation
pass can reuse the DGs with ``--stages sim,plot``.
"""

import argparse
import subprocess
import sys
from pathlib import Path

PIPELINE = Path(__file__).with_name("run_pipeline-sweep.py")
TOPOLOGIES = ("line", "two-lines", "ladder")
SWEEPS = {
    "path_life": {"path_life": None, "stability": 0.8, "path_persistency": 0.75},
    "stability": {"path_life": 0.5, "stability": None, "path_persistency": 0.75},
    "pathPersistency": {"path_life": 0.5, "stability": 0.8, "path_persistency": None},
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", type=Path, default=Path("simple-graph-experiments-v2"))
    parser.add_argument("--ns3-dir", type=Path, default=None)
    parser.add_argument("--stages", default=None,
                        help="Pipeline stages; defaults to graph,dg without --ns3-dir, "
                             "or graph,dg,sim,plot with it")
    parser.add_argument("--epoch", type=int, default=5,
                        help="DG realizations and replays per DG (N gives N squared runs per point)")
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--p-edge", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--warmup", type=float, default=45.0,
                        help="Routing warm-up seconds for v2 runs (0 disables warm-up)")
    parser.add_argument("--warmup-mode", choices=["first", "union"], default="first")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--properties-only", action="store_true",
                        help="Plot existing properties.csv files without regenerating DGs")
    args = parser.parse_args()
    args.work_root = args.work_root.resolve()
    if args.ns3_dir is not None:
        args.ns3_dir = args.ns3_dir.resolve()
    if args.epoch < 1:
        parser.error("--epoch must be >= 1")
    if args.trials < 1 or args.frames < 1:
        parser.error("--trials and --frames must be >= 1")
    if not 0.0 <= args.p_edge <= 1.0:
        parser.error("--p-edge must be in [0, 1]")
    if args.stages is None:
        args.stages = "graph,dg,sim,plot" if args.ns3_dir else "graph,dg"
    if "sim" in args.stages.split(",") and args.ns3_dir is None:
        parser.error("--ns3-dir is required when --stages includes sim")
    return args


def main():
    args = parse_args()
    if args.properties_only:
        plot_script = PIPELINE.with_name("plot.py")
        for topology in TOPOLOGIES:
            for sweep_param in SWEEPS:
                work_dir = args.work_root / topology / sweep_param
                command = [
                    sys.executable, str(plot_script),
                    "--dg-properties", str(work_dir / "dynamic_frames"),
                    "--outDir", str(work_dir / "plots"),
                    "--dg-properties-only",
                ]
                print(f"\n=== Plot existing {topology}/{sweep_param} DG properties ===", flush=True)
                if args.dry_run:
                    print(" ".join(command), flush=True)
                else:
                    subprocess.run(command, check=True, cwd=PIPELINE.parent.parent)
        return

    for topology in TOPOLOGIES:
        for sweep_param, fixed in SWEEPS.items():
            work_dir = args.work_root / topology / sweep_param
            command = [
                sys.executable, str(PIPELINE),
                "--work-dir", str(work_dir),
                "--stages", args.stages,
                "--topology", topology,
                "--topology-length", "3",
                "--pair-a", "S", "--pair-b", "R",
                "--sweep", "--sweep-param", sweep_param,
                "--sweep-step", "0.25" if sweep_param == "pathPersistency" else "0.2",
                "--trials", str(args.trials),
                "--p_edge", str(args.p_edge),
                "--dg-frames", str(args.frames),
                "--epoch", str(args.epoch),
                "--seed", str(args.seed),
                "--path-life", str(fixed["path_life"] or 0.5),
                "--stability", str(fixed["stability"] or 0.8),
                "--path-persistency", str(fixed["path_persistency"] or 0.75),
                "--warmup", str(args.warmup),
                "--warmup-mode", args.warmup_mode,
                "--link-down-loss-db", "125",
                "--include-static-baseline",
            ]
            if args.ns3_dir is not None:
                command.extend(("--ns3-dir", str(args.ns3_dir)))
            print(f"\n=== {topology}: sweep {sweep_param} ===", flush=True)
            print(" ".join(command), flush=True)
            if not args.dry_run:
                subprocess.run(command, check=True, cwd=PIPELINE.parent.parent)

    if args.dry_run:
        print("\nDry run complete; no pipeline stages were executed.")
    else:
        print(f"\nExperiment matrix complete: {args.work_root}")
        print("Each topology/parameter combination has its own run_args.txt, DG frames, "
              "and measured properties.csv files.")


if __name__ == "__main__":
    main()
