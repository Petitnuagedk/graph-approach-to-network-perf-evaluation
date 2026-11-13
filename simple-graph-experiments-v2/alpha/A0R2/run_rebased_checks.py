#!/usr/bin/env python3
"""Frozen A0 rerun and patched-axis probes for the A0R2 isolated source overlay."""
from __future__ import annotations
import csv
import hashlib
import importlib.util
import itertools
import json
import statistics
import sys
import time
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "YaDyGaGa"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE))
from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator, MPCTimelineBlockGenerator

spec = importlib.util.spec_from_file_location(
    "a0r2_rebased_dynaGraph", SOURCE / "yadygaga" / "dynaGraph.py"
)
dyna = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dyna)
SPCDynamicGraph = dyna.SPCDynamicGraph
MPCDynamicGraph = dyna.MPCDynamicGraph
from icosahedral_geodesic import create_icosahedral_geodesic_graph

ladder_spec = importlib.util.spec_from_file_location("a0r2_ladder_maker", ROOT / "ladder-maker.py")
ladder_module = importlib.util.module_from_spec(ladder_spec)
ladder_spec.loader.exec_module(ladder_module)
build_ladder_with_terminals = ladder_module.build_ladder_with_terminals
build_line_with_terminals = ladder_module.build_line_with_terminals

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)


def geodesic(frequency=3):
    raw = create_icosahedral_geodesic_graph(frequency, 0)
    graph = nx.relabel_nodes(raw, {node: f"Node_{node}" for node in raw.nodes()}, copy=True)
    nodes = sorted(graph, key=lambda n: int(n.rpartition("_")[2]))
    best = (-1, None, None)
    for i, source in enumerate(nodes):
        distances = nx.single_source_shortest_path_length(graph, source)
        for destination in nodes[i + 1:]:
            if distances[destination] > best[0]:
                best = (distances[destination], source, destination)
    return graph, best[1], best[2]


def bits(frames, source, destination):
    out = []
    for frame in frames:
        try:
            nx.shortest_path(frame, source, destination)
            out.append("1")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            out.append("0")
    return "".join(out)


def run_trace(graph, source, destination, frames, life, stability, persistency, seed, trials=500, frame_seed=None, assembly_seed=None):
    frame_seed = seed + 10_000 if frame_seed is None else frame_seed
    assembly_seed = seed + 20_000 if assembly_seed is None else assembly_seed
    fg = FrameGenerator()
    fg.generateSPCFrames(graph, source, destination, trials=trials, p_edge=.5, pathPersistency=persistency, seed=frame_seed)
    timeline = SPCTimelineBlockGenerator(frames, life, stability, seed, pathPersistency=persistency).generate_blocks()
    assembled = SPCDynamicGraph().buildDynaGraph(timeline, fg.path_up_frames, fg.path_down_frames, seed=assembly_seed)
    sr = bits(assembled, source, destination)
    schedule = "".join("1" if value else "0" for value in timeline["timeline"])
    up_runs = sum(value == "1" and (i == 0 or schedule[i-1] == "0") for i, value in enumerate(schedule))
    return {
        "schedule": schedule, "path_ids": timeline["path_ids"], "sr_bits": sr,
        "up_pool_frames": sum(len(group) for group in fg.path_up_frames),
        "up_pool_groups": len(fg.path_up_frames), "down_pool_frames": len(fg.path_down_frames),
        "pool_empty": not fg.path_up_frames or not fg.path_down_frames,
        "up_runs": up_runs,
    }


def pairwise_mean(strings):
    values = [sum(a != b for a, b in zip(x, y)) / len(x) for x, y in itertools.combinations(strings, 2)]
    return statistics.mean(values) if values else 0.0


def frozen_a0():
    graph92, s92, d92 = geodesic(3)
    graph162, s162, d162 = geodesic(4)
    rows = []
    for role, cases in (
        ("diversity", [(0.5, seed) for seed in range(42, 47)]),
        ("fidelity", [(life, seed) for life in (.3, .5, .7) for seed in range(42, 47)]),
        ("timing", [(.5, seed) for seed in (42, 43, 44)]),
    ):
        for life, seed in cases:
            graph, source, destination, frames = (graph162, s162, d162, 120) if role == "timing" else (graph92, s92, d92, 120)
            started = time.perf_counter()
            record = run_trace(graph, source, destination, frames, life, .8, .9, seed)
            elapsed = time.perf_counter() - started
            record.update({
                "role": role, "N": graph.number_of_nodes(), "life": life,
                "stability": .8, "persistency": .9, "seed": seed,
                "generation_seconds": elapsed,
                "timeline_quota": record["schedule"].count("1"),
                "realized_sr_uptime": record["sr_bits"].count("1") / frames,
            })
            rows.append(record)
    with (RESULTS / "frozen_a0_rebased.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    diversity = [r for r in rows if r["role"] == "diversity"]
    fidelity = [r for r in rows if r["role"] == "fidelity"]
    timing = [r for r in rows if r["role"] == "timing"]
    return {
        "diversity_unique": len({r["sr_bits"] for r in diversity}),
        "diversity_mean_hamming": pairwise_mean([r["sr_bits"] for r in diversity]),
        "diversity_pass": len({r["sr_bits"] for r in diversity}) >= 5 and pairwise_mean([r["sr_bits"] for r in diversity]) > .10,
        "fidelity_cases": len(fidelity),
        "fidelity_exact_quota": all(r["timeline_quota"] == round(120*r["life"]) for r in fidelity),
        "fidelity_max_abs_uptime_error": max(abs(r["realized_sr_uptime"]-r["life"]) for r in fidelity),
        "fidelity_pass": all(abs(r["realized_sr_uptime"]-r["life"]) <= .05 for r in fidelity),
        "timing_max_seconds": max(r["generation_seconds"] for r in timing),
        "timing_all_pools_nonempty": all(not r["pool_empty"] for r in timing),
        "timing_pass": max(r["generation_seconds"] for r in timing) < 600 and all(not r["pool_empty"] for r in timing),
        "timing_pool_extents": [{k:r[k] for k in ("seed","up_pool_frames","up_pool_groups","down_pool_frames","generation_seconds")} for r in timing],
    }


def stability_probe(graph, source, destination):
    rows=[]
    for stability in (0,.2,.4,.6,.8):
        for seed in range(42,52):
            timeline=SPCTimelineBlockGenerator(120,.5,stability,seed,pathPersistency=.75).generate_blocks()["timeline"]
            schedule="".join("1" if x else "0" for x in timeline)
            up_runs=sum(x and (i==0 or not timeline[i-1]) for i,x in enumerate(timeline))
            transitions=sum(schedule[i]!=schedule[i-1] for i in range(1,len(schedule)))
            rows.append({"life":.5,"stability":stability,"persistency":.75,"seed":seed,"up_count":sum(timeline),"transitions":transitions,"up_runs":up_runs,"mean_up_run":sum(timeline)/up_runs,"schedule":schedule})
    with (RESULTS/"stability_axis.csv").open("w",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summaries=[]
    for stability in (0,.2,.4,.6,.8):
        sub=[r for r in rows if r["stability"]==stability]
        summaries.append({"stability":stability,"mean_transitions":statistics.mean(r["transitions"] for r in sub),"min_transitions":min(r["transitions"] for r in sub),"max_transitions":max(r["transitions"] for r in sub),"mean_up_run":statistics.mean(r["mean_up_run"] for r in sub),"min_up_run":min(r["mean_up_run"] for r in sub),"max_up_run":max(r["mean_up_run"] for r in sub)})
    return summaries


def persistency_probe():
    line=build_line_with_terminals(90)
    ladder=build_ladder_with_terminals(45)
    geod,_,_=geodesic(3)
    cases=(("line",line,"S","R",1.0),("ladder",ladder,"S","R",.9),("geodesic",geod,"Node_0","Node_31",.5))
    all_rows=[]
    for name, graph, source, destination, edge_prob in cases:
        fg=FrameGenerator()
        fg.generateSPCFrames(graph,source,destination,trials=3000,p_edge=edge_prob,seed=51042)
        route_groups=len(fg.path_up_frames)
        for persistency in (0,.25,.5,.75,1):
            for seed in range(42,52):
                schedule=SPCTimelineBlockGenerator(120,.5,.8,seed,pathPersistency=persistency).generate_blocks()
                ids=schedule["path_ids"]
                bits_=[]
                dynamic=SPCDynamicGraph().buildDynaGraph(schedule,fg.path_up_frames,fg.path_down_frames,seed=seed+20000)
                route_seq=[]
                for frame in dynamic:
                    try: route_seq.append(tuple(nx.shortest_path(frame,source,destination)))
                    except (nx.NetworkXNoPath,nx.NodeNotFound): route_seq.append(None)
                id_same=id_total=route_same=route_total=0
                for i in range(1,120):
                    if schedule["timeline"][i] and schedule["timeline"][i-1]:
                        id_total+=1; route_total+=1
                        id_same+=ids[i]==ids[i-1]
                        route_same+=route_seq[i] is not None and route_seq[i]==route_seq[i-1]
                all_rows.append({"skeleton":name,"N":graph.number_of_nodes(),"pair":f"{source}-{destination}","edge_probability":edge_prob,"candidate_trials":3000,"candidate_up_groups":route_groups,"persistency":persistency,"seed":seed,"adjacent_up_id_pairs":id_total,"path_id_retention":id_same/id_total if id_total else None,"adjacent_up_route_pairs":route_total,"assembled_route_retention":route_same/route_total if route_total else None})
    with (RESULTS/"persistency_skeletons.csv").open("w",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=list(all_rows[0])); w.writeheader(); w.writerows(all_rows)
    summary=[]
    for name in ("line","ladder","geodesic"):
        for persistency in (0,.25,.5,.75,1):
            sub=[r for r in all_rows if r["skeleton"]==name and r["persistency"]==persistency]
            summary.append({"skeleton":name,"persistency":persistency,"candidate_up_groups":sub[0]["candidate_up_groups"],"mean_id_retention":statistics.mean(r["path_id_retention"] for r in sub if r["path_id_retention"] is not None),"mean_route_retention":statistics.mean(r["assembled_route_retention"] for r in sub if r["assembled_route_retention"] is not None)})
    return summary


def mpc_probe(graph, label, pairs):
    fg=FrameGenerator().generateMPCFrames(graph,pairs,trials=1000,p_edge=.5,seed=42)
    timeline=MPCTimelineBlockGenerator(120,2,.5,.8,mode="indep",seed=42,pathPersistency=.9).generate()
    dg=MPCDynamicGraph(); assembled=dg.buildDynaGraph(timeline,fg,seed=43)
    return {"relation":label,"pairs":pairs,"N":graph.number_of_nodes(),"sample_frames":1000,"p_edge":.5,"frame_seed":42,"timeline_frames":120,"timeline_mode":"indep","timeline_seed":42,"assembly_seed":43,"status_counts":{str(k):v for k,v in fg["counts"].items()},"per_pair_up_pools":[len(p["up_indices"]) for p in fg["per_pair"]],"per_pair_down_pools":[len(p["down_indices"]) for p in fg["per_pair"]],"timeline_patterns":len({tuple(x is not None for x in frame) for frame in timeline}),"assembled_frames":len(assembled),"selected_status_counts":{str(k):dg.selected_statuses.count(k) for k in sorted(set(dg.selected_statuses))}}


def main():
    graph92,s92,d92=geodesic(3)
    result={"frozen_a0":frozen_a0(),"stability_axis":stability_probe(graph92,s92,d92),"persistency_skeletons":persistency_probe()}
    pairs={"disjoint":[(s92,d92),("Node_1","Node_91")],"shared_source":[(s92,d92),(s92,"Node_1")]}
    result["mpc_two_pair"]=[mpc_probe(graph92,label,these) for label,these in pairs.items()]
    (RESULTS/"rebased_axis_summary.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__": main()
