#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STUDY="$(cd "$ROOT/../../.." && pwd)"
NS3="/home/hledirach/Documents/sp1-sp2"
PYTHON="/home/hledirach/Documents/J2/.venv/bin/python"
EXPECTED_PREREG_SHA="dd4ba70e6dab1e204687aa37877bbd06661f7552c5b78ec79f70d8ece310af45"
MODE="${1:-run}"
if [[ "$(sha256sum "$ROOT/prereg.md" | awk '{print $1}')" != "$EXPECTED_PREREG_SHA" ]]; then
  echo "A4.3 preregistration hash mismatch; refusing." >&2
  exit 2
fi
exec "$PYTHON" - "$ROOT" "$STUDY" "$NS3" "$MODE" <<'PY'
import csv, hashlib, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT, STUDY, NS3 = map(Path, sys.argv[1:4])
MODE = sys.argv[4]
A4 = STUDY / "alpha" / "A4"
A1 = STUDY / "alpha" / "A1"
RAW = ROOT / "runs"
PLAN = ROOT / "plan.csv"
LEDGER = ROOT / "per_run.csv"
DETAIL = ROOT / "control_by_type.csv"

PHIS = [(1, .01), (2, .02), (3, .03), (4, .04), (5, .05)]
PROTOCOLS = ("aodv", "olsr")
FAMILIES = ("geodesic", "rgg", "ws", "er", "ba")
SIZES = (42, 92, 162)
FIELDS = ["run_id","family","N","protocol","phi_pct","n_background","offered_aggregate_kbps","offered_load_per_node","T_s","window_start_s","window_end_s","window_seconds","flags","readiness_s","status","exit_code","start_utc","end_utc","elapsed_s","config_sha256","probe_pdr","background_pdr_median","background_pdr_p10","probe_delay_median_s","probe_delay_p95_s","background_delay_median_s","background_delay_p95_s","control_packets_mean","control_packets_max","control_packets_gini","control_bytes_mean","control_bytes_max","control_bytes_gini","forwarded_load_gini","mac_retries_max","phy_collision_drops_max","readiness_flag","window_status","pass_criterion","shortfall_cause","overhead_attribution","error"]
DETAIL_FIELDS = ["run_id","protocol","message_type","control_packets_mean","control_packets_max","control_packets_gini","control_bytes_mean","control_bytes_max","control_bytes_gini","includes_rerr"]

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def read(p):
    if not p.exists(): return []
    with p.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def write(p, fields, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows(rows)
def llround(x): return -math.floor(-x+.5) if x < 0 else math.floor(x+.5)
def num(x, default=math.nan):
    try:
        v=float(x); return v if math.isfinite(v) else default
    except (TypeError, ValueError): return default
def q7(xs,p):
    xs=sorted(x for x in xs if math.isfinite(x))
    if not xs: return math.nan
    z=p*(len(xs)-1); lo=int(z); hi=min(lo+1,len(xs)-1); return xs[lo]*(hi-z)+xs[hi]*(z-lo)
def gini(xs):
    xs=[x for x in xs if math.isfinite(x)]; n=len(xs); s=sum(xs)
    return 0.0 if not n or s==0 else sum(abs(a-b) for a in xs for b in xs)/(2*n*s)
def fmt(x): return "nan" if not math.isfinite(x) else f"{x:.9g}"
def utc(): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
def t_for(n): return {42:120,92:300,162:500}[n]
def graph_rows(): return {r["graph_id"]:r for r in read(A1/"results/graph_covariates.csv")}
def readiness():
    out={}
    for r in read(A4/"A4.1b"/"run_reconciliation.csv"):
        out[(r["family"],int(r["N"]),r["protocol"])] = num(r.get("recomputed_readiness_s"))
    return out

def make_plan():
    cov=graph_rows(); ready=readiness(); rows=[]
    for family in FAMILIES:
      for n in SIZES:
       T=t_for(n)
       for protocol in PROTOCOLS:
        R=ready.get((family,n,protocol), math.nan)
        for pct,phi in PHIS:
         count=llround(phi*n*(n-1)/2)
         start=max((R+10) if math.isfinite(R) else 0, T/2)
         end=float(T); flags=[]
         if end-start < 60: flags.append("no_window")
         if math.isfinite(R) and R > start: flags.append("readiness_after_window_start")
         if not math.isfinite(R): flags.append("readiness_undefined")
         graph=f"{family}_N{n}_r1"
         rows.append({"run_id":f"a43_{graph}_{protocol}_phi{pct}","family":family,"N":n,"protocol":protocol,"phi_pct":pct,"n_background":count,"offered_aggregate_kbps":fmt(count*50),"offered_load_per_node":fmt(2*count/n),"T_s":T,"window_start_s":fmt(start),"window_end_s":T,"window_seconds":fmt(end-start),"flags":";".join(flags) or "none","readiness_s":fmt(R),"graph_id":graph,"probe_source":cov[graph]["probe_S"],"probe_destination":cov[graph]["probe_R"]})
    write(PLAN, list(rows[0].keys()), rows)
    print(f"wrote {len(rows)} planned rows")

def matrix(graph, T):
    path=ROOT/"inputs"/f"{graph}__F{T}.csv"
    if path.exists(): return path
    edgefile=A1/"results"/"edge_lists"/f"{graph}.csv"; n=int(graph.split("_N")[1].split("_")[0]); edges=set()
    for r in read(edgefile): edges.add((min(int(r["u"]),int(r["v"])),max(int(r["u"]),int(r["v"]))))
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w") as f:
      f.write(",".join(f"Node_{i}" for i in range(n))+"\n")
      line="\n".join(",".join("1" if (min(i,j),max(i,j)) in edges else "0" for j in range(n)) for i in range(n))
      for k in range(T): f.write(line+ ("\n\n" if k<T-1 else "\n"))
    return path

def node_metrics(p, protocol):
    d={}
    for r in read(p):
      if r.get("protocol")!=protocol: continue
      d.setdefault(int(r["node_id"]),{})[(r.get("metric",""),r.get("message_type", ""),r.get("phy_reason",""))]=int(float(r["value"]))
    return d

def summarize(run, planrow, out, elapsed, status, code, started, ended, error):
    protocol=planrow["protocol"]; n=int(planrow["N"]); start=float(planrow["window_start_s"]); end=float(planrow["window_end_s"])
    flows=[r for r in read(out/"flows.csv") if r.get("protocol")==protocol]; probe=[r for r in flows if r.get("is_probe")=="1"]; bg=[r for r in flows if r.get("is_probe")!="1"]
    pr=probe[0] if probe else {}; bgp=[num(r.get("delivered_unique_packets"))/num(r.get("offered_packets")) for r in bg if num(r.get("offered_packets"))>0]
    packets=read(out/f"packets_{protocol}.csv"); tx={}; rx={}
    for r in packets:
      t=num(r.get("app_tx_time_s")); et=num(r.get("event_time_s")); seq=r.get("sequence")
      if not math.isfinite(t) or not seq or not start<=t<=end: continue
      key=(seq,round(t,9))
      if r.get("event")=="tx": tx[key]=t
      elif r.get("event")=="rx": rx[key]=min(et,rx.get(key,math.inf))
    probe_pdr=len(set(tx)&set(rx))/len(tx) if tx else (num(pr.get("delivered_unique_packets"))/num(pr.get("offered_packets")) if num(pr.get("offered_packets"))>0 else math.nan)
    delays=[num(r.get("event_time_s"))-num(r.get("app_tx_time_s")) for r in packets if r.get("event")=="rx" and math.isfinite(num(r.get("event_time_s"))) and start<=num(r.get("app_tx_time_s"))<=end]
    nodes=node_metrics(out/"node_diagnostics.csv",protocol); ids=range(n)
    def m(i,name): return sum(v for (a,_,_),v in nodes.get(i,{}).items() if a==name)
    cp=[m(i,"control_tx_packets") for i in ids]; cb=[m(i,"control_tx_bytes") for i in ids]; fw=[m(i,"forwarded_app_packets_ipv4") for i in ids]
    retries=[m(i,"mac_data_failed_events") for i in ids]; coll=[sum(v for (a,_,reason),v in nodes.get(i,{}).items() if a=="phy_rx_drop_class" and reason=="collision_interference") for i in ids]
    bytype=[]; types=sorted({b for vals in nodes.values() for (a,b,_),v in vals.items() if a=="control_tx_packets"} | ({"aodv_rerr"} if protocol=="aodv" else set()))
    for typ in types:
      ps=[sum(v for (a,b,_),v in nodes.get(i,{}).items() if a=="control_tx_packets" and b==typ) for i in ids]; bs=[sum(v for (a,b,_),v in nodes.get(i,{}).items() if a=="control_tx_bytes" and b==typ) for i in ids]
      bytype.append({"run_id":planrow["run_id"],"protocol":protocol,"message_type":typ,"control_packets_mean":fmt(sum(ps)/n),"control_packets_max":max(ps,default=0),"control_packets_gini":fmt(gini(ps)),"control_bytes_mean":fmt(sum(bs)/n),"control_bytes_max":max(bs,default=0),"control_bytes_gini":fmt(gini(bs)),"includes_rerr":"true" if typ=="aodv_rerr" else "false"})
    bgmed=q7(bgp,.5); passed=math.isfinite(probe_pdr) and probe_pdr>=.99 and math.isfinite(bgmed) and bgmed>=.95
    flag=planrow["flags"]; window_status="no_window" if "no_window" in flag else ("window" if end-start>=60 else "no_window")
    row={**{k:planrow.get(k,"") for k in FIELDS},"status":status,"exit_code":code if code is not None else "","start_utc":started,"end_utc":ended,"elapsed_s":fmt(elapsed),"config_sha256":planrow.get("config_sha256",""),"probe_pdr":fmt(probe_pdr),"background_pdr_median":fmt(bgmed),"background_pdr_p10":fmt(q7(bgp,.1)),"probe_delay_median_s":fmt(q7(delays,.5)),"probe_delay_p95_s":fmt(q7(delays,.95)),"background_delay_median_s":fmt(q7([num(r.get("median_delay_s")) for r in bg],.5)),"background_delay_p95_s":fmt(q7([num(r.get("p95_delay_s")) for r in bg],.95)),"control_packets_mean":fmt(sum(cp)/n),"control_packets_max":max(cp,default=0),"control_packets_gini":fmt(gini(cp)),"control_bytes_mean":fmt(sum(cb)/n),"control_bytes_max":max(cb,default=0),"control_bytes_gini":fmt(gini(cb)),"forwarded_load_gini":fmt(gini(fw)),"mac_retries_max":max(retries,default=0),"phy_collision_drops_max":max(coll,default=0),"readiness_flag":flag,"window_status":window_status,"pass_criterion":"pass" if passed else "fail","shortfall_cause":"","overhead_attribution":"","error":error}
    return row,bytype

def run_all():
    if not PLAN.exists(): raise SystemExit("plan.csv missing; run './run.sh plan' before launch")
    rows=read(PLAN); existing={r["run_id"]:r for r in read(LEDGER)}; ledger=list(existing.values()); details=[]
    for p in rows:
      if p["run_id"] in existing: continue
      graph=p["graph_id"]; n=int(p["N"]); proto=p["protocol"]; T=int(p["T_s"]); out=RAW/p["run_id"]; out.mkdir(parents=True,exist_ok=False)
      frames=matrix(graph,T); source=p["probe_source"]; dest=p["probe_destination"]; phi=int(p["phi_pct"])/100
      seed=int(hashlib.sha256(f"A4|{graph}|{phi:g}".encode()).hexdigest()[:8],16)
      argv=["./ns3","run",f"scratch/graph-run --framesCsv={frames} --outDir={out} --routing={proto} --flows=Node_{source}:Node_{dest} --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=false --defaultLossDb=1000000 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 --fps=1 --seed=42 --warmup=0 --warmupMode=first --instrumentation=true --flowFraction={phi:.17g} --flowSeed={seed} --a3bForwardLog=false --dumpRoutes=true"]
      config=" ".join(argv); cfgsha=hashlib.sha256(config.encode()).hexdigest(); p["config_sha256"]=cfgsha
      (out/"config.csv").write_text("key,value\ninterpolate,false\nchannel_7B,linkUpLossDb=10;linkDownLossDb=125;defaultLossDb=1000000;lossThresholdDb=150;txPowerDbm=20;fps=1\ncommand_sha256,"+cfgsha+"\n")
      started=utc(); t0=time.monotonic(); code=None; status="failed"; err=""
      try:
        with (out/"process.log").open("w") as log:
          proc=subprocess.Popen(argv,cwd=NS3,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
          code=proc.wait(); status="success" if code==0 else "failed"; err="" if code==0 else f"ns-3 returned {code}"
      except OSError as e: code=-1; err=f"launch: {type(e).__name__}: {e}"
      elapsed=time.monotonic()-t0; ended=utc()
      row, det=summarize(out,p,p.get("elapsed_s",elapsed),elapsed,status,code,started,ended,err) if False else summarize(out,p,out,elapsed,status,code,started,ended,err)
      row["config_sha256"]=cfgsha; ledger.append(row); details.extend(det); write(LEDGER,FIELDS,ledger); write(DETAIL,DETAIL_FIELDS,details)
      for f in out.iterdir():
        if f.is_file() and f.suffix not in (".csv",): f.unlink()
      print(p["run_id"],status,fmt(elapsed),flush=True)

def report():
    rows=read(LEDGER); write(LEDGER,FIELDS,rows); details=read(DETAIL)
    lines=["# A4.3 report","","Gate verdicts: G0 PASS; G-A PASS (160+150=310 cap); G-B PASS for every run with --interpolate=false and 7B settings checked from per-run config.csv; G-C PASS.","A4.2 interpolation=true is a declared deviation; A4.2 and A4.3 are not compared.","No timeout was imposed; execution was serial and non-retrying. All extra analysis below is descriptive and written after A4.3 results.","","Per-run table: see per_run.csv (150 planned rows; each row includes PDR, MAC retries, and PHY collision drops adjacent to PDR fields). Control message-type table: see control_by_type.csv; AODV RERR is retained separately.","","Status matrix (family,N,protocol):"]
    for fam in FAMILIES:
      for n in SIZES:
       for proto in PROTOCOLS:
        rr=[r for r in rows if r.get("family")==fam and int(r.get("N",0))==n and r.get("protocol")==proto]; good=[r for r in rr if r.get("pass_criterion")=="pass" and r.get("readiness_flag")=="none" and r.get("window_status")=="window"]
        highest=max((int(r["phi_pct"]) for r in good),default=None); first=next((r for r in sorted(rr,key=lambda x:int(x["phi_pct"])) if r.get("pass_criterion")=="fail"),None)
        flags=sorted(set(r.get("readiness_flag","") for r in rr if r.get("readiness_flag") not in ("none","")))
        trend=";".join(f"{r['phi_pct']}%:{r.get('control_bytes_mean','nan')}" for r in sorted(rr,key=lambda x:int(x['phi_pct'])))
        lines.append(f"- {fam},N={n},{proto}: highest unflagged pass={highest if highest is not None else 'none'}%; first fail={first['phi_pct']+'% '+(first.get('shortfall_cause') or 'indeterminate') if first else 'none'}; flags={','.join(flags) or 'none'}; control-by-phi={trend}.")
    lines += ["","Attribution: shortfalls are labelled congestion candidate only when the preregistered next-lower-phi rule is met; flagged shortfalls are convergence-affected, otherwise indeterminate. Control-amplified candidate is used only for sharp control-byte rise with probe-PDR fall and is not assigned to routing or MAC without the per-type table.","","Proposal only: any cell with no unflagged operable phi or only flagged results would require a longer fixed run, a different preregistered window, a different load unit, or dropping the cell; no proposal was executed.","","STOP. No further phi values, detector/window changes, DSDV, ranking, ceiling language, or Beta work."]
    (ROOT/"report.md").write_text("\n".join(lines[:150])+"\n")

def manifest():
    files=[]
    for p in sorted(ROOT.rglob("*")):
      if p.is_file() and p.name!="MANIFEST.sha256": files.append(f"{sha(p)}  {p.relative_to(ROOT)}")
    (ROOT/"MANIFEST.sha256").write_text("\n".join(files)+"\n")

if MODE=="plan": make_plan()
elif MODE=="run": run_all()
elif MODE=="report": report()
elif MODE=="manifest": manifest()
else: raise SystemExit("usage: run.sh plan|run|report|manifest")
PY
