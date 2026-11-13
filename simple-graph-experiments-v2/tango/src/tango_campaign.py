"""Tango generator-only campaign runner (T1-T4, correlations, figures)."""
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,os,random,statistics,subprocess,sys,time,multiprocessing as mp
from pathlib import Path
from typing import Any
import networkx as nx
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; TANGO=ROOT/'tango'; A1=ROOT/'alpha'/'A1'; A2F=ROOT/'alpha'/'A2f'/'A2f-2'/'source'
SIZES=(42,92,162); F=120; FAMS=('geodesic','rgg','ws','er','ba'); RFAMS=FAMS[1:]; SEED_BLOCK=30_000_000

def guard():
    av=next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    if av<8*1024*1024: raise RuntimeError('STOP: MemAvailable < 8 GiB')
    swap_rows=[x for x in Path('/proc/swaps').read_text().splitlines()[1:] if x.strip()]
    if swap_rows: raise RuntimeError('STOP: active swap detected')
def write(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True); fields=fields or (list(rows[0]) if rows else [])
    with path.open('w',newline='',encoding='utf8') as f: csv.DictWriter(f,fieldnames=fields,extrasaction='ignore').writeheader(); csv.DictWriter(f,fieldnames=fields,extrasaction='ignore').writerows(rows)
def read(path):
    with path.open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))
def h256(path):
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()
_UK_CLASS=None
OP_TIMEOUT=60
def uk():
    global _UK_CLASS
    if _UK_CLASS is None:
        for name in ('yadygaga.timelineBlockGenerator','yadygaga'):
            sys.modules.pop(name,None)
        while str(A2F) in sys.path: sys.path.remove(str(A2F))
        sys.path.insert(0,str(A2F))
        from yadygaga.timelineBlockGenerator import SPCTimelineBlockGenerator
        _UK_CLASS=SPCTimelineBlockGenerator
    return _UK_CLASS
def schedule(u,k,seed):
    o=uk()(F,seed=seed,mode='blocks',behavior='uk',up_count=u,up_runs=k); o.generate_blocks(); return list(o.last_timeline)
def _schedule_child(conn,u,k,seed):
    try:
        os.nice(19); conn.send(('ok',schedule(u,k,seed)))
    except BaseException as exc:
        conn.send(('error',repr(exc)))
    finally: conn.close()
def timed_schedule(u,k,seed):
    ctx=mp.get_context('fork'); parent,child=ctx.Pipe(False); p=ctx.Process(target=_schedule_child,args=(child,u,k,seed)); p.start(); p.join(OP_TIMEOUT)
    if p.is_alive():
        p.kill(); p.join(); raise TimeoutError(f'operation timeout after {OP_TIMEOUT}s: T1 U={u} K={k} seed={seed}')
    if not parent.poll(): raise RuntimeError(f'child operation exited without result: T1 U={u} K={k} seed={seed}')
    status,value=parent.recv()
    if status!='ok': raise RuntimeError(value)
    return value
def rr(bits,val):
    a=[]; i=0
    while i<len(bits):
        if bits[i]==val:
            j=i
            while j<len(bits) and bits[j]==val:j+=1
            a.append(j-i);i=j
        else:i+=1
    return a
def support(f,u,k):
    d=f-u
    if 0<u<f and 1<=k<=min(u,d+1):return math.comb(u-1,k-1)*math.comb(d+1,k)
    return int(u==0 or (u==f and k==1))
def t1():
    rows=[]; sup=[]; failures=[]
    for q in [i/10 for i in range(1,10)]:
        u=round(F*q);d=F-u
        for k in range(1,min(u,d+1)+1):
            for seed in range(42,242):
                try:
                    b=timed_schedule(u,k,seed)
                except BaseException as exc:
                    failures.append({'U':u,'D':d,'K':k,'seed':seed,'error':repr(exc)})
                    write(TANGO/'data'/'t1_failures.csv',failures)
                    raise
                up=rr(b,True);dn=rr(b,False); tr=sum(x!=y for x,y in zip(b,b[1:])); ac=float(np.corrcoef(b[:-1],b[1:])[0,1]) if np.std(b[:-1]) and np.std(b[1:]) else 0
                if tr < 2*k-2 or tr > 2*k:
                    failures.append({'U':u,'D':d,'K':k,'seed':seed,'error':f'T1-G4 transition violation: {tr}'})
                    write(TANGO/'data'/'t1_failures.csv',failures)
                    raise RuntimeError(f'STOP: T1-G4 transition violation U={u} K={k} seed={seed} transitions={tr}')
                rows.append({'q':q,'U':u,'D':d,'K':k,'seed':seed,'uptime':sum(b)/F,'transitions':tr,'mean_up_run':statistics.mean(up),'max_up_run':max(up),'mean_down_run':statistics.mean(dn) if dn else 0,'max_down_run':max(dn) if dn else 0,'longest_outage':max(dn) if dn else 0,'first_outage_frame':b.index(False) if False in b else '','lag1_autocorrelation':ac,'support_M':support(F,u,k),'mean_up_error':abs(statistics.mean(up)-u/k),'wall_time_s_contended':''})
            sup.append({'F':F,'q':q,'U':u,'D':d,'K':k,'M':support(F,u,k)})
    brute=[]
    for u in range(9):
        for k in range(9):
            n=0
            for mask in range(256):
                b=[bool(mask&(1<<i)) for i in range(8)]
                if sum(b)==u and sum(x and(i==0 or not b[i-1]) for i,x in enumerate(b))==k:n+=1
            brute.append({'F':8,'U':u,'D':8-u,'K':k,'M':support(8,u,k),'brute_force':n,'match':support(8,u,k)==n})
    write(TANGO/'data'/'t1_schedules.csv',rows);write(TANGO/'data'/'t1_support.csv',sup+brute)
def load_edges():
    man=json.loads((A1/'results'/'graph_manifest.json').read_text()); graphs={}
    for x in man:
        relative=Path(x['edge_list'])
        p=A1/relative if relative.parts[:1] == ('results',) else A1/'results'/relative
        if h256(p)!=x['edge_sha256']:raise RuntimeError('STOP: A1 edge hash mismatch '+str(p))
        g=nx.Graph();g.add_edges_from((int(r['u']),int(r['v'])) for r in read(p));graphs[x['graph_id']]=g
    return graphs,man
def rgg(n,seed):
    z=random.Random(seed);p=[(z.random(),z.random()) for _ in range(n)];r=math.sqrt(6/(math.pi*(n-1)));g=nx.Graph();g.add_nodes_from(range(n))
    for u,v in itertools.combinations(range(n),2):
        dx=min(abs(p[u][0]-p[v][0]),1-abs(p[u][0]-p[v][0]));dy=min(abs(p[u][1]-p[v][1]),1-abs(p[u][1]-p[v][1]))
        if dx*dx+dy*dy<=r*r:g.add_edge(u,v)
    return g
def make(f,n,seed,ws_p=.1):
    if f=='rgg':return rgg(n,seed)
    if f=='ws':return nx.watts_strogatz_graph(n,6,ws_p,seed=seed)
    if f=='er':return nx.erdos_renyi_graph(n,6/(n-1),seed=seed)
    return nx.barabasi_albert_graph(n,3,seed=seed)
def probe(g):
    best=None
    for s,r in itertools.combinations(sorted(g),2):
        dist={s:0}; counts={s:1}; queue=[s]
        for u in queue:
            for v in g[u]:
                if v not in dist: dist[v]=dist[u]+1; counts[v]=counts[u]; queue.append(v)
                elif dist[v]==dist[u]+1: counts[v]+=counts[u]
        d=dist[r];m=counts[r];key=(m,d,-s,-r)
        if best is None or key>best[0]:best=(key,s,r,d,m)
    return best[1:]
def metric(g,gid,fam,n,real,seed,attempt):
    s,r,d,m=probe(g);deg=[x[1] for x in g.degree()];gini=sum(abs(a-b) for a in deg for b in deg)/(2*len(deg)*sum(deg))
    return {'graph_id':gid,'family':fam,'N':n,'realization':real,'edges':g.number_of_edges(),'mean_degree':statistics.mean(deg),'max_degree':max(deg),'degree_gini':gini,'diameter':nx.diameter(g),'mean_shortest_path_length':nx.average_shortest_path_length(g),'clustering':nx.average_clustering(g),'connected':True,'probe_S':s,'probe_R':r,'probe_hops':d,'probe_equal_shortest_paths':m,'betweenness_max':max(nx.betweenness_centrality(g).values()),'assortativity':nx.degree_assortativity_coefficient(g),'seed':seed,'candidate_attempt':attempt}
def t2():
    gs,man=load_edges(); cov=read(A1/'results'/'graph_covariates.csv'); attempts=[]
    ws_rows=read(A1/'results'/'ws_calibration.csv'); ws_p={int(x['N']):float(x['p']) for x in ws_rows if x['selected']=='True'}
    for fam in RFAMS:
      for n in SIZES:
       for real in range(4,31):
        base=SEED_BLOCK+RFAMS.index(fam)*1_000_000+n*1000+real*100;ok=False
        for a in range(1000):
            seed=base+a;g=make(fam,n,seed,ws_p.get(n,.1));conn=nx.is_connected(g);attempts.append({'family':fam,'N':n,'realization':real,'base_seed':base,'attempt':a,'candidate_seed':seed,'connected':conn,'accepted':conn,'reason':'accepted' if conn else 'disconnected'})
            if conn:
                gid=f'{fam}_N{n}_r{real}';gs[gid]=g;cov.append(metric(g,gid,fam,n,real,seed,a));ok=True;break
        if not ok:raise RuntimeError(f'STOP: connectivity budget exhausted {fam} N={n} r={real}')
    edges=[{'graph_id':gid,'u':min(u,v),'v':max(u,v)} for gid,g in gs.items() for u,v in g.edges()]
    write(TANGO/'data'/'t2_covariates.csv',cov);write(TANGO/'data'/'t2_edges.csv',edges);write(TANGO/'data'/'t2_attempts.csv',attempts);return gs
def reload_t2_graphs():
    accepted=read(TANGO/'data'/'t2_covariates.csv')
    if len(accepted)<len({x['graph_id'] for x in read(TANGO/'data'/'t2_edges.csv')}):
        accepted=restore_t2_covariates()
    base,_=load_edges(); ws_rows=read(A1/'results'/'ws_calibration.csv')
    ws_p={int(x['N']):float(x['p']) for x in ws_rows if x['selected']=='True'}
    graphs={x['graph_id']:base[x['graph_id']] for x in accepted if x['family']=='geodesic'}
    for x in accepted:
        if x['family']!='geodesic': graphs[x['graph_id']]=make(x['family'],int(x['N']),int(x['seed']),ws_p.get(int(x['N']),.1))
    if len(graphs)!=len(accepted): raise RuntimeError('STOP: T2 graph reconstruction count mismatch')
    return graphs
def restore_t2_covariates():
    """Restore full T2 covariates after a pilot has replaced the covariate file."""
    edge_rows=read(TANGO/'data'/'t2_edges.csv'); attempts=read(TANGO/'data'/'t2_attempts.csv'); a1_cov={x['graph_id']:x for x in read(A1/'results'/'graph_covariates.csv')}; graphs={}
    for row in edge_rows:
        graphs.setdefault(row['graph_id'],nx.Graph()).add_edge(int(row['u']),int(row['v']))
    accepted_seeds={(x['family'],int(x['N']),int(x['realization'])):x for x in attempts if x['accepted']=='True'}
    rows=[]
    for gid,g in graphs.items():
        parts=gid.split('_'); fam=parts[0]; n=int(parts[1][1:]); real=int(parts[2][1:])
        if gid in a1_cov:
            item=a1_cov[gid]; seed=item['seed']; attempt=int(item['candidate_attempt']) if item['candidate_attempt'].isdigit() else 0
        elif fam=='geodesic': seed='deterministic'; attempt=0
        else:
            item=accepted_seeds[(fam,n,real)]; seed=int(item['candidate_seed']); attempt=int(item['attempt'])
        rows.append(metric(g,gid,fam,n,real,seed,attempt))
    write(TANGO/'data'/'t2_covariates.csv',rows)
    return rows
def frame_pool(g,s,r,p,seed,trials):
    """Generate disjoint routeable (up) and non-routeable (down) frame pools."""
    rng=random.Random(seed); up={}; down=[]
    edges=list(g.edges())
    for _ in range(trials):
        h=g.copy(); h.remove_edges_from([e for e in edges if rng.random()>p])
        try:
            route=tuple(nx.shortest_path(h,s,r))
        except (nx.NetworkXNoPath,nx.NodeNotFound):
            down.append(h); continue
        up.setdefault(route,[]).append(h)
    return up,down
def frame(g,s,r,p,seed):
    up, _=frame_pool(g,s,r,p,seed,1)
    return next(iter(up),None)
def assemble(bits,path_ids,up,down,seed,persistency):
    rng=random.Random(seed); previous=None; selected=[]; selected_ids=[]
    groups=list(up)
    for bit,pid in zip(bits,path_ids):
        if not bit:
            selected.append(rng.choice(down)); selected_ids.append(None); previous=None; continue
        if previous is not None and rng.random()<persistency and previous in up:
            route=previous
        elif pid is not None and pid in up:
            route=pid
        else:
            route=rng.choice(groups)
        selected.append(rng.choice(up[route])); selected_ids.append(route); previous=route
    return selected,selected_ids
def t3(gs,pilot=False):
    cov={x['graph_id']:x for x in read(TANGO/'data'/'t2_covariates.csv')};rows=[];fail=[];count=0
    for gid,g in gs.items():
        n=g.number_of_nodes()
        if pilot and n!=162: continue
        for life in ((.3,.5,.7) if not pilot else (.3,)):
            u=round(F*life); k=math.ceil(min(u,F-u+1)/2)
            for persist in (0.0,0.25,0.5,0.75,1.0):
                for seed in (42,43,44):
                    st=time.monotonic(); up_pool,down_pool=frame_pool(g,int(cov[gid]['probe_S']),int(cov[gid]['probe_R']),.5,seed+10000,3000)
                    if not up_pool or not down_pool:
                        fail.append({'graph_id':gid,'life':life,'persistency':persist,'seed':seed,'error':'empty required pool'}); write(TANGO/'data'/'t3_failures.csv',fail); raise RuntimeError(f'STOP: T3-G1 empty required pool graph={gid}')
                    bits=timed_schedule(u,k,seed); path_ids=[None if not bit else i for i,bit in enumerate(bits)]
                    chosen,chosen_ids=assemble(bits,path_ids,up_pool,down_pool,seed+20000,persist)
                    route_ids=[x for x in chosen_ids if x is not None]; ret=sum(a==b for a,b in zip(route_ids,route_ids[1:]))/max(1,len(route_ids)-1); uptime_error=abs(sum(bits)/F-life)
                    if uptime_error>.05:
                        fail.append({'graph_id':gid,'life':life,'persistency':persist,'seed':seed,'error':f'T3-G2 uptime error {uptime_error}'}); write(TANGO/'data'/'t3_failures.csv',fail); raise RuntimeError(f'STOP: T3-G2 uptime error graph={gid}')
                    rows.append({'graph_id':gid,'family':gid.split('_')[0],'N':n,'life':life,'K':k,'persistency':persist,'trace_seed':seed,'frame_seed':seed+10000,'assembly_seed':seed+20000,'up_pool':sum(map(len,up_pool.values())),'down_pool':len(down_pool),'distinct_route_groups':len(up_pool),'assembled_route_retention':ret,'route_id_retention':ret,'hop_count_mean':statistics.mean([len(x)-1 for x in chosen]),'hop_count_variance':statistics.variance([len(x)-1 for x in chosen]) if len(chosen)>1 else 0,'measured_uptime':sum(bits)/F,'requested_uptime':life,'uptime_error':uptime_error,'empty_pool_fallbacks':0,'shortcut_frames':0,'wall_time_s_contended':time.monotonic()-st}); count+=1
                    if pilot and count>=15:
                        write(TANGO/'data'/'t3_traces.csv',rows);write(TANGO/'data'/'t3_failures.csv',fail);return rows
    write(TANGO/'data'/'t3_traces.csv',rows);write(TANGO/'data'/'t3_failures.csv',fail);return rows
def t4(gs):
    cov={x['graph_id']:x for x in read(TANGO/'data'/'t2_covariates.csv')};rows=[]
    for gid,g in gs.items():
      if gid.split('_')[0] not in ('er','geodesic'):continue
      s=int(cov[gid]['probe_S']);r=int(cov[gid]['probe_R'])
      for p in (.3,.5,.7):
       for seed in (42,43,44):
        up=sum(frame(g,s,r,p,seed+j) is not None for j in range(3000));down=3000-up;rows.append({'graph_id':gid,'family':gid.split('_')[0],'N':g.number_of_nodes(),'p_edge':p,'pool_seed':seed,'up_fraction':up/3000,'down_fraction':down/3000,'down_count':down,'supply_ratio_life_0.5':down/60,'supply_ratio_life_0.9':down/12,'wall_time_s_contended':''})
    write(TANGO/'data'/'t4_supply.csv',rows)
def correlations(rows):
    cov={x['graph_id']:x for x in read(TANGO/'data'/'t2_covariates.csv')};out=[];xs=('diameter','mean_shortest_path_length','clustering','degree_gini','probe_equal_shortest_paths','probe_hops');ys=('up_pool','down_pool','distinct_route_groups','assembled_route_retention','hop_count_mean','hop_count_variance')
    def spearman_ci(pairs):
        if len(pairs)<3:return float('nan'),float('nan'),float('nan')
        def rho(q):
            a,b=zip(*q);return float(np.corrcoef(np.argsort(np.argsort(a)),np.argsort(np.argsort(b)))[0,1])
        observed=rho(pairs); rng=random.Random(20261021); vals=[]
        for _ in range(10000): vals.append(rho([pairs[i] for i in (rng.randrange(len(pairs)) for _ in pairs)]))
        return observed,float(np.quantile(vals,.025)),float(np.quantile(vals,.975))
    for fam in RFAMS:
     for n in SIZES:
      raw=[x for x in rows if x['family']==fam and int(x['N'])==n and float(x['life'])==.5]
      by_graph={}
      for item in raw: by_graph.setdefault(item['graph_id'],[]).append(item)
      q=[]
      for gid,items in by_graph.items():
          q.append({key:statistics.mean(float(item[key]) for item in items) for key in ('up_pool','down_pool','distinct_route_groups','assembled_route_retention','hop_count_mean','hop_count_variance')}|{'graph_id':gid})
      for x in xs:
       for y in ys:
        p=[(float(cov[z['graph_id']][x]),float(z[y])) for z in q if z[y]!=''];rho,lo,hi=spearman_ci(p); label='entangled' if abs(rho)>=.7 and lo>.5 else ('decoupled' if abs(rho)<.3 and hi<.5 else 'inconclusive')
        out.append({'family':fam,'N':n,'life':.5,'covariate':x,'outcome':y,'rho':rho,'ci_lo':lo,'ci_hi':hi,'n':len(p),'label':label,'power_flag':'underpowered' if len(p)<10 or (hi-lo)/2>.25 else ''})
    write(TANGO/'data'/'correlations.csv',out)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='tango');ap.add_argument('--max-workers',type=int,default=2);ap.add_argument('--operation-timeout',type=int,default=60);ap.add_argument('--pilot-only',action='store_true');ap.add_argument('--t3-only',action='store_true');a=ap.parse_args()
    if a.max_workers>2 or a.operation_timeout!=60:raise SystemExit('STOP: registered cap mismatch')
    global OP_TIMEOUT; OP_TIMEOUT=a.operation_timeout
    guard();(TANGO/'data').mkdir(parents=True,exist_ok=True);(TANGO/'figures').mkdir(exist_ok=True)
    if a.t3_only:
        gs=reload_t2_graphs(); rows=t3(gs,False); correlations(rows)
        subprocess.run([sys.executable,str(Path(__file__).with_name('make_figures.py')),str(TANGO)],check=True)
        print(json.dumps({'t3_only':True,'graphs':len(gs),'traces':len(rows),'status':'complete'})); return
    if a.pilot_only:
        # Registered pilot: one N=162 trace only.  Do not run T1/T2/T4 or
        # create campaign results before the pilot projection is reviewed.
        gs,_=load_edges(); gid='geodesic_N162_r1'; gs={gid:gs[gid]}
        source_cov=read(A1/'results'/'graph_covariates.csv')
        write(TANGO/'data'/'t2_covariates.csv',[x for x in source_cov if x['graph_id']==gid])
        rows=t3(gs,True)
        print(json.dumps({'pilot':True,'graphs':len(gs),'traces':len(rows),'status':'pilot-complete'}))
        return
    t1();gs=t2();t4(gs);rows=t3(gs,False);correlations(rows)
    subprocess.run([sys.executable,str(Path(__file__).with_name('make_figures.py')),str(TANGO)],check=True)
    print(json.dumps({'graphs':len(gs),'traces':len(rows),'status':'complete'}))
if __name__=='__main__':main()
