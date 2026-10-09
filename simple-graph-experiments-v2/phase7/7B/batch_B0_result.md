# Phase 7B-B0 result — qualifies under clarified frame accounting

## Execution record

- Preregistration: [prereg.md](prereg.md), Gate B0; the frame-count clarification is documented there.
- Invocations: 1 `graph-run` invocation with OLSR, AODV, and static variants = **3 protocol variants**.
- Output: [legacy_before](legacy_before/) and [config.json](legacy_before/config.json).
- Source trace SHA-256: `282feae63d0822c096bc427b9e7fc8705447509d352a72a78761805acd81f603`.
- Resolved legacy settings: interpolation enabled; seed 42; 50 kbps UDP; 1,024-byte packets; 45-second first-frame warm-up; 1 fps; down-loss 125 dB; dump-routes enabled.

## Gate outcome

**B0 validity passes under the clarified source-versus-applied frame accounting.** The source file is stored as one matrix per frame: it contains 60 blank-delimited frame matrices, each with five node rows. Its physical format is 1 header + 300 matrix-data rows + 59 blank separators = 360 physical lines; physical lines are not frames. The source-case config independently records `dg_frames=60` and `fps=1`.

The requested warm-up was 45 seconds at 1 fps, and the ns-3 loader rounds warm-up up to whole frames. Thus `expected applied frames = 60 + ceil(45 × 1) = 105`. The captured ns-3 load log reports 105 loaded frames and a time span of 0–104 seconds. The result CSV reports `frame_apply_calls=105` for OLSR, AODV, and static. These checks agree exactly. The trace hash matches the preregistered input hash, interpolation resolved to true, and the run completed successfully.

The preregistration was amended on 2026-10-08 after observing the output, solely to clarify the distinction between source frame matrices and warm-up-applied frames. The 60-frame source threshold and deterministic warm-up formula were not relaxed. The existing B0 output therefore qualifies; **B0 was not rerun**. No source code was edited; B1 and B2 have not been run.

Current cumulative Phase 7 spend is **3/300 variants**; remaining budget is **297**. No conclusion about the no-interpolation profile is made by B0.
