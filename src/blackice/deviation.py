
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import math

from .baseline import BaselineComputer


class DeviationDirection(Enum):
    NONE = "NONE"
    HIGH = "HIGH"
    LOW = "LOW"


@dataclass
class DeviationResult:
    timestamp: int
    value: float
    zscore: float
    magnitude: float
    direction: DeviationDirection
    consecutive_count: int
    deviation_start_ts: Optional[int]
    is_significant: bool
    
    @property
    def duration(self) -> int:
        if self.deviation_start_ts is None:
            return 0
        return self.timestamp - self.deviation_start_ts


class DeviationTracker:
    
    def __init__(
        self, 
        baseline: BaselineComputer,
        zscore_threshold: float = 2.0
    ):
        self.baseline = baseline
        self.zscore_threshold = zscore_threshold
        
        self._consecutive_deviations: int = 0
        self._deviation_start_ts: Optional[int] = None
        self._current_direction: DeviationDirection = DeviationDirection.NONE
        self._last_significant_zscore: float = 0.0
    
    def compute_zscore(self, value: float) -> float:
        std = self.baseline.std
        if std < 1e-6:
            return 0.0
        return (value - self.baseline.mean) / std
    
    def update(self, value: float, timestamp: int) -> DeviationResult:
        zscore = self.compute_zscore(value)
        magnitude = abs(zscore)
        
        if magnitude >= self.zscore_threshold:
            direction = DeviationDirection.HIGH if zscore > 0 else DeviationDirection.LOW
            is_significant = True
            
            if self._current_direction == direction:
                self._consecutive_deviations += 1
            else:
                self._consecutive_deviations = 1
                self._deviation_start_ts = timestamp
                self._current_direction = direction
            
            self._last_significant_zscore = zscore
        else:
            direction = DeviationDirection.NONE
            is_significant = False
            self._consecutive_deviations = 0
            self._deviation_start_ts = None
            self._current_direction = DeviationDirection.NONE
        
        self.baseline.update(value)
        
        return DeviationResult(
            timestamp=timestamp,
            value=value,
            zscore=zscore,
            magnitude=magnitude,
            direction=direction,
            consecutive_count=self._consecutive_deviations,
            deviation_start_ts=self._deviation_start_ts,
            is_significant=is_significant
        )
    
    @property
    def consecutive_deviations(self) -> int:
        return self._consecutive_deviations
    
    @property
    def current_direction(self) -> DeviationDirection:
        return self._current_direction
    
    @property
    def last_significant_zscore(self) -> float:
        return self._last_significant_zscore
    
    def reset(self) -> None:
        self._consecutive_deviations = 0
        self._deviation_start_ts = None
        self._current_direction = DeviationDirection.NONE
        self._last_significant_zscore = 0.0
    
    def __repr__(self) -> str:
        return (
            f"DeviationTracker(threshold={self.zscore_threshold}, "
            f"consecutive={self._consecutive_deviations}, "
            f"direction={self._current_direction.value})"
        )
