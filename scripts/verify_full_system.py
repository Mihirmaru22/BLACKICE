#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def run_step(description: str, command: str) -> bool:
    print(f"\n🔵 [STEP] {description}...")
    try:
        # Run command, capturing output but streaming it if it fails
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        print(f"✅ SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED")
        print(f"Command: {command}")
        print("--- Output ---")
        print(e.stdout)
        print("--- Error ---")
        print(e.stderr)
        return False

def main():
    print("❄️  Verifying BLACKICE Full System (Hybrid ML Architecture) ❄️")
    print("=============================================================")
    
    # 1. Unit & Integration Tests (The Engine)
    if not run_step("Running Core Engine Tests", "python scripts/test_blackice.py"):
        sys.exit(1)
        
    # 2. System Invariant Tests (Determinism)
    # Ensure PYTHONPATH is set so scripts can find src
    if not run_step("Running Systems Invariant Checks (Determinism)", "export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python scripts/test_determinism.py"):
        sys.exit(1)
        
    # 3. Hybrid ML: Offline Training (The Brain)
    # Create dummy data first
    dummy_data = """machine_id,timestamp,cpu_util,mem_util,c5,c6,c7,c8,c9
m_test,100,50.0,40.0,0,0,0,0,0
m_test,101,99.0,40.0,0,0,0,0,0
m_test,102,99.0,40.0,0,0,0,0,0
m_test,103,50.0,40.0,0,0,0,0,0
"""
    with open("verify_ml_data.csv", "w") as f:
        f.write(dummy_data)
        
    if not run_step("Running Offline ML Optimizer (Training Loop)", "python train_model.py verify_ml_data.csv --output configs/verify_learned.yaml"):
        Path("verify_ml_data.csv").unlink()
        sys.exit(1)
        
    # 4. Hybrid ML: Inference with Learned Config
    if not run_step("Running Inference with Learned Config", "export PYTHONPATH=$PYTHONPATH:$(pwd)/src && python src/blackice/cli.py --data verify_ml_data.csv --config configs/verify_learned.yaml --report"):
        Path("verify_ml_data.csv").unlink()
        Path("configs/verify_learned.yaml").unlink()
        sys.exit(1)

    # Cleanup
    if Path("verify_ml_data.csv").exists(): Path("verify_ml_data.csv").unlink()
    if Path("configs/verify_learned.yaml").exists(): Path("configs/verify_learned.yaml").unlink()
    
    print("\n✨ ALL SYSTEMS OPERATIONAL. PROJECT IS READY FOR DEPLOYMENT. ✨")

if __name__ == "__main__":
    main()
