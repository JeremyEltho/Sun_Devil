<h1 align="center">⚙️ Drivetrain Data Analysis code 🏁</h1>
<h3 align="center">Analyze slip events, differential loads, and wheel speed behavior for FSAE and robotics performance</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/pandas-✓-orange.svg" alt="Pandas">
  <img src="https://img.shields.io/badge/matplotlib-✓-yellow.svg" alt="Matplotlib">
  <img src="https://img.shields.io/github/last-commit/jeremyeltho/drivetrain-analysis?style=flat-square" alt="Last Commit">
  <img src="https://img.shields.io/github/license/jeremyeltho/drivetrain-analysis?style=flat-square" alt="License">
</p>

<hr/>

<h2>📌 Overview</h2>
<p>This Python-based toolkit processes rear wheel speed data from FSAE or robotics vehicles to detect:</p>
<ul>
  <li>🟥 <strong>Slip Events</strong> — sudden RPM changes</li>
  <li>🟢 <strong>Differential Load</strong> — significant RPM imbalance</li>
  <li>🧼 <strong>Z-Score Filtering</strong> — optional noise reduction</li>
  <li>📈 <strong>Full Visualization</strong> — annotated plots with steering overlay</li>
</ul>
<p>Developed for Sun Devil Motorsports’ drivetrain testing, it’s ideal for engineers and data enthusiasts seeking performance insights from wheel telemetry.</p>

<hr/>

<h2>🚀 How to Run</h2>
<ol>
  <li><strong>Prepare Your Data:</strong> Ensure your <code>.csv</code> includes these columns:
    <ul>
      <li><code>time (s)</code> ⏱️</li>
      <li><code>rr wheel speed (rpm)</code> 🔶</li>
      <li><code>rl wheel speed (rpm)</code> 🔷</li>
      <li><em>(optional)</em> <code>steering (degrees)</code> 🕹️</li>
    </ul>
    Place the file in the project folder and update <code>Config.INPUT_CSV_PATH</code> if needed.
  </li>
  <li><strong>Run the Script:</strong>
    <pre><code>python drivetrain_analysis.py</code></pre>
  </li>
  <li><strong>Enter Thresholds When Prompted:</strong>
    <pre><code>
Z-score threshold (e.g. 2.5 or 0 to disable)
Differential load threshold (e.g. 100)
Slip detection threshold (e.g. 200)
    </code></pre>
  </li>
</ol>

<hr/>

<h2>📤 Outputs</h2>
<ul>
  <li><code>cleaned_wheel_data.csv</code> – Filtered data with noise and invalid readings removed</li>
  <li><code>slip_events_report.csv</code> – Slip events exceeding jump threshold</li>
  <li><code>differential_load_events.csv</code> – Timepoints with RPM deltas beyond threshold</li>
  <li><code>drivetrain.log</code> – Detailed processing logs, warnings, and errors</li>
</ul>

<hr/>

<h2>📦 Dependencies</h2>
<pre><code>pip install pandas matplotlib</code></pre>

<hr/>

<h2>🧾 Imports Used</h2>
<pre><code>import pandas as pd
import matplotlib.pyplot as plt
import logging
import os
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
</code></pre>

<hr/>

<h2>📊 Visual Output</h2>
<ul>
  <li>✅ Left & right rear wheel speeds plotted over time</li>
  <li>❌ Slip event markers (red X)</li>
  <li>🟢 Differential load markers (green dots or bars)</li>
  <li>📈 Steering angle overlay (dashed green line)</li>
  <li>🧭 Gridlines, axes, and legends auto-configured</li>
</ul>

<hr/>

<h2>⚙️ Configuration</h2>
<p>All runtime settings live in the <code>Config</code> class:</p>
<pre><code>@dataclass
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
</code></pre>
<p>Modify these values in the script or set interactively at runtime.</p>

<hr/>

<h2>🧪 Use Cases</h2>
<ul>
  <li>🏎️ FSAE drivetrain testing & torque bias analysis</li>
  <li>🤖 Robotics wheel behavior & collision recovery</li>
  <li>📉 Testing telemetry review</li>
  <li>🧠 Engineering diagnostics for differential tuning</li>
  <li>🧼 Data smoothing for hoping in the future simulation/ML pipelines</li>
</ul>

<hr/>

<h2>👤 Author</h2>
<p><strong>Jeremy Eltho</strong><br/>
📚 Computer Science @ Arizona State University<br/>
🔧 Drivetrain Engineer @ Sun Devil Motorsports FSAE<br/>
📧 <a href="mailto:jeremyeltho@gmail.com">jeremyeltho@gmail.com</a><br/>
🔗 <a href="https://linkedin.com/in/jeremyeltho">LinkedIn</a></p>

<hr/>

<h2>📄 License</h2>
<p>This project is intended for academic and personal use. Contact the author for commercial licensing or redistribution.</p>

<p align="center">Made with Python 🐍 and ChatGpt</p>
