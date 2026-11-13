"""
FrameGenerator class responsible for generating frames based on specified parameters.

Methods:
- generate_frames: Generates frames based on input parameters.
- get_frame_data: Retrieves the generated frame data.
- clear_frames: Clears the current frame data.
"""

from typing import List, Dict, Tuple
import random
import networkx as nx


class FrameGenerator:
    def __init__(self):
        self.path_up_frames = []
        self.path_down_frames = []
        self.path_up_keys = []

    def generateSPCFrames(
        self,
        limited_G: nx.Graph,
        s: str,
        d: str,
        trials: int = 1000,
        p_edge: float = 0.5,
        pathPersistency: float = 0.0,
        seed: int = 0,
        behavior: str = "legacy",
        timeline: list[bool] | None = None,
        mean_up_duration: float = 4.0,
    ) -> None:
        """Dispatch to the unchanged legacy sampler or the opt-in patched-v3 sampler."""
        if behavior == "patched-v3":
            if timeline is None:
                raise ValueError("patched-v3 requires a fixed S-R target timeline")
            result = self.generateTemporalSPCFrames(
                limited_G,
                s,
                d,
                timeline,
                p_edge,
                mean_up_duration,
                seed,
            )
            self.path_up_frames = [
                [graph]
                for graph, is_up in zip(result["frames"], timeline)
                if is_up
            ]
            self.path_down_frames = [
                graph
                for graph, is_up in zip(result["frames"], timeline)
                if not is_up
            ]
            self.path_up_keys = []
            self.temporal_result = result
            return
        if behavior != "legacy":
            raise ValueError("behavior must be 'legacy' or 'patched-v3'")
        # The original sampler below remains the legacy implementation.
        return self._generateSPCFramesLegacy(
            limited_G, s, d, trials, p_edge, pathPersistency, seed
        )

    def _generateSPCFramesLegacy(
        self,
        limited_G: nx.Graph,
        s: str,
        d: str,
        trials: int = 1000,
        p_edge: float = 0.5,
        pathPersistency: float = 0.0,
        seed: int = 0,
    ) -> None:
        """Legacy body retained verbatim behind the selectable behavior dispatch."""
        assert 0.0 <= pathPersistency <= 1.0
        rng = random.Random(seed)
        edges = list(limited_G.edges())
        path_map = {}
        down_list = []
        for _ in range(trials):
            H = nx.Graph()
            H.add_nodes_from(limited_G.nodes())
            for e in edges:
                if rng.random() < p_edge:
                    H.add_edge(*e)
            if s in H and d in H and nx.has_path(H, s, d):
                try:
                    path_nodes = tuple(nx.shortest_path(H, s, d))
                except Exception:
                    path_nodes = tuple()
                path_map.setdefault(path_nodes, []).append(H)
            else:
                down_list.append(H)
        ordered_keys = sorted(
            path_map.keys(), key=lambda k: (len(k), tuple(map(str, k)))
        )
        self.path_up_frames = [path_map[k] for k in ordered_keys]
        self.path_down_frames = down_list
        self.path_up_keys = ordered_keys

    @staticmethod
    def sample_two_state_chain(
        frames: int, pi: float, mean_up_duration: float, seed: int
    ) -> list[bool]:
        """Sample a stationary binary Markov chain with controlled up fraction and duration."""
        if frames < 0:
            raise ValueError("frames must be nonnegative")
        if not 0.0 < pi < 1.0 or mean_up_duration <= 0.0:
            raise ValueError("pi must be in (0,1) and mean_up_duration positive")
        p10 = 1.0 / mean_up_duration
        p01 = pi / ((1.0 - pi) * mean_up_duration)
        if p10 > 1.0 or p01 > 1.0:
            raise ValueError("infeasible stationary fraction / up-duration combination")
        rng = random.Random(seed)
        state = rng.random() < pi
        chain = []
        for _ in range(frames):
            chain.append(state)
            state = (rng.random() >= p10) if state else (rng.random() < p01)
        return chain

    @staticmethod
    def _canonical_shortest_path(graph: nx.Graph, source, destination) -> list | None:
        if not nx.has_path(graph, source, destination):
            return None
        from_source = nx.single_source_shortest_path_length(graph, source)
        to_destination = nx.single_source_shortest_path_length(graph, destination)
        distance = from_source[destination]
        path = [source]
        current = source
        while current != destination:
            choices = [node for node in graph.neighbors(current) if from_source.get(node) == from_source[current] + 1 and from_source[node] + to_destination.get(node, float("inf")) == distance]
            if not choices:
                raise RuntimeError("cannot reconstruct canonical shortest path")
            current = min(choices, key=str)
            path.append(current)
        return path

    def generateTemporalSPCFrames(
        self,
        limited_G: nx.Graph,
        s,
        d,
        timeline: list[bool],
        pi: float,
        mean_up_duration: float,
        seed: int = 0,
    ) -> dict:
        """Generate per-edge Markov frames and project each to the target S-R state."""
        if not 0.0 < pi < 1.0:
            raise ValueError("pi must be strictly between zero and one")
        if mean_up_duration <= 0.0:
            raise ValueError("mean_up_duration must be positive")
        p_up_given_down = pi / ((1.0 - pi) * mean_up_duration)
        if 1.0 / mean_up_duration > 1.0 or p_up_given_down > 1.0:
            raise ValueError("infeasible stationary fraction / up-duration combination")
        if s not in limited_G or d not in limited_G:
            raise nx.NodeNotFound("S and R must both be in the skeleton")

        nodes = list(limited_G.nodes())
        edges = sorted(
            (tuple(sorted(edge, key=str)) for edge in limited_G.edges()),
            key=lambda edge: (str(edge[0]), str(edge[1])),
        )
        edge_chains = [
            self.sample_two_state_chain(
                len(timeline), pi, mean_up_duration, seed + 104729 * edge_index
            )
            for edge_index in range(len(edges))
        ]
        raw_frames = []
        constrained_frames = []
        corrections = []
        for frame_index in range(len(timeline)):
            raw = nx.Graph()
            raw.add_nodes_from(nodes)
            for edge_index, edge in enumerate(edges):
                if edge_chains[edge_index][frame_index]:
                    raw.add_edge(*edge)
            constrained = raw.copy()
            changed_edges = set()
            if timeline[frame_index] and not nx.has_path(constrained, s, d):
                route = self._canonical_shortest_path(limited_G, s, d)
                if route is None:
                    raise nx.NetworkXNoPath("S-R are disconnected in the skeleton")
                for left, right in zip(route, route[1:]):
                    if not constrained.has_edge(left, right):
                        constrained.add_edge(left, right)
                        changed_edges.add(frozenset((left, right)))
            elif not timeline[frame_index] and nx.has_path(constrained, s, d):
                ordered_edges = sorted(
                    (tuple(sorted(edge, key=str)) for edge in constrained.edges()),
                    key=lambda edge: (str(edge[0]), str(edge[1])),
                )
                edge_count = len(ordered_edges)
                cardinality_weight = 1 << edge_count
                weighted = nx.Graph()
                weighted.add_nodes_from(constrained.nodes())
                for rank, edge in enumerate(ordered_edges):
                    lexical_reward = 1 << (edge_count - rank - 1)
                    weighted.add_edge(*edge, capacity=cardinality_weight - lexical_reward)
                _, partition = nx.minimum_cut(weighted, s, d, capacity="capacity")
                left, right = partition
                ordered_cut = [
                    edge for edge in ordered_edges
                    if (edge[0] in left and edge[1] in right)
                    or (edge[1] in left and edge[0] in right)
                ]
                if not ordered_cut:
                    raise RuntimeError("connected S-R frame produced an empty minimum edge cut")
                constrained.remove_edges_from(ordered_cut)
                changed_edges.update(frozenset(edge) for edge in ordered_cut)
            if nx.has_path(constrained, s, d) != bool(timeline[frame_index]):
                raise RuntimeError(f"S-R projection failed at frame {frame_index}")
            raw_frames.append(raw)
            constrained_frames.append(constrained)
            corrections.append(
                sorted(
                    [sorted(edge, key=str) for edge in changed_edges],
                    key=lambda edge: (str(edge[0]), str(edge[1])),
                )
            )

        self.temporal_raw_frames = raw_frames
        self.temporal_frames = constrained_frames
        self.temporal_corrections = corrections
        return {
            "raw_frames": raw_frames,
            "frames": constrained_frames,
            "corrections": corrections,
            "p_down_given_up": 1.0 / mean_up_duration,
            "p_up_given_down": p_up_given_down,
            "pi": pi,
            "mean_up_duration": mean_up_duration,
        }

    def generateSPCFramesOriginal(
        self,
        limited_G: nx.Graph,
        s: str,
        d: str,
        trials: int = 1000,
        p_edge: float = 0.5,
        pathPersistency: float = 0.0,
        seed: int = 0,
    ) -> None:
        """
        Generate `trials` random frames from `limited_G`. For SPC:
        - group frames where a path exists (s->d) by the actual node-sequence of that path.
          self.path_up_frames becomes a list of lists: each sublist contains frames that
          share the same s->d node-sequence (the path), but may differ elsewhere.
        - self.path_down_frames remains a flat list of frames without s->d path.
        - pathPersistency is accepted here for API compatibility (used in timeline builder).
        """
        assert 0.0 <= pathPersistency <= 1.0
        rng = random.Random(seed)
        edges = list(limited_G.edges())
        # temporary map: path_tuple -> list of frames
        path_map = {}
        down_list = []

        for _ in range(trials):
            H = nx.Graph()
            H.add_nodes_from(limited_G.nodes())
            for e in edges:
                if rng.random() < p_edge:
                    H.add_edge(*e)
            # check reachability
            if s in H and d in H and nx.has_path(H, s, d):
                try:
                    path_nodes = tuple(nx.shortest_path(H, s, d))
                except Exception:
                    path_nodes = tuple()
                path_map.setdefault(path_nodes, []).append(H)
            else:
                down_list.append(H)

        # store grouped up-frames as list of lists (stable ordering by stringified path)
        # ensure reproducible order
        ordered_keys = sorted(
            path_map.keys(), key=lambda k: (len(k), tuple(map(str, k)))
        )
        self.path_up_frames = [path_map[k] for k in ordered_keys]
        self.path_down_frames = down_list
        # keep auxiliary info
        self.path_up_keys = ordered_keys

    def generateMPCFrames(
        self,
        limited_G: nx.Graph,
        pairs: List[Tuple[str, str]],
        trials: int = 1000,
        p_edge: float = 0.5,
        seed: int = None,
    ) -> Dict:
        """
        Generate `trials` random frames from `limited_G` and for each frame evaluate
        reachability for each pair in `pairs`.

        Returns a dict with:
          - frames: list of generated nx.Graph objects (length == trials)
          - pairs: the input pairs list (for consumer convenience)
          - cases: dict mapping status_tuple -> list of frame indices where that exact pattern occurs
          - counts: dict mapping status_tuple -> integer count
          - per_pair: list aligned with `pairs`, each entry is dict with:
                'pair': (s,d)
                'up_indices': [...], 'down_indices': [...]
                'idx_to_path': { frame_idx: path_tuple or None }
                'path_map': { path_tuple: [frame_idx, ...] }
        """
        rnd = random.Random(seed)
        edges = list(limited_G.edges())

        frames: List[nx.Graph] = []
        cases: Dict[Tuple[bool, ...], List[int]] = {}
        per_pair = []
        # generate frames (simple Erdos-Renyi subgraph sampling of limited_G)
        for ti in range(trials):
            G = nx.Graph()
            G.add_nodes_from(limited_G.nodes())
            for u, v in edges:
                if rnd.random() < p_edge:
                    G.add_edge(u, v)
            frames.append(G)

        # evaluate reachability for each frame / pair
        idx_to_status = {}
        for idx, G in enumerate(frames):
            status = []
            for s, d in pairs:
                try:
                    # reachability via shortest_path
                    path = nx.shortest_path(G, source=s, target=d)
                    status.append(True)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    status.append(False)
            status_t = tuple(status)
            idx_to_status[idx] = status_t
            cases.setdefault(status_t, []).append(idx)

        # build per-pair information (path keys)
        per_pair = []
        for pi, (s, d) in enumerate(pairs):
            idx_to_path = {}
            path_map = {}
            up_indices = []
            down_indices = []
            for idx, G in enumerate(frames):
                try:
                    path = nx.shortest_path(G, source=s, target=d)
                    # normalize path key as tuple of node names (strings)
                    path_key = tuple(map(str, path))
                    idx_to_path[idx] = path_key
                    path_map.setdefault(path_key, []).append(idx)
                    up_indices.append(idx)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    idx_to_path[idx] = None
                    down_indices.append(idx)
            per_pair.append(
                {
                    "pair": (s, d),
                    "up_indices": up_indices,
                    "down_indices": down_indices,
                    "idx_to_path": idx_to_path,
                    "path_map": path_map,
                }
            )

        counts = {k: len(v) for k, v in cases.items()}

        return {
            "frames": frames,
            "pairs": pairs,
            "cases": cases,
            "counts": counts,
            "per_pair": per_pair,
            "idx_to_status": idx_to_status,
        }

    def clear_frames(self) -> None:
        self.path_up_frames.clear()
        self.path_down_frames.clear()
