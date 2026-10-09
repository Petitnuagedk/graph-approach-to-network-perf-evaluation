import math
import os
import json
import numpy as np
import glob
import csv
import networkx as nx
from .visualizer import _load_dynamic_graph_from_dir
import logging
import datetime

# simple per-out_dir debug logger (writes into the out_dir folder)
def _make_logger(out_dir):
    log_path = os.path.join(out_dir, "toolbox_debug.log")
    def _log(msg):
        ts = datetime.datetime.now().isoformat()
        try:
            with open(log_path, "a", encoding="utf-8") as lf:
                lf.write(f"{ts} {msg}\n")
        except Exception:
            # best-effort only
            pass
    return _log


def timelineFeasibleParams(
    frames: int, path_life: float = None, stability: float = None
):
    """
    Given number of frames `frames` and either `path_life` (alpha in [0,1]) or
    `stability` (s in [0,1]), return feasible values/ranges for the other parameter.

    Definitions used:
    - l = frames
    - k = number of frames where the path exists = ceil(alpha * l)
    - transitions t is number of adjacent frame changes (0 <= t <= l-1)
    - stability s is defined as s = 1 - t/(l - 1)  (fraction of unchanged adjacencies)

    Feasible transitions for a given k:
    - if k == 0 or k == l: t_min = 0, t_max = 0
    - else: t_min = 2 (one contiguous run of presences and one run of absences)
            t_max = min(l - 1, 2 * min(k, l - k)) (alternating as much as counts allow)

    Returns a dict with keys:
      - 'frames'
      - 'given' -> ('path_life', value) or ('stability', value)
      - 'feasible_stability' -> (s_min, s_max) if path_life provided
      - 'feasible_path_life' -> (alpha_min, alpha_max) if stability provided
      - 'possible_k' -> list of integer k values compatible with given stability (when stability provided)
    """
    l = int(frames)
    if l <= 0:
        raise ValueError("frames must be > 0")

    if (path_life is None) == (stability is None):
        raise ValueError("Provide exactly one of path_life or stability")

    # handle trivial single-frame case
    if l == 1:
        if path_life is not None:
            k = math.ceil(path_life * l)
            # stability undefined (no adjacencies) -> treat as 1.0
            return {
                "frames": l,
                "given": ("path_life", path_life),
                "feasible_stability": (1.0, 1.0),
                "k": k,
            }
        else:
            # stability given -> only path_life options are 0 or 1 depending on desired k
            return {
                "frames": l,
                "given": ("stability", stability),
                "feasible_path_life": (0.0, 1.0),
                "possible_k": [0, 1],
            }

    if path_life is not None:
        if not (0.0 <= path_life <= 1.0):
            raise ValueError("path_life must be in [0,1]")
        k = math.ceil(path_life * l)

        # compute t_min, t_max
        if k == 0 or k == l:
            t_min = t_max = 0
        else:
            t_min = 2
            t_max = min(l - 1, 2 * min(k, l - k))

        s_min = 1 - (t_max / (l - 1))
        s_max = 1 - (t_min / (l - 1))
        # clamp to [0,1]
        s_min = max(0.0, min(1.0, s_min))
        s_max = max(0.0, min(1.0, s_max))

        return {
            "frames": l,
            "given": ("path_life", path_life),
            "k": k,
            "feasible_stability": (s_min, s_max),
            "note": f"For k={k} frames with path present, stability must be in [{s_min:.3f}, {s_max:.3f}]",
        }

    else:
        # stability provided -> find all k that can realize that stability
        if not (0.0 <= stability <= 1.0):
            raise ValueError("stability must be in [0,1]")
        feasible_ks = []
        for k in range(0, l + 1):
            if k == 0 or k == l:
                t_min = t_max = 0
            else:
                t_min = 2
                t_max = min(l - 1, 2 * min(k, l - k))
            s_min = 1 - (t_max / (l - 1))
            s_max = 1 - (t_min / (l - 1))
            # numerical tolerance
            if s_min - 1e-9 <= stability <= s_max + 1e-9:
                feasible_ks.append(k)

        if not feasible_ks:
            return {
                "frames": l,
                "given": ("stability", stability),
                "feasible_path_life": None,
                "possible_k": [],
                "note": "No feasible path_life (k) exists for the provided stability",
            }

        alpha_min = min(feasible_ks) / l
        alpha_max = max(feasible_ks) / l
        return {
            "frames": l,
            "given": ("stability", stability),
            "possible_k": feasible_ks,
            "feasible_path_life": (alpha_min, alpha_max),
            "note": f"For stability={stability}, path_life (alpha) must be in [{alpha_min:.3f}, {alpha_max:.3f}]",
        }


def saveSweepMatrices(
    sweep_results, out_dir, overwrite=False, file_format: str = "csv"
):
    """
    Persist sweep results to disk.

    file_format: "csv" (default) -> compact CSV per-entry: one CSV file containing
                 node header then stacked adjacency matrices (frames stacked vertically,
                 optional blank line between frames).
                 "json" -> per-entry JSON file containing nodes and per-frame edge lists.

    Other behavior unchanged.
    """
    os.makedirs(out_dir, exist_ok=True)
    _log = _make_logger(out_dir)
    _log(f"saveSweepMatrices: starting, entries={len(sweep_results)}, format={file_format}, overwrite={overwrite}")
    index_rows = []
    fmt = file_format.lower()
    for i, entry in enumerate(sweep_results):
        param_name = entry.get("param_name", "param")
        param_value = entry.get("param_value", entry.get(param_name, "nan"))
        dyn_graph = entry.get("dynamic_graph")
        if dyn_graph is None:
            _log(f"entry[{i}] skipped: dynamic_graph is None (param_value={param_value})")
            # skip malformed entry
            continue

        # Create a safe directory name
        entry_dirname = f"entry_{i}_{param_name}_{str(param_value).replace('.', '_')}"
        entry_dir = os.path.join(out_dir, entry_dirname)
        if os.path.exists(entry_dir):
            if overwrite:
                for fn in os.listdir(entry_dir):
                    fp = os.path.join(entry_dir, fn)
                    try:
                        if os.path.isfile(fp):
                            os.remove(fp)
                    except Exception:
                        pass
            else:
                suffix = 1
                while os.path.exists(entry_dir):
                    entry_dir = os.path.join(out_dir, f"{entry_dirname}_{suffix}")
                    suffix += 1
        os.makedirs(entry_dir, exist_ok=True)

        # Determine node ordering: union of all nodes across frames, sorted for reproducibility
        all_nodes = set()
        for G in dyn_graph:
            try:
                all_nodes.update(list(G.nodes()))
            except Exception as e:
                _log(f"entry[{i}] warning: could not get nodes() from a frame: {e}")
        nodes = sorted(list(all_nodes), key=lambda x: str(x))

        _log(f"entry[{i}] param_value={param_value} frames={len(dyn_graph)} nodes_count={len(nodes)} entry_dir={entry_dir}")

        # Save nodes order (keep for compatibility)
        nodes_file = os.path.join(entry_dir, "nodes.txt")
        with open(nodes_file, "w", encoding="utf-8") as f:
            for n in nodes:
                f.write(f"{n}\n")

        if fmt == "csv":
            # Compact CSV: one file containing nodes header then stacked adjacency matrices.
            # File format:
            #   A,B,C
            #   frame0_row0
            #   frame0_row1
            #   ...
            #
            #   frame1_row0
            #   frame1_row1
            #   ...
            frames_file = os.path.join(entry_dir, f"frames.csv")
            try:
                with open(frames_file, "w", encoding="utf-8", newline="") as cf:
                    # header: node labels
                    cf.write(",".join(map(str, nodes)) + "\n")
                    for t, G in enumerate(dyn_graph):
                        # ensure adjacency uses same node order and integer 0/1
                        try:
                            A = nx.to_numpy_array(G, nodelist=nodes, dtype=int)
                        except Exception as e:
                            _log(f"entry[{i}] frame[{t}] to_numpy_array failed: {e}")
                            # write an all-zero row block to keep CSV structure
                            A = np.zeros((len(nodes), len(nodes)), dtype=int)
                        # shape check
                        if A.shape != (len(nodes), len(nodes)):
                            _log(f"entry[{i}] frame[{t}] adjacency shape mismatch {A.shape} expected {(len(nodes), len(nodes))}")
                        # write each row of adjacency
                        for row in A.astype(int):
                            cf.write(",".join(map(str, row.tolist())) + "\n")
                        # separate frames with a blank line (except after last)
                        if t != len(dyn_graph) - 1:
                            cf.write("\n")
                # post-write verification
                try:
                    sz = os.path.getsize(frames_file)
                except Exception:
                    sz = -1
                _log(f"entry[{i}] wrote frames.csv size={sz} ({frames_file})")
                if sz <= 1:
                    _log(f"entry[{i}] frames.csv suspiciously small (size={sz}), dumping debug adjacency files")
                    # dump debug adjacency matrices for inspection
                    dbg_dir = os.path.join(entry_dir, "debug_dump")
                    os.makedirs(dbg_dir, exist_ok=True)
                    for t, G in enumerate(dyn_graph):
                        try:
                            A = nx.to_numpy_array(G, nodelist=nodes, dtype=int)
                            np.savetxt(os.path.join(dbg_dir, f"adj_frame_{t:03d}.csv"), A, fmt="%d", delimiter=",")
                        except Exception as e:
                            _log(f"entry[{i}] dump frame[{t}] failed: {e}")
            except Exception as e:
                _log(f"entry[{i}] ERROR writing frames.csv: {e}")
                # fallback: write per-frame debug dumps
                dbg_dir = os.path.join(entry_dir, "debug_dump")
                os.makedirs(dbg_dir, exist_ok=True)
                for t, G in enumerate(dyn_graph):
                    try:
                        A = nx.to_numpy_array(G, nodelist=nodes, dtype=int)
                        np.savetxt(os.path.join(dbg_dir, f"adj_frame_{t:03d}.csv"), A, fmt="%d", delimiter=",")
                    except Exception as e2:
                        _log(f"entry[{i}] fallback dump frame[{t}] failed: {e2}")
        elif fmt == "json":
            # Save compact JSON representation: nodes + per-frame edge lists (node labels)
            frames_json = []
            for t, G in enumerate(dyn_graph):
                edges = [[str(u), str(v)] for (u, v) in G.edges()]
                frames_json.append({"frame": t, "edges": edges})
            frames_file = os.path.join(entry_dir, "frames.json")
            with open(frames_file, "w", encoding="utf-8") as jf:
                json.dump({"nodes": nodes, "frames": frames_json}, jf, indent=2)
        else:
            raise ValueError(f"unsupported file_format: {file_format!r}")

        # Save metadata JSON for the entry
        meta = {
            "param_name": param_name,
            "param_value": param_value,
            "frames": len(dyn_graph),
            "nodes_file": "nodes.txt",
            "format": fmt,
            "entry_dir": os.path.basename(entry_dir),
        }
        meta_file = os.path.join(entry_dir, f"entry_{i}_meta.json")
        with open(meta_file, "w", encoding="utf-8") as mf:
            json.dump(meta, mf, indent=2)

        index_rows.append(
            {
                "entry_id": i,
                "param_name": param_name,
                "param_value": param_value,
                "frames": len(dyn_graph),
                "entry_dir": os.path.basename(entry_dir),
            }
        )

    # write index CSV (unchanged)
    index_file = os.path.join(out_dir, "index.csv")
    with open(index_file, "w", encoding="utf-8") as idxf:
        idxf.write("entry_id,param_name,param_value,frames,entry_dir\n")
        for r in index_rows:
            idxf.write(
                f"{r['entry_id']},{r['param_name']},{r['param_value']},{r['frames']},{r['entry_dir']}\n"
            )
    _log(f"saveSweepMatrices: finished, wrote index={index_file}, entries_written={len(index_rows)}")
    return index_file


def saveDGmatrices(
    dynamicGraph,
    out_dir,
    entry_name="dynamicGraph",
    overwrite=False,
    file_format: str = "csv",
):
    """
    Save a single dynamic graph.

    file_format: "csv" (default) -> adjacency CSV per frame (same as before)
                 "json" -> single JSON file "frames.json" with nodes + per-frame edge lists.
    Returns the entry directory path.
    """
    os.makedirs(out_dir, exist_ok=True)
    # accept a single Graph as input is TODO
    if hasattr(dynamicGraph, "DynamicGraph") and dynamicGraph.DynamicGraph is not None:
        dyn_graph = dynamicGraph.DynamicGraph
    else:
        raise ValueError(
            "saveDGmatrices: dynamicGraph has no DynamicGraph attribute or is None"
        )

    entry_dirname = entry_name
    entry_dir = os.path.join(out_dir, entry_dirname)
    if os.path.exists(entry_dir):
        if overwrite:
            for fn in os.listdir(entry_dir):
                fp = os.path.join(entry_dir, fn)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                except Exception:
                    pass
        else:
            suffix = 1
            base = entry_dir
            while os.path.exists(entry_dir):
                entry_dir = f"{base}_{suffix}"
                suffix += 1
    os.makedirs(entry_dir, exist_ok=True)

    # Determine node ordering: union of all nodes across frames, sorted for reproducibility
    all_nodes = set()
    for G in dyn_graph:
        all_nodes.update(list(G.nodes()))
    nodes = sorted(list(all_nodes), key=lambda x: int(str(x).split("_")[1]))

    # Save nodes order
    nodes_file = os.path.join(entry_dir, "nodes.txt")
    with open(nodes_file, "w", encoding="utf-8") as f:
        for n in nodes:
            f.write(f"{n}\n")

    fmt = file_format.lower()
    if fmt == "csv":
        # Save all adjacency matrices in a single CSV file.
        # Matrices are stacked vertically with a blank line between frames.
        frames_file = os.path.join(entry_dir, "frames.csv")

        with open(frames_file, "w", encoding="utf-8", newline="") as cf:
            # Node labels as the header
            cf.write(",".join(map(str, nodes)) + "\n")

            for t, G in enumerate(dyn_graph):
                # Use the same node ordering for every frame
                A = nx.to_numpy_array(
                    G,
                    nodelist=nodes,
                    dtype=int
                )

                # Write matrix rows
                for row in A.astype(int):
                    cf.write(",".join(map(str, row.tolist())) + "\n")

                # Empty line separating matrices
                if t != len(dyn_graph) - 1:
                    cf.write("\n")

        meta = {
            "entry_name": entry_name,
            "frames": len(dyn_graph),
            "nodes_file": "nodes.txt",
            "frames_file": "frames.csv",
            "format": fmt,
            "entry_dir": os.path.basename(entry_dir),
        }
    
    elif fmt == "json":
        frames_json = []
        for t, G in enumerate(dyn_graph):
            edges = [[str(u), str(v)] for (u, v) in G.edges()]
            frames_json.append({"frame": t, "edges": edges})
        frames_file = os.path.join(entry_dir, "frames.json")
        with open(frames_file, "w", encoding="utf-8") as jf:
            json.dump({"nodes": nodes, "frames": frames_json}, jf, indent=2)
        meta = {
            "entry_name": entry_name,
            "frames": len(dyn_graph),
            "nodes_file": "nodes.txt",
            "frames_file": "frames.json",
            "format": fmt,
            "entry_dir": os.path.basename(entry_dir),
        }
    else:
        raise ValueError(f"unsupported file_format: {file_format!r}")

    # Save metadata JSON for the entry
    meta_file = os.path.join(entry_dir, f"{entry_name}_meta.json")
    with open(meta_file, "w", encoding="utf-8") as mf:
        json.dump(meta, mf, indent=2)

    return entry_dir


def saveDGbatch(graphs, out_dir, names=None, overwrite=False, file_format: str = "csv"):
    """
    Save a list of dynamic graphs (each a list of frames or single Graph) into out_dir.
    Produces per-entry directories and an index.csv summarizing saved entries.

    Parameters:
      - graphs: list of dynamic_graph objects
      - names: optional list of names matching graphs
    Returns:
      - path to index.csv
    """
    os.makedirs(out_dir, exist_ok=True)
    index_rows = []
    for i, dg in enumerate(graphs):
        name = None
        if names and i < len(names):
            name = names[i]
        else:
            name = f"graph_{i}"
        entry_dir = saveDGmatrices(
            dg, out_dir, entry_name=name, overwrite=overwrite, file_format=file_format
        )
        # load metadata to get frames count
        meta_path = os.path.join(entry_dir, f"{name}_meta.json")
        frames = None
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as mf:
                    meta = json.load(mf)
                    frames = meta.get("frames", None)
            except Exception:
                frames = None
        index_rows.append(
            {
                "entry_id": i,
                "entry_name": name,
                "frames": frames if frames is not None else "",
                "entry_dir": os.path.basename(entry_dir),
            }
        )

    index_file = os.path.join(out_dir, "index.csv")
    with open(index_file, "w", encoding="utf-8") as idxf:
        idxf.write("entry_id,entry_name,frames,entry_dir\n")
        for r in index_rows:
            idxf.write(
                f"{r['entry_id']},{r['entry_name']},{r['frames']},{r['entry_dir']}\n"
            )

    return index_file


def loadDGfromDir(entry_dir):
    """
    Read nodes.txt + adj_frame_*.csv from entry_dir and return a list of networkx.Graph frames.
    """
    nodes_file = os.path.join(entry_dir, "nodes.txt")
    if not os.path.exists(nodes_file):
        raise FileNotFoundError(f"nodes.txt not found in {entry_dir}")

    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes = [line.strip() for line in f if line.strip()]

    adj_files = sorted(glob.glob(os.path.join(entry_dir, "adj_frame_*.csv")))
    if not adj_files:
        raise FileNotFoundError(f"No adjacency frame CSVs found in {entry_dir}")

    graphs = []
    for af in adj_files:
        A = np.loadtxt(af, delimiter=",", dtype=int)
        G = nx.from_numpy_array(A)
        # relabel numeric nodes to original labels (handles non-integer labels)
        mapping = {i: nodes[i] for i in range(len(nodes))}
        G = nx.relabel_nodes(G, mapping)
        graphs.append(G)
    return graphs


def loadFromDirectory(path):
    """
    Load sweep output produced by saveSweepMatrices().
    Returns a dict compatible with Visualizer.plotLoadedData:
      - {'type':'single', 'dynamic_graph': [...frames...]} for a single entry dir
      - {'type':'batch', 'entries': [ {entry_id, param_name, param_value, frames, entry_dir, dynamic_graph}, ... ]}
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # single dynamic graph directory (has nodes.txt or frames.csv/frames.json)
    try:
        dg = _load_dynamic_graph_from_dir(path)
        return {"type": "single", "dynamic_graph": dg}
    except Exception:
        # not a single entry dir -> continue to try batch/index
        pass

    index_file = os.path.join(path, "index.csv")
    entries = []
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as idxf:
            reader = csv.DictReader(idxf)
            for row in reader:
                entry_dir = os.path.join(path, row.get("entry_dir", "").strip())
                try:
                    dg = _load_dynamic_graph_from_dir(entry_dir)
                except Exception:
                    dg = []
                entry = {
                    "entry_id": row.get("entry_id"),
                    "entry_dir": row.get("entry_dir"),
                    "param_name": row.get("param_name"),
                    "param_value": row.get("param_value"),
                    "frames": int(row.get("frames")) if row.get("frames") else (len(dg) if dg else 0),
                    "dynamic_graph": dg,
                }
                entries.append(entry)
        return {"type": "batch", "entries": entries}

    # fallback: discover subdirectories and try to load each as an entry
    subdirs = [os.path.join(path, d) for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    for sd in subdirs:
        try:
            dg = _load_dynamic_graph_from_dir(sd)
            entries.append({"entry_dir": os.path.basename(sd), "dynamic_graph": dg, "frames": len(dg)})
        except Exception:
            continue
    return {"type": "batch", "entries": entries}


# def sweep_mpc_generate(dynamic_graph_base, pairs, frames: int, path_life: float = None, stability: float = None,
#                        step: float = 0.1, mode: str = "indep", trials: int = 1000, p_edge: float = 0.5, seed: int = 42):
#     """
#     Sweep the unspecified parameter (path_life or stability) using timeline_feasible_params,
#     build one MPC dynamic graph per step, and return a list of results.

#     Returns a list of dicts: {'param_name': 'path_life'|'stability', 'param_value': v, 'timeline': timeline, 'dynamic_graph': dynamic_graph}
#     """
#     if (path_life is None) == (stability is None):
#         raise ValueError("Provide exactly one of path_life or stability")

#     params_info = timeline_feasible_params(frames=frames, path_life=path_life, stability=stability)
#     results = []

#     # prepare augmented base graph and frame generator once
#     limitedMPC = SourceGraphAugmenter.augmentBaseGraph(dynamic_graph_base, pairs, seed=seed, verbose=False)
#     frame_generator = FrameGenerator()

#     nPairs = len(pairs)

#     if path_life is not None:
#         # produce stability values in feasible range
#         s_min, s_max = params_info.get('feasible_stability', (0.0, 1.0))
#         vals = np.arange(s_min, s_max + 1e-9, step)
#         param_name = "stability"
#         for v in np.unique(np.round(vals, 6)):
#             stability_v = float(np.clip(v, 0.0, 1.0))
#             # generate MPC frame set (sampling frames for each pair)
#             MPCFrameSet = frame_generator.generateMPCFrames(limitedMPC, pairs, trials=trials, p_edge=p_edge, seed=seed)
#             # generate timeline with current parameters
#             timelineGen = MPCTimelineBlockGenerator(frames, nPairs, path_life, stability_v, mode, seed=seed)
#             timeline = timelineGen.generate()
#             MPCDynaGA = MPCDynamicGraph()
#             MPCDynaGA.buildDynaGraph(timeline, MPCFrameSet)
#             results.append({
#                 'param_name': param_name,
#                 'param_value': stability_v,
#                 'timeline': timeline,
#                 'dynamic_graph': MPCDynaGA.DynamicGraph
#             })

#     else:
#         # stability provided -> sweep path_life values in feasible range
#         feasible = params_info.get('feasible_path_life')
#         if feasible is None:
#             return results
#         a_min, a_max = feasible
#         vals = np.arange(a_min, a_max + 1e-9, step)
#         param_name = "path_life"
#         for v in np.unique(np.round(vals, 6)):
#             path_life_v = float(np.clip(v, 0.0, 1.0))
#             MPCFrameSet = frame_generator.generateMPCFrames(limitedMPC, pairs, trials=trials, p_edge=p_edge, seed=seed)
#             timelineGen = MPCTimelineBlockGenerator(frames, nPairs, path_life_v, stability, mode, seed=seed)
#             timeline = timelineGen.generate()
#             MPCDynaGA = MPCDynamicGraph()
#             MPCDynaGA.buildDynaGraph(timeline, MPCFrameSet)
#             results.append({
#                 'param_name': param_name,
#                 'param_value': path_life_v,
#                 'timeline': timeline,
#                 'dynamic_graph': MPCDynaGA.DynamicGraph
#             })

#     return results
