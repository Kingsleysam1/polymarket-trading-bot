"""
WebSocket Manager for Polymarket Real-Time Data

Manages WebSocket connections to Polymarket for real-time market updates.
Falls back to aggressive REST polling if WebSocket is unavailable.
"""
import asyncio
import json
import time
import logging
from typing import Callable, Optional, Dict, Any
from enum import Enum
import aiohttp

logger = logging.getLogger(__name__)


class ConnectionMode(Enum):
    """Connection mode for market data"""
    WEBSOCKET = "websocket"
    REST_POLLING = "rest_polling"
    DISCONNECTED = "disconnected"


class WebSocketManager:
    """
    Manages WebSocket connections to Polymarket for real-time market data.
    
    Features:
    - Async WebSocket connection handling
    - Auto-reconnection with exponential backoff
    - Fallback to REST polling if WebSocket unavailable
    - Message parsing and event emission
    - Connection health monitoring
    """
    
    def __init__(
        self,
        ws_url: str,
        rest_api_url: str,
        on_message: Callable[[Dict[str, Any]], None],
        reconnect_delay: int = 5,
        max_reconnect_attempts: int = 10,
        ping_interval: int = 30
    ):
        """
        Initialize WebSocket manager.
        
        Args:
            ws_url: WebSocket URL for Polymarket
            rest_api_url: REST API URL for fallback
            on_message: Callback function for incoming messages
            reconnect_delay: Base delay between reconnection attempts (seconds)
            max_reconnect_attempts: Maximum reconnection attempts before fallback
            ping_interval: Interval for ping/pong health checks (seconds)
        """
        self.ws_url = ws_url
        self.rest_api_url = rest_api_url
        self.on_message = on_message
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.ping_interval = ping_interval
        
        # Connection state
        self.mode = ConnectionMode.DISCONNECTED
        self.ws = None
        self.session = None
        self.running = False
        self.reconnect_attempts = 0
        
        # Performance metrics
        self.last_message_time = 0
        self.message_count = 0
        self.latency_samples = []
        
        # Subscriptions
        self.subscribed_markets = set()
        
    async def start(self):
        """Start the WebSocket connection or REST polling fallback"""
        if self.running:
            logger.warning("WebSocket manager already running")
            return
        
        self.running = True
        self.session = aiohttp.ClientSession()
        
        # Try WebSocket first
        logger.info("🌐 Attempting WebSocket connection...")
        ws_success = await self._try_websocket_connection()
        
        if ws_success:
            logger.info("✅ WebSocket connection established")
            self.mode = ConnectionMode.WEBSOCKET
            # Start WebSocket message loop
            asyncio.create_task(self._websocket_loop())
        else:
            logger.warning("⚠️  WebSocket unavailable, falling back to REST polling")
            self.mode = ConnectionMode.REST_POLLING
            # Start REST polling loop
            asyncio.create_task(self._rest_polling_loop())
    
    async def stop(self):
        """Stop the WebSocket connection or polling"""
        logger.info("🛑 Stopping WebSocket manager...")
        self.running = False
        
        if self.ws:
            await self.ws.close()
        
        if self.session:
            await self.session.close()
        
        self.mode = ConnectionMode.DISCONNECTED
        logger.info("✅ WebSocket manager stopped")
    
    async def subscribe_market(self, token_id: str):
        """
        Subscribe to market updates for a specific token.
        
        Args:
            token_id: Token ID to subscribe to
        """
        if token_id in self.subscribed_markets:
            return
        
        self.subscribed_markets.add(token_id)
        
        if self.mode == ConnectionMode.WEBSOCKET and self.ws:
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "channel": "market",
                "market": token_id
            }
            try:
                await self.ws.send_json(subscribe_msg)
                logger.debug(f"📡 Subscribed to market: {token_id}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {token_id}: {e}")
    
    async def unsubscribe_market(self, token_id: str):
        """
        Unsubscribe from market updates.
        
        Args:
            token_id: Token ID to unsubscribe from
        """
        if token_id not in self.subscribed_markets:
            return
        
        self.subscribed_markets.discard(token_id)
        
        if self.mode == ConnectionMode.WEBSOCKET and self.ws:
            unsubscribe_msg = {
                "type": "unsubscribe",
                "channel": "market",
                "market": token_id
            }
            try:
                await self.ws.send_json(unsubscribe_msg)
                logger.debug(f"📡 Unsubscribed from market: {token_id}")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {token_id}: {e}")
    
    async def _try_websocket_connection(self) -> bool:
        """
        Attempt to establish WebSocket connection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ws = await self.session.ws_connect(
                self.ws_url,
                timeout=10,
                heartbeat=self.ping_interval
            )
            return True
        except Exception as e:
            logger.warning(f"WebSocket connection failed: {e}")
            return False
    
    async def _websocket_loop(self):
        """Main WebSocket message receiving loop"""
        while self.running:
            try:
                if not self.ws or self.ws.closed:
                    # Attempt reconnection
                    if self.reconnect_attempts >= self.max_reconnect_attempts:
                        logger.error("Max reconnection attempts reached, falling back to REST")
                        self.mode = ConnectionMode.REST_POLLING
                        asyncio.create_task(self._rest_polling_loop())
                        return
                    
                    self.reconnect_attempts += 1
                    wait_time = min(self.reconnect_delay * (2 ** self.reconnect_attempts), 60)
                    logger.info(f"Reconnecting in {wait_time}s (attempt {self.reconnect_attempts})")
                    await asyncio.sleep(wait_time)
                    
                    if await self._try_websocket_connection():
                        logger.info("✅ Reconnected to WebSocket")
                        self.reconnect_attempts = 0
                        # Re-subscribe to all markets
                        for token_id in list(self.subscribed_markets):
                            await self.subscribe_market(token_id)
                    continue
                
                # Receive message
                msg = await self.ws.receive()
                
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("WebSocket closed by server")
                    break
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    break
                    
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                await asyncio.sleep(1)
    
    async def _rest_polling_loop(self):
        """Fallback REST polling loop (1-second intervals)"""
        logger.info("🔄 Starting REST polling mode (1s intervals)")
        
        while self.running and self.mode == ConnectionMode.REST_POLLING:
            try:
                # Poll each subscribed market
                for token_id in list(self.subscribed_markets):
                    await self._poll_market_rest(token_id)
                
                # Wait 1 second before next poll
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in REST polling loop: {e}")
                await asyncio.sleep(1)
    
    async def _poll_market_rest(self, token_id: str):
        """
        Poll a single market via REST API.
        
        Args:
            token_id: Token ID to poll
        """
        try:
            # Fetch order book from CLOB API
            url = f"{self.rest_api_url}/book"
            params = {"token_id": token_id}
            
            async with self.session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convert to WebSocket-like message format
                    message = {
                        "type": "market_update",
                        "token_id": token_id,
                        "data": data,
                        "timestamp": time.time()
                    }
                    
                    await self._handle_message(json.dumps(message))
                    
        except Exception as e:
            logger.debug(f"Error polling market {token_id}: {e}")
    
    async def _handle_message(self, message_data: str):
        """
        Parse and handle incoming message.
        
        Args:
            message_data: Raw message data (JSON string)
        """
        try:
            # Record timing
            receive_time = time.time()
            
            # Parse JSON
            message = json.loads(message_data)
            
            # Calculate latency if timestamp available
            if "timestamp" in message:
                latency_ms = (receive_time - message["timestamp"]) * 1000
                self.latency_samples.append(latency_ms)
                # Keep only last 100 samples
                if len(self.latency_samples) > 100:
                    self.latency_samples.pop(0)
            
            # Update metrics
            self.last_message_time = receive_time
            self.message_count += 1
            
            # Call user callback
            if self.on_message:
                await self.on_message(message)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def get_average_latency(self) -> float:
        """
        Get average latency in milliseconds.
        
        Returns:
            Average latency in ms, or 0 if no samples
        """
        if not self.latency_samples:
            return 0.0
        return sum(self.latency_samples) / len(self.latency_samples)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and metrics.
        
        Returns:
            Status dictionary with connection info and metrics
        """
        return {
            "mode": self.mode.value,
            "connected": self.running and self.mode != ConnectionMode.DISCONNECTED,
            "subscribed_markets": len(self.subscribed_markets),
            "message_count": self.message_count,
            "average_latency_ms": self.get_average_latency(),
            "last_message_age_seconds": time.time() - self.last_message_time if self.last_message_time > 0 else None
        }
    
    def is_healthy(self) -> bool:
        """
        Check if connection is healthy.
        
        Returns:
            True if connection is healthy and receiving messages
        """
        if not self.running or self.mode == ConnectionMode.DISCONNECTED:
            return False
        
        # Consider unhealthy if no messages in last 60 seconds
        if self.last_message_time > 0:
            age = time.time() - self.last_message_time
            return age < 60
        
        return True
