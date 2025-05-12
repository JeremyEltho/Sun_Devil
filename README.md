<h1 align="center">⚙️ Drivetrain Data Analysis Toolkit 🏁</h1>
<h3 align="center">Analyze slip events, differential loads, and wheel speed behavior for FSAE and robotics performance</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/pandas-✓-orange.svg" alt="Pandas">
  <img src="https://img.shields.io/badge/matplotlib-✓-yellow.svg" alt="Matplotlib">
  <img src="https://img.shields.io/github/last-commit/jeremyeltho/drivetrain-analysis?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/license/jeremyeltho/drivetrain-analysis?style=flat-square" alt="License">
</p>

---

## 📌 Overview

This Python-based toolkit processes rear wheel speed data from FSAE or robotics vehicles to detect:

- 🟥 **Slip Events** — sudden RPM changes  
- 🟢 **Differential Load** — significant RPM imbalance  
- 🧼 **Z-Score Filtering** — optional noise reduction  
- 📈 **Full Visualization** — annotated plots with steering overlay  

It was developed for Sun Devil Motorsports’ drivetrain testing and is designed for engineers and data enthusiasts who want performance insights from wheel telemetry.

---

## 🚀 How to Run

### 1️⃣ Prepare Your Data

Ensure your `.csv` contains the following columns:
- `time (s)` ⏱️  
- `rr wheel speed (rpm)` 🔶  
- `rl wheel speed (rpm)` 🔷  
- Optional: `steering (degrees)` 🕹️

Place the file in your working directory and update `Config.INPUT_CSV_PATH` if needed.

### 2️⃣ Run the Script

```bash
python drivetrain_analysis.py
📄 File	                      📋 Description
cleaned_wheel_data.csv	       Filtered data with noise and invalid readings removed
slip_events_report.csv	        Slip events exceeding jump threshold
differential_load_events.csv	  Timepoints with RPM deltas beyond threshold
drivetrain.log	                Full processing logs, warnings, and errors
