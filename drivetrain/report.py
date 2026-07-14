"""Summary statistics and a human-readable markdown report."""

from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

from .config import Config
from .events import summarize_runs

logger = logging.getLogger("drivetrain")


def build_summary(df: pd.DataFrame, events: Dict[str, pd.DataFrame], cfg: Config) -> Dict[str, Any]:
    """Compute the headline metrics a drivetrain engineer looks at first.

    "Peak" figures use a fault-robust percentile (``cfg.robust_pct``) rather
    than raw maxima, which in this log are dominated by sensor glitches.
    """
    t = df[cfg.time_col].to_numpy()
    v = df["v"].to_numpy()
    dt = 1.0 / cfg.resample_hz
    moving = v > 2.0
    rob = df.attrs.get("robust", {})

    slip = df["slip_ratio"].to_numpy()
    wheelspin_mask = (slip > cfg.thresholds.slip_ratio_pct) & (v > 3.0)
    spin_runs = summarize_runs(df, cfg, wheelspin_mask, "slip_ratio", min_duration_s=0.1)

    s = {
        "duration_s": round(float(t[-1] - t[0]) if len(t) > 1 else 0.0, 1),
        "moving_time_s": round(float(moving.sum()) * dt, 1),
        "distance_km": round(float(df["distance"].iloc[-1]) / 1000.0, 3),
        "max_speed_kmh": rob.get("speed_kmh", round(float(df["speed_kmh"].max()), 1)),
        "abs_max_speed_kmh": round(float(df["speed_kmh"].max()), 1),
        "avg_moving_speed_kmh": round(float(df["speed_kmh"][moving].mean()) if moving.any() else 0.0, 1),
        "accel_g": rob.get("accel_g", 0.0),
        "brake_g": rob.get("brake_g", 0.0),
        "peak_slip_pct": rob.get("slip_pct", 0.0),
        "abs_peak_slip_pct": round(float(slip.max()), 1),
        "median_slip_pct": round(float(np.median(slip[moving])) if moving.any() else 0.0, 1),
        "pct_time_wheelspin": round(float(wheelspin_mask.mean()) * 100.0, 1),
        "avg_traction": round(float(df["traction"].to_numpy()[moving].mean()) if moving.any() else 1.0, 3),
        "worst_imbalance_rpm": round(float(np.percentile(df["delta_rpm"].abs(), cfg.robust_pct)), 1),
        "n_wheelspin_events": int(len(spin_runs)),
        "n_slip_events": int(len(summarize_runs(
            df, cfg,
            (df["rr_rate_rpm_s"].abs() > cfg.thresholds.slip_rate_rpm_s)
            | (df["rl_rate_rpm_s"].abs() > cfg.thresholds.slip_rate_rpm_s),
            "rr_rate_rpm_s", min_duration_s=0.0))),
        "n_launches": int(len(events.get("launches", []))),
        "n_braking": int(len(events.get("braking", []))),
    }
    s["_spin_runs"] = spin_runs
    return s


def render_markdown(df: pd.DataFrame, summary: Dict[str, Any], cfg: Config) -> str:
    v = cfg.vehicle
    pct = cfg.robust_pct
    spin = summary.get("_spin_runs", pd.DataFrame())
    if len(spin):
        spin = spin.reindex(spin["peak"].abs().sort_values(ascending=False).index).head(5)

    lines = [
        "# Sun Devil Motorsports — Drivetrain Analysis",
        "",
        f"**Source:** `{cfg.input_csv}`  ",
        f"**Session:** {summary['duration_s']} s "
        f"({summary['moving_time_s']} s moving · {summary['distance_km']} km travelled)",
        "",
        "## Performance envelope",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Top speed (P{pct:g}) | **{summary['max_speed_kmh']} km/h** "
        f"(abs max {summary['abs_max_speed_kmh']}) |",
        f"| Avg moving speed | {summary['avg_moving_speed_kmh']} km/h |",
        f"| Peak acceleration (P{pct:g}) | **{summary['accel_g']} g** |",
        f"| Peak braking (P{pct:g}) | **{summary['brake_g']} g** |",
        f"| Hard-accel phases | {summary['n_launches']} |",
        f"| Hard-braking phases | {summary['n_braking']} |",
        "",
        "## Traction & differential",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Median differential slip | {summary['median_slip_pct']} % |",
        f"| Peak differential slip (P{pct:g}) | **{summary['peak_slip_pct']} %** "
        f"(abs max {summary['abs_peak_slip_pct']}) |",
        f"| Average traction index | {summary['avg_traction']} (1.0 = no slip) |",
        f"| Time in wheelspin | {summary['pct_time_wheelspin']} % |",
        f"| Wheelspin events | {summary['n_wheelspin_events']} |",
        f"| Angular-accel slip events | {summary['n_slip_events']} |",
        f"| Worst wheel-speed imbalance (P{pct:g}) | {summary['worst_imbalance_rpm']} rpm |",
        "",
        "## Worst wheelspin events",
        "",
    ]
    if len(spin):
        lines += ["| t (s) | duration (s) | peak slip (%) |", "| --- | --- | --- |"]
        for _, r in spin.iterrows():
            lines.append(f"| {r['t_peak']} | {r['duration_s']} | {r['peak']:.0f} |")
    else:
        lines.append("_No sustained wheelspin above threshold._")

    lines += [
        "",
        "## Model & assumptions",
        "",
        f"- Tyre loaded radius **{v.tire_radius_m} m** → speed & distance scale from this.",
        f"- Longitudinal g = d/dt of speed low-passed at **{cfg.accel_cutoff_hz} Hz**; "
        f'"peak" figures use the **P{pct:g}** percentile to reject sensor glitches.',
        "- Differential slip uses the slower rear wheel as a ground-speed proxy "
        "(no non-driven wheel is logged), so it is a robust estimate, not an absolute.",
        "",
        "> **Not reported on purpose:** lateral g / yaw / a dead-reckoned track map. "
        "Only the two driven-wheel speeds are logged, and their split here is dominated "
        "by *wheelspin*, not cornering — deriving chassis yaw from it produces "
        "non-physical (>3 g) results. This tool reports what the data can defend.",
        "",
    ]
    return "\n".join(lines)
