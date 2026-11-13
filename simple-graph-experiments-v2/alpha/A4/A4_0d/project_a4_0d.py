#!/usr/bin/env python3
"""Offline, preregister-aware A4.1+4.2+4.3 runtime projection."""
from __future__ import annotations
import csv, math
from pathlib import Path

A4=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
N_VALUES=(42,92,162)
PROTOCOLS=("aodv","dsdv","olsr")


def rows(path: Path):
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))

def write(path: Path, data: list[dict]):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator="\n"); w.writeheader(); w.writerows(data)

def llround(x: float) -> int: return math.floor(x+0.5)

def main():
    ledger=rows(A4/"runs.csv")
    validation={r["protocol"]:float(r["process_wall_s"]) for r in ledger if r["stage"]=="4.0B"}
    successful=[r for r in ledger if r["stage"]=="4.0A" and r["status"]=="success"]
    pilot={(r["protocol"],r["load_role"]):float(r["process_wall_s"]) for r in successful}
    a1=pilot[("aodv","phi1")]; d1=pilot[("dsdv","phi1")]; d10=pilot[("dsdv","phi10")]
    slope=(d10-d1)/(1304-130)
    anchors={"aodv":a1,"dsdv":d1}
    role_count={n:[llround(k*n) for k in (.25,.5,1.)] for n in N_VALUES}
    multipliers=(1.25,2.5)
    scenarios=("direct_N42_anchor","olsr_AODV_pilot_bound","olsr_DSDV_pilot_bound")
    detail=[]
    for scenario in scenarios:
      for n in N_VALUES:
       for proto in PROTOCOLS:
        base_direct=validation[proto]*(n/42)**2
        if proto=="olsr":
            bound=anchors["dsdv"] if scenario=="olsr_DSDV_pilot_bound" else anchors["aodv"]
            base_pilot=bound*2*(n/162)**2 # 120 pilot frames -> 240-frame 4.1 basis
            base=base_direct if scenario=="direct_N42_anchor" else max(base_direct,base_pilot)
            load_anchor=bound
        else:
            base_pilot=anchors[proto]*2*(n/162)**2
            base=base_direct if scenario=="direct_N42_anchor" else max(base_direct,base_pilot)
            load_anchor=anchors[proto]
        load_factors=[1.0 if cnt<=130 else max(1.0,(load_anchor+slope*(cnt-130))/load_anchor)
                      for cnt in role_count[n]]
        # 4.1: 5 families, 1 probe-only run per family/protocol.
        detail.append({"scenario":scenario,"duration_multiplier":1.0,"stage":"4.1","N":n,
          "protocol":proto,"variants":5,"unit_runtime_s":f"{base:.9f}","projected_serial_s":f"{5*base:.9f}",
          "load_role":"probe_only","background_flows":0})
        for mult in multipliers:
            # The exact post-4.1 projection replaces this illustrative factor by (warmup+120)/240.
            detail.append({"scenario":scenario,"duration_multiplier":mult,"stage":"4.2","N":n,
              "protocol":proto,"variants":15,"unit_runtime_s":f"{base:.9f}",
              "projected_serial_s":f"{5*base*sum(load_factors)*mult:.9f}",
              "load_role":"kappa_0.25|0.5|1.0","background_flows":"|".join(map(str,role_count[n]))})
            # 4.3 maximum: four random families x two realizations x one highest tested role.
            detail.append({"scenario":scenario,"duration_multiplier":mult,"stage":"4.3","N":n,
              "protocol":proto,"variants":8,"unit_runtime_s":f"{base:.9f}",
              "projected_serial_s":f"{8*base*load_factors[-1]*mult:.9f}",
              "load_role":"kappa_1.0_upper_bound","background_flows":role_count[n][-1]})
    write(OUT/"projection_by_stage_cell.csv",detail)
    totals=[]
    for scenario in scenarios:
      for mult in multipliers:
        stage_s={st:sum(float(r["projected_serial_s"]) for r in detail if r["scenario"]==scenario and r["stage"]==st and (st=="4.1" or float(r["duration_multiplier"])==mult)) for st in ("4.1","4.2","4.3")}
        total=sum(stage_s.values()); k=4; ideal=total/k
        totals.append({"scenario":scenario,"duration_multiplier_4_2_4_3":mult,
          "variants_4_1":45,"variants_4_2_max":135,"variants_4_3_max":72,"variants_total_max":252,
          "serial_4_1_h":f"{stage_s['4.1']/3600:.6f}","serial_4_2_h":f"{stage_s['4.2']/3600:.6f}",
          "serial_4_3_h":f"{stage_s['4.3']/3600:.6f}","serial_total_h":f"{total/3600:.6f}",
          "workers_k":k,"ideal_k_worker_h":f"{ideal/3600:.6f}",
          "vs_24h":"UNDER" if ideal<=24*3600 else "OVER"})
    write(OUT/"projection_totals.csv",totals)
    print("DSDV slope s/background-flow",slope)
    print("role counts",role_count)
    for r in totals: print(r)
if __name__=="__main__": main()
