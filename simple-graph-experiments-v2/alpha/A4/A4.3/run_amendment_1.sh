#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="/home/hledirach/Documents/J2/.venv/bin/python"
EXPECTED="9f94de2ae486053ada00292d035060af844d33b3a644edaefb9c82a5705a8979"
[[ "$(sha256sum "$ROOT/prereg_amendment_1.md" | awk '{print $1}')" == "$EXPECTED" ]] || { echo 'amendment hash mismatch; refusing'; exit 2; }
exec "$PYTHON" - "$ROOT" "${1:-plan}" <<'PY'
import csv,hashlib,math,os,subprocess,sys,time,datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(sys.argv[1]); MODE=sys.argv[2]; STUDY=ROOT.parents[2]; A4=STUDY/'alpha'/'A4'; A1=STUDY/'alpha'/'A1'; NS3=Path('/home/hledirach/Documents/sp1-sp2'); RAW=ROOT/'runs'
FAM=('geodesic','rgg','ws','er','ba'); PROTO=('aodv','olsr'); PHI=((1,.01),(2,.02),(3,.03),(4,.04),(5,.05)); T=120

def rd(p):
 if not p.exists(): return []
 with p.open(newline='') as f:return list(csv.DictReader(f))
def wr(p,fields,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
def ll(x):return math.floor(x+.5)
def num(x):
 try:return float(x)
 except:return math.nan
def fmt(x):return 'nan' if not math.isfinite(x) else f'{x:.9g}'
def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def gini(a):
 n=len(a);s=sum(a);return 0 if not n or not s else sum(abs(x-y) for x in a for y in a)/(2*n*s)
def q(a,p):
 a=sorted(x for x in a if math.isfinite(x));
 if not a:return math.nan
 z=p*(len(a)-1);i=int(z);j=min(i+1,len(a)-1);return a[i]*(j-z)+a[j]*(z-i)
def ready():
 d={}
 for r in rd(A4/'A4.1b'/'run_reconciliation.csv'):d[(r['family'],int(r['N']),r['protocol'])]=num(r.get('recomputed_readiness_s'))
 return d
def cov():return {r['graph_id']:r for r in rd(A1/'results'/'graph_covariates.csv')}
def reusable(oldr,p):
 if not oldr or oldr.get('status')!='success' or oldr.get('run_id')!=p['run_id']: return False
 for k in ('family','N','protocol','phi_pct','n_background','T_s','window_start_s','window_end_s','window_seconds','flags','readiness_s'):
  if oldr.get(k)!=p.get(k): return False
 cfg=RAW/p['run_id']/'config.csv'
 if not cfg.exists(): return False
 cv={r.get('key'):r.get('value') for r in rd(cfg)}
 return (cv.get('interpolate')=='false' and cv.get('channel_7B')=='linkUpLossDb=10;linkDownLossDb=125;defaultLossDb=1000000;lossThresholdDb=150;txPowerDbm=20;fps=1' and oldr.get('config_sha256')==cv.get('command_sha256'))
def plan():
 old=rd(ROOT/'per_run.csv'); oldmap={r['run_id']:r for r in old}; R=ready(); C=cov(); rows=[]
 for fam in FAM:
  for proto in PROTO:
   for pct,phi in PHI:
    gid=f'{fam}_N42_r1'; rid=f'a43_{gid}_{proto}_phi{pct}'; r=R.get((fam,42,proto),math.nan); start=max(r+10 if math.isfinite(r) else 0,60); flags=[]
    if 120-start<60:flags+=['no_window']
    if math.isfinite(r) and r>start:flags+=['readiness_after_window_start']
    if not math.isfinite(r):flags+=['readiness_undefined']
    count=ll(phi*42*41/2)
    oldr=oldmap.get(rid); reuse='false';decision='new'
    candidate={'run_id':rid,'family':fam,'N':'42','protocol':proto,'phi_pct':str(pct),'n_background':str(count),'T_s':'120','window_start_s':fmt(start),'window_end_s':'120','window_seconds':fmt(120-start),'flags':';'.join(flags) or 'none','readiness_s':fmt(r)}
    if fam=='geodesic' and reusable(oldr,candidate):reuse='true';decision='reuse'
    rows.append({'run_id':rid,'family':fam,'N':42,'protocol':proto,'phi_pct':pct,'n_background':count,'offered_aggregate_kbps':fmt(count*50),'offered_load_per_node':fmt(2*count/42),'T_s':120,'window_start_s':fmt(start),'window_end_s':'120','window_seconds':fmt(120-start),'flags':';'.join(flags) or 'none','readiness_s':fmt(r),'graph_id':gid,'probe_source':C[gid]['probe_S'],'probe_destination':C[gid]['probe_R'],'decision':decision,'reuse':reuse,'prior_run_id':rid})
 wr(ROOT/'plan_amendment_1.csv',list(rows[0]),rows);print('planned',len(rows),'reuse',sum(r['reuse']=='true' for r in rows))
def inventory():
 old=rd(ROOT/'per_run.csv'); rows=[]
 for r in old:
  r=dict(r);r['scope_status']='in_scope_N42' if r.get('N')=='42' else 'out_of_scope_after_correction';rows.append(r)
 # append aborted in-flight, with best available elapsed from process start/end logs
 rid='a43_geodesic_N162_r1_aodv_phi5'; out=RAW/rid; rows.append({'run_id':rid,'N':'162','family':'geodesic','protocol':'aodv','status':'aborted_by_user','exit_code':'-15','elapsed_s':'861.0','scope_status':'out_of_scope_after_correction'})
 wr(ROOT/'attempt_inventory.csv',list(rows[0]),rows)
 print('inventory',len(rows),'attempts; N42',sum(r.get('N')=='42' for r in rows),'out_of_scope',sum(r.get('scope_status')=='out_of_scope_after_correction' for r in rows))
def matrix(gid):
 p=ROOT/'inputs'/f'{gid}__F120.csv'
 if p.exists():return p
 n=42; edges={(min(int(r['u']),int(r['v'])),max(int(r['u']),int(r['v']))) for r in rd(A1/'results'/'edge_lists'/f'{gid}.csv')}
 p.parent.mkdir(exist_ok=True)
 with p.open('w') as f:
  f.write(','.join(f'Node_{i}' for i in range(n))+'\n')
  block='\n'.join(','.join('1' if (min(i,j),max(i,j)) in edges else '0' for j in range(n)) for i in range(n))
  for k in range(120):f.write(block+'\n\n' if k<119 else block+'\n')
 return p
def config(gid,proto,phi,out,src,dst,seed):
 return f'./ns3 run scratch/graph-run --framesCsv={matrix(gid)} --outDir={out} --routing={proto} --flows=Node_{src}:Node_{dst} --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=false --defaultLossDb=1000000 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 --fps=1 --seed=42 --warmup=0 --warmupMode=first --instrumentation=true --flowFraction={phi:.17g} --flowSeed={seed} --a3bForwardLog=false --dumpRoutes=true'
def summarize(p,out,elapsed,status,code,st,en,cfgsha,error):
 proto=p['protocol']; n=42; flows=[r for r in rd(out/'flows.csv') if r.get('protocol')==proto];pr=next((r for r in flows if r.get('is_probe')=='1'),{});bg=[r for r in flows if r.get('is_probe')!='1'];bp=[num(r.get('delivered_unique_packets'))/num(r.get('offered_packets')) for r in bg if num(r.get('offered_packets'))>0]
 nodes={}
 for r in rd(out/'node_diagnostics.csv'):
  if r.get('protocol')==proto:nodes.setdefault(int(r['node_id']),{})[(r.get('metric'),r.get('message_type',''),r.get('phy_reason',''))]=int(float(r['value']))
 def m(i,name):return sum(v for (a,_,_),v in nodes.get(i,{}).items() if a==name)
 cp=[m(i,'control_tx_packets') for i in range(n)];cb=[m(i,'control_tx_bytes') for i in range(n)];fw=[m(i,'forwarded_app_packets_ipv4') for i in range(n)];retry=[m(i,'mac_data_failed_events') for i in range(n)];coll=[sum(v for (a,_,z),v in nodes.get(i,{}).items() if a=='phy_rx_drop_class' and z=='collision_interference') for i in range(n)]
 pp=num(pr.get('delivered_unique_packets'))/num(pr.get('offered_packets')) if num(pr.get('offered_packets'))>0 else math.nan;med=q(bp,.5); passed=math.isfinite(pp) and pp>=.99 and math.isfinite(med) and med>=.95
 row={**p,'status':status,'exit_code':code,'start_utc':st,'end_utc':en,'elapsed_s':fmt(elapsed),'config_sha256':cfgsha,'probe_pdr':fmt(pp),'background_pdr_median':fmt(med),'background_pdr_p10':fmt(q(bp,.1)),'control_packets_mean':fmt(sum(cp)/n),'control_packets_max':max(cp),'control_packets_gini':fmt(gini(cp)),'control_bytes_mean':fmt(sum(cb)/n),'control_bytes_max':max(cb),'control_bytes_gini':fmt(gini(cb)),'forwarded_load_gini':fmt(gini(fw)),'mac_retries_max':max(retry),'phy_collision_drops_max':max(coll),'readiness_flag':p['flags'],'window_status':'window' if 'no_window' not in p['flags'] else 'no_window','pass_criterion':'pass' if passed else 'fail','error':error}
 d=[]
 for typ in sorted({b for vals in nodes.values() for (a,b,_),v in vals.items() if a=='control_tx_packets'}|({'aodv_rerr'} if proto=='aodv' else set())):
  ps=[sum(v for (a,b,_),v in nodes.get(i,{}).items() if a=='control_tx_packets' and b==typ) for i in range(n)];bs=[sum(v for (a,b,_),v in nodes.get(i,{}).items() if a=='control_tx_bytes' and b==typ) for i in range(n)]
  d.append({'run_id':p['run_id'],'protocol':proto,'message_type':typ,'control_packets_mean':fmt(sum(ps)/n),'control_packets_max':max(ps),'control_packets_gini':fmt(gini(ps)),'control_bytes_mean':fmt(sum(bs)/n),'control_bytes_max':max(bs),'control_bytes_gini':fmt(gini(bs)),'includes_rerr':'true' if typ=='aodv_rerr' else 'false'})
 return row,d
def one(p,worker):
 mem={}
 for line in Path('/proc/meminfo').read_text().splitlines():
  k,v,*_=line.replace(':','').split(); mem[k]=int(v)
 if mem.get('MemAvailable',0)<8*1024*1024 or mem.get('SwapTotal',0)-mem.get('SwapFree',0)!=0:
  raise RuntimeError(f"A4.0d memory guard blocked {p['run_id']}: MemAvailable={mem.get('MemAvailable')}kB swap_used={mem.get('SwapTotal',0)-mem.get('SwapFree',0)}kB")
 out=RAW/p['run_id'];out.mkdir(exist_ok=False);gid=p['graph_id'];proto=p['protocol'];phi=int(p['phi_pct'])/100;seed=int(hashlib.sha256(f'A4|{gid}|{phi:g}'.encode()).hexdigest()[:8],16);cmd=config(gid,proto,phi,out,p['probe_source'],p['probe_destination'],seed);h=sha_bytes(cmd.encode());(out/'config.csv').write_text('key,value\ninterpolate,false\nchannel_7B,linkUpLossDb=10;linkDownLossDb=125;defaultLossDb=1000000;lossThresholdDb=150;txPowerDbm=20;fps=1;dataRate=50kbps;packetSize=1024\nworker_id,'+str(worker)+'\ncommand_sha256,'+h+'\n');st=utc();t=time.monotonic();code=-1;status='failed';err=''
 try:
  with (out/'process.log').open('w') as log:code=subprocess.call(['./ns3','run',cmd[len('./ns3 run '):]],cwd=NS3,stdout=log,stderr=subprocess.STDOUT);status='success' if code==0 else 'failed';err='' if code==0 else f'ns-3 returned {code}'
 except Exception as e:err=f'{type(e).__name__}: {e}'
 en=utc();elapsed=time.monotonic()-t
 return summarize(p,out,elapsed,status,code,st,en,h,err)
def run():
 ps=rd(ROOT/'plan_amendment_1.csv'); old=rd(ROOT/'per_run.csv'); oldm={r['run_id']:r for r in old}; ledger=[];details=[]
 for p in ps:
  if p['reuse']=='true':
   r=dict(oldm[p['run_id']]);r.update(p);r['status']='reused';r['scope_status']='reused_prior_N42';ledger.append(r)
 todo=[p for p in ps if p['reuse']!='true'];
 with ThreadPoolExecutor(max_workers=2) as ex:
  fut={ex.submit(one,p,i%2+1):p for i,p in enumerate(todo)}
  for f in as_completed(fut):
   r,d=f.result();ledger.append(r);details+=d;print(r['run_id'],r['status'],r['elapsed_s'],flush=True)
 fields=list(ledger[0]);wr(ROOT/'per_run_amendment_1.csv',fields,ledger);wr(ROOT/'control_by_type_amendment_1.csv',list(details[0]) if details else ['run_id'],details)

def report():
 rows=rd(ROOT/'per_run_amendment_1.csv');lines=['# A4.3 correction report','',f'G0 PASS; G-B PASS for amended runs; G-C PASS (T=120 s).','Abort: geodesic N=162 AODV phi=5% recorded in attempt_inventory.csv as aborted_by_user; elapsed and exit code retained.','Budget: before correction 160; prior A4.3 attempts 25; reused 10; new 40; after correction 225/310. N=92/N=162 are out of scope after correction, not verdicts.','', 'Per-run N=42 table: see per_run_amendment_1.csv; MAC retries and PHY collision drops are in every PDR row. Control message-type bytes and AODV RERR are in control_by_type_amendment_1.csv.','Plots: the A4.2-style N=42 plot set is in plots_amendment_1/; N=92/N=162 plots are intentionally omitted.','', 'Status matrix:']
 for fam in FAM:
  for proto in PROTO:
   rr=[r for r in rows if r.get('family')==fam and r.get('protocol')==proto];good=[r for r in rr if r.get('pass_criterion')=='pass' and r.get('readiness_flag')=='none'];trend=';'.join(f"{r['phi_pct']}%:{r.get('control_bytes_mean','nan')}" for r in sorted(rr,key=lambda x:int(x['phi_pct'])));lines.append(f'- {fam},{proto}: unflagged pass cells={len(good)}/5; control-by-phi={trend}; shortfalls descriptive only.')
 lines+=['','Attribution and overhead labels follow the frozen A4.3 rules; extra analysis is written after A4.3 results.','Decisions (maximum 5): retain the N=42 results; defer N=92/N=162; do not compare with A4.2 interpolation-on results; retain per-type control/RERR reporting; stop.','STOP: no further phi, window/detector changes, DSDV, or Beta work.'];(ROOT/'report_amendment_1.md').write_text('\n'.join(lines[:150])+'\n')
def manifest():
 def hs(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 lines=[]
 for p in sorted(ROOT.rglob('*')):
  if p.is_file() and p.name!='MANIFEST.sha256':lines.append(f'{hs(p)}  {p.relative_to(ROOT)}')
 (ROOT/'MANIFEST.sha256').write_text('\n'.join(lines)+'\n')
if MODE=='plan':plan()
elif MODE=='inventory':inventory()
elif MODE=='run':run()
elif MODE=='report':report()
elif MODE=='manifest':manifest()
else:raise SystemExit('plan|inventory|run|report|manifest')
PY
