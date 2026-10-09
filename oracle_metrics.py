"""Pure-Python reference implementation for trace-derived S-to-R oracle metrics."""

from __future__ import annotations

from collections import deque
from math import nan
from typing import Mapping, Sequence


def _shortest_path(matrix: Sequence[Sequence[int]], source: int, destination: int):
    count = len(matrix)
    parent = [-1] * count
    seen = {source}
    pending = deque([source])
    while pending:
        node = pending.popleft()
        if node == destination:
            break
        for neighbor, up in enumerate(matrix[node]):
            if up and neighbor not in seen:
                seen.add(neighbor)
                parent[neighbor] = node
                pending.append(neighbor)
    if destination not in seen:
        return None
    path = [destination]
    while path[-1] != source:
        path.append(parent[path[-1]])
    return tuple(reversed(path))


def _has_alternative_path(matrix: Sequence[Sequence[int]], path: tuple[int, ...], source: int, destination: int):
    for u, v in zip(path, path[1:]):
        seen = {source}
        pending = deque([source])
        while pending:
            node = pending.popleft()
            for neighbor, up in enumerate(matrix[node]):
                if not up or (node == u and neighbor == v) or (node == v and neighbor == u):
                    continue
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        if destination in seen:
            return True
    return False


def _runs(states: Sequence[bool], state: bool, frame_duration_s: float):
    result = []
    length = 0
    for value in states:
        if value == state:
            length += 1
        elif length:
            result.append(length * frame_duration_s)
            length = 0
    if length:
        result.append(length * frame_duration_s)
    return result


def _quantile(values: Sequence[float], probability: float):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def compute_oracle_metrics(frames: Sequence[Sequence[Sequence[int]]], source: int,
                           destination: int, frame_duration_s: float = 1.0) -> dict:
    """Compute connectivity, route identity, run lengths and outages from 0/1 frames."""
    paths = [_shortest_path(frame, source, destination) for frame in frames]
    connected = [path is not None for path in paths]
    up_runs = _runs(connected, True, frame_duration_s)
    outages = _runs(connected, False, frame_duration_s)
    transitions = sum(left != right for left, right in zip(connected, connected[1:]))
    alternatives = any(
        path is not None and _has_alternative_path(frame, path, source, destination)
        for frame, path in zip(frames, paths)
    )
    comparisons = [(left, right) for left, right in zip(paths, paths[1:])
                   if left is not None and right is not None]
    retention = (sum(left == right for left, right in comparisons) / len(comparisons)
                 if alternatives and comparisons else nan)
    return {
        "uptime_ratio": sum(connected) / len(connected) if connected else nan,
        "up_runs_s": up_runs,
        "mean_up_run_s": sum(up_runs) / len(up_runs) if up_runs else nan,
        "median_up_run_s": _quantile(up_runs, 0.5) if up_runs else nan,
        "p90_up_run_s": _quantile(up_runs, 0.9) if up_runs else nan,
        "transition_count": transitions,
        "path_identity_retention": retention,
        "has_alternative_paths": alternatives,
        "outage_durations_s": outages,
        "connected": connected,
        "routes": paths,
    }


def compute_traffic_window_usable_uptime(
    frames: Sequence[Sequence[Sequence[int]]],
    source: int,
    destination: int,
    traffic_start_s: float,
    traffic_stop_s: float,
    frame_duration_s: float = 1.0,
    link_up_loss_db: float = 10.0,
    link_down_loss_db: float = 125.0,
    tx_power_dbm: float = 20.0,
    rx_sensitivity_dbm: float = -101.0,
    sparse_threshold_db: float = 150.0,
    default_loss_db: float = 1e6,
    interpolate: bool = True,
) -> dict:
    """Integrate frame-oracle and thresholded channel connectivity over traffic time.

    Frame ``i`` is applied at ``i * frame_duration_s``. When interpolation is
    enabled, per-edge path loss is linearly interpolated to frame ``i + 1``;
    sparse entries at or above ``sparse_threshold_db`` resolve to
    ``default_loss_db``, matching Trace Matrix Propagation Loss Model behavior.
    The traffic stop must not exceed the final frame timestamp because replay
    stops at that timestamp and has no later staged frame.
    """
    if not frames:
        raise ValueError("frames must not be empty")
    if frame_duration_s <= 0:
        raise ValueError("frame_duration_s must be positive")
    if traffic_stop_s <= traffic_start_s:
        raise ValueError("traffic_stop_s must be after traffic_start_s")
    if traffic_start_s < 0 or traffic_stop_s > (len(frames) - 1) * frame_duration_s:
        raise ValueError("traffic window must lie within the replay frame timestamps")
    node_count = len(frames[0])
    if not (0 <= source < node_count and 0 <= destination < node_count):
        raise ValueError("source and destination must index the frame matrices")
    if any(len(frame) != node_count or any(len(row) != node_count for row in frame)
           for frame in frames):
        raise ValueError("all frames must be square matrices with the same dimension")

    usable_loss_limit_db = tx_power_dbm - rx_sensitivity_dbm

    def committed_loss(is_up: int) -> float:
        loss = link_up_loss_db if is_up else link_down_loss_db
        return loss if loss < sparse_threshold_db else default_loss_db

    def is_connected(time_s: float, usable: bool) -> bool:
        frame_position = time_s / frame_duration_s
        frame_index = min(int(frame_position), len(frames) - 1)
        alpha = frame_position - frame_index
        next_index = frame_index + 1
        can_interpolate = interpolate and next_index < len(frames)
        adjacency = [[] for _ in range(node_count)]
        for left in range(node_count):
            for right in range(left + 1, node_count):
                current = frames[frame_index][left][right]
                if usable:
                    loss = committed_loss(current)
                    if can_interpolate:
                        next_loss = committed_loss(frames[next_index][left][right])
                        loss += alpha * (next_loss - loss)
                    if loss > usable_loss_limit_db:
                        continue
                elif not current:
                    continue
                adjacency[left].append(right)
                adjacency[right].append(left)
        seen = {source}
        pending = deque([source])
        while pending:
            node = pending.popleft()
            if node == destination:
                return True
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    pending.append(neighbor)
        return False

    breakpoints = {traffic_start_s, traffic_stop_s}
    for index in range(1, len(frames) - 1):
        boundary = index * frame_duration_s
        if traffic_start_s < boundary < traffic_stop_s:
            breakpoints.add(boundary)
    if interpolate:
        for index, (current_frame, next_frame) in enumerate(zip(frames, frames[1:])):
            interval_start = index * frame_duration_s
            for left in range(node_count):
                for right in range(left + 1, node_count):
                    current_loss = committed_loss(current_frame[left][right])
                    next_loss = committed_loss(next_frame[left][right])
                    if current_loss == next_loss:
                        continue
                    alpha = (usable_loss_limit_db - current_loss) / (next_loss - current_loss)
                    crossing = interval_start + alpha * frame_duration_s
                    if 0 < alpha < 1 and traffic_start_s < crossing < traffic_stop_s:
                        breakpoints.add(crossing)

    ordered = sorted(breakpoints)
    frame_connected_s = 0.0
    usable_connected_s = 0.0
    frame_up_intervals = []
    usable_up_intervals = []
    for start, stop in zip(ordered, ordered[1:]):
        midpoint = (start + stop) / 2
        duration = stop - start
        if is_connected(midpoint, usable=False):
            frame_connected_s += duration
            if frame_up_intervals and abs(frame_up_intervals[-1][1] - start) < 1e-10:
                frame_up_intervals[-1] = (frame_up_intervals[-1][0], stop)
            else:
                frame_up_intervals.append((start, stop))
        if is_connected(midpoint, usable=True):
            usable_connected_s += duration
            if usable_up_intervals and abs(usable_up_intervals[-1][1] - start) < 1e-10:
                usable_up_intervals[-1] = (usable_up_intervals[-1][0], stop)
            else:
                usable_up_intervals.append((start, stop))
    window_s = traffic_stop_s - traffic_start_s
    return {
        "traffic_window_s": window_s,
        "frame_connected_s": frame_connected_s,
        "usable_connected_s": usable_connected_s,
        "frame_uptime_ratio": frame_connected_s / window_s,
        "usable_uptime_ratio": usable_connected_s / window_s,
        "usable_loss_limit_db": usable_loss_limit_db,
        "frame_up_intervals_s": frame_up_intervals,
        "usable_up_intervals_s": usable_up_intervals,
    }


def is_time_connected(time_s: float, intervals: Sequence[tuple[float, float]]) -> bool:
    """Return whether ``time_s`` lies in a half-open connected interval [start, stop)."""
    return any(start <= time_s < stop for start, stop in intervals)


def compute_deadline_pdr(
    tx_times_by_sequence: Mapping[int, float],
    rx_times_by_sequence: Mapping[int, float],
    deadline_s: float,
) -> dict:
    """Compute unique-sequence PDR delivered no later than ``deadline_s`` after Tx.

    The mappings must contain one application Tx time and at most one Rx time
    per sequence. Receives for unoffered sequence numbers are ignored.
    """
    if deadline_s < 0:
        raise ValueError("deadline_s must be nonnegative")
    delays = {
        sequence: rx_time - tx_times_by_sequence[sequence]
        for sequence, rx_time in rx_times_by_sequence.items()
        if sequence in tx_times_by_sequence
        and rx_time >= tx_times_by_sequence[sequence]
    }
    deadline_delivered = sum(delay <= deadline_s for delay in delays.values())
    offered = len(tx_times_by_sequence)
    return {
        "offered_packets": offered,
        "unique_received_packets": len(delays),
        "deadline_delivered_packets": deadline_delivered,
        "deadline_miss_packets": offered - deadline_delivered,
        "deadline_s": deadline_s,
        "deadline_pdr": deadline_delivered / offered if offered else nan,
    }
