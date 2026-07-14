"""Drivetrain event detection.

Operates on the derived-channel frame from :mod:`drivetrain.physics`. Each
detector returns a DataFrame of flagged samples so events can be tabulated in
the report and overlaid on the plots.

Detectors
---------
* **wheelspin** — sustained differential slip: one driven wheel racing ahead of
  the other (open/limited-slip diff losing traction under power).
* **slip**      — per-wheel angular-acceleration spikes (rapid spin-up / lock-up).
* **diff_load** — raw |RR-RL| imbalance (kept for backward compatibility).
* **launch / braking** — hard longitudinal-acceleration phases.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .config import Config

logger = logging.getLogger("drivetrain")


def contiguous_runs(mask: np.ndarray) -> List[Tuple[int, int]]:
    """Return [(start_idx, end_idx_inclusive), ...] runs where mask is True."""
    if not mask.any():
        return []
    idx = np.flatnonzero(mask)
    breaks = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate(([idx[0]], idx[breaks + 1]))
    ends = np.concatenate((idx[breaks], [idx[-1]]))
    return list(zip(starts.tolist(), ends.tolist()))


def summarize_runs(df: pd.DataFrame, cfg: Config, mask: np.ndarray, value_col: str,
                   min_duration_s: float = 0.05) -> pd.DataFrame:
    """Collapse a boolean mask into discrete events with duration and peak.

    Turns "3,400 flagged samples" into "22 events, worst 41% for 0.8 s at
    t=142.5 s" — what an engineer actually reads.
    """
    t = df[cfg.time_col].to_numpy()
    val = df[value_col].to_numpy()
    rows = []
    for s, e in contiguous_runs(mask):
        dur = float(t[e] - t[s])
        if dur < min_duration_s:
            continue
        seg = val[s:e + 1]
        peak_i = s + int(np.argmax(np.abs(seg)))
        rows.append({
            "t_start": round(float(t[s]), 2),
            "t_end": round(float(t[e]), 2),
            "duration_s": round(dur, 2),
            "peak": round(float(val[peak_i]), 1),
            "t_peak": round(float(t[peak_i]), 2),
        })
    return pd.DataFrame(rows)


def detect_wheelspin(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Flag sustained differential slip beyond ``slip_ratio_pct``."""
    thr = cfg.thresholds.slip_ratio_pct
    mask = (df["slip_ratio"].to_numpy() > thr) & (df["v"].to_numpy() > 3.0)
    events = df.loc[mask].copy()
    logger.info("%d wheelspin samples (>%.0f%% differential slip)", len(events), thr)
    return events.round(3)


def detect_slip(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Flag angular-acceleration spikes on either wheel (spin-up / lock-up)."""
    thr = cfg.thresholds.slip_rate_rpm_s
    mask = (df["rr_rate_rpm_s"].abs() > thr) | (df["rl_rate_rpm_s"].abs() > thr)
    events = df.loc[mask].copy()
    logger.info("%d slip samples (>%.0f rpm/s)", len(events), thr)
    return events.round(3)


def detect_diff_load(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Raw |RR-RL| imbalance flag (backward compatible)."""
    thr = cfg.thresholds.diff_rpm
    diff = df["delta_rpm"].abs()
    events = df.loc[diff > thr].copy()
    events["difference"] = diff[diff > thr]
    logger.info("%d differential-load samples (>%.0f rpm)", len(events), thr)
    return events.round(3)


def detect_launches(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Hard-acceleration phases (a_long above launch_g)."""
    mask = df["a_long"].to_numpy() > cfg.thresholds.launch_g
    return summarize_runs(df, cfg, mask, "a_long", min_duration_s=0.3)


def detect_braking(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Hard-braking phases (a_long below -brake_g)."""
    mask = df["a_long"].to_numpy() < -cfg.thresholds.brake_g
    return summarize_runs(df, cfg, mask, "a_long", min_duration_s=0.3)


def detect_all(df: pd.DataFrame, cfg: Config) -> Dict[str, pd.DataFrame]:
    """Run every detector. Returns a dict keyed by event type."""
    return {
        "wheelspin": detect_wheelspin(df, cfg),
        "slip": detect_slip(df, cfg),
        "diff_load": detect_diff_load(df, cfg),
        "launches": detect_launches(df, cfg),
        "braking": detect_braking(df, cfg),
    }
