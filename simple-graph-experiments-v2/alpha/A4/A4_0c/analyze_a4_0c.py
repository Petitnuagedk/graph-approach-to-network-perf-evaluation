#!/usr/bin/env python3
"""Offline A4.0c detector, negative-control, and projection analysis."""
from __future__ import annotations
import csv, hashlib, json, math, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
A4 = HERE.parent
STUDY = A4.parents[1]
RUNS = A4 / "runs"
DELTA = 1024 * 8 / 50_000
TOL = 2e-8
STOP_B = 239.0
STOP_A = 119.0


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def write_manifests():
    ns3=Path("/home/hledirach/Documents/sp1-sp2")
    inputs=[A4/"prereg.md",A4/"amendment_1.md",A4/"a4.py",A4/"PRE_RUN_IDENTITY.md",
            A4/"runs.csv",A4/"validation_4.0.json",A4/"flow_count_checks_4.0.csv",
            A4/"endpoint_incidence_4.0.csv",A4/"derived_4.0.csv",
            A4/"A4_0b"/"a4_0b_report.md",A4/"A4_0b"/"INPUTS.sha256",A4/"A4_0b"/"MANIFEST.sha256",
            ns3/"VERSION",ns3/"ns3",ns3/"scratch"/"graph-run.cc",
            ns3/"src"/"olsr"/"model"/"olsr-header.cc",ns3/"src"/"olsr"/"model"/"olsr-header.h",
            ns3/"src"/"aodv"/"model"/"aodv-routing-protocol.cc"]
    inputs.extend(p for run in sorted((A4/"runs").glob("40A_*"))+sorted((A4/"runs").glob("40B_*"))
                  for p in run.rglob("*") if p.is_file())
    graph_manifest=STUDY/"alpha"/"A1"/"results"/"graph_manifest.json"
    inputs.append(graph_manifest)
    if graph_manifest.exists():
        item=next(x for x in json.loads(graph_manifest.read_text(encoding="utf-8")) if x["graph_id"]=="geodesic_N42_r1")
        inputs.append(STUDY/"alpha"/"A1"/item["edge_list"])
    entries=[]
    for path in sorted(set(inputs),key=str):
        if not path.is_file(): continue
        try: label=path.relative_to(STUDY).as_posix()
        except ValueError: label=path.as_posix()
        entries.append(f"{sha(path)}  {label}")
    (HERE/"INPUTS.sha256").write_text("\n".join(entries)+"\n",encoding="utf-8")
    outputs=sorted([p for p in HERE.rglob("*") if p.is_file() and p.name!="MANIFEST.sha256"]+
                   [A4/"amendment_2.md"],key=str)
    rows=[f"{sha(p)}  {p.relative_to(STUDY).as_posix()}" for p in outputs if p.is_file()]
    (HERE/"MANIFEST.sha256").write_text("\n".join(rows)+"\n",encoding="utf-8")


def fnum(x, default=math.nan):
    try:
        z=float(x); return z if math.isfinite(z) else default
    except (TypeError, ValueError): return default


def schedule_index(t: float, n: int, warmup: float=0.0):
    found=[]
    for i in range(n):
        start=warmup+0.1+i/n
        k=round((t-start)/DELTA)
        if k>=0 and abs(t-(start+k*DELTA))<=TOL: found.append((i,k))
    return found[0] if len(found)==1 else None


def load_b_packet_data(run_dir: Path, protocol: str):
    flows=[r for r in read_csv(run_dir/"flows.csv") if r["protocol"]==protocol]
    packet=read_csv(run_dir/f"packets_{protocol}.csv")
    tx_by_time={}
    for r in packet:
        if r["event"]!="tx": continue
        t=float(r["app_tx_time_s"]); m=schedule_index(t,len(flows))
        if m and m[0]==0: tx_by_time[round(t,9)]=t
    rx_by_time={}
    for r in packet:
        if r["event"]!="rx": continue
        t=float(r["app_tx_time_s"]); k=round(t,9)
        if k in tx_by_time:
            rx_by_time[k]=min(float(r["event_time_s"]),rx_by_time.get(k,math.inf))
    return flows, sorted(tx_by_time.values()), rx_by_time


def detector_evals(tx: list[float], rxmap: dict[float,float], stop: float,
                    mature: bool=False, threshold: float=.99):
    rxtimes=list(rxmap.values())
    first=tx[0]+10 if tx else math.inf
    ends={first,stop}
    tags={first:{"expiry"},stop:{"expiry"}}
    for t in tx:
        if first<=t<=stop: ends.add(t); tags.setdefault(t,set()).add("Tx")
        if first<=t+10<=stop: ends.add(t+10); tags.setdefault(t+10,set()).add("expiry")
    for t in rxtimes:
        if first<=t<=stop: ends.add(t); tags.setdefault(t,set()).add("Rx")
        if first<=t+10<=stop: ends.add(t+10); tags.setdefault(t+10,set()).add("expiry")
    rows=[]
    for end in sorted(ends):
        begin=end-10
        window_tx=[t for t in tx if begin<t<=end]
        if mature:
            eligible=[t for t in window_tx if t+DELTA<=end+1e-12]
            n=len(eligible)
            num=sum(1 for t in eligible if rxmap.get(round(t,9),math.inf)<=end+1e-12)
        else:
            n=len(window_tx)
            num=sum(1 for rt in rxtimes if begin<rt<=end)
        ratio=num/n if n else math.nan
        passed=(n>0 and ratio>=threshold)
        # A packet is in-flight in this window if known to arrive after evaluation,
        # or still inside one full packet-interval maturity grace.
        inflight=sum(1 for t in window_tx if rxmap.get(round(t,9),math.inf)>end+1e-12 or end-t<DELTA-1e-12)
        rows.append({"evaluation_s":end,"event_type":"+".join(sorted(tags.get(end,{"expiry"}))),
                     "numerator":num,"denominator":n,"ratio":ratio,"pass":passed,
                     "window_start_s":begin,"inflight_window_packets":inflight})
    # A3 suffix rule: earliest evaluation in the final contiguous passing suffix.
    conv=math.nan; suffix=True
    for row in reversed(rows):
        suffix=suffix and row["pass"]
        if suffix: conv=row["evaluation_s"]
    return conv,rows


def one_run_detector(run_id: str, protocol: str):
    d=RUNS/run_id
    flows,tx,rxmap=load_b_packet_data(d,protocol)
    _,original=detector_evals(tx,rxmap,STOP_B,False,.99)
    conv_orig,_=detector_evals(tx,rxmap,STOP_B,False,.99)
    conv_corr,ecorr=detector_evals(tx,rxmap,STOP_B,True,.99)
    conv95,e95=detector_evals(tx,rxmap,STOP_B,True,.95)
    conv90,e90=detector_evals(tx,rxmap,STOP_B,True,.90)
    rxkeys=set(rxmap); losses=[t for t in tx if round(t,9) not in rxkeys]
    last_loss=max(losses) if losses else math.nan
    # Identity test for terminal probe TX and its actual one-way delay.
    last_tx=max(tx); last_rx=rxmap.get(round(last_tx,9),math.nan)
    saved=float(flows[0]["probe_convergence_s"])
    identity=(last_tx+(last_rx-last_tx)) if math.isfinite(last_rx) else math.nan
    idres=saved-identity if math.isfinite(identity) else math.nan
    def convstr(v): return f"{v:.9f}" if math.isfinite(v) else "nan"
    failures=[dict(x) for x in original if not x["pass"]]
    last_fail=failures[-1] if failures else None
    # Include last ten original evaluations, and all failing ones separately.
    rows=original[-10:]
    last10_failure_count=sum(row["pass"] is False for row in rows)
    for row in rows:
        row["run_id"]=run_id; row["protocol"]=protocol
        row["evaluation_s"]=f"{row['evaluation_s']:.9f}"
        row["window_start_s"]=f"{row['window_start_s']:.9f}"
        row["ratio"]=f"{row['ratio']:.9f}" if math.isfinite(row["ratio"]) else "nan"
        row["pass"]=str(row["pass"]).lower()
    summary={"run_id":run_id,"protocol":protocol,"saved_convergence_s":flows[0]["probe_convergence_s"],
             "replayed_original_s":convstr(conv_orig),"corrected_original_matured_delta_s":convstr(conv_corr),
             "candidate_0_95_matured_s":convstr(conv95),"candidate_0_90_matured_s":convstr(conv90),
             "last_probe_tx_s":f"{last_tx:.9f}","last_probe_tx_rx_s":convstr(last_rx),
             "last_probe_tx_delay_s":convstr(last_rx-last_tx) if math.isfinite(last_rx) else "unreceived",
             "convergence_minus_last_probe_rx_s":f"{saved-last_rx:.12g}" if math.isfinite(last_rx) else "not_defined",
             "convergence_identity_residual_s":f"{idres:.12g}" if math.isfinite(idres) else "not_defined",
             "last_probe_loss_tx_s":f"{last_loss:.9f}" if math.isfinite(last_loss) else "none",
             "loss_count":len(losses),"last10_original_evaluations":10,
             "last10_failures":last10_failure_count,
             "final_failing_inflight_counts":";".join(str(x["inflight_window_packets"]) for x in original[-10:] if not x["pass"]),
             "last_eval_s":f"{float(original[-1]['evaluation_s']):.9f}",
             "last_failing_eval_s":f"{last_fail['evaluation_s']:.9f}" if last_fail else "none",
             "last_failing_eval_type":last_fail["event_type"] if last_fail else "none",
             "last_failing_eval_inflight":last_fail["inflight_window_packets"] if last_fail else 0,
             "failures_after_last_loss_plus_10s":sum(x["evaluation_s"]>last_loss+10 for x in failures) if math.isfinite(last_loss) else "unknown"}
    mature_rows=[]
    for method,allrows in (("corrected_original_0.99",ecorr),("candidate_0.95",e95),("candidate_0.90",e90)):
        for row in allrows[-10:]:
            mature_rows.append({"run_id":run_id,"protocol":protocol,"definition":method,
                                "evaluation_s":f"{row['evaluation_s']:.9f}","event_type":row["event_type"],
                                "numerator":row["numerator"],"denominator":row["denominator"],
                                "ratio":f"{row['ratio']:.9f}" if math.isfinite(row["ratio"]) else "nan",
                                "pass":str(row["pass"]).lower(),"inflight_window_packets":row["inflight_window_packets"]})
    failure_rows=[]
    for row in failures:
        ev=row["evaluation_s"]
        failure_rows.append({"run_id":run_id,"protocol":protocol,"evaluation_s":f"{ev:.9f}",
                             "event_type":row["event_type"],
                             "numerator":row["numerator"],"denominator":row["denominator"],
                             "ratio":f"{row['ratio']:.9f}" if math.isfinite(row["ratio"]) else "nan",
                             "inflight_window_packets":row["inflight_window_packets"],
                             "last_loss_plus_10_s":f"{last_loss+10:.9f}" if math.isfinite(last_loss) else "nan",
                             "is_after_last_loss_plus_10":str(math.isfinite(last_loss) and ev>last_loss+10).lower()})
    return summary,rows,mature_rows,failure_rows


def synthetic_tests():
    def run(name,tx,rx,stop,expect_original=None):
        rxmap={round(t,9):t for t in rx}
        o,_=detector_evals(tx,rxmap,stop,False,.99)
        c,_=detector_evals(tx,rxmap,stop,True,.99)
        p95,_=detector_evals(tx,rxmap,stop,True,.95)
        p90,_=detector_evals(tx,rxmap,stop,True,.90)
        def s(x): return "nan" if not math.isfinite(x) else f"{x:.9f}"
        return {"case":name,"original_0_99_s":s(o),"corrected_0_99_s":s(c),
                "candidate_0_95_s":s(p95),"candidate_0_90_s":s(p90),
                "expected_original":expect_original or "descriptive","candidate_0_95_gate":"pending"}
    cadence=1.0
    immediate=list(map(float,range(41)))
    delayed=[float(t) for t in range(15,41)]
    never=[float(t) for t in range(0,41,2)]
    out=[run("T3_immediate",immediate,immediate,40,"10.000000000"),
         run("T3_delayed",immediate,delayed,40,"24.000000000"),
         run("T3_never",immediate,never,40,"nan")]
    tx=list(map(float,range(41))); rx=list(map(float,range(40)))
    out.append(run("synthetic_inflight_tail",tx,rx,40))
    tx=[i*DELTA for i in range(0,153)]; rx=[t for i,t in enumerate(tx) if i!=61]
    out.append(run("synthetic_single_random_loss",tx,rx,25))
    expected={"T3_immediate":"10.000000000","T3_delayed":"24.000000000","T3_never":"nan"}
    last_rx={"T3_immediate":40.0,"T3_delayed":40.0,"T3_never":40.0,
             "synthetic_inflight_tail":39.0,"synthetic_single_random_loss":tx[-1]}
    for row in out:
        name=row["case"]; c95=row["candidate_0_95_s"]
        if name in expected:
            row["candidate_0_95_gate"]="pass" if c95==expected[name] else "fail"
        else:
            val=fnum(c95)
            if name=="synthetic_single_random_loss":
                ok=math.isfinite(val) and val<=10.0 and val<last_rx[name]
            else:
                ok=math.isfinite(val) and val<last_rx[name]
            row["candidate_0_95_gate"]="pass" if ok else "fail"
    return out


def v1_negative_controls():
    controls=[]
    base=HERE/"negative_control"; base.mkdir(exist_ok=True)
    for protocol in ("olsr","aodv","dsdv"):
        run=RUNS/f"40B_geodesic_N42_r1_{protocol}_validation"
        original=run/f"forward_events_{protocol}.csv"
        dst=base/protocol/f"forward_events_{protocol}.csv"; dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,dst)
        rows=read_csv(dst); flows=[r for r in read_csv(run/"flows.csv") if r["protocol"]==protocol]
        first=next(r for r in rows if r["counts_as_forward"]=="1")
        src=int(first["source"].rsplit(".",1)[1])-1
        first["node_id"]=str(src)  # force source->source in reconstructed path
        write_csv(dst,rows,list(rows[0]))
        # Apply the path-level V1 clauses to the corrupted copied forward log.
        key=round(float(first["app_timestamp_s"]),9)
        matching=[r for r in rows if r["counts_as_forward"]=="1" and round(float(r["app_timestamp_s"]),9)==key]
        flow=next(f for f in flows if f["source"]==f"Node_{src}" and f["destination"]==f"Node_{int(first['destination'].rsplit('.',1)[1])-1}")
        path=[src]+[int(r["node_id"]) for r in sorted(matching,key=lambda r:float(r["time_s"]))]+[int(flow["destination"].split("_")[1])]
        consecutive=all(a!=b for a,b in zip(path,path[1:]))
        controls.append({"protocol":protocol,"copied_log":dst.relative_to(HERE).as_posix(),
                         "corrupted_event_timestamp_s":first["app_timestamp_s"],"corruption":"forwarder node changed to source node",
                         "reconstructed_path":">".join(map(str,path)),"V1_path_clause_pass":str(consecutive).lower(),
                         "V1_negative_control_result":"FAIL_EXPECTED" if not consecutive else "FAIL_NOT_DETECTED"})
    return controls


def projections():
    # Pilot process-wall times. Per-node flow counts use C++ llround semantics.
    pilot={"aodv":662.068669,"dsdv":869.164999}
    dsdv_hi=2284.32516
    n1,n10=130,1304
    slope=(dsdv_hi-pilot["dsdv"])/(n10-n1) # strong cross-role linear-slope assumption
    def llround(x): return math.floor(x+0.5)
    Ns=(42,92,162); roles=(.25,.5,1.0); fams=5
    table=[]; totals={"aodv":0.0,"dsdv":0.0,"olsr_aodv_bound":0.0,"olsr_dsdv_bound":0.0}
    records=[]
    for n in Ns:
        scale=(n/162)**2*(180+120)/240
        for kappa in roles:
            count=llround(kappa*n)
            for proto in ("aodv","dsdv"):
                base=pilot[proto]+slope*(count-n1)
                cell=base*scale
                totals[proto]+=fams*cell
                records.append({"N":n,"kappa":kappa,"background_flows":count,"protocol":proto,
                                "scale_factor":scale,"pilot_anchor_s":pilot[proto],"assumed_slope_s_per_flow":slope,
                                "projected_seconds_per_cell":cell})
            for key,anchor in (("olsr_aodv_bound",pilot["aodv"]),("olsr_dsdv_bound",pilot["dsdv"])):
                cell=(anchor+slope*(count-n1))*scale
                totals[key]+=fams*cell
                records.append({"N":n,"kappa":kappa,"background_flows":count,"protocol":key,
                                "scale_factor":scale,"pilot_anchor_s":anchor,"assumed_slope_s_per_flow":slope,
                                "projected_seconds_per_cell":cell})
    combined={"all_protocols_olsr_aodv_bound":totals["olsr_aodv_bound"]+totals["aodv"]+totals["dsdv"],
              "all_protocols_olsr_dsdv_bound":totals["olsr_dsdv_bound"]+totals["aodv"]+totals["dsdv"]}
    totals.update(combined)
    for name,total in totals.items():
        table.append({"projection_case":name,"serial_total_s":total,"serial_total_h":total/3600,
                      "ideal_k1_h":total/3600,"ideal_k2_h":total/7200,"ideal_k4_h":total/14400,
                      "ideal_k8_h":total/28800,"vs_24h":"UNDER" if total<=86400 else "OVER"})
    write_csv(HERE/"projection_by_cell.csv",records)
    write_csv(HERE/"projection_totals.csv",table)
    countrows=[{"N":n,"kappa":k,"background_flows":llround(k*n)} for n in Ns for k in roles]
    write_csv(HERE/"per_node_flow_counts.csv",countrows)
    return table,records,countrows,{"dsdv_slope_s_per_background_flow_assumed":slope,"formula":"Tpilot + slope*(n_bg-130), then *(N/162)^2*((180+120)/240); five families per size, 3 roles"}


def main():
    controls=v1_negative_controls()
    all_s=[]; all_w=[]; all_m=[]; all_f=[]
    for rid,p in (("40B_geodesic_N42_r1_olsr_validation","olsr"),
                  ("40B_geodesic_N42_r1_aodv_validation","aodv"),
                  ("40B_geodesic_N42_r1_dsdv_validation","dsdv")):
        s,w,m,f=one_run_detector(rid,p); all_s.append(s); all_w.extend(w); all_m.extend(m); all_f.extend(f)
    synth=synthetic_tests(); proj,cellcounts,flowcounts,assump=projections()
    comparisons=[]
    for s in all_s: comparisons.append({**s,"timing_status":"packet logs available"})
    for rid,p in (("40A_geodesic_N162_r1_aodv_phi1","aodv"),
                  ("40A_geodesic_N162_r1_dsdv_phi1","dsdv"),
                  ("40A_geodesic_N162_r1_dsdv_phi10","dsdv")):
        fr=next(r for r in read_csv(RUNS/rid/"flows.csv") if r["protocol"]==p and r["is_probe"]=="1")
        offered=int(fr["offered_packets"]); lasttx=.1+(offered-1)*DELTA; conv=fnum(fr["probe_convergence_s"])
        comparisons.append({"run_id":rid,"protocol":p,"saved_convergence_s":fr["probe_convergence_s"],
             "replayed_original_s":"unavailable_no_packet_timing_log","corrected_original_matured_delta_s":"unavailable",
             "candidate_0_95_matured_s":"unavailable","candidate_0_90_matured_s":"unavailable",
             "last_probe_tx_s":f"{lasttx:.9f}","last_probe_tx_rx_s":"unavailable",
             "last_probe_tx_delay_s":"unavailable","convergence_minus_last_probe_rx_s":"unavailable",
             "convergence_identity_residual_s":"unverifiable_no_last_packet_delay",
             "saved_minus_last_tx_s":f"{conv-lasttx:.9f}" if math.isfinite(conv) else "nan",
             "last_probe_loss_tx_s":"unavailable","loss_count":"unavailable",
             "last10_original_evaluations":"unavailable","last10_failures":"unavailable",
             "final_failing_inflight_counts":"unavailable","last_eval_s":"unavailable",
             "last_failing_eval_s":"unavailable","last_failing_eval_inflight":"unavailable",
             "timing_status":"no packet-timing file; last-Rx identity cannot be independently checked"})
    write_csv(HERE/"v1_negative_controls.csv",controls)
    write_csv(HERE/"detector_comparison_six_runs.csv",comparisons)
    write_csv(HERE/"detector_validation_runs.csv",all_s)
    write_csv(HERE/"detector_last10_original.csv",all_w)
    write_csv(HERE/"detector_last10_matured.csv",all_m)
    write_csv(HERE/"detector_all_failures.csv",all_f)
    write_csv(HERE/"detector_synthetic_tests.csv",synth)
    (HERE/"analysis_summary.json").write_text(json.dumps({"negative_controls":controls,"detector_runs":all_s,"all_six_comparison":comparisons,"all_detector_failures":all_f,
        "synthetic_tests":synth,"projection_totals":proj,"assumptions":assump,
        "A4A_packet_timing_availability":"missing; no packets_<protocol>.csv / per-packet timing file in successful pilot directories"},indent=2)+"\n",encoding="utf-8")
    write_manifests()
    print(json.dumps({"controls":controls,"detector":all_s,"synthetic":synth,"projections":proj,"assumptions":assump},indent=2))

if __name__=="__main__": main()
