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

    def generateSPCFrames(
        self,
        limited_G: nx.Graph,
        s: str,
        d: str,
        trials: int = 1000,
        p_edge: float = 0.5,
        pathPersistency: float = 0.0,
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
        edges = list(limited_G.edges())
        # temporary map: path_tuple -> list of frames
        path_map = {}
        down_list = []

        for _ in range(trials):
            H = nx.Graph()
            H.add_nodes_from(limited_G.nodes())
            for e in edges:
                if random.random() < p_edge:
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
