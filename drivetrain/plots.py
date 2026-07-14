"""Publication-quality drivetrain dashboard (dark theme).

Every panel is grounded in a directly-measured or defensibly-derived channel
(see :mod:`drivetrain.physics`): wheel & vehicle speed, longitudinal g,
differential slip and wheelspin. No fabricated lateral-g / yaw / track map.

* :func:`render_dashboard` — the seven-panel session dashboard.
* :func:`render_wheelspin_detail` — zoomed wheel traces around the worst
  wheelspin event (the "what actually happened" view).
"""

from __future__ import annotations

import logging
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd

from .config import Config

logger = logging.getLogger("drivetrain")

CLR = {
    "left": "#4fc3f7", "right": "#ff9800", "speed": "#eeeeee",
    "spin": "#ef5350", "accel": "#66bb6a", "brake": "#ffca28",
    "slip": "#ec407a", "steer": "#ce93d8", "muted": "#666666", "grid": "#1e1e1e",
}


def _style():
    matplotlib.rcParams.update({
        "figure.facecolor": "#0b0b0d", "axes.facecolor": "#111114",
        "savefig.facecolor": "#0b0b0d", "axes.edgecolor": "#2a2a30",
        "axes.labelcolor": "#b8b8c0", "axes.titlecolor": "#f0f0f4",
        "axes.titlesize": 10.5, "axes.titleweight": "bold",
        "grid.color": CLR["grid"], "grid.linewidth": 0.7,
        "xtick.color": CLR["muted"], "ytick.color": CLR["muted"],
        "text.color": "#dddde2", "legend.framealpha": 0.15, "legend.edgecolor": "#333",
        "legend.fontsize": 7.5, "font.family": "monospace", "font.size": 8.5,
    })


def _grid(ax, xlabel=None, ylabel=None, title=None, legend=True, loc="upper right"):
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.grid(True, zorder=0)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
    if legend:
        ax.legend(loc=loc)


def _shade_runs(ax, t, mask, color, alpha=0.16, label=None):
    """Shade contiguous True spans of ``mask`` along the x (time) axis."""
    from .events import contiguous_runs
    first = True
    for s, e in contiguous_runs(mask):
        ax.axvspan(t[s], t[e], color=color, alpha=alpha, lw=0,
                   label=label if first else None, zorder=0)
        first = False


# ── panels ───────────────────────────────────────────────────────────────────

def _panel_overview(ax, raw, df, cfg):
    t = df[cfg.time_col].to_numpy()
    ax.plot(raw[cfg.time_col], raw[cfg.rl_col], color=CLR["left"], lw=0.4, alpha=0.22, zorder=1)
    ax.plot(raw[cfg.time_col], raw[cfg.rr_col], color=CLR["right"], lw=0.4, alpha=0.22, zorder=1)
    ax.plot(t, df[cfg.rl_col], color=CLR["left"], lw=1.0, label="Left rear", zorder=3)
    ax.plot(t, df[cfg.rr_col], color=CLR["right"], lw=1.0, label="Right rear", zorder=3)
    spin = (df["slip_ratio"].to_numpy() > cfg.thresholds.slip_ratio_pct) & (df["v"].to_numpy() > 3)
    _shade_runs(ax, t, spin, CLR["spin"], 0.14, "Wheelspin")
    ax.set_ylabel("Wheel speed (rpm)")
    ax.grid(True, zorder=0)

    ax2 = ax.twinx()
    ax2.plot(t, df["speed_kmh"], color=CLR["speed"], lw=1.2, alpha=0.85, label="Vehicle km/h")
    ax2.set_ylabel("Vehicle speed (km/h)", color=CLR["speed"])
    ax2.tick_params(axis="y", colors=CLR["speed"])
    l1, la1 = ax.get_legend_handles_labels()
    l2, la2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, la1 + la2, loc="upper right", ncol=3)
    ax.set_title("Session overview — wheel & vehicle speed (wheelspin shaded)")
    ax.set_xlabel("Time (s)")


def _panel_longitudinal(ax, df, cfg):
    t = df[cfg.time_col].to_numpy()
    a = df["a_long"].to_numpy()
    ax.plot(t, df["speed_kmh"], color=CLR["speed"], lw=1.0, label="Speed", zorder=3)
    ax.set_ylabel("Speed (km/h)")
    ax.grid(True, zorder=0)
    ax2 = ax.twinx()
    ax2.axhline(0, color=CLR["muted"], lw=0.5)
    ax2.fill_between(t, a, 0, where=a > 0, color=CLR["accel"], alpha=0.35, label="accel")
    ax2.fill_between(t, a, 0, where=a < 0, color=CLR["brake"], alpha=0.35, label="brake")
    ax2.set_ylabel("Longitudinal g", color=CLR["accel"])
    ax2.tick_params(axis="y", colors=CLR["accel"])
    lim = max(0.5, np.percentile(np.abs(a), 99.5) * 1.2)
    ax2.set_ylim(-lim, lim)
    l1, la1 = ax.get_legend_handles_labels()
    l2, la2 = ax2.get_legend_handles_labels()
    ax.legend(l1 + l2, la1 + la2, loc="upper right")
    ax.set_title("Longitudinal performance")
    ax.set_xlabel("Time (s)")


def _panel_diffslip(ax, df, cfg):
    t = df[cfg.time_col].to_numpy()
    slip = df["slip_ratio"].to_numpy()
    ax.plot(t, slip, color=CLR["slip"], lw=0.7, zorder=3, label="differential slip")
    ax.axhline(cfg.thresholds.slip_ratio_pct, color=CLR["spin"], ls=":", lw=0.9,
               label=f"wheelspin thresh ({cfg.thresholds.slip_ratio_pct:.0f}%)")
    ax.fill_between(t, slip, cfg.thresholds.slip_ratio_pct,
                    where=slip > cfg.thresholds.slip_ratio_pct,
                    color=CLR["spin"], alpha=0.3, zorder=2)
    ax.set_ylim(0, min(100, np.percentile(slip, 99.9) * 1.3 + 5))
    _grid(ax, "Time (s)", "Slip (fast/slow − 1) [%]", "Differential slip / wheelspin")


def _panel_traction_map(ax, df, cfg):
    v = df["speed_kmh"].to_numpy()
    slip = df["slip_ratio"].to_numpy()
    a = df["a_long"].to_numpy()
    m = v > 3
    sc = ax.scatter(v[m], slip[m], c=a[m], cmap="RdYlGn", s=5, alpha=0.5,
                    vmin=-1, vmax=1, edgecolors="none")
    cb = ax.figure.colorbar(sc, ax=ax, pad=0.02, fraction=0.05)
    cb.set_label("long g", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    ax.axhline(cfg.thresholds.slip_ratio_pct, color=CLR["spin"], ls=":", lw=0.9)
    ax.set_ylim(0, min(100, np.percentile(slip[m], 99.5) * 1.3 + 5))
    _grid(ax, "Vehicle speed (km/h)", "Differential slip (%)",
          "Traction map — slip vs speed (colour = g)", legend=False)


def _panel_wheel_scatter(ax, df, cfg):
    slow = df["slow_rpm"].to_numpy()
    fast = df["fast_rpm"].to_numpy()
    v = df["speed_kmh"].to_numpy()
    m = df["v"].to_numpy() > 3
    sc = ax.scatter(slow[m], fast[m], c=v[m], cmap="viridis", s=4, alpha=0.4, edgecolors="none")
    cb = ax.figure.colorbar(sc, ax=ax, pad=0.02, fraction=0.05)
    cb.set_label("km/h", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    hi = max(fast[m].max(), slow[m].max()) if m.any() else 1
    ax.plot([0, hi], [0, hi], color=CLR["muted"], lw=0.9, ls="--", label="1:1 (locked)")
    _grid(ax, "Slower wheel (rpm)", "Faster wheel (rpm)",
          "Wheel coupling — off the line = slip")


def _panel_hist(ax, df, cfg):
    a = df["a_long"].to_numpy()
    a = a[np.abs(a) < 3]
    ax.hist(a, bins=80, color=CLR["accel"], alpha=0.85)
    ax.axvline(0, color=CLR["muted"], lw=0.7)
    ax.axvline(np.percentile(df["a_long"], cfg.robust_pct), color=CLR["accel"], ls=":", lw=1)
    ax.axvline(np.percentile(df["a_long"], 100 - cfg.robust_pct), color=CLR["brake"], ls=":", lw=1)
    _grid(ax, "Longitudinal g", "Samples", "Acceleration distribution", legend=False)


def _panel_stats(ax, summary, cfg):
    ax.axis("off")
    ax.set_title("Session summary", loc="left")
    rows = [
        ("TOP SPEED", f"{summary['max_speed_kmh']} km/h"),
        ("DISTANCE", f"{summary['distance_km']} km"),
        ("PEAK ACCEL", f"{summary['accel_g']} g"),
        ("PEAK BRAKE", f"{summary['brake_g']} g"),
        ("MEDIAN SLIP", f"{summary['median_slip_pct']} %"),
        ("PEAK SLIP", f"{summary['peak_slip_pct']} %"),
        ("AVG TRACTION", f"{summary['avg_traction']:.2f}"),
        ("TIME IN WHEELSPIN", f"{summary['pct_time_wheelspin']} %"),
        ("WHEELSPIN EVENTS", f"{summary['n_wheelspin_events']}"),
        ("SLIP EVENTS", f"{summary['n_slip_events']}"),
        ("LAUNCHES / BRAKES", f"{summary['n_launches']} / {summary['n_braking']}"),
    ]
    y = 0.95
    for k, val in rows:
        ax.text(0.02, y, k, fontsize=8.5, color=CLR["muted"], va="top")
        ax.text(0.98, y, val, fontsize=9.5, color="#f0f0f4", va="top", ha="right", fontweight="bold")
        y -= 0.088


def render_dashboard(raw, df, events, summary, cfg: Config,
                     save_path: Optional[str] = None, show: bool = True):
    _style()
    fig = plt.figure(figsize=(16, 18))
    gs = GridSpec(4, 2, figure=fig, hspace=0.34, wspace=0.2,
                  top=0.955, bottom=0.045, left=0.06, right=0.97,
                  height_ratios=[1.05, 1.0, 1.0, 1.0])
    _panel_overview(fig.add_subplot(gs[0, :]), raw, df, cfg)
    _panel_longitudinal(fig.add_subplot(gs[1, 0]), df, cfg)
    _panel_diffslip(fig.add_subplot(gs[1, 1]), df, cfg)
    _panel_traction_map(fig.add_subplot(gs[2, 0]), df, cfg)
    _panel_wheel_scatter(fig.add_subplot(gs[2, 1]), df, cfg)
    _panel_hist(fig.add_subplot(gs[3, 0]), df, cfg)
    _panel_stats(fig.add_subplot(gs[3, 1]), summary, cfg)

    fig.suptitle("SUN DEVIL MOTORSPORTS · REAR DRIVETRAIN ANALYSIS",
                 fontsize=15, fontweight="bold", y=0.995)
    fig.text(0.5, 0.004,
             f"top {summary['max_speed_kmh']} km/h · {summary['accel_g']}g accel / "
             f"{summary['brake_g']}g brake · {summary['pct_time_wheelspin']}% wheelspin · "
             f"traction {summary['avg_traction']:.2f}",
             ha="center", color=CLR["muted"], fontsize=9)
    if save_path:
        fig.savefig(save_path, dpi=140, bbox_inches="tight")
        logger.info("Saved dashboard -> %s", save_path)
    plt.show() if show else plt.close(fig)


def render_wheelspin_detail(df, summary, cfg: Config,
                            save_path: Optional[str] = None, show: bool = True):
    """Zoom on the single worst wheelspin event: wheel traces + slip ratio."""
    _style()
    spin = summary.get("_spin_runs", pd.DataFrame())
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [2, 1], "hspace": 0.12})
    if not len(spin):
        ax1.text(0.5, 0.5, "No sustained wheelspin events detected",
                 ha="center", va="center", transform=ax1.transAxes, color=CLR["muted"])
        ax2.axis("off")
    else:
        worst = spin.reindex(spin["peak"].abs().sort_values(ascending=False).index).iloc[0]
        t = df[cfg.time_col].to_numpy()
        pad = 1.5
        m = (t >= worst["t_start"] - pad) & (t <= worst["t_end"] + pad)
        sub = df.loc[m]
        ts = sub[cfg.time_col].to_numpy()
        ax1.plot(ts, sub[cfg.rr_col], color=CLR["right"], lw=1.6, label="Right rear")
        ax1.plot(ts, sub[cfg.rl_col], color=CLR["left"], lw=1.6, label="Left rear")
        ax1.axvspan(worst["t_start"], worst["t_end"], color=CLR["spin"], alpha=0.15,
                    label="wheelspin")
        _grid(ax1, None, "Wheel speed (rpm)",
              f"Worst wheelspin — {worst['peak']:.0f}% for {worst['duration_s']}s "
              f"@ t={worst['t_peak']}s")
        ax2.plot(ts, sub["slip_ratio"], color=CLR["slip"], lw=1.4)
        ax2.axhline(cfg.thresholds.slip_ratio_pct, color=CLR["spin"], ls=":", lw=0.9)
        ax2.fill_between(ts, sub["slip_ratio"], cfg.thresholds.slip_ratio_pct,
                         where=sub["slip_ratio"] > cfg.thresholds.slip_ratio_pct,
                         color=CLR["spin"], alpha=0.3)
        _grid(ax2, "Time (s)", "Slip (%)", None, legend=False)

    fig.suptitle("SUN DEVIL MOTORSPORTS · WHEELSPIN EVENT DETAIL",
                 fontsize=13, fontweight="bold")
    if save_path:
        fig.savefig(save_path, dpi=140, bbox_inches="tight")
        logger.info("Saved wheelspin detail -> %s", save_path)
    plt.show() if show else plt.close(fig)
