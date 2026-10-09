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
        """Generate an exact-quota SPC timeline and persistent path labels."""
        frames = self.frames
        if frames <= 0:
            self.last_timeline = []
            self.last_path_ids = []
            return {"timeline": [], "path_ids": []}

        if not 0.0 <= self.path_life <= 1.0:
            raise ValueError("path_life must be in [0, 1]")
        if not 0.0 <= self.stability <= 1.0:
            raise ValueError("stability must be in [0, 1]")

        rng = random.Random(self.seed)
        up_count = max(0, min(frames, int(round(frames * self.path_life))))
        down_count = frames - up_count

        if self.mode == "random":
            timeline = [True] * up_count + [False] * down_count
            rng.shuffle(timeline)
        elif up_count == 0:
            timeline = [False] * frames
        elif down_count == 0:
            timeline = [True] * frames
        else:
            up_runs = int(round(1 + (1.0 - float(self.stability)) * (up_count - 1)))
            up_runs = max(1, min(up_count, up_runs))
            if up_runs > down_count + 1:
                raise ValueError(
                    f"Infeasible exact timeline: up_count={up_count}, "
                    f"up_runs={up_runs}, down_count={down_count}"
                )

            min_down_runs = max(1, up_runs - 1)
            max_down_runs = min(down_count, up_runs + 1)
            down_runs = rng.randint(min_down_runs, max_down_runs)

            def composition(total: int, parts: int) -> List[int]:
                if parts == 1:
                    return [total]
                cuts = sorted(rng.sample(range(1, total), parts - 1))
                points = [0, *cuts, total]
                return [points[i + 1] - points[i] for i in range(parts)]

            up_sizes = composition(up_count, up_runs)
            down_sizes = composition(down_count, down_runs)
            if down_runs == up_runs - 1:
                state_up = True
            elif down_runs == up_runs + 1:
                state_up = False
            else:
                state_up = rng.choice((True, False))

            timeline = []
            up_index = down_index = 0
            while up_index < up_runs or down_index < down_runs:
                if state_up and up_index < up_runs:
                    timeline.extend([True] * up_sizes[up_index])
                    up_index += 1
                elif not state_up and down_index < down_runs:
                    timeline.extend([False] * down_sizes[down_index])
                    down_index += 1
                state_up = not state_up

        # Keep path identity randomness on a separate seeded stream so it cannot
        # change the Boolean timeline produced for this seed.
        label_rng = random.Random((int(self.seed) if self.seed is not None else 0) ^ 0x5A17)
        path_ids = [None] * len(timeline)
        next_pid = 0
        last_pid = None
        for index, is_up in enumerate(timeline):
            if not is_up:
                last_pid = None
                continue
            if last_pid is None or label_rng.random() >= self.pathPersistency:
                last_pid = next_pid
                next_pid += 1
            path_ids[index] = last_pid

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
        rng = random.Random(self.seed)
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
                        remaining, max(1, int(rng.expovariate(1.0 / max(1, avg))))
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
                up_positions = set(rng.sample(range(self.frames), up_count))
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
                        if rng.random() <= self.pathPersistency:
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
