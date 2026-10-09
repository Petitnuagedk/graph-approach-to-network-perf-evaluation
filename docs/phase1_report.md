# Phase 1 report: OLSR zero-PDR diagnosis

All new outputs are under `simple-graph-experiments-v2/phase1/`. Existing results were not touched.

## Code changes
- `sp1-sp2/scratch/graph-run.cc` (new flags, defaults preserve old behaviour):
  - `--warmup=<s>`: prepends whole frames (spaced 1/fps) held up, shifts the trace, traffic starts at warm-up + 0.1 s. Effective warm-up is rounded up to whole frames.
  - `--warmupMode=first|union`: warm-up topology = trace frame 0 (`first`), or every link ever up (`union`). The C++ default is `union`; the pipeline default is `first` (see below).
  - `--dumpRoutes=true`: writes `routes_<proto>.txt` (routing tables of all nodes at 1 Hz, via `Ipv4RoutingHelper::PrintRoutingTableAllEvery`) and `times_<proto>.csv` (tx/rx timestamps of app packets).
- `run_pipeline-sweep.py`: `--warmup` (default 0 = legacy), `--warmup-mode` (default `first`), `--dump-routes`. Flags are only forwarded to ns-3 when `--warmup > 0` / `--dump-routes`.
- Regression check: with no new flags, ladder / graph_0001 / path_life 0.5 / seed 42 reproduces the existing `epoch_0001` CSV exactly (all columns except wall/cpu time; the diff was empty).

## Runs (single seed 42, fps 1, 50 kbps, 1024 B, up 10 dB / down 200 dB, interpolate on, flow S to R; 27 protocol runs total, 3 protocols x 9 configurations)

Commands: `./ns3 run "graph-run --framesCsv=<trace> --outDir=<dir> --routing=all --flows=S:R --dataRate=50kbps --packetSize=1024 --lossThresholdDb=150 --interpolate=true --defaultLossDb=1e6 --txPowerDbm=20 --linkUpLossDb=10 --linkDownLossDb=200 --fps=1 --seed=42 [--warmup=W --warmupMode=M] --dumpRoutes=true"`.
Static trace: `traces/static_ladder.csv` (ladder adjacency from `ladder/path_life/graph.csv` repeated for 60 frames, all links up).
T_warm = max(3 Hello, 3 TC, neighbor hold) = max(6, 15, 6) = 15 s, so 30 s (the stated minimum) was used; 60 s was added to look at DSDV.

### A. Static, always-up ladder (PDR, app packets sent / received)

| warm-up | OLSR | AODV | DSDV |
|---|---|---|---|
| 0 s | 1.000 (296/296) | 1.000 (360/360) | 1.000 (273/273) |
| 30 s | 1.000 (360/360) | 0.983 (360/354) | 1.000 (360/360) |
| 60 s | 1.000 (360/360) | 1.000 (360/360) | 0.747 (360/269) |

First packet that left the sender (time from client start at 0.1 s, warm-up 0):

| | OLSR | AODV | DSDV |
|---|---|---|---|
| first IP-level tx | 10.59 s | 0.37 s | 15.02 s |

Meaning: OLSR needs about 10.6 s and DSDV 15 s before the first data packet is even handed to IP, because the routing layer holds packets (no route). AODV's 0.983 at 30 s is the first-second route discovery (6 packets lost at t = 30 to 31). DSDV 0.747 at 60 s is a 15 s outage (trace t = 15 to 29) on a static all-up network. That is a separate DSDV instability (sequence numbers in the dumps jump to even and odd values, with routes to R repeatedly invalidated). It is not explained here; it matters for DSDV conclusions (see open issues).

### B. Dynamic ladder, graph_0001 (oracle uptime 0.5 and 0.9; PDR as reported by the scenario)

| path_life | warm-up | OLSR | AODV | DSDV |
|---|---|---|---|---|
| 0.5 | none | 0.000 (tx 25) | 0.573 | 0.044 |
| 0.5 | 30 s, `union` | 0.042 | 0.000 | 0.008 |
| 0.5 | 30 s, `first` | 0.393 | 0.667 | 0.067 |
| 0.9 | none | 0.000 (tx 90) | 0.859 | 0.011 |
| 0.9 | 30 s, `union` | 0.039 | 0.246 | 0.075 |
| 0.9 | 30 s, `first` | 0.253 | 0.855 | 0.231 |

`union` warm-up is harmful: protocols pre-build routes over links that were never simultaneously up, and then fail to recover (AODV delivered nothing for frames 0 to 37 at path_life 0.9). `first` is the sane warm-up and is the pipeline default.

### C. Route evidence (`times_*.csv` and the per-frame timeline, path_life 0.9, `first`)
- AODV: delivers 6/6 per frame in every up frame after discovery, matches the no-warm-up run (0.859 vs 0.855). Warm-up is irrelevant to AODV, as expected for a reactive protocol.
- OLSR: delivers 6/6 in frames 0 to 3, then degrades to 1, 0, 3, 0 while IP-level tx continues at 6 per frame. So a route to R exists in the table (the sender keeps handing packets to IP) but it is stale. After the first break at frame 8, delivery recovers only in frames 12 to 15, and from frame 16 on it never recovers although frames 18 to 25 are an 8-frame up-run. At frame 33 onward OLSR stops sending completely (no route in the table).
- Last frame of every up-run: tx 1, rx 0 in all AODV timelines (`U1/0` before each `d`). This confirms the TMLM interpolation effect from the audit (an up frame followed by a down frame is dead almost throughout), so the effective up-run is one frame shorter than the oracle trace.

## Conclusion

The OLSR zero PDR is **not one single cause**. Backed by the evidence above:

1. **(a) warm-up artifact, for the zeros in the existing data.** In the existing ladder `path_life` sweep, 115 of 125 OLSR rows have PDR 0, and 103 of those 115 have `app_tx_pkts = 0`: not one data packet ever left the sender, because OLSR had no route (static run: first tx at 10.6 s; typical oracle up-runs are 3 to 8 s). The same holds for DSDV (48 of its 60 zero rows have tx 0). These rows are "never converged", not "converged and lost everything".
2. **(c) genuine protocol behaviour, once the warm-up artifact is removed.** With a same-topology warm-up OLSR is no longer zero but is poor (0.25 to 0.39) and cannot recover after the first break within the trace (hold times 6 s for neighbours and 15 s for topology versus up-runs of 5 to 8 frames). The static results prove the replay interface itself works (OLSR PDR 1.000).
3. **(b) not an interface bug on the S-to-R path**, but two real measurement defects were found:
   - **PDR denominator error**: `app_tx_pkts` is counted at the IPv4 Tx trace, so packets dropped at the source because there is no route are never counted. Static OLSR with no warm-up shows 296 of 360 sent packets and PDR 1.000, which is wrong; the true value is about 296/360 = 0.82. Every PDR in the existing campaign is therefore conditional on a route existing, and OLSR and DSDV look better than they are. The fix (count at the UdpClient Tx trace) belongs in Phase 2.
   - **Last-frame effect**: each up-run loses about one frame in ns-3 (see C), so oracle uptime is overstated.

### Existing results that are invalid or not comparable
- All OLSR and DSDV numbers in `simple-graph-experiments/**` (no warm-up): invalid for protocol ranking. PDR is conditional on route existence and is dominated by convergence time. This covers every `ns3-results`, `plots/summary.csv`, `aggregate.csv`, `PDR_*`, `GOODPUT_*`, `EED_*`, `RTX_*` for OLSR and DSDV.
- AODV rows are less affected (it converges in under 1 s), but its PDR is still conditional on the same denominator defect, and the up-run values include the last-frame effect. They are usable for qualitative trends, not for ranking.
- DG-only outputs (`DG_*`, `dg_properties_summary.csv`) are unaffected as DG properties, but the oracle uptime derived from them overstates ns-3 connectivity.
- Nothing was deleted or changed.

## Verification
- Run count: 3 static + 6 dynamic (2 traces x {none, union, first}) = 9 configurations x 3 protocols = 27 protocol runs, same trace and seed across the three protocols in each case. Caveat: the `first` runs reused the output directories of the `union` runs (`dyn_pl*_warm30`), so the on-disk files for those two cases are the `first` results; the `union` numbers in table B come from the console output of the earlier run and can be regenerated with `--warmupMode=union`. The header of the "24 protocol runs" in the Runs section should read 27.
- Backward compatibility: identical CSV on the legacy path (see above).
- Not done: multi-seed or multi-realization statistics (this phase is single-trace diagnosis; two dynamic traces only), and a rerun-identical check of the new flags (same seed was used throughout, but a double-run diff of a warm-up case was not performed).

## Open issues for your decision
1. Fix PDR denominator and last-frame effect in Phase 2 (my proposal: count at UdpClient Tx; set `linkDownLossDb` below 150 dB, for example 140, or disable interpolation, and compare against the oracle).
2. DSDV loses 15 s on a static all-up network at 60 s warm-up. Needs a short investigation before DSDV is included in any ranking (Global rule: no ranking where a protocol has a known convergence problem). It could be genuine ns-3 DSDV behaviour (settling time, hold-down).
3. Confirm the v2 default: `--warmup 30 --warmup-mode first`. For DSDV, 30 s is only 2 update periods; I suggest 45 s.
