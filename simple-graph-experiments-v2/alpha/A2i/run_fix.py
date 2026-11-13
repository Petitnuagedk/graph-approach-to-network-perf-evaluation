#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, time, traceback
from pathlib import Path
import run_diagnosis as base

HERE=Path(__file__).resolve().parent
RESULTS=HERE/'results_fix'
SOURCE=HERE/'src'

def run_one(p,m,seed):
 out=RESULTS/f'disjoint_p{p:.1f}_m{m}_seed{seed}'; out.mkdir(parents=True,exist_ok=True)
 cfg={'p_edge':p,'pair_count':m,'seed':seed,'budgets':list(base.BUDGETS),'timeout_seconds':base.TIMEOUT,'source_sha256':base.sha(SOURCE/'yadygaga'/'frameGenerator.py'),'input_sha256':base.sha(base.GRAPH),'preregistration_sha256':base.sha(base.PREREG)}
 base.writej(out/'config.json',cfg)
 try:
  sys.path.insert(0,str(SOURCE))
  from yadygaga.frameGenerator import FrameGenerator
  from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
  from yadygaga.dynaGraph import MPCDynamicGraph
  graph=base.readg(); pairs=base.PAIRS[:m]
  tg=MPCTimelineBlockGenerator(base.FRAMES,m,.5,.5,mode='sync',seed=seed,pathPersistency=.75)
  timeline=tg.generate(); requested=[base.status_tuple(x) for x in timeline]
  t=time.perf_counter(); pool=FrameGenerator().generateMPCFramesForTimeline(graph,pairs,requested,p_edge=p,seed=seed+10000,trial_ladder=base.BUDGETS); pool_s=time.perf_counter()-t
  dg=MPCDynamicGraph(); assembled=dg.buildDynaGraph(timeline,pool,seed=seed+20000,no_double=True,allow_hamming_fallback=True,force=True)
  realized=[]; counts=[0]*m
  for g in assembled:
   st=tuple(__import__('networkx').has_path(g,*pair) for pair in pairs); realized.append(st)
   for i,x in enumerate(st): counts[i]+=int(x)
  per=[]
  for i,pair in enumerate(pairs):
   req=sum(x[i] for x in requested); meas=counts[i]; err=abs(req-meas)/base.FRAMES
   per.append({'pair_index':i,'source':pair[0],'destination':pair[1],'requested_up_frames':req,'measured_up_frames':meas,'absolute_uptime_error':err,'fidelity_pass':err<=.05})
  metrics={'status':'success','p_edge':p,'pair_count':m,'seed':seed,'adaptive_budget':pool['adaptive_budget'],'pool_generation_seconds':pool_s,'requested_joint_status_counts':{base.key(k):requested.count(k) for k in set(requested)},'pool_status_counts':{base.key(k):len(v) for k,v in pool['cases'].items()},'realized_joint_status_counts':{base.key(k):realized.count(k) for k in set(realized)},'sequence_divergence_frames':sum(a!=b for a,b in zip(requested,realized)),'all_pair_fidelity_pass':all(x['fidelity_pass'] for x in per),'per_pair':per,'all_edges_in_skeleton':all(frozenset(e) in {frozenset(x) for x in graph.edges()} for g in assembled for e in g.edges())}
  base.writej(out/'metrics.json',metrics); base.writej(out/'status.json',{'status':'success'})
 except Exception as e:
  base.writej(out/'status.json',{'status':'failed_exception','exception':repr(e),'traceback':traceback.format_exc()})

def main():
 RESULTS.mkdir(exist_ok=True); log=[]
 for p in base.PS:
  for m in (2,4,8):
   for seed in base.SEEDS:
    label=f'disjoint_p{p:.1f}_m{m}_seed{seed}'
    out=RESULTS/label; out.mkdir(parents=True,exist_ok=True)
    try:
     result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--operation',str(out/'operation.json')],cwd=HERE,timeout=base.TIMEOUT,check=False)
     status=json.loads((out/'status.json').read_text()).get('status') if (out/'status.json').exists() else 'failed_missing_status'
     log.append({'label':label,'returncode':result.returncode,'status':status})
    except subprocess.TimeoutExpired:
     base.writej(out/'status.json',{'status':'failed_timeout','timeout_seconds':base.TIMEOUT}); log.append({'label':label,'returncode':'TIMEOUT','status':'failed_timeout'})
 base.writej(RESULTS/'operation_log.json',log)
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser(); ap.add_argument('--operation'); a=ap.parse_args()
 if a.operation:
  c=json.loads(Path(a.operation).read_text()); run_one(c['p_edge'],c['pair_count'],c['seed'])
 else:
  for p in base.PS:
   for m in (2,4,8):
    for seed in base.SEEDS:
     o=RESULTS/f'disjoint_p{p:.1f}_m{m}_seed{seed}'; o.mkdir(parents=True,exist_ok=True); base.writej(o/'operation.json',{'p_edge':p,'pair_count':m,'seed':seed})
  main()
