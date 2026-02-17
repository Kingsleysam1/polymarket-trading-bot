"""
Unit Tests for Spike Detector

Tests BTC price spike detection logic.
"""
import pytest
import time
from core.spike_detector import SpikeDetector


def test_spike_detector_initialization():
    """Test spike detector initialization"""
    detector = SpikeDetector(
        min_move=150.0,
        time_window_min=3,
        time_window_max=10,
        cooldown_seconds=30
    )
    
    assert detector.min_move == 150.0
    assert detector.cooldown_seconds == 30
    assert len(detector.price_history) == 0
    assert detector.spike_count == 0


def test_add_price():
    """Test adding price updates"""
    detector = SpikeDetector()
    
    detector.add_price(50000.0)
    detector.add_price(50100.0)
    detector.add_price(50200.0)
    
    assert len(detector.price_history) == 3
    assert detector.price_history[-1]['price'] == 50200.0


def test_detect_spike_up():
    """Test detecting upward spike"""
    detector = SpikeDetector(min_move=150.0, cooldown_seconds=0)
    
    # Add prices with significant upward movement
    base_time = time.time()
    detector.add_price(50000.0, base_time)
    detector.add_price(50050.0, base_time + 1)
    detector.add_price(50100.0, base_time + 2)
    detector.add_price(50200.0, base_time + 5)  # +$200 in 5 seconds
    
    spike = detector.detect_spike()
    
    assert spike is not None
    assert spike['direction'] == 'up'
    assert spike['price_change'] >= 150.0
    assert spike['old_price'] == 50000.0
    assert spike['new_price'] == 50200.0


def test_detect_spike_down():
    """Test detecting downward spike"""
    detector = SpikeDetector(min_move=150.0, cooldown_seconds=0)
    
    # Add prices with significant downward movement
    base_time = time.time()
    detector.add_price(50000.0, base_time)
    detector.add_price(49950.0, base_time + 1)
    detector.add_price(49900.0, base_time + 2)
    detector.add_price(49800.0, base_time + 5)  # -$200 in 5 seconds
    
    spike = detector.detect_spike()
    
    assert spike is not None
    assert spike['direction'] == 'down'
    assert spike['price_change'] <= -150.0


def test_no_spike_small_movement():
    """Test that small movements don't trigger spike"""
    detector = SpikeDetector(min_move=150.0, cooldown_seconds=0)
    
    # Add prices with small movement
    base_time = time.time()
    detector.add_price(50000.0, base_time)
    detector.add_price(50050.0, base_time + 5)  # Only $50 in 5 seconds
    
    spike = detector.detect_spike()
    
    assert spike is None


def test_cooldown():
    """Test cooldown between detections"""
    detector = SpikeDetector(min_move=150.0, cooldown_seconds=30)
    
    # First spike
    base_time = time.time()
    detector.add_price(50000.0, base_time)
    detector.add_price(50200.0, base_time + 5)
    
    spike1 = detector.detect_spike()
    assert spike1 is not None
    
    # Second spike immediately after (should be blocked by cooldown)
    detector.add_price(50400.0, base_time + 10)
    spike2 = detector.detect_spike()
    assert spike2 is None  # Blocked by cooldown


def test_get_stats():
    """Test statistics reporting"""
    detector = SpikeDetector(min_move=150.0, cooldown_seconds=30)
    
    stats = detector.get_stats()
    
    assert 'total_spikes' in stats
    assert 'last_spike_time' in stats
    assert 'in_cooldown' in stats
    assert 'price_history_size' in stats
    assert stats['total_spikes'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
