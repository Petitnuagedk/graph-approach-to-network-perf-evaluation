# Proposed fixed per-size hard timeouts for future 4.1–4.3

This proposal is to freeze before 4.1; it does not alter A4.0's registered 3,600-s cap or the two authorized A4.0d variants (each capped at 3,600 s by user instruction).

Successful N=162 pilots: AODV φ1 = 662.068669 s; DSDV φ1 = 869.164999 s; DSDV φ10 = 2,284.325160 s. The largest Part-A scaling factor is 2.5 and the contention allowance is 1.5. At the one-percent anchor, DSDV φ1 × 2.5 × 1.5 = 3,259.368746 s. The observed φ10 DSDV run × 1.5 = 3,426.487740 s, which is the larger sizing bound. N=92 and N=42 bounds scale by `(N/162)^2`: 1,105.082771 s and 230.312619 s respectively. Round up to operational hard caps:

| N | Scaled sizing bound | Proposed hard timeout |
|---:|---:|---:|
| 42 | 230.3 s | 1,800 s |
| 92 | 1,105.1 s | 3,600 s |
| 162 | 3,426.5 s | 7,200 s |

Freeze these before 4.1 or use stricter prereg/user timeout. A timeout consumes its variant attempt, is retained as timeout/unknown, and never triggers retry. For 4.2, add no per-cell retries. The above scaling is a proposal, not measured per-size runtime.
