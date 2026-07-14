"""Configuration objects for the drivetrain analysis pipeline.

Everything the pipeline needs to know lives in three dataclasses:

* :class:`VehicleParams` — the physical car (tyre radius, track, wheelbase …).
  These drive every derived vehicle-dynamics channel, so they are exposed on
  the CLI and documented loudly wherever assumptions are made.
* :class:`EventThresholds` — the detector sensitivities.
* :class:`Config`     — file paths, column names and pipeline knobs.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class VehicleParams:
    """Physical parameters of the car.

    Defaults are typical for a Formula SAE car on 10 in wheels. Override them
    for your vehicle — every downstream physics channel scales from these, so
    getting them right is what turns "wheel rpm" into "lateral g".
    """

    tire_radius_m: float = 0.21          # loaded rolling radius of the rear tyre
    rear_track_m: float = 1.20           # lateral distance between rear contact patches
    wheelbase_m: float = 1.55            # front-to-rear axle distance
    steering_ratio: float = 4.0          # steering-wheel deg per road-wheel deg
    mass_kg: float = 300.0               # car + driver (used for load/force estimates)
    tire_mu: float = 1.4                 # peak grip coefficient of the slicks
    cg_height_m: float = 0.30            # centre-of-gravity height (load transfer)

    @property
    def rpm_to_mps(self) -> float:
        """Conversion factor: wheel rpm -> contact-patch speed in m/s."""
        import math
        return 2.0 * math.pi * self.tire_radius_m / 60.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EventThresholds:
    """Detector sensitivities. Negative user input falls back to these."""

    z_score: float = 0.0                 # rolling z-score noise gate (0 = off)
    diff_rpm: float = 100.0              # raw |RR-RL| rpm imbalance flag
    slip_ratio_pct: float = 12.0         # differential slip: (fast-slow)/slow, % -> wheelspin
    slip_rate_rpm_s: float = 3000.0      # per-wheel angular-accel spike (rpm/s) -> spin-up/lock
    launch_g: float = 0.4                # longitudinal g that marks a launch/hard accel
    brake_g: float = 0.5                 # longitudinal g (magnitude) that marks hard braking


@dataclass
class Config:
    """Paths, column names and pipeline knobs."""

    # ── files ────────────────────────────────────────────────────────────
    input_csv: str = "DrivetrainData_11.3.csv"
    output_dir: str = "outputs"
    cleaned_csv: str = "cleaned_wheel_data.csv"
    slip_csv: str = "slip_events_report.csv"
    diff_csv: str = "differential_load_events.csv"
    channels_csv: str = "derived_channels.csv"
    summary_md: str = "analysis_summary.md"
    dashboard_png: str = "drivetrain_dashboard.png"
    wheelspin_png: str = "wheelspin_detail.png"
    log_file: str = "drivetrain.log"

    # ── columns ──────────────────────────────────────────────────────────
    time_col: str = "time (s)"
    rr_col: str = "rr wheel speed (rpm)"
    rl_col: str = "rl wheel speed (rpm)"
    steer_col: str = "steering (degrees)"

    # ── cleaning / resampling ────────────────────────────────────────────
    min_rpm: float = 0.0                 # keep standstill (0 rpm) rows
    max_rpm: float = 2000.0              # physically implausible above this -> spike
    resample_hz: float = 50.0            # uniform grid for derivatives/plots
    smooth_window_s: float = 0.24        # Savitzky-Golay window for smoothing/derivs
    rolling_window: int = 15             # z-score rolling window (samples)
    hampel_window: int = 41              # de-spike median window (raw samples ~80ms)
    hampel_sigma: float = 4.0            # de-spike outlier threshold (robust sigmas)
    max_wheel_accel: float = 30000.0     # physical rpm/s limit -> rate-based de-spike
    accel_cutoff_hz: float = 2.5         # low-pass cutoff for the longitudinal-accel channel
    robust_pct: float = 99.5             # percentile used for "peak" metrics (fault-robust)

    vehicle: VehicleParams = field(default_factory=VehicleParams)
    thresholds: EventThresholds = field(default_factory=EventThresholds)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d
