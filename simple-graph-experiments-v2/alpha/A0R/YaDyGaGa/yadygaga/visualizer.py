"""
Module for visualizing timelines.
"""

import random
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import networkx as nx
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np
from matplotlib.collections import LineCollection
import os
import json
import glob
import csv


class Visualizer:
    def __init__(self, timeline=None):
        self.timeline = timeline

    def render_text(self):
        """Render the timeline as a text representation."""
        return " ".join(["UP" if state else "DOWN" for state in self.timeline])

    def render_graphically(self):
        """Render the timeline graphically (placeholder for actual implementation)."""
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 2))
        plt.plot(self.timeline, drawstyle="steps-post")
        plt.yticks([0, 1], ["DOWN", "UP"])
        plt.title("Timeline Visualization")
        plt.xlabel("Frames")
        plt.ylabel("State")
        plt.grid(True)
        plt.show()

    def save_to_file(self, filename):
        """Save the timeline visualization to a file."""
        with open(filename, "w") as f:
            f.write(self.render_text())

    def visualize_dynamic_graph(
        self,
        graphs,
        interval=1000,
        loop=True,
        node_pos=None,
        node_size=300,
        node_color="skyblue",
        edge_color="gray",
        absent_node_color="lightgray",
        with_labels=True,
        target_pairs=None,
        layout="",
    ):
        """
        Animated network with a bottom contact timeline.
        If `target_pairs` is provided (list of (src,dst) tuples), highlight the
        current shortest path for each pair in a distinct color and show a legend
        on the right listing all targeted pairs.

        Improvements:
        - node labels are drawn to the right of the node (not inside)
        - when multiple target paths traverse the same link, the link is shown
          as a sequence of colored sub-segments (one segment per path) so each
          path color is visible as a fraction of the link.
        """
        if not graphs:
            raise ValueError("graphs list is empty")

        # Build union graph to have consistent node set and positions
        union = nx.Graph()
        for g in graphs:
            union.add_nodes_from(g.nodes())
            union.add_edges_from(g.edges())

        node_list = list(union.nodes())
        n_nodes = len(node_list)

        # Compute positions once unless provided (use circular layout)
        if node_pos is None:
            if layout == "random":
                pos = nx.random_layout(union) if len(union) > 0 else {}
            if layout == "spectral":
                pos = nx.spectral_layout(union) if len(union) > 0 else {}
            else:
                pos = nx.circular_layout(union) if len(union) > 0 else {}
        else:
            pos = node_pos

        # prepare pair colors
        pair_colors = {}
        if target_pairs:
            cmap = plt.cm.get_cmap("tab10")
            for i, p in enumerate(target_pairs):
                pair_colors[p] = cmap(i % cmap.N)

        # figure with two stacked subplots
        fig, (ax_top, ax_bottom) = plt.subplots(
            2, 1, figsize=(8, 8), gridspec_kw={"height_ratios": [2, 1]}
        )
        ax_top.set_title("Network (animated)")
        ax_top.axis("off")

        # bottom timeline static setup
        ax_bottom.set_title("Connections over time (y = node index, x = frame)")
        ax_bottom.set_xlabel("Frame")
        ax_bottom.set_ylabel("Node")
        if n_nodes > 0:
            ax_bottom.set_ylim(-0.5, n_nodes - 0.5)
            ax_bottom.set_yticks(range(n_nodes))
            ax_bottom.set_yticklabels([str(n) for n in node_list])
        else:
            ax_bottom.set_ylim(-0.5, 0.5)
        ax_bottom.set_xlim(-0.5, max(0, len(graphs) - 0.5))
        ax_bottom.grid(True, axis="x", linestyle=":", alpha=0.4)

        node_to_index = {n: i for i, n in enumerate(node_list)}

        # draw all arcs (one per edge occurrence) and prepare scatter points for nodes that are connected
        from matplotlib.path import Path
        from matplotlib.patches import PathPatch, Rectangle

        scatter_x = []
        scatter_y = []

        for f_idx, G in enumerate(graphs):
            connected_nodes = set()
            for u, v in G.edges():
                connected_nodes.add(u)
                connected_nodes.add(v)
                if u not in node_to_index or v not in node_to_index:
                    continue
                y1 = node_to_index[u]
                y2 = node_to_index[v]
                if y1 == y2:
                    mid_y = y1
                    rad_x = 0.4
                    verts = [
                        (f_idx - rad_x, mid_y),
                        (f_idx, mid_y + 0.5),
                        (f_idx + rad_x, mid_y),
                    ]
                else:
                    mid_y = 0.5 * (y1 + y2)
                    gap = abs(y2 - y1)
                    rad_x = 0.2 + 0.12 * gap
                    verts = [
                        (f_idx, y1),
                        (f_idx + rad_x, mid_y),
                        (f_idx, y2),
                    ]
                codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]
                path = Path(verts, codes)
                patch = PathPatch(
                    path,
                    edgecolor=edge_color,
                    facecolor="none",
                    lw=1.2,
                    alpha=0.9,
                    zorder=1,
                )
                ax_bottom.add_patch(patch)

            for n in connected_nodes:
                if n in node_to_index:
                    scatter_x.append(f_idx)
                    scatter_y.append(node_to_index[n])

        if scatter_x:
            ax_bottom.scatter(scatter_x, scatter_y, c=node_color, s=30, zorder=3)

        # animated soft red vertical bar (covers one-frame width)
        bar_width = 1.0
        bar = Rectangle(
            (-0.5, -0.5),
            width=bar_width,
            height=max(0, n_nodes),
            color="red",
            alpha=0.12,
            zorder=4,
        )
        ax_bottom.add_patch(bar)

        # prepare legend handles for target pairs (on the right)
        legend_handles = []
        if target_pairs:
            for p, col in pair_colors.items():
                lbl = f"{p[0]} -> {p[1]}"
                legend_handles.append(Line2D([0], [0], color=col, lw=3, label=lbl))

        # place a figure-level legend so it is not removed by per-frame axis.clear()
        fig_legend = None
        if legend_handles:
            fig_legend = fig.legend(
                handles=legend_handles,
                title="Target pairs",
                loc="center right",
                bbox_to_anchor=(0.98, 0.5),
            )
            plt.subplots_adjust(right=0.78)

        # animation: update top subplot per-frame and move the red bar
        def update(frame_index):
            ax_top.clear()
            ax_top.axis("off")
            ax_top.set_title(f"Frame {frame_index + 1}/{len(graphs)}")

            G = graphs[frame_index]

            # Node colors: highlight nodes present in this frame, fade absent ones
            top_node_colors = [
                node_color if (n in G.nodes()) else absent_node_color for n in node_list
            ]

            if node_list:
                nodes_coll = nx.draw_networkx_nodes(
                    union,
                    pos,
                    nodelist=node_list,
                    node_color=top_node_colors,
                    node_size=node_size,
                    ax=ax_top,
                )
                try:
                    nodes_coll.set_zorder(1)
                except Exception:
                    pass
            # draw base edges faintly (only edges present in the current frame)
            if G.number_of_edges() > 0:
                edges_coll = nx.draw_networkx_edges(
                    G,
                    pos,
                    edgelist=G.edges(),
                    edge_color=edge_color,
                    alpha=0.6,
                    ax=ax_top,
                )
                try:
                    edges_coll.set_zorder(1)
                except Exception:
                    pass

            # For each target pair, compute shortest path if exists and collect path edges per-edge
            edge_to_path_colors = (
                {}
            )  # key: (u,v) sorted, val: list of colors in order encountered
            if target_pairs:
                for p, col in pair_colors.items():
                    s, t = p
                    if s in G and t in G:
                        try:
                            path_nodes = nx.shortest_path(G, source=s, target=t)
                            path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
                            for e in path_edges:
                                key = tuple(sorted(e))
                                edge_to_path_colors.setdefault(key, []).append(col)
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            pass

                # Draw per-edge segmented colored representation where paths share links.
                seg_collections = []
                for (u, v), cols in edge_to_path_colors.items():
                    p0 = np.array(pos[u])
                    p1 = np.array(pos[v])
                    m = len(cols)
                    # create m consecutive sub-segments along the edge
                    segs = []
                    seg_colors = []
                    for i, c in enumerate(cols):
                        a = i / m
                        b = (i + 1) / m
                        seg_start = tuple(p0 * (1 - a) + p1 * a)
                        seg_end = tuple(p0 * (1 - b) + p1 * b)
                        segs.append((seg_start, seg_end))
                        seg_colors.append(c)
                    lc = LineCollection(
                        segs, colors=seg_colors, linewidths=3.0, zorder=3
                    )
                    ax_top.add_collection(lc)

            # draw full labels to the right of nodes (not inside)
            if with_labels and node_list:
                # draw labels with horizontal alignment left so they appear next to nodes
                labels = {n: str(n) for n in node_list}
                nx.draw_networkx_labels(
                    union,
                    pos,
                    labels=labels,
                    font_size=9,
                    horizontalalignment="left",
                    verticalalignment="center",
                    ax=ax_top,
                )

            # legend is drawn at figure level (fig_legend) so do not create per-frame axes legend

            # move bar on bottom timeline
            x = frame_index - 0.5  # align bar to frame column
            bar.set_x(x)

            return []

        ani = FuncAnimation(
            fig,
            update,
            frames=range(len(graphs)),
            interval=interval,
            repeat=loop,
            blit=False,
        )

        plt.tight_layout()
        plt.show()
        return ani

    def animate_random_dynamics(
        self,
        dynamics,
        n: int = 5,
        interval: int = 1000,
        loop: bool = True,
        seed: int = None,
        figsize=(15, 5),
        node_size=100,
        node_color="skyblue",
        absent_node_color="lightgray",
        edge_color="gray",
        with_labels=True,
        target_pairs=None,
        titles=None,
        layout="",
    ):
        """
        Pick up to `n` dynamics from `dynamics` and animate them side-by-side.
        If `target_pairs` is provided, highlight shortest paths for any pair that
        appears in the union node set of that column; pair colors are consistent.
        Also display a legend (right) listing the targeted pairs.
        """
        if seed is not None:
            random.seed(seed)
        print(
            f"Animating up to {n} random dynamics from pool of {len(dynamics)} dynamics."
        )
        # normalize dynamics into list of list-of-graphs
        pool = []
        for d in dynamics:
            if hasattr(d, "DynamicGraph"):
                frames = getattr(d, "DynamicGraph")
            elif isinstance(d, list):
                frames = d
            else:
                continue
            if not frames:
                frames = [nx.Graph()]
            # Normalize each frame element to a single networkx.Graph.
            # Many producers (SPC with pathPersistency) may return grouped entries
            # where a frame slot can be a list of candidate graphs. For visualization
            # pick a representative graph deterministically using the provided seed.
            rnd_pick = random.Random(seed)
            normalized = []
            for fe in frames:
                if isinstance(fe, (list, tuple)):
                    # pick a representative graph from the group (deterministic choice)
                    chosen = None
                    for el in fe:
                        if isinstance(el, nx.Graph):
                            chosen = el
                            break
                    if chosen is None:
                        # fallback to random pick if group contains non-graph entries
                        try:
                            chosen = rnd_pick.choice(list(fe))
                        except Exception:
                            chosen = nx.Graph()
                    normalized.append(chosen)
                elif isinstance(fe, nx.Graph):
                    normalized.append(fe)
                else:
                    # unknown element, try to use first attribute .nodes if present
                    try:
                        if hasattr(fe, "nodes"):
                            normalized.append(fe)
                        else:
                            normalized.append(nx.Graph())
                    except Exception:
                        normalized.append(nx.Graph())

            pool.append(normalized)

        if not pool:
            raise ValueError("No valid dynamics provided")

        count = min(n, len(pool))
        chosen_indices = random.sample(range(len(pool)), count)

        # pair colors global (so same across columns)
        pair_colors = {}
        if target_pairs:
            cmap = plt.cm.get_cmap("tab10")
            for i, p in enumerate(target_pairs):
                pair_colors[p] = cmap(i % cmap.N)

        from matplotlib.path import Path
        from matplotlib.patches import PathPatch, Rectangle

        dyn_info = []
        for idx in chosen_indices:
            frames = pool[idx]
            union = nx.Graph()
            for f in frames:
                union.add_nodes_from(f.nodes())
                union.add_edges_from(f.edges())
                if layout == "random":
                    pos = nx.random_layout(union) if len(union) > 0 else {}
                if layout == "spectral":
                    pos = nx.spectral_layout(union) if len(union) > 0 else {}
                else:
                    pos = nx.circular_layout(union) if len(union) > 0 else {}
            node_list = list(union.nodes())
            node_to_index = {n: i for i, n in enumerate(node_list)}
            patches = []
            scatter_x = []
            scatter_y = []
            for f_idx, G in enumerate(frames):
                connected_nodes = set()
                for u, v in G.edges():
                    connected_nodes.add(u)
                    connected_nodes.add(v)
                    if u not in node_to_index or v not in node_to_index:
                        continue
                    y1 = node_to_index[u]
                    y2 = node_to_index[v]
                    if y1 == y2:
                        mid_y = y1
                        rad_x = 0.4
                        verts = [
                            (f_idx - rad_x, mid_y),
                            (f_idx, mid_y + 0.5),
                            (f_idx + rad_x, mid_y),
                        ]
                    else:
                        mid_y = 0.5 * (y1 + y2)
                        gap = abs(y2 - y1)
                        rad_x = 0.2 + 0.12 * gap
                        verts = [
                            (f_idx, y1),
                            (f_idx + rad_x, mid_y),
                            (f_idx, y2),
                        ]
                    codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]
                    path = Path(verts, codes)
                    patches.append(
                        PathPatch(
                            path,
                            edgecolor=edge_color,
                            facecolor="none",
                            lw=1.2,
                            alpha=0.9,
                            zorder=1,
                        )
                    )
                for n in connected_nodes:
                    if n in node_to_index:
                        scatter_x.append(f_idx)
                        scatter_y.append(node_to_index[n])

            dyn_info.append(
                {
                    "frames": frames,
                    "union": union,
                    "pos": pos,
                    "node_list": node_list,
                    "node_to_index": node_to_index,
                    "length": len(frames),
                    "patches": patches,
                    "scatter_x": scatter_x,
                    "scatter_y": scatter_y,
                    "n_nodes": len(node_list),
                    "bar": None,
                }
            )

        max_frames = max(info["length"] for info in dyn_info)

        # create 2 x count axes: top row animated networks, bottom row static timelines
        fig, axes = plt.subplots(
            2, count, figsize=figsize, gridspec_kw={"height_ratios": [2, 1]}
        )
        if count == 1:
            top_axes = [axes[0]]
            bottom_axes = [axes[1]]
        else:
            top_axes = axes[0]
            bottom_axes = axes[1]

        # prepare legend handles (global)
        legend_handles = []
        if target_pairs:
            for p, col in pair_colors.items():
                lbl = f"{p[0]} -> {p[1]}"
                legend_handles.append(Line2D([0], [0], color=col, lw=3, label=lbl))

        for i, (ax_top, ax_bottom, info) in enumerate(
            zip(top_axes, bottom_axes, dyn_info)
        ):
            ax_top.axis("off")
            n_nodes = info["n_nodes"]
            node_list = info["node_list"]
            ax_bottom.set_title("Connections over time")
            ax_bottom.set_xlabel("Frame")
            ax_bottom.set_ylabel("Node")
            if n_nodes > 0:
                ax_bottom.set_ylim(-0.5, n_nodes - 0.5)
                ax_bottom.set_yticks(range(n_nodes))
                ax_bottom.set_yticklabels([str(n) for n in node_list])
            else:
                ax_bottom.set_ylim(-0.5, 0.5)
            ax_bottom.set_xlim(-0.5, max(0, info["length"] - 0.5))
            ax_bottom.grid(True, axis="x", linestyle=":", alpha=0.4)

            for p in info["patches"]:
                ax_bottom.add_patch(p)
            if info["scatter_x"]:
                ax_bottom.scatter(
                    info["scatter_x"], info["scatter_y"], c=node_color, s=30, zorder=3
                )
            bar = Rectangle(
                (-0.5, -0.5),
                width=1.0,
                height=max(0, n_nodes),
                color="red",
                alpha=0.12,
                zorder=4,
            )
            ax_bottom.add_patch(bar)
            info["bar"] = bar

            # add a per-column title (use provided titles when available)
            if titles and i < len(titles):
                ax_top.set_title(str(titles[i]))
            # add legend on top axis if target pairs provided
            if legend_handles:
                ax_top.legend(
                    handles=legend_handles,
                    title="Target pairs",
                    bbox_to_anchor=(1.02, 1),
                    loc="upper left",
                )

        # animation: update top row per-frame and move each bottom bar
        def update(frame_index):
            for ax_top, info in zip(top_axes, dyn_info):
                ax_top.clear()
                ax_top.axis("off")
                fi = frame_index % info["length"]
                G = info["frames"][fi]
                pos = info["pos"]
                node_list = info["node_list"]

                ax_top.set_title(f"Dyn frame {fi}")

                node_colors = [
                    node_color if (n in G.nodes()) else absent_node_color
                    for n in node_list
                ]

                if node_list:
                    nodes_coll = nx.draw_networkx_nodes(
                        info["union"],
                        pos,
                        nodelist=node_list,
                        node_color=node_colors,
                        node_size=node_size,
                        ax=ax_top,
                    )
                    try:
                        nodes_coll.set_zorder(1)
                    except Exception:
                        pass
                # draw only edges present in the current frame
                if G.number_of_edges() > 0:
                    edges_coll = nx.draw_networkx_edges(
                        G, pos, edgelist=G.edges(), edge_color=edge_color, ax=ax_top
                    )
                    try:
                        edges_coll.set_zorder(1)
                    except Exception:
                        pass
                if with_labels and node_list:
                    nx.draw_networkx_labels(info["union"], pos, ax=ax_top)

                # highlight target pair paths if present in this union/graph
                if target_pairs:
                    for p, col in pair_colors.items():
                        s, t = p
                        if s in G and t in G:
                            try:
                                path_nodes = nx.shortest_path(G, source=s, target=t)
                                path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
                                path_edges_coll = nx.draw_networkx_edges(
                                    G,
                                    pos,
                                    edgelist=path_edges,
                                    edge_color=[col],
                                    width=3.0,
                                    ax=ax_top,
                                )
                                try:
                                    path_edges_coll.set_zorder(3)
                                except Exception:
                                    pass
                                path_nodes_coll = nx.draw_networkx_nodes(
                                    G,
                                    pos,
                                    nodelist=path_nodes,
                                    node_color=[col] * len(path_nodes),
                                    node_size=int(node_size * 1.1),
                                    ax=ax_top,
                                    edgecolors="k",
                                )
                                try:
                                    path_nodes_coll.set_zorder(4)
                                except Exception:
                                    pass
                            except (nx.NetworkXNoPath, nx.NodeNotFound):
                                pass

                x = fi - 0.5
                info["bar"].set_x(x)

            return []

        ani = FuncAnimation(
            fig, update, frames=range(max_frames), interval=interval, repeat=loop
        )
        plt.tight_layout()
        plt.show()
        return ani

    def plotLoadedData(
        self,
        loaded,
        n_display=None,
        interval=800,
        loop=True,
        seed=1,
        target_pairs=None,
        layout="",
    ):
        """
        Plot content returned by load_from_directory(), a Python object (list/dict)
        or a JSON-compatible input (JSON string or path to a .json file or saved directory).

        - If `loaded` is a directory path -> uses load_from_directory(path)
        - If `loaded` is a path to a file and file is JSON -> parse JSON
        - If `loaded` is a JSON string/bytes -> parse JSON
        - Otherwise falls back to existing behavior for Python list/dict produced by API.
        """

        def _resolve_input(x):
            # directory path -> load directory
            if isinstance(x, str):
                if os.path.isdir(x):
                    return load_from_directory(x)
                if os.path.isfile(x):
                    # try to parse JSON file
                    try:
                        with open(x, "r", encoding="utf-8") as fh:
                            return json.load(fh)
                    except Exception:
                        # if not JSON, try to load as directory (fallback handled above)
                        raise
                # try JSON string
                try:
                    return json.loads(x)
                except Exception:
                    raise ValueError(
                        "String `loaded` is neither a directory, a JSON file path nor a JSON string"
                    )
            if isinstance(x, (bytes, bytearray)):
                try:
                    return json.loads(x.decode("utf-8"))
                except Exception:
                    raise ValueError("Bytes `loaded` is not valid JSON")
            return x

        # allow JSON/path inputs
        try:
            loaded = _resolve_input(loaded)
        except Exception as e:
            raise ValueError(f"Unable to interpret `loaded` input: {e}")

        # handle raw sweep results (list of dicts)
        if isinstance(loaded, list) and all(
            isinstance(e, dict) and "dynamic_graph" in e for e in loaded
        ):
            results = loaded
            if not results:
                raise RuntimeError("Empty sweep results")
            # extract dynamics and titles
            dynamics = [r["dynamic_graph"] for r in results]
            titles = [
                f"{r.get('param_name','param')}={r.get('param_value','')}"
                for r in results
            ]
            if n_display is None:
                n_display = min(6, len(dynamics))
            chosen = dynamics[:n_display]
            chosen_titles = titles[:n_display]
            v = Visualizer([])  # use animate_random_dynamics to render multiple columns
            return v.animate_random_dynamics(
                chosen,
                n=len(chosen),
                interval=interval,
                loop=loop,
                seed=seed,
                titles=chosen_titles,
                target_pairs=target_pairs,
                layout=layout,
            )

        # loaded dict returned by load_from_directory()
        if isinstance(loaded, dict) and loaded.get("type") == "single":
            dg = loaded["dynamic_graph"]
            v = Visualizer([])  # instance used to access method
            return v.visualize_dynamic_graph(
                dg,
                interval=interval,
                loop=loop,
                target_pairs=target_pairs,
                layout=layout,
            )

        if isinstance(loaded, dict) and loaded.get("type") == "batch":
            entries = loaded["entries"]
            graphs = [e["dynamic_graph"] for e in entries if e.get("dynamic_graph")]
            titles = [
                f"{e.get('param_name','') }={e.get('param_value','')}"
                for e in entries
                if e.get("dynamic_graph")
            ]
            if not graphs:
                raise RuntimeError("No dynamic graphs found in batch to plot.")
            # limit how many to show
            if n_display is None:
                n_display = min(5, len(graphs))
            chosen = graphs[:n_display]
            chosen_titles = titles[:n_display]
            v = Visualizer([])  # use animate_random_dynamics to render multiple columns
            return v.animate_random_dynamics(
                chosen,
                n=len(chosen),
                interval=interval,
                loop=loop,
                seed=seed,
                titles=chosen_titles,
                target_pairs=target_pairs,
                layout=layout,
            )

        raise ValueError("Unknown loaded data type or unsupported format")


def _load_dynamic_graph_from_dir(entry_dir):
    """
    Read nodes.txt + frames.csv OR frames.json OR adj_frame_*.csv from entry_dir
    and return a list of networkx.Graph frames.

    Supported layouts (in order):
      - frames.csv : compact CSV written by saveSweepMatrices:
            first line = comma-separated node labels
            then adjacency matrices stacked vertically; frames separated by blank lines
      - frames.json : JSON with {"nodes": [...], "frames": [{"frame":i,"edges":[[u,v],...]}, ...]}
      - adj_frame_*.csv : legacy per-frame adjacency CSV files (adj_frame_0.csv, ...)
    """
    # Prefer compact frames.csv if present
    frames_csv = os.path.join(entry_dir, "frames.csv")
    frames_json = os.path.join(entry_dir, "frames.json")
    nodes_file = os.path.join(entry_dir, "nodes.txt")

    if os.path.exists(frames_csv):
        graphs = []
        with open(frames_csv, "r", encoding="utf-8") as fh:
            lines = [ln.rstrip("\n") for ln in fh]
        if not lines:
            raise FileNotFoundError(f"{frames_csv} is empty")
        # first non-empty line is header nodes
        header_idx = 0
        while header_idx < len(lines) and lines[header_idx].strip() == "":
            header_idx += 1
        if header_idx >= len(lines):
            raise FileNotFoundError(f"No header found in {frames_csv}")
        nodes = [s.strip() for s in lines[header_idx].split(",")]
        # remaining lines form stacked matrices; blank line separates frames
        frame_rows = []
        for ln in lines[header_idx + 1 :]:
            if ln.strip() == "":
                if frame_rows:
                    A = np.array([[int(x) for x in row.split(",")] for row in frame_rows], dtype=int)
                    if A.size == 0:
                        graphs.append(nx.Graph())
                    else:
                        G = nx.from_numpy_array(A)
                        mapping = {i: nodes[i] for i in range(min(len(nodes), A.shape[0]))}
                        G = nx.relabel_nodes(G, mapping)
                        graphs.append(G)
                    frame_rows = []
                continue
            frame_rows.append(ln)
        # last frame if any
        if frame_rows:
            A = np.array([[int(x) for x in row.split(",")] for row in frame_rows], dtype=int)
            if A.size == 0:
                graphs.append(nx.Graph())
            else:
                G = nx.from_numpy_array(A)
                mapping = {i: nodes[i] for i in range(min(len(nodes), A.shape[0]))}
                G = nx.relabel_nodes(G, mapping)
                graphs.append(G)
        return graphs

    if os.path.exists(frames_json):
        with open(frames_json, "r", encoding="utf-8") as jf:
            j = json.load(jf)
        nodes = j.get("nodes", [])
        frames = j.get("frames", [])
        graphs = []
        for fr in frames:
            G = nx.Graph()
            G.add_nodes_from(nodes)
            for e in fr.get("edges", []):
                if len(e) >= 2:
                    G.add_edge(str(e[0]), str(e[1]))
            graphs.append(G)
        return graphs

    # legacy: per-frame adjacency CSV files plus nodes.txt
    if not os.path.exists(nodes_file):
        raise FileNotFoundError(f"nodes.txt not found in {entry_dir}")
    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes = [line.strip() for line in f if line.strip()]

    adj_files = sorted(glob.glob(os.path.join(entry_dir, "adj_frame_*.csv")))
    if not adj_files:
        raise FileNotFoundError(f"No adjacency frame CSVs or frames.csv/frames.json found in {entry_dir}")
    graphs = []
    for af in adj_files:
        A = np.loadtxt(af, delimiter=",", dtype=int)
        G = nx.from_numpy_array(A)
        mapping = {i: nodes[i] for i in range(len(nodes))}
        G = nx.relabel_nodes(G, mapping)
        graphs.append(G)
    return graphs


def load_from_directory(path):
    """
    Inspect `path` and load dynamic graph(s).
    - If path contains nodes.txt -> returns a single dynamic graph (list of frames).
    - If path contains index.csv -> returns a list of entries; each entry is dict with keys:
        {entry_id, entry_dir, param_name, param_value, frames, dynamic_graph}
    - Otherwise tries to auto-discover subdirectories containing nodes.txt and loads them.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # single dynamic graph directory (has nodes.txt)
    if os.path.exists(os.path.join(path, "nodes.txt")):
        dg = _load_dynamic_graph_from_dir(path)
        return {"type": "single", "dynamic_graph": dg}

    # try index.csv for batch/sweep
    index_file = os.path.join(path, "index.csv")
    if not os.path.exists(index_file):
        # try to find single entry subdirectories automatically
        subdirs = [
            os.path.join(path, d)
            for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d))
        ]
        results = []
        for sd in subdirs:
            try:
                dg = _load_dynamic_graph_from_dir(sd)
                results.append({"entry_dir": os.path.basename(sd), "dynamic_graph": dg})
            except FileNotFoundError:
                continue
        return {"type": "batch", "entries": results}

    # parse index.csv entries
    entries = []
    with open(index_file, "r", encoding="utf-8") as idxf:
        reader = csv.DictReader(idxf)
        for row in reader:
            entry_dir = os.path.join(path, row.get("entry_dir", "").strip())
            if not entry_dir:
                continue
            try:
                dg = _load_dynamic_graph_from_dir(entry_dir)
            except Exception:
                dg = []
            entry = {
                "entry_id": row.get("entry_id"),
                "entry_dir": row.get("entry_dir"),
                "param_name": row.get("param_name"),
                "param_value": row.get("param_value"),
                "frames": int(row.get("frames")) if row.get("frames") else None,
                "dynamic_graph": dg,
            }
            entries.append(entry)
    return {"type": "batch", "entries": entries}
