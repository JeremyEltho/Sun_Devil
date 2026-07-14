#!/usr/bin/env python3
"""Sun Devil Motorsports — drivetrain analysis CLI.

Runs the full pipeline: load -> clean -> resample -> derive physics -> detect
events -> report -> plot.

Examples
--------
Interactive (prompts for thresholds, like the original tool)::

    python analyze.py

Fully unattended, custom car + headless (CI / batch)::

    python analyze.py --csv DrivetrainData_11.3.csv --no-show \\
        --tire-radius 0.21 --track 1.20 --wheelbase 1.55 --steer-ratio 4.0

All outputs (CSVs, PNGs, markdown report, log) land in ``--outdir``.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from drivetrain.config import Config
from drivetrain.pipeline import full_ingest
from drivetrain.physics import derive_channels
from drivetrain.events import detect_all
from drivetrain.report import build_summary, render_markdown
from drivetrain.plots import render_dashboard, render_wheelspin_detail


def build_config(args) -> Config:
    cfg = Config()
    if args.csv:
        cfg.input_csv = args.csv
    if args.outdir:
        cfg.output_dir = args.outdir
    if args.resample_hz:
        cfg.resample_hz = args.resample_hz

    v = cfg.vehicle
    if args.tire_radius:
        v.tire_radius_m = args.tire_radius
    if args.track:
        v.rear_track_m = args.track
    if args.wheelbase:
        v.wheelbase_m = args.wheelbase
    if args.steer_ratio:
        v.steering_ratio = args.steer_ratio
    if args.mu:
        v.tire_mu = args.mu
    if args.mass:
        v.mass_kg = args.mass

    th = cfg.thresholds
    if args.z is not None:
        th.z_score = args.z
    if args.diff is not None:
        th.diff_rpm = args.diff
    if args.slip_ratio is not None:
        th.slip_ratio_pct = args.slip_ratio
    if args.slip_rate is not None:
        th.slip_rate_rpm_s = args.slip_rate
    return cfg


def maybe_prompt(cfg: Config, interactive: bool):
    """Prompt for the three classic thresholds if running interactively."""
    if not interactive:
        return

    def ask(prompt, default):
        try:
            raw = input(f"{prompt} [{default}]: ").strip()
            if not raw:
                return default
            val = float(raw)
            return val if val >= 0 else default
        except (ValueError, EOFError):
            return default

    th = cfg.thresholds
    th.z_score = ask("Z-score noise gate (0 = off)", th.z_score)
    th.diff_rpm = ask("Differential-load threshold (rpm)", th.diff_rpm)
    th.slip_ratio_pct = ask("Wheelspin slip threshold (%)", th.slip_ratio_pct)
    th.slip_rate_rpm_s = ask("Slip angular-accel threshold (rpm/s)", th.slip_rate_rpm_s)


def setup_logging(cfg: Config):
    os.makedirs(cfg.output_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(cfg.output_dir, cfg.log_file)),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("drivetrain")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Sun Devil Motorsports drivetrain analysis")
    p.add_argument("--csv", help="input telemetry CSV")
    p.add_argument("--outdir", help="output directory (default: outputs)")
    p.add_argument("--resample-hz", type=float, help="uniform resample rate (default 50)")

    g = p.add_argument_group("vehicle parameters")
    g.add_argument("--tire-radius", type=float, help="loaded tyre radius (m)")
    g.add_argument("--track", type=float, help="rear track width (m)")
    g.add_argument("--wheelbase", type=float, help="wheelbase (m)")
    g.add_argument("--steer-ratio", type=float, help="steering-wheel:road-wheel ratio")
    g.add_argument("--mu", type=float, help="tyre peak grip coefficient")
    g.add_argument("--mass", type=float, help="vehicle + driver mass (kg)")

    t = p.add_argument_group("event thresholds")
    t.add_argument("--z", type=float, help="rolling z-score gate (0=off)")
    t.add_argument("--diff", type=float, help="raw imbalance threshold (rpm)")
    t.add_argument("--slip-ratio", type=float, help="wheelspin slip threshold (%%)")
    t.add_argument("--slip-rate", type=float, help="slip angular-accel threshold (rpm/s)")

    p.add_argument("--no-show", action="store_true", help="save figures without opening windows")
    p.add_argument("--no-prompt", action="store_true", help="skip interactive threshold prompts")
    return p.parse_args(argv)


def run(cfg: Config, show: bool):
    log = logging.getLogger("drivetrain")
    outdir = cfg.output_dir

    raw, uniform = full_ingest(cfg)
    df = derive_channels(uniform, cfg)
    events = detect_all(df, cfg)
    summary = build_summary(df, events, cfg)

    # persist tabular outputs
    df.round(4).to_csv(os.path.join(outdir, cfg.channels_csv), index=False)
    events["slip"].to_csv(os.path.join(outdir, cfg.slip_csv), index=False)
    events["diff_load"].to_csv(os.path.join(outdir, cfg.diff_csv), index=False)
    df[[cfg.time_col, cfg.rr_col, cfg.rl_col, "v", "speed_kmh"]].round(3).to_csv(
        os.path.join(outdir, cfg.cleaned_csv), index=False)

    md = render_markdown(df, summary, cfg)
    with open(os.path.join(outdir, cfg.summary_md), "w") as fh:
        fh.write(md)
    log.info("Wrote report -> %s", os.path.join(outdir, cfg.summary_md))

    render_dashboard(raw, df, events, summary, cfg,
                     save_path=os.path.join(outdir, cfg.dashboard_png), show=show)
    render_wheelspin_detail(df, summary, cfg,
                            save_path=os.path.join(outdir, cfg.wheelspin_png), show=show)

    print("\n" + md)
    return summary


def main(argv=None):
    args = parse_args(argv)
    cfg = build_config(args)
    log = setup_logging(cfg)
    log.info("Starting drivetrain analysis v2")

    interactive = (not args.no_prompt) and (not args.no_show) and sys.stdin.isatty()
    maybe_prompt(cfg, interactive)

    try:
        run(cfg, show=not args.no_show)
    except Exception as exc:  # noqa: BLE001 — top-level guard, log & exit non-zero
        log.error("Analysis failed: %s", exc, exc_info=True)
        return 1
    log.info("Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
