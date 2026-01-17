
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Iterator, Any
import time
import pandas as pd

from .baseline import BaselineComputer
from .deviation import DeviationTracker
from .persistence import PersistenceValidator, PersistenceConfig
from .state import RegimeStateMachine, StateTransition, StateEvent, RegimeState
from .metrics import MetricsComputer


@dataclass
class PipelineConfig:
    window_size: int = 60
    use_ewma: bool = False
    ewma_alpha: float = 0.3
    zscore_threshold: float = 2.0
    min_consecutive_points: int = 10
    min_fraction_of_window: float = 0.3
    track_cpu: bool = True
    track_memory: bool = True
    
    @classmethod
    def from_dict(cls, config: dict) -> "PipelineConfig":
        baseline = config.get("baseline", {})
        deviation = config.get("deviation", {})
        persistence = config.get("persistence", {})
        metrics = config.get("metrics", {})
        
        return cls(
            window_size=baseline.get("window_size", 60),
            use_ewma=baseline.get("use_ewma", False),
            ewma_alpha=baseline.get("ewma_alpha", 0.3),
            zscore_threshold=deviation.get("zscore_threshold", 2.0),
            min_consecutive_points=persistence.get("min_consecutive_points", 10),
            min_fraction_of_window=persistence.get("min_fraction_of_window", 0.3),
            track_cpu=metrics.get("cpu", True),
            track_memory=metrics.get("memory", True)
        )


@dataclass
class MetricTracker:
    name: str
    baseline: BaselineComputer
    deviation: DeviationTracker
    persistence: PersistenceValidator
    state_machine: RegimeStateMachine
    
    values: List[float] = field(default_factory=list)
    timestamps: List[int] = field(default_factory=list)
    zscores: List[float] = field(default_factory=list)
    means: List[float] = field(default_factory=list)
    stds: List[float] = field(default_factory=list)


class BlackicePipeline:
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        
        self._trackers: Dict[str, MetricTracker] = {}
        
        if config.track_cpu:
            self._trackers["cpu"] = self._create_tracker("cpu")
        if config.track_memory:
            self._trackers["memory"] = self._create_tracker("memory")
        
        self._metrics = MetricsComputer(track_memory=True)
        self._events: List[StateEvent] = []
        self._machine_id: str = ""
        self._first_timestamp: Optional[int] = None
        self._last_timestamp: Optional[int] = None
        self._started: bool = False
    
    def _create_tracker(self, name: str) -> MetricTracker:
        baseline = BaselineComputer(
            window_size=self.config.window_size,
            use_ewma=self.config.use_ewma,
            ewma_alpha=self.config.ewma_alpha
        )
        
        deviation = DeviationTracker(
            baseline=baseline,
            zscore_threshold=self.config.zscore_threshold
        )
        
        persistence_config = PersistenceConfig(
            min_consecutive_points=self.config.min_consecutive_points,
            min_fraction_of_window=self.config.min_fraction_of_window,
            window_size=self.config.window_size
        )
        persistence = PersistenceValidator(persistence_config)
        
        state_machine = RegimeStateMachine(metric_name=name)
        
        return MetricTracker(
            name=name,
            baseline=baseline,
            deviation=deviation,
            persistence=persistence,
            state_machine=state_machine
        )
    
    def process_chunk(self, df_chunk: pd.DataFrame) -> List[StateEvent]:
        if not self._started:
            self._metrics.start_processing()
            self._started = True
        
        start_time = time.time()
        events: List[StateEvent] = []
        
        if df_chunk.empty:
            return events
        
        if self._machine_id == "" and "machine_id" in df_chunk.columns:
            self._machine_id = str(df_chunk["machine_id"].iloc[0])
        
        for row in df_chunk.itertuples(index=False):
            timestamp = int(row.timestamp)
            
            if self._first_timestamp is None:
                self._first_timestamp = timestamp
            self._last_timestamp = timestamp
            
            if "cpu" in self._trackers and hasattr(row, "cpu_util"):
                event = self._process_point(
                    self._trackers["cpu"],
                    float(row.cpu_util),
                    timestamp
                )
                if event:
                    events.append(event)
            
            if "memory" in self._trackers and hasattr(row, "mem_util"):
                event = self._process_point(
                    self._trackers["memory"],
                    float(row.mem_util),
                    timestamp
                )
                if event:
                    events.append(event)
        
        duration = time.time() - start_time
        self._metrics.record_chunk(len(df_chunk), duration)
        
        self._events.extend(events)
        
        return events
    
    def _process_point(
        self, 
        tracker: MetricTracker, 
        value: float, 
        timestamp: int
    ) -> Optional[StateEvent]:
        tracker.values.append(value)
        tracker.timestamps.append(timestamp)
        tracker.means.append(tracker.baseline.mean)
        tracker.stds.append(tracker.baseline.std)
        
        deviation_result = tracker.deviation.update(value, timestamp)
        tracker.zscores.append(deviation_result.zscore)
        
        if not tracker.baseline.is_ready:
            return None
        
        persistence_result = tracker.persistence.check(deviation_result)
        
        transition = tracker.state_machine.process(
            persistence_result, 
            timestamp,
            zscore=deviation_result.zscore
        )
        
        if transition:
            self._metrics.record_transition(transition)
            return StateEvent(
                metric_name=tracker.name,
                transition=transition,
                machine_id=self._machine_id
            )
        
        return None
    
    @property
    def events(self) -> List[StateEvent]:
        return self._events.copy()
    
    @property
    def machine_id(self) -> str:
        return self._machine_id
    
    def get_tracker(self, metric: str) -> Optional[MetricTracker]:
        return self._trackers.get(metric)
    
    def get_transitions(self, metric: str) -> List[StateTransition]:
        tracker = self._trackers.get(metric)
        if tracker:
            return tracker.state_machine.transitions
        return []
    
    def get_current_state(self, metric: str) -> Optional[RegimeState]:
        tracker = self._trackers.get(metric)
        if tracker:
            return tracker.state_machine.current_state
        return None
    
    def get_time_series_data(self, metric: str) -> Dict[str, List]:
        tracker = self._trackers.get(metric)
        if not tracker:
            return {}
        
        return {
            "timestamps": tracker.timestamps.copy(),
            "values": tracker.values.copy(),
            "means": tracker.means.copy(),
            "stds": tracker.stds.copy(),
            "zscores": tracker.zscores.copy()
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        total_duration = 0
        if self._first_timestamp and self._last_timestamp:
            total_duration = self._last_timestamp - self._first_timestamp
        
        result = {
            "machine_id": self._machine_id,
            "total_duration": total_duration,
            "systems": self._metrics.compute_systems_metrics().to_dict()
        }
        
        for name, tracker in self._trackers.items():
            transitions = tracker.state_machine.transitions
            result[name] = {
                "detection": self._metrics.compute_detection_quality(transitions).to_dict(),
                "stability": self._metrics.compute_stability(transitions, total_duration).to_dict(),
                "current_state": tracker.state_machine.current_state.value,
                "transition_count": len(transitions)
            }
        
        return result
    
    def stop(self) -> None:
        self._metrics.stop_tracking()
    
    def reset(self) -> None:
        for tracker in self._trackers.values():
            tracker.baseline.reset()
            tracker.deviation.reset()
            tracker.persistence.reset()
            tracker.state_machine.reset()
            tracker.values.clear()
            tracker.timestamps.clear()
            tracker.zscores.clear()
            tracker.means.clear()
            tracker.stds.clear()
        
        self._metrics.reset()
        self._events.clear()
        self._machine_id = ""
        self._first_timestamp = None
        self._last_timestamp = None
        self._started = False
    
    def __repr__(self) -> str:
        trackers = ", ".join(self._trackers.keys())
        return f"BlackicePipeline(trackers=[{trackers}], events={len(self._events)})"


def stream_machine_data(
    filepath: str,
    machine_id: str,
    chunksize: int = 500000,
    columns: Optional[List[str]] = None
) -> Iterator[pd.DataFrame]:
    if columns is None:
        columns = ["machine_id", "timestamp", "cpu_util", "mem_util", "c5", "c6", "c7", "c8", "c9"]
    
    reader = pd.read_csv(
        filepath,
        names=columns,
        header=None,
        usecols=["machine_id", "timestamp", "cpu_util", "mem_util"],
        chunksize=chunksize
    )
    
    for chunk in reader:
        filtered = chunk[chunk["machine_id"] == machine_id]
        if not filtered.empty:
            yield filtered.sort_values("timestamp")
