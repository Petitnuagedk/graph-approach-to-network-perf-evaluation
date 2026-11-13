from typing import List, Tuple
import random
import networkx as nx
import itertools
import math

# local toggle: set to True to enable prints/logging in this file, False to silence
DG_LOG = False


def _log(*args, **kwargs):
    if DG_LOG:
        print(*args, **kwargs)


class dynamicGraph:
    """
    Base class for DynamicGraph structures.
    """

    def __init__(self):
        self.DynamicGraph = []

    def appendGraph(self, graph: nx.Graph):
        self.DynamicGraph.append(graph)


class SPCDynamicGraph:
    """
    Assembles generated timeline blocks into a cohesive timeline called a DynamicGraph.
    """

    def __init__(self):
        self.DynamicGraph = []

    def buildDynaGraph(self, timeline, path_up, path_down):
        """
        Given a timeline (legacy: List[bool] OR new: dict {'timeline':..., 'path_ids':...})
        and two sets of frames (path_up grouped as list-of-groups, path_down flat list),
        pick frames according to the timeline.

        New behavior for SPC when timeline is labeled:
         - `path_up` is expected to be a list of groups (each group is a list of frames sharing same s->d path).
         - timeline may carry `path_ids` distinguishing desired persistent path identities across up frames.
         - we map timeline path_id -> chosen group index (first occurrence chooses a group randomly,
           subsequent frames with same path_id reuse the same group).
        Legacy behavior (flat path_up list) is still supported.
        """
        rnd = random.Random()

        # accept timeline as either dict or list
        if isinstance(timeline, dict):
            tl = timeline.get("timeline", [])
            path_ids = timeline.get("path_ids", [None] * len(tl))
        else:
            tl = list(timeline)
            path_ids = [None] * len(tl)

        # detect if path_up is grouped (list of lists) or flat (list of graphs)
        grouped_up = False
        if (
            path_up
            and isinstance(path_up, list)
            and any(isinstance(x, list) for x in path_up)
        ):
            grouped_up = True

        # prepare pools
        if grouped_up:
            groups = path_up  # list of lists
            n_groups = len(groups)
        else:
            flat_up = list(path_up) if path_up else []
            n_groups = len(flat_up)

        down_pool = list(path_down) if path_down else []

        # mapping timeline path id -> group index (for grouped_up case)
        pid_to_group = {}

        self.DynamicGraph = []
        for idx, state in enumerate(tl):
            if state:
                # up frame requested
                pid = path_ids[idx] if idx < len(path_ids) else None
                if grouped_up:
                    if n_groups == 0:
                        # no up groups available: fallback to empty graph
                        self.DynamicGraph.append(nx.Graph())
                        continue
                    if pid is None:
                        # no label: pick any group at random
                        gid = rnd.randrange(n_groups)
                    else:
                        if pid in pid_to_group:
                            gid = pid_to_group[pid]
                        else:
                            # choose a group for this path-id (allow reuse)
                            gid = rnd.randrange(n_groups)
                            pid_to_group[pid] = gid
                    # pick a frame from the chosen group
                    group_pool = groups[gid]
                    if group_pool:
                        gf = rnd.choice(group_pool)
                        self.DynamicGraph.append(gf)
                    else:
                        # empty group fallback
                        self.DynamicGraph.append(nx.Graph())
                else:
                    # flat up pool
                    if not flat_up:
                        self.DynamicGraph.append(nx.Graph())
                    else:
                        self.DynamicGraph.append(rnd.choice(flat_up))
            else:
                # down frame
                if down_pool:
                    self.DynamicGraph.append(rnd.choice(down_pool))
                else:
                    # fallback to empty graph
                    self.DynamicGraph.append(nx.Graph())
        return self.DynamicGraph

    def addGraphatindex(self, index: int, graph: nx.Graph):
        """
        Add a graph at a specific index in the DynamicGraph.

        :param index: Index at which to add the graph.
        :param graph: The graph to add.
        """
        if 0 <= index <= len(self.DynamicGraph):
            self.DynamicGraph.insert(index, graph)
        else:
            raise IndexError("Index out of bounds for DynamicGraph.")

    def clearDynaGaph(self):
        """
        Clear all added timeline blocks.
        """
        self.DynamicGraph = []

    def _frame_fingerprint(self, g):
        """
        Return a deterministic fingerprint for a single frame-like object.
        Accepts:
          - networkx Graph-like objects (have .nodes()/.edges())
          - lists of graphs (grouped frames) -> use first non-empty element
        """
        # handle grouped frames (list of graphs)
        if isinstance(g, (list, tuple)):
            if len(g) == 0:
                return ("EMPTY_GROUP",)
            # recurse on first element (it may itself be a group)
            return self._frame_fingerprint(g[0])

        # assume graph-like object
        try:
            nodes = tuple(sorted(map(str, g.nodes())))
            edges = tuple(sorted(tuple(sorted(map(str, e))) for e in g.edges()))
            return (nodes, edges)
        except Exception:
            # fallback: stringify object
            return (str(g),)

    def _timeline_fingerprint(self, frames):
        """
        Produce a fingerprint for a sequence of frames (used to detect duplicates).
        Frames elements may be graphs or grouped lists; _frame_fingerprint handles both.
        """
        return tuple(self._frame_fingerprint(g) for g in frames)

    def generateUniqueSet(
        self,
        timeline: List[bool],
        path_up: List[nx.Graph],
        path_down: List[nx.Graph],
        target_count: int,
        seed: int = None,
        max_enumeration: int = 1000000,
    ) -> List["SPCDynamicGraph"]:
        """
        Generate up to `target_count` distinct DynamicGraph instances following `timeline`.
        Supports the new map-style timeline (dict with 'timeline' and 'path_ids') and
        grouped `path_up` (list-of-groups). When `path_up` is grouped, `path_ids`
        (if provided) bind particular up-frames to the same group index across the whole sequence;

        Behavior:
         - timeline may be a list[bool] or dict {'timeline': [...], 'path_ids': [...]}
         - when path_up is grouped (list of lists), frames with a non-None path_id must
           use the same group for that path_id across the whole sequence; frames with
           path_id == None can select from any group's frames independently.
         - fallback semantics follow buildDynaGraph: for grouped_up, if groups exist
           use them; if groups empty, treat as empty-frame placeholder. For non-grouped
           up/down the previous primary/fallback logic is preserved.
        """
        random.seed(seed)
        _log("Generating unique SPCDynamicGraph set with target_count = ", target_count)

        if target_count <= 0:
            return []

        # accept timeline as either dict or list (same as buildDynaGraph)
        if isinstance(timeline, dict):
            tl = timeline.get("timeline", [])
            path_ids = timeline.get("path_ids", [None] * len(tl))
        else:
            tl = list(timeline)
            path_ids = [None] * len(tl)

        frames = len(tl)

        # detect grouped_up as in buildDynaGraph
        grouped_up = False
        if (
            path_up
            and isinstance(path_up, list)
            and any(isinstance(x, list) for x in path_up)
        ):
            grouped_up = True

        # prepare down pool and flat_up
        down_pool = list(path_down) if path_down else []
        if not grouped_up:
            flat_up = list(path_up) if path_up else []

        results: List[SPCDynamicGraph] = []
        seen = set()

        def build_and_record(frames_seq):
            fp = self._timeline_fingerprint(frames_seq)
            if fp in seen:
                return None
            seen.add(fp)
            dg = SPCDynamicGraph()
            dg.DynamicGraph = frames_seq.copy()
            return dg

        # Non-grouped case: reuse previous behavior (with simple primary/fallback per-frame pools)
        if not grouped_up:
            # Build per-frame pools using primary/fallback logic (same as before)
            pools: List[List[nx.Graph]] = []
            for state in tl:
                primary = flat_up if state else down_pool
                fallback = down_pool if state else flat_up
                if primary:
                    pools.append(primary)
                elif fallback:
                    pools.append(fallback)
                else:
                    pools.append([nx.Graph()])

            sizes = [len(p) for p in pools]
            total_combinations = 1
            for s in sizes:
                total_combinations *= s

            # enumeration path
            if total_combinations <= max_enumeration:
                for indices in itertools.product(*(range(s) for s in sizes)):
                    frames_seq = [pools[i][indices[i]] for i in range(frames)]
                    dg = build_and_record(frames_seq)
                    if dg:
                        results.append(dg)
                        if len(results) >= target_count:
                            break
                return results

            # randomized sampling path
            attempts = 0
            max_attempts = int(
                min(max_enumeration, total_combinations, target_count * 50)
            )
            while len(results) < target_count and attempts < max_attempts:
                indices = [random.randrange(s) for s in sizes]
                frames_seq = [pools[i][indices[i]] for i in range(frames)]
                dg = build_and_record(frames_seq)
                if dg:
                    results.append(dg)
                attempts += 1

            # best-effort deterministic fill
            if (
                len(results) < target_count
                and total_combinations <= max_enumeration * 5
            ):
                for indices in itertools.product(*(range(s) for s in sizes)):
                    frames_seq = [pools[i][indices[i]] for i in range(frames)]
                    dg = build_and_record(frames_seq)
                    if dg:
                        results.append(dg)
                        if len(results) >= target_count:
                            break

            return results

        # Grouped-up case
        # groups is list-of-lists (may contain empty groups)
        groups = path_up if path_up else []
        n_groups = len(groups)
        groups_sizes = [len(g) for g in groups]
        # flattened list of all up-frames across groups (for pid == None cases)
        flat_all = [g for group in groups for g in group]

        # collect ordered unique non-None path_ids to assign group indices to them
        unique_pids = []
        pid_to_slot = {}
        for pid in path_ids:
            if pid is None:
                continue
            if pid not in pid_to_slot:
                pid_to_slot[pid] = len(unique_pids)
                unique_pids.append(pid)
        m = len(unique_pids)

        # helper to create per-frame pools for a given assignment mapping (tuple of group indices per unique_pids slot)
        def pools_for_assignment(assignment):
            # assignment is tuple length m with group indices
            assign_map = {}
            for i, pid in enumerate(unique_pids):
                assign_map[pid] = assignment[i]
            pools_a: List[List[nx.Graph]] = []
            for i, state in enumerate(tl):
                if not state:
                    # down frame: use down_pool or placeholder
                    if down_pool:
                        pools_a.append(down_pool)
                    else:
                        pools_a.append([nx.Graph()])
                else:
                    # up frame: if no groups (n_groups==0) -> placeholder (matches buildDynaGraph)
                    if n_groups == 0:
                        pools_a.append([nx.Graph()])
                        continue
                    pid = path_ids[i] if i < len(path_ids) else None
                    if pid is None:
                        # can pick any group's frames
                        if flat_all:
                            pools_a.append(flat_all)
                        else:
                            pools_a.append([nx.Graph()])
                    else:
                        gid = assign_map.get(pid, None)
                        # if gid is invalid (shouldn't happen) treat as placeholder
                        if gid is None or gid < 0 or gid >= n_groups:
                            pools_a.append([nx.Graph()])
                        else:
                            group_pool = groups[gid]
                            if group_pool:
                                pools_a.append(group_pool)
                            else:
                                pools_a.append([nx.Graph()])
            return pools_a

        # compute total combinations by summing over assignments product of per-frame pool sizes
        total_combinations = 0
        if m == 0:
            # single 'assignment' where there are no pid bindings
            pools0 = pools_for_assignment(())
            sizes0 = [len(p) for p in pools0]
            prod0 = 1
            for s in sizes0:
                prod0 *= s
            total_combinations = prod0
        else:
            # avoid iterating all n_groups**m assignments when that count is huge.
            assignment_count = n_groups**m
            # threshold for exact assignment enumeration (tunable)
            EXACT_ASSIGNMENT_LIMIT = min(100000, max(10000, int(max_enumeration)))
            if assignment_count <= EXACT_ASSIGNMENT_LIMIT:
                # exact enumeration (safe)
                for assignment in itertools.product(range(n_groups), repeat=m):
                    pools_a = pools_for_assignment(assignment)
                    prod = 1
                    for p in pools_a:
                        prod *= len(p)
                    total_combinations += prod
            else:
                # sample assignments to estimate average per-assignment product,
                # then extrapolate to approximate total_combinations.
                SAMPLE_LIMIT = 2000
                sample_n = min(SAMPLE_LIMIT, assignment_count)
                sum_prod = 0
                for _ in range(sample_n):
                    assignment = tuple(random.randrange(n_groups) for _ in range(m))
                    pools_a = pools_for_assignment(assignment)
                    prod = 1
                    for p in pools_a:
                        prod *= len(p)
                    sum_prod += prod
                avg_prod = (sum_prod / sample_n) if sample_n > 0 else 0
                # conservative estimate, but prevent zero which would break logic
                est_total = int(avg_prod * assignment_count)
                total_combinations = max(est_total, assignment_count, 1)
                _log(
                    f"estimate total_combinations={total_combinations} (assignment_count={assignment_count}, avg_prod={avg_prod:.2f})"
                )

        # enumeration path if small enough
        if total_combinations <= max_enumeration:
            if m == 0:
                # single assignment
                pools_a = pools_for_assignment(())
                sizes = [len(p) for p in pools_a]
                for indices in itertools.product(*(range(s) for s in sizes)):
                    frames_seq = [pools_a[i][indices[i]] for i in range(frames)]
                    dg = build_and_record(frames_seq)
                    if dg:
                        results.append(dg)
                        if len(results) >= target_count:
                            break
                return results
            else:
                for assignment in itertools.product(range(n_groups), repeat=m):
                    pools_a = pools_for_assignment(assignment)
                    sizes = [len(p) for p in pools_a]
                    for indices in itertools.product(*(range(s) for s in sizes)):
                        frames_seq = [pools_a[i][indices[i]] for i in range(frames)]
                        dg = build_and_record(frames_seq)
                        if dg:
                            results.append(dg)
                            if len(results) >= target_count:
                                break
                    if len(results) >= target_count:
                        break
                return results

        # randomized sampling path (total_combinations huge)
        attempts = 0
        # Allow more trials for hard labeled constraints so rare-valid combos can be found.
        max_attempts = int(
            min(
                max_enumeration,
                total_combinations if total_combinations > 0 else max_enumeration,
                max(target_count * 1000, 1000),
            )
        )
        _log(f"[generateUniqueSet-MPC] max_attempts={max_attempts}")
        while len(results) < target_count and attempts < max_attempts:
            # pick a random assignment for labeled pids
            if m == 0:
                assignment = ()
            else:
                assignment = tuple(random.randrange(n_groups) for _ in range(m))
            pools_a = pools_for_assignment(assignment)
            # pick random index from each pool
            indices = [random.randrange(len(p)) for p in pools_a]
            frames_seq = [pools_a[i][indices[i]] for i in range(frames)]
            dg = build_and_record(frames_seq)
            if dg:
                results.append(dg)
            attempts += 1

        # best-effort deterministic fill if still short and not too enormous
        if len(results) < target_count and total_combinations <= max_enumeration * 5:
            _log("[generateUniqueSet-MPC] doing best-effort deterministic fill")
            for indices in itertools.product(*(range(s) for s in sizes)):
                frames_seq = [pools[i][indices[i]] for i in range(frames)]
                dg = build_and_record(frames_seq)
                if dg:
                    results.append(dg)
                    if len(results) >= target_count:
                        break
            _log(
                f"[generateUniqueSet-MPC] deterministic fill finished, total found {len(results)}"
            )

        _log(f"[generateUniqueSet-MPC] returning {len(results)} dynamics")
        return results


class MPCDynamicGraph:
    """
    Build a dynamic graph sequence for Multi-Pair timelines.

    Core method:
      - buildDynaGraph(mpc_timeline, mpc_frame_set, seed=None, no_double=True)

    - mpc_timeline: list of tuples of booleans, one tuple per frame (e.g. [(True,False),(True,False)])
    - mpc_frame_set: output of FrameGenerator.generate_frames_for_pairs, expected keys:
        'frames' : list[nx.Graph]
        'cases'  : dict{ status_tuple -> [frame_indices] }
    - seed: optional int for deterministic selection
    - no_double: if True avoid reusing the same frame index twice when possible
    """

    def __init__(self):
        self.DynamicGraph: List[nx.Graph] = []
        self.selected_frame_indices: List[int] = []
        self.selected_statuses: List[Tuple[bool, ...]] = []

    def _hamming(self, a: Tuple[bool, ...], b: Tuple[bool, ...]) -> int:
        return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))

    def buildDynaGraph(
        self,
        mpc_timeline: List[Tuple[bool, ...]],
        mpc_frame_set: dict,
        seed: int = None,
        no_double: bool = True,
        allow_hamming_fallback: bool = True,
        force: bool = True,
    ) -> List[nx.Graph]:
        """
        Modified to accept MPC timeline in the new form:
          - mpc_timeline: list of tuples of Optional[int] per pair (None -> down, int -> up with id)
        Greedy persistence:
          - when a non-None id appears for a given pair, we map that id -> a chosen path_key (first occurrence)
            and subsequent frames that reference same id will prefer frames with the same path_key.
        force: if False, abort when a required pool is empty and no fallback allowed.
               if True, attempt fallbacks (Hamming, any-unused, any) with warnings.
        """
        rnd = random.Random(seed)

        frames = mpc_frame_set.get("frames", [])
        cases = mpc_frame_set.get("cases", {})
        per_pair = mpc_frame_set.get("per_pair", None)
        pairs = mpc_frame_set.get("pairs", None)

        if not mpc_timeline:
            raise ValueError("mpc_timeline is empty")
        if not frames:
            raise ValueError("mpc_frame_set has no frames")

        # normalize timeline entries to tuples; detect if entries are id-labeled (None or int) or boolean tuples
        labeled = False
        # target structure: list of tuples of Optional[int] (None -> down, int -> up)
        timeline = []
        for t in mpc_timeline:
            tpl = tuple(x for x in t)
            timeline.append(tpl)
            if any(x is not None for x in tpl):
                labeled = True

        # precompute idx -> status (boolean tuple)
        idx_to_status = mpc_frame_set.get("idx_to_status", None)
        if not idx_to_status:
            # build from cases
            idx_to_status = {}
            for status, idxs in cases.items():
                for i in idxs:
                    idx_to_status[i] = status

        # helper: status tuple (bool) from labeled timeline entry
        def status_from_labeled(entry):
            return tuple(((x is not None) for x in entry))

        # prepare available pools (copy)
        available = {k: list(v) for k, v in cases.items()}

        chosen_indices: List[int] = []
        chosen_statuses: List[Tuple[bool, ...]] = []

        all_indices = set(range(len(frames)))

        # prepare persistence maps per pair: mapping pid -> path_key
        pid_maps_per_pair = []
        n_pairs = len(timeline[0])

        # extract per_pair idx_to_path if available
        per_pair_idx_to_path = []
        if per_pair:
            for pp in per_pair:
                per_pair_idx_to_path.append(pp.get("idx_to_path", {}))
        else:
            # try to compute if 'pairs' & frames available (best-effort)
            per_pair_idx_to_path = [{} for _ in range(n_pairs)]
            if pairs:
                for pi, (s, d) in enumerate(pairs):
                    for idx, G in enumerate(frames):
                        try:
                            p = nx.shortest_path(G, source=s, target=d)
                            per_pair_idx_to_path[pi][idx] = tuple(map(str, p))
                        except (nx.NetworkXNoPath, nx.NodeNotFound):
                            per_pair_idx_to_path[pi][idx] = None

        for frame_entry in timeline:
            desired_status = status_from_labeled(frame_entry)
            # base pool: exact match of status
            pool = available.get(desired_status, []).copy()
            if not pool:
                if force:
                    # fallback flow with warning
                    _log(
                        f"warning: no exact pool for status {desired_status}, attempting fallbacks (force=True)"
                    )
                    # Try hamming fallback
                    found = False
                    if allow_hamming_fallback and cases:
                        candidates = sorted(
                            cases.keys(), key=lambda s: self._hamming(s, desired_status)
                        )
                        for cand in candidates:
                            pool2 = available.get(cand, [])
                            if pool2:
                                pool = pool2.copy()
                                found = True
                                break
                    if not found:
                        # fallback to any unused if no_double
                        remaining = (
                            list(all_indices - set(chosen_indices)) if no_double else []
                        )
                        if remaining:
                            pool = remaining
                        else:
                            # last resort all frames
                            pool = list(all_indices)
                else:
                    print(
                        f"aborting: no pool for status {desired_status} and force=False"
                    )
                    raise RuntimeError(f"No pool for status {desired_status}")

            # apply greedy pid constraints (if labeled)
            # build mapping pid -> chosen path_key for this frame set if needed
            # pid_maps_per_pair will be built on demand
            if labeled:
                # ensure pid_maps_per_pair length
                while len(pid_maps_per_pair) < n_pairs:
                    pid_maps_per_pair.append({})

                # for each pair with a non-None pid, try to filter pool
                filtered = pool
                for pi, pid in enumerate(frame_entry):
                    if pid is None:
                        continue
                    pid_map = pid_maps_per_pair[pi]
                    # if pid already bound -> filter pool to frames matching that path_key
                    if pid in pid_map:
                        desired_path = pid_map[pid]
                        filtered = [
                            i
                            for i in filtered
                            if per_pair_idx_to_path[pi].get(i, None) == desired_path
                        ]
                        if not filtered:
                            break
                    else:
                        # bind pid greedily to some candidate's path_key (choose random candidate that is up for this pair)
                        candidates_with_path = [
                            i
                            for i in filtered
                            if per_pair_idx_to_path[pi].get(i, None) is not None
                        ]
                        if candidates_with_path:
                            chosen_idx = rnd.choice(candidates_with_path)
                            pid_map[pid] = per_pair_idx_to_path[pi].get(chosen_idx)
                            # now filter to match that chosen path
                            desired_path = pid_map[pid]
                            filtered = [
                                i
                                for i in filtered
                                if per_pair_idx_to_path[pi].get(i, None) == desired_path
                            ]
                        else:
                            # no candidate with a path for this pair -> empty
                            filtered = []
                            break
                if not filtered:
                    if force:
                        _log(
                            f"warning: pid constraints left empty pool for frame {frame_entry}, relaxing constraints"
                        )
                        # relax pid constraints and keep base pool
                        filtered = pool
                    else:
                        _log(
                            f"aborting: pid constraints unsatisfiable for frame {frame_entry} and force=False"
                        )
                        raise RuntimeError(
                            f"pid constraints unsatisfiable for frame {frame_entry}"
                        )
                pool = filtered

            # choose one from pool
            if pool:
                idx = rnd.choice(pool)
                chosen_indices.append(idx)
                chosen_statuses.append(idx_to_status.get(idx, tuple()))
                if no_double:
                    # remove from available pools where present
                    for k in list(available.keys()):
                        if idx in available[k]:
                            available[k].remove(idx)
                continue
            else:
                # pool empty after all attempts
                if force:
                    # pick any frame as last resort
                    idx = rnd.randrange(len(frames))
                    chosen_indices.append(idx)
                    chosen_statuses.append(idx_to_status.get(idx, tuple()))
                else:
                    raise RuntimeError(f"No candidate found for frame {frame_entry}")

        # assemble DynamicGraph frames
        self.DynamicGraph = [frames[i] for i in chosen_indices]
        self.selected_frame_indices = chosen_indices
        self.selected_statuses = chosen_statuses

        return self.DynamicGraph

    def generateUniqueSet(
        self,
        mpc_timeline: List[Tuple[bool, ...]],
        mpc_frame_set: dict,
        target_count: int,
        seed: int = None,
        max_enumeration: int = 1000000,
        force: bool = True,
    ) -> List["MPCDynamicGraph"]:
        """
        Generate unique MPCDynamicGraph sequences honoring greedy pid persistence if
        mpc_timeline entries are id-labeled (None or int per pair).
        force controls whether to attempt fallbacks when a pool is empty (True), or abort (False).
        """
        rnd = random.Random(seed)

        frames = mpc_frame_set.get("frames", [])
        cases = mpc_frame_set.get("cases", {})

        if target_count <= 0:
            return []
        if not mpc_timeline:
            raise ValueError("mpc_timeline is empty")
        if not frames:
            raise ValueError("mpc_frame_set has no frames")

        # determine if timeline is labeled (None/int) or simple booleans
        labeled = any(any(x is not None for x in t) for t in mpc_timeline)

        _log(
            f"[generateUniqueSet-MPC] frames={len(frames)}, cases_keys={len(cases)}, target_count={target_count}, labeled={labeled}, seed={seed}"
        )

        # build per-frame pools by status (like before)
        pools_idx: List[List[int]] = []
        all_indices = list(range(len(frames)))
        # also keep per_pair idx_to_path if present
        per_pair = mpc_frame_set.get("per_pair", None)
        per_pair_idx_to_path = []
        if per_pair:
            per_pair_idx_to_path = [pp.get("idx_to_path", {}) for pp in per_pair]
        else:
            # best-effort empty maps if not present
            per_pair_idx_to_path = []

        # normalize and produce desired status tuples from labeled timeline
        desired_statuses = []
        for entry in mpc_timeline:
            # entry may be boolean tuple or labeled tuple (None/int)
            if any(x is None or isinstance(x, int) for x in entry):
                desired_statuses.append(tuple((x is not None) for x in entry))
            else:
                desired_statuses.append(tuple(bool(x) for x in entry))

        for si, status in enumerate(desired_statuses):
            idxs = list(cases.get(status, []))
            if not idxs:
                if force:
                    # fallback to all frames (but warn)
                    _log(
                        f"[generateUniqueSet-MPC] warning: no exact pool for status {status} (frame {si}), falling back to all frames (force=True)"
                    )
                    idxs = all_indices.copy()
                else:
                    raise RuntimeError(f"No pool for status {status}")
            pools_idx.append(idxs)

        sizes = [len(p) for p in pools_idx]
        _log(f"[generateUniqueSet-MPC] pools per frame: {sizes}")

        # quick size calc
        total_combinations = 1
        for s in sizes:
            total_combinations *= s
        _log(
            f"[generateUniqueSet-MPC] estimated total_combinations (product of sizes) = {total_combinations}"
        )

        # fingerprint helpers (same as before)
        def _frame_fingerprint(g: nx.Graph):
            if g is None:
                return ("nodes", tuple(), "edges", tuple())
            nodes = tuple(sorted(map(str, g.nodes())))
            edges = tuple(sorted(tuple(sorted((str(u), str(v)))) for u, v in g.edges()))
            return ("nodes", nodes, "edges", edges)

        def _timeline_fingerprint(seq: List[nx.Graph]):
            return tuple(_frame_fingerprint(g) for g in seq)

        results: List[MPCDynamicGraph] = []
        seen = set()

        # check a candidate choice for pid-consistency (greedy):
        def choice_accepts(choice_idxs: List[int], labeled_timeline):
            # labeled_timeline: original mpc_timeline entries (None/int per pair)
            if not labeled:
                return True
            # ensure per_pair_idx_to_path has entries for all pairs; if not, compute is impossible => reject
            if not per_pair_idx_to_path:
                # attempt best-effort: accept but warn
                _log(
                    "[generateUniqueSet-MPC] warning: per_pair path info missing; cannot enforce pid persistence -> accepting any choice"
                )
                return True
            pid_maps_per_pair = [{} for _ in range(len(per_pair_idx_to_path))]
            for pos, idx in enumerate(choice_idxs):
                entry = labeled_timeline[pos]
                # for each pair in entry
                for pi, pid in enumerate(entry):
                    if pid is None:
                        continue
                    path_key = per_pair_idx_to_path[pi].get(idx, None)
                    if pid in pid_maps_per_pair[pi]:
                        # relaxed handling: treat None as "unknown wildcard"
                        existing = pid_maps_per_pair[pi][pid]
                        if existing is None and path_key is not None:
                            # bind unknown to observed path_key
                            pid_maps_per_pair[pi][pid] = path_key
                        elif existing is not None and path_key is None:
                            # keep existing binding (observed None is wildcard)
                            pass
                        elif existing is None and path_key is None:
                            # both unknown -> still compatible
                            pass
                        elif existing != path_key:
                            # real conflict
                            return False
                    else:
                        # bind pid to observed path_key (may be None)
                        pid_maps_per_pair[pi][pid] = path_key
            return True

        # builder function (with logging)
        def build_from_choice_indices(choice_idxs: List[int]):
            seq = [frames[i] for i in choice_idxs]
            fp = _timeline_fingerprint(seq)
            if fp in seen:
                _log(
                    f"[generateUniqueSet-MPC] skipped duplicate fingerprint for indices {choice_idxs}"
                )
                return None
            seen.add(fp)
            dg = MPCDynamicGraph()
            dg.DynamicGraph = seq.copy()
            dg.selected_frame_indices = choice_idxs.copy()
            _log(f"[generateUniqueSet-MPC] recorded DG for indices {choice_idxs}")
            return dg

        # enumeration path (still expensive but we filter by pid consistency)
        if total_combinations <= max_enumeration:
            _log("[generateUniqueSet-MPC] doing exact enumeration")
            for combo in itertools.product(
                *(range(len(pools_idx[i])) for i in range(len(pools_idx)))
            ):
                choice = [pools_idx[i][combo[i]] for i in range(len(combo))]
                if labeled:
                    if not choice_accepts(choice, mpc_timeline):
                        # debug: show small sample of rejections
                        _log(
                            f"[generateUniqueSet-MPC] rejected by choice_accepts: {choice}"
                        )
                        continue
                dg = build_from_choice_indices(choice)
                if dg:
                    results.append(dg)
                    if len(results) >= target_count:
                        break
            _log(
                f"[generateUniqueSet-MPC] enumeration finished, found {len(results)} results"
            )
            return results

        # randomized sampling path
        _log("[generateUniqueSet-MPC] entering randomized sampling path")
        attempts = 0
        # Allow more trials for hard labeled constraints so rare-valid combos can be found.
        max_attempts = int(
            min(
                max_enumeration,
                total_combinations if total_combinations > 0 else max_enumeration,
                max(target_count * 1000, 1000),
            )
        )
        _log(f"[generateUniqueSet-MPC] max_attempts={max_attempts}")
        while len(results) < target_count and attempts < max_attempts:
            choice = [rnd.choice(pools_idx[i]) for i in range(len(pools_idx))]
            if labeled and not choice_accepts(choice, mpc_timeline):
                if attempts < 50:
                    _log(
                        f"[generateUniqueSet-MPC] attempt {attempts} rejected by choice_accepts: {choice}"
                    )
                attempts += 1
                continue
            if attempts < 50:
                _log(
                    f"[generateUniqueSet-MPC] attempt {attempts} candidate choice: {choice}"
                )
            dg = build_from_choice_indices(choice)
            if dg:
                results.append(dg)
            attempts += 1

        _log(
            f"[generateUniqueSet-MPC] sampling finished after {attempts} attempts, found {len(results)} results"
        )

        # best-effort deterministic fill if still short (bounded)
        if len(results) < target_count and total_combinations <= max_enumeration * 5:
            _log("[generateUniqueSet-MPC] doing best-effort deterministic fill")
            for combo in itertools.product(
                *(range(len(pools_idx[i])) for i in range(len(pools_idx)))
            ):
                choice = [pools_idx[i][combo[i]] for i in range(len(combo))]
                if labeled and not choice_accepts(choice, mpc_timeline):
                    continue
                dg = build_from_choice_indices(choice)
                if dg:
                    results.append(dg)
                    if len(results) >= target_count:
                        break
            _log(
                f"[generateUniqueSet-MPC] deterministic fill finished, total found {len(results)}"
            )

        _log(f"[generateUniqueSet-MPC] returning {len(results)} dynamics")
        return results
