# BLACKICE Development & Verification Guide

## Quick Validation

```bash
cd /Users/mihirmaru/Work/SIde\ Quest/projects/blackice
source .venv/bin/activate

# Run quick validation
python -c "
import sys; sys.path.insert(0, 'src')
from blackice.pipeline import BlackicePipeline, PipelineConfig, stream_machine_data
import yaml

with open('configs/default.yaml') as f:
    config = yaml.safe_load(f)

pipeline = BlackicePipeline(PipelineConfig.from_dict(config))
for chunk in stream_machine_data('../machine_usage.csv', 'm_1932', chunksize=500000):
    events = pipeline.process_chunk(chunk)
    if events:
        for e in events[:3]:
            print(f'{e.metric_name}: {e.transition.from_state.value} -> {e.transition.to_state.value}')
pipeline.stop()
print('✓ Pipeline works!')
"
```

## Full Test Suite

```bash
cd /Users/mihirmaru/Work/SIde\ Quest/projects/blackice
source .venv/bin/activate
python scripts/test_blackice.py
```

## Run CLI Script

```bash
cd /Users/mihirmaru/Work/SIde\ Quest/projects/blackice
source .venv/bin/activate
python scripts/run_blackice.py --help
python scripts/run_blackice.py --machine m_1932
```

## Run Jupyter Notebook

```bash
cd /Users/mihirmaru/Work/SIde\ Quest/projects/blackice
source .venv/bin/activate
pip install jupyter  # If not installed
jupyter notebook notebooks/main.ipynb
```

## Test Individual Modules

### Baseline Module
```python
from blackice.baseline import BaselineComputer

bc = BaselineComputer(window_size=60)
for i in range(100):
    bc.update(float(i % 20))

print(f"Warm: {bc.is_warm}")
print(f"Mean: {bc.mean:.2f}")
print(f"Std: {bc.std:.2f}")
```

### Pipeline with Custom Config
```python
from blackice.pipeline import BlackicePipeline, PipelineConfig
import pandas as pd

config = PipelineConfig(
    window_size=30,
    zscore_threshold=2.5,
    min_consecutive_points=5
)

pipeline = BlackicePipeline(config)

# Create test data
data = pd.DataFrame({
    'machine_id': ['m_test'] * 100,
    'timestamp': range(100),
    'cpu_util': [50]*50 + [80]*50,  # Regime shift at t=50
    'mem_util': [40]*100
})

events = pipeline.process_chunk(data)
pipeline.stop()

print(f"Events: {len(events)}")
for e in events:
    print(f"  {e.transition.to_state.value} at t={e.transition.timestamp}")
```

## Project Structure

```
blackice/
├── .venv/                 # Python virtual environment
├── configs/
│   └── default.yaml       # Pipeline configuration
├── data/
│   ├── machine_meta.csv   # Machine metadata
│   └── README.md
├── notebooks/
│   └── main.ipynb         # Analysis notebook
├── reports/
│   └── incident_analysis.md
├── scripts/
│   ├── run_blackice.py    # CLI runner
│   └── test_blackice.py   # Test suite
├── src/blackice/
│   ├── __init__.py
│   ├── baseline.py        # Rolling statistics (Welford's algorithm)
│   ├── deviation.py       # Z-score tracking
│   ├── persistence.py     # Spike filtering
│   ├── state.py           # State machine (NORMAL/UNSTABLE/SHIFTED)
│   ├── metrics.py         # Detection quality metrics
│   └── pipeline.py        # Main streaming pipeline
└── requirements.txt
```

## Key Commands Summary

| Action | Command |
|--------|---------|
| Activate env | `source .venv/bin/activate` |
| Run tests | `python scripts/test_blackice.py` |
| Run CLI | `python scripts/run_blackice.py --machine m_1932` |
| Open notebook | `jupyter notebook notebooks/main.ipynb` |
| Install deps | `pip install -r requirements.txt` |
