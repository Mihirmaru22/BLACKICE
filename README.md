# BLACKICE ❄️

**A production-grade streaming pipeline that detects persistent regime shifts in infrastructure metrics using statistical validation instead of opaque ML models.**

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-stable-success)

> *Note: This project is an independent signals engineering library and is not associated with BlackIce Forensics, Databricks, or other security vendors.*

---

## 1. Quick Start

### Installation
Requires Python 3.10+.

```bash
# Install via pip
pip install blackice
```

### Usage (Library)
Use `RegimeDetector` to embed stability logic directly into your Python services.

```python
from blackice import RegimeDetector, RegimeState

# 1. Initialize detector (defaults: window=60, sigma=3.0)
detector = RegimeDetector()

# 2. Feed data points (e.g., from Kafka/Prometheus)
# Returns a DetectionEvent object
event = detector.update(45.5)

# 3. Act on findings
if event.is_anomaly:
    print(f"Instability detected: {event.reason}")
    print(f"Severity: {event.zscore:.2f}σ")
    
if event.state == RegimeState.SHIFTED:
    # Use explicit Enums for type-safety
    trigger_pager(f"Regime shift confirmled: {event.duration}s")
```

### Usage (CLI)
Run the full analysis pipeline on your own data.

```bash
blackice --data <logs.csv> --machine <server_id> --report
```

**Universal Input Requirements:**
- **Input**: A CSV file with columns `['machine_id', 'timestamp', 'cpu_util', 'mem_util']`.
- **Output**: Generates an incident report at `reports/analysis_<server_id>.md`.
- **Logic**: Filters noise using the persistence logic defined in `configs/default.yaml`.

---

## 2. Hybrid ML (Offline Training)

**Optimized Parameters, Deterministic Runtime.**

BLACKICE includes an Offline Learning module that optimizes configuration parameters (Decision Boundaries) using historical data. This allows the system to adapt to specific infrastructure characteristics without running opaque models in production.

### Training Usage
Use the training script to find the optimal `z_threshold` and `window_size` for your data:

```bash
# Finds best parameters using Grid Search over 48 combinations
python train_model.py data/machine_usage.csv --output configs/learned.yaml
```

**What happens:**
1.  **Objective Function**: Minimizes a loss function where `False_Alerts` are penalized 5x more than `Detection_Layency`.
2.  **Optimizer**: Runs the pipeline on historical data with varying parameters (Grid Search).
3.  **Output**: Generates a production-ready `learned.yaml` config file.

Then run the detector with the learned config:

```bash
blackice --config configs/learned.yaml ...
```

---

## 2. Motivation

Infrastructure monitoring is plagued by **alert fatigue**. Traditional threshold-based alerting generates noise from transient spikes, while complex ML models introduce opacity and drift.

**BLACKICE** addresses this by shifting focus from *point anomalies* to *persistent regime shifts*. It acknowledges that infrastructure data is inherently noisy and bursty. Instead of training complex models to predict every spike, BLACKICE uses rigorous statistical persistence validation to distinguish between:
1.  **Transient Instability**: Burstiness that returns to baseline (filtered out).
2.  **Structural Deviation**: Shifts that persist beyond a confidence interval (reported).

The system avoids "AI magic" in favor of deterministic, explainable signal processing that can be debugged by an SRE at 3 AM.

---

## 3. Architecture Overview

BLACKICE is engineered as a streaming processing pipeline, not a batch analysis script. It operates in O(1) memory per metric tracker.

```mermaid
%%{init: {'themeVariables': { 'fontSize': '13px'}}}%%
graph LR
  %% 1. Define Subgraphs
  subgraph Control["Control Plane"]
    PF[Persistence Filter]
    SM[State Machine]
    IR[Incident Report]
  end

  subgraph Data["Data Plane"]
    SS[Stream Source]
    IP[Ingest Pipeline]
    DD[Deviation Detect]
  end

  %% 2. Data Plane Flow
  SS --> IP
  IP -->|Stats| DD

  %% 3. Cross-Layer Signal
  DD -.->|Signal| PF

  %% 4. Control Plane Flow
  PF -->|Confirmed| SM
  SM -->|Alert| IR

  %% 5. Feedback Loop
  SM -->|Mute| DD
```

### Components
- **Baseline Modeling**: Welford's algorithm for numerically stable, streaming mean/variance without history retention.
- **Deviation Detection**: Real-time z-score computation against rolling baselines.
- **Persistence Validation**: Deterministic filter requiring deviations to sustain magnitude and duration thresholds to trigger state changes.
- **State Machine**: Formal transition logic (NORMAL → UNSTABLE → SHIFTED) providing clean audit trails.
- **RegimeDetector**: High-level facade that encapsulates the entire engine into a single, easy-to-use API.
- **Metrics/Reporting**: Generates label-free stability metrics and automated incident analysis files.

---

## 4. Key Features

- **Streaming-First Design**: Processes infinite streams chunk-by-chunk using minimal resources.
- **Constant Memory**: O(window_size) memory complexity regardless of dataset size.
- **Label-Free Metrics**: Quality metrics (detection latency, spike rejection) computed without ground truth labels.
- **Noise Rejection**: Aggressive persistence layer filters 80-90% of transient noise typical in cloud workloads.
- **Automated Reporting**: Instantly generates production-grade Markdown incident reports.
- **CLI-Driven**: Unix-philosophy operational interface.

---

## 5. Project Structure

```text
blackice/
├── configs/            # YAML configuration for pipelines
│   └── default.yaml    # Production default thresholds
├── data/               # Data processing artifacts
├── notebooks/          # Analysis and visualization logic
│   └── main.ipynb      # Interactive validation notebook
├── reports/            # Generated incident analysis reports
├── scripts/            # Executable entry points
│   ├── run_blackice.py # Main pipeline CLI
│   └── test_blackice.py# Integration test suite
└── src/
    └── blackice/       # Core library
        ├── baseline.py     # Streaming statistics
        ├── cli.py          # CLI entry point
        ├── detector.py     # High-level RegimeDetector API
        ├── deviation.py    # Signal detection
        ├── metrics.py      # Stability metrics
        ├── persistence.py  # Noise filtering logic
        ├── pipeline.py     # Orchestration
        └── state.py        # Regime state machine
```

---

## 6. Example Output

BLACKICE generates structured incident reports designed for engineering transparency.

### Report Sections:
- **Executive Summary**: Immediate text verdict (HEALTHY/UNHEALTHY) based on confirmed shifts.
- **Signal Summary**: Detailed breakdown of CPU/Memory behavior patterns.
- **Detection Statistics**: Tables showing total events vs. confirmed shifts (often 100% rejection rate for stable but bursty machines).
- **Infra Interpretation**: Automated diagnosis of workload characteristics (e.g., "High variance but stable").

A "Health" verdict often accompanies high instability counts. This is **correct behavior**: it proves the system successfully identified thousands of spikes as non-critical noise, preventing thousands of false pages.

---

## 7. Design Philosophy

1.  **Conservative by Design**: We prefer missing a subtle shift over waking an engineer for a false positive.
2.  **Deterministic > Probabilistic**: Given the same input, the system must produce the exact same state transitions.
3.  **Explainability > Complexity**: Every regime shift has a clear reason (e.g., *"Deviation persisted for >10 points"*), traceable back to specific timestamps.

---

## 8. System Properties

### Guarantees
- **Deterministic output** for identical input streams
- **O(1) update time** per data point
- **Bounded memory usage** (O(window_size))
- **No training phase** or learned parameters

### Non-Goals
- Not a forecasting system
- Not a root-cause analysis engine
- Not a replacement for TSDBs or Prometheus

---

## 9. License

MIT License.

---

> **For Contributors**: To setup a development environment and run tests, please see [DEVELOPMENT.md](DEVELOPMENT.md).
