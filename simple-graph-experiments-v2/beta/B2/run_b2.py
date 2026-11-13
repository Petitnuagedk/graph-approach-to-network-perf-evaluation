#!/usr/bin/env python3
import csv, hashlib, json, math, sys
from pathlib import Path
import networkx as nx

ROOT=Path(__file__).resolve().parents[2]; A1=ROOT/'alpha'/'A1'/'results'; PIN=ROOT/'beta'/'B0'/'pinned_A0R2_5a497f5'
sys.path.insert(0,str(PIN)); from yadygaga.frameGenerator import FrameGenerator
from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
from yadygaga.dynaGraph import SPCDynamicGraph

OUT=Path(__file__).resolve().parent; F=300; P=(.3,.5,.7); TRIALS=(3000,10000); POOL_SEEDS=(11,29,47); FAMS=('geodesic','rgg','ws','er','ba')

def csvrows(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))
def graph(gid,n):
 g=nx.Graph();g.add_nodes_from(range(n));
 for r in csvrows(A1/'edge_lists'/f'{gid}.csv'):g.add_edge(int(r['u']),int(r['v']))
 return g
def cov():return {r['graph_id']:r for r in csvrows(A1/'graph_covariates.csv')}
def key(x):return f'{x:.1f}'
def demands(life):return round(F*life),F-round(F*life)
def metrics(frames,s,d,path_ids):
 paths=[]
 for g in frames:
  try:paths.append(tuple(nx.shortest_path(g,s,d)))
  except nx.NetworkXNoPath:paths.append(None)
 connected=[p is not None for p in paths]; pairs=[(a,b) for a,b in zip(paths,paths[1:]) if a is not None and b is not None]
 return {'realized_life':sum(connected)/F,'transitions':sum(a!=b for a,b in zip(connected,connected[1:])),'up_runs':sum(a and not (i and connected[i-1]) for i,a in enumerate(connected)),'path_identity_retention':sum(a==b for a,b in pairs)/len(pairs) if pairs else None,'path_id_retention':sum(a==b for a,b in zip(path_ids,path_ids[1:]) if a is not None and b is not None)/sum(a is not None and b is not None for a,b in zip(path_ids,path_ids[1:])) if any(a is not None and b is not None for a,b in zip(path_ids,path_ids[1:])) else None,'has_alternative_path':len(set(p for p in paths if p is not None))>1}
def main():
 c=cov(); rows=[]; pools={}
 for fam in FAMS:
  gid=f'{fam}_N42_r1'; g=graph(gid,42); s=int(c[gid]['probe_S']);d=int(c[gid]['probe_R'])
  for p in P:
   for trials in TRIALS:
    for seed in POOL_SEEDS:
     fg=FrameGenerator();fg.generateSPCFrames(g,s,d,trials=trials,p_edge=p,seed=seed)
     pools[(fam,p,trials,seed)]=(fg.path_up_frames,fg.path_down_frames,s,d)
 for (fam,p,trials,seed),(up,down,s,d) in pools.items():
  for axis,levels in [('life',[.1,.2,.3,.4,.5,.6,.7,.9]),('stability',[.8,1.0]),('persistency',[.1,.2,.3,.4,.5,.6,.7,.8,.9])]:
   for level in levels:
    life=.8;stability=.9;persist=level if axis=='persistency' else 1.0
    if axis=='life':life=level
    if axis=='stability':stability=level
    try:
     tl=SPCTimelineBlockGenerator(F,life,stability,42,pathPersistency=persist,behavior='patched').generate_blocks()
     dg=SPCDynamicGraph().buildDynaGraph(tl,up,down,seed=42)
     m=metrics(dg,s,d,tl['path_ids']); upn=sum(tl['timeline']); dn=F-upn; k=sum(a and not (i and tl['timeline'][i-1]) for i,a in enumerate(tl['timeline']))
     rows.append({'family':fam,'graph_id':f'{fam}_N42_r1','axis':axis,'level':key(level),'p_edge':key(p),'trials':trials,'pool_seed':seed,'timeline_seed':42,'path_life':life,'stability':stability,'persistency':persist,'U':upn,'D':dn,'K':k,'feasibility_status':'feasible','up_pool':sum(map(len,up)),'down_pool':len(down),**m})
    except ValueError as e:
     rows.append({'family':fam,'graph_id':f'{fam}_N42_r1','axis':axis,'level':key(level),'p_edge':key(p),'trials':trials,'pool_seed':seed,'timeline_seed':42,'path_life':life,'stability':stability,'persistency':persist,'U':round(F*life),'D':F-round(F*life),'K':'','feasibility_status':'infeasible_not_run','error':str(e)})
 fields=list(dict.fromkeys(k for r in rows for k in r));
 with (OUT/'results.csv').open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 (OUT/'summary.json').write_text(json.dumps({'status':'complete','rows':len(rows),'pinned_tree':'32b243bc84b587f1782ead0d0ac56382a57425e5','behavior':'patched','families':FAMS,'p_edge':P,'trials':TRIALS,'pool_seeds':POOL_SEEDS},indent=2)+'\n')
 print(f'B2 complete: {len(rows)} characterization rows')
if __name__=='__main__':main()
