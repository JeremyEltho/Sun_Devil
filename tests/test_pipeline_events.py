"""Pipeline cleaning + event-detection tests."""

import numpy as np
import pandas as pd

from drivetrain.pipeline import clean_data, resample_uniform, _hampel
from drivetrain.physics import derive_channels
from drivetrain.events import detect_slip, detect_wheelspin, contiguous_runs


def _raw(cfg, n=500):
    t = np.linspace(0, 5, n)
    return pd.DataFrame({
        cfg.time_col: t,
        cfg.rr_col: np.full(n, 500.0),
        cfg.rl_col: np.full(n, 480.0),
        cfg.steer_col: np.zeros(n),
    })


def test_clean_drops_hard_faults(cfg):
    df = _raw(cfg)
    df.loc[10, cfg.rr_col] = 999999      # above max_rpm
    df.loc[20, cfg.rl_col] = np.nan      # dropout
    cleaned = clean_data(df, cfg)
    assert cleaned[cfg.rr_col].max() <= cfg.max_rpm
    assert not cleaned[[cfg.rr_col, cfg.rl_col]].isna().any().any()


def test_hampel_repairs_isolated_spike(cfg):
    s = pd.Series(np.full(200, 500.0))
    s.iloc[100] = 1800.0                  # single glitch, within max_rpm
    repaired, n = _hampel(s, cfg.hampel_window, cfg.hampel_sigma)
    assert n >= 1
    assert abs(repaired.iloc[100] - 500.0) < 1e-6


def test_resample_is_uniform(cfg):
    res = resample_uniform(_raw(cfg), cfg)
    dt = np.diff(res[cfg.time_col].to_numpy())
    assert np.allclose(dt, 1 / cfg.resample_hz, atol=1e-9)


def test_contiguous_runs_groups_spans():
    mask = np.array([0, 1, 1, 0, 0, 1, 0, 1, 1, 1], dtype=bool)
    assert contiguous_runs(mask) == [(1, 2), (5, 5), (7, 9)]


def test_slip_detects_rapid_spinup(cfg):
    # a realistic spin-up: +900 rpm over 0.2 s ~= 4500 rpm/s (> threshold)
    df = _raw(cfg, n=500)
    ramp = np.linspace(500, 1400, 20)
    df.loc[250:269, cfg.rr_col] = ramp
    df.loc[270:, cfg.rr_col] = 1400
    derived = derive_channels(resample_uniform(df, cfg), cfg)
    assert derived["rr_rate_rpm_s"].abs().max() > cfg.thresholds.slip_rate_rpm_s
    assert not detect_slip(derived, cfg).empty


def test_wheelspin_flagged(cfg):
    df = _raw(cfg)
    df[cfg.rr_col] = 800.0
    df[cfg.rl_col] = 500.0               # 60% differential slip
    derived = derive_channels(resample_uniform(df, cfg), cfg)
    assert not detect_wheelspin(derived, cfg).empty
    assert derived["slip_ratio"].max() > cfg.thresholds.slip_ratio_pct
