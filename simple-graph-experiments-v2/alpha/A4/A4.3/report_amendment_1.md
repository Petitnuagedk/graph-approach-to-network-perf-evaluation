# A4.3 correction report

G0 PASS; G-B PASS for amended runs; G-C PASS (T=120 s).
Abort: geodesic N=162 AODV phi=5% recorded in attempt_inventory.csv as aborted_by_user; elapsed and exit code retained.
Budget: before correction 160; prior A4.3 attempts 25; reused 10; new 40; after correction 225/310. N=92/N=162 are out of scope after correction, not verdicts.

Per-run N=42 table: see per_run_amendment_1.csv; MAC retries and PHY collision drops are in every PDR row. Control message-type bytes and AODV RERR are in control_by_type_amendment_1.csv.
Plots: the A4.2-style N=42 plot set is in plots_amendment_1/; N=92/N=162 plots are intentionally omitted.

Status matrix:
- geodesic,aodv: unflagged pass cells=0/5; control-by-phi=1%:8630.33333;2%:7392.33333;3%:8438.61905;4%:7815;5%:9246; shortfalls descriptive only.
- geodesic,olsr: unflagged pass cells=0/5; control-by-phi=1%:25846.8571;2%:25930;3%:25909.1429;4%:26013.5238;5%:26074.9524; shortfalls descriptive only.
- rgg,aodv: unflagged pass cells=0/5; control-by-phi=1%:6781.66667;2%:9304.71429;3%:9742.28571;4%:10541.619;5%:11481.2857; shortfalls descriptive only.
- rgg,olsr: unflagged pass cells=0/5; control-by-phi=1%:16689.619;2%:16738.9524;3%:16658;4%:16660.1905;5%:16759.3333; shortfalls descriptive only.
- ws,aodv: unflagged pass cells=0/5; control-by-phi=1%:7251.28571;2%:8400.47619;3%:9694.04762;4%:8696.04762;5%:8054.57143; shortfalls descriptive only.
- ws,olsr: unflagged pass cells=0/5; control-by-phi=1%:17971.4286;2%:18050.8571;3%:18072.2857;4%:18028.9524;5%:18102.5714; shortfalls descriptive only.
- er,aodv: unflagged pass cells=0/5; control-by-phi=1%:6767.71429;2%:7572.38095;3%:8742.7619;4%:9130.42857;5%:9001.33333; shortfalls descriptive only.
- er,olsr: unflagged pass cells=0/5; control-by-phi=1%:33379.9048;2%:33214.4762;3%:33301.8095;4%:33310.1905;5%:33314.8571; shortfalls descriptive only.
- ba,aodv: unflagged pass cells=3/5; control-by-phi=1%:7083.42857;2%:11120.5714;3%:9270.61905;4%:9885.33333;5%:11527.5714; shortfalls descriptive only.
- ba,olsr: unflagged pass cells=0/5; control-by-phi=1%:23243.5238;2%:23365.7143;3%:23405.1429;4%:23233.9048;5%:23414.6667; shortfalls descriptive only.

Attribution and overhead labels follow the frozen A4.3 rules; extra analysis is written after A4.3 results.
Decisions (maximum 5): retain the N=42 results; defer N=92/N=162; do not compare with A4.2 interpolation-on results; retain per-type control/RERR reporting; stop.
STOP: no further phi, window/detector changes, DSDV, or Beta work.
