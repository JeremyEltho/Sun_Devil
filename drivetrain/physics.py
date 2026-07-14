"""Drivetrain physics — honest channels the data can actually support.

This dataset is *traction / differential test* telemetry: only the two rear
(driven) wheel speeds and steering are logged. A key, hard-won finding drove
this module's design:

    The RR-RL wheel-speed split does **not** represent chassis yaw here.
    With an open / limited-slip differential the big splits are *wheelspin*
    (one driven wheel racing ahead under power), not cornering. Converting the
    split to yaw -> lateral-g gives physically impossible numbers (>3 g even
    after aggressive low-pass filtering). So we do **not** fabricate lateral
    acceleration, a "traction circle", or a dead-reckoned track map from it.

What we *can* compute cleanly and defend:

===================  =========================================================
column               meaning                                            source
===================  =========================================================
v_r, v_l             right / left rear contact-patch speed   [m/s]   measured
v                    axle-centre (vehicle) speed             [m/s]   measured
speed_kmh            vehicle speed                           [km/h]  measured
a_long               longitudinal acceleration (low-passed dv/dt) [g] derived
delta_rpm            RR - RL wheel-speed split               [rpm]   measured
slip_speed           |fast - slow| rear-wheel speed          [m/s]   measured
slip_ratio           (fast-slow)/slow  -> differential slip  [%]     derived
rr_rate, rl_rate     per-wheel angular acceleration          [rpm/s] derived
traction             1 - slip_ratio/100, clipped [0,1]       [-]     derived
distance             integrated distance travelled           [m]     derived
steer_ctr            steering, zero-offset removed           [deg]   measured
===================  =========================================================
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

from .config import Config

logger = logging.getLogger("drivetrain")

G = 9.80665  # m/s^2


def _lowpass(x: np.ndarray, cutoff_hz: float, fs: float, order: int = 2) -> np.ndarray:
    """Zero-phase Butterworth low-pass. Falls back to the raw signal if short."""
    nyq = fs / 2.0
    wn = min(cutoff_hz / nyq, 0.99)
    n = len(x)
    if n <= order * 3 or wn <= 0:
        return np.asarray(x, dtype=float)
    b, a = butter(order, wn)
    padlen = 3 * max(len(a), len(b))
    if n <= padlen:
        return np.asarray(x, dtype=float)
    return filtfilt(b, a, x)


def _cumtrapz(y: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Cumulative trapezoidal integral with a leading zero (same length as y)."""
    out = np.zeros_like(y, dtype=float)
    if len(y) > 1:
        out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(t))
    return out


def derive_channels(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Compute drivetrain channels on a uniform-time frame."""
    df = df.copy()
    veh = cfg.vehicle
    fs = cfg.resample_hz
    dt = 1.0 / fs
    t = df[cfg.time_col].to_numpy(dtype=float)
    k = veh.rpm_to_mps

    rr = df[cfg.rr_col].to_numpy(dtype=float)
    rl = df[cfg.rl_col].to_numpy(dtype=float)

    df["v_r"] = rr * k
    df["v_l"] = rl * k

    # vehicle speed = axle-centre, gently low-passed (encoder rpm is integer-quantised)
    v_raw = 0.5 * (df["v_r"].to_numpy() + df["v_l"].to_numpy())
    v = _lowpass(v_raw, cfg.accel_cutoff_hz * 2.0, fs)
    df["v"] = v
    df["speed_kmh"] = v * 3.6

    # longitudinal acceleration: derivative of a properly band-limited speed.
    # (differentiating raw quantised speed explodes into noise; the low-pass is
    #  what makes a_long physically meaningful.)
    v_smooth = _lowpass(v_raw, cfg.accel_cutoff_hz, fs)
    df["a_long"] = np.gradient(v_smooth, dt) / G

    # ── differential / traction ─────────────────────────────────────────────
    df["delta_rpm"] = rr - rl
    fast = np.maximum(rr, rl)
    slow = np.minimum(rr, rl)
    df["fast_rpm"] = fast
    df["slow_rpm"] = slow
    df["slip_speed"] = (fast - slow) * k                      # m/s of driven-wheel overspin
    # differential slip ratio: how much faster the racing wheel turns than the
    # gripping one. slow wheel is the best available ground-speed proxy (no
    # non-driven wheel is logged), so this is a proxy — but a robust, honest one.
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = (fast - slow) / np.where(slow > 5.0, slow, np.nan) * 100.0
    df["slip_ratio"] = np.where(slow > 5.0, ratio, 0.0)
    df["traction"] = np.clip(1.0 - df["slip_ratio"].to_numpy() / 100.0, 0.0, 1.0)

    # per-wheel angular acceleration (spin-up / lock-up signature)
    df["rr_rate_rpm_s"] = np.gradient(_lowpass(rr, cfg.accel_cutoff_hz * 2, fs), dt)
    df["rl_rate_rpm_s"] = np.gradient(_lowpass(rl, cfg.accel_cutoff_hz * 2, fs), dt)

    df["distance"] = _cumtrapz(v, t)

    # steering as context only (zero-offset removed; NOT used to fabricate yaw)
    if cfg.steer_col in df.columns:
        steer = df[cfg.steer_col].to_numpy(dtype=float)
        moving = v > 3.0
        offset = float(np.median(steer[moving])) if moving.sum() > 50 else float(np.median(steer))
        df["steer_ctr"] = steer - offset
        df.attrs["steer_offset"] = offset

    df.attrs["robust"] = _robust_stats(df, cfg)
    logger.info(
        "Derived: peak %.1f km/h, %.2f g accel / %.2f g brake (%.1f%%ile), max slip %.0f%%",
        df["speed_kmh"].max(),
        df.attrs["robust"]["accel_g"], df.attrs["robust"]["brake_g"],
        cfg.robust_pct, df["slip_ratio"].max(),
    )
    return df


def _robust_stats(df: pd.DataFrame, cfg: Config) -> dict:
    """Fault-robust peak values (high/low percentiles, not glitch-prone maxima)."""
    v = df["v"].to_numpy()
    moving = v > 2.0
    a = df["a_long"].to_numpy()
    a_move = a[moving] if moving.any() else a
    p = cfg.robust_pct
    return {
        "accel_g": round(float(np.percentile(a_move, p)), 2),
        "brake_g": round(float(np.percentile(a_move, 100 - p)), 2),
        "speed_kmh": round(float(np.percentile(df["speed_kmh"].to_numpy()[moving] if moving.any()
                                               else df["speed_kmh"].to_numpy(), p)), 1),
        "slip_pct": round(float(np.percentile(df["slip_ratio"].to_numpy(), p)), 1),
    }
