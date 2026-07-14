"""Shared fixtures: synthetic runs with analytically-known drivetrain physics."""

import numpy as np
import pandas as pd
import pytest

from drivetrain.config import Config


@pytest.fixture
def cfg():
    c = Config()
    c.resample_hz = 50.0
    return c


@pytest.fixture
def constant_accel(cfg):
    """Both wheels rolling equally, speed ramping at a known longitudinal g.

    v(t) = a*t with a = 0.5 g. Wheels equal -> zero differential slip, and the
    derived a_long must recover 0.5 g in the interior (away from filter edges).
    """
    v = cfg.vehicle
    fs = cfg.resample_hz
    t = np.arange(0, 12, 1 / fs)
    a = 0.5 * 9.80665                 # m/s^2
    speed = a * t                     # m/s
    rpm = speed / v.rpm_to_mps
    df = pd.DataFrame({
        cfg.time_col: t,
        cfg.rr_col: rpm,
        cfg.rl_col: rpm,
        cfg.steer_col: np.zeros_like(t),
    })
    df.attrs["a_g"] = 0.5
    return df


@pytest.fixture
def wheelspin(cfg):
    """Right wheel spins 30% faster than the left at constant vehicle speed."""
    fs = cfg.resample_hz
    t = np.arange(0, 10, 1 / fs)
    base = 600.0
    df = pd.DataFrame({
        cfg.time_col: t,
        cfg.rr_col: np.full_like(t, base * 1.30),
        cfg.rl_col: np.full_like(t, base),
        cfg.steer_col: np.zeros_like(t),
    })
    df.attrs["slip_pct"] = 30.0
    return df
