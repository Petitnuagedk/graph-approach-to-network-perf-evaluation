"""Isolated v2 S--R timeline generator for Phase 7 offline validation.

This module intentionally does not import or modify YaDyGaGa. Its stream
semantics and serialized output are versioned independently from legacy data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


GENERATOR_VERSION = "j2-sr-timeline-v2.1"
FRAME_COUNT = 60
TARGET_MEAN_UP_RUN_FRAMES = 5
STABILITY_VALUES = (0.0, 0.2, 0.4, 0.6, 0.8)
TOPOLOGIES = ("line", "two-lines", "ladder")

Matrix = tuple[tuple[int, ...], ...]


def _stable_seed(*parts: object) -> int:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _route(matrix: Matrix, source: int, destination: int) -> tuple[int, ...] | None:
    pending = deque([source])
    parent = {source: -1}
    while pending:
        node = pending.popleft()
        if node == destination:
            path = [destination]
            while path[-1] != source:
                path.append(parent[path[-1]])
            return tuple(reversed(path))
        for neighbor, edge in enumerate(matrix[node]):
            if edge and neighbor not in parent:
                parent[neighbor] = node
                pending.append(neighbor)
    return None


def read_trace(path: Path) -> tuple[list[str], list[Matrix]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    header_index = next(i for i, row in enumerate(rows) if row and any(v.strip() for v in row))
    labels = [value.strip() for value in rows[header_index]]
    matrices: list[Matrix] = []
    current: list[tuple[int, ...]] = []
    for row in rows[header_index + 1 :]:
        if not row or not any(value.strip() for value in row):
            if current:
                matrices.append(tuple(current))
                current = []
            continue
        matrix_row = tuple(int(value) for value in row)
        if len(matrix_row) != len(labels):
            raise ValueError(f"{path}: matrix row has {len(matrix_row)} entries; expected {len(labels)}")
        current.append(matrix_row)
    if current:
        matrices.append(tuple(current))
    if not matrices:
        raise ValueError(f"{path}: no frame matrices")
    if any(len(matrix) != len(labels) for matrix in matrices):
        raise ValueError(f"{path}: at least one matrix has the wrong row count")
    if any(matrix[i][j] != matrix[j][i] for matrix in matrices for i in range(len(labels))
           for j in range(len(labels))):
        raise ValueError(f"{path}: adjacency matrix is not symmetric")
    return labels, matrices


def serialize_trace(labels: Sequence[str], frames: Sequence[Matrix]) -> bytes:
    lines = [",".join(labels)]
    for index, matrix in enumerate(frames):
        lines.extend(",".join(str(value) for value in row) for row in matrix)
        if index + 1 < len(frames):
            lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


def quota_for(path_life: float, frames: int = FRAME_COUNT) -> int:
    if not 0.0 <= path_life <= 1.0:
        raise ValueError("path_life must lie in [0, 1]")
    return math.floor(frames * path_life + 0.5)


def run_count_for(up_count: int, frame_count: int = FRAME_COUNT,
                  target_mean: int = TARGET_MEAN_UP_RUN_FRAMES) -> int:
    down_count = frame_count - up_count
    if up_count == 0:
        return 0
    if up_count == frame_count:
        return 1
    return min(math.ceil(up_count / target_mean), down_count + 1)


def _cv(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values)) / mean


def _run_composition(up_count: int, run_count: int, stability: float) -> tuple[list[int], float, float]:
    if not 0.0 <= stability <= 1.0:
        raise ValueError("stability must lie in [0, 1]")
    if run_count == 0:
        return [], 0.0, 0.0
    balanced = [up_count // run_count] * run_count
    for index in range(up_count % run_count):
        balanced[index] += 1
    balanced.sort()
    extreme = [1] * run_count
    extreme[-1] = up_count - run_count + 1
    extreme.sort()

    attainable = [balanced.copy()]
    current = balanced.copy()
    while current != extreme:
        smallest_value = min(value for value in current if value > 1)
        largest_value = max(current)
        smallest = next(index for index, value in enumerate(current)
                        if value == smallest_value)
        largest = next(index for index in range(run_count - 1, -1, -1)
                       if current[index] == largest_value and index != smallest)
        current[smallest] -= 1
        current[largest] += 1
        current.sort()
        attainable.append(current.copy())

    cvs = [_cv(comp) for comp in attainable]
    target = cvs[-1] * (1.0 - stability) + cvs[0] * stability
    chosen = min(range(len(cvs)), key=lambda index: (abs(cvs[index] - target), index))
    return attainable[chosen].copy(), cvs[chosen], target


def _endpoint_pattern(up_count: int, down_count: int, run_count: int,
                      frame_count: int, seed: int) -> tuple[bool, bool]:
    if run_count == 0:
        return False, False
    feasible: list[tuple[bool, bool]] = []
    for first_up in (False, True):
        for last_up in (False, True):
            minimum_down = run_count - 1 + int(not first_up) + int(not last_up)
            if minimum_down > down_count:
                continue
            if run_count == 1 and first_up and last_up and up_count != frame_count:
                continue
            feasible.append((first_up, last_up))
    if not feasible:
        raise ValueError("no endpoint policy is feasible for this U/D/K tuple")
    return random.Random(seed).choice(feasible)


def generate_timeline(path_life: float, stability: float, topology: str,
                      realization_id: int, master_seed: int = 42,
                      frame_count: int = FRAME_COUNT,
                      endpoint_pattern: tuple[bool, bool] | None = None
                      ) -> tuple[list[bool], dict[str, object]]:
    up_count = quota_for(path_life, frame_count)
    down_count = frame_count - up_count
    run_count = run_count_for(up_count, frame_count)
    timeline_seed = _stable_seed(GENERATOR_VERSION, master_seed, topology, frame_count,
                                 f"{path_life:.6f}", f"{stability:.6f}",
                                 realization_id, "timeline")
    endpoint_seed = _stable_seed(GENERATOR_VERSION, master_seed, topology, frame_count,
                                 f"{path_life:.6f}", "boundary")
    endpoints = endpoint_pattern or _endpoint_pattern(
        up_count, down_count, run_count, frame_count, endpoint_seed)
    composition, measured_cv, target_cv = _run_composition(up_count, run_count, stability)
    rng = random.Random(timeline_seed)
    rng.shuffle(composition)

    if run_count == 0:
        timeline = [False] * frame_count
    elif up_count == frame_count:
        timeline = [True] * frame_count
    else:
        first_up, last_up = endpoints
        gaps = [0] * (run_count + 1)
        gaps[0] = int(not first_up)
        gaps[-1] = int(not last_up)
        for index in range(1, run_count):
            gaps[index] = 1
        excess = down_count - sum(gaps)
        if excess < 0:
            raise ValueError("selected endpoint pattern is infeasible")
        for _ in range(excess):
            gaps[rng.randrange(len(gaps))] += 1
        timeline = []
        for index, run_length in enumerate(composition):
            timeline.extend([False] * gaps[index])
            timeline.extend([True] * run_length)
        timeline.extend([False] * gaps[-1])
        if len(timeline) != frame_count:
            raise AssertionError("timeline assembly did not preserve frame count")

    metadata: dict[str, object] = {
        "generator_version": GENERATOR_VERSION,
        "master_seed": master_seed,
        "topology": topology,
        "frame_count": frame_count,
        "fps": 1.0,
        "path_life_requested": path_life,
        "stability": stability,
        "realization_id": realization_id,
        "timeline_seed": str(timeline_seed),
        "endpoint_seed": str(endpoint_seed),
        "endpoint_pattern_first_last_up": [endpoints[0], endpoints[1]],
        "boundary_policy": "free-linear-no-wrap",
        "up_quota": up_count,
        "down_quota": down_count,
        "up_run_count": run_count,
        "up_run_lengths_frames": _up_runs(timeline),
        "mean_up_run_frames": up_count / run_count if run_count else 0.0,
        "up_run_cv": _cv(_up_runs(timeline)),
        "target_up_run_cv": target_cv,
        "measured_up_frames": sum(timeline),
        "measured_uptime": sum(timeline) / frame_count,
        "transition_count": sum(a != b for a, b in zip(timeline, timeline[1:])),
        "timeline_sha256": _sha256(bytes(timeline)),
    }
    return timeline, metadata


def _up_runs(timeline: Sequence[bool]) -> list[int]:
    runs: list[int] = []
    current = 0
    for state in timeline:
        if state:
            current += 1
        elif current:
            runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


@dataclass
class GraphPools:
    labels: list[str]
    up_by_route: dict[tuple[int, ...], list[Matrix]]
    down: list[Matrix]
    source_hashes: dict[str, str]

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> "GraphPools":
        unique_paths = sorted(set(paths))
        if not unique_paths:
            raise ValueError("no trace paths supplied for graph pools")
        labels: list[str] | None = None
        up_sets: dict[tuple[int, ...], set[Matrix]] = defaultdict(set)
        down_set: set[Matrix] = set()
        source_hashes: dict[str, str] = {}
        for path in unique_paths:
            raw = path.read_bytes()
            source_hashes[str(path)] = _sha256(raw)
            file_labels, matrices = read_trace(path)
            if labels is None:
                labels = file_labels
            elif labels != file_labels:
                raise ValueError(f"node-label order differs in {path}")
            source = labels.index("S")
            destination = labels.index("R")
            for matrix in matrices:
                route = _route(matrix, source, destination)
                if route is None:
                    down_set.add(matrix)
                else:
                    up_sets[route].add(matrix)
        if not down_set or not up_sets:
            raise ValueError("topology pools must contain both connected and disconnected matrices")
        return cls(labels or [], {key: sorted(value) for key, value in sorted(up_sets.items())},
                   sorted(down_set), source_hashes)


def assemble_trace(timeline: Sequence[bool], pools: GraphPools, topology: str,
                   parameter_tuple: tuple[float, float, float], realization_id: int,
                   master_seed: int = 42) -> tuple[list[Matrix], list[tuple[int, ...] | None], dict[str, object]]:
    path_life, stability, path_persistency = parameter_tuple
    graph_seed = _stable_seed(GENERATOR_VERSION, master_seed, topology, realization_id, "graph_pool")
    identity_seed = _stable_seed(GENERATOR_VERSION, master_seed, topology,
                                 f"{path_life:.6f}", f"{stability:.6f}",
                                 f"{path_persistency:.6f}", realization_id, "path_identity")
    graph_rng = random.Random(graph_seed)
    identity_rng = random.Random(identity_seed)
    route_keys = sorted(pools.up_by_route)
    frames: list[Matrix] = []
    path_ids: list[tuple[int, ...] | None] = []
    previous: tuple[int, ...] | None = None
    for is_up in timeline:
        if not is_up:
            frames.append(graph_rng.choice(pools.down))
            path_ids.append(None)
            previous = None
            continue
        if previous is not None and identity_rng.random() < path_persistency:
            route = previous
        else:
            route = graph_rng.choice(route_keys)
        frames.append(graph_rng.choice(pools.up_by_route[route]))
        path_ids.append(route)
        previous = route
    metadata = {
        "graph_pool_seed": str(graph_seed),
        "path_identity_seed": str(identity_seed),
        "source_trace_sha256": dict(sorted(pools.source_hashes.items())),
        "path_identity_retention_requested": path_persistency,
        "path_identity_retention_observed": (
            sum(a == b for a, b in zip(path_ids, path_ids[1:]) if a is not None and b is not None)
            / sum(a is not None and b is not None for a, b in zip(path_ids, path_ids[1:]))
            if any(a is not None and b is not None for a, b in zip(path_ids, path_ids[1:])) else None
        ),
    }
    return frames, path_ids, metadata


def generate_trace(pools: GraphPools, topology: str, parameter_tuple: tuple[float, float, float],
                   realization_id: int, master_seed: int = 42,
                   endpoint_pattern: tuple[bool, bool] | None = None
                   ) -> tuple[bytes, dict[str, object]]:
    path_life, stability, path_persistency = parameter_tuple
    timeline, timeline_metadata = generate_timeline(
        path_life, stability, topology, realization_id, master_seed,
        endpoint_pattern=endpoint_pattern)
    frames, _, assembly_metadata = assemble_trace(
        timeline, pools, topology, parameter_tuple, realization_id, master_seed)
    trace_bytes = serialize_trace(pools.labels, frames)
    metadata = {
        **timeline_metadata,
        "parameter_tuple": {
            "path_life": path_life,
            "stability": stability,
            "pathPersistency": path_persistency,
        },
        **assembly_metadata,
        "frames_sha256": _sha256(trace_bytes),
    }
    return trace_bytes, metadata


def dump_metadata(metadata: dict[str, object]) -> bytes:
    return (json.dumps(metadata, sort_keys=True, indent=2, separators=(",", ": ")) + "\n").encode("utf-8")
