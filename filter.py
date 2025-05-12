import pandas as pd
import matplotlib.pyplot as plt
import logging
import os
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("drivetrain.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Drivetrain")

# Configuration class for better organization
@dataclass
class Config:
    # File paths
    INPUT_CSV_PATH: str = 'DrivetrainData_11.3.csv'
    OUTPUT_CLEANED_DATA: str = 'cleaned_wheel_data.csv'
    OUTPUT_SLIP_DATA: str = 'slip_events_report.csv'
    OUTPUT_DIFFERENTIAL_LOAD_DATA: str = 'differential_load_events.csv'
    
    # Column names
    TIME_COLUMN: str = 'time (s)'
    RIGHT_REAR_RPM: str = 'rr wheel speed (rpm)'
    LEFT_REAR_RPM: str = 'rl wheel speed (rpm)'
    STEERING_COLUMN: str = 'steering (degrees)'
    
    # Thresholds and defaults
    MINIMUM_RPM: float = 10
    MAXIMUM_RPM: float = 3000
    MAX_TIME_DIFFERENCE: float = 0.125
    TIME_BIN_SIZE: float = 0.125
    WINDOW_SIZE: int = 15
    
    # Default thresholds for user input
    DEFAULT_Z_THRESHOLD: float = 0.0
    DEFAULT_DIFF_THRESHOLD: float = 100.0
    DEFAULT_SLIP_THRESHOLD: float = 200.0

# Create a global config object
config = Config()

def load_data(csv_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found: {csv_path}")
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
    try:
        data = pd.read_csv(csv_path)
        logger.info(f"Successfully loaded data from {csv_path} with {len(data)} rows")
    except Exception as e:
        logger.error(f"Error reading {csv_path}: {e}")
        raise

    # Make sure we have the essential columns
    required_columns = [config.TIME_COLUMN, config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]
    optional_columns = [config.STEERING_COLUMN]
    
    missing_required = [col for col in required_columns if col not in data.columns]
    if missing_required:
        error_msg = f"Missing required columns: {', '.join(missing_required)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
        
    missing_optional = [col for col in optional_columns if col not in data.columns]
    if missing_optional:
        logger.warning(f"Missing optional columns: {', '.join(missing_optional)}")

    # Sort data by time so everything is in chronological order
    data = data.sort_values(config.TIME_COLUMN)

    # Keep a copy of the raw, sorted data
    raw_data = data.copy()

    # Group time values into bins of width TIME_BIN_SIZE, then average them
    data[config.TIME_COLUMN] = (data[config.TIME_COLUMN] // config.TIME_BIN_SIZE) * config.TIME_BIN_SIZE
    averaged_data = data.groupby(config.TIME_COLUMN, as_index=False).mean().round(3)
    
    logger.info(f"Data processed: {len(averaged_data)} rows after binning")

    return raw_data.round(3), averaged_data

def clean_data(data: pd.DataFrame, z_threshold: float, window_size: int = config.WINDOW_SIZE) -> pd.DataFrame:
    """
    Cleans up the data by removing out-of-range RPMs and applying a rolling z-score filter.
    
    Args:
        data: DataFrame to clean
        z_threshold: Threshold for z-score filtering (0 to disable)
        window_size: Window size for rolling calculations
        
    Returns:
        Cleaned DataFrame
    """
    # Convert the relevant columns to numeric, if they're not already
    data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]] = data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]].apply(pd.to_numeric, errors='coerce')
    
    # Count rows before cleaning
    initial_rows = len(data)
    
    # Remove rows with NaN values
    data.dropna(subset=[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM], inplace=True)
    if len(data) < initial_rows:
        logger.info(f"Removed {initial_rows - len(data)} rows with NaN values")

    # Filter out RPM values that seem impossible or invalid
    data = data[
        (data[config.RIGHT_REAR_RPM].between(config.MINIMUM_RPM, config.MAXIMUM_RPM)) &
        (data[config.LEFT_REAR_RPM].between(config.MINIMUM_RPM, config.MAXIMUM_RPM))
    ]
    if len(data) < initial_rows:
        logger.info(f"Removed {initial_rows - len(data)} rows with out-of-range RPM values")

    # If the user specifies a z_threshold > 0, we also do a rolling z-score filter
    if z_threshold > 0:
        logger.info(f"Applying z-score filter with threshold {z_threshold}")
        rolling_means = data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]].rolling(window=window_size, center=True).mean()
        rolling_stds = data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]].rolling(window=window_size, center=True).std().replace(0, 1)

        # Calculate z-scores for each row
        z_scores = (data[[config.RIGHT_REAR_RPM, config.LEFT_REAR_RPM]] - rolling_means) / rolling_stds

        # Only keep rows where the absolute z-score is within the threshold
        rows_before = len(data)
        data = data[(z_scores.abs() <= z_threshold).all(axis=1)]
        logger.info(f"Z-score filter removed {rows_before - len(data)} rows")

    return data.round(3)

def detect_differential_load(data: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """
    Flags data points where the difference between Right Rear and Left Rear wheel speeds
    exceeds the given threshold.
    
    Args:
        data: DataFrame to analyze
        threshold: RPM difference threshold
        
    Returns:
        DataFrame containing only the rows where differential load was detected
    """
    diff = (data[config.RIGHT_REAR_RPM] - data[config.LEFT_REAR_RPM]).abs()
    diff_data = data[diff > threshold].copy()

    # Save that difference in a new column for convenience
    diff_data['difference'] = diff[diff > threshold]
    
    logger.info(f"Detected {len(diff_data)} differential load events with threshold {threshold}")
    return diff_data.round(3)

def detect_slip_events(data: pd.DataFrame, slip_threshold: float) -> pd.DataFrame:
    """
    Finds 'slips' by looking for sudden jumps in either wheel's RPM,
    provided the time gap between consecutive measurements is small.
    
    Args:
        data: DataFrame to analyze
        slip_threshold: RPM jump threshold
        
    Returns:
        DataFrame containing only the rows where slip events were detected
    """
    # Sort by time, reset index for clean consecutive rows
    data = data.sort_values(config.TIME_COLUMN).reset_index(drop=True)

    # Time difference between consecutive rows
    data['time_gap'] = data[config.TIME_COLUMN].diff().round(3)

    # Compare how much the RPM changes from one reading to the next
    data['rr_diff'] = data[config.RIGHT_REAR_RPM].diff().round(3)
    data['rl_diff'] = data[config.LEFT_REAR_RPM].diff().round(3)

    # We define a slip if the difference in wheel speed is bigger than slip_threshold
    # AND the time gap is not too large
    slip_data = data[
        (data['time_gap'] <= config.MAX_TIME_DIFFERENCE) &
        (
            (data['rr_diff'].abs() > slip_threshold) |
            (data['rl_diff'].abs() > slip_threshold)
        )
    ].copy()
    
    logger.info(f"Detected {len(slip_data)} slip events with threshold {slip_threshold}")
    return slip_data.round(3)

def filter_by_steering(data: pd.DataFrame, steering_col: str = config.STEERING_COLUMN, 
                      min_angle: float = -9999, max_angle: float = 9999) -> pd.DataFrame:
    """
    Filters data to only keep rows where the steering value is within [min_angle, max_angle].
    
    Args:
        data: DataFrame to filter
        steering_col: Name of the steering column
        min_angle: Minimum steering angle to keep
        max_angle: Maximum steering angle to keep
        
    Returns:
        Filtered DataFrame
    """
    if steering_col not in data.columns:
        logger.warning(f"Steering column '{steering_col}' not found, returning unfiltered data")
        return data
        
    rows_before = len(data)
    filtered_data = data[(data[steering_col] >= min_angle) & (data[steering_col] <= max_angle)]
    logger.info(f"Steering filter removed {rows_before - len(filtered_data)} rows")
    
    return filtered_data

# Split the plotting function into smaller, more focused functions
def plot_wheel_speed(ax, data, wheel_col, title, slip_data=None, differential_data=None):
    """Helper function to plot a single wheel's speed with markers for events"""
    ax.plot(
        data[config.TIME_COLUMN], 
        data[wheel_col],
        label=f'Cleaned {wheel_col}', 
        linewidth=1.5, 
        color='grey',
        zorder=1
    )

    # Mark slip events with an 'x'
    if slip_data is not None and not slip_data.empty:
        ax.scatter(
            slip_data[config.TIME_COLUMN], 
            slip_data[wheel_col],
            marker='x', 
            s=90, 
            label='Slip', 
            color='red',
            zorder=2
        )

    # Mark differential load events with '.'
    diff_times = set(differential_data[config.TIME_COLUMN]) if differential_data is not None and not differential_data.empty else set()
    diff_wheel = data[data[config.TIME_COLUMN].isin(diff_times)]
    if not diff_wheel.empty:
        ax.scatter(
            diff_wheel[config.TIME_COLUMN], 
            diff_wheel[wheel_col],
            marker='.', 
            s=70, 
            facecolors='none', 
            edgecolors='green',
            label='Diff Load', 
            linewidths=2
        )

    ax.set_title(title)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Wheel Speed (rpm)')
    ax.legend(loc='best')
    ax.grid(True)

def plot_wheel_speeds_and_steering(ax_speed, data):
    """Helper function to plot both wheel speeds and steering angle"""
    ax_speed.set_title('Wheel Speed & Steering Angle Over Time')

    # Plot the two wheel speeds
    ax_speed.plot(
        data[config.TIME_COLUMN], 
        data[config.LEFT_REAR_RPM],
        label='Left Wheel Speed', 
        linewidth=2.0, 
        color='blue'
    )
    ax_speed.plot(
        data[config.TIME_COLUMN], 
        data[config.RIGHT_REAR_RPM],
        label='Right Wheel Speed', 
        linewidth=2.0, 
        color='orange'
    )
    ax_speed.set_xlabel('Time (s)')
    ax_speed.set_ylabel('Wheel Speed (rpm)')
    ax_speed.grid(True)

    # Steering goes on the twin y-axis
    ax_steer = ax_speed.twinx()
    if config.STEERING_COLUMN in data.columns:
        ax_steer.plot(
            data[config.TIME_COLUMN], 
            data[config.STEERING_COLUMN],
            '--', 
            label='Steering (deg)', 
            linewidth=1.8, 
            color='green'
        )
        ax_steer.set_ylabel('Steering (degrees)')

    # Combine legends for both axes
    lines_1, labels_1 = ax_speed.get_legend_handles_labels()
    if config.STEERING_COLUMN in data.columns:
        lines_2, labels_2 = ax_steer.get_legend_handles_labels()
    else:
        lines_2, labels_2 = [], []
    ax_speed.legend(lines_1 + lines_2, labels_1 + labels_2, loc='best')

def plot_differential_load(ax_diff, data, differential_data):
    """Helper function to plot differential load and steering"""
    ax_diff.set_title('Differential Load & Steering')
    ax_diff.set_xlabel('Time (s)')
    ax_diff.set_ylabel('RPM Difference')
    ax_diff.grid(True)

    # Another twin axis for Steering
    ax_diff_steer = ax_diff.twinx()
    ax_diff_steer.set_ylabel('Steering (degrees)')

    # Plot steering in a similar style
    if config.STEERING_COLUMN in data.columns:
        ax_diff_steer.plot(
            data[config.TIME_COLUMN],
            data[config.STEERING_COLUMN],
            '--', label='Steering (deg)',
            linewidth=1,
            color='blue'
        )

    # Plot the difference in RPM on the main axis
    rpm_diff_all = (data[config.RIGHT_REAR_RPM] - data[config.LEFT_REAR_RPM]).abs()
    ax_diff.plot(
        data[config.TIME_COLUMN],
        rpm_diff_all,
        label='Differential (rpm)',
        linewidth=1.5,
        color='grey'
    )

    # Use vertical bars at the bottom of the chart for differential load detection times
    if differential_data is not None and not differential_data.empty:
        # Label just the first bar so the legend doesn't repeat
        first_time = differential_data[config.TIME_COLUMN].iloc[0]
        ax_diff.axvline(
            first_time,
            color='red',
            ymin=0.0,
            ymax=0.001,
            label='Detected Load (bars)',
            linewidth=.25
        )
        # Plot the rest 
        for t in differential_data[config.TIME_COLUMN].iloc[1:]:
            ax_diff.axvline(t, color='red', ymin=0.0, ymax=0.1, linewidth=1)
    else:
        ax_diff.text(
            0.5, 0.5,
            'No Differential Load Events Found',
            horizontalalignment='center',
            verticalalignment='center',
            transform=ax_diff.transAxes
        )

    # Merge legends
    lines_1, labels_1 = ax_diff.get_legend_handles_labels()
    if config.STEERING_COLUMN in data.columns:
        lines_2, labels_2 = ax_diff_steer.get_legend_handles_labels()
    else:
        lines_2, labels_2 = [], []
    ax_diff.legend(lines_1 + lines_2, labels_1 + labels_2, loc='best')

def plot_all_subplots(raw_data: pd.DataFrame, cleaned_data: pd.DataFrame, 
                     slip_data: pd.DataFrame, differential_data: pd.DataFrame) -> None:
    """
    Creates a figure with four subplots showing wheel speeds, slip events, and differential load.
    
    Args:
        raw_data: Raw data DataFrame
        cleaned_data: Cleaned data DataFrame
        slip_data: DataFrame containing slip events
        differential_data: DataFrame containing differential load events
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    
    # Plot left wheel
    plot_wheel_speed(
        axes[0, 0], 
        cleaned_data, 
        config.LEFT_REAR_RPM, 
        'Left Rear Wheel Speed Over Time',
        slip_data,
        differential_data
    )

    # Plot right wheel
    plot_wheel_speed(
        axes[0, 1], 
        cleaned_data, 
        config.RIGHT_REAR_RPM, 
        'Right Rear Wheel Speed Over Time',
        slip_data,
        differential_data
    )

    # Plot wheel speeds and steering
    plot_wheel_speeds_and_steering(axes[1, 0], cleaned_data)

    # Plot differential load
    plot_differential_load(axes[1, 1], cleaned_data, differential_data)
    
    # Make it all fit nicely
    plt.tight_layout()
    plt.show()

def get_user_input(prompt: str, default: float) -> float:
    """
    Safely get numeric input from the user with a default value.
    
    Args:
        prompt: Prompt to show the user
        default: Default value to use if input is invalid
        
    Returns:
        User-provided value or default
    """
    try:
        value = float(input(prompt))
        if value < 0:
            logger.warning(f"Negative value provided: {value}, using default: {default}")
            return default
        return value
    except ValueError:
        logger.warning(f"Invalid input, using default: {default}")
        return default

def main() -> None:
    """
    Main function that:
    1) Asks the user for thresholds
    2) Loads and cleans the data
    3) Detects differential load and slip events
    4) Saves those results
    5) Plots the data in four subplots
    """
    logger.info("Starting Drivetrain analysis")
    
    # Get user input with validation
    z_threshold = get_user_input(
        f"Enter z-score threshold (0 = none) [{config.DEFAULT_Z_THRESHOLD}]: ", 
        config.DEFAULT_Z_THRESHOLD
    )
    
    diff_threshold = get_user_input(
        f"Enter rpm difference threshold for differential load [{config.DEFAULT_DIFF_THRESHOLD}]: ", 
        config.DEFAULT_DIFF_THRESHOLD
    )
    
    slip_threshold = get_user_input(
        f"Enter rpm jump threshold for slip detection [{config.DEFAULT_SLIP_THRESHOLD}]: ", 
        config.DEFAULT_SLIP_THRESHOLD
    )

    # Load our CSV data
    try:
        raw_data, averaged_data = load_data(config.INPUT_CSV_PATH)
        if averaged_data.empty:
            logger.error("No data was loaded. Exiting...")
            return
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    # Clean up our data
    cleaned_data = clean_data(averaged_data, z_threshold)
    cleaned_data.to_csv(config.OUTPUT_CLEANED_DATA, index=False)
    logger.info(f"Cleaned data saved to: {config.OUTPUT_CLEANED_DATA}")

    # Flag spots where the difference in wheel speed is too large
    differential_data = detect_differential_load(cleaned_data, diff_threshold)
    differential_data.to_csv(config.OUTPUT_DIFFERENTIAL_LOAD_DATA, index=False)
    logger.info(f"Differential load events saved to: {config.OUTPUT_DIFFERENTIAL_LOAD_DATA}")

    # Flag slips (quick jumps in RPM)
    slip_data = detect_slip_events(cleaned_data, slip_threshold)
    slip_data.to_csv(config.OUTPUT_SLIP_DATA, index=False)
    logger.info(f"Slip events saved to: {config.OUTPUT_SLIP_DATA}")

    # Generate our four-subplot figure
    plot_all_subplots(raw_data, cleaned_data, slip_data, differential_data)
    
    logger.info("Analysis completed successfully")

if __name__ == '__main__':
    main()

"""
Basically know what rpms u are defining as differntating as load 
"""
