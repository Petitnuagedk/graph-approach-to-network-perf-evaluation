#!/usr/bin/env python3
"""Offline A4.0d detector replay and DSDV outage characterization."""
from __future__ import annotations
import csv, math
from pathlib import Path

HERE=Path(__file__).resolve().parent
A4=HERE.parent
DELTA=1024*8/50_000
GAP_LIMIT=1.0
HORIZON=10.0
RUNS=A4/"runs"


def read_csv(path: Path) -> list[dict[str,str]]:
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str,object]]) -> None:
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def fmt(x: float) -> str:
    return "nan" if not math.isfinite(x) else f"{x:.9f}"


def unique_schedule_match(app_tx: float, nflows: int):
    found=[]
    for flow_index in range(nflows):
        start=.1+flow_index/nflows
        packet_index=round((app_tx-start)/DELTA)
        if packet_index>=0 and abs(app_tx-(start+packet_index*DELTA))<=2e-8:
            found.append((flow_index,packet_index))
    return found[0] if len(found)==1 else None


def readiness(rx_times: list[float], first_tx: float) -> tuple[float,list[dict[str,object]]]:
    """Return start of final all-ready suffix of 10s Rx-gap windows."""
    rx=sorted(set(round(x,9) for x in rx_times))
    states=[]
    for t in rx:
        if t+1e-12 < first_tx+HORIZON:
            continue
        left=t-HORIZON
        in_window=[x for x in rx if left-1e-10 <= x <= t+1e-10]
        good=bool(in_window) and in_window[0]-left <= GAP_LIMIT+1e-10
        good=good and all(b-a <= GAP_LIMIT+1e-10 for a,b in zip(in_window,in_window[1:]))
        states.append((t,good,len(in_window),in_window[0]-left if in_window else math.nan,
                       max((b-a for a,b in zip(in_window,in_window[1:])),default=math.nan)))
    last_bad=max((i for i,(_,ok,*_) in enumerate(states) if not ok),default=-1)
    suffix=states[last_bad+1:]
    conv=suffix[0][0] if suffix else math.nan
    rows=[{"evaluation_s":fmt(t),"ready":str(ok).lower(),"rx_count_10s":n,
           "leading_gap_s":fmt(lead),"max_internal_gap_s":fmt(max_gap)}
          for t,ok,n,lead,max_gap in states]
    return conv,rows


def scheduled_probe(run_id: str, protocol: str):
    run_dir=RUNS/run_id
    rows=read_csv(run_dir/f"packets_{protocol}.csv")
    nflows=len([r for r in read_csv(run_dir/"flows.csv") if r["protocol"]==protocol])
    tx_times={round(float(r["app_tx_time_s"]),9) for r in rows if r["event"]=="tx" and
              (match:=unique_schedule_match(float(r["app_tx_time_s"]),nflows)) is not None and match[0]==0}
    rxmap={}
    for r in rows:
        if r["event"]!="rx": continue
        app=round(float(r["app_tx_time_s"]),9)
        match=unique_schedule_match(app,nflows)
        if match is not None and match[0]==0 and app in tx_times:
            event=float(r["event_time_s"])
            rxmap[app]=min(event,rxmap.get(app,math.inf))
    probe_tx=[]
    for i in range(2000):
        t=round(.1+i*DELTA,9)
        if t > 239.0: break
        if t not in tx_times: continue
        probe_tx.append(t)
    successful=[(i,t,rxmap[t]) for i,t in enumerate(probe_tx) if t in rxmap]
    losses=[(i,t) for i,t in enumerate(probe_tx) if t not in rxmap]
    groups=[]
    for item in losses:
        if not groups or item[0] > groups[-1][-1][0]+1: groups.append([])
        groups[-1].append(item)
    delivered=sorted(set(r for _,_,r in successful))
    gaps=[(b-a,a,b) for a,b in zip(delivered,delivered[1:])]
    bad=[x for x in gaps if x[0]>GAP_LIMIT]
    conv,window_rows=readiness(delivered,probe_tx[0] if probe_tx else 0.0)
    return {"tx":probe_tx,"successful":successful,"losses":losses,"loss_groups":groups,
            "delivered":delivered,"gaps":gaps,"bad_gaps":bad,"readiness":conv,
            "readiness_windows":window_rows}


def main() -> None:
    six=read_csv(HERE.parent/"A4_0c"/"detector_comparison_six_runs.csv")
    by_run={r["run_id"]:r for r in six}
    comparisons=[]; dsdv_data=None
    for protocol in ("olsr","aodv","dsdv"):
        run=f"40B_geodesic_N42_r1_{protocol}_validation"
        data=scheduled_probe(run,protocol)
        old=by_run[run]
        conv=data["readiness"]
        censored=(not math.isfinite(conv) or conv>180)
        comparisons.append({"run_id":run,"protocol":protocol,
            "original_s":old["replayed_original_s"],"corrected_original_0_99_s":old["corrected_original_matured_delta_s"],
            "C95_s_not_adopted":old["candidate_0_95_matured_s"],"C90_s":old["candidate_0_90_matured_s"],
            "readiness_G1_s":fmt(conv),"censored_gt180_or_nan":str(censored).lower(),
            "mechanical_ceil_1_5x_frames_diagnostic_only":math.ceil(1.5*conv) if math.isfinite(conv) else "not_derivable",
            "last_gap_gt1_start_rx_s":fmt(data["bad_gaps"][-1][1]) if data["bad_gaps"] else "none",
            "last_gap_gt1_end_rx_s":fmt(data["bad_gaps"][-1][2]) if data["bad_gaps"] else "none",
            "last_gap_gt1_s":fmt(data["bad_gaps"][-1][0]) if data["bad_gaps"] else "none",
            "last_gap_sets_readiness":str(bool(data["bad_gaps"])).lower()})
        if protocol=="dsdv": dsdv_data=data
        write_csv(HERE/f"readiness_windows_{protocol}.csv",data["readiness_windows"])
    write_csv(HERE/"detector_comparison.csv",comparisons)
    assert dsdv_data is not None
    event_rows=[]
    for j,group in enumerate(dsdv_data["loss_groups"],1):
        for i,t in group:
            event_rows.append({"loss_run":j,"consecutive_run_length":len(group),"probe_packet_index":i,
                               "loss_tx_s":fmt(t),"offset_from_nearest_15s_tick_s":fmt(t-round(t/15)*15)})
    write_csv(HERE/"dsdv_loss_events.csv",event_rows)
    gap_rows=[{"gap_s":fmt(gap),"previous_rx_s":fmt(a),"next_rx_s":fmt(b),
               "next_rx_tx_index":next((i for i,_,r in dsdv_data["successful"] if abs(r-b)<1e-9),"")}
              for gap,a,b in sorted(dsdv_data["gaps"],reverse=True)]
    write_csv(HERE/"dsdv_delivery_gaps.csv",gap_rows)
    run_dir=RUNS/"40B_geodesic_N42_r1_dsdv_validation"
    packet_diag=read_csv(run_dir/"packet_diagnostics_dsdv.csv")[0]
    node_diag=read_csv(run_dir/"node_diagnostics.csv")
    by_node={}
    for row in node_diag:
        node=int(row["node_id"]); metric=row["metric"]
        value=int(row["value"])
        if metric in ("mac_queue_drops","phy_rx_drop_class"):
            slot=by_node.setdefault(node,{"node_id":node,"mac_queue_drops_all_run":0,
                "phy_rx_below_sensitivity_all_run":0,"phy_rx_collision_interference_all_run":0,
                "phy_rx_other_unclassified_all_run":0})
            if metric=="mac_queue_drops": slot["mac_queue_drops_all_run"]+=value
            elif row["phy_reason"]=="below_sensitivity": slot["phy_rx_below_sensitivity_all_run"]+=value
            elif row["phy_reason"]=="collision_interference": slot["phy_rx_collision_interference_all_run"]+=value
            elif row["phy_reason"]=="other_unclassified": slot["phy_rx_other_unclassified_all_run"]+=value
    counters=[{"scope":"all_run_global","node_id":"all","counter":"app_ip_no_route_drops",
               "count":packet_diag["app_ip_no_route_drops"],"timestamped_for_195_7_196_3s":False},
              {"scope":"all_run_global","node_id":"all","counter":"app_ip_route_error_drops",
               "count":packet_diag["app_ip_route_error_drops"],"timestamped_for_195_7_196_3s":False},
              {"scope":"all_run_global","node_id":"all","counter":"mac_queue_drop_callbacks",
               "count":packet_diag["mac_queue_drop_callbacks"],"timestamped_for_195_7_196_3s":False},
              {"scope":"all_run_global","node_id":"all","counter":"phy_rx_drop_callbacks",
               "count":packet_diag["phy_rx_drop_callbacks"],"timestamped_for_195_7_196_3s":False}]
    counters.extend({"scope":"per_node_all_run","node_id":n,"counter":k,"count":v,
                     "timestamped_for_195_7_196_3s":False}
                    for n,vals in sorted(by_node.items()) for k,v in vals.items())
    write_csv(HERE/"dsdv_counter_observability.csv",counters)
    t3={"T3_immediate":list(map(float,range(41))),
        "T3_delayed":list(map(float,range(15,41))),
        "T3_never":list(map(float,range(0,41,2)))}
    syn=[]
    for name,rx in t3.items():
        conv,_=readiness(rx,0.0); expected={"T3_immediate":10.,"T3_delayed":24.,"T3_never":math.nan}[name]
        passed=(math.isnan(conv) and math.isnan(expected)) or conv==expected
        syn.append({"case":name,"readiness_s":fmt(conv),"expected_s":fmt(expected),"pass":str(passed).lower()})
    base=[i*DELTA for i in range(245)]
    base_result=readiness(base,0.0)[0]
    for count in range(4):
        removed={30+8*j for j in range(count)}
        rx=[t for i,t in enumerate(base) if i not in removed]
        conv=readiness(rx,0.0)[0]
        syn.append({"case":f"isolated_losses_{count}","readiness_s":fmt(conv),
                    "expected_s":fmt(base_result),"pass":str(conv==base_result).lower()})
    write_csv(HERE/"readiness_synthetic_tests.csv",syn)
    print("detector",comparisons)
    print("DSDV loss runs",[(len(g),g[0][1],g[-1][1]) for g in dsdv_data["loss_groups"]])
    print("DSDV largest gap",max(dsdv_data["gaps"]))
    print("synthetics",syn)

if __name__=="__main__": main()
