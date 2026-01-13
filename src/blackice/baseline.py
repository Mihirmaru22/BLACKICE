
from dataclasses import dataclass
from typing import Optional
import math


@dataclass(frozen=True, slots=True)
class BaselineStats:
    mean: float
    variance: float
    std: float
    count: int
    is_warm: bool
    ewma: Optional[float] = None


class RollingBuffer:
    __slots__ = ('_buffer', '_capacity', '_head', '_size')
    
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._buffer: list[Optional[float]] = [None] * capacity
        self._capacity = capacity
        self._head = 0
        self._size = 0
    
    def push(self, value: float) -> Optional[float]:
        displaced = None
        if self._size == self._capacity:
            displaced = self._buffer[self._head]
        else:
            self._size += 1
        
        self._buffer[self._head] = value
        self._head = (self._head + 1) % self._capacity
        return displaced
    
    @property
    def is_full(self) -> bool:
        return self._size == self._capacity
    
    @property
    def size(self) -> int:
        return self._size
    
    @property
    def capacity(self) -> int:
        return self._capacity
    
    def clear(self) -> None:
        self._buffer = [None] * self._capacity
        self._head = 0
        self._size = 0


class BaselineComputer:
    __slots__ = (
        'window_size', 'use_ewma', 'ewma_alpha', 'min_std',
        '_buffer', '_mean', '_m2', '_ewma', '_total_count'
    )
    
    def __init__(
        self,
        window_size: int,
        use_ewma: bool = False,
        ewma_alpha: float = 0.3,
        min_std: float = 1e-8
    ) -> None:
        if window_size < 2:
            raise ValueError("window_size must be at least 2")
        if not (0 < ewma_alpha <= 1):
            raise ValueError("ewma_alpha must be in (0, 1]")
        if min_std < 0:
            raise ValueError("min_std must be non-negative")
        
        self.window_size = window_size
        self.use_ewma = use_ewma
        self.ewma_alpha = ewma_alpha
        self.min_std = min_std
        
        self._buffer = RollingBuffer(window_size)
        self._mean: float = 0.0
        self._m2: float = 0.0
        self._ewma: Optional[float] = None
        self._total_count: int = 0
    
    def update(self, value: float) -> bool:
        if not math.isfinite(value):
            return False
        
        n = self._buffer.size
        displaced = self._buffer.push(value)
        self._total_count += 1
        
        if displaced is None:
            n_new = n + 1
            delta = value - self._mean
            self._mean += delta / n_new
            delta2 = value - self._mean
            self._m2 += delta * delta2
        else:
            old_mean = self._mean
            self._mean += (value - displaced) / self.window_size
            
            self._m2 += (value - displaced) * (
                (value - self._mean) + (displaced - old_mean)
            )
            self._m2 = max(0.0, self._m2)
        
        if self.use_ewma:
            if self._ewma is None:
                self._ewma = value
            else:
                self._ewma = self.ewma_alpha * value + (1 - self.ewma_alpha) * self._ewma
        
        return True
    
    @property
    def is_warm(self) -> bool:
        return self._buffer.is_full
    
    @property
    def is_ready(self) -> bool:
        return self.is_warm
    
    @property
    def count(self) -> int:
        return self._buffer.size
    
    @property
    def total_count(self) -> int:
        return self._total_count
    
    @property
    def mean(self) -> float:
        return self._mean if self._buffer.size > 0 else 0.0
    
    @property
    def variance(self) -> float:
        n = self._buffer.size
        if n < 2:
            return 0.0
        return self._m2 / n
    
    @property
    def std(self) -> float:
        return max(math.sqrt(self.variance), self.min_std)
    
    @property
    def ewma(self) -> Optional[float]:
        return self._ewma
    
    def get_stats(self) -> BaselineStats:
        return BaselineStats(
            mean=self.mean,
            variance=self.variance,
            std=self.std,
            count=self.count,
            is_warm=self.is_warm,
            ewma=self._ewma
        )
    
    def reset(self) -> None:
        self._buffer.clear()
        self._mean = 0.0
        self._m2 = 0.0
        self._ewma = None
        self._total_count = 0
    
    def __repr__(self) -> str:
        warm_status = "warm" if self.is_warm else f"warming:{self.count}/{self.window_size}"
        return (
            f"BaselineComputer({warm_status}, "
            f"mean={self.mean:.4f}, std={self.std:.4f})"
        )
