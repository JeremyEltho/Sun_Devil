<h1 align="center">Drivetrain Data Analysis</h1>
<h3 align="center">Turn rear-wheel telemetry into real drivetrain physics — speed, longitudinal g, differential slip & wheelspin — for FSAE and robotics</h3>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/pandas-✓-orange.svg" alt="Pandas">
  <img src="https://img.shields.io/badge/numpy-✓-013243.svg" alt="NumPy">
  <img src="https://img.shields.io/badge/scipy-✓-8caae6.svg" alt="SciPy">
  <img src="https://img.shields.io/badge/matplotlib-✓-yellow.svg" alt="Matplotlib">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License"></a>
</p>

<hr/>

<h2>Overview</h2>

<p>This toolkit ingests rear (driven) wheel-speed and steering telemetry and reconstructs the
drivetrain behaviour behind it — then renders a publication-quality analysis dashboard and a
markdown engineering report. It was built for <strong>Sun Devil Motorsports</strong> drivetrain testing.</p>

<p>The analysis is deliberately <em>honest about what the data can support</em>. With only the two
driven-wheel speeds logged, the RR&minus;RL split is dominated by <strong>wheelspin through the
differential</strong>, not chassis yaw — so the tool computes and reports:</p>

<ul>
  <li><strong>Vehicle speed &amp; distance</strong> — from wheel speed and tyre radius (directly measured).</li>
  <li><strong>Longitudinal acceleration</strong> — band-limited d/dt of speed, reported as fault-robust percentiles.</li>
  <li><strong>Differential slip &amp; traction index</strong> — how much the racing wheel outruns the gripping wheel.</li>
  <li><strong>Wheelspin, spin-up/lock and launch/brake events</strong> — collapsed into discrete, ranked events.</li>
</ul>

<p>It deliberately does <strong>not</strong> fabricate lateral-g, yaw or a dead-reckoned track map — deriving
those from this dataset's wheel split gives physically impossible results (&gt;3&nbsp;g even after aggressive
filtering). See <em>Design notes</em> below.</p>

<hr/>

<h2>How to Run</h2>

<pre><code># 1. install deps (a virtualenv is recommended)
pip install -r requirements.txt

# 2a. interactive — prompts for thresholds, opens the plots (like the classic tool)
python filter.py

# 2b. full CLI — unattended, custom vehicle params, headless for CI/batch
python analyze.py --csv DrivetrainData_11.3.csv --no-show \
    --tire-radius 0.21 --track 1.20 --wheelbase 1.55

python analyze.py --help      # every flag
</code></pre>

<p>Your CSV needs these columns (names are configurable): <code>time (s)</code>,
<code>rr wheel speed (rpm)</code>, <code>rl wheel speed (rpm)</code>, and optionally
<code>steering (degrees)</code>.</p>

<hr/>

<h2>Outputs</h2>

<p>Everything lands in <code>outputs/</code>:</p>

<ul>
  <li><code>drivetrain_dashboard.png</code> — 7-panel dashboard (below).</li>
  <li><code>wheelspin_detail.png</code> — zoom on the worst wheelspin event.</li>
  <li><code>analysis_summary.md</code> — headline metrics, ranked events, assumptions.</li>
  <li><code>derived_channels.csv</code> — every computed channel, per sample.</li>
  <li><code>cleaned_wheel_data.csv</code>, <code>slip_events_report.csv</code>,
      <code>differential_load_events.csv</code> — tabular data (backward compatible).</li>
  <li><code>drivetrain.log</code> — processing log.</li>
</ul>

<h3>Dashboard panels</h3>
<ol>
  <li><strong>Session overview</strong> — raw + cleaned wheel speeds, vehicle speed, wheelspin shaded.</li>
  <li><strong>Longitudinal performance</strong> — speed with accel/brake g fill.</li>
  <li><strong>Differential slip</strong> — slip % over time vs the wheelspin threshold.</li>
  <li><strong>Traction map</strong> — slip vs speed, coloured by longitudinal g.</li>
  <li><strong>Wheel coupling</strong> — faster-vs-slower wheel scatter; distance off the 1:1 line = slip.</li>
  <li><strong>Acceleration distribution</strong> — histogram with robust-percentile markers.</li>
  <li><strong>Session summary</strong> — the numbers at a glance.</li>
</ol>

<hr/>

<h2>Architecture</h2>

<pre><code>drivetrain/
  config.py      Config, VehicleParams, EventThresholds  (all knobs live here)
  pipeline.py    load -> clean (de-spike) -> uniform resample
  physics.py     derived vehicle-dynamics channels
  events.py      wheelspin / slip / launch / brake detection
  report.py      summary metrics + markdown report
  plots.py       the dark-theme dashboard + event detail
analyze.py       CLI orchestrator (argparse + interactive fallback)
filter.py        backward-compatible entry point -> analyze.main()
tests/           pytest suite (physics validated against analytic cases)
</code></pre>

<p>Run the tests with <code>pytest</code>. Continuous integration lints with flake8 and runs the suite.</p>

<hr/>

<h2>Configuration</h2>

<p>All settings live in the dataclasses in <code>drivetrain/config.py</code> and are overridable on the CLI.
Vehicle parameters drive every physics channel, so set them for your car:</p>

<pre><code>@dataclass
class VehicleParams:
    tire_radius_m: float = 0.21    # loaded rolling radius -> speed &amp; distance scale
    rear_track_m:  float = 1.20
    wheelbase_m:   float = 1.55
    tire_mu:       float = 1.4
    mass_kg:       float = 300.0
</code></pre>

<hr/>

<h2>Design notes — why no lateral-g / track map</h2>

<p>Only the two <em>driven</em> rear wheels are logged. In principle a wheel-speed split maps to yaw
rate (<code>ψ̇ = (v_R − v_L)/track</code>) and thus lateral acceleration — but on this differential-test
data the split is dominated by wheelspin, not cornering. Converting it to lateral g yields
&gt;3&nbsp;g even after aggressive low-pass filtering, which is non-physical. Rather than ship an
impressive-but-wrong "traction circle", the tool reports what the wheel speeds can actually
defend: <strong>longitudinal</strong> performance and <strong>differential/traction</strong> behaviour.
Peak figures use a robust percentile (default P99.5) so a single sensor glitch never sets a record.</p>

<p>Data hygiene before any physics: a physical rpm/s rate limiter and a Hampel median filter repair
encoder glitches (single-sample spikes and short "stuck" blocks); the signal is then resampled to a
uniform grid so derivatives are well defined.</p>

<hr/>

<h2>Author</h2>
<p><strong>Jeremy Eltho</strong><br/>
Computer Science @ Arizona State University<br/>
Drivetrain Engineer @ Sun Devil Motorsports FSAE<br/>
<a href="mailto:jeremyeltho@gmail.com">jeremyeltho@gmail.com</a> ·
<a href="https://linkedin.com/in/jeremyeltho">LinkedIn</a></p>

<h2>License</h2>
<p>Released under the <a href="LICENSE">MIT License</a>.</p>

<p align="center">Made with Python · pandas · NumPy · SciPy · Matplotlib</p>
