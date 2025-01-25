import pandas as pd
import matplotlib.pyplot as plt

# File paths
input_csv_path = 'DrivetrainData_11.3.csv'  # Update this with your file path
cleaned_csv_path = 'cleaned_wheel_data.csv'  # Update this with your file path

# Columns to be used
time_column = 'time (s)'
right_rear_rpm = 'rr wheel speed (rpm)'
left_rear_rpm = 'rl wheel speed (rpm)'

# Function to plot the data
def plot_wheel_speeds(original_data, cleaned_data):
    plt.figure(figsize=(12, 6))
    
    # Original data
    plt.plot(original_data[time_column], original_data[right_rear_rpm], label='Original RR Wheel', alpha=0.7)
    plt.plot(original_data[time_column], original_data[left_rear_rpm], label='Original RL Wheel', alpha=0.7)
    
    # Cleaned data
    plt.plot(cleaned_data[time_column], cleaned_data[right_rear_rpm], label='Cleaned RR Wheel', alpha=0.7)
    plt.plot(cleaned_data[time_column], cleaned_data[left_rear_rpm], label='Cleaned RL Wheel', alpha=0.7)
    
    # Customize the plot
    plt.title('Wheel Speeds Over Time')
    plt.xlabel('Time (s)')
    plt.ylabel('Wheel Speed (RPM)')
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

# Load the data
try:
    # Load original data
    original_data = pd.read_csv(input_csv_path)
    
    # Load cleaned data
    cleaned_data = pd.read_csv(cleaned_csv_path)
    
    # Plot the data
    plot_wheel_speeds(original_data, cleaned_data)
    
except FileNotFoundError as e:
    print(f"File not found: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
