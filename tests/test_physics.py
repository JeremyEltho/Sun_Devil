"""Physics tests against synthetic runs with known answers."""

import numpy as np

from drivetrain.physics import derive_channels, _cumtrapz, _lowpass


def _mid(series):
    """Middle-of-record value, avoiding filter edge transients."""
    return float(series.iloc[len(series) // 2])


def test_vehicle_speed_recovered(cfg, constant_accel):
    df = derive_channels(constant_accel, cfg)
    t = df[cfg.time_col].iloc[len(df) // 2]
    expected = 0.5 * 9.80665 * t          # v = a*t
    assert abs(_mid(df["v"]) - expected) < 0.2


def test_longitudinal_g_recovered(cfg, constant_accel):
    df = derive_channels(constant_accel, cfg)
    assert abs(_mid(df["a_long"]) - constant_accel.attrs["a_g"]) < 0.03


def test_no_slip_when_wheels_equal(cfg, constant_accel):
    df = derive_channels(constant_accel, cfg)
    assert df["slip_ratio"].abs().max() < 1e-6
    assert _mid(df["traction"]) == 1.0


def test_slip_ratio_recovered(cfg, wheelspin):
    df = derive_channels(wheelspin, cfg)
    assert abs(_mid(df["slip_ratio"]) - wheelspin.attrs["slip_pct"]) < 0.5


def test_lowpass_passes_dc():
    x = np.full(500, 7.0)
    assert np.allclose(_lowpass(x, 2.0, 50.0), 7.0, atol=1e-6)


def test_cumtrapz_matches_linear_integral():
    t = np.linspace(0, 10, 500)
    y = np.full_like(t, 3.0)              # integral of 3 over [0,10] = 30
    assert abs(_cumtrapz(y, t)[-1] - 30.0) < 1e-6
