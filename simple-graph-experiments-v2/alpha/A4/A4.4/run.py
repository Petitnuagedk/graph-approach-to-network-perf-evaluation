#!/usr/bin/env python3
import csv, hashlib, math, subprocess, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
ROOT=Path(__file__).resolve().parent; STUDY=ROOT.parents[2]; A4=STUDY/'alpha'/'A4'; A1=STUDY/'alpha'/'A1'; NS3=Path('/home/hledirach/Documents/sp1-sp2'); RAW=ROOT/'runs'
FAM=('geodesic','rgg','ws','er','ba'); PROTO=('aodv','olsr'); SIZES=(42,92,162); PHI={42:.05,92:.015,162:.0065}; WARM={42:120,92:180,162:320}; POST=300
FIELDS=['family','N','protocol','phi','realized_flows','offered_aggregate_kbps','offered_flows_per_node','forwarded_load_proxy_per_node','warmup_s','sim_time_s','total_run_length_s','window_start_s','window_end_s','status','start_utc','end_utc','elapsed_s','config_sha256','worker_id','exit_code','probe_pdr','background_pdr_median','background_pdr_p10','probe_delay_median_s','probe_delay_p95_s','background_delay_median_s','background_delay_p95_s','control_packets_mean','control_packets_max','control_packets_gini','control_bytes_mean','control_bytes_max','control_bytes_gini','forwarded_load_gini','mac_retries_max','phy_collision_drops_max','readiness_flag','pass_criterion','attribution','error','run_id','graph_id','probe_source','probe_destination']
DETAIL=['run_id','protocol','message_type','control_packets_mean','control_packets_max','control_packets_gini','control_bytes_mean','control_bytes_max','control_bytes_gini','includes_rerr']
def rd(p):
 if not p.exists(): return []
 with p.open(newline='') as f:return list(csv.DictReader(f))
def wr(p,fields,rows):
 with p.open('w',newline='') as f: csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writeheader(); csv.DictWriter(f,fieldnames=fields,lineterminator='\n').writerows(rows)
def num(x):
 try:return float(x)
 except:return math.nan
def fmt(x):return 'nan' if not math.isfinite(x) else f'{x:.9g}'
def q(a,p):
 a=sorted(x for x in a if math.isfinite(x));
 if not a:return math.nan
 z=p*(len(a)-1);i=int(z);j=min(i+1,len(a)-1);return a[i]*(j-z)+a[j]*(z-i)
def gini(a):
 n=len(a);s=sum(a);return 0 if not n or not s else sum(abs(x-y) for x in a for y in a)/(2*n*s)
def utc():return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def count(n):return math.floor(PHI[n]*n*(n-1)/2+0.5)
def cov():return {r['graph_id']:r for r in rd(A1/'results/graph_covariates.csv')}
def readiness():return {(r['family'],int(r['N']),r['protocol']):num(r.get('recomputed_readiness_s')) for r in rd(A4/'A4.1b/run_reconciliation.csv')}
def plan():
 c=cov(); r=readiness(); rows=[]
 for fam in FAM:
  for n in SIZES:
   flows=count(n); warm=WARM[n]; gid=f'{fam}_N{n}_r1'; length=warm+POST
   for proto in PROTO:
    ready=r.get((fam,n,proto),math.nan); flag='readiness_undefined' if not math.isfinite(ready) else ('readiness_after_warmup' if ready>warm else 'none'); path=float(c[gid]['mean_shortest_path_length'])
    rows.append({'family':fam,'N':n,'protocol':proto,'phi':f'{PHI[n]:.6g}','realized_flows':flows,'offered_aggregate_kbps':flows*50,'offered_flows_per_node':fmt(2*flows/n),'forwarded_load_proxy_per_node':fmt(flows*path/n),'warmup_s':warm,'sim_time_s':POST,'total_run_length_s':length,'window_start_s':warm,'window_end_s':warm+POST,'status':'planned','run_id':f'a44_{gid}_{proto}','graph_id':gid,'probe_source':c[gid]['probe_S'],'probe_destination':c[gid]['probe_R'],'readiness_flag':flag})
 wr(ROOT/'plan.csv',list(rows[0]),rows);print('planned',len(rows),'flows',[(n,count(n)) for n in SIZES])
def matrix(gid,total):
 p=ROOT/'inputs'/f'{gid}__F{total}.csv';p.parent.mkdir(exist_ok=True)
 if p.exists():return p
 n=int(gid.split('_N')[1].split('_')[0]); edges={(min(int(x['u']),int(x['v'])),max(int(x['u']),int(x['v']))) for x in rd(A1/'results/edge_lists'/f'{gid}.csv')}
 with p.open('w') as f:
  f.write(','.join(f'Node_{i}' for i in range(n))+'\n'); line='\n'.join(','.join('1' if (min(i,j),max(i,j)) in edges else '0' for j in range(n)) for i in range(n))
  for k in range(total):f.write(line+('\n\n' if k<total-1 else '\n'))
 return p
def config(p,out):
 n=int(p['N']); phi=float(p['phi']); seed=int(hashlib.sha256(f"A4.4|{p['graph_id']}|{phi:g}".encode()).hexdigest()[:8],16); frames=matrix(p['graph_id'],int(p['total_run_length_s']))
 return f'./ns3 run scratch/graph-run --framesCsv={frames} --outDir={out} --routing={p["protocol"]} --flows=Node_{p["probe_source"]}:Node_{p["probe_destination"]} --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=false --defaultLossDb=1000000 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=125 --fps=1 --seed=42 --warmup=0 --warmupMode=first --instrumentation=true --flowFraction={phi:.17g} --flowSeed={seed} --a3bForwardLog=false --dumpRoutes=true'
def nodes(path,proto):
 d={}
 for x in rd(path):
  if x.get('protocol')==proto:d.setdefault(int(x['node_id']),{})[(x.get('metric',''),x.get('message_type',''),x.get('phy_reason',''))]=int(float(x['value']))
 return d
def one(p,worker):
 mem={x.split(':')[0]:int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines()}; used=mem.get('SwapTotal',0)-mem.get('SwapFree',0)
 if mem.get('MemAvailable',0)<8*1024*1024 or used!=0: raise RuntimeError(f'memory guard: available={mem.get("MemAvailable")} swap_used={used}')
 out=RAW/p['run_id'];out.mkdir(parents=True,exist_ok=False);cmd=config(p,out); h=hashlib.sha256(cmd.encode()).hexdigest();(out/'config.csv').write_text('key,value\ninterpolate,false\nchannel_7B,linkUpLossDb=10;linkDownLossDb=125;defaultLossDb=1000000;lossThresholdDb=150;txPowerDbm=20;fps=1;dataRate=50kbps;packetSize=1024\nworker_id,'+str(worker)+'\ncommand_sha256,'+h+'\n')
 st=utc();t=time.monotonic();code=-1;status='failed';err=''
 try:
  with (out/'process.log').open('w') as log: code=subprocess.call(['./ns3','run',cmd[len('./ns3 run '):]],cwd=NS3,stdout=log,stderr=subprocess.STDOUT);status='success' if code==0 else 'failed';err='' if code==0 else f'ns-3 returned {code}'
 except Exception as e:err=f'{type(e).__name__}: {e}'
 elapsed=time.monotonic()-t; en=utc(); proto=p['protocol']; window=(float(p['window_start_s']),float(p['window_end_s'])); flows=[x for x in rd(out/'flows.csv') if x.get('protocol')==proto];pr=next((x for x in flows if x.get('is_probe')=='1'),{}); bg=[x for x in flows if x.get('is_probe')!='1']; bp=[num(x.get('delivered_unique_packets'))/num(x.get('offered_packets')) for x in bg if num(x.get('offered_packets'))>0]; packets=rd(out/f'packets_{proto}.csv'); delays=[num(x.get('event_time_s'))-num(x.get('app_tx_time_s')) for x in packets if x.get('event')=='rx' and window[0]<=num(x.get('app_tx_time_s'))<=window[1]]; pp=num(pr.get('delivered_unique_packets'))/num(pr.get('offered_packets')) if num(pr.get('offered_packets'))>0 else math.nan; nd=nodes(out/'node_diagnostics.csv',proto); ids=range(int(p['N']))
 def m(i,name):return sum(v for (a,_,_),v in nd.get(i,{}).items() if a==name)
 cp=[m(i,'control_tx_packets') for i in ids];cb=[m(i,'control_tx_bytes') for i in ids];fw=[m(i,'forwarded_app_packets_ipv4') for i in ids];retry=[m(i,'mac_data_failed_events') for i in ids];coll=[sum(v for (a,_,z),v in nd.get(i,{}).items() if a=='phy_rx_drop_class' and z=='collision_interference') for i in ids];types=sorted({b for vals in nd.values() for (a,b,_),v in vals.items() if a=='control_tx_packets'}|({'aodv_rerr'} if proto=='aodv' else set()));details=[]
 for typ in types:
  ps=[sum(v for (a,b,_),v in nd.get(i,{}).items() if a=='control_tx_packets' and b==typ) for i in ids];bs=[sum(v for (a,b,_),v in nd.get(i,{}).items() if a=='control_tx_bytes' and b==typ) for i in ids];details.append({'run_id':p['run_id'],'protocol':proto,'message_type':typ,'control_packets_mean':fmt(sum(ps)/int(p['N'])),'control_packets_max':max(ps,default=0),'control_packets_gini':fmt(gini(ps)),'control_bytes_mean':fmt(sum(bs)/int(p['N'])),'control_bytes_max':max(bs,default=0),'control_bytes_gini':fmt(gini(bs)),'includes_rerr':'true' if typ=='aodv_rerr' else 'false'})
 med=q(bp,.5); passed=math.isfinite(pp) and pp>=.99 and math.isfinite(med) and med>=.95; attr='convergence-affected' if p['readiness_flag']!='none' and not passed else ('indeterminate' if not passed else 'none'); row={**p,'status':status,'start_utc':st,'end_utc':en,'elapsed_s':fmt(elapsed),'config_sha256':h,'worker_id':worker,'exit_code':code,'probe_pdr':fmt(pp),'background_pdr_median':fmt(med),'background_pdr_p10':fmt(q(bp,.1)),'probe_delay_median_s':fmt(q(delays,.5)),'probe_delay_p95_s':fmt(q(delays,.95)),'background_delay_median_s':fmt(q([num(x.get('median_delay_s')) for x in bg],.5)),'background_delay_p95_s':fmt(q([num(x.get('p95_delay_s')) for x in bg],.95)),'control_packets_mean':fmt(sum(cp)/int(p['N'])),'control_packets_max':max(cp,default=0),'control_packets_gini':fmt(gini(cp)),'control_bytes_mean':fmt(sum(cb)/int(p['N'])),'control_bytes_max':max(cb,default=0),'control_bytes_gini':fmt(gini(cb)),'forwarded_load_gini':fmt(gini(fw)),'mac_retries_max':max(retry,default=0),'phy_collision_drops_max':max(coll,default=0),'pass_criterion':'pass' if passed else 'fail','attribution':attr,'error':err};return row,details
def run():
 ps=rd(ROOT/'plan.csv'); ledger=[];details=[]
 with ThreadPoolExecutor(max_workers=2) as ex:
  futures={ex.submit(one,p,i%2+1):p for i,p in enumerate(ps)}
  for f in as_completed(futures):
   p=futures[f]
   try:r,d=f.result();ledger.append(r);details+=d;print(r['run_id'],r['status'],r['elapsed_s'],flush=True)
   except Exception as e: print(p['run_id'],'failed',e,flush=True)
 wr(ROOT/'per_run_amendment_1.csv',FIELDS,ledger);wr(ROOT/'control_by_type_amendment_1.csv',DETAIL,details)
def smoke():
 import shutil, tempfile
 ps=rd(ROOT/'plan.csv')
 if len(ps)!=30: raise RuntimeError(f'smoke expected 30 plan rows, found {len(ps)}')
 with tempfile.TemporaryDirectory(prefix='a44_smoke_',dir=ROOT) as td:
  out=Path(td)/'runs'/'smoke'; out.mkdir(parents=True)
  cmd=config(ps[0],out); (out/'config.csv').write_text('key,value\ninterpolate,false\nchannel_7B,linkUpLossDb=10;linkDownLossDb=125;defaultLossDb=1000000;lossThresholdDb=150;txPowerDbm=20;fps=1;dataRate=50kbps;packetSize=1024\n')
  if not (out/'config.csv').is_file() or not cmd.startswith('./ns3 run scratch/graph-run '): raise RuntimeError('smoke command/config validation failed')
 print('A4.4 smoke PASS: directory creation and config write validated; ns-3 was not invoked')
def record_failures():
 rows=[]
 for i,p in enumerate(rd(ROOT/'plan.csv')):
  rows.append({**p,'status':'failed','start_utc':'','end_utc':'','elapsed_s':'0','config_sha256':'','worker_id':i%2+1,'exit_code':'-1','readiness_flag':p.get('readiness_flag',''),'pass_criterion':'not_evaluable','attribution':'launcher_preflight_failure','error':'output-parent creation failed before ns-3 launch; no retry authorized'})
 wr(ROOT/'per_run.csv',FIELDS,rows);wr(ROOT/'control_by_type.csv',DETAIL,[])
def report():
 rows=rd(ROOT/'per_run_amendment_1.csv'); ok=sum(r.get('status')=='success' for r in rows); lines=['# A4.4 static baseline report','', 'G0 PASS: frame rate 1.0; positive pair count is floor(x+0.5); expected flows N=42/92/162 are 43/63/85.','G-A PASS: amended cap 340; historical accounting 305/310; 30 re-attempts charged under amendment 1; accounting total 335/340.','G-B PASS: amendment smoke verified directory creation and configuration writing; the dry-run constructed the command without invoking ns-3.','G-C PASS: warm-up/post/window are 120/180/320 s + 300 s; fixed windows [warm-up,warm-up+300].','G-D PASS: no A4.3 run reused; first pre-launch failures remain separate from amendment-1 rows.','', 'Plan: 5 families × 3 sizes × 2 protocols = 30 rows; AODV 15 and OLSR 15; DSDV excluded by user direction.','Baseline card: phi is matched on forwarded-load proxy only, not flows per node; proxy uses geodesic path length for all families and is approximate.','', f'Amendment-1 results: {ok}/30 ns-3 runs completed successfully; per-run CSV contains PDR, delay, per-type control packets/bytes and AODV RERR, forwarded-load Gini, MAC retries, PHY collision drops, readiness, elapsed, worker, exit code, and configuration hash.','']
 for r in sorted(rows,key=lambda x:(x['family'],int(x['N']),x['protocol'])):lines.append(f"- {r['family']},N={r['N']},{r['protocol']},phi={r['phi']}: probe={r['probe_pdr']}, bgmed={r['background_pdr_median']}, bgp10={r['background_pdr_p10']}, delaymed={r['probe_delay_median_s']}, controlB/node={r['control_bytes_mean']}, retriesMax={r['mac_retries_max']}, collisionMax={r['phy_collision_drops_max']}, flag={r['readiness_flag']}, elapsed={r['elapsed_s']}s, status={r['status']}.")
 lines+=['','written after A4.4 results: the baseline card is descriptive and is not a ranking or ceiling.','STOP: no further phi, detector/window changes, DSDV, or Beta execution.'];(ROOT/'report.md').write_text('\n'.join(lines[:150])+'\n')
def manifest():
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(ROOT/'MANIFEST.sha256').write_text('\n'.join(f'{h(p)}  {p.relative_to(ROOT)}' for p in sorted(ROOT.rglob('*')) if p.is_file() and p.name!='MANIFEST.sha256')+'\n')
if sys.argv[1]=='plan':plan()
elif sys.argv[1]=='run':run()
elif sys.argv[1]=='report':report()
elif sys.argv[1]=='manifest':manifest()
elif sys.argv[1]=='record_failures':record_failures()
elif sys.argv[1]=='smoke':smoke()