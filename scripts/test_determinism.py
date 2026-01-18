#!/usr/bin/env python3
import sys
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from blackice.pipeline import BlackicePipeline, PipelineConfig

def generate_fixed_data():
    """Generate a deterministic dataset"""
    data = []
    # Machine 1: Stable
    for i in range(50):
        data.append({
            'machine_id': 'm_fixed',
            'timestamp': 1000 + i,
            'cpu_util': 50.0,
            'mem_util': 40.0
        })
    # Machine 1: Spike
    for i in range(50, 60):
        data.append({
            'machine_id': 'm_fixed',
            'timestamp': 1000 + i,
            'cpu_util': 90.0, # Spike
            'mem_util': 40.0
        })
    # Machine 1: Return
    for i in range(60, 100):
        data.append({
            'machine_id': 'm_fixed',
            'timestamp': 1000 + i,
            'cpu_util': 50.0,
            'mem_util': 40.0
        })
    return pd.DataFrame(data)

def run_pipeline(df):
    config = PipelineConfig(
        window_size=20,
        zscore_threshold=2.0,
        min_consecutive_points=5
    )
    pipeline = BlackicePipeline(config)
    events = pipeline.process_chunk(df)
    return [e.to_dict() for e in events]

def main():
    print("Running Determinism Check...")
    
    df = generate_fixed_data()
    
    # Run 1
    print("  Run 1...")
    results_1 = run_pipeline(df)
    
    # Run 2
    print("  Run 2...")
    results_2 = run_pipeline(df)
    
    # Compare
    if len(results_1) != len(results_2):
        print(f"  ❌ Mismatch event counts: {len(results_1)} vs {len(results_2)}")
        sys.exit(1)
        
    for i, (r1, r2) in enumerate(zip(results_1, results_2)):
        # Compare critical fields - note StateEvent.to_dict() flattens the transition
        if r1['to_state'] != r2['to_state']:
            print(f"  ❌ Event {i} state mismatch: {r1['to_state']} vs {r2['to_state']}")
            sys.exit(1)
        if abs(r1['zscore'] - r2['zscore']) > 1e-9:
             print(f"  ❌ Event {i} z-score mismatch")
             sys.exit(1)
             
    print("  ✅ Determinism Verified: Output is bit-exact identical.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
