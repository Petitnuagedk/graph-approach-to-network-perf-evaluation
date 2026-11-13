#!/usr/bin/env python3
"""A4.3-style plots adapted to the A4.4 three-size static baseline.

A4.4 has one phi per N, so plots use family on the x-axis and protocol as
line/marker style; no artificial phi sweep is introduced.
"""
from __future__ import annotations
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
FAMILIES=["ba","er","geodesic","rgg","ws"]
PROTOCOLS=["aodv","olsr"]
COLORS={"ba":"#0072B2","er":"#009E73","geodesic":"#D55E00","rgg":"#CC79A7","ws":"#E69F00"}

def rows():
 with (ROOT/"per_run_amendment_1.csv").open(newline="",encoding="utf-8") as f:r=list(csv.DictReader(f))
 if len(r)!=30 or {x["status"] for x in r}!={"success"}:raise SystemExit("Expected 30 successful A4.4 rows")
 return r

def val(r,k):
 if k=="pass_criterion":return 1.0 if r.get(k)=="pass" else 0.0 if r.get(k)=="fail" else np.nan
 try:
  x=float(r[k]);return x if np.isfinite(x) else np.nan
 except (KeyError,ValueError,TypeError):return np.nan

def grouped(rs,field,fam,proto):
 return [val(x,field) for x in rs if x["family"]==fam and x["protocol"]==proto]

def metric(rs,n,field,ylabel,filename,ylim=None,log=False):
 fig,ax=plt.subplots(figsize=(11,6)); x=np.arange(len(FAMILIES)); width=.36
 for j,proto in enumerate(PROTOCOLS):
  means=[np.nanmean(grouped([r for r in rs if int(r["N"])==n],field,f,proto)) for f in FAMILIES]
  ax.bar(x+(j-.5)*width,means,width,label=proto.upper(),color=[COLORS[f] for f in FAMILIES],alpha=.72 if proto=="aodv" else .42,hatch="" if proto=="aodv" else "//",edgecolor="black",linewidth=.35)
 ax.set_xticks(x,FAMILIES);ax.set_xlabel("Graph family");ax.set_ylabel(ylabel);ax.set_title(f"A4.4 N={n}: {ylabel} (A4.3-style)");ax.grid(axis="y",alpha=.25);ax.legend(frameon=False)
 if ylim:ax.set_ylim(*ylim)
 if log:ax.set_yscale("log")
 fig.tight_layout();fig.savefig(ROOT/"plots_a44"/f"N{n}"/filename,dpi=160);plt.close(fig)

def architecture(rs,n):
 fields=[("probe_pdr","Probe PDR",(0,1.05),False,"01_probe_pdr.png"),("background_pdr_median","Background median PDR",(0,1.05),False,"02_background_pdr.png"),("probe_delay_median_s","Probe delay median (s)",None,True,"03_probe_delay_median.png"),("control_packets_mean","Mean control packets",None,True,"04_control_packets.png"),("forwarded_load_gini","Forwarded-load Gini",(0,1.05),False,"05_forwarded_load_gini.png")]
 for field,label,ylim,log,name in fields:metric(rs,n,field,label,name,ylim,log)
 metric(rs,n,"pass_criterion","Criterion indicator", "06_pdr_criterion.png",(0,1.05),False)

def main():
 rs=rows();
 for n in (42,92,162):
  (ROOT/"plots_a44"/f"N{n}").mkdir(parents=True,exist_ok=True);architecture(rs,n)
 (ROOT/"plots_a44"/"plot_index.csv").write_text("N,plots\n42,6\n92,6\n162,6\n")
 print("wrote 18 A4.4 plots across N=42,92,162")
if __name__=="__main__":main()
