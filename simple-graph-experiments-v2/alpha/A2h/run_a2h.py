#!/usr/bin/env python3
"""Registered A2h null, memory-chain sweep, and one-cell A2g-2 completion."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ALPHA = ROOT / "alpha"
A1 = ALPHA / "A1" / "results"
EDGE_DIR = A1 / "edge_lists"
COVARIATES = A1 / "graph_covariates.csv"
A2G4 = ALPHA / "A2g" / "A2g-4"
A2G3_OPS = ALPHA / "A2g" / "A2g-3" / "operations"
A2F3 = ALPHA / "A2f" / "A2f-3" / "results"
DONOR = ALPHA / "A2" / "A2d" / "item1" / "source"
OVERLAY = ALPHA / "A2f" / "A2f-2" / "source"
A2G3_RUNNER = ALPHA / "A2g" / "run_a2g3.py"
A2G2_RUNNER = ALPHA / "A2g" / "run_a2g2.py"
A2G2_PREREG = ALPHA / "A2g" / "a2g2_prereg.md"
PREREG = HERE / "prereg.md"
LIMITATIONS = ALPHA / "LIMITATIONS.md"
OUT1 = HERE / "A2h-1"
OUT2 = HERE / "A2h-2"
FPS = 1
FRAMES = 120
LIVES = (0.3, 0.5, 0.7, 0.9)
M_UP = (6, 12, 24)
PARAMS = ((0.5, 2.0), (0.5, 8.0), (0.8, 2.0), (0.8, 8.0))
SEEDS = (42, 43, 44)
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
NS = (92, 162)
TIMEOUT = 60


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def boolval(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"true", "1", "yes"}


def graph_records() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in read_csv(COVARIATES):
        n = int(row["N"])
        if int(row["realization"]) == 1 and n in NS:
            out.append({
                "family": row["family"], "graph_id": row["graph_id"], "N": n,
                "source": int(row["probe_S"]), "destination": int(row["probe_R"]),
                "probe_hops": int(row["probe_hops"]),
                "edge_file": EDGE_DIR / f"{row['graph_id']}.csv",
            })
    if len(out) != 10:
        raise RuntimeError(f"expected 10 A1 graphs, got {len(out)}")
    return sorted(out, key=lambda r: (r["family"], r["N"]))


def load_graph(path: Path, n: int) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(range(n))
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g.add_edge(int(row["u"]), int(row["v"]))
    return g


def edge_key(u: Any, v: Any) -> tuple[int, int]:
    return (int(u), int(v)) if int(u) < int(v) else (int(v), int(u))


def canonical_shortest_path(graph: nx.Graph, source: int, destination: int) -> list[int]:
    dist_s = nx.single_source_shortest_path_length(graph, source)
    dist_r = nx.single_source_shortest_path_length(graph, destination)
    length = dist_s[destination]
    path = [source]
    current = source
    while current != destination:
        choices = [v for v in graph.neighbors(current)
                   if dist_s.get(v) == dist_s[current] + 1
                   and dist_s[v] + dist_r.get(v, math.inf) == length]
        current = min(choices, key=str)
        path.append(current)
    return path


def eligible_edges(graph: nx.Graph, source: int, destination: int) -> list[tuple[int, int]]:
    path = canonical_shortest_path(graph, source, destination)
    path_edges = {edge_key(a, b) for a, b in zip(path, path[1:])}
    return sorted(edge_key(a, b) for a, b in graph.edges()
                  if source not in (a, b) and destination not in (a, b)
                  and edge_key(a, b) not in path_edges)


def conditional_d(matrix: np.ndarray, mask: np.ndarray) -> float:
    if matrix.shape[1] != mask.size or mask.sum() == 0 or mask.sum() == mask.size:
        raise ValueError("invalid frame count or empty conditional class")
    m = mask.astype(bool)
    up = matrix[:, m].mean(axis=1)
    down = matrix[:, ~m].mean(axis=1)
    return float(np.abs(up - down).mean())


def trace_matrix_and_mask(trace: dict[str, str], eligible: list[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    trace_id, stage = trace["trace_id"], trace["source_stage"]
    if stage == "A2f-3":
        trace_dir = A2F3 / trace_id
        frame_path, edge_path = trace_dir / "frames.csv", trace_dir / "edges.csv"
        with frame_path.open(newline="", encoding="utf-8") as f:
            frame_rows = list(csv.DictReader(f))
        mask = np.array([boolval(r["timeline_up"]) for r in frame_rows], dtype=bool)
        states = np.zeros((len(eligible), len(mask)), dtype=np.uint8)
        eindex = {e: i for i, e in enumerate(eligible)}
        with edge_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                e = edge_key(row["u"], row["v"])
                if e in eindex:
                    states[eindex[e], int(row["frame"])] = 1
    elif stage == "A2g-3":
        trace_dir = A2G3_OPS / trace_id
        edge_path = trace_dir / "edge_states.csv.gz"
        states = np.zeros((len(eligible), FRAMES), dtype=np.uint8)
        mask_values: list[bool | None] = [None] * FRAMES
        eindex = {e: i for i, e in enumerate(eligible)}
        with gzip.open(edge_path, "rt", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                frame = int(row["frame"])
                bit = boolval(row["timeline_up"])
                if mask_values[frame] is not None and mask_values[frame] != bit:
                    raise RuntimeError(f"inconsistent repeated timeline mask in {trace_id}")
                mask_values[frame] = bit
                e = edge_key(row["u"], row["v"])
                if e in eindex:
                    states[eindex[e], frame] = int(boolval(row["projected_up"]))
        if any(v is None for v in mask_values):
            raise RuntimeError(f"missing frames in {trace_id}")
        mask = np.array(mask_values, dtype=bool)
    else:
        raise ValueError(stage)
    if states.shape != (len(eligible), FRAMES) or mask.size != FRAMES:
        raise RuntimeError(f"unexpected shape for {trace_id}: {states.shape}, {mask.size}")
    return states, mask


def run_distortion() -> None:
    OUT1.mkdir(parents=True, exist_ok=True)
    trace_rows = read_csv(A2G4 / "per_trace_conditioning.csv")
    edge_rows = read_csv(A2G4 / "per_edge_conditioning.csv")
    if len(trace_rows) != 140:
        raise RuntimeError(f"expected 140 traces, got {len(trace_rows)}")
    edges_by_trace: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in edge_rows:
        edges_by_trace[row["trace_id"]].append(edge_key(row["u"], row["v"]))
    out_rows: list[dict[str, Any]] = []
    null_rows: list[dict[str, Any]] = []
    for trace in trace_rows:
        trace_id = trace["trace_id"]
        eligible = sorted(set(edges_by_trace[trace_id]))
        config_dir = OUT1 / "configs" / trace_id
        config_dir.mkdir(parents=True, exist_ok=True)
        paths = [A2G4 / "per_trace_conditioning.csv", A2G4 / "per_edge_conditioning.csv"]
        if trace["source_stage"] == "A2f-3":
            paths += [A2F3 / trace_id / "frames.csv", A2F3 / trace_id / "edges.csv"]
        else:
            paths += [A2G3_OPS / trace_id / "edge_states.csv.gz", A2G3_OPS / trace_id / "config.json"]
        cfg = {
            "stage": "A2h-1", "preregistration_sha256": sha256(PREREG),
            "trace_id": trace_id, "source_stage": trace["source_stage"],
            "family": trace["family"], "graph_id": trace["graph_id"], "life": float(trace["life"]),
            "pi": float(trace["pi"]), "L": float(trace["L"]), "seed": int(trace["seed"]),
            "eligible_edge_count": len(eligible), "frames": FRAMES, "circular_shifts": list(range(1, FRAMES)),
            "input_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in paths},
        }
        write_json(config_dir / "config.json", cfg)
        matrix, mask = trace_matrix_and_mask(trace, eligible)
        d_obs = conditional_d(matrix, mask)
        previous = float(trace["mean_absolute_conditional_difference"])
        if not math.isclose(d_obs, previous, rel_tol=0, abs_tol=1e-12):
            raise RuntimeError(f"A2g-4 D recomputation mismatch {trace_id}: {d_obs} vs {previous}")
        null = []
        for shift in range(1, FRAMES):
            d = conditional_d(matrix, np.roll(mask, shift))
            null.append(d)
            null_rows.append({"trace_id": trace_id, "source_stage": trace["source_stage"], "family": trace["family"],
                              "life": trace["life"], "shift": shift, "D_null": d})
        null_sorted = sorted(null)
        null_mean = statistics.mean(null)
        q95 = null_sorted[math.ceil(0.95 * len(null)) - 1]
        exceedances = sum(v >= d_obs for v in null)
        p = (1 + exceedances) / 120
        out_rows.append({
            "source_stage": trace["source_stage"], "trace_id": trace_id, "family": trace["family"],
            "graph_id": trace["graph_id"], "life": trace["life"], "pi": trace["pi"], "L": trace["L"],
            "seed": trace["seed"], "eligible_background_edges": len(eligible), "n_up": int(mask.sum()),
            "n_down": int(FRAMES - mask.sum()), "D_obs_recomputed": d_obs, "earlier_D_trace": previous,
            "null_mean": null_mean, "null_q95_nearest_rank": q95, "excess": d_obs - null_mean,
            "null_exceedances_ge_obs": exceedances, "empirical_one_sided_p": p,
            "p_lt_0_05": p < 0.05, "null_shifts": len(null),
        })
    cell_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in out_rows:
        cell_groups[(row["source_stage"], row["family"], str(row["life"]))].append(row)
    cell_rows = []
    for (source, family, life), group in sorted(cell_groups.items()):
        hits = sum(bool(r["p_lt_0_05"]) for r in group)
        mean_excess = statistics.mean(float(r["excess"]) for r in group)
        needed = math.ceil(2 * len(group) / 3)
        real = mean_excess > 0.05 and hits >= needed
        cell_rows.append({
            "source_stage": source, "family": family, "life": life, "n_traces": len(group),
            "mean_D_obs": statistics.mean(float(r["D_obs_recomputed"]) for r in group),
            "mean_null": statistics.mean(float(r["null_mean"]) for r in group),
            "mean_excess": mean_excess, "traces_p_lt_0_05": hits,
            "fraction_p_lt_0_05": hits / len(group), "required_p_hits": needed,
            "real_conditioning": real, "classification": "real_conditioning" if real else "not_resolved_above_null",
        })
    write_csv(OUT1 / "per_trace_null.csv", out_rows)
    write_csv(OUT1 / "null_shifts.csv", null_rows)
    write_csv(OUT1 / "source_family_life_summary.csv", cell_rows)
    write_json(OUT1 / "summary.json", {
        "stage": "A2h-1", "traces": len(out_rows), "null_values": len(null_rows),
        "cells": len(cell_rows), "all_D_recomputed_match_previous": True,
        "classification_rule": "mean excess >0.05 and at least ceil(2n/3) traces with empirical p<0.05",
        "real_conditioning_cells": sum(bool(r["real_conditioning"]) for r in cell_rows),
        "source_consequence": {
            source: ("Background traffic should be treated as S-R-state-conditioned in the flagged family/life cells; no causal mechanism is identified."
                    if any(r["source_stage"] == source and r["real_conditioning"] for r in cell_rows)
                    else "This test did not resolve conditioning above the circular-shift null; it does not establish conditional invariance." )
            for source in ("A2f-3", "A2g-3")
        },
    })
    print(json.dumps({"traces": len(out_rows), "null_values": len(null_rows), "cells": len(cell_rows),
                      "real_cells": sum(bool(r["real_conditioning"]) for r in cell_rows)}, indent=2))


def all_up_runs(values: list[bool]) -> list[int]:
    runs: list[int] = []
    active = 0
    for value in values:
        if value:
            active += 1
        elif active:
            runs.append(active)
            active = 0
    return runs


def chain_sources() -> dict[str, Path]:
    return {
        "frame_generator": DONOR / "yadygaga" / "frameGenerator.py",
        "timeline_generator": DONOR / "yadygaga" / "timelineBlockGenerator.py",
        "dyna_graph": DONOR / "yadygaga" / "dynaGraph.py",
        "uk_overlay_timeline": OVERLAY / "yadygaga" / "timelineBlockGenerator.py",
        "uk_overlay_init": OVERLAY / "yadygaga" / "__init__.py",
    }


def worker_chain(config_path: Path) -> int:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    out = config_path.parent
    started = time.perf_counter()
    status_path = out / "operation_status.json"
    try:
        expected = chain_sources()
        for name, path in expected.items():
            if sha256(path) != config["source_sha256"][name]:
                raise RuntimeError(f"source hash changed: {name}")
        graph_file = ROOT / config["graph_edge_list"]
        if sha256(graph_file) != config["graph_edge_sha256"]:
            raise RuntimeError("graph edge-list hash mismatch")
        sys.path.insert(0, str(OVERLAY))
        from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
        from yadygaga.frameGenerator import FrameGenerator

        graph = load_graph(graph_file, int(config["N"]))
        s, r = int(config["source_node"]), int(config["destination_node"])
        u_requested, k_requested = int(config["U_requested"]), int(config["K_requested"])
        timeline_data = SPCTimelineBlockGenerator(
            frames=FRAMES, seed=int(config["timeline_seed"]), mode="blocks",
            pathPersistency=0.75, behavior="uk", up_count=u_requested, up_runs=k_requested,
        ).generate_blocks()
        bits = [bool(v) for v in timeline_data["timeline"]]
        k_actual = sum(bit and (i == 0 or not bits[i - 1]) for i, bit in enumerate(bits))
        if sum(bits) != u_requested or k_actual != k_requested:
            raise RuntimeError("uk schedule violated exact U/K")
        fg = FrameGenerator()
        result = fg.generateSPCFrames(
            limited_G=graph, s=s, d=r, trials=0, p_edge=float(config["pi"]),
            seed=int(config["sampler_seed"]), behavior="patched-v3", timeline=bits,
            mean_up_duration=float(config["L_frames"]),
        )
        temporal = fg.temporal_result
        raw_frames, projected_frames = temporal["raw_frames"], temporal["frames"]
        edges = sorted(edge_key(*e) for e in graph.edges())
        bg_edges = eligible_edges(graph, s, r)
        raw = {e: [bool(f.has_edge(*e)) for f in raw_frames] for e in edges}
        projected = {e: [bool(f.has_edge(*e)) for f in projected_frames] for e in edges}
        background = set(bg_edges)
        raw_pi = sum(sum(raw[e]) for e in edges) / (len(edges) * FRAMES)
        projected_pi = sum(sum(projected[e]) for e in edges) / (len(edges) * FRAMES)
        raw_up_runs = [x for e in edges for x in all_up_runs(raw[e])]
        projected_up_runs = [x for e in edges for x in all_up_runs(projected[e])]
        raw_l = statistics.mean(raw_up_runs) / FPS if raw_up_runs else math.nan
        projected_l = statistics.mean(projected_up_runs) / FPS if projected_up_runs else math.nan
        bg_raw_pi = sum(sum(raw[e]) for e in bg_edges) / (len(bg_edges) * FRAMES)
        bg_projected_pi = sum(sum(projected[e]) for e in bg_edges) / (len(bg_edges) * FRAMES)
        bg_raw_runs = [x for e in bg_edges for x in all_up_runs(raw[e])]
        bg_projected_runs = [x for e in bg_edges for x in all_up_runs(projected[e])]
        bg_raw_l = statistics.mean(bg_raw_runs) / FPS if bg_raw_runs else math.nan
        bg_projected_l = statistics.mean(bg_projected_runs) / FPS if bg_projected_runs else math.nan
        changed = sum(raw[e][i] != projected[e][i] for e in edges for i in range(FRAMES))
        projection_fraction = changed / (len(edges) * FRAMES)
        mask = [nx.has_path(frame, s, r) for frame in projected_frames]
        skeleton_edges = {frozenset(e) for e in edges}
        all_inside = all(frozenset(edge_key(*e)) in skeleton_edges for frame in (*raw_frames, *projected_frames) for e in frame.edges())
        static_hops = nx.shortest_path_length(graph, s, r)
        shortcut_frames = sum(nx.has_path(frame, s, r) and nx.shortest_path_length(frame, s, r) < static_hops
                              for frame in projected_frames)
        shortcut_fraction = shortcut_frames / FRAMES
        neighbors = [set(edge_key(*e) for e in frame.edges()) for frame in projected_frames]
        neighbor_membership_changes = sum(2 * len(neighbors[i] ^ neighbors[i - 1]) for i in range(1, FRAMES))
        denom_node_seconds = int(config["N"]) * (FRAMES - 1) / FPS
        neighbor_rate = neighbor_membership_changes / denom_node_seconds
        l_target = float(config["L_seconds"])
        pi_error = abs(projected_pi - float(config["pi"]))
        l_error = abs(projected_l - l_target) / l_target
        exact_mask = mask == bits
        exact_u = sum(mask) == u_requested
        uk_exact = sum(bits) == u_requested and k_actual == k_requested
        metrics = {
            "status": "success", "family": config["family"], "graph_id": config["graph_id"],
            "N": config["N"], "life": config["life"], "m_up_target_frames": config["m_up_target_frames"],
            "U_requested": u_requested, "D_requested": FRAMES - u_requested,
            "K_requested": k_requested, "K_realized": k_actual,
            "pi": config["pi"], "L_seconds": l_target, "L_frames": config["L_frames"],
            "seed": config["timeline_seed"], "sampler_seed": config["sampler_seed"],
            "all_edge_raw_pi": raw_pi, "all_edge_projected_pi": projected_pi,
            "all_edge_raw_completed_up_duration_s": raw_l,
            "all_edge_projected_completed_up_duration_s": projected_l,
            "background_edge_count": len(bg_edges), "background_raw_pi": bg_raw_pi,
            "background_projected_pi": bg_projected_pi,
            "background_raw_completed_up_duration_s": bg_raw_l,
            "background_projected_completed_up_duration_s": bg_projected_l,
            "projection_changed_edge_time_fraction": projection_fraction,
            "sr_mask_exact": exact_mask, "projected_up_count": sum(mask), "uk_exact_UK": uk_exact,
            "all_edges_in_skeleton": all_inside, "shortcut_fraction": shortcut_fraction,
            "shortcut_frames": shortcut_frames, "down_frame_starvation": not exact_mask or sum(mask) != u_requested,
            "projected_pi_abs_error": pi_error, "projected_duration_relative_error": l_error,
            "projection_pass": projection_fraction <= 0.05, "pi_pass": pi_error <= 0.05,
            "duration_pass": l_error <= 0.20,
            "carried_tolerances_pass": projection_fraction <= 0.05 and pi_error <= 0.05 and l_error <= 0.20,
            "operation_pass": exact_mask and exact_u and uk_exact and all_inside and shortcut_fraction == 0.0
                               and projection_fraction <= 0.05 and pi_error <= 0.05 and l_error <= 0.20,
            "neighbor_membership_changes": neighbor_membership_changes,
            "neighbor_membership_changes_per_frame": neighbor_membership_changes / (FRAMES - 1),
            "neighbor_membership_changes_per_node_second": neighbor_rate,
            "elapsed_worker_seconds": time.perf_counter() - started,
        }
        write_json(out / "trace_metrics.json", metrics)
        write_json(status_path, {"status": "success", "elapsed_worker_seconds": metrics["elapsed_worker_seconds"]})
        return 0
    except Exception as exc:
        write_json(status_path, {"status": "failed_exception", "exception": repr(exc),
                                 "elapsed_worker_seconds": time.perf_counter() - started})
        return 1


def job_configs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    jobs: list[dict[str, Any]] = []
    infeasible: list[dict[str, Any]] = []
    source_hashes = {key: sha256(path) for key, path in chain_sources().items()}
    source_hashes["A2g3_runner"] = sha256(A2G3_RUNNER)
    for graph in graph_records():
        for life in LIVES:
            u = round(FRAMES * life)
            kmax = min(u, FRAMES - u + 1)
            for m in M_UP:
                k = round(u / m)
                quota_reason = "" if 1 <= k <= kmax else f"K={k} outside 1..Kmax={kmax}"
                for pi, l_seconds in PARAMS:
                    p01 = pi / ((1 - pi) * l_seconds * FPS)
                    p10 = 1 / (l_seconds * FPS)
                    param_reason = "" if p01 <= 1 and p10 <= 1 else f"transition infeasible: p01={p01:g}, p10={p10:g}"
                    reason = "; ".join(x for x in (quota_reason, param_reason) if x)
                    for seed in SEEDS:
                        name = (f"{graph['family']}__N{graph['N']}__life{life:.1f}__m{m}"
                                f"__pi{pi:.1f}__L{l_seconds:g}s__seed{seed}")
                        cfg = {
                            "stage": "A2h-2", "operation": name, "preregistration_sha256": sha256(PREREG),
                            "runner_sha256": sha256(Path(__file__).resolve()),
                            "family": graph["family"], "graph_id": graph["graph_id"], "N": graph["N"],
                            "graph_edge_list": graph["edge_file"].relative_to(ROOT).as_posix(),
                            "graph_edge_sha256": sha256(graph["edge_file"]),
                            "source_node": graph["source"], "destination_node": graph["destination"],
                            "static_probe_hops": graph["probe_hops"], "fps": FPS, "F": FRAMES,
                            "life": life, "U_requested": u, "D_requested": FRAMES - u,
                            "m_up_target_frames": m, "K_requested": k, "Kmax": kmax,
                            "pi": pi, "L_seconds": l_seconds, "L_frames": l_seconds * FPS,
                            "p10": p10, "p01": p01, "timeline_behavior": "uk",
                            "timeline_seed": seed, "sampler_seed": seed + 10000,
                            "timeout_seconds": TIMEOUT, "source_sha256": source_hashes,
                            "launch_status": "not_launched_infeasible" if reason else "registered_feasible",
                            "infeasible_reason": reason,
                        }
                        row = {**cfg, "planned_status": "not_launched_infeasible" if reason else "registered_feasible"}
                        jobs.append({"name": name, "config": cfg, "graph": graph, "reason": reason})
                        if reason:
                            infeasible.append(row)
    if len(jobs) != 1440 or sum(not j["reason"] for j in jobs) != 990:
        raise RuntimeError("A2h preregistered grid arithmetic mismatch")
    return jobs, infeasible


def run_chain_grid() -> int:
    OUT2.mkdir(parents=True, exist_ok=True)
    jobs, _ = job_configs()
    design_dir = OUT2 / "design_configs"
    ops_dir = OUT2 / "operations"
    log_path = OUT2 / "operation_log.csv"
    rows: list[dict[str, Any]] = []
    fields = ["operation", "status", "returncode", "family", "graph_id", "N", "life", "m_up_target_frames",
              "K_requested", "pi", "L_seconds", "seed", "elapsed_seconds", "config_sha256", "config_path", "error"]
    n_launched = 0
    for index, job in enumerate(jobs, 1):
        cfg = job["config"]
        name = job["name"]
        dcfg = design_dir / f"{name}.json"
        if job["reason"]:
            write_json(dcfg, cfg)
            rows.append({"operation": name, "status": "not_launched_infeasible", "returncode": "NA",
                         "family": cfg["family"], "graph_id": cfg["graph_id"], "N": cfg["N"],
                         "life": cfg["life"], "m_up_target_frames": cfg["m_up_target_frames"],
                         "K_requested": cfg["K_requested"], "pi": cfg["pi"], "L_seconds": cfg["L_seconds"],
                         "seed": cfg["timeline_seed"], "elapsed_seconds": 0,
                         "config_sha256": sha256(dcfg), "config_path": dcfg.relative_to(ROOT).as_posix(),
                         "error": job["reason"]})
            continue
        op_dir = ops_dir / name
        op_dir.mkdir(parents=True, exist_ok=True)
        config_path = op_dir / "config.json"
        launch_path = op_dir / "launch_started.json"
        if launch_path.exists():
            status_doc = json.loads((op_dir / "operation_status.json").read_text()) if (op_dir / "operation_status.json").exists() else {"status": "unknown_interruption_no_retry"}
            metric = json.loads((op_dir / "trace_metrics.json").read_text()) if (op_dir / "trace_metrics.json").exists() else {}
            rows.append({"operation": name, "status": status_doc.get("status", "unknown_interruption_no_retry"),
                         "returncode": "prior_attempt_recorded", "family": cfg["family"], "graph_id": cfg["graph_id"],
                         "N": cfg["N"], "life": cfg["life"], "m_up_target_frames": cfg["m_up_target_frames"],
                         "K_requested": cfg["K_requested"], "pi": cfg["pi"], "L_seconds": cfg["L_seconds"],
                         "seed": cfg["timeline_seed"], "elapsed_seconds": metric.get("elapsed_worker_seconds", "NA"),
                         "config_sha256": sha256(config_path), "config_path": config_path.relative_to(ROOT).as_posix(),
                         "error": status_doc.get("exception", "")})
            continue
        # Config is materialized immediately before this one launch, and the marker forbids retries.
        write_json(config_path, cfg)
        write_json(launch_path, {"launch_started": True, "utc_epoch": time.time(), "timeout_seconds": TIMEOUT})
        started = time.perf_counter()
        n_launched += 1
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker-chain", str(config_path)],
                                  cwd=HERE, timeout=TIMEOUT, capture_output=True, text=True, check=False)
            elapsed = time.perf_counter() - started
            status_doc = json.loads((op_dir / "operation_status.json").read_text()) if (op_dir / "operation_status.json").exists() else {"status": "missing_status"}
            status = status_doc.get("status", "missing_status")
            error = status_doc.get("exception", proc.stderr[-800:])
            retcode: int | str = proc.returncode
        except subprocess.TimeoutExpired as exc:
            elapsed = time.perf_counter() - started
            status, retcode, error = "failed_timeout", "TIMEOUT", str(exc)
            write_json(op_dir / "operation_status.json", {"status": status, "timeout_seconds": TIMEOUT, "elapsed_seconds": elapsed})
        row = {"operation": name, "status": status, "returncode": retcode,
               "family": cfg["family"], "graph_id": cfg["graph_id"], "N": cfg["N"],
               "life": cfg["life"], "m_up_target_frames": cfg["m_up_target_frames"],
               "K_requested": cfg["K_requested"], "pi": cfg["pi"], "L_seconds": cfg["L_seconds"],
               "seed": cfg["timeline_seed"], "elapsed_seconds": elapsed,
               "config_sha256": sha256(config_path), "config_path": config_path.relative_to(ROOT).as_posix(),
               "error": error}
        rows.append(row)
        write_csv(log_path, rows, fields)
        if status == "success" and (op_dir / "trace_metrics.json").exists():
            met = json.loads((op_dir / "trace_metrics.json").read_text())
            if float(met["shortcut_fraction"]) != 0.0:
                print(f"STOP-CRITICAL: shortcut fraction nonzero at {name}; halted after one operation", flush=True)
                summarize_chain(rows, jobs)
                return 2
        print(f"[{index}/{len(jobs)}] {name}: {status} ({elapsed:.2f}s)", flush=True)
    write_csv(log_path, rows, fields)
    summarize_chain(rows, jobs)
    return 0


def summarize_chain(log_rows: list[dict[str, Any]], jobs: list[dict[str, Any]]) -> None:
    by_name = {r["operation"]: r for r in log_rows}
    per_seed: list[dict[str, Any]] = []
    for job in jobs:
        if job["reason"]:
            continue
        cfg, name = job["config"], job["name"]
        op_dir = OUT2 / "operations" / name
        status = by_name.get(name, {}).get("status", "not_started_after_stop")
        metric = {}
        if (op_dir / "trace_metrics.json").exists():
            metric = json.loads((op_dir / "trace_metrics.json").read_text())
            status = metric.get("status", status)
        per_seed.append({**{k: cfg[k] for k in ("family", "graph_id", "N", "life", "m_up_target_frames", "U_requested", "D_requested", "K_requested", "pi", "L_seconds")},
                 "seed": cfg["timeline_seed"], "operation": name, "status": status, **metric})
    write_csv(OUT2 / "per_seed_results.csv", per_seed)
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in per_seed:
        groups[(row["family"], row["N"], row["life"], row["m_up_target_frames"], row["pi"], row["L_seconds"])].append(row)
    cell_rows = []
    for key, group in sorted(groups.items()):
        successful = [r for r in group if r.get("status") == "success"]
        passing = [bool(r.get("operation_pass")) for r in successful]
        rates = [float(r["neighbor_membership_changes_per_node_second"]) for r in successful if r.get("neighbor_membership_changes_per_node_second") is not None]
        cell_pass = len(successful) == 3 and len(passing) == 3 and all(passing)
        cell_rows.append({
            "family": key[0], "N": key[1], "life": key[2], "m_up_target_frames": key[3], "pi": key[4], "L_seconds": key[5],
            "n_registered_seeds": 3, "n_success": len(successful), "n_operation_pass": sum(passing),
            "cell_pass_all_three_seeds": cell_pass,
            "mean_neighbor_changes_per_node_second": statistics.mean(rates) if rates else "NA",
            "sample_sd_neighbor_changes_per_node_second_ddof1": statistics.stdev(rates) if len(rates) > 1 else "NA",
            "mean_neighbor_changes_per_frame": statistics.mean(float(r["neighbor_membership_changes_per_frame"]) for r in successful) if successful else "NA",
        })
    write_csv(OUT2 / "feasible_cell_summary.csv", cell_rows)
    gates = []
    for n in NS:
        rows = [r for r in per_seed if int(r["N"]) == n and r.get("status") == "success"]
        total_launched = sum(1 for j in jobs if int(j["config"]["N"]) == n and not j["reason"] and
                             (OUT2 / "operations" / j["name"] / "launch_started.json").exists())
        tol_pass = sum(bool(r.get("carried_tolerances_pass")) for r in rows)
        mask_pass = sum(bool(r.get("sr_mask_exact")) and bool(r.get("uk_exact_UK")) for r in rows)
        shortcut_zero = sum(float(r.get("shortcut_fraction", math.nan)) == 0 for r in rows)
        gates.append({"N": n, "launched": total_launched, "successful": len(rows), "mask_and_UK_exact": mask_pass,
                      "mask_quota_fraction": mask_pass / total_launched if total_launched else "NA",
                      "mask_gate_pass": total_launched > 0 and mask_pass == total_launched,
                      "joint_carried_tolerance_pass": tol_pass,
                      "joint_tolerance_fraction": tol_pass / total_launched if total_launched else "NA",
                      "required_fraction": 0.9, "tolerance_gate_pass": total_launched > 0 and tol_pass / total_launched >= 0.9,
                      "shortcut_zero_count": shortcut_zero, "shortcut_unresolved_count": total_launched - len(rows),
                      "shortcut_gate_pass": len(rows) > 0 and shortcut_zero == len(rows),
                      "projection_pass": sum(bool(r.get("projection_pass")) for r in rows),
                      "pi_pass": sum(bool(r.get("pi_pass")) for r in rows),
                      "duration_pass": sum(bool(r.get("duration_pass")) for r in rows)})
    write_csv(OUT2 / "per_N_gate_summary.csv", gates)
    tolerance_groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in per_seed:
        tolerance_groups[(row["N"], row["family"], row["pi"], row["L_seconds"])].append(row)
    tolerance_rows = []
    for key, group in sorted(tolerance_groups.items()):
        successful = [r for r in group if r.get("status") == "success"]
        tolerance_rows.append({
            "N": key[0], "family": key[1], "pi": key[2], "L_seconds": key[3],
            "registered_feasible_operations": len(group), "successful_operations": len(successful),
            "exact_mask_UK_pass": sum(bool(r.get("sr_mask_exact")) and bool(r.get("uk_exact_UK")) for r in successful),
            "projection_pass": sum(bool(r.get("projection_pass")) for r in successful),
            "all_edge_pi_pass": sum(bool(r.get("pi_pass")) for r in successful),
            "all_edge_duration_pass": sum(bool(r.get("duration_pass")) for r in successful),
            "joint_carried_tolerance_pass": sum(bool(r.get("carried_tolerances_pass")) for r in successful),
            "shortcut_nonzero_count": sum(float(r.get("shortcut_fraction", 0.0)) != 0.0 for r in successful),
            "unresolved_count": len(group) - len(successful),
        })
    write_csv(OUT2 / "tolerance_by_N_family_parameter.csv", tolerance_rows)
    design_rows = []
    for job in jobs:
        if job["reason"]:
            design_rows.append({"operation": job["name"], "family": job["config"]["family"], "N": job["config"]["N"],
                                "life": job["config"]["life"], "m_up_target_frames": job["config"]["m_up_target_frames"],
                                "pi": job["config"]["pi"], "L_seconds": job["config"]["L_seconds"],
                                "seed": job["config"]["timeline_seed"], "status": "not_launched_infeasible", "reason": job["reason"]})
    write_csv(OUT2 / "infeasible_conditions.csv", design_rows)
    write_json(OUT2 / "summary.json", {"planned_ops": 990, "launched_ops": sum(int(g["launched"]) for g in gates),
                                        "per_N_gates": gates, "shortcut_stop_critical": any(g["shortcut_zero_count"] < g["successful"] for g in gates),
                                        "condition_cells": len(cell_rows), "infeasible_seed_rows": len(design_rows),
                                        "comparison_thresholds": {"A2d_item1_standalone_pi": 0.02, "A2d_item1_standalone_duration_relative": 0.10,
                                                                    "A2g3_integrated_pi": 0.05, "A2g3_integrated_duration_relative": 0.20}})


def run_missing_pool() -> int:
    out = OUT2 / "missing_a2g2_pool_cell"
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / "config.json"
    marker = out / "launch_started.json"
    if marker.exists():
        print("Refusing to retry A2g-2 missing cell: launch marker exists", file=sys.stderr)
        return 3
    graph = next(g for g in graph_records() if g["graph_id"] == "er_N162_r1")
    g = load_graph(graph["edge_file"], 162)
    cfg = {
        "stage": "A2g-2-missing-cell-authorized-by-A2h", "family": "er", "graph_id": "er_N162_r1", "N": 162,
        "graph_edge_list": graph["edge_file"].relative_to(ROOT).as_posix(), "graph_edge_sha256": sha256(graph["edge_file"]),
        "source_node": graph["source"], "destination_node": graph["destination"],
        "endpoint_degree_S": g.degree[graph["source"]], "endpoint_degree_R": g.degree[graph["destination"]],
        "endpoint_edge_shared": g.has_edge(graph["source"], graph["destination"]),
        "mean_degree": 2 * g.number_of_edges() / g.number_of_nodes(), "diameter": 6.0,
        "p_edge": 0.7, "frame_pool_trials": 10000, "pool_seed": 47, "timeout_seconds": TIMEOUT,
        "sampler_behavior": "legacy-iid-frame-pool-count-only-equivalent", "with_replacement_assembly": True,
        "source_sha256": {
            "A2d_item1_frameGenerator.py": sha256(DONOR / "yadygaga" / "frameGenerator.py"),
            "A2d_item1_dynaGraph.py": sha256(DONOR / "yadygaga" / "dynaGraph.py"),
            "runner": sha256(A2G2_RUNNER),
        },
        "preregistration_sha256": sha256(A2G2_PREREG), "a2h_authorization_sha256": sha256(PREREG),
        "python": sys.version, "networkx": nx.__version__,
        "original_missing_operation_id": "er_N162_r1__p0.7__t10000__seed47",
    }
    write_json(config_path, cfg)
    write_json(marker, {"launch_started": True, "utc_epoch": time.time(), "timeout_seconds": TIMEOUT})
    started = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, str(A2G2_RUNNER), "--operation", str(config_path)],
                              cwd=ALPHA / "A2g", timeout=TIMEOUT, capture_output=True, text=True, check=False)
        status = json.loads((out / "operation_status.json").read_text()) if (out / "operation_status.json").exists() else {"status": "missing_status"}
        log = {"status": status.get("status"), "returncode": proc.returncode, "elapsed_seconds": time.perf_counter() - started,
               "stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:], "config_sha256": sha256(config_path)}
    except subprocess.TimeoutExpired as exc:
        status = {"status": "failed_timeout", "timeout_seconds": TIMEOUT}
        write_json(out / "operation_status.json", status)
        log = {"status": status["status"], "returncode": "TIMEOUT", "elapsed_seconds": time.perf_counter() - started,
               "stdout": "", "stderr": str(exc), "config_sha256": sha256(config_path)}
    write_json(out / "a2h_completion_log.json", log)
    if status.get("status") != "success":
        print(json.dumps(log, indent=2))
        return 1
    summarize_missing_pool()
    print(json.dumps(log, indent=2))
    return 0


def summarize_missing_pool() -> None:
    metrics = json.loads((OUT2 / "missing_a2g2_pool_cell" / "pool_metrics.json").read_text())
    old_seed = read_csv(ALPHA / "A2g" / "A2g-2" / "pstar_per_seed.csv")
    old_seed47 = next(r for r in old_seed if r["family"] == "er" and int(r["N"]) == 162
                      and int(r["trials"]) == 10000 and int(r["seed"]) == 47)
    old_seed_p120 = float(old_seed47["pstar_F120"]) if old_seed47["pstar_F120"] not in ("", "NA", "nan") else None
    old_seed_p240 = float(old_seed47["pstar_F240"]) if old_seed47["pstar_F240"] not in ("", "NA", "nan") else None
    # This one missing p=.7 result updates seed 47's registered p* if it passes quota.
    new_p120 = max([x for x in (old_seed_p120, 0.7 if metrics["strict_all_life_F120"] else None) if x is not None], default=None)
    new_p240 = max([x for x in (old_seed_p240, 0.7 if metrics["strict_all_life_F240"] else None) if x is not None], default=None)
    old_er_n162_by_seed = {int(r["seed"]): float(r["pstar_F120"]) for r in old_seed
                           if r["family"] == "er" and int(r["N"]) == 162 and int(r["trials"]) == 10000
                           and r["pstar_F120"] not in ("", "NA", "nan")}
    if 47 not in old_er_n162_by_seed:
        raise RuntimeError("registered ER N=162 seed-47 p* row missing from prior results")
    updated_er_n162_by_seed = dict(old_er_n162_by_seed)
    if new_p120 is not None:
        updated_er_n162_by_seed[47] = new_p120
    pstar_row = {"family": "er", "graph_id": "er_N162_r1", "N": 162, "trials": 10000, "seed": 47,
                 "new_cell_p_edge": 0.7, "F120_cell_ready": metrics["strict_all_life_F120"],
                 "F240_cell_ready": metrics["strict_all_life_F240"], "pstar_F120_contribution": new_p120 if new_p120 is not None else "not_reached",
                 "pstar_F240_contribution": new_p240 if new_p240 is not None else "not_reached",
                 "up_pool_frames": metrics["up_pool_frames"], "down_pool_frames": metrics["down_pool_frames"]}
    write_csv(OUT2 / "missing_pool_cell_result.csv", [pstar_row])
    graph_summary = read_csv(ALPHA / "A2g" / "A2g-2" / "pstar_by_graph_trials.csv")
    # Recompute with the completed cell replacing seed 47's existing p*; retain the original three-seed denominator.
    family_results = []
    for family in FAMILIES:
        old_means: dict[int, float] = {}
        for r in graph_summary:
            if r["family"] == family and int(r["trials"]) == 10000:
                old_means[int(r["N"])] = float(r["pstar_F120_mean"])
        values = {n: old_means[n] for n in (42, 92, 162)}
        if family == "er":
            values[162] = statistics.mean(updated_er_n162_by_seed.values())
        monotone = values[42] >= values[92] >= values[162]
        family_results.append({"family": family, "trials": 10000,
                               "pstar_mean_N42": values[42], "pstar_mean_N92": values[92],
                               "pstar_mean_N162_updated_if_er": values[162], "nonincreasing": monotone,
                               "N162_seed_count": len(updated_er_n162_by_seed) if family == "er" else "NA",
                               "updated_N162_seed47_pstar": new_p120 if family == "er" and new_p120 is not None else "unchanged"})
    prior_count = 4
    updated_count = sum(bool(r["nonincreasing"]) for r in family_results)
    write_csv(OUT2 / "pstar_monotonicity_update.csv", family_results)
    write_json(OUT2 / "missing_pool_summary.json", {
        "operation": "er_N162_r1__p0.7__t10000__seed47", "pool_metrics": metrics,
        "F120_pstar_contribution": new_p120, "F240_pstar_contribution": new_p240,
        "previous_10000_trial_monotonic_families": prior_count,
        "updated_10000_trial_monotonic_families": updated_count,
        "monotonicity_count_changed": updated_count != prior_count,
        "family_results": family_results,
    })


def finalize_manifest() -> None:
    manifest_path = HERE / "MANIFEST.sha256"
    paths = [p for p in HERE.rglob("*") if p.is_file() and p != manifest_path
             and p.name != "a2h_report.md" and ".git" not in p.parts]
    paths.append(LIMITATIONS)
    lines = [f"{sha256(p)}  {p.relative_to(HERE).as_posix() if p.is_relative_to(HERE) else '../LIMITATIONS.md'}"
             for p in sorted(set(paths))]
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--distortion", action="store_true")
    parser.add_argument("--chain-grid", action="store_true")
    parser.add_argument("--missing-pool", action="store_true")
    parser.add_argument("--worker-chain", type=Path)
    parser.add_argument("--manifest", action="store_true")
    args = parser.parse_args()
    if args.worker_chain:
        return worker_chain(args.worker_chain.resolve())
    if args.distortion:
        run_distortion()
        return 0
    if args.chain_grid:
        return run_chain_grid()
    if args.missing_pool:
        return run_missing_pool()
    if args.manifest:
        finalize_manifest()
        return 0
    parser.error("select one operation")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
