"""A2f isolated `(U,K)` timeline interface overlay.

The baseline implementation is loaded read-only from the A2d item 1 snapshot.
Legacy and patched modes delegate directly; patched-v2 is a named alias, and
uk translates explicit integer quotas to the same patched sampler call.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Any

_BASELINE_SOURCE = os.environ.get("A2F_BASELINE_SOURCE")
if _BASELINE_SOURCE:
    _BASELINE = Path(_BASELINE_SOURCE).resolve() / "yadygaga" / "timelineBlockGenerator.py"
else:
    _BASELINE = (
        Path(__file__).resolve().parents[5]
        / "alpha"
        / "A2"
        / "A2d"
        / "item1"
        / "source"
        / "yadygaga"
        / "timelineBlockGenerator.py"
    )
_SPEC = importlib.util.spec_from_file_location("_a2d1_timelineBlockGenerator", _BASELINE)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load baseline timeline generator from {_BASELINE}")
_BASE: ModuleType = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)

# Retain the baseline module's other public classes and helpers unchanged.
for _name in dir(_BASE):
    if not _name.startswith("_") and _name not in {"SPCTimelineBlockGenerator"}:
        globals()[_name] = getattr(_BASE, _name)


class InfeasibleTimeline(ValueError):
    """Requested integer quota is outside the exact finite timeline support."""

    def __init__(self, U: int, D: int, K_requested: int, K_max: int) -> None:
        self.U = U
        self.D = D
        self.K_requested = K_requested
        self.K_max = K_max
        super().__init__(
            f"Requested K={K_requested} is infeasible for U={U}, D={D}; "
            f"K must be in 0..{K_max} for trivial support or 1..{K_max} otherwise"
        )


class SPCTimelineBlockGenerator:
    """Compatibility-preserving timeline generator with opt-in exact `(U,K)` mode."""

    def __init__(
        self,
        frames: int,
        path_life: float | None = None,
        stability: float | None = None,
        seed: int | float | None = None,
        mode: str = "blocks",
        pathPersistency: float = 0.0,
        behavior: str = "patched",
        *,
        up_count: int | None = None,
        up_runs: int | None = None,
        mean_up_duration: float | None = None,
    ) -> None:
        self.frames = int(frames)
        self.path_life = path_life
        self.stability = stability
        self.seed = seed
        self.mode = mode
        self.pathPersistency = float(pathPersistency or 0.0)
        self.behavior = behavior
        self.up_count = up_count
        self.up_runs = up_runs
        self.mean_up_duration = mean_up_duration
        if self.frames < 0:
            raise ValueError("frames must be non-negative")
        if behavior not in {"legacy", "patched", "patched-v2", "uk"}:
            raise ValueError("behavior must be legacy, patched, patched-v2, or uk")
        if behavior != "uk":
            if path_life is None or stability is None:
                raise ValueError("path_life and stability are required outside uk mode")
            if any(value is not None for value in (up_count, up_runs, mean_up_duration)):
                raise ValueError("U/K inputs are only valid in behavior='uk'")
            baseline_behavior = "legacy" if behavior == "legacy" else "patched"
            self._delegate = _BASE.SPCTimelineBlockGenerator(
                self.frames,
                path_life,
                stability,
                seed,
                mode,
                pathPersistency,
                baseline_behavior,
            )
        else:
            if stability is not None:
                raise ValueError("uk mode does not accept stability")
            if mode != "blocks":
                raise ValueError("uk mode requires mode='blocks' to guarantee exact K")
            if (up_count is None) == (path_life is None):
                raise ValueError("provide exactly one of up_count or path_life")
            if (up_runs is None) == (mean_up_duration is None):
                raise ValueError("provide exactly one of up_runs or mean_up_duration")
            U = int(up_count) if up_count is not None else int(round(self.frames * float(path_life)))
            if U < 0 or U > self.frames:
                raise ValueError("up_count must be in 0..frames")
            D = self.frames - U
            K_max = 0 if U == 0 else (1 if D == 0 else min(U, D + 1))
            if mean_up_duration is not None:
                if U == 0:
                    raise ValueError("mean_up_duration is undefined when U=0")
                if not float(mean_up_duration) > 0:
                    raise ValueError("mean_up_duration must be positive")
                K_requested = int(round(U / float(mean_up_duration)))
            else:
                K_requested = int(up_runs)  # type: ignore[arg-type]
            valid = (U == 0 and K_requested == 0) or (U == self.frames and K_requested == 1)
            if not valid and not (0 < U < self.frames and 1 <= K_requested <= K_max):
                raise InfeasibleTimeline(U, D, K_requested, K_max)
            if U == 0:
                exact_stability = 0.0
            elif U == self.frames or U == 1:
                exact_stability = 1.0
            else:
                exact_stability = 1.0 - (K_requested - 1) / (U - 1)
            self.up_count = U
            self.up_runs = K_requested
            self.path_life = U / self.frames if self.frames else 0.0
            self.stability = exact_stability
            self._delegate = _BASE.SPCTimelineBlockGenerator(
                self.frames,
                self.path_life,
                exact_stability,
                seed,
                "blocks",
                pathPersistency,
                "patched",
            )
        self.last_timeline: list[bool] = []
        self.last_path_ids: list[int | None] = []

    def generate_blocks(self) -> dict[str, Any]:
        result = self._delegate.generate_blocks()
        self.last_timeline = self._delegate.last_timeline
        self.last_path_ids = self._delegate.last_path_ids
        if self.behavior == "uk" and self.up_runs is not None and 0 < self.up_count < self.frames:
            realized_u = sum(self.last_timeline)
            realized_k = sum(
                state and (index == 0 or not self.last_timeline[index - 1])
                for index, state in enumerate(self.last_timeline)
            )
            if realized_u != self.up_count or realized_k != self.up_runs:
                raise RuntimeError(
                    f"exact quota invariant failed: requested U={self.up_count}, K={self.up_runs}; "
                    f"realized U={realized_u}, K={realized_k}"
                )
        return result
