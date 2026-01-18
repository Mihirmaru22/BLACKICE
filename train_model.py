#!/usr/bin/env python3
import sys
import argparse
import pandas as pd
import yaml
from pathlib import Path
from dataclasses import asdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from blackice.learning.optimizer import GridSearchOptimizer
from blackice.learning.objective import AnomalyInterval


def generate_heuristic_ground_truth(df: pd.DataFrame, cpu_threshold: float = 95.0) -> list[AnomalyInterval]:
    """
    Generates 'Ground Truth' labels based on a simple heuristic for demonstration.
    In a real scenario, this would load human-labeled data.
    
    Heuristic: Continuous regions where CPU > threshold are 'True Anomalies'.
    """
    labels = []
    in_anomaly = False
    start_time = None
    
    # Sort by time just in case
    df = df.sort_values('timestamp')
    
    for _, row in df.iterrows():
        is_high = row['cpu_util'] > cpu_threshold
        
        if is_high and not in_anomaly:
            in_anomaly = True
            start_time = row['timestamp']
        elif not is_high and in_anomaly:
            in_anomaly = False
            labels.append(AnomalyInterval(start_time, row['timestamp']))
            
    # Close pending
    if in_anomaly:
        labels.append(AnomalyInterval(start_time, df.iloc[-1]['timestamp']))
        
    return labels

def main():
    parser = argparse.ArgumentParser(description="Train BlackIce Params (Offline Learning)")
    parser.add_argument('data', help="Path to training CSV (machine_usage.csv)")
    parser.add_argument('--output', default='configs/learned_config.yaml', help="Output config file")
    args = parser.parse_args()
    
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"Error: Data file {data_path} not found.")
        sys.exit(1)
        
    print(f"Loading training data from {data_path}...")
    # Load assuming standard schema, but handle only needed columns for speed
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)
        
    # 1. Generate Ground Truth (Simulated Labels)
    print("Generating heuristic ground truth (CPU > 95%)...")
    ground_truth = generate_heuristic_ground_truth(df)
    print(f"Found {len(ground_truth)} mock anomaly intervals.")
    
    if not ground_truth:
        print("Warning: No anomalies found in data. Training might be trivial.")
        
    # 2. Configure Search Space
    # We use a smaller grid for the demo to run fast
    param_grid = {
        "window_size": [10, 20, 50, 100],
        "zscore_threshold": [2.5, 3.0, 4.0, 5.0],
        "min_consecutive_points": [3, 5, 8]
    }
    
    # 3. Run Optimization
    optimizer = GridSearchOptimizer(param_grid)
    best_config = optimizer.train(df, ground_truth)
    
    # 4. Save Result
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        config_dict = asdict(best_config)
        yaml.dump(config_dict, f)
        
    print("\n✅ Training Complete.")
    print(f"Learned Configuration saved to {output_path}")
    print("You can now run the detector with:")
    print(f"  python src/blackice/cli.py --config {output_path} ...")

if __name__ == "__main__":
    main()
