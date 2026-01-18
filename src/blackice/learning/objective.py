from typing import List
from dataclasses import dataclass
from blackice.state import StateEvent

@dataclass
class AnomalyInterval:
    """Represents a time range where a true anomaly exists."""
    start_time: float
    end_time: float
    
    def contains(self, timestamp: float) -> bool:
        return self.start_time <= timestamp <= self.end_time

def calculate_loss(
    events: List[StateEvent], 
    ground_truth: List[AnomalyInterval],
    penalty_fp: float = 5.0,
    penalty_fn: float = 10.0,
    penalty_delay: float = 0.1
) -> float:
    """
    Calculates the loss (cost) of a detection run against ground truth.
    
    Loss = (False Positives * W_FP) + (False Negatives * W_FN) + (Avg Delay * W_Delay)
    
    Args:
        events: List of detection events produced by the pipeline.
        ground_truth: List of time intervals that are TRUE anomalies.
        penalty_fp: Cost of a False Positive (Alert where no anomaly exists).
        penalty_fn: Cost of a False Negative (Missed anomaly interval).
        penalty_delay: Cost per second of delay in detecting the start of an anomaly.
        
    Returns:
        float: Total loss scores (lower is better).
    """
    false_positives = 0
    detected_intervals = set()
    total_delay = 0.0
    
    # 1. Evaluate Precision (False Positives & Delay)
    for event in events:
        timestamp = event.transition.timestamp
        matched = False
        
        for i, interval in enumerate(ground_truth):
            if interval.contains(timestamp):
                matched = True
                detected_intervals.add(i)
                # Calculate delay only for the first detection in an interval
                # (Simple heuristic: assumes events are sorted)
                delay = max(0, timestamp - interval.start_time)
                total_delay += delay
                break
        
        if not matched:
            false_positives += 1
            
    # 2. Evaluate Recall (False Negatives)
    false_negatives = len(ground_truth) - len(detected_intervals)
    
    # 3. Calculate Weighted Loss
    loss = (
        (false_positives * penalty_fp) +
        (false_negatives * penalty_fn) +
        (total_delay * penalty_delay)
    )
    
    return loss
