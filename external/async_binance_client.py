"""
Async Binance WebSocket Client

Real-time BTC/USDT price monitoring using async WebSocket.
Integrates with bot_v2.py's async architecture.
"""
import asyncio
import json
import time
import logging
from typing import Callable, Optional, List, Dict
from collections import deque
import websockets

logger = logging.getLogger(__name__)


class AsyncBinanceMonitor:
    """
    Async WebSocket monitor for Binance BTC/USDT price.
    
    Features:
    - Real-time price updates
    - Auto-reconnection with exponential backoff
    - Price history buffer (last 100 updates)
    - Latency tracking
    - Spike detection callback
    """
    
    def __init__(
        self,
        on_price_update: Callable[[float], None],
        ws_url: str = "wss://stream.binance.com:9443/ws/btcusdt@trade",
        history_size: int = 100
    ):
        """
        Initialize async Binance monitor.
        
        Args:
            on_price_update: Callback function for price updates
            ws_url: Binance WebSocket URL
            history_size: Number of price updates to keep in history
        """
        self.on_price_update = on_price_update
        self.ws_url = ws_url
        self.history_size = history_size
        
        # Connection state
        self.ws = None
        self.running = False
        self.connected = False
        
        # Price tracking
        self.last_price = None
        self.last_update_time = 0
        self.price_history: deque = deque(maxlen=history_size)
        
        # Reconnection
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5
        
        # Latency tracking
        self.latency_samples: List[float] = []
        self.max_latency_samples = 50
    
    async def start(self):
        """Start the WebSocket connection"""
        if self.running:
            logger.warning("Binance monitor already running")
            return
        
        self.running = True
        logger.info("🚀 Starting async Binance WebSocket monitor...")
        
        # Start connection loop
        asyncio.create_task(self._connection_loop())
    
    async def stop(self):
        """Stop the WebSocket connection"""
        logger.info("🛑 Stopping Binance monitor...")
        self.running = False
        self.connected = False
        
        if self.ws:
            await self.ws.close()
    
    async def _connection_loop(self):
        """Main connection loop with auto-reconnect"""
        while self.running:
            try:
                await self._connect_and_listen()
            except Exception as e:
                logger.error(f"Binance WebSocket error: {e}")
                
                if self.running:
                    self.reconnect_attempts += 1
                    
                    if self.reconnect_attempts >= self.max_reconnect_attempts:
                        logger.error("Max reconnection attempts reached, stopping")
                        self.running = False
                        break
                    
                    # Exponential backoff
                    wait_time = min(self.reconnect_delay * (2 ** self.reconnect_attempts), 60)
                    logger.info(f"Reconnecting in {wait_time}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
                    await asyncio.sleep(wait_time)
    
    async def _connect_and_listen(self):
        """Connect to WebSocket and listen for messages"""
        logger.info(f"Connecting to Binance: {self.ws_url}")
        
        async with websockets.connect(self.ws_url) as websocket:
            self.ws = websocket
            self.connected = True
            self.reconnect_attempts = 0
            
            logger.info("✅ Connected to Binance WebSocket")
            
            # Listen for messages
            async for message in websocket:
                if not self.running:
                    break
                
                await self._handle_message(message)
    
    async def _handle_message(self, message: str):
        """
        Handle incoming WebSocket message.
        
        Binance trade message format:
        {
            "e": "trade",
            "E": 123456789,
            "s": "BTCUSDT",
            "t": 12345,
            "p": "50000.00",
            "q": "0.001",
            "T": 123456785,
            ...
        }
        """
        try:
            receive_time = time.time()
            data = json.loads(message)
            
            # Extract price
            if 'p' in data:
                price = float(data['p'])
                event_time = data.get('E', 0) / 1000  # Convert ms to seconds
                
                # Calculate latency
                if event_time > 0:
                    latency_ms = (receive_time - event_time) * 1000
                    self._record_latency(latency_ms)
                
                # Update state
                self.last_price = price
                self.last_update_time = receive_time
                
                # Add to history
                self.price_history.append({
                    'price': price,
                    'timestamp': receive_time,
                    'event_time': event_time
                })
                
                # Call callback
                if self.on_price_update:
                    self.on_price_update(price)
                
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
    
    def _record_latency(self, latency_ms: float):
        """Record latency sample"""
        self.latency_samples.append(latency_ms)
        
        # Keep only recent samples
        if len(self.latency_samples) > self.max_latency_samples:
            self.latency_samples.pop(0)
    
    def get_last_price(self) -> Optional[float]:
        """Get the most recent BTC price"""
        return self.last_price
    
    def get_price_history(self, seconds: int = 10) -> List[Dict]:
        """
        Get price history for the last N seconds.
        
        Args:
            seconds: Number of seconds of history to return
            
        Returns:
            List of price entries
        """
        if not self.price_history:
            return []
        
        cutoff_time = time.time() - seconds
        return [
            entry for entry in self.price_history
            if entry['timestamp'] >= cutoff_time
        ]
    
    def get_average_latency(self) -> float:
        """Get average latency in milliseconds"""
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and receiving updates"""
        if not self.connected:
            return False
        
        # Consider connected if we've received an update in the last 10 seconds
        if self.last_update_time == 0:
            return False
        
        return (time.time() - self.last_update_time) < 10
    
    def get_connection_status(self) -> Dict:
        """Get detailed connection status"""
        return {
            'connected': self.connected,
            'is_healthy': self.is_connected(),
            'last_price': self.last_price,
            'last_update_time': self.last_update_time,
            'seconds_since_update': time.time() - self.last_update_time if self.last_update_time > 0 else 0,
            'average_latency_ms': self.get_average_latency(),
            'price_history_size': len(self.price_history),
            'reconnect_attempts': self.reconnect_attempts
        }
