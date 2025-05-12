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
3️⃣ You Will Be Prompted To Enter:
Z-score threshold (e.g. 2.5 or 0 to disable)

Differential load threshold (e.g. 100)

Slip detection threshold (e.g. 200)

📤 Outputs
📄 File	📋 Description
cleaned_wheel_data.csv	Filtered data with noise and invalid readings removed
slip_events_report.csv	Slip events exceeding jump threshold
differential_load_events.csv	Timepoints with RPM deltas beyond threshold
drivetrain.log	Full processing logs, warnings, and errors

📦 Dependencies
Install required packages using:

bash
Copy
Edit
pip install pandas matplotlib
🧾 Imports Used
python
Copy
Edit
import pandas as pd
import matplotlib.pyplot as plt
import logging
import os
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
📊 Visual Output
✅ Left & right rear wheel speed over time
❌ Slip event markers (red X)
🟢 Differential load markers (green circle or bar)
📈 Steering angle overlay (dashed green)
🧭 Grid, legends, and axis labels auto-configured

⚙️ Configuration
All runtime settings are defined in the Config class:

python
Copy
Edit
DEFAULT_Z_THRESHOLD = 0.0
DEFAULT_DIFF_THRESHOLD = 100.0
DEFAULT_SLIP_THRESHOLD = 200.0
WINDOW_SIZE = 15
TIME_BIN_SIZE = 0.125
You may edit these values directly in code or provide them via CLI prompts at runtime.

🧪 Use Cases
🏎️ FSAE drivetrain testing & torque bias analysis

🤖 Robotics wheel behavior & collision recovery

📉 Post-race telemetry breakdown

🧠 Engineering diagnostics for torque vectoring

🧼 Data smoothing for mechanical simulation or ML models

👤 Author
Jeremy Eltho
📚 Computer Science @ Arizona State University
🔧 Drivetrain Engineer — Sun Devil Motorsports FSAE
📧 jeremyeltho@gmail.com
🔗 LinkedIn

📄 License
This project is intended for academic and personal use. Please contact the author for commercial licensing or redistribution.

<p align="center">Made with ❤️, RPMs, and Python 🐍</p> ```
Let me know if you want:

A sample dataset (.csv) for users to test

A GitHub Actions workflow for automatic testing

Dark-mode compatible screenshots or demo GIFs
