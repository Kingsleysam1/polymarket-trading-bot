"""
Binance WebSocket Client - Real-time BTC price monitoring

Connects to Binance WebSocket stream for live BTC/USDT price updates.
Used for latency arbitrage strategy.
"""
import json
import threading
import time
from typing import Callable, Optional
import websocket
import logging

logger = logging.getLogger(__name__)


class BinanceMonitor:
    """
    Monitors Binance BTC/USDT price via WebSocket.
    Calls callback function when price updates.
    """
    
    def __init__(self, on_price_update: Callable[[float], None], ws_url: str):
        self.on_price_update = on_price_update
        self.ws_url = ws_url
        self.ws = None
        self.thread = None
        self.running = False
        self.last_price = None
        self.last_update_time = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
    def start(self):
        """Start the WebSocket connection in a background thread"""
        if self.running:
            logger.warning("Binance monitor already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.thread.start()
        logger.info("🌐 Binance WebSocket monitor started")
    
    def stop(self):
        """Stop the WebSocket connection"""
        self.running = False
        if self.ws:
            self.ws.close()
        logger.info("🛑 Binance WebSocket monitor stopped")
    
    def _run_websocket(self):
        """Run WebSocket connection with auto-reconnect"""
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Connecting to Binance WebSocket: {self.ws_url}")
                
                self.ws = websocket.WebSocketApp(
                    self.ws_url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                
                self.ws.run_forever()
                
                # If we get here, connection closed
                if self.running:
                    self.reconnect_attempts += 1
                    wait_time = min(5 * self.reconnect_attempts, 30)
                    logger.info(f"Reconnecting in {wait_time}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if self.running:
                    time.sleep(5)
    
    def _on_open(self, ws):
        """Called when WebSocket connection is established"""
        logger.info("✅ Connected to Binance WebSocket")
        self.reconnect_attempts = 0
    
    def _on_message(self, ws, message):
        """
        Handle incoming price updates from Binance.
        
        Message format from Binance:
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
            data = json.loads(message)
            
            # Extract BTC price
            if 'p' in data:
                price = float(data['p'])
                self.last_price = price
                self.last_update_time = time.time()
                
                # Call the callback function
                self.on_price_update(price)
                
        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"Binance WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.warning(f"Binance WebSocket closed: {close_status_code} - {close_msg}")
    
    def get_last_price(self) -> Optional[float]:
        """Get the most recent BTC price"""
        return self.last_price
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected and receiving updates"""
        # Consider connected if we've received an update in the last 10 seconds
        if self.last_update_time == 0:
            return False
        return (time.time() - self.last_update_time) < 10
