from typing import List, Tuple
import random


class SPCTimelineBlockGenerator:
    """
    TimelineBlockGenerator is responsible for generating blocks of timelines
    based on specified criteria. It includes methods for creating and managing
    timeline blocks.
    """

    def __init__(
        self,
        frames: int,
        path_life: float,
        stability: float,
        seed: float,
        mode: str = "blocks",
        pathPersistency: float = 0.0,
    ):
        self.frames = frames
        self.path_life = path_life
        self.stability = stability
        self.mode = mode
        self.seed = seed
        self.pathPersistency = (
            float(pathPersistency) if pathPersistency is not None else 0.0
        )

    def generate_blocks(self) -> dict:
        """
        Generate a sequence of booleans representing timeline blocks (legacy behavior)
        plus a parallel `path_ids` list labeling up-frames with an integer id.

        Returns dict:
           { 'timeline': List[bool], 'path_ids': List[Optional[int]] }

        path_ids: None for down frames, integer id for up frames. Ids indicate which
        up-frames should share the same path identity. Id assignment is deterministic
        given `seed` and reflects `pathPersistency`:
          - 1.0 -> all frames inside an up run share same id
          - 0.0 -> each successive up frame gets a new id
          - intermediate -> probability of keeping same id between successive up frames = pathPersistency
        """
        random.seed(self.seed)
        if self.frames <= 0:
            return {"timeline": [], "path_ids": []}

        # reuse existing logic to compute boolean timeline
        up_count = int(round(self.frames * self.path_life))
        up_count = max(0, min(self.frames, up_count))
        down_count = self.frames - up_count

        if self.mode == "random":
            timeline = [True] * up_count + [False] * down_count
            random.shuffle(timeline)
            # assign path_ids based on persistence rule applied on successive True frames
            path_ids = [None] * len(timeline)
            next_pid = 0
            last_pid = None
            for i, st in enumerate(timeline):
                if st:
                    if last_pid is None:
                        pid = next_pid
                        next_pid += 1
                    else:
                        if random.random() < self.pathPersistency:
                            pid = last_pid
                        else:
                            pid = next_pid
                            next_pid += 1
                    path_ids[i] = pid
                    last_pid = pid
                else:
                    last_pid = None
            self.last_timeline = timeline
            self.last_path_ids = path_ids
            return {"timeline": timeline, "path_ids": path_ids}

        # trivial cases
        if up_count == 0:
            timeline = [False] * self.frames
            path_ids = [None] * self.frames
            self.last_timeline = timeline
            self.last_path_ids = path_ids
            return {"timeline": timeline, "path_ids": path_ids}
        if down_count == 0:
            timeline = [True] * self.frames
            # If all frames up, decide id assignment according to pathPersistency
            path_ids = [None] * self.frames
            next_pid = 0
            last_pid = None
            for i in range(self.frames):
                if last_pid is None:
                    pid = next_pid
                    next_pid += 1
                else:
                    if random.random() < self.pathPersistency:
                        pid = last_pid
                    else:
                        pid = next_pid
                        next_pid += 1
                path_ids[i] = pid
                last_pid = pid
            self.last_timeline = timeline
            self.last_path_ids = path_ids
            return {"timeline": timeline, "path_ids": path_ids}

        # determine number of up blocks based on stability
        # min_up_blocks = 1, max_up_blocks = up_count (each up frame isolated)
        min_up_blocks = 1
        max_up_blocks = up_count
        up_blocks = int(
            round(
                min_up_blocks
                + (1.0 - float(self.stability)) * (max_up_blocks - min_up_blocks)
            )
        )
        up_blocks = max(min_up_blocks, min(max_up_blocks, up_blocks))
        # Every pair of adjacent up-runs needs at least one separating down
        # frame. Without this bound, high path_life plus moderate stability
        # can request more up-runs than the available down frames can separate.
        up_blocks = min(up_blocks, down_count + 1)

        # helper to split a total into `parts` positive integers (as even as possible)
        def _split_counts(total: int, parts: int) -> List[int]:
            parts = max(1, min(parts, total))
            base = total // parts
            rem = total % parts
            sizes = [base + (1 if i < rem else 0) for i in range(parts)]
            # ensure each part at least 1 if possible
            for i in range(len(sizes)):
                if sizes[i] == 0:
                    sizes[i] = 1
            # adjust if we increased sum beyond total (rare)
            while sum(sizes) > total:
                for j in range(len(sizes) - 1, -1, -1):
                    if sizes[j] > 1 and sum(sizes) > total:
                        sizes[j] -= 1
            return sizes

        # decide number of down blocks
        # minimal internal down blocks between up blocks is up_blocks - 1
        # possible down blocks are in [max(1, up_blocks - 1), up_blocks + 1]
        min_down_blocks = max(1, up_blocks - 1)
        max_down_blocks = min(
            up_blocks + 1, down_count
        )  # cannot exceed count (each block >=1)
        if max_down_blocks < min_down_blocks:
            # fallback: force min_down_blocks but will merge later
            max_down_blocks = min_down_blocks

        if up_blocks == 1:
            # single up block: either place on edge (one down block) or in middle (two down blocks)
            if down_count == 1:
                down_blocks = 1
            elif down_count >= 2:
                # random placement: half chance middle (2 down blocks), half chance edge (1 down block)
                if random.choice([True, False]):
                    down_blocks = 2
                else:
                    down_blocks = 1
            else:
                down_blocks = 1
            down_blocks = min(down_blocks, down_count)
        else:
            # multiple up blocks: prefer internal down blocks only (start and end with up)
            preferred = up_blocks - 1
            if preferred <= max_down_blocks:
                down_blocks = preferred
            else:
                down_blocks = max_down_blocks

        down_blocks = max(min_down_blocks, min(max_down_blocks, down_blocks))

        # generate sizes
        up_sizes = _split_counts(up_count, up_blocks)
        down_sizes = _split_counts(down_count, down_blocks)

        # build sequence of states (blocks) by interleaving
        blocks: List[Tuple[bool, int]] = []

        # Decide starting state to fit number of blocks: possible patterns depend on counts
        # If down_blocks == up_blocks + 1 -> must start with down and end with down
        # If down_blocks == up_blocks - 1 -> start and end with up
        # If equal -> start with either; prefer starting with up for visibility
        if down_blocks == up_blocks + 1:
            # pattern: D U D U ... D (starts with down)
            d_idx = 0
            u_idx = 0
            for i in range(down_blocks + up_blocks):
                if i % 2 == 0:
                    # down
                    blocks.append((False, down_sizes[d_idx]))
                    d_idx += 1
                else:
                    blocks.append((True, up_sizes[u_idx]))
                    u_idx += 1
        elif down_blocks == up_blocks - 1:
            # pattern: U D U D ... U (starts with up and ends with up)
            u_idx = 0
            d_idx = 0
            for i in range(down_blocks + up_blocks):
                if i % 2 == 0:
                    blocks.append((True, up_sizes[u_idx]))
                    u_idx += 1
                else:
                    blocks.append((False, down_sizes[d_idx]))
                    d_idx += 1
        else:
            # down_blocks == up_blocks or single up block cases where we may want edge/middle placement
            # prefer putting up blocks separated by downs and start with up
            u_idx = 0
            d_idx = 0
            start_with_up = True
            if up_blocks == 1 and down_blocks == 1:
                # when single up and single down, randomly choose order (edge placement)
                start_with_up = random.choice([True, False])
            for i in range(down_blocks + up_blocks):
                if start_with_up:
                    if i % 2 == 0:
                        blocks.append((True, up_sizes[u_idx]))
                        u_idx += 1
                    else:
                        blocks.append((False, down_sizes[d_idx]))
                        d_idx += 1
                else:
                    if i % 2 == 0:
                        blocks.append((False, down_sizes[d_idx]))
                        d_idx += 1
                    else:
                        blocks.append((True, up_sizes[u_idx]))
                        u_idx += 1

        # build timeline from blocks
        timeline: List[bool] = []
        for st, size in blocks:
            timeline.extend([bool(st)] * size)

        # final adjustment to ensure exact frame count
        if len(timeline) > self.frames:
            timeline = timeline[: self.frames]
        elif len(timeline) < self.frames:
            # pad with last state
            if timeline:
                timeline.extend([timeline[-1]] * (self.frames - len(timeline)))
            else:
                timeline = [False] * self.frames

        # After timeline computed: assign path_ids according to pathPersistency
        path_ids = [None] * len(timeline)
        next_pid = 0
        last_pid = None
        for i, st in enumerate(timeline):
            if st:
                if last_pid is None:
                    pid = next_pid
                    next_pid += 1
                else:
                    # print(random.random(), self.pathPersistency)
                    if random.random() < self.pathPersistency:
                        pid = last_pid
                    else:
                        pid = next_pid
                        next_pid += 1
                path_ids[i] = pid
                last_pid = pid
            else:
                last_pid = None
            # print(i, st, path_ids[i], last_pid)
        self.last_timeline = timeline
        self.last_path_ids = path_ids
        return {"timeline": timeline, "path_ids": path_ids}


class MPCTimelineBlockGenerator:
    """
    Multi-Pair (MPC) timeline block generator.

    Creates a timeline of length `frames` where each frame is a tuple of booleans
    of size `n_pairs` representing the up/down state of each tracked pair.

    Parameters passed to constructor:
      - frames: total number of frames
      - n_pairs: number of (source,destination) pairs to track
      - path_life: average fraction of frames where a pair is up (0..1)
      - stability: average stability for up blocks per pair (0..1)
      - mode: 'sync' or 'indep'
          - 'sync' (default) builds a single global up/down block timeline and
            replicates it across all pairs (useful when pairs are correlated).
          - 'indep' builds independent timelines per pair (same stats but different placements).
      - seed: optional random seed for deterministic generation

    The generate() method returns a list of frame-state tuples:
      e.g. for n_pairs==3: [(False,False,False),(True,True,True), ...]
    """

    def __init__(
        self,
        frames: int,
        n_pairs: int,
        path_life: float,
        stability: float,
        mode: str = "sync",
        seed: int = None,
        pathPersistency: float = 0.0,
    ):
        self.frames = frames
        self.n_pairs = n_pairs
        self.path_life = path_life
        self.stability = stability
        self.mode = mode
        self.seed = seed
        self.pathPersistency = (
            float(pathPersistency) if pathPersistency is not None else 0.0
        )

    def generate(self):
        """
        Return a list of length `frames`. Each element is a tuple of length `n_pairs`.
        Each tuple entry is either:
          - None  -> pair is down in that frame
          - int   -> an id for an up-state (ids are integers used to enforce persistence)

        Path id semantics (per-pair):
          - When a pair transitions into up, a new id is created.
          - While up, successive up-frames may keep the same id with probability pathPersistency,
            otherwise a new id is emitted. This mirrors SPC pathPersistency behaviour.
        """
        random.seed(self.seed)
        if self.frames <= 0 or self.n_pairs <= 0:
            return []

        # Build per-pair boolean timelines first (either sync or independent)
        def build_boolean_tl():
            up_count = int(round(self.frames * self.path_life))
            up_count = max(0, min(self.frames, up_count))
            down_count = self.frames - up_count
            # simple blocky generator using stability to choose run lengths
            tl = [False] * self.frames
            if up_count == 0:
                return tl
            if down_count == 0:
                return [True] * self.frames

            if self.mode == "sync":
                # generate a single boolean timeline and replicate
                runs = []
                remaining = self.frames
                up_remaining = up_count
                is_up = False
                while remaining > 0:
                    # expected run length
                    avg = max(1, int(round(self.stability * self.frames)))
                    run = min(
                        remaining, max(1, int(random.expovariate(1.0 / max(1, avg))))
                    )
                    # but bias to meet up_count roughly
                    runs.append((is_up, run))
                    if is_up:
                        up_remaining = max(0, up_remaining - run)
                    remaining -= run
                    is_up = not is_up
                # build tl from runs
                pos = 0
                for state, run in runs:
                    for i in range(run):
                        if pos < self.frames:
                            tl[pos] = state
                        pos += 1
                # if up_count mismatch, adjust by flipping some frames
                # keep it simple: ensure exact up_count by promoting/demoting frames at end
                cur_up = sum(1 for x in tl if x)
                i = 0
                while cur_up < up_count and i < self.frames:
                    if not tl[i]:
                        tl[i] = True
                        cur_up += 1
                    i += 1
                i = self.frames - 1
                while cur_up > up_count and i >= 0:
                    if tl[i]:
                        tl[i] = False
                        cur_up -= 1
                    i -= 1
                return tl
            else:
                # independent per pair timelines
                # build a timeline with up_count True positions randomly placed with run-length bias
                tl2 = [False] * self.frames
                up_positions = set(random.sample(range(self.frames), up_count))
                for p in up_positions:
                    tl2[p] = True
                return tl2

        # Generate boolean timelines per-pair
        if self.mode == "sync":
            bool_tl = build_boolean_tl()
            per_pair_bool = [list(bool_tl) for _ in range(self.n_pairs)]
        else:
            per_pair_bool = [build_boolean_tl() for _ in range(self.n_pairs)]

        # Now convert per-pair boolean timelines into id-labelled timelines
        # Maintain a counter per pair to emit fresh ids
        per_pair_next_id = [0] * self.n_pairs
        per_pair_last_id = [None] * self.n_pairs

        timeline = []
        for frame_idx in range(self.frames):
            frame_tuple = []
            for p in range(self.n_pairs):
                is_up = per_pair_bool[p][frame_idx]
                if not is_up:
                    frame_tuple.append(None)
                    per_pair_last_id[p] = None
                else:
                    if per_pair_last_id[p] is None:
                        # start of up-run -> new id
                        per_pair_last_id[p] = per_pair_next_id[p]
                        per_pair_next_id[p] += 1
                    else:
                        # decide whether to keep same id
                        if random.random() <= self.pathPersistency:
                            # keep same id
                            pass
                        else:
                            per_pair_last_id[p] = per_pair_next_id[p]
                            per_pair_next_id[p] += 1
                    frame_tuple.append(per_pair_last_id[p])
            timeline.append(tuple(frame_tuple))
        return timeline

    def computeStatistics(self, timeline):
        """
        Compute simple per-pair statistics from a generated timeline (list of tuples).
        Returns dict with per_pair {'up_count','uptime_ratio','up_blocks','changes'} and
        global counts for distinct status tuples.
        """
        if not timeline:
            return {}

        frames = len(timeline)
        # collect per-pair lists
        per_pair = [[] for _ in range(self.n_pairs)]
        for t in timeline:
            for i, val in enumerate(t):
                per_pair[i].append(bool(val))

        stats = {"frames": frames, "pairs": []}
        for i, seq in enumerate(per_pair):
            # up blocks
            up_blocks = 0
            cur = False
            for v in seq:
                if v and not cur:
                    up_blocks += 1
                cur = v
            changes = sum(1 for j in range(1, frames) if seq[j] != seq[j - 1])
            up_count = sum(1 for v in seq if v)
            stats["pairs"].append(
                {
                    "pair_index": i,
                    "up_count": up_count,
                    "uptime_ratio": up_count / frames,
                    "up_blocks": up_blocks,
                    "changes": changes,
                }
            )

        # global status tuple counts
        if self.n_pairs == 2:
            # optimize for 2 pairs: just count the 4 possible tuples
            stats["status_tuples"] = {
                (False, False): 0,
                (False, True): 0,
                (True, False): 0,
                (True, True): 0,
            }
            for t in timeline:
                stats["status_tuples"][tuple(t)] += 1
        else:
            # general case: count all unique tuples
            stats["status_tuples"] = {}
            for t in timeline:
                if tuple(t) not in stats["status_tuples"]:
                    stats["status_tuples"][tuple(t)] = 0
                stats["status_tuples"][tuple(t)] += 1

        return stats
