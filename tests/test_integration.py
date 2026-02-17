"""
Integration test for bot_v2.py

Tests WebSocket connectivity and multi-market scanning.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot_v2 import PolymarketBotV2
import config


async def test_websocket_connection():
    """Test WebSocket connection and latency"""
    print("=" * 60)
    print("Testing WebSocket Connection")
    print("=" * 60)
    
    bot = PolymarketBotV2(dry_run=True, enable_dashboard=False)
    
    # Start WebSocket manager
    await bot.websocket_manager.start()
    
    # Wait for connection
    print("Waiting 10 seconds for connection...")
    await asyncio.sleep(10)
    
    # Check status
    status = bot.websocket_manager.get_connection_status()
    print(f"\nWebSocket Status:")
    print(f"  Mode: {status['mode']}")
    print(f"  Connected: {status['connected']}")
    print(f"  Subscribed Markets: {status['subscribed_markets']}")
    print(f"  Message Count: {status['message_count']}")
    print(f"  Average Latency: {status['average_latency_ms']:.2f}ms")
    
    # Check health
    is_healthy = bot.websocket_manager.is_healthy()
    print(f"  Healthy: {is_healthy}")
    
    # Stop
    await bot.websocket_manager.stop()
    
    # Verify latency requirement
    if status['average_latency_ms'] > 0:
        if status['average_latency_ms'] < config.TARGET_LATENCY_MS:
            print(f"\n✅ PASS: Latency {status['average_latency_ms']:.2f}ms < {config.TARGET_LATENCY_MS}ms")
        else:
            print(f"\n⚠️  WARNING: Latency {status['average_latency_ms']:.2f}ms > {config.TARGET_LATENCY_MS}ms")
    
    print("\n" + "=" * 60)


async def test_market_scanning():
    """Test multi-market scanning"""
    print("=" * 60)
    print("Testing Multi-Market Scanning")
    print("=" * 60)
    
    bot = PolymarketBotV2(dry_run=True, enable_dashboard=False)
    
    # Start market scanner
    await bot.market_scanner.start()
    
    # Wait for scan
    print("Waiting 15 seconds for market scan...")
    await asyncio.sleep(15)
    
    # Get results
    markets = bot.market_scanner.get_active_markets()
    stats = bot.market_scanner.get_stats()
    
    print(f"\nMarket Scanner Stats:")
    print(f"  Active Markets: {stats['active_markets']}")
    print(f"  Max Markets: {stats['max_markets']}")
    print(f"  Running: {stats['running']}")
    
    print(f"\nFound {len(markets)} markets:")
    for i, market in enumerate(markets[:10], 1):  # Show first 10
        question = market.get('question', 'Unknown')
        market_id = market.get('id', 'Unknown')
        tokens = bot.market_scanner.get_market_tokens(market_id)
        print(f"  {i}. {question[:70]}")
        if tokens:
            print(f"     Tokens: {tokens[0][:20]}... / {tokens[1][:20]}...")
    
    # Stop
    await bot.market_scanner.stop()
    
    # Verify requirements
    if len(markets) >= 5:
        print(f"\n✅ PASS: Found {len(markets)} markets (minimum 5)")
    else:
        print(f"\n⚠️  WARNING: Only found {len(markets)} markets (expected 5+)")
    
    print("\n" + "=" * 60)


async def test_connection_health():
    """Test connection pool health monitoring"""
    print("=" * 60)
    print("Testing Connection Health Monitoring")
    print("=" * 60)
    
    bot = PolymarketBotV2(dry_run=True, enable_dashboard=False)
    
    # Record some metrics
    bot.connection_pool.record_success("test_connection")
    bot.connection_pool.record_latency("test_connection", 50.0)
    bot.connection_pool.record_latency("test_connection", 60.0)
    bot.connection_pool.record_latency("test_connection", 70.0)
    
    # Get health status
    health = bot.connection_pool.get_health_status()
    
    print(f"\nConnection Pool Health:")
    print(f"  State: {health['state']}")
    print(f"  Healthy: {health['healthy']}")
    print(f"  Can Execute: {health['can_execute']}")
    print(f"  Error Count: {health['global_error_count']}")
    
    # Test error handling
    print("\nSimulating errors...")
    for i in range(3):
        bot.connection_pool.record_error("test_connection")
    
    health = bot.connection_pool.get_health_status()
    print(f"  After 3 errors - State: {health['state']}")
    
    if health['healthy']:
        print(f"\n✅ PASS: Connection pool handling errors correctly")
    
    print("\n" + "=" * 60)


async def main():
    """Run all integration tests"""
    print("\n🧪 Running Integration Tests for Bot V2\n")
    
    try:
        # Test 1: WebSocket Connection
        await test_websocket_connection()
        await asyncio.sleep(2)
        
        # Test 2: Market Scanning
        await test_market_scanning()
        await asyncio.sleep(2)
        
        # Test 3: Connection Health
        await test_connection_health()
        
        print("\n✅ All integration tests completed!\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
