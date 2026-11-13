#!/usr/bin/env python3
"""A4.3-style A4.4 plots with one three-folder output hierarchy.

X is network size. Each graph family is a curve; protocol is line style and
marker. This avoids repeating the same figures under N42/N92/N162 folders.
"""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

ROOT=Path(__file__).resolve().parent
FAMS=['ba','er','geodesic','rgg','ws']; PROT=['aodv','olsr']; SIZES=[42,92,162]
COL={'ba':'#0072B2','er':'#009E73','geodesic':'#D55E00','rgg':'#CC79A7','ws':'#E69F00'}
MARK={'aodv':'o','olsr':'s'}; STYLE={'aodv':'-','olsr':'--'}

def read(path):
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def val(row,key):
    if key=='criterion': return 1.0 if row.get('pass_criterion')=='pass' else 0.0
    try:
        x=float(row[key]);return x if np.isfinite(x) else np.nan
    except (KeyError,ValueError,TypeError):return np.nan
def subset(rows,n,fam,proto):return [r for r in rows if int(r['N'])==n and r['family']==fam and r['protocol']==proto]
def avg(rows,key):
    xs=[val(r,key) for r in rows];xs=[x for x in xs if np.isfinite(x)]
    return float(np.mean(xs)) if xs else np.nan
def dirs():
    root=ROOT/'plots_amendment_1';out={k:root/k for k in ('plots','graph_characteristic_plots','architecture_plots')}
    for p in out.values():p.mkdir(parents=True,exist_ok=True)
    return out

def line_plot(rows,key,ylabel,title,name,out,ylim=None,log=False):
    fig,ax=plt.subplots(figsize=(11,6))
    for fam in FAMS:
        for proto in PROT:
            ys=[avg(subset(rows,n,fam,proto),key) for n in SIZES]
            ax.plot(SIZES,ys,color=COL[fam],marker=MARK[proto],linestyle=STYLE[proto],linewidth=.9,markersize=5,label=f'{fam} {proto.upper()}')
    ax.set(xlabel='Network size N',ylabel=ylabel,title=title);ax.set_xticks(SIZES);ax.grid(axis='y',alpha=.25)
    if ylim:ax.set_ylim(*ylim)
    if log:ax.set_yscale('log')
    ax.legend(title='Graph family / protocol',frameon=False,fontsize=8,ncol=2)
    fig.tight_layout();fig.savefig(out/name,dpi=160);plt.close(fig)

def characteristic_plots(rows,cov,out):
    specs=[('diameter','Static diameter','background_pdr_median','Background median PDR',False,'01_diameter_vs_pdr.png'),('mean_shortest_path_length','Mean shortest-path length','probe_delay_median_s','Probe delay median (s)',True,'02_path_length_vs_delay.png'),('clustering','Clustering coefficient','background_pdr_median','Background median PDR',False,'03_clustering_vs_pdr.png'),('degree_centralization','Degree centralization','control_packets_mean','Mean control packets',True,'04_centralization_vs_control.png'),('node_connectivity','Node connectivity','background_pdr_median','Background median PDR',False,'05_connectivity_vs_pdr.png')]
    for xfield,xlabel,yfield,ylabel,log,name in specs:
        fig,ax=plt.subplots(figsize=(11,6))
        for fam in FAMS:
            for proto in PROT:
                xs=[];ys=[]
                for n in SIZES:
                    xs.append(val(cov[(fam,n)],xfield));ys.append(avg(subset(rows,n,fam,proto),yfield))
                ax.plot(xs,ys,color=COL[fam],marker=MARK[proto],linestyle=STYLE[proto],linewidth=.9,markersize=5,label=f'{fam} {proto.upper()}')
        ax.set(xlabel=xlabel,ylabel=ylabel,title=f'A4.4: {ylabel} versus {xlabel}');ax.grid(axis='y',alpha=.25)
        if log:ax.set_yscale('log')
        ax.legend(title='Graph family / protocol',frameon=False,fontsize=8,ncol=2)
        fig.tight_layout();fig.savefig(out/name,dpi=160);plt.close(fig)
    fields=['family','N','diameter','mean_shortest_path_length','clustering','degree_centralization','node_connectivity']
    with (out/'graph_characteristics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for fam in FAMS:
            for n in SIZES:w.writerow({'family':fam,'N':n,**{k:cov[(fam,n)].get(k,'') for k in fields[2:]}})

def architecture(out):
    total={42:420,92:480,162:620}
    for n in SIZES:
        fig,axes=plt.subplots(1,len(FAMS),figsize=(20,4.4),constrained_layout=True)
        for ax,fam in zip(axes,FAMS):
            path=ROOT/'inputs'/f'{fam}_N{n}_r1__F{total[n]}.csv'
            with path.open(newline='') as f:
                r=csv.reader(f);labels=next(r);a=np.asarray([[int(x) for x in next(r)] for _ in labels])
            graph=nx.from_numpy_array(a);pos=nx.spring_layout(graph,seed=42,iterations=250);deg=np.asarray([graph.degree(i) for i in graph],dtype=float);sizes=16+30*(deg-deg.min())/max(1,deg.max()-deg.min())
            nx.draw_networkx_edges(graph,pos,ax=ax,edge_color='#7f8c8d',alpha=.28,width=.45);nx.draw_networkx_nodes(graph,pos,ax=ax,node_color=COL[fam],node_size=sizes,linewidths=.25,edgecolors='white')
            ax.set_title(f'{fam}\nN={n}, E={graph.number_of_edges()}');ax.set_axis_off()
        fig.suptitle(f'A4.4 static graph architectures, N={n}');fig.savefig(out/f'architecture_overview_N{n}.png',dpi=180,bbox_inches='tight');plt.close(fig)

def main():
    rows=read(ROOT/'per_run_amendment_1.csv')
    if len(rows)!=30 or {r['status'] for r in rows}!={'success'}:raise SystemExit('Expected 30 successful A4.4 rows')
    covrows=read(ROOT.parents[1]/'A1'/'results'/'graph_covariates.csv');cov={(r['family'],int(r['N'])):r for r in covrows};out=dirs()
    line_plot(rows,'probe_pdr','Probe PDR','A4.4 probe PDR by network size and topology','01_probe_pdr.png',out['plots'],(0,1.05))
    line_plot(rows,'background_pdr_median','Background median PDR','A4.4 background PDR by network size and topology','02_background_pdr.png',out['plots'],(0,1.05))
    line_plot(rows,'probe_delay_median_s','Probe delay median (s)','A4.4 probe delay by network size and topology','03_probe_delay_median.png',out['plots'],log=True)
    line_plot(rows,'control_packets_mean','Mean control packets','A4.4 control packets by network size and topology','04_control_packets.png',out['plots'],log=True)
    line_plot(rows,'criterion','PDR criterion pass indicator','A4.4 PDR criterion by network size and topology','05_pdr_gate_pass_rate.png',out['plots'],(0,1.05))
    characteristic_plots(rows,cov,out['graph_characteristic_plots']);architecture(out['architecture_plots'])
    (ROOT/'plots_amendment_1'/'plot_index.csv').write_text('folder,files\nplots,5\ngraph_characteristic_plots,6\narchitecture_plots,3\n')
    print('wrote 14 plots in exactly three folders; X=network size, curves=family/protocol')
if __name__=='__main__':main()
