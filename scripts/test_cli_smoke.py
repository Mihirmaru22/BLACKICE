#!/usr/bin/env python3
import sys
import subprocess
import csv
import os
from pathlib import Path

def create_dummy_csv(filename):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        # machine_id, timestamp, cpu, mem, c5, c6, c7, c8, c9
        for i in range(100):
            writer.writerow(['m_smoke', 1000+i, 50.0, 40.0, 0, 0, 0, 0, 0])

def main():
    print("Running CLI Smoke Test...")
    
    base_dir = Path(__file__).parent.parent
    data_file = base_dir / "smoke_test_data.csv"
    output_file = base_dir / "smoke_output.json"
    
    # 1. Setup Data
    create_dummy_csv(data_file)
    
    # 2. Run CLI
    cmd = [
        sys.executable,
        str(base_dir / "src/blackice/cli.py"),
        "--config", str(base_dir / "configs/default.yaml"),
        "--data", str(data_file),
        "--machine", "m_smoke",
        "--output", str(output_file)
    ]
    
    # Add src to PYTHONPATH so the CLI can find the package
    env = os.environ.copy()
    src_path = str(base_dir / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    
    print(f"  Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    # Cleanup (comment out if debugging)
    if data_file.exists():
        data_file.unlink()
    if output_file.exists():
        output_file.unlink()
    
    # 3. Assertions
    if result.returncode != 0:
        print("  ❌ CLI failed with non-zero exit code")
        print("  Stderr:", result.stderr)
        sys.exit(1)
        
    print("  ✅ CLI exited successfully (0)")
    
    if "Processing complete" not in result.stdout:
        print("  ❌ CLI stdout missing expected completion message")
        sys.exit(1)
        
    print("  ✅ CLI stdout looks correct")
    return 0

if __name__ == "__main__":
    sys.exit(main())
