import networkx as nx
import random


class SourceGraphAugmenter:

    def __init__(self):
        pass

    def augment_graph_keep_baseline(G: nx.Graph, s: str, d: str) -> nx.Graph:
        """
        Return a new graph that contains G plus any extra edge (u,v) between
        nodes that are not neighbors in G such that adding (u,v) does NOT reduce
        the shortest-path length between s and d (compared to the baseline).
        Baseline is computed on the original G.
        """
        baseline = None
        try:
            baseline = nx.shortest_path_length(G, s, d)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            baseline = float("inf")

        limited = G.copy()
        nodes = list(G.nodes())
        n = len(nodes)
        for i in range(n):
            for j in range(i + 1, n):
                u, v = nodes[i], nodes[j]
                if limited.has_edge(u, v):
                    continue
                # test adding (u, v) to original graph and see new distance
                H = G.copy()
                H.add_edge(u, v)
                try:
                    new_len = nx.shortest_path_length(H, s, d)
                except nx.NetworkXNoPath:
                    new_len = float("inf")
                # only allow the new edge if it does NOT reduce the s-d distance
                if new_len >= baseline:
                    limited.add_edge(u, v)
        return limited

    def augmentBaseGraph(
        G: nx.Graph,
        group,
        seed: int = None,
        max_edges: int = None,
        verbose: bool = False,
    ) -> nx.Graph:
        """
        Greedy, order-randomized augmentation that keeps original group baselines.

        Behaviour:
         - baseline distances are computed once on the original G for each pair in `group`.
         - candidate non-edges are shuffled deterministically with `seed`.
         - iterate candidates one by one; when an edge is accepted it is permanently
           added to the working graph and becomes the base for subsequent tests.
         - an edge is accepted only if adding it to the current working graph does NOT
           reduce the shortest-path length for ANY pair in `group` compared to the
           original baseline.
         - this is a single-branch greedy walk through the space of augmentations;
           the `seed` determines which branch is explored. `max_edges` can cap
           how many edges are added.

        Params:
         - G: original graph
         - group: iterable of pairs (e.g. [["A","C"], ["A","D"]])
         - seed: optional int to deterministically shuffle candidate edge order
         - max_edges: optional int to stop after adding this many edges
         - verbose: print progress if True

        Returns:
         - limited: augmented graph (copy of G with accepted edges added)
        """
        # normalize group into list of tuple strings
        group_pairs = []
        for item in group:
            try:
                a, b = item
            except Exception:
                continue
            group_pairs.append((str(a), str(b)))

        # compute baseline distances on original G
        baseline = {}
        for u, v in group_pairs:
            try:
                baseline[(u, v)] = nx.shortest_path_length(G, u, v)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                baseline[(u, v)] = float("inf")

        limited = G.copy()
        nodes = list(G.nodes())
        # build candidate non-edges (u,v) with u < v to avoid duplicates
        candidates = []
        n = len(nodes)
        for i in range(n):
            for j in range(i + 1, n):
                u, v = nodes[i], nodes[j]
                if not limited.has_edge(u, v):
                    candidates.append((u, v))

        rnd = random.Random(seed)
        rnd.shuffle(candidates)

        added = 0
        for u, v in candidates:
            # stop if reached max_edges
            if max_edges is not None and added >= max_edges:
                break

            # test adding (u, v) to the current working graph
            H = limited.copy()
            H.add_edge(u, v)

            reduces_distance = False
            for x, y in group_pairs:
                # skip if x or y not present in H (treat as no reduction)
                if x not in H or y not in H:
                    continue
                try:
                    new_len = nx.shortest_path_length(H, x, y)
                except nx.NetworkXNoPath:
                    new_len = float("inf")
                if new_len < baseline.get((x, y), float("inf")):
                    reduces_distance = True
                    break

            if not reduces_distance:
                limited.add_edge(u, v)
                added += 1
                if verbose:
                    print(f"Accepted edge {(u, v)} (total added {added})")
            else:
                if verbose:
                    print(
                        f"Rejected edge {(u, v)} (would reduce distance for some group pair)"
                    )

        return limited
