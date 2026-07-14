"""Sun Devil Motorsports — drivetrain telemetry analysis toolkit.

A small, well-factored pipeline that turns raw rear-wheel-speed + steering
telemetry into real vehicle-dynamics channels (speed, yaw, lateral/longitudinal
acceleration, differential behaviour), detects driveline events, and renders a
publication-quality analysis dashboard.

Public API::

    from drivetrain import Config, VehicleParams
    from drivetrain.pipeline import load_data, clean_data, resample_uniform
    from drivetrain.physics import derive_channels
    from drivetrain.events import detect_all
    from drivetrain.report import build_summary
    from drivetrain.plots import render_dashboard
"""

from .config import Config, VehicleParams, EventThresholds

__all__ = ["Config", "VehicleParams", "EventThresholds"]
__version__ = "2.0.0"
