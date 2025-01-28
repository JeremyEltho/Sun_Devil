import pandas as pd
import matplotlib.pyplot as plt


# File paths
INPUT_CSV_PATH = 'DrivetrainData_11.3.csv'
OUTPUT_CLEANED_DATA = 'cleaned_wheel_data.csv'
OUTPUT_SLIP_DATA = 'slip_events_report.csv'
OUTPUT_DIFFERENTIAL_LOAD_DATA = 'differential_load_events.csv'

# Column names
TIME_COLUMN = 'time (s)'
RIGHT_REAR_RPM = 'rr wheel speed (rpm)'
LEFT_REAR_RPM = 'rl wheel speed (rpm)'

# Basic thresholds
MINIMUM_RPM = 0.1
MAXIMUM_RPM = 3000
MAX_TIME_DIFFERENCE = 1.0


def load_data(csv_path):
    # Load and sort the data by time column, get rid duplicates
    try:
        data = pd.read_csv(csv_path)
        if TIME_COLUMN in data.columns:
            data = data.sort_values(TIME_COLUMN).drop_duplicates(TIME_COLUMN)
        return data
    except FileNotFoundError:
        print(f"File not found: {csv_path}")
        return pd.DataFrame()


def clean_data(data, z_threshold):
    # Clean the wheel RPM columns and remove bad data
    data[[RIGHT_REAR_RPM, LEFT_REAR_RPM]] = data[[RIGHT_REAR_RPM, LEFT_REAR_RPM]].apply(pd.to_numeric, errors='coerce')
    data.dropna(subset=[RIGHT_REAR_RPM, LEFT_REAR_RPM], inplace=True)

    # Remove RPM values outside the range
    data = data[(data[RIGHT_REAR_RPM] >= MINIMUM_RPM) & (data[RIGHT_REAR_RPM] <= MAXIMUM_RPM)]
    data = data[(data[LEFT_REAR_RPM] >= MINIMUM_RPM) & (data[LEFT_REAR_RPM] <= MAXIMUM_RPM)]

    # Apply z-score filtering
    if z_threshold > 0:
        for col in [RIGHT_REAR_RPM, LEFT_REAR_RPM]:
            col_mean = data[col].mean()
            col_std = data[col].std()
            if col_std > 0:
                z_scores = (data[col] - col_mean) / col_std
                data = data[z_scores.abs() <= z_threshold]

    return data


def detect_differential_load(data, threshold):
    # Find cases where the RPM difference between wheels exceeds the threshold
    diff_data = data[abs(data[RIGHT_REAR_RPM] - data[LEFT_REAR_RPM]) > threshold].copy()
    diff_data['difference'] = abs(diff_data[RIGHT_REAR_RPM] - diff_data[LEFT_REAR_RPM])
    return diff_data


def detect_slip_events(data, threshold):
    # Detect rapid changes in RPM between consecutive rows
    slip_events = []
    for i in range(1, len(data)):
        current = data.iloc[i]
        previous = data.iloc[i - 1]
        time_gap = current[TIME_COLUMN] - previous[TIME_COLUMN]

        if time_gap <= MAX_TIME_DIFFERENCE:
            rr_diff = current[RIGHT_REAR_RPM] - previous[RIGHT_REAR_RPM]
            rl_diff = current[LEFT_REAR_RPM] - previous[LEFT_REAR_RPM]

            if abs(rr_diff) > threshold or abs(rl_diff) > threshold:
                slip_events.append({
                    TIME_COLUMN: current[TIME_COLUMN],
                    RIGHT_REAR_RPM: current[RIGHT_REAR_RPM],
                    LEFT_REAR_RPM: current[LEFT_REAR_RPM],
                    'time_gap': round(time_gap, 3),
                    'right_rear_diff': round(rr_diff, 3),
                    'left_rear_diff': round(rl_diff, 3)
                })

    return pd.DataFrame(slip_events)


def plot_data(original_data, cleaned_data):
    # Plot the wheel speeds
    plt.figure(figsize=(12, 6))
    plt.plot(original_data[TIME_COLUMN], original_data[RIGHT_REAR_RPM], label='Original RR Wheel', alpha=0.7)
    plt.plot(original_data[TIME_COLUMN], original_data[LEFT_REAR_RPM], label='Original RL Wheel', alpha=0.7)
    plt.plot(cleaned_data[TIME_COLUMN], cleaned_data[RIGHT_REAR_RPM], label='Cleaned RR Wheel', alpha=0.7)
    plt.plot(cleaned_data[TIME_COLUMN], cleaned_data[LEFT_REAR_RPM], label='Cleaned RL Wheel', alpha=0.7)

    plt.title('Wheel Speeds Over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Wheel Speed (RPM)')
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()


def main():
    # Get user inputs for thresholds
    try:
        z_threshold = float(input("Enter z-score threshold (0=none): "))
    except ValueError:
        z_threshold = 0

    try:
        diff_threshold = float(input("Enter RPM difference threshold for differential load: "))
    except ValueError:
        diff_threshold = 100

    try:
        slip_threshold = float(input("Enter RPM jump threshold for slip detection: "))
    except ValueError:
        slip_threshold = 200

    # Load original data
    original_data = load_data(INPUT_CSV_PATH)
    if original_data.empty:
        print("No data loaded. Exiting.")
        return

    # Clean the data
    cleaned_data = clean_data(original_data, z_threshold)
    cleaned_data.to_csv(OUTPUT_CLEANED_DATA, index=False)
    print(f"Cleaned data saved to {OUTPUT_CLEANED_DATA}.")

    # Detect differential load events
    differential_data = detect_differential_load(cleaned_data, diff_threshold)
    differential_data.to_csv(OUTPUT_DIFFERENTIAL_LOAD_DATA, index=False)
    print(f"Differential load events saved to {OUTPUT_DIFFERENTIAL_LOAD_DATA}.")

    # Detect slip events
    slip_data = detect_slip_events(cleaned_data, slip_threshold)
    slip_data.to_csv(OUTPUT_SLIP_DATA, index=False)
    print(f"Slip events saved to {OUTPUT_SLIP_DATA}.")

    # Plot the original and cleaned data
    plot_data(original_data, cleaned_data)


if __name__ == "__main__":
    main()
