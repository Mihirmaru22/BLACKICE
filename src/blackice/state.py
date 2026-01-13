
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .deviation import DeviationDirection
from .persistence import PersistenceResult, PersistenceStatus


class RegimeState(Enum):
    NORMAL = "NORMAL"
    UNSTABLE = "UNSTABLE"
    SHIFTED = "SHIFTED"


@dataclass
class StateTransition:
    from_state: RegimeState
    to_state: RegimeState
    timestamp: int
    direction: DeviationDirection
    reason: str
    zscore: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp,
            "direction": self.direction.value,
            "reason": self.reason,
            "zscore": self.zscore
        }


@dataclass
class StateEvent:
    metric_name: str
    transition: StateTransition
    machine_id: str = ""
    
    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "machine_id": self.machine_id,
            **self.transition.to_dict()
        }


class RegimeStateMachine:
    
    def __init__(self, metric_name: str = "metric"):
        self.metric_name = metric_name
        self._state: RegimeState = RegimeState.NORMAL
        self._transitions: List[StateTransition] = []
        self._unstable_since: Optional[int] = None
        self._shifted_since: Optional[int] = None
        self._last_direction: DeviationDirection = DeviationDirection.NONE
    
    def process(
        self, 
        persistence: PersistenceResult, 
        timestamp: int,
        zscore: float = 0.0
    ) -> Optional[StateTransition]:
        transition = None
        
        if self._state == RegimeState.NORMAL:
            if persistence.status == PersistenceStatus.WATCHING:
                transition = self._transition_to(
                    RegimeState.UNSTABLE,
                    timestamp,
                    persistence.direction,
                    zscore,
                    f"Significant deviation detected ({persistence.direction.value}), "
                    f"watching for persistence ({persistence.consecutive_count}/{persistence.required_count})"
                )
                self._unstable_since = timestamp
                
            elif persistence.status == PersistenceStatus.CONFIRMED:
                transition = self._transition_to(
                    RegimeState.SHIFTED,
                    timestamp,
                    persistence.direction,
                    zscore,
                    f"Immediate regime shift confirmed ({persistence.direction.value}), "
                    f"deviation persisted for {persistence.consecutive_count} points"
                )
                self._shifted_since = timestamp
        
        elif self._state == RegimeState.UNSTABLE:
            if persistence.status == PersistenceStatus.NOT_DEVIATING:
                transition = self._transition_to(
                    RegimeState.NORMAL,
                    timestamp,
                    DeviationDirection.NONE,
                    zscore,
                    f"Deviation did not persist (noise filtered), "
                    f"returning to normal after {timestamp - self._unstable_since} time units"
                )
                self._unstable_since = None
                
            elif persistence.status == PersistenceStatus.CONFIRMED:
                transition = self._transition_to(
                    RegimeState.SHIFTED,
                    timestamp,
                    persistence.direction,
                    zscore,
                    f"Regime shift confirmed ({persistence.direction.value}), "
                    f"deviation persisted for {persistence.consecutive_count} points"
                )
                self._shifted_since = timestamp
                self._unstable_since = None
        
        elif self._state == RegimeState.SHIFTED:
            if persistence.status == PersistenceStatus.NOT_DEVIATING:
                transition = self._transition_to(
                    RegimeState.NORMAL,
                    timestamp,
                    DeviationDirection.NONE,
                    zscore,
                    f"System returned to baseline, "
                    f"regime lasted {timestamp - self._shifted_since} time units"
                )
                self._shifted_since = None
                
            elif persistence.status == PersistenceStatus.WATCHING:
                if persistence.direction != self._last_direction:
                    transition = self._transition_to(
                        RegimeState.UNSTABLE,
                        timestamp,
                        persistence.direction,
                        zscore,
                        f"New deviation in opposite direction ({persistence.direction.value}), "
                        f"watching for new regime"
                    )
                    self._unstable_since = timestamp
                    self._shifted_since = None
        
        if persistence.status != PersistenceStatus.NOT_DEVIATING:
            self._last_direction = persistence.direction
        
        return transition
    
    def _transition_to(
        self, 
        new_state: RegimeState, 
        timestamp: int,
        direction: DeviationDirection,
        zscore: float,
        reason: str
    ) -> StateTransition:
        transition = StateTransition(
            from_state=self._state,
            to_state=new_state,
            timestamp=timestamp,
            direction=direction,
            zscore=zscore,
            reason=reason
        )
        self._state = new_state
        self._transitions.append(transition)
        return transition
    
    @property
    def current_state(self) -> RegimeState:
        return self._state
    
    @property
    def transitions(self) -> List[StateTransition]:
        return self._transitions.copy()
    
    @property
    def transition_count(self) -> int:
        return len(self._transitions)
    
    def reset(self) -> None:
        self._state = RegimeState.NORMAL
        self._transitions.clear()
        self._unstable_since = None
        self._shifted_since = None
        self._last_direction = DeviationDirection.NONE
    
    def __repr__(self) -> str:
        return (
            f"RegimeStateMachine(metric={self.metric_name}, "
            f"state={self._state.value}, transitions={len(self._transitions)})"
        )
