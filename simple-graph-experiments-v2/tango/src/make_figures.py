"""Matplotlib-only Tango P01-P13 figure writer."""
from __future__ import annotations
import csv,shutil,sys,random
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
FAMS=('geodesic','rgg','ws','er','ba'); COLORS={'geodesic':'#000000','rgg':'#0072B2','ws':'#E69F00','er':'#009E73','ba':'#D55E00'}
BOUNDED=('uptime','requested_uptime','measured_uptime','persistency','assembled_route_retention','route_id_retention','clustering','degree_gini','up_fraction','down_fraction','p_edge','life')
def read(p):
 with p.open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))
def save(root,num,title,x,y,rows,kind='scatter',xlabel='',ylabel=''):
 out=root/'figures'; data=out/'data'; pdf=out/'pdf'; data.mkdir(parents=True,exist_ok=True); pdf.mkdir(parents=True,exist_ok=True); stem=f'P{num:02d}_{title.lower().replace(" ","_")}'
 if rows:
  with (data/(stem+'.csv')).open('w',newline='',encoding='utf8') as f:csv.DictWriter(f,fieldnames=list(rows[0])).writeheader();csv.DictWriter(f,fieldnames=list(rows[0])).writerows(rows)
 fig,ax=plt.subplots(figsize=(8,5))
 if not rows: ax.text(.5,.5,'No qualifying data',ha='center',va='center')
 elif kind=='heat':
  value_key=y if y in rows[0] else ('M' if y=='support_M' and 'M' in rows[0] else y)
  values=[]
  for r in rows:
   try: values.append(float(r[value_key]))
   except (KeyError,TypeError,ValueError): values.append(np.nan)
  a=np.array([values],dtype=float);ax.imshow(a,aspect='auto',cmap='viridis');ax.set_yticks([])
 else:
  for fam in FAMS:
   q=[r for r in rows if r.get('family')==fam]
   if q:
    try: ax.scatter([float(r[x]) for r in q],[float(r[y]) for r in q],s=10,alpha=.55,label=fam,color=COLORS[fam])
    except (ValueError,KeyError):pass
  if kind=='line':
   for fam in FAMS:
    q=[r for r in rows if r.get('family')==fam]
    try:
     q=sorted(q,key=lambda r:float(r[x]));ax.plot([float(r[x]) for r in q],[float(r[y]) for r in q],color=COLORS[fam],label=fam)
    except (ValueError,KeyError):pass
 ax.set_title(title);ax.set_xlabel(xlabel or x);ax.set_ylabel(ylabel or y)
 if x in BOUNDED: ax.set_xlim(0,1)
 if y in BOUNDED: ax.set_ylim(0,1)
 if ax.get_legend_handles_labels()[0]: ax.legend(frameon=False,ncol=3,fontsize=8)
 ax.text(.01,.01,'Seeds/realizations: registered Tango design',transform=ax.transAxes,fontsize=7)
 fig.tight_layout();fig.savefig(out/(stem+'.png'),dpi=200);fig.savefig(pdf/(stem+'.pdf'));plt.close(fig)
def save_dynamic_panels(root,num,title,x,y,rows,xlabel,ylabel):
 out=root/'figures'; data=out/'data'; pdf=out/'pdf'; data.mkdir(parents=True,exist_ok=True); pdf.mkdir(parents=True,exist_ok=True)
 stem=f'P{num:02d}_{title.lower().replace(" ","_")}'
 with (data/(stem+'.csv')).open('w',newline='',encoding='utf8') as f:
  fields=list(rows[0]) if rows else [x,y]
  csv.DictWriter(f,fieldnames=fields).writeheader(); csv.DictWriter(f,fieldnames=fields).writerows(rows)
 fig,axes=plt.subplots(1,len(FAMS),figsize=(17,4.2),sharey=True,squeeze=False); axes=axes[0]
 life_colors={'0.3':'#0072B2','0.5':'#009E73','0.7':'#D55E00'}
 for ax,fam in zip(axes,FAMS):
  fq=[r for r in rows if r.get('family')==fam]
  for life in life_colors:
   q=[r for r in fq if r.get('life')==life]
   vals=[]
   for r in q:
    try: vals.append((float(r[x]),float(r[y])))
    except (KeyError,ValueError): pass
   if not vals: continue
   rng=random.Random(20261021+num); jitter=[a+(rng.random()-.5)*.025 for a,b in vals]
   ax.scatter(jitter,[b for a,b in vals],s=14,alpha=.22,color=life_colors[life],edgecolors='none')
   groups={}
   for a,b in vals: groups.setdefault(a,[]).append(b)
   for xv, observed in sorted(groups.items()):
    rr=random.Random(20261021+num+int(xv*1000)); means=[sum(observed[rr.randrange(len(observed))] for _ in observed)/len(observed) for _ in range(1000)]
    mean=sum(observed)/len(observed)
    ax.errorbar(xv,mean,yerr=[[mean-np.quantile(means,.025)],[np.quantile(means,.975)-mean]],fmt='o',color=life_colors[life],capsize=2)
  ax.set_title(fam); ax.set_xlabel(xlabel); ax.set_xlim(-.05,1.05); ax.grid(alpha=.15)
 axes[0].set_ylabel(ylabel); fig.suptitle(title); fig.tight_layout(); fig.savefig(out/(stem+'.png'),dpi=200); fig.savefig(pdf/(stem+'.pdf')); plt.close(fig)
def main(root):
 root=Path(root);t1=read(root/'data/t1_schedules.csv') if (root/'data/t1_schedules.csv').exists() else [];cov=read(root/'data/t2_covariates.csv') if (root/'data/t2_covariates.csv').exists() else [];t3=read(root/'data/t3_traces.csv') if (root/'data/t3_traces.csv').exists() else [];t4=read(root/'data/t4_supply.csv') if (root/'data/t4_supply.csv').exists() else [];cor=read(root/'data/correlations.csv') if (root/'data/correlations.csv').exists() else []
 save(root,1,'feasible_region','uptime','mean_up_run',t1,xlabel='realized uptime',ylabel='mean up-run (frames)')
 for i,title,x,y,rows,xlabel,ylabel in [
  (2,'realized_stability','uptime','transitions',t1,'realized uptime','transitions'),
  (4,'structural_scatter','diameter','mean_shortest_path_length',cov,'diameter','mean shortest-path length'),
  (6,'probe_structure','probe_hops','probe_equal_shortest_paths',cov,'probe hops','equal shortest paths'),
  (9,'route_diversity','probe_equal_shortest_paths','distinct_route_groups',t3,'probe equal-shortest-path count','distinct route groups'),
  (10,'persistency','persistency','assembled_route_retention',t3,'path persistency','route stability / retention'),
 ]:save(root,i,title,x,y,rows,xlabel=xlabel,ylabel=ylabel)
 save_dynamic_panels(root,11,'path_lifetime_vs_route_retention', 'life','assembled_route_retention',t3,'path lifetime','route retention')
 save_dynamic_panels(root,12,'persistency_vs_route_retention','persistency','assembled_route_retention',t3,'path persistency','route retention')
 save_dynamic_panels(root,13,'path_lifetime_vs_persistency','life','persistency',t3,'path lifetime','path persistency')
 save(root,3,'support_size','K','support_M',read(root/'data/t1_support.csv') if (root/'data/t1_support.csv').exists() else [],kind='heat',xlabel='K',ylabel='log10 support M')
 save(root,5,'simpson_check','degree_gini','clustering',cov)
 save(root,7,'down_state_supply','p_edge','supply_ratio_life_0.5',t4,kind='line',xlabel='p_edge',ylabel='down supply ratio')
 save(root,8,'spearman_forest','rho','n',cor,xlabel='Spearman rho',ylabel='n')
if __name__=='__main__':main(sys.argv[1])
