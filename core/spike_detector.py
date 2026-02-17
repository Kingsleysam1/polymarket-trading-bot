"""
BTC Price Spike Detector

Detects significant BTC price movements in real-time for latency arbitrage.
"""
import time
import logging
from typing import Optional, Dict, List
from collections import deque

logger = logging.getLogger(__name__)


class SpikeDetector:
    """
    Detects significant BTC price spikes for latency arbitrage.
    
    Spike criteria:
    - Minimum price change: $150 (configurable)
    - Time window: 3-10 seconds
    - Cooldown: 30 seconds between detections
    """
    
    def __init__(
        self,
        min_move: float = 150.0,
        time_window_min: int = 3,
        time_window_max: int = 10,
        cooldown_seconds: int = 30,
        history_size: int = 100
    ):
        """
        Initialize spike detector.
        
        Args:
            min_move: Minimum price change to detect ($)
            time_window_min: Minimum seconds for comparison
            time_window_max: Maximum seconds for comparison
            cooldown_seconds: Seconds to wait between detections
            history_size: Number of price updates to keep
        """
        self.min_move = min_move
        self.time_window_min = time_window_min
        self.time_window_max = time_window_max
        self.cooldown_seconds = cooldown_seconds
        
        # Price history
        self.price_history: deque = deque(maxlen=history_size)
        
        # Spike tracking
        self.last_spike_time = 0
        self.spike_count = 0
    
    def add_price(self, price: float, timestamp: Optional[float] = None):
        """
        Add a price update to history.
        
        Args:
            price: BTC price
            timestamp: Unix timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = time.time()
        
        self.price_history.append({
            'price': price,
            'timestamp': timestamp
        })
    
    def detect_spike(self) -> Optional[Dict]:
        """
        Detect if a significant price spike has occurred.
        
        Returns:
            Spike info dict if detected, None otherwise
        """
        # Check cooldown
        if time.time() - self.last_spike_time < self.cooldown_seconds:
            return None
        
        # Need enough history
        if len(self.price_history) < 2:
            return None
        
        current = self.price_history[-1]
        
        # Find price from time_window_min to time_window_max seconds ago
        past_entry = None
        
        for entry in reversed(list(self.price_history)[:-1]):
            time_diff = current['timestamp'] - entry['timestamp']
            
            if self.time_window_min <= time_diff <= self.time_window_max:
                past_entry = entry
                break
        
        if not past_entry:
            return None
        
        # Calculate price change
        price_change = current['price'] - past_entry['price']
        price_change_pct = (price_change / past_entry['price']) * 100
        
        # Check if spike threshold met
        if abs(price_change) >= self.min_move:
            direction = "up" if price_change > 0 else "down"
            time_diff = current['timestamp'] - past_entry['timestamp']
            
            # Record spike
            self.last_spike_time = time.time()
            self.spike_count += 1
            
            spike_info = {
                'direction': direction,
                'price_change': price_change,
                'price_change_pct': price_change_pct,
                'old_price': past_entry['price'],
                'new_price': current['price'],
                'time_window': time_diff,
                'detection_time': current['timestamp'],
                'spike_id': f"spike_{int(current['timestamp'])}"
            }
            
            logger.info(f"🚨 SPIKE DETECTED #{self.spike_count}")
            logger.info(f"   Direction: {direction.upper()}")
            logger.info(f"   Change: ${price_change:+.2f} ({price_change_pct:+.2f}%)")
            logger.info(f"   From ${past_entry['price']:.2f} to ${current['price']:.2f}")
            logger.info(f"   Time window: {time_diff:.1f}s")
            
            return spike_info
        
        return None
    
    def get_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            'total_spikes': self.spike_count,
            'last_spike_time': self.last_spike_time,
            'seconds_since_last_spike': time.time() - self.last_spike_time if self.last_spike_time > 0 else 0,
            'in_cooldown': time.time() - self.last_spike_time < self.cooldown_seconds,
            'price_history_size': len(self.price_history),
            'min_move': self.min_move,
            'cooldown_seconds': self.cooldown_seconds
        }
    
    def reset_cooldown(self):
        """Reset cooldown (for testing)"""
        self.last_spike_time = 0
