# Phase 0 audit (read-only): graph-run.cc and the existing campaign

Sources: `sp1-sp2/scratch/graph-run.cc`, `sp1-sp2/contrib/trace-matrix-propagation-model/model/trace-matrix-propagation-model.{h,cc}` (TMLM), ns-3 3.46.1 (`VERSION`; sp1-sp2 is not a git repo, so no commit hash is available), `run_pipeline-sweep.py::stage_run_ns3`, `simple-graph-experiments/*/*/run_args.txt`.
No code was changed. Everything below is read from source or existing outputs; nothing here is yet confirmed by a new simulation (that is Phase 1).

## 1. Scenario facts

| Item | Value | Where |
|---|---|---|
| Frame duration | 1 / fps = 1.0 s (campaign `fps: 1.0`) | `g_framesPerSecond`, `run_args.txt` |
| Frame to time | frame i is applied at t = i / fps (no timestamps in CSV) | `LoadFramesCsv`, `Simulator::Schedule(Seconds(time), TraceApplyFrame)` |
| Frames per trace | 60, so t = 0 .. 59 s | `--dg-frames 60` |
| Traffic start / stop | client start 0.1 s, stop 59 s (= last frame time) | `clientApps.Start/Stop` |
| Simulation end | 59 s (`Simulator::Stop(stopTime)`); sink stops at 60 s but is never reached | `runTraceReplay` |
| Routing start | t = 0 (ns-3 default, no delay), so no warm-up | no `Start` offset set |
| Packet size / rate | 1024 B at 50 kbps, so one packet every 0.16384 s, about 360 packets per run | defaults |
| Flow | one UDP flow S to R, port 9000, `MaxPackets` = UINT32_MAX | `--flows=S:R` |
| PHY | YansWifiPhy, TxPower 20 dBm, default RxSensitivity -101 dBm, CcaEdThreshold -62, CcaSensitivity -82 | `phy.Set`, wifi-phy.cc |
| MAC/standard | AdhocWifiMac, 802.11g, default `IdealWifiManager` (helper default) | `wifi-helper.cc:1006` |
| Channel | Yans, TMLM loss model, ConstantSpeedPropagationDelay | |
| Loss values | 1 gives `linkUpLossDb` = 10 dB, 0 gives `linkDownLossDb` = 200 dB | `LoadFramesCsv` |
| Routing attributes set by scenario | none. All protocol timers are ns-3 defaults | `OlsrHelper/AodvHelper/DsdvHelper` default-constructed |
| Seeds | `RngSeedManager::SetSeed(seed)`, run 1; epoch seed = base + (graph-1)*epochs + epoch-1 | `stage_run_ns3` |

### How link up/down is applied (important)

Per frame, `SetCurrentFrameSparse` is called for frame i and `SetNextFrameSparse` for frame i+1 (target time (i+1)/fps). TMLM runs in SPARSE mode with `SparseThreshold = lossThresholdDb = 150`, so:

1. Any entry with loss >= 150 dB (every down link, 200 dB) is **not stored** and is looked up as the default loss, `defaultLossDb = 1e6` dB.
2. `interpolate=true` (campaign setting) linearly interpolates the loss in dB between current and next frame: `loss = cur + alpha*(next - cur)`, alpha = elapsed/span.

Consequence (derived from the code, to be confirmed empirically in Phase 1): because "down" is 1e6 dB rather than 200 dB, the interpolation is effectively a step for down to up, but for a link that goes up to down at the next frame the loss crosses the usable limit (about 121 dB = 20 dBm + 101 dBm) at alpha ~ 1.1e-4, that is after ~0.1 ms. So:

- A link that is up in frame i and down in frame i+1 is **dead for essentially the whole frame i**.
- A link that is down in frame i and up in frame i+1 comes up at t = (i+1)/fps (the usable window starts in the last ~0.1 ms of frame i).
- Net effect: the ns-3 connectivity of an up-run of k frames that is followed by a down frame is k-1 frames. Up-runs of 1 frame give no connectivity. The final frame has no "next", so a run ending at the last frame is not shortened.
- This makes the oracle uptime derived from the trace (frame counts) an overestimate of what ns-3 sees, by about one frame per up-run. With mean up-runs of 3 to 8 frames, that is a 12 to 33 percent shortening of effective up-runs. It must be fixed or accounted for in Phase 2 oracle metrics (candidates: `--no-interpolate`, or `--linkDownLossDb` below the sparse threshold, e.g. 140 dB, which keeps the interpolation but still gives a hard down). Not changed here.

### Timers in effect (ns-3 defaults, verified in source)

| Protocol | Attribute | Default | Source line |
|---|---|---|---|
| OLSR | HelloInterval | 2 s | olsr-routing-protocol.cc:192 |
| OLSR | TcInterval | 5 s | :197 |
| OLSR | MidInterval / HnaInterval | 5 s / 5 s | :202, :207 |
| OLSR | Neighbor hold (`OLSR_NEIGHB_HOLD_TIME`) | 3 x Hello = 6 s (compile-time macro) | :69 |
| OLSR | Topology hold (`OLSR_TOP_HOLD_TIME`) | 3 x TC = 15 s (macro) | :71 |
| OLSR | Duplicate hold | 30 s (macro) | :73 |
| AODV | HelloInterval (EnableHello = true) | 1 s | aodv-routing-protocol.cc:188 |
| AODV | AllowedHelloLoss | 2, so neighbor lifetime 2 s | :296 |
| AODV | ActiveRouteTimeout | 3 s | :243 |
| AODV | MyRouteTimeout / DeletePeriod | 11.2 s / 15 s | :249, :264 |
| AODV | NodeTraversalTime / NetTraversalTime / PathDiscoveryTime | 40 ms / 2.8 s / 5.6 s | :232, :276, :282 |
| AODV | BlackListTimeout | 5.6 s | :255 |
| AODV | RreqRetries / TtlStart / TtlIncrement / TtlThreshold | 2 / 1 / 2 / 7 | |
| DSDV | PeriodicUpdateInterval | 15 s | dsdv-routing-protocol.cc:111 |
| DSDV | SettlingTime | 5 s | :117 |
| DSDV | Holdtimes | 3, so route purge hold 45 s | :147, :259 |
| DSDV | MaxQueueTime / MaxQueueLen / PerDst | 30 s / 500 / 5 | :132 |

Attribute names above were grepped from the ns-3 source, not assumed.

## 2. Ratio: mean up-run duration / protocol timer (existing path_life sweep)

Mean up-run duration = `mean_up_run_frames / fps` (fps = 1), averaged over the 5 graph realizations, from `plots/dg_properties_summary.csv`. The values are identical for line, two-lines and ladder (the S to R up/down timeline is the same for the same seed), so one table covers all three. These are oracle (frame-count) durations; subtract about 1 s for the effective ns-3 duration (see above).

| path_life | mean up-run (s) | / OLSR Hello (2 s) | / OLSR TC (5 s) | / OLSR hold (6 s) | / AODV Hello (1 s) | / AODV ActiveRouteTimeout (3 s) | / DSDV periodic (15 s) | / DSDV hold (45 s) |
|---|---|---|---|---|---|---|---|---|
| 0.1 | 3.00 | 1.50 | 0.60 | 0.50 | 3.00 | 1.00 | 0.20 | 0.07 |
| 0.3 | 4.50 | 2.25 | 0.90 | 0.75 | 4.50 | 1.50 | 0.30 | 0.10 |
| 0.5 | 4.29 | 2.14 | 0.86 | 0.71 | 4.29 | 1.43 | 0.29 | 0.10 |
| 0.7 | 4.67 | 2.33 | 0.93 | 0.78 | 4.67 | 1.56 | 0.31 | 0.10 |
| 0.9 | 7.71 | 3.86 | 1.54 | 1.29 | 7.71 | 2.57 | 0.51 | 0.17 |

Observations:
- Up-runs are shorter than the OLSR TC interval for every path_life except 0.9, shorter than the OLSR neighbor hold (6 s) up to 0.7, and 2 to 7 times shorter than the DSDV periodic update.
- Mean up-run grows only from 3.0 to 7.7 s over path_life 0.1 to 0.9 (max 5 frames for 0.1 to 0.7). The sweep covers rho of about 0.2 to 0.5 for DSDV and 1 to 3.9 for AODV Hello, i.e. a narrow window, and it spans very different regimes per protocol. This is why Phase 3 needs an explicit rho axis.
- The `plots` directory has no 0.3, 0.5, ... duplicates by topology; sweep step is 0.2, giving the 5 values 0.1, 0.3, 0.5, 0.7, 0.9.

## 3. Does traffic start before the protocols can converge?

Traffic starts at 0.1 s and routing starts at 0 s, with no warm-up and no pre-converged state.

| Protocol | Needs before a usable S to R route | Time from t=0 | Traffic starts at 0.1 s? |
|---|---|---|---|
| OLSR | At least two Hello rounds to reach SYM links (>= ~2 to 4 s at Hello = 2 s), MPR selection, then a TC from the MPR selector (interval 5 s) for multi-hop topology knowledge. Estimate ~7 to 12 s for a multi-hop path. Link/neighbor tuples expire after 6 s of silence | ~7 to 12 s | Before convergence. First packets are dropped (no route) |
| AODV | Reactive: RREQ at the first data packet; Hello (1 s) only for neighbor liveness. Discovery is on demand | < 1 s if the path is up | Not a convergence problem, but route is lost when the path breaks and needs rediscovery |
| DSDV | First full-table advertisement within the 15 s periodic interval (plus 5 s settling); a route to R multi-hop requires propagation of an advertisement hop by hop | ~5 to 20 s | Before convergence |

Verdict: traffic starts before OLSR and DSDV can have converged. OLSR needs about 2 to 6 times longer to build a multi-hop route than the typical up-run (3 to 5 s), and up-runs are further shortened by about 1 frame (see the TMLM point). This is a strong candidate explanation for OLSR zero PDR, but it is only a hypothesis until Phase 1 shows route-table evidence. Other candidates to rule out in Phase 1: the up-to-down early-drop behaviour above, and neighbor-tuple state staleness after repeated link loss.

## 4. Other observations relevant to later phases

- `numFlows` default is 30 but the pipeline always passes `--flows=S:R`, so the campaign is single-flow.
- Control traffic counters in `graph-run.cc` (`routing_tx/rx`) count non-app IPv4 packets, not bytes, and not split by protocol message type. Phase 2 needs new instrumentation.
- `goodput_mbps` is computed over (lastRx - firstRx) if multiple RX exist, else over stopTime. That is a window that depends on the delivery pattern, so it is not comparable across cases with different outage patterns. Flag for Phase 2/5.
- No `config.json` is written by the existing pipeline (only `run_args.txt`); no ns-3 commit is available (not a git repo). J2 repo HEAD is `ed1425c2cc3e62eafa7be0d9e821d5cca7a7e43b` with a dirty working tree (modified `G2DG-SPC.py`, `README.md`, etc.), so reproducibility records must store the diff or a file hash, not just the commit.
- All existing outputs must remain untouched. New results go to `simple-graph-experiments-v2/`.
