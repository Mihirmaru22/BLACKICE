
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time
import tracemalloc

from .state import StateTransition, RegimeState
from .deviation import DeviationDirection


@dataclass
class DetectionQualityMetrics:
    detection_latency_mean: float = 0.0
    detection_latency_max: float = 0.0
    spike_rejection_rate: float = 0.0
    confirmed_shifts: int = 0
    rejected_spikes: int = 0
    
    def to_dict(self) -> dict:
        return {
            "detection_latency_mean": self.detection_latency_mean,
            "detection_latency_max": self.detection_latency_max,
            "spike_rejection_rate": self.spike_rejection_rate,
            "confirmed_shifts": self.confirmed_shifts,
            "rejected_spikes": self.rejected_spikes
        }


@dataclass
class StabilityMetrics:
    mean_time_between_regimes: float = 0.0
    average_regime_duration: float = 0.0
    total_regimes: int = 0
    time_in_normal_pct: float = 0.0
    time_in_unstable_pct: float = 0.0
    time_in_shifted_pct: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "mean_time_between_regimes": self.mean_time_between_regimes,
            "average_regime_duration": self.average_regime_duration,
            "total_regimes": self.total_regimes,
            "time_in_normal_pct": self.time_in_normal_pct,
            "time_in_unstable_pct": self.time_in_unstable_pct,
            "time_in_shifted_pct": self.time_in_shifted_pct
        }


@dataclass  
class SystemsMetrics:
    rows_processed: int = 0
    total_time_seconds: float = 0.0
    rows_per_second: float = 0.0
    peak_memory_mb: float = 0.0
    avg_time_per_chunk_ms: float = 0.0
    chunks_processed: int = 0
    
    def to_dict(self) -> dict:
        return {
            "rows_processed": self.rows_processed,
            "total_time_seconds": self.total_time_seconds,
            "rows_per_second": self.rows_per_second,
            "peak_memory_mb": self.peak_memory_mb,
            "avg_time_per_chunk_ms": self.avg_time_per_chunk_ms,
            "chunks_processed": self.chunks_processed
        }


class MetricsComputer:
    
    def __init__(self, track_memory: bool = True):
        self.track_memory = track_memory
        
        self._start_time: Optional[float] = None
        self._chunk_times: List[float] = []
        self._rows_processed: int = 0
        self._peak_memory: float = 0.0
        
        self._unstable_entries: int = 0
        self._shifted_entries: int = 0
        self._normal_returns: int = 0
        
        if track_memory:
            tracemalloc.start()
    
    def start_processing(self) -> None:
        self._start_time = time.time()
    
    def record_chunk(self, rows: int, duration: float) -> None:
        self._rows_processed += rows
        self._chunk_times.append(duration)
        
        if self.track_memory:
            current, peak = tracemalloc.get_traced_memory()
            self._peak_memory = max(self._peak_memory, peak / 1024 / 1024)
    
    def record_transition(self, transition: StateTransition) -> None:
        if transition.to_state == RegimeState.UNSTABLE:
            self._unstable_entries += 1
        elif transition.to_state == RegimeState.SHIFTED:
            self._shifted_entries += 1
        elif transition.to_state == RegimeState.NORMAL:
            self._normal_returns += 1
    
    def compute_detection_quality(
        self, 
        transitions: List[StateTransition]
    ) -> DetectionQualityMetrics:
        latencies = []
        confirmed = 0
        rejected = 0
        
        unstable_start = None
        
        for t in transitions:
            if t.to_state == RegimeState.UNSTABLE:
                unstable_start = t.timestamp
            elif t.to_state == RegimeState.SHIFTED and unstable_start is not None:
                latencies.append(t.timestamp - unstable_start)
                confirmed += 1
                unstable_start = None
            elif t.to_state == RegimeState.NORMAL and t.from_state == RegimeState.UNSTABLE:
                rejected += 1
                unstable_start = None
        
        for t in transitions:
            if t.to_state == RegimeState.SHIFTED and t.from_state == RegimeState.NORMAL:
                confirmed += 1
        
        total_unstable = confirmed + rejected
        rejection_rate = rejected / total_unstable if total_unstable > 0 else 0.0
        
        return DetectionQualityMetrics(
            detection_latency_mean=sum(latencies) / len(latencies) if latencies else 0.0,
            detection_latency_max=max(latencies) if latencies else 0.0,
            spike_rejection_rate=rejection_rate,
            confirmed_shifts=confirmed,
            rejected_spikes=rejected
        )
    
    def compute_stability(
        self, 
        transitions: List[StateTransition],
        total_duration: int
    ) -> StabilityMetrics:
        if not transitions:
            return StabilityMetrics(
                time_in_normal_pct=100.0
            )
        
        shift_times = [
            t.timestamp for t in transitions 
            if t.to_state == RegimeState.SHIFTED
        ]
        
        regime_intervals = []
        for i in range(1, len(shift_times)):
            regime_intervals.append(shift_times[i] - shift_times[i-1])
        
        regime_durations = []
        shifted_start = None
        for t in transitions:
            if t.to_state == RegimeState.SHIFTED:
                shifted_start = t.timestamp
            elif shifted_start is not None and t.from_state == RegimeState.SHIFTED:
                regime_durations.append(t.timestamp - shifted_start)
                shifted_start = None
        
        time_in_normal = 0
        time_in_unstable = 0
        time_in_shifted = 0
        
        sorted_trans = sorted(transitions, key=lambda x: x.timestamp)
        if sorted_trans:
            prev_time = 0
            prev_state = RegimeState.NORMAL
            
            for t in sorted_trans:
                duration = t.timestamp - prev_time
                if prev_state == RegimeState.NORMAL:
                    time_in_normal += duration
                elif prev_state == RegimeState.UNSTABLE:
                    time_in_unstable += duration
                elif prev_state == RegimeState.SHIFTED:
                    time_in_shifted += duration
                prev_time = t.timestamp
                prev_state = t.to_state
            
            final_duration = total_duration - prev_time
            if prev_state == RegimeState.NORMAL:
                time_in_normal += final_duration
            elif prev_state == RegimeState.UNSTABLE:
                time_in_unstable += final_duration
            elif prev_state == RegimeState.SHIFTED:
                time_in_shifted += final_duration
        
        total_time = time_in_normal + time_in_unstable + time_in_shifted
        if total_time == 0:
            total_time = 1
        
        return StabilityMetrics(
            mean_time_between_regimes=sum(regime_intervals) / len(regime_intervals) if regime_intervals else 0.0,
            average_regime_duration=sum(regime_durations) / len(regime_durations) if regime_durations else 0.0,
            total_regimes=len(shift_times),
            time_in_normal_pct=(time_in_normal / total_time) * 100,
            time_in_unstable_pct=(time_in_unstable / total_time) * 100,
            time_in_shifted_pct=(time_in_shifted / total_time) * 100
        )
    
    def compute_systems_metrics(self) -> SystemsMetrics:
        total_time = time.time() - self._start_time if self._start_time else 0.0
        
        return SystemsMetrics(
            rows_processed=self._rows_processed,
            total_time_seconds=total_time,
            rows_per_second=self._rows_processed / total_time if total_time > 0 else 0.0,
            peak_memory_mb=self._peak_memory,
            avg_time_per_chunk_ms=(sum(self._chunk_times) / len(self._chunk_times) * 1000) if self._chunk_times else 0.0,
            chunks_processed=len(self._chunk_times)
        )
    
    def stop_tracking(self) -> None:
        if self.track_memory:
            tracemalloc.stop()
    
    def reset(self) -> None:
        self._start_time = None
        self._chunk_times.clear()
        self._rows_processed = 0
        self._peak_memory = 0.0
        self._unstable_entries = 0
        self._shifted_entries = 0
        self._normal_returns = 0


def compute_variance_shift(
    pre_values: List[float], 
    post_values: List[float]
) -> Dict[str, float]:
    import statistics
    
    if len(pre_values) < 2 or len(post_values) < 2:
        return {"pre_variance": 0.0, "post_variance": 0.0, "ratio": 1.0}
    
    pre_var = statistics.variance(pre_values)
    post_var = statistics.variance(post_values)
    
    ratio = post_var / pre_var if pre_var > 0 else float('inf')
    
    return {
        "pre_variance": pre_var,
        "post_variance": post_var,
        "ratio": ratio,
        "significant_change": abs(ratio - 1.0) > 0.5
    }
