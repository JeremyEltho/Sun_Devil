"""Data ingest, cleaning and uniform resampling.

The raw log is ~500 Hz but not perfectly evenly sampled. Derivatives (accel,
yaw, jerk) and any frequency-aware smoothing need a *uniform* time base, so the
pipeline is:

    load_data  ->  clean_data  ->  resample_uniform

``load_data`` returns the untouched raw frame (for "raw vs cleaned" overlays)
plus a validated copy. ``resample_uniform`` puts everything on an even grid.
"""

from __future__ import annotations

import logging
import os
from typing import Tuple

import numpy as np
import pandas as pd

from .config import Config

logger = logging.getLogger("drivetrain")


def load_data(cfg: Config) -> pd.DataFrame:
    """Read the CSV, validate columns, sort by time. Returns the raw frame."""
    if not os.path.exists(cfg.input_csv):
        raise FileNotFoundError(f"CSV not found: {cfg.input_csv}")

    data = pd.read_csv(cfg.input_csv)
    logger.info("Loaded %d rows from %s", len(data), cfg.input_csv)

    required = [cfg.time_col, cfg.rr_col, cfg.rl_col]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    if cfg.steer_col not in data.columns:
        logger.warning("Steering column absent — geometry/steering channels disabled")

    data = data.sort_values(cfg.time_col).reset_index(drop=True)
    return data


def _hampel(series: pd.Series, window: int, n_sigma: float, min_abs: float = 25.0) -> pd.Series:
    """Hampel filter: replace outliers with the local median.

    Wheel-speed encoders throw glitches — single-sample spikes and short
    "stuck" blocks (missed/extra teeth, electrical noise) — that become an
    *enormous* fake acceleration once differentiated, so they must be rejected
    *before* any physics. A point is an outlier when it lies more than
    ``n_sigma`` robust sigmas (1.4826·MAD) *and* at least ``min_abs`` rpm from
    the local median. The absolute floor stops the filter from nibbling at
    genuine quantisation noise in flat/idle regions (where MAD→0), so it only
    touches real faults.
    """
    med = series.rolling(window, center=True, min_periods=1).median()
    dev = (series - med).abs()
    mad = dev.rolling(window, center=True, min_periods=1).median()
    sigma = 1.4826 * mad
    outlier = (dev > (n_sigma * sigma)) & (dev > min_abs)
    return series.where(~outlier, med), int(outlier.sum())


def clean_data(data: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Coerce to numeric, drop NaNs, then de-spike the wheel channels.

    Unlike the original tool this *keeps* standstill (0 rpm) samples — a race
    engineer cares about launches and stops — and only removes readings above
    ``max_rpm`` (hard sensor faults) and non-numeric rows. Transient encoder
    glitches are then repaired with a Hampel median filter rather than being
    left to poison the derivatives. An optional rolling z-score gate remains
    available for very noisy logs.
    """
    data = data.copy()
    wheels = [cfg.rr_col, cfg.rl_col]
    data[wheels] = data[wheels].apply(pd.to_numeric, errors="coerce")

    n0 = len(data)
    data = data.dropna(subset=wheels)
    data = data[
        data[cfg.rr_col].between(cfg.min_rpm, cfg.max_rpm)
        & data[cfg.rl_col].between(cfg.min_rpm, cfg.max_rpm)
    ].reset_index(drop=True)
    logger.info("Dropped %d invalid/spike rows, %d remain", n0 - len(data), len(data))

    # Physical rate limiter: a rotating wheel cannot change speed faster than
    # ``max_wheel_accel`` rpm/s. Any per-sample jump beyond that (e.g. a missed
    # encoder tooth reading double, or a 1-sample dropout) is non-physical, so
    # we null it and interpolate. This kills the sharp spikes the median filter
    # can miss and is what stops "316% slip for one sample" artefacts.
    dt = data[cfg.time_col].diff().clip(lower=1e-4)
    max_jump = cfg.max_wheel_accel * dt
    zapped = 0
    for c in wheels:
        glitch = data[c].diff().abs() > max_jump
        zapped += int(glitch.sum())
        data.loc[glitch, c] = np.nan
    data[wheels] = data[wheels].interpolate(limit_direction="both")
    logger.info("Rate limiter nulled %d non-physical samples", zapped)

    if cfg.hampel_window > 1:
        repaired = 0
        for c in wheels:
            data[c], n = _hampel(data[c], cfg.hampel_window, cfg.hampel_sigma)
            repaired += n
        logger.info("Hampel filter repaired %d glitch samples", repaired)

    z = cfg.thresholds.z_score
    if z > 0:
        win = cfg.rolling_window
        means = data[wheels].rolling(win, center=True).mean()
        stds = data[wheels].rolling(win, center=True).std().replace(0, 1)
        zsc = (data[wheels] - means) / stds
        before = len(data)
        data = data[(zsc.abs() <= z).all(axis=1)]
        logger.info("Z-score gate (%.1f) removed %d rows", z, before - len(data))

    return data.reset_index(drop=True)


def resample_uniform(data: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Interpolate all channels onto an even ``resample_hz`` time grid.

    Linear interpolation on the (already cleaned, monotonic) time base. The
    even grid is what makes Savitzky-Golay derivatives and load-transfer maths
    well-defined downstream.
    """
    t = data[cfg.time_col].to_numpy(dtype=float)
    if len(t) < 2:
        raise ValueError("Not enough samples to resample")

    dt = 1.0 / cfg.resample_hz
    grid = np.arange(t[0], t[-1] + dt, dt)

    out = {cfg.time_col: grid}
    cols = [cfg.rr_col, cfg.rl_col]
    if cfg.steer_col in data.columns:
        cols.append(cfg.steer_col)
    for c in cols:
        out[c] = np.interp(grid, t, data[c].to_numpy(dtype=float))

    res = pd.DataFrame(out)
    logger.info("Resampled to %.0f Hz -> %d rows", cfg.resample_hz, len(res))
    return res


def full_ingest(cfg: Config) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience: load -> clean -> resample. Returns (raw, uniform)."""
    raw = load_data(cfg)
    cleaned = clean_data(raw, cfg)
    uniform = resample_uniform(cleaned, cfg)
    return raw, uniform
