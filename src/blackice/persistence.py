
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .deviation import DeviationResult, DeviationDirection


class PersistenceStatus(Enum):
    NOT_DEVIATING = "NOT_DEVIATING"
    WATCHING = "WATCHING"
    CONFIRMED = "CONFIRMED"


@dataclass
class PersistenceConfig:
    min_consecutive_points: int = 10
    min_fraction_of_window: float = 0.3
    window_size: int = 60
    
    @property
    def effective_threshold(self) -> int:
        fractional = int(self.min_fraction_of_window * self.window_size)
        return max(self.min_consecutive_points, fractional)


@dataclass
class PersistenceResult:
    status: PersistenceStatus
    consecutive_count: int
    required_count: int
    direction: DeviationDirection
    deviation_start_ts: Optional[int]
    confirmation_ts: Optional[int]
    progress_fraction: float
    
    @property
    def is_confirmed(self) -> bool:
        return self.status == PersistenceStatus.CONFIRMED


class PersistenceValidator:
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        
        self._watching: bool = False
        self._watch_start_ts: Optional[int] = None
        self._confirmed: bool = False
        self._confirmation_ts: Optional[int] = None
        self._last_direction: DeviationDirection = DeviationDirection.NONE
    
    def check(self, deviation: DeviationResult) -> PersistenceResult:
        required = self.config.effective_threshold
        
        if not deviation.is_significant:
            status = PersistenceStatus.NOT_DEVIATING
            self._watching = False
            self._confirmed = False
            self._watch_start_ts = None
            self._confirmation_ts = None
            self._last_direction = DeviationDirection.NONE
            
            return PersistenceResult(
                status=status,
                consecutive_count=0,
                required_count=required,
                direction=DeviationDirection.NONE,
                deviation_start_ts=None,
                confirmation_ts=None,
                progress_fraction=0.0
            )
        
        if deviation.direction != self._last_direction:
            self._watching = True
            self._watch_start_ts = deviation.deviation_start_ts
            self._confirmed = False
            self._confirmation_ts = None
            self._last_direction = deviation.direction
        
        consecutive = deviation.consecutive_count
        progress = consecutive / required if required > 0 else 0.0
        
        if consecutive >= required:
            status = PersistenceStatus.CONFIRMED
            if not self._confirmed:
                self._confirmed = True
                self._confirmation_ts = deviation.timestamp
        else:
            status = PersistenceStatus.WATCHING
        
        return PersistenceResult(
            status=status,
            consecutive_count=consecutive,
            required_count=required,
            direction=deviation.direction,
            deviation_start_ts=self._watch_start_ts,
            confirmation_ts=self._confirmation_ts,
            progress_fraction=min(1.0, progress)
        )
    
    @property
    def is_watching(self) -> bool:
        return self._watching
    
    @property
    def is_confirmed(self) -> bool:
        return self._confirmed
    
    def reset(self) -> None:
        self._watching = False
        self._watch_start_ts = None
        self._confirmed = False
        self._confirmation_ts = None
        self._last_direction = DeviationDirection.NONE
    
    def __repr__(self) -> str:
        status = "CONFIRMED" if self._confirmed else ("WATCHING" if self._watching else "IDLE")
        return f"PersistenceValidator(status={status}, threshold={self.config.effective_threshold})"
