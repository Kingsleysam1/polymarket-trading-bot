"""
Unit Tests for WebSocket Manager

Tests WebSocket connection, reconnection, and fallback to REST polling.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from core.websocket_manager import WebSocketManager, ConnectionMode


@pytest.mark.asyncio
async def test_websocket_initialization():
    """Test WebSocket manager initialization"""
    on_message = AsyncMock()
    
    ws_manager = WebSocketManager(
        ws_url="wss://test.example.com",
        rest_api_url="https://api.example.com",
        on_message=on_message
    )
    
    assert ws_manager.mode == ConnectionMode.DISCONNECTED
    assert ws_manager.running == False
    assert len(ws_manager.subscribed_markets) == 0


@pytest.mark.asyncio
async def test_subscribe_market():
    """Test market subscription"""
    on_message = AsyncMock()
    
    ws_manager = WebSocketManager(
        ws_url="wss://test.example.com",
        rest_api_url="https://api.example.com",
        on_message=on_message
    )
    
    # Subscribe to a market
    await ws_manager.subscribe_market("token_123")
    
    assert "token_123" in ws_manager.subscribed_markets


@pytest.mark.asyncio
async def test_connection_status():
    """Test connection status reporting"""
    on_message = AsyncMock()
    
    ws_manager = WebSocketManager(
        ws_url="wss://test.example.com",
        rest_api_url="https://api.example.com",
        on_message=on_message
    )
    
    status = ws_manager.get_connection_status()
    
    assert "mode" in status
    assert "connected" in status
    assert "subscribed_markets" in status
    assert status["connected"] == False


@pytest.mark.asyncio
async def test_latency_tracking():
    """Test latency measurement"""
    on_message = AsyncMock()
    
    ws_manager = WebSocketManager(
        ws_url="wss://test.example.com",
        rest_api_url="https://api.example.com",
        on_message=on_message
    )
    
    # Add some latency samples
    ws_manager.latency_samples = [50.0, 60.0, 70.0]
    
    avg_latency = ws_manager.get_average_latency()
    assert avg_latency == 60.0


@pytest.mark.asyncio
async def test_health_check():
    """Test connection health check"""
    on_message = AsyncMock()
    
    ws_manager = WebSocketManager(
        ws_url="wss://test.example.com",
        rest_api_url="https://api.example.com",
        on_message=on_message
    )
    
    # Initially unhealthy (not running)
    assert ws_manager.is_healthy() == False
    
    # Simulate running with recent message
    ws_manager.running = True
    ws_manager.mode = ConnectionMode.WEBSOCKET
    ws_manager.last_message_time = asyncio.get_event_loop().time()
    
    assert ws_manager.is_healthy() == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
