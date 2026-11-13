#!/usr/bin/env python3
"""Once-only corrected AODV phi10 pilot authorized by addendum 3."""
from __future__ import annotations
import csv, hashlib, json, os, signal, subprocess, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
NS3 = Path('/home/hledirach/Documents/sp1-sp2')
A4 = HERE.parents[1]
ADDENDUM_SHA = '9f0ee2c3a57ef40444dcd73d0a0a72e04ed0d5e65c5b529e1d2d5f1d181b1a46'
SOURCE_SHA = 'e8f75e0efa0988ae4e039e2ce04eda3e667128f99b035806057412f03b930b5e'
LIB_SHA = '31eca374d5d519ea348ed500bf9a263ba40cacac259bbd79ac264078f55ca79a'
GRAPH_SOURCE_SHA = '9745439728fd4c5ca5f8667c90abb596e5c6746a81b21b9260d0904f0b63a433'
GRAPH_BINARY_SHA = '4a39073b4b2b1ede65b35452717acf231c664a89db256fed194f8f0b448de74c'
FRAME_SHA = '5c090a758d0ffdb3cc7e6fc4739dbddf4c7d389d7d52594fb1bf90586512795d'
TIMEOUT = 3600

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def guard():
    v={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        f=line.replace(':','').split()
        if f[0] in {'MemAvailable','SwapTotal','SwapFree'}: v[f[0]]=int(f[1])
    avail=v['MemAvailable']; swap=v['SwapTotal']-v['SwapFree']
    return avail >= 8*1024*1024 and swap == 0, avail, swap

def main():
    source=NS3/'src/aodv/model/aodv-routing-protocol.cc'
    lib=NS3/'build/lib/libns3.46.1-aodv-default.so'
    gs=NS3/'scratch/graph-run.cc'; binary=NS3/'build/scratch/ns3.46.1-graph-run-default'
    frames=A4/'inputs/geodesic_N162_r1__F120.csv'
    for p, h, label in [(HERE/'addendum_3.md',ADDENDUM_SHA,'addendum'),(source,SOURCE_SHA,'AODV source'),
        (lib,LIB_SHA,'AODV library'),(gs,GRAPH_SOURCE_SHA,'graph-run source'),(binary,GRAPH_BINARY_SHA,'graph-run binary'),
        (frames,FRAME_SHA,'frame input')]:
        if not p.is_file() or sha(p)!=h: raise SystemExit(f'{label} hash mismatch; refusing pilot')
    out=HERE/'runs/corrected_aodv_phi10'
    ledger=HERE/'corrected_aodv_pilot.csv'
    if out.exists() or ledger.exists(): raise SystemExit('corrected pilot output exists; no retry')
    ok,avail,swap=guard(); out.mkdir(parents=True)
    if not ok:
        with ledger.open('w',newline='') as f:
            w=csv.writer(f); w.writerow(['run_id','status','resource_guard_available_kb','resource_guard_swap_used_kb','error'])
            w.writerow(['corrected_aodv_phi10','resource_guard_blocked',avail,swap,'not launched; no retry'])
        return
    args=[str(binary),f'--framesCsv={frames}',f'--outDir={out}','--routing=aodv','--flows=Node_0:Node_51',
      '--dataRate=50kbps','--packetSize=1024','--lossThresholdDb=150','--interpolate=true','--defaultLossDb=1000000',
      '--txPowerDbm=20','--linkUpLossDb=10','--linkDownLossDb=125','--fps=1','--seed=42','--warmup=0',
      '--warmupMode=first','--instrumentation=true','--flowFraction=0.10000000000000001',
      '--flowSeed=3717987640','--a3bForwardLog=false','--dumpRoutes=false']
    command=['/usr/bin/time','-v','-o',str(out/'time.txt'),*args]
    (out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    t=time.monotonic(); status='failed'; code=None; error=''
    with (out/'ns3.log').open('w') as log:
        proc=subprocess.Popen(command,cwd=NS3,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,text=True)
        try:
            code=proc.wait(timeout=TIMEOUT); status='success' if code==0 else 'failed'
            if code: error=f'simulator returned {code}'
        except subprocess.TimeoutExpired:
            status='timeout'; error=f'exceeded {TIMEOUT}s; no retry'
            try: os.killpg(proc.pid,signal.SIGTERM); proc.wait(timeout=5)
            except (ProcessLookupError,subprocess.TimeoutExpired):
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
    wall=time.monotonic()-t
    tm=(out/'time.txt').read_text(errors='replace') if (out/'time.txt').exists() else ''
    rss=next((x.split(':',1)[1].strip() for x in tm.splitlines() if x.startswith('Maximum resident set size (kbytes):')),'')
    cols=['run_id','status','exit_code','process_wall_s','peak_rss_kb','resource_guard_available_kb','resource_guard_swap_used_kb',
      'addendum_sha256','source_sha256','library_sha256','graph_source_sha256','graph_binary_sha256','frame_sha256','output_dir','error']
    with ledger.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n'); w.writeheader()
        w.writerow(dict(run_id='corrected_aodv_phi10',status=status,exit_code=code,process_wall_s=f'{wall:.9g}',peak_rss_kb=rss,
          resource_guard_available_kb=avail,resource_guard_swap_used_kb=swap,addendum_sha256=ADDENDUM_SHA,source_sha256=SOURCE_SHA,
          library_sha256=LIB_SHA,graph_source_sha256=GRAPH_SOURCE_SHA,graph_binary_sha256=GRAPH_BINARY_SHA,frame_sha256=FRAME_SHA,
          output_dir=str(out.relative_to(HERE)),error=error))
    print(f'corrected_aodv_phi10: {status}, exit={code}, wall={wall:.3f}s',flush=True)
if __name__=='__main__': main()
