# A4.4 amendment 1 — harness correction and re-attempt

**Registration date:** 2026-11-10

## Root cause

The first A4.4 launch attempted all 30 preregistered rows but failed before invoking ns-3. The harness called `runs/<run_id>.mkdir(exist_ok=False)` while the `runs/` parent did not exist. The exception occurred before configuration creation and before subprocess launch. The archived ledger therefore contains 30 failed pre-launch attempts and no measurement data.

## Authorized exception to no-retry

This amendment explicitly makes an exception to the original A4.4 no-retry rule. The exception is justified because no ns-3 process reached execution, no configuration was measured, and no data exist. The amendment changes only the harness pre-launch path and adds validation; it does not change the measurement design, graph inputs, protocols, phi values, timings, windows, detector, or attribution rules. The original 30 failed attempts remain preserved and are not pooled with the re-attempt results.

The amendment raises the Alpha cap from 310 to 340. The 30 re-attempts are separately charged once under this amendment; failures or interruptions during the re-attempt count, and no further retry is authorized.

## Pre-launch smoke gate

Before any re-attempt, the launcher must verify the amendment hash, create a disposable output directory and configuration record, validate the exact required 7B configuration and command construction, and perform one dry-run invocation of the launcher. The dry-run may construct and validate the ns-3 command string but must not execute ns-3, start a worker, consume a variant, or create measured-run output. The smoke gate must verify that the actual run path can create `runs/` and a run-specific output directory and write its configuration record. A failed smoke gate blocks all 30 re-attempts.

## Frozen measurement design

The exact original A4.4 plan remains in force: five A1 families, N={42,92,162}, AODV and OLSR, phi={0.05,0.015,0.0065} by N, realized flow counts 43/63/85, warm-ups 120/180/320 s, 300 s measurement duration, total lengths 420/480/620 s, and windows `[warm-up,warm-up+300]`. The 7B settings remain interpolation=false, link-up loss 10 dB, link-down loss 125 dB, default loss 1,000,000 dB, threshold 150 dB, transmit power 20 dBm, fps 1, 50 kbps, and packet size 1024. Two workers maximum, at least 8 GiB available memory, zero swap, and no timeout remain required.

No A4.3 outputs are reusable. DSDV and Beta remain excluded from this amendment. The amended ledger must distinguish `attempt_1_prelaunch_failure` from `attempt_2_measurement` rows.

## Registration boundary

The amendment hash must be written into the launcher and recorded in the gate log before the smoke test and before any re-attempt. The original preregistration, plan, failure ledger, and report remain immutable historical artifacts. A final amended report and manifest must state whether the 30 re-attempts produced usable baseline data and must stop after completion.
