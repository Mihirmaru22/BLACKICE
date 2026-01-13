#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import math
import yaml


def test_rolling_buffer():
    from blackice.baseline import RollingBuffer
    
    print("Testing RollingBuffer...")
    
    rb = RollingBuffer(5)
    assert rb.size == 0
    assert rb.is_full == False
    
    for i in range(5):
        displaced = rb.push(float(i))
        assert displaced is None
    
    assert rb.size == 5
    assert rb.is_full == True
    
    displaced = rb.push(99.0)
    assert displaced == 0.0
    
    rb.clear()
    assert rb.size == 0
    assert rb.is_full == False
    
    print("  ✓ RollingBuffer passed")


def test_baseline_computer():
    from blackice.baseline import BaselineComputer
    
    print("Testing BaselineComputer...")
    
    bc = BaselineComputer(window_size=10)
    assert bc.is_warm == False
    assert bc.is_ready == False
    assert bc.count == 0
    
    for i in range(10):
        bc.update(float(i))
    
    assert bc.is_warm == True
    assert bc.is_ready == True
    assert bc.count == 10
    
    expected_mean = 4.5
    assert abs(bc.mean - expected_mean) < 0.01, f"Mean {bc.mean} != {expected_mean}"
    
    assert bc.variance > 0
    assert bc.std > 0
    
    result = bc.update(float('nan'))
    assert result == False
    
    result = bc.update(float('inf'))
    assert result == False
    
    bc.reset()
    assert bc.is_warm == False
    assert bc.count == 0
    
    print("  ✓ BaselineComputer passed")


def test_deviation_tracker():
    from blackice.baseline import BaselineComputer
    from blackice.deviation import DeviationTracker, DeviationDirection
    
    print("Testing DeviationTracker...")
    
    baseline = BaselineComputer(window_size=10)
    tracker = DeviationTracker(baseline, zscore_threshold=2.0)
    
    for i in range(10):
        tracker.update(50.0 + (i % 2) * 0.01, timestamp=i)
    
    result = tracker.update(50.0, timestamp=10)
    assert result.is_significant == False
    assert result.direction == DeviationDirection.NONE
    
    result = tracker.update(100.0, timestamp=11)
    assert result.is_significant == True
    assert result.direction == DeviationDirection.HIGH
    
    print("  ✓ DeviationTracker passed")


def test_persistence_validator():
    from blackice.persistence import PersistenceValidator, PersistenceConfig, PersistenceStatus
    from blackice.deviation import DeviationResult, DeviationDirection
    
    print("Testing PersistenceValidator...")
    
    config = PersistenceConfig(
        min_consecutive_points=5,
        min_fraction_of_window=0.3,
        window_size=10
    )
    validator = PersistenceValidator(config)
    
    deviating = DeviationResult(
        timestamp=0,
        value=100.0,
        zscore=3.0,
        magnitude=3.0,
        direction=DeviationDirection.HIGH,
        consecutive_count=1,
        deviation_start_ts=0,
        is_significant=True
    )
    
    not_deviating = DeviationResult(
        timestamp=0,
        value=55.0,
        zscore=0.5,
        magnitude=0.5,
        direction=DeviationDirection.NONE,
        consecutive_count=0,
        deviation_start_ts=None,
        is_significant=False
    )
    
    for i in range(4):
        result = validator.check(deviating)
    assert result.status == PersistenceStatus.WATCHING
    
    result = validator.check(not_deviating)
    assert result.status == PersistenceStatus.NOT_DEVIATING
    
    validator.reset()
    for i in range(6):
        deviating.consecutive_count = i + 1
        result = validator.check(deviating)
    
    assert result.status == PersistenceStatus.CONFIRMED
    
    print("  ✓ PersistenceValidator passed")


def test_state_machine():
    from blackice.state import RegimeStateMachine, RegimeState
    from blackice.persistence import PersistenceResult, PersistenceStatus
    from blackice.deviation import DeviationDirection
    
    print("Testing RegimeStateMachine...")
    
    sm = RegimeStateMachine(metric_name="test")
    assert sm.current_state == RegimeState.NORMAL
    
    watching = PersistenceResult(
        status=PersistenceStatus.WATCHING,
        direction=DeviationDirection.HIGH,
        consecutive_count=3,
        required_count=10,
        deviation_start_ts=None,
        confirmation_ts=None,
        progress_fraction=0.3
    )
    transition = sm.process(watching, timestamp=100)
    assert sm.current_state == RegimeState.UNSTABLE
    assert transition is not None
    assert transition.to_state == RegimeState.UNSTABLE
    
    confirmed = PersistenceResult(
        status=PersistenceStatus.CONFIRMED,
        direction=DeviationDirection.HIGH,
        consecutive_count=10,
        required_count=10,
        deviation_start_ts=None,
        confirmation_ts=None,
        progress_fraction=1.0
    )
    transition = sm.process(confirmed, timestamp=200)
    assert sm.current_state == RegimeState.SHIFTED
    
    not_deviating = PersistenceResult(
        status=PersistenceStatus.NOT_DEVIATING,
        direction=DeviationDirection.NONE,
        consecutive_count=0,
        required_count=10,
        deviation_start_ts=None,
        confirmation_ts=None,
        progress_fraction=0.0
    )
    transition = sm.process(not_deviating, timestamp=300)
    assert sm.current_state == RegimeState.NORMAL
    
    assert len(sm.transitions) == 3
    
    print("  ✓ RegimeStateMachine passed")


def test_pipeline_config():
    from blackice.pipeline import PipelineConfig
    
    print("Testing PipelineConfig...")
    
    config_path = Path(__file__).parent.parent / 'configs' / 'default.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    pc = PipelineConfig.from_dict(config)
    assert pc.window_size == 60
    assert pc.zscore_threshold == 2.0
    assert pc.min_consecutive_points == 10
    
    print("  ✓ PipelineConfig passed")


def test_pipeline_synthetic():
    from blackice.pipeline import BlackicePipeline, PipelineConfig
    from blackice.state import RegimeState
    import pandas as pd
    
    print("Testing Pipeline with synthetic data...")
    
    config = PipelineConfig(
        window_size=20,
        zscore_threshold=2.0,
        min_consecutive_points=5,
        min_fraction_of_window=0.2,
        track_cpu=True,
        track_memory=True
    )
    
    pipeline = BlackicePipeline(config)
    
    data = []
    
    for i in range(100):
        data.append({
            'machine_id': 'test_machine',
            'timestamp': i,
            'cpu_util': 50 + (i % 5) - 2,
            'mem_util': 40 + (i % 3) - 1
        })
    
    for i in range(100, 200):
        data.append({
            'machine_id': 'test_machine',
            'timestamp': i,
            'cpu_util': 80 + (i % 5) - 2,
            'mem_util': 70 + (i % 3) - 1
        })
    
    for i in range(200, 300):
        data.append({
            'machine_id': 'test_machine',
            'timestamp': i,
            'cpu_util': 50 + (i % 5) - 2,
            'mem_util': 40 + (i % 3) - 1
        })
    
    df = pd.DataFrame(data)
    events = pipeline.process_chunk(df)
    pipeline.stop()
    
    assert len(events) > 0, "Should have detected state transitions"
    
    unstable_count = len([e for e in events if e.transition.to_state == RegimeState.UNSTABLE])
    assert unstable_count > 0, "Should have detected UNSTABLE states"
    
    metrics = pipeline.get_all_metrics()
    assert metrics['systems']['rows_processed'] == 300
    
    print(f"  Events detected: {len(events)}")
    print(f"  UNSTABLE transitions: {unstable_count}")
    print("  ✓ Pipeline synthetic test passed")


def test_metrics_computation():
    from blackice.metrics import MetricsComputer, compute_variance_shift
    from blackice.state import StateTransition, RegimeState
    from blackice.deviation import DeviationDirection
    
    print("Testing MetricsComputer...")
    
    mc = MetricsComputer(track_memory=False)
    mc.start_processing()
    
    mc.record_chunk(1000, 0.5)
    mc.record_chunk(1000, 0.4)
    
    transitions = [
        StateTransition(RegimeState.NORMAL, RegimeState.UNSTABLE, 100, DeviationDirection.HIGH, "test"),
        StateTransition(RegimeState.UNSTABLE, RegimeState.SHIFTED, 110, DeviationDirection.HIGH, "test"),
        StateTransition(RegimeState.SHIFTED, RegimeState.NORMAL, 200, DeviationDirection.NONE, "test"),
    ]
    
    detection = mc.compute_detection_quality(transitions)
    assert detection.confirmed_shifts >= 1
    
    stability = mc.compute_stability(transitions, total_duration=300)
    assert stability.total_regimes >= 1
    
    systems = mc.compute_systems_metrics()
    assert systems.rows_processed == 2000
    
    pre = [50, 51, 49, 50, 52]
    post = [80, 79, 81, 80, 78]
    vs = compute_variance_shift(pre, post)
    assert 'ratio' in vs
    
    print("  ✓ MetricsComputer passed")


def test_integration_real_data():
    from blackice.pipeline import BlackicePipeline, PipelineConfig, stream_machine_data
    from pathlib import Path
    import yaml
    
    print("Testing Integration with real data...")
    
    data_path = Path(__file__).parent.parent.parent / 'machine_usage.csv'
    if not data_path.exists():
        print("  ⊘ Skipped (no machine_usage.csv)")
        return
    
    config_path = Path(__file__).parent.parent / 'configs' / 'default.yaml'
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    pipeline_config = PipelineConfig.from_dict(config)
    pipeline = BlackicePipeline(pipeline_config)
    
    chunk_count = 0
    for chunk in stream_machine_data(str(data_path), 'm_1932', chunksize=100000):
        pipeline.process_chunk(chunk)
        chunk_count += 1
        if chunk_count >= 1:
            break
    
    pipeline.stop()
    
    metrics = pipeline.get_all_metrics()
    assert metrics['systems']['rows_processed'] > 0
    
    print(f"  Processed {metrics['systems']['rows_processed']} rows")
    print("  ✓ Integration test passed")


def main():
    print("=" * 60)
    print("BLACKICE TEST SUITE")
    print("=" * 60)
    print()
    
    tests = [
        test_rolling_buffer,
        test_baseline_computer,
        test_deviation_tracker,
        test_persistence_validator,
        test_state_machine,
        test_pipeline_config,
        test_pipeline_synthetic,
        test_metrics_computation,
        test_integration_real_data,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} FAILED: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
