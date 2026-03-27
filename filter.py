import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import logging
import os
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("drivetrain.log"), logging.StreamHandler()]
)
logger = logging.getLogger("drivetrain")


@dataclass
class Config:
    INPUT_CSV_PATH: str = 'DrivetrainData_11.3.csv'
    OUTPUT_CLEANED_DATA: str = 'cleaned_wheel_data.csv'
    OUTPUT_SLIP_DATA: str = 'slip_events_report.csv'
    OUTPUT_DIFFERENTIAL_LOAD_DATA: str = 'differential_load_events.csv'

    TIME_COLUMN: str = 'time (s)'
    RIGHT_REAR_RPM: str = 'rr wheel speed (rpm)'
    LEFT_REAR_RPM: str = 'rl wheel speed (rpm)'
    STEERING_COLUMN: str = 'steering (degrees)'

    MINIMUM_RPM: float = 10
    MAXIMUM_RPM: float = 3000
    MAX_TIME_DIFFERENCE: float = 0.125
    TIME_BIN_SIZE: float = 0.125
    WINDOW_SIZE: int = 15

    DEFAULT_Z_THRESHOLD: float = 0.0
    DEFAULT_DIFF_THRESHOLD: float = 100.0
    DEFAULT_SLIP_THRESHOLD: float = 200.0


config = Config()

CLR = {
    'left':  '#4fc3f7',
    'right': '#ff9800',
    'slip':  '#ef5350',
    'diff':  '#66bb6a',
    'steer': '#ce93d8',
    'raw':   '#444444',
}


def load_data(csv_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    data = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(data)} rows from {csv_path}")

    required = [config.TIME_COLUMN, config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    if config.STEERING_COLUMN not in data.columns:
        logger.warning("Steering column not found — steering overlays will be skipped")

    data = data.sort_values(config.TIME_COLUMN)
    raw = data.copy()

    data[config.TIME_COLUMN] = (data[config.TIME_COLUMN] // config.TIME_BIN_SIZE) * config.TIME_BIN_SIZE
    binned = data.groupby(config.TIME_COLUMN, as_index=False).mean().round(3)
    logger.info(f"{len(binned)} rows after {config.TIME_BIN_SIZE}s binning")

    return raw.round(3), binned


def clean_data(data: pd.DataFrame, z_threshold: float, window_size: int = config.WINDOW_SIZE) -> pd.DataFrame:
    data = data.copy()
    data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]] = (
        data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]].apply(pd.to_numeric, errors='coerce')
    )

    n = len(data)
    data = data.dropna(subset=[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM])
    data = data[
        data[config.RIGHT_REAR_RPM].between(config.MINIMUM_RPM, config.MAXIMUM_RPM) &
        data[config.LEFT_REAR_RPM].between(config.MINIMUM_RPM, config.MAXIMUM_RPM)
    ]
    logger.info(f"Removed {n - len(data)} invalid rows, {len(data)} remain")

    if z_threshold > 0:
        means = data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]].rolling(window=window_size, center=True).mean()
        stds  = data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]].rolling(window=window_size, center=True).std().replace(0, 1)
        z = (data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]] - means) / stds
        before = len(data)
        data = data[(z.abs() <= z_threshold).all(axis=1)]
        logger.info(f"Z-score filter (thresh={z_threshold}) removed {before - len(data)} rows")

    return data.round(3)


def detect_differential_load(data: pd.DataFrame, threshold: float) -> pd.DataFrame:
    diff = (data[config.RIGHT_REAR_RPM] - data[config.LEFT_REAR_RPM]).abs()
    events = data[diff > threshold].copy()
    events['difference'] = diff[diff > threshold]
    logger.info(f"{len(events)} differential load events (thresh={threshold} RPM)")
    return events.round(3)


def detect_slip_events(data: pd.DataFrame, slip_threshold: float) -> pd.DataFrame:
    data = data.sort_values(config.TIME_COLUMN).reset_index(drop=True)
    data['time_gap'] = data[config.TIME_COLUMN].diff().round(3)
    data['rr_diff']  = data[config.RIGHT_REAR_RPM].diff().round(3)
    data['rl_diff']  = data[config.LEFT_REAR_RPM].diff().round(3)

    events = data[
        (data['time_gap'] <= config.MAX_TIME_DIFFERENCE) &
        (data['rr_diff'].abs().gt(slip_threshold) | data['rl_diff'].abs().gt(slip_threshold))
    ].copy()

    logger.info(f"{len(events)} slip events (thresh={slip_threshold} RPM)")
    return events.round(3)


# ── plotting ────────────────────────────────────────────────────────────────

def _apply_style():
    plt.style.use('dark_background')
    plt.rcParams.update({
        'axes.facecolor':    '#111111',
        'figure.facecolor':  '#0d0d0d',
        'axes.edgecolor':    '#2a2a2a',
        'grid.color':        '#1e1e1e',
        'grid.linewidth':    0.8,
        'axes.labelcolor':   '#aaaaaa',
        'xtick.color':       '#666666',
        'ytick.color':       '#666666',
        'text.color':        '#dddddd',
        'legend.framealpha': 0.25,
        'legend.edgecolor':  '#333333',
        'font.family':       'monospace',
        'font.size':         9,
    })


def _twin_steer(ax, data):
    """Overlay steering angle on a secondary y-axis. Returns the twin axis."""
    ax2 = ax.twinx()
    if config.STEERING_COLUMN in data.columns:
        ax2.plot(
            data[config.TIME_COLUMN], data[config.STEERING_COLUMN],
            color=CLR['steer'], linewidth=1.0, alpha=0.55, linestyle='--', label='Steering (°)'
        )
        ax2.set_ylabel('Steering (°)', color=CLR['steer'], fontsize=8)
        ax2.tick_params(axis='y', colors=CLR['steer'], labelsize=7)
    return ax2


def plot_wheel_speed(ax, raw_data, cleaned_data, wheel_col, label, color, slip_data=None, diff_data=None):
    ax.plot(
        raw_data[config.TIME_COLUMN], raw_data[wheel_col],
        color=CLR['raw'], linewidth=0.5, alpha=0.45, zorder=1, label='Raw'
    )
    ax.plot(
        cleaned_data[config.TIME_COLUMN], cleaned_data[wheel_col],
        color=color, linewidth=1.4, zorder=2, label=label
    )

    if slip_data is not None and not slip_data.empty:
        ax.scatter(
            slip_data[config.TIME_COLUMN], slip_data[wheel_col],
            marker='x', s=55, color=CLR['slip'], linewidths=1.4, zorder=4, label='Slip'
        )

    if diff_data is not None and not diff_data.empty:
        matched = cleaned_data[cleaned_data[config.TIME_COLUMN].isin(diff_data[config.TIME_COLUMN])]
        if not matched.empty:
            ax.scatter(
                matched[config.TIME_COLUMN], matched[wheel_col],
                marker='o', s=28, facecolors='none', edgecolors=CLR['diff'],
                linewidths=1.1, zorder=3, label='Diff Load'
            )

    ax.set_ylabel('RPM', fontsize=8)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, zorder=0)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())


def plot_wheel_speeds_and_steering(ax, data):
    ax.plot(data[config.TIME_COLUMN], data[config.LEFT_REAR_RPM],
            color=CLR['left'], linewidth=1.5, label='Left Rear')
    ax.plot(data[config.TIME_COLUMN], data[config.RIGHT_REAR_RPM],
            color=CLR['right'], linewidth=1.5, label='Right Rear')
    ax.set_ylabel('RPM', fontsize=8)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.grid(True, zorder=0)

    ax2 = _twin_steer(ax, data)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc='upper right')


def plot_differential_load(ax, data, diff_data, threshold):
    t = data[config.TIME_COLUMN]
    rpm_diff = (data[config.RIGHT_REAR_RPM] - data[config.LEFT_REAR_RPM]).abs()

    ax.plot(t, rpm_diff, color='#888888', linewidth=1.2, zorder=2, label='|RR − LR|')
    ax.fill_between(t, rpm_diff, alpha=0.12, color='#888888', zorder=1)
    ax.fill_between(
        t, rpm_diff, threshold,
        where=rpm_diff > threshold,
        color=CLR['slip'], alpha=0.35, zorder=3, label=f'> {threshold:.0f} RPM'
    )
    ax.axhline(threshold, color=CLR['slip'], linewidth=0.8, linestyle=':', alpha=0.6)

    ax.set_ylabel('RPM Δ', fontsize=8)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.grid(True, zorder=0)
    ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())

    ax2 = _twin_steer(ax, data)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc='upper right')

    if diff_data is None or diff_data.empty:
        ax.text(0.5, 0.5, 'No events detected', ha='center', va='center',
                transform=ax.transAxes, color='#555555', fontsize=10)


def plot_all_subplots(raw_data, cleaned_data, slip_data, diff_data, diff_threshold):
    _apply_style()

    fig, axes = plt.subplots(2, 2, figsize=(16, 9), constrained_layout=True)
    fig.suptitle('Sun Devil Motorsports — Rear Drivetrain Analysis', fontsize=12, fontweight='bold')

    plot_wheel_speed(
        axes[0, 0], raw_data, cleaned_data,
        config.LEFT_REAR_RPM, 'Left Rear', CLR['left'], slip_data, diff_data
    )
    axes[0, 0].set_title('Left Rear Wheel Speed', fontsize=10)

    plot_wheel_speed(
        axes[0, 1], raw_data, cleaned_data,
        config.RIGHT_REAR_RPM, 'Right Rear', CLR['right'], slip_data, diff_data
    )
    axes[0, 1].set_title('Right Rear Wheel Speed', fontsize=10)

    plot_wheel_speeds_and_steering(axes[1, 0], cleaned_data)
    axes[1, 0].set_title('Wheel Speeds + Steering', fontsize=10)

    plot_differential_load(axes[1, 1], cleaned_data, diff_data, diff_threshold)
    axes[1, 1].set_title('Differential Load', fontsize=10)

    plt.show()


# ── main ─────────────────────────────────────────────────────────────────────

def get_threshold(prompt: str, default: float) -> float:
    try:
        val = float(input(prompt))
        return val if val >= 0 else default
    except ValueError:
        return default


def main():
    logger.info("Starting drivetrain analysis")

    z_thresh    = get_threshold(f"Z-score threshold (0 = off) [{config.DEFAULT_Z_THRESHOLD}]: ", config.DEFAULT_Z_THRESHOLD)
    diff_thresh = get_threshold(f"Differential load threshold RPM [{config.DEFAULT_DIFF_THRESHOLD}]: ", config.DEFAULT_DIFF_THRESHOLD)
    slip_thresh = get_threshold(f"Slip detection threshold RPM [{config.DEFAULT_SLIP_THRESHOLD}]: ", config.DEFAULT_SLIP_THRESHOLD)

    try:
        raw_data, binned = load_data(config.INPUT_CSV_PATH)
    except Exception as e:
        logger.error(e)
        return

    if binned.empty:
        logger.error("No data loaded, exiting")
        return

    cleaned = clean_data(binned, z_thresh)
    cleaned.to_csv(config.OUTPUT_CLEANED_DATA, index=False)

    diff_events = detect_differential_load(cleaned, diff_thresh)
    diff_events.to_csv(config.OUTPUT_DIFFERENTIAL_LOAD_DATA, index=False)

    slip_events = detect_slip_events(cleaned, slip_thresh)
    slip_events.to_csv(config.OUTPUT_SLIP_DATA, index=False)

    logger.info(f"Results saved: {config.OUTPUT_CLEANED_DATA}, {config.OUTPUT_SLIP_DATA}, {config.OUTPUT_DIFFERENTIAL_LOAD_DATA}")

    plot_all_subplots(raw_data, cleaned, slip_events, diff_events, diff_thresh)
    logger.info("Done")


if __name__ == '__main__':
    main()
