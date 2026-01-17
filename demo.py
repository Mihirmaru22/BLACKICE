
from blackice import RegimeDetector
import random

def demo():
    print("Initializing RegimeDetector...")
    # Smaller window/persistence for quick demo
    # Explicitly set min_fraction=0.0 to rely purely on persistence count (3)
    detector = RegimeDetector(window_size=10, z_threshold=2.0, persistence=3, min_fraction=0.0)
    
    # 1. Feed normal data
    print("\nPhase 1: Normal Operation (Value ~ 50)")
    for i in range(15):
        val = 50 + random.uniform(-1, 1)
        event = detector.update(val)
        print(f"[{i}] Val={val:.1f} -> {event.state.name} (z={event.zscore:.1f})")
        
    # 2. Feed Spike (Anomaly)
    print("\nPhase 2: Introducing Spike (Value = 80)")
    # Should trigger SHIFTED after 3 ticks
    for i in range(5):
        val = 80 + random.uniform(-1, 1)
        event = detector.update(val)
        reason_short = event.reason.split(',')[0] if event.reason else ""
        print(f"[{15+i}] Val={val:.1f} -> {event.state.name} (z={event.zscore:.1f}, reason='{reason_short}...')")
        
    print("\nPhase 3: Returning to Normal")
    for i in range(5):
        val = 50 + random.uniform(-1, 1)
        event = detector.update(val)
        print(f"[{20+i}] Val={val:.1f} -> {event.state.name}")

if __name__ == "__main__":
    demo()
