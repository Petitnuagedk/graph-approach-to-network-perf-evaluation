#!/usr/bin/env python3
"""Run exactly the authorized A4.0d regression, then gated OLSR canary."""
from __future__ import annotations
import csv, datetime as dt, json, math, os, re, shlex, signal, subprocess, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
A4=HERE.parent
NS3=Path("/home/hledirach/Documents/sp1-sp2")
EXE=NS3/"build/scratch/ns3.46.1-graph-run-default"
RUNS=HERE/"runs"
LEDGER=HERE/"runs.csv"
TIME_FIELDS={"wall_time_s","cpu_time_s","eed_mean_s","oracle_mean_up_run_s","oracle_median_up_run_s",
             "oracle_p90_up_run_s","oracle_up_runs_s","oracle_outage_durations_s",
             "reestablishment_times_s","reestablishment_outage_durations_s"}


def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
def read_csv(path):
    with path.open(newline="",encoding="utf-8") as f: return list(csv.DictReader(f))
def free_guard():
    vals={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k,v,*_=line.replace(":","").split()
        if k in ("MemAvailable","SwapTotal","SwapFree"): vals[k]=int(v)
    available=vals["MemAvailable"]; swap_used=vals["SwapTotal"]-vals["SwapFree"]
    if available < 8*1024*1024 or swap_used > 0:
        raise RuntimeError(f"resource guard blocked launch: MemAvailable={available}kB SwapUsed={swap_used}kB")
    return available,swap_used

def append_row(row):
    fields=list(row)
    exists=LEDGER.exists()
    if exists:
        with LEDGER.open(newline="",encoding="utf-8") as f: fields=next(csv.reader(f))
    with LEDGER.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore",lineterminator="\n")
        if not exists: w.writeheader()
        w.writerow(row)

def execute(run_id, stage, protocol, frames, routing, flows, flow_fraction, flow_seed,
            forward_log, dump_routes, timeout_s):
    out=RUNS/run_id
    if out.exists(): raise RuntimeError(f"refuse existing run ID; no retry: {run_id}")
    available,swap=free_guard()
    out.mkdir(parents=True)
    args=[str(EXE),f"--framesCsv={frames}",f"--outDir={out}",f"--routing={routing}",
          f"--flows={flows}","--dataRate=50kbps","--packetSize=1024","--lossThresholdDb=150",
          "--interpolate=true","--defaultLossDb=1000000","--txPowerDbm=20","--linkUpLossDb=10",
          "--linkDownLossDb=125","--fps=1","--seed=42","--warmup=0","--warmupMode=first",
          "--instrumentation=true",f"--flowFraction={flow_fraction:.17g}",f"--flowSeed={flow_seed}",
          f"--a3bForwardLog={'true' if forward_log else 'false'}",
          f"--dumpRoutes={'true' if dump_routes else 'false'}","--emitControlUnparsed=true"]
    timed=["/usr/bin/time","-v","-o",str(out/"time.txt"),*args]
    (out/"command.txt").write_text(shlex.join(timed)+"\n",encoding="utf-8")
    start_utc=now(); started=time.monotonic(); rc=None; status="failed"; error=""
    with (out/"simulator.log").open("w",encoding="utf-8") as log:
        proc=subprocess.Popen(timed,cwd=NS3,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            rc=proc.wait(timeout=timeout_s); status="success" if rc==0 else "failed"
            if rc!=0: error=f"built executable exited {rc}"
        except subprocess.TimeoutExpired:
            status="timeout"; error=f"hard timeout {timeout_s}s; no retry"
            try: os.killpg(proc.pid,signal.SIGTERM); proc.wait(timeout=5)
            except (ProcessLookupError,subprocess.TimeoutExpired):
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
    wall=time.monotonic()-started; end_utc=now()
    time_text=(out/"time.txt").read_text(errors="replace") if (out/"time.txt").exists() else ""
    m=re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)",time_text)
    rss=int(m.group(1)) if m else ""
    meta={"run_id":run_id,"stage":stage,"protocol":protocol,"k":1,"parallel_start_utc":start_utc,
          "parallel_end_utc":end_utc,"process_wall_s":wall,"peak_rss_kb":rss,
          "resource_guard_available_kb":available,"resource_guard_swap_used_kb":swap,
          "exit_code":rc,"status":status,"error":error,"timeout_s":timeout_s,
          "command":timed,"built_executable":str(EXE)}
    (out/"run_metadata.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    result={"stage":stage,"run_id":run_id,"protocol":protocol,"k":1,"parallel_start_utc":start_utc,
            "parallel_end_utc":end_utc,"status":status,"exit_code":rc,"process_wall_s":f"{wall:.6f}",
            "peak_rss_kb":rss,"timeout_s":timeout_s,"resource_guard_available_kb":available,
            "resource_guard_swap_used_kb":swap,"control_unparsed_packets":"","control_unparsed_bytes":"",
            "probe_pdr":"","background_pdr_median":"","first_delivery_s":"","control_conservation":"",
            "error":error,"output_dir":str(out.relative_to(HERE))}
    if status=="success":
        result.update(parse_result(out,protocol))
    append_row(result)
    return out,result

def parse_result(out,protocol):
    traces=read_csv(out/"trace_replay_results.csv")
    row=next(r for r in traces if r["protocol"]==protocol)
    flows=[r for r in read_csv(out/"flows.csv") if r["protocol"]==protocol]
    probe=next(r for r in flows if r["is_probe"]=="1")
    bg=[r for r in flows if r["is_probe"]!="1"]
    rates=[float(r["delivered_unique_packets"])/float(r["offered_packets"]) for r in bg if int(r["offered_packets"])>0]
    rates.sort(); mid=len(rates)//2
    median=(rates[mid] if len(rates)%2 else (rates[mid-1]+rates[mid])/2) if rates else math.nan
    packets=int(row["control_packets"]); bytes_=int(row["control_bytes"])
    packet_cols=[c for c in row if c.endswith("_packets") and c!="control_packets"]
    byte_cols=[c for c in row if c.endswith("_bytes") and c!="control_bytes"]
    types_p=sum(int(row[c]) for c in packet_cols); types_b=sum(int(row[c]) for c in byte_cols)
    nodes=read_csv(out/"node_diagnostics.csv")
    node_p=sum(int(r["value"]) for r in nodes if r["metric"]=="control_tx_packets")
    node_b=sum(int(r["value"]) for r in nodes if r["metric"]=="control_tx_bytes")
    unp=row.get("control_unparsed_packets",""); unb=row.get("control_unparsed_bytes","")
    conserved=(types_p==packets and types_b==bytes_ and node_p==packets and node_b==bytes_)
    probe_offered=int(probe["offered_packets"]); probe_delivered=int(probe["delivered_unique_packets"])
    return {"control_unparsed_packets":unp,"control_unparsed_bytes":unb,
            "probe_pdr":f"{probe_delivered/probe_offered:.9f}" if probe_offered else "nan",
            "probe_delivered":probe_delivered,"probe_offered":probe_offered,
            "background_pdr_median":f"{median:.9f}" if math.isfinite(median) else "nan",
            "first_delivery_s":probe["first_delivery_s"],"control_conservation":str(conserved).lower(),
            "control_packets":packets,"control_bytes":bytes_,"classified_type_packets":types_p,
            "classified_type_bytes":types_b,"node_type_packets":node_p,"node_type_bytes":node_b,
            "background_flow_count":len(bg)}

def compare_regression(out):
    old=read_csv(A4/"runs/40B_geodesic_N42_r1_olsr_validation/trace_replay_results.csv")
    new=read_csv(out/"trace_replay_results.csv")
    oldrow=next(r for r in old if r["protocol"]=="olsr"); newrow=next(r for r in new if r["protocol"]=="olsr")
    mismatches={k:(oldrow[k],newrow.get(k)) for k in oldrow if k not in TIME_FIELDS and oldrow[k]!=newrow.get(k)}
    required={"control_unparsed_packets","control_unparsed_bytes"}
    present=required.issubset(newrow)
    unparsed_zero=(newrow.get("control_unparsed_packets")=="0" and newrow.get("control_unparsed_bytes")=="0")
    counts=parse_result(out,"olsr")
    passed=(not mismatches and present and counts["control_conservation"]=="true")
    summary={"pass":passed,"non_timing_mismatch_count":len(mismatches),"non_timing_mismatches":mismatches,
             "unparsed_columns_present":present,"unparsed_zero":unparsed_zero,
             "unparsed_packets":newrow.get("control_unparsed_packets"),"unparsed_bytes":newrow.get("control_unparsed_bytes"),
             "control_conservation":counts["control_conservation"],"compared_non_timing_columns":len(oldrow)-len(TIME_FIELDS)}
    (out/"regression_gate.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    if not EXE.is_file() or not os.access(EXE,os.X_OK): raise RuntimeError(f"built executable unavailable: {EXE}")
    frames42=A4/"inputs/geodesic_N42_r1__F240.csv"
    reg,regrow=execute("40D_geodesic_N42_r1_olsr_regression","regression","olsr",frames42,"olsr",
        "Node_0:Node_16",2/861,24681357,True,True,3600)
    gate=compare_regression(reg)
    print("REGRESSION",gate)
    if not gate["pass"]:
        print("Canary not run: regression gate failed; no retry.")
        return
    frames162=A4/"inputs/geodesic_N162_r1__F120.csv"
    can,canrow=execute("40D_geodesic_N162_r1_olsr_phi1_canary","canary","olsr",frames162,"olsr",
        "Node_0:Node_51",0.01,162343213,False,False,3600)
    (can/"canary_summary.json").write_text(json.dumps(canrow,indent=2)+"\n",encoding="utf-8")
    print("CANARY",canrow)

if __name__=="__main__": main()
