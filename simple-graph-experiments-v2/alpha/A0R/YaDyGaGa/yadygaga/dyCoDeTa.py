import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import colors as mcolors
import matplotlib.patches as mpatches


class DynaGraphCommuDetection:
    def __init__(self, dynamic_graph, method="louvain", seed=444):
        self.dynamic_graph = dynamic_graph
        self.community = []  # [C1, C2, C3, ...] where Ci is the community at time i
        self.dynaCommunity = (
            []
        )  # [[C1_t1, C2_t1, ...], [C1_t2, C2_t2, ...], ...] where Ci_tj is the community i at time j
        self.method = method
        self.seed = seed
        self.CommuMapper = {}  # Map the nodes to their positions
        self.HspaceMapper = {}  # Map frame_index -> list of community H-space positions

    def detectStatCommunities(self):
        for frame in self.dynamic_graph:
            if self.method == "louvain":
                partition = nx.community.louvain_communities(frame, self.seed)
                self.community.append(partition)
            # TODO : add more methods here (walktrap, girvan-newman, etc.)
            else:
                raise ValueError(f"Unknown community detection method: {self.method}")
        return self.community

    def unitCirclePlacement(self):
        # Take the community detected on the first frame and place nodes in unit circle
        if not self.community:
            self.detectStatCommunities()
        fstFrameCommu = self.community[0]
        numNodes = self.dynamic_graph[0].number_of_nodes()

        for comm in fstFrameCommu:
            for node in comm:
                index = list(self.dynamic_graph[0].nodes()).index(node)
                # print(index)
                angle = 2 * np.pi * index / numNodes
                x = 0.5 + 0.4 * np.math.cos(angle)
                y = 0.5 + 0.4 * np.math.sin(angle)
                self.CommuMapper[node] = (x, y)
        return self.CommuMapper

    def HspacePlacement(self, frame_index=0):
        # Take the CommuMapper and compute the position of the communities in H space
        # For each community, position h = sum of member node coordinates (x_sum, y_sum).
        if not self.community:
            self.detectStatCommunities()

        if not self.CommuMapper:
            self.unitCirclePlacement()

        if frame_index < 0 or frame_index >= len(self.community):
            raise IndexError("frame_index out of range")

        comms = self.community[frame_index]
        comm_positions = []

        for comm in comms:
            sum_x = 0.0
            sum_y = 0.0
            for node in comm:
                pos = self.CommuMapper.get(node)
                if pos is None:
                    # skip nodes without placement (shouldn't happen if unitCirclePlacement covered all nodes)
                    continue
                sum_x += pos[0]
                sum_y += pos[1]
            comm_positions.append((sum_x, sum_y))

        self.HspaceMapper[frame_index] = comm_positions
        return comm_positions

    def plotCommuMapper(self):
        comm_mapper = self.unitCirclePlacement()
        labels = list(comm_mapper.keys())
        x_vals = [comm_mapper[l][0] for l in labels]
        y_vals = [comm_mapper[l][1] for l in labels]

        # ensure communities are detected
        if not self.community:
            self.detectStatCommunities()
        fst_comms = self.community[0] if self.community else []

        # map node -> community index (first-frame membership)
        node_to_comm = {}
        for ci, comm in enumerate(fst_comms):
            for n in comm:
                node_to_comm[n] = ci

        num_comms = max(1, len(fst_comms))
        base_cmap = plt.cm.get_cmap("tab10")
        comm_colors = [base_cmap(i % base_cmap.N) for i in range(num_comms)]

        # build color list aligned with labels
        node_colors = [comm_colors[node_to_comm.get(n, 0)] for n in labels]

        plt.figure(figsize=(6, 6))
        ax = plt.gca()
        # add unit circle (center 0.5,0.5 radius 0.4) as thin hard-grey line behind points
        circ = mpatches.Circle(
            (0.5, 0.5), 0.4, edgecolor="0.3", facecolor="none", linewidth=0.8, zorder=0
        )
        ax.add_patch(circ)

        plt.scatter(
            x_vals,
            y_vals,
            c=node_colors,
            s=100,
            edgecolors="k",
            linewidths=0.5,
            zorder=2,
        )

        for label, x, y in zip(labels, x_vals, y_vals):
            plt.text(x, y, label, fontsize=9, ha="right", zorder=3)

        plt.title("Node Placement Based on Communities")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.axis("equal")
        plt.grid(True)
        plt.show()

    def plotHspacePlacement(self, frame_index=0):
        if frame_index not in self.HspaceMapper:
            self.HspacePlacement(frame_index)

        comm_positions = self.HspaceMapper[frame_index]
        x_vals = [pos[0] for pos in comm_positions]
        y_vals = [pos[1] for pos in comm_positions]

        plt.figure(figsize=(6, 6))
        ax = plt.gca()
        # add unit circle (center 0.5,0.5 radius 0.4) as thin hard-grey line behind points
        circ = mpatches.Circle(
            (0.5, 0.5), 0.4, edgecolor="0.3", facecolor="none", linewidth=0.8, zorder=0
        )
        ax.add_patch(circ)

        plt.scatter(x_vals, y_vals, zorder=2)

        for i, (x, y) in enumerate(comm_positions):
            plt.text(x, y, f"C{i+1}", fontsize=9, ha="right", zorder=3)

        plt.title(f"Community Positions in H Space (Frame {frame_index})")
        plt.xlabel("H-X")
        plt.ylabel("H-Y")
        plt.axis("equal")
        plt.grid(True)
        plt.show()

    def HspacePropagation(self, threshold=0.2):
        """
        Compute H-space for every frame and propagate community identities over time.
        Two communities (points in H-space) are considered the same if their H-space
        positions are within `threshold` Euclidean distance. Returns self.dynaCommunity
        as a list per frame of dicts: {'id': int, 'members': [...], 'hpos': (x,y)}.
        """
        if not self.community:
            self.detectStatCommunities()

        # Ensure H-space computed for all frames
        for fi in range(len(self.community)):
            if fi not in self.HspaceMapper:
                self.HspacePlacement(fi)

        self.dynaCommunity = []
        next_id = 0

        for fi, comms in enumerate(self.community):
            frame_entries = []
            h_positions = self.HspaceMapper.get(fi, [])

            for ci, comm in enumerate(comms):
                hpos = h_positions[ci] if ci < len(h_positions) else (0.0, 0.0)

                assigned_id = None
                if fi > 0:
                    # find nearest community from previous frame
                    prev_entries = self.dynaCommunity[fi - 1]
                    min_dist = float("inf")
                    candidate_id = None
                    for prev in prev_entries:
                        pdist = np.hypot(
                            hpos[0] - prev["hpos"][0], hpos[1] - prev["hpos"][1]
                        )
                        if pdist < min_dist:
                            min_dist = pdist
                            candidate_id = prev["id"]
                    if min_dist <= threshold:
                        assigned_id = candidate_id

                if assigned_id is None:
                    assigned_id = next_id
                    next_id += 1

                frame_entries.append(
                    {"id": assigned_id, "members": list(comm), "hpos": hpos}
                )

            self.dynaCommunity.append(frame_entries)

    def plotDynaCommunity(self, interval=1500, annote=False):
        """
        Animate community H-space positions over time.
        Colors are computed from each community H-position (x+y) mapped through a colormap.
        """
        # Ensure propagation computed
        if not self.dynaCommunity:
            self.HspacePropagation()

        frames = len(self.dynaCommunity)
        if frames == 0:
            raise RuntimeError(
                "No dynamic community data to plot. Run HspacePropagation first."
            )

        # collect all h positions to set consistent axes and normalization
        all_h = [entry["hpos"] for frame in self.dynaCommunity for entry in frame]
        xs_all = [h[0] for h in all_h]
        ys_all = [h[1] for h in all_h]
        if not xs_all or not ys_all:
            raise RuntimeError("H-space positions are empty.")

        xmin, xmax = min(xs_all), max(xs_all)
        ymin, ymax = min(ys_all), max(ys_all)
        xpad = (xmax - xmin) * 0.1 if xmax > xmin else 0.5
        ypad = (ymax - ymin) * 0.1 if ymax > ymin else 0.5

        cmap = plt.cm.viridis
        # use scalar = x+y for color mapping across all frames
        scalars = [x + y for x, y in all_h]
        norm = mcolors.Normalize(vmin=min(scalars), vmax=max(scalars), clip=True)

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_xlim(xmin - xpad, xmax + xpad)
        ax.set_ylim(ymin - ypad, ymax + ypad)
        ax.set_title("Dynamic Communities in H-space")
        ax.set_xlabel("H-X")
        ax.set_ylabel("H-Y")
        ax.grid(True)

        # prepare initial frame points (so scatter has a valid size/facecolors)
        first_entries = self.dynaCommunity[0] if frames > 0 else []
        xs0 = [e["hpos"][0] for e in first_entries]
        ys0 = [e["hpos"][1] for e in first_entries]
        vals0 = [x + y for x, y in zip(xs0, ys0)]
        colors0 = cmap(norm(vals0)) if vals0 else np.empty((0, 4))

        # create scatter with initial points so matplotlib knows the correct array shapes
        scat = ax.scatter(
            xs0, ys0, s=120, c=colors0, edgecolors="k", linewidths=0.6, zorder=2
        )

        texts = []

        def init():
            # set to first frame (or empty)
            if xs0 and ys0:
                offsets = np.column_stack((xs0, ys0))
                scat.set_offsets(offsets)
                scat.set_facecolors(colors0)
            else:
                scat.set_offsets(np.empty((0, 2)))
                scat.set_facecolors(np.empty((0, 4)))
            # clear any texts
            for t in texts:
                t.remove()
            texts.clear()
            return (scat,)

        def update(i):
            # clear previous texts
            nonlocal texts
            for t in texts:
                t.remove()
            texts = []

            entries = self.dynaCommunity[i]
            xs = [e["hpos"][0] for e in entries]
            ys = [e["hpos"][1] for e in entries]
            vals = [x + y for x, y in zip(xs, ys)]
            colors = cmap(norm(vals)) if vals else np.empty((0, 4))

            if xs and ys:
                offsets = np.column_stack((xs, ys))
                scat.set_offsets(offsets)
                # ensure color array length matches number of points
                scat.set_facecolors(colors)
                scat.set_sizes([120] * len(xs))
            else:
                scat.set_offsets(np.empty((0, 2)))
                scat.set_facecolors(np.empty((0, 4)))
                scat.set_sizes(np.array([]))

            # annotate with community id
            if annote == True:
                for e in entries:
                    x, y = e["hpos"]
                    tid = e.get("id", "")
                    txt = ax.text(
                        x, y, f"{tid}", fontsize=9, ha="right", va="bottom", zorder=3
                    )
                    texts.append(txt)

            ax.set_title(f"Dynamic Communities in H-space (Frame {i})")
            return scat, *texts

        ani = animation.FuncAnimation(
            fig,
            update,
            frames=frames,
            init_func=init,
            interval=interval,
            blit=False,
            repeat=True,
        )
        plt.axis("equal")
        plt.show()
        return ani


class AnalyzerDynaCommu:
    def __init__(self, dynaCommunity=[]):
        self.dynaCommunity = dynaCommunity  # [[C1_t1, C2_t1, ...], [C1_t2, C2_t2, ...], ...] where Ci_tj is the community i at time j

    def commuLifeTime(self):
        """
        Analyze the lifetime of communities over time.
        Returns a list of dicts: {'id': int, 'start_frame': int, 'end_frame': int, 'lifetime': int}
        """
        if not self.dynaCommunity:
            raise RuntimeError("No dynamic community data to analyze.")

        comm_lifetimes = {}
        for fi, frame in enumerate(self.dynaCommunity):
            for entry in frame:
                cid = entry["id"]
                if cid not in comm_lifetimes:
                    comm_lifetimes[cid] = {"start_frame": fi, "end_frame": fi}
                else:
                    comm_lifetimes[cid]["end_frame"] = fi

        # convert to list with lifetime calculation
        result = []
        for cid, times in comm_lifetimes.items():
            lifetime = times["end_frame"] - times["start_frame"] + 1
            result.append(
                {
                    "id": cid,
                    "start_frame": times["start_frame"],
                    "end_frame": times["end_frame"],
                    "lifetime": lifetime,
                }
            )
        return result

    def flexibility(self):
        """
        Compute the flexibility of nodes in changing community membership over time.
        Returns a dict: {node: flexibility_score}
        """
        if not self.dynaCommunity:
            raise RuntimeError("No dynamic community data to analyze.")

        node_membership = {}
        total_frames = len(self.dynaCommunity)

        for fi, frame in enumerate(self.dynaCommunity):
            for entry in frame:
                cid = entry["id"]
                for node in entry["members"]:
                    if node not in node_membership:
                        node_membership[node] = []
                    node_membership[node].append((fi, cid))

        flexibility_scores = {}
        for node, memberships in node_membership.items():
            changes = 0
            last_cid = None
            for fi, cid in memberships:
                if last_cid is not None and cid != last_cid:
                    changes += 1
                last_cid = cid
            flexibility_scores[node] = (
                changes / (total_frames - 1) if total_frames > 1 else 0.0
            )

        return flexibility_scores

    def promiscuity(self):
        """
        Compute the promiscuity of nodes in terms of the number of different communities they belong to over time.
        Returns a dict: {node: promiscuity_score}
        """
        if not self.dynaCommunity:
            raise RuntimeError("No dynamic community data to analyze.")

        node_communities = {}
        total_frames = len(self.dynaCommunity)

        for fi, frame in enumerate(self.dynaCommunity):
            for entry in frame:
                cid = entry["id"]
                for node in entry["members"]:
                    if node not in node_communities:
                        node_communities[node] = set()
                    node_communities[node].add(cid)

        promiscuity_scores = {}
        for node, comms in node_communities.items():
            promiscuity_scores[node] = (
                len(comms) / total_frames if total_frames > 0 else 0.0
            )

        return promiscuity_scores


class visualizer:
    def __init__(self, dynamic_graph=[], flexibilityScores={}):
        self.dynamic_graph = dynamic_graph
        self.flexibilityScores = flexibilityScores

    def flexibilityVisualization(self):
        """
        Visualize node flexibility scores on the dynamic graph.
        Merge all frames into a single plot: union of nodes/edges, node colors show flexibility.
        """
        if not self.dynamic_graph:
            raise RuntimeError("No dynamic graph data to visualize.")

        # build union graph of all frames (nodes + edges present in any frame)
        union_g = nx.Graph()
        for G in self.dynamic_graph:
            union_g.add_nodes_from(G.nodes())
            union_g.add_edges_from(G.edges())

        if union_g.number_of_nodes() == 0:
            raise RuntimeError("Union graph is empty, nothing to visualize.")

        # fixed layout for consistency across frames
        pos = nx.spring_layout(union_g, seed=42)

        # prepare scalar values (flexibility) per node in union graph
        nodes = list(union_g.nodes())
        vals = [self.flexibilityScores.get(n, 0.0) for n in nodes]

        fig, ax = plt.subplots(figsize=(8, 6))
        # draw faint union edges as background context
        nx.draw_networkx_edges(union_g, pos=pos, edge_color="0.8", alpha=0.5, ax=ax)

        # draw nodes colored by flexibility score using a colormap
        nodes_collection = nx.draw_networkx_nodes(
            union_g,
            pos=pos,
            nodelist=nodes,
            node_size=500,
            node_color=vals,
            cmap=plt.cm.viridis,
            vmin=0.0,
            vmax=1.0,
            ax=ax,
            edgecolors="k",
            linewidths=0.5,
            alpha=1.0,
        )

        # draw labels
        nx.draw_networkx_labels(
            union_g, pos=pos, labels={n: n for n in nodes}, font_size=9, ax=ax
        )

        ax.set_title("Node Flexibility (merged frames)")
        ax.axis("off")

        # colorbar anchored to the axes via fig.colorbar
        sm = plt.cm.ScalarMappable(
            cmap=plt.cm.viridis, norm=plt.Normalize(vmin=0.0, vmax=1.0)
        )
        sm.set_array(vals)
        cbar = fig.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Flexibility Score")

        plt.show()
