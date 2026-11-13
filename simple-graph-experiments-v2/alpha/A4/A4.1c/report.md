# A4.1c — offline readiness validity and event audit

**Written after A4.1c results.** Offline only: 0 variants, no ns-3, simulator, or reruns. A4.0*/A4.1/A4.1b artifacts remain read-only. Budget 70/300. Retained protocols: AODV/OLSR. DSDV is excluded only by user direction, not a routing finding; rationale remains `[user to state]`. Phase 6D's DSDV outage question is untested in Alpha.

Frozen preregistration SHA-256: `66d4f765650d668ce01df786bd89996f018f70f05f8e5119bb7e9a73d538f548`. G0 source: [a4.py](../a4.py#L27). `FRAME_RATE=1.0` frame/s means 1.0 s/frame.

## Gate outcomes

- **G0 PASS:** frame mapping is source-stated as 1.0 s/frame.
- **G4 PASS:** 24/24 eligible AODV/OLSR runs have readiness-minus-first-delivery in [9,10] s (100.0%); threshold 80%. Eligible runs with absolute readiness ≤10.5 s: 3/24.
- **G5 PASS:** 0 of 30 runs fail first-five latency ≤100 s / five receptions. Full rows: [first5_latencies.csv](first5_latencies.csv); failing run first-10 Tx/Rx and unmatched early Tx: [g5_failures.csv](g5_failures.csv).
- **G8 PASS:** all 45 A4.1 records scanned; membership is AODV-only across 15 AODV runs. Recomputed first-delivery 100–110-s set has 5 runs; A4.1b set has 5; symmetric difference 0. See [g8_membership.csv](g8_membership.csv).
- **Detector classification:** **window-fill**, determined only by G0/G4/G5 under the preregistered rule. This is a validity classification, not a revised detector or convergence estimate.

### G4 offset summaries (max gap ≤1 s)

| Protocol | N | n | min offset (s) | median (s) | max (s) | in [9,10] n | readiness ≤10.5 s |
|---|---:|---:|---:|---:|---:|---:|---:|
| aodv | 42 | 5 | 9.14604013 | 9.15845542 | 9.87060707 | 5 | 1 |
| aodv | 92 | 5 | 9.00016427 | 9.1580359 | 9.86851052 | 5 | 1 |
| aodv | 162 | 5 | 9.00152825 | 9.14079995 | 9.31593296 | 5 | 1 |
| olsr | 42 | 5 | 9.05922973 | 9.10041821 | 9.12376804 | 5 | 0 |
| olsr | 92 | 2 | 9.07299544 | 9.10818168 | 9.14336791 | 2 | 0 |
| olsr | 162 | 2 | 9.06702622 | 9.11336612 | 9.15970602 | 2 | 0 |

## AODV/OLSR per-run data

First-five values are ordered by reception event; exact matched Tx/Rx timestamps and every latency are in [first5_latencies.csv](first5_latencies.csv). Cluster membership is the 100–110-s AODV first-delivery membership check.

| Family | N | Protocol | First delivery (s) | First 5 latencies (s) | Readiness (s) | Offset (s) | Max gap (s) | G4 eligible | G8 member |
|---|---:|---|---:|---|---:|---:|---:|---|---|
| geodesic | 42 | olsr | 11.5224314 | 1.10051141;0.937245821;0.773810237;0.001661135;0.001661135 | 20.5816611 | 9.05922973 | 0.17381 | true | not_applicable |
| geodesic | 42 | aodv | 1.76906107 | 1.66906107;1.50791369;0.001661192;0.001661192;0.001661192 | 10.9151012 | 9.14604013 | 0.168795957 | true | false |
| rgg | 42 | olsr | 10.6596623 | 0.07390231;0.00137677;0.00137677;0.00137677;0.00137677 | 19.7621768 | 9.10251446 | 0.17405 | true | not_applicable |
| rgg | 42 | aodv | 104.811741 | 0.017981347;0.001377013;0.001377013;0.001377013;0.001377013 | 113.970177 | 9.15843567 | 0.168344 | true | true |
| ws | 42 | olsr | 10.6867563 | 0.100996322;0.001660868;0.001660868;0.001660868;0.001660868 | 19.7624609 | 9.07570455 | 0.17154 | true | not_applicable |
| ws | 42 | aodv | 104.811205 | 0.017444741;0.001660641;0.001660641;0.001660641;0.001660641 | 113.970461 | 9.1592559 | 0.16729 | true | true |
| er | 42 | olsr | 10.310445 | 0.052365005;0.001093047;0.001093047;0.001093047;0.001093047 | 19.434213 | 9.12376804 | 0.338486 | true | not_applicable |
| er | 42 | aodv | 104.483757 | 0.017677288;0.00109271;0.00109271;0.00109271;0.00109271 | 113.642213 | 9.15845542 | 0.172541012 | true | true |
| ba | 42 | olsr | 11.6445147 | 1.05875469;0.895649025;0.732393359;0.001092897;0.001092897 | 20.7449329 | 9.10041821 | 0.21500327 | true | not_applicable |
| ba | 42 | aodv | 0.388565927 | 0.288565927;0.125574381;0.001092993;0.001092993;0.001092993 | 10.259173 | 9.87060707 | 0.17921 | true | false |
| geodesic | 92 | olsr | 11.0707658 | 0.157325828;0.019389163;0.002513163;0.002513163;0.002513163 | 180.497333 | 169.426567 | 1.30643647 | false | not_applicable |
| geodesic | 92 | aodv | 4.05167688 | 3.95167688;3.79207202;0.002512787;0.002512787;0.002512787 | 13.2097128 | 9.1580359 | 0.168344292 | true | false |
| rgg | 92 | olsr | 11.1812695 | 0.103989463;0.001945471;0.001945471;0.001945471;0.001945471 | 20.2542649 | 9.07299544 | 0.200458546 | true | not_applicable |
| rgg | 92 | aodv | 105.462102 | 0.012981792;0.001946062;0.001946062;0.001946062;0.001946062 | 114.462266 | 9.00016427 | 0.17030057 | true | true |
| ws | 92 | olsr | 12.2594809 | 0.199160859;0.035954905;0.009839342;0.003648767;0.003648767 | 21.4028488 | 9.14336791 | 0.179222142 | true | not_applicable |
| ws | 92 | aodv | 106.120712 | 0.016232477;0.003648409;0.003648409;0.003648409;0.003648409 | 115.283168 | 9.16245593 | 0.167580068 | true | true |
| er | 92 | olsr | 10.3441274 | 0.086047393;0.010353436;0.010353436;0.016327436;0.001377436 | 155.913217 | 145.56909 | 1.17301967 | false | not_applicable |
| er | 92 | aodv | 2.76307309 | 2.66307309;2.49969763;0.001377089;0.001377089;0.001377089 | 11.8978571 | 9.134784 | 0.173834616 | true | false |
| ba | 92 | olsr | 10.3232548 | 0.065174821;0.019044657;0.018232657;0.026571531;0.001092657 | 35.9824851 | 25.6592303 | 1.18739667 | false | not_applicable |
| ba | 92 | aodv | 0.390662357 | 0.290662357;0.127900741;0.001092878;0.001092878;0.001092878 | 10.2591729 | 9.86851052 | 0.200806211 | true | false |
| geodesic | 162 | olsr | 13.254763 | 2.17748304;2.01435723;1.85108143;0.003365246;0.003365246 | 70.7529644 | 57.4982013 | 1.17293617 | false | not_applicable |
| geodesic | 162 | aodv | 3.06359687 | 2.96359687;2.80058505;0.003365118;0.003365118;0.003365118 | 12.0651251 | 9.00152825 | 0.16948814 | true | false |
| rgg | 162 | olsr | 11.0954117 | 0.181971678;0.018865978;0.002797702;0.002797702;0.003477702 | 20.2551177 | 9.15970602 | 0.358696 | true | not_applicable |
| rgg | 162 | aodv | 3.08465468 | 2.98465468;2.8226821;0.003082361;0.003082361;0.003082361 | 12.2269579 | 9.14230323 | 0.19076747 | true | false |
| ws | 162 | olsr | 13.7958247 | 0.260944723;0.097718761;0.004784895;0.004784895;0.005314895 | 80.5509793 | 66.7551546 | 1.27669133 | false | not_applicable |
| ws | 162 | aodv | 3.10716049 | 3.00716049;2.84396852;0.004784596;0.004784596;0.004784596 | 12.2307646 | 9.12360411 | 0.17056 | true | false |
| er | 162 | olsr | 10.3674708 | 0.109390831;0.042589161;0.011509786;0.103567067;0.008737052 | 19.4344971 | 9.06702622 | 0.827680519 | true | not_applicable |
| er | 162 | aodv | 0.943523811 | 0.024323811;0.001376773;0.001376773;0.001376773;0.001376773 | 10.2594568 | 9.31593296 | 0.17975 | true | false |
| ba | 162 | olsr | 11.3586227 | 1.1005427;0.955787177;0.798157947;0.001376844;0.001376844 | 233.409537 | 222.050914 | 23.5785621 | false | not_applicable |
| ba | 162 | aodv | 1.77401718 | 1.67401717;1.5105412;0.003399528;0.00137712;0.00137712 | 10.9148171 | 9.14079995 | 0.189668885 | true | false |

## G7 — BA/OLSR N=92 and N=162 event structure

| N | Max-gap interval (s) | Gap (s) | Tx received after gap? | Rx in first 1 s after end |
|---:|---|---:|---|---:|
| 92 | 25.6738626–26.8612593 | 1.18739667 | True | 9 |
| 162 | 121.198457–144.777019 | 23.5785621 | True | 6 |

| N | Window | Scheduled Tx | Rx arrivals | Unmatched scheduled Tx |
|---:|---|---:|---:|---:|
| 92 | preceding_equal | 8 | 7 | 0 |
| 92 | gap | 7 | 1 | 4 |
| 92 | following_equal | 7 | 10 | 0 |
| 162 | preceding_equal | 144 | 137 | 6 |
| 162 | gap | 144 | 1 | 143 |
| 162 | following_equal | 143 | 133 | 11 |

First matched Tx/Rx after the gap: N=92 Tx 26.96976 s → Rx 26.9708527 s; N=162 Tx 144.93456 s → Rx 144.935937 s.
These packet timestamps establish event ordering, not cause; counters are not time-resolved and no causal inference is claimed.

### AODV late-first-delivery packet evidence — written after A4.1c results

The five G8 members, including WS N=92 at 106.120712 s, have matched first-five latency values above. Their early unmatched Tx counts and first packet times are in [aodv_late_first_delivery.csv](aodv_late_first_delivery.csv). This localizes the symptom to absence of an early matched app Rx in these logs; it does not distinguish route discovery, forwarding, or another cause.

## Warm-up status and proposal-only policy options

No warm-up value is recomputed and no option is selected. AODV statuses are carried from A4.1b; OLSR uses G9. OLSR G9 validity does not inherit or automatically adopt any A4.1 warm-up value; policy remains an explicit decision.

| Protocol | N | G9 / carried status | Reason |
|---|---:|---|---|
| aodv | 42 | derived | carried from A4.1b; not a new G9 verdict |
| aodv | 92 | derived | carried from A4.1b; not a new G9 verdict |
| aodv | 162 | derived | carried from A4.1b; not a new G9 verdict |
| olsr | 42 | valid | G0/G4 pass; no censored contributors; existing A4.1 value 32 frames (not inherited) |
| olsr | 92 | not_derivable_censored | 1 censored contributor(s) |
| olsr | 162 | not_derivable_censored | 1 censored contributor(s) |

| Option (not selected) | Run-length implication | Variant cost / effect |
|---|---|---|
| (a) Keep A4.1 AODV warm-ups; OLSR unresolved | AODV totals at N=42/92/162 remain 291/293/139 s (171/173/19 warm-up +120 measured); OLSR run length unresolved | 0 added; reserve 4.2=90 and 4.3=48; OLSR N92/162 counts conditional on G4/G9 |
| (b) Fixed OLSR warm-up chosen from noncensored observations | Each 4.2 run is W_N+120 s; existing N=42 32-frame value would imply 152 s only if separately selected; W_92/W_162 not selected | 0 added if replacing cells; 90+48 retained; transfer assumption requires separate registration |
| (c) Per-run readiness-gated measured window | Each run is observed readiness W_i+120 s; variable and may exceed 240 s, so elapsed cost is unbounded here | 0 added variants; 90+48 retained; requires separate design authorization |
| (d) Drop OLSR N=92/162 cells | Removes 15 4.2 load runs per N and 8 4.3 variants per N | Frees 30 of 90 4.2 and 16 of 48 4.3; remaining 4.2=60, 4.3=32; separate future decision |

## Budget and stop

Retained-protocol design: 4.2 = AODV 45 + OLSR 45 = 90; 4.3 = AODV 24 + OLSR 24 = 48. With 70 spent, planned total is 208/300, leaving 92. The OLSR N=92/162 4.2=30 and 4.3=16 counts depend on unresolved G4/G9; under option (d) those counts are freed, while options (a)–(c) retain them and add 0 variants. No budget counts include DSDV.

### Decisions (maximum five; none selected)

1. State the rationale to replace `[user to state]` for the user-directed DSDV drop.
2. Decide whether OLSR warm-up remains unresolved, uses a separately authorized fixed policy, or is handled with readiness-gated measurement.
3. Decide whether OLSR N=92/162 cells should be retained or separately proposed for removal.
4. Confirm whether this A4.1c validity classification is sufficient to close the detector question; no detector change is made here.

**STOP.** No reruns, detector change, cell disposition beyond the stated DSDV user decision, A4.2, or A4.3 were performed or authorized.
