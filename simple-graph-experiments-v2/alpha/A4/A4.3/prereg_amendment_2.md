# A4.3 extension amendment 2 — N=42 phi 6–10 extension

This amendment is registered after the completed amendment-1 A4.3 correction and before any extension launch. Amendment 1, the original preregistration, original plan, original launcher, budget, and amendment-1 outputs remain unchanged.

## Scope

Add phi values `{6,7,8,9,10}%` for the same five graph families, N=42, AODV and OLSR, realization 1, fixed 120 s traces, and the unchanged A4.3 configuration. This is 50 new cells. The existing phi 1–5 amendment-1 rows are included by concatenation for a combined 100-row N=42 ledger. N=92 and N=162 remain out of scope.

## Execution and accounting

The new 50 cells run once each with at most two workers, no timeout, no automatic retry, and the existing per-launch guard of at least 8 GiB `MemAvailable` and zero swap. The extension adds 50 attempted variants: cumulative Alpha accounting is 225 + 50 = 275/310, below the hard cap. No budget file is edited. No existing cell is rerun or reused.

## Frozen settings and analysis

Use `--interpolate=false`, linkUpLossDb=10, linkDownLossDb=125, defaultLossDb=1000000, lossThresholdDb=150, txPowerDbm=20, fps=1, dataRate=50kbps, packetSize=1024, the same graph inputs, probe pairs, readiness rule, measurement window, PDR criteria, control-by-type/RERR accounting, and population summaries as amendment 1. The combined report and plots show phi 1–10; no ranking or ceiling claim is made. The extension is descriptive and does not change prior verdicts.

## Stop rule

After the combined ledger, report, plots, and manifest are written, stop. No further phi, size, detector/window, protocol, DSDV, or Beta work is authorized by this amendment.
