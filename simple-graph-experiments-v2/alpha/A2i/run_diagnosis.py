#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, os, random, statistics, subprocess, sys, time, traceback
from pathlib import Path
import networkx as nx

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'src'
GRAPH=HERE/'input'/'er_N92_r1.csv'
RESULTS=HERE/'results_baseline'
PREREG=HERE/'prereg.md'
PAIRS=[(2*j,2*j+1) for j in range(8)]
SEEDS=(11,29,47)
PS=(0.3,0.5,0.7)
BUDGETS=(3000,30000,300000)
FRAMES=120
TIMEOUT=60

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def writej(p,v): Path(p).write_text(json.dumps(v,indent=2,sort_keys=True,default=str)+'\n')
def readg():
 g=nx.Graph(); g.add_nodes_from(range(92))
 with GRAPH.open(newline='') as f:
  for r in csv.DictReader(f): g.add_edge(int(r['u']),int(r['v']))
 return g

def status_tuple(row): return tuple(x is not None for x in row)
def key(t): return '|'.join('1' if x else '0' for x in t)
def known_answer_tests():
 # Hand-built skeleton: pair A=(0,1), B=(2,3), with four exact states.
 skeleton=nx.Graph(); skeleton.add_edges_from([(0,1),(2,3)])
 pairs=[(0,1),(2,3)]
 requested=[(0,0),(1,0),(0,1),(1,1)]
 assembled=[]
 for st in requested:
  g=nx.Graph(); g.add_nodes_from(skeleton.nodes())
  if st[0]: g.add_edge(0,1)
  if st[1]: g.add_edge(2,3)
  assembled.append(g)
 got=[]
 for g in assembled:
  got.append(tuple(nx.has_path(g,*p) for p in pairs))
 assert got==requested, (got,requested)
 assert [sum(s[i] for s in requested)/4 for i in range(2)]==[0.5,0.5]
 always_up=[(1,0)]*4; always_down=[(0,0)]*4
 assert [sum(s[i] for s in always_up)/4 for i in range(2)]==[1.0,0.0]
 # ID-labeled conversion must preserve None/int semantics.
 assert [status_tuple((None,0)),status_tuple((1,None))]==[(False,True),(True,False)]
 return {'status':'pass','four_state_uptimes':[0.5,0.5],'always_up_down_uptimes':[1.0,0.0]}

def run_one(arr,p,m,seed,budget):
 out=RESULTS/f'{arr}_p{p:.1f}_m{m}_seed{seed}_t{budget}'
 out.mkdir(parents=True,exist_ok=True)
 config={'arrangement':arr,'p_edge':p,'pair_count':m,'seed':seed,'budget':budget,'pairs':[list(x) for x in PAIRS[:m]],'frames':FRAMES,'path_life':.5,'stability':.5,'pathPersistency':.75,'source_sha256':{x:sha(SOURCE/'yadygaga'/x) for x in ['frameGenerator.py','timelineBlockGenerator.py','dynaGraph.py']},'input_sha256':sha(GRAPH),'preregistration_sha256':sha(PREREG),'timeout_seconds':TIMEOUT}
 writej(out/'config.json',config)
 try:
  sys.path.insert(0,str(SOURCE))
  from yadygaga.frameGenerator import FrameGenerator
  from yadygaga.timelineBlockGenerator import MPCTimelineBlockGenerator
  from yadygaga.dynaGraph import MPCDynamicGraph
  graph=readg(); pairs=[tuple(x) for x in config['pairs']]
  t0=time.perf_counter(); pool=FrameGenerator().generateMPCFrames(graph,pairs,trials=budget,p_edge=p,seed=seed+10000); pool_s=time.perf_counter()-t0
  tg=MPCTimelineBlockGenerator(FRAMES,m,.5,.5,mode='sync',seed=seed,pathPersistency=.75)
  t1=time.perf_counter(); timeline=tg.generate(); timeline_s=time.perf_counter()-t1
  requested=[status_tuple(x) for x in timeline]
  pool_counts={key(k):len(v) for k,v in pool['cases'].items()}
  t2=time.perf_counter(); dg=MPCDynamicGraph(); assembled=dg.buildDynaGraph(timeline,pool,seed=seed+20000,no_double=True,allow_hamming_fallback=True,force=True); assembly_s=time.perf_counter()-t2
  realized=[]; empty_sub=0; mismatch=0; pair_counts=[0]*m; first_div=None
  pid_path={}; pid_mismatch=0
  for i,g in enumerate(assembled):
   st=tuple(nx.has_path(g,*pair) for pair in pairs); realized.append(st)
   if st!=requested[i] and first_div is None: first_div=i
   if st!=requested[i]: mismatch+=1
   if len(g.edges())==0 and requested[i] != (False,)*m: empty_sub+=1
   for j,pair in enumerate(pairs):
    pair_counts[j]+=int(st[j])
    pid=timeline[i][j]
    if pid is not None:
     try: path=tuple(map(str,nx.shortest_path(g,*pair)))
     except nx.NetworkXNoPath: path=None
     if pid in pid_path and pid_path[pid]!=path: pid_mismatch+=1
     else: pid_path[pid]=path
  pair_rows=[]
  for j,pair in enumerate(pairs):
   req=sum(x[j] for x in requested); meas=pair_counts[j]
   pair_rows.append({'pair_index':j,'source':pair[0],'destination':pair[1],'requested_up_frames':req,'measured_up_frames':meas,'requested_uptime':req/FRAMES,'measured_uptime':meas/FRAMES,'absolute_uptime_error':abs(req-meas)/FRAMES,'fidelity_pass':abs(req-meas)/FRAMES<=.05})
  metrics={'status':'success','arrangement':arr,'p_edge':p,'pair_count':m,'seed':seed,'budget':budget,'pool_generation_seconds':pool_s,'timeline_generation_seconds':timeline_s,'assembly_seconds':assembly_s,'total_operation_seconds':pool_s+timeline_s+assembly_s,'pool_status_counts':pool_counts,'requested_joint_status_counts':{key(k):requested.count(k) for k in set(requested)},'realized_joint_status_counts':{key(k):realized.count(k) for k in set(realized)},'requested_states_with_zero_pool':[key(k) for k in set(requested) if pool_counts.get(key(k),0)==0],'scarce_requested_states':{key(k):pool_counts.get(key(k),0) for k in set(requested) if pool_counts.get(key(k),0)<10},'sequence_divergence_frames':mismatch,'first_divergence_frame':first_div,'empty_graph_substitutions':empty_sub,'pid_path_mismatches':pid_mismatch,'selected_status_mismatch_count':sum(status_tuple(s)!=r for s,r in zip(dg.selected_statuses,requested)),'per_pair':pair_rows,'all_pair_fidelity_pass':all(x['fidelity_pass'] for x in pair_rows),'all_edges_in_skeleton':all(frozenset(e) in {frozenset(x) for x in graph.edges()} for g in assembled for e in g.edges())}
  writej(out/'metrics.json',metrics); writej(out/'timeline.json',{'timeline':timeline,'requested_statuses':[list(x) for x in requested]}); writej(out/'selected.json',{'indices':dg.selected_frame_indices,'statuses':[list(x) for x in dg.selected_statuses]}); writej(out/'output_hash_inputs.json',{'config':sha(out/'config.json'),'timeline':sha(out/'timeline.json'),'selected':sha(out/'selected.json'),'metrics':sha(out/'metrics.json')}); writej(out/'status.json',{'status':'success'})
 except Exception as e:
  writej(out/'status.json',{'status':'failed_exception','exception':repr(e),'traceback':traceback.format_exc()})

def main():
 import argparse
 parser=argparse.ArgumentParser(); parser.add_argument('--operation'); args=parser.parse_args()
 if args.operation:
  cfg=json.loads(Path(args.operation).read_text())
  run_one('disjoint',cfg['p_edge'],cfg['pair_count'],cfg['seed'],cfg['budget'])
  return
 RESULTS.mkdir(exist_ok=True)
 tests=known_answer_tests(); writej(HERE/'known_answer_tests.json',tests)
 if tests['status']!='pass': raise SystemExit('known-answer tests failed')
 log=[]
 for p in PS:
  for budget in BUDGETS:
   for m in (2,4,8):
    for seed in SEEDS:
     label=f'disjoint_p{p:.1f}_m{m}_seed{seed}_t{budget}'
     out=RESULTS/label; out.mkdir(parents=True,exist_ok=True)
     cfg={'p_edge':p,'pair_count':m,'seed':seed,'budget':budget}
     writej(out/'operation_config.json',cfg)
     try:
      result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--operation',str(out/'operation_config.json')],cwd=HERE,timeout=TIMEOUT,check=False)
      status=json.loads((out/'status.json').read_text()).get('status') if (out/'status.json').exists() else 'failed_missing_status'
      log.append({'label':label,'returncode':result.returncode,'status':status})
     except subprocess.TimeoutExpired:
      writej(out/'status.json',{'status':'failed_timeout','timeout_seconds':TIMEOUT}); log.append({'label':label,'returncode':'TIMEOUT','status':'failed_timeout'})
 writej(RESULTS/'operation_log.json',log)
 rows=[]
 for mp in sorted(RESULTS.glob('*/metrics.json')): rows.append(json.loads(mp.read_text()))
 writej(RESULTS/'all_metrics.json',rows)
 print(json.dumps({'completed':len(rows),'logged':len(log),'known_answer':'pass'}))
if __name__=='__main__': main()
