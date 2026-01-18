from typing import List, Dict, Any, Optional
import itertools
import pandas as pd
from dataclasses import asdict
import logging

from blackice.pipeline import BlackicePipeline, PipelineConfig
from blackice.learning.objective import calculate_loss, AnomalyInterval

logger = logging.getLogger(__name__)

class GridSearchOptimizer:
    """
    Performs a Grid Search to find the optimal BlackIce configuration
    that minimizes the loss function against a Ground Truth dataset.
    """
    
    def __init__(
        self, 
        param_grid: Optional[Dict[str, List[Any]]] = None
    ):
        self.param_grid = param_grid or {
            "window_size": [10, 20, 50, 100],
            "zscore_threshold": [2.0, 3.0, 4.0, 5.0],
            "min_consecutive_points": [3, 5, 8, 12]
        }
        
    def _generate_configs(self) -> List[PipelineConfig]:
        """Generates all combinations of parameters."""
        keys = self.param_grid.keys()
        values = self.param_grid.values()
        combinations = itertools.product(*values)
        
        configs = []
        for combo in combinations:
            params = dict(zip(keys, combo))
            # Create config object (handling defaults for others)
            config = PipelineConfig(
                window_size=params["window_size"],
                zscore_threshold=params["zscore_threshold"],
                min_consecutive_points=params["min_consecutive_points"]
            )
            configs.append(config)
        return configs

    def train(
        self, 
        df: pd.DataFrame, 
        ground_truth: List[AnomalyInterval]
    ) -> Optional[PipelineConfig]:
        """
        Runs the optimization loop.
        
        Args:
            df: Historical training data.
            ground_truth: Known anomaly intervals.
            
        Returns:
            PipelineConfig: The best configuration found.
        """
        configs = self._generate_configs()
        best_loss = float('inf')
        best_config = None
        
        print(f"Starting Grid Search over {len(configs)} configurations...")
        
        for i, config in enumerate(configs):
            # 1. Initialize Pipeline
            pipeline = BlackicePipeline(config)
            
            # 2. Run Inference (Offline Training Mode)
            # We treat the whole df as one stream source per machine
            events = pipeline.process_chunk(df)
            
            # 3. Calculate Loss
            loss = calculate_loss(events, ground_truth)
            
            print(f"[{i+1}/{len(configs)}] Params: {asdict(config)} -> Loss: {loss:.4f}")
            
            # 4. Update Best
            if loss < best_loss:
                best_loss = loss
                best_config = config
                
        print("\nOptimization Complete.")
        if best_config:
            print(f"Best Loss: {best_loss:.4f}")
            print(f"Best Config: {asdict(best_config)}")
        else:
            print("Optimization failed: No valid config found.")
        
        return best_config
