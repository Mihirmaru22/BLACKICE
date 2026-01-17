
import time
from dataclasses import dataclass
from typing import Optional

from .baseline import BaselineComputer
from .deviation import DeviationTracker
from .persistence import PersistenceValidator, PersistenceConfig
from .state import RegimeStateMachine, RegimeState

@dataclass
class DetectionEvent:
    """
    A high-level event representing the system's current regime status.
    Returned by RegimeDetector.update().
    """
    timestamp: float
    value: float
    zscore: float
    state: RegimeState
    reason: str
    duration: float  # Duration in current state in seconds
    is_anomaly: bool # Helper property: True if not NORMAL

class RegimeDetector:
    """
    The main entry point for BLACKICE.
    
    Wraps the statistical engine (Baseline, Deviation, Persistence, State Machine)
    into a single, easy-to-use object.
    
    Usage:
        detector = RegimeDetector(window_size=60, z_threshold=3.0)
        event = detector.update(cpu_usage)
        if event.is_anomaly:
            print(f"Anomaly detected: {event.reason}")
    """
    
    def __init__(
        self, 
        window_size: int = 60, 
        z_threshold: float = 3.0,
        persistence: int = 10,
        min_fraction: float = 0.1,
        metric_name: str = "metric"
    ):
        """
        Initialize the detector with configuration.
        
        Args:
            window_size: Number of samples for the sliding window baseline.
            z_threshold: Sigma threshold for outlier detection (e.g., 3.0).
            persistence: Minimum consecutive outliers to confirm a regime shift.
            min_fraction: Minimum fraction of outliers in window (e.g., 0.1).
            metric_name: Label for the metric (used in logs/reasons).
        """
        self.metric_name = metric_name
        
        # 1. Baseline Computer (O(1) Welford's Algorithm)
        self.baseline = BaselineComputer(window_size=window_size)
        
        # 2. Deviation Tracker (Z-Score monitoring)
        self.deviation = DeviationTracker(
            baseline=self.baseline, 
            zscore_threshold=z_threshold
        )
        
        # 3. Persistence Validator (Noise filtering)
        self.persistence = PersistenceValidator(
            PersistenceConfig(
                min_consecutive_points=persistence,
                min_fraction_of_window=min_fraction,
                window_size=window_size
            )
        )
        
        # 4. State Machine (Deterministic regimes)
        self.sm = RegimeStateMachine(metric_name=metric_name)
        
        # Internal tracking for duration
        self._state_start_ts: Optional[float] = None
        self._last_state: RegimeState = RegimeState.NORMAL
        
    def update(self, value: float, timestamp: Optional[float] = None) -> DetectionEvent:
        """
        Process a new data point and return the current system state.
        
        Args:
            value: The numeric metric value (e.g., CPU %, latency ms).
            timestamp: Optional epoch timestamp. Defaults to time.time().
            
        Returns:
            DetectionEvent object containing state, z-score, duration, etc.
        """
        if timestamp is None:
            timestamp = time.time()
            
        # 0. Initial state timestamp tracking
        if self._state_start_ts is None:
            self._state_start_ts = timestamp
            
        # 1. Update internals (Chain of Responsibility)
        dev_result = self.deviation.update(value, int(timestamp))
        persist_result = self.persistence.check(dev_result)
        
        # 2. Process State Machine
        # Note: process() returns a transaction IF state changed, but we want current state
        transition = self.sm.process(persist_result, int(timestamp), zscore=dev_result.zscore)
        current_state = self.sm.current_state
        
        # 3. Handle Duration Logic
        if current_state != self._last_state:
            self._state_start_ts = timestamp
            self._last_state = current_state
            
        duration = timestamp - self._state_start_ts
        
        # 4. Construct high-level event
        reason = "Normal operation"
        if current_state == RegimeState.UNSTABLE:
            reason = f"Volatility detected (z={dev_result.zscore:.1f})"
        elif current_state == RegimeState.SHIFTED:
            reason = f"regime shift confirmed (duration={duration:.1f}s)"
            
        # Override reason if we just transitioned
        if transition:
            reason = transition.reason
            
        return DetectionEvent(
            timestamp=timestamp,
            value=value,
            zscore=dev_result.zscore,
            state=current_state,
            reason=reason,
            duration=duration,
            is_anomaly=(current_state != RegimeState.NORMAL)
        )
        
    @property
    def is_calibrated(self) -> bool:
        """True if the baseline window is full and statistics are reliable."""
        return self.baseline.is_ready
