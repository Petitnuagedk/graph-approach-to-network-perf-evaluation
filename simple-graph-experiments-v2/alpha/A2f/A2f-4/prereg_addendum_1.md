# A2f-4 preregistration addendum 1 — MPC timeline run-count interpretation

Registered before any cause classification is accepted and before the Step 2 pool sweep. This addendum corrects one prespecified audit validity check, without changing the 18-cell input set, the sweep design, fidelity/capacity thresholds, or cause precedence apart from the meaning of `timeline_quota_invalid`.

## Reason and retained preliminary artifact

The initial A2f-4 read-only audit script was executed once after the base preregistration, and its output is retained as `audit_18_cells.csv` and `audit_18_cells.json`. During review of that output, the observed requested up-run counts (2–3) showed that the preregistration's assumed K=30 did not describe the A2d MPC timeline generator. Source inspection confirms that `MPCTimelineBlockGenerator.generate()` uses a separate exponential-run procedure in synchronous mode, then corrects the Boolean series to exact U; it does not implement the A2a exact U/K schedule. The K=30 comparison was therefore a category error, not evidence of timeline quota failure. The preliminary audit output is exploratory and **superseded for all cause labels and timeline-validity conclusions**; its read-only metrics are preserved. No new frame pool, assembly, or sweep operation has run.

## Corrected frozen Step 1 validity rule

Treat the stored `None`/integer timeline labels as Boolean down/up. A requested timeline is quota-valid iff it has exactly the configured F=120 rows and each pair has exactly U=round(120×.5)=60 up frames. Report each pair's requested up-run count and transitions as observed descriptive quantities; do not compare them to A2a K=30 or any other target. The saved MPC artifacts have no preregistered exact run-count quota, so run count cannot invalidate this timeline. A malformed row/pair shape or a U mismatch still assigns `timeline_quota_invalid` at cause-order step 1. All subsequent cause-order steps from the base preregistration remain unchanged.

The sweep's `timeline_quota_valid` field uses this corrected F/U-only rule. Sweep requested and realized per-pair run counts remain persisted/reported descriptively, with no run-count pass/fail threshold. All other frozen sweep parameters and capacity classifications are unchanged.

The authoritative corrected read-only census must be written separately as `audit_18_cells_v2.csv` and `.json`; do not overwrite the retained exploratory output. In the final report disclose both the incorrect preliminary check and this correction. No thresholds are changed after observing pair-fidelity or pool-supply results; the amendment concerns only correct interpretation of the source's timeline semantics.
