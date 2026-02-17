"""
Integration Test for Latency Arbitrage Strategy

Tests Binance connection, spike detection, and strategy execution.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from external.async_binance_client import AsyncBinanceMonitor
from core.spike_detector import SpikeDetector
import config_v2 as config


async def test_binance_connection():
    """Test Binance WebSocket connection"""
    print("=" * 60)
    print("Testing Binance WebSocket Connection")
    print("=" * 60)
    
    price_updates = []
    
    def on_price_update(price: float):
        price_updates.append(price)
        print(f"  BTC Price: ${price:,.2f}")
    
    monitor = AsyncBinanceMonitor(
        on_price_update=on_price_update,
        ws_url=config.BINANCE_WS_URL
    )
    
    # Start monitor
    await monitor.start()
    
    # Wait for updates
    print("\nWaiting 15 seconds for price updates...")
    await asyncio.sleep(15)
    
    # Check status
    status = monitor.get_connection_status()
    print(f"\nBinance Status:")
    print(f"  Connected: {status['connected']}")
    print(f"  Healthy: {status['is_healthy']}")
    print(f"  Last Price: ${status['last_price']:,.2f}" if status['last_price'] else "  Last Price: None")
    print(f"  Average Latency: {status['average_latency_ms']:.2f}ms")
    print(f"  Price Updates: {len(price_updates)}")
    print(f"  Price History: {status['price_history_size']}")
    
    # Stop monitor
    await monitor.stop()
    
    # Verify
    if status['is_healthy'] and len(price_updates) > 0:
        print(f"\n✅ PASS: Binance connection working ({len(price_updates)} updates)")
    else:
        print(f"\n⚠️  WARNING: Binance connection issues")
    
    print("\n" + "=" * 60)


async def test_spike_detection():
    """Test spike detection with live Binance data"""
    print("=" * 60)
    print("Testing Spike Detection")
    print("=" * 60)
    
    spike_detector = SpikeDetector(
        min_move=config.LATENCY_MIN_BTC_MOVE,
        time_window_min=config.LATENCY_SPIKE_TIME_WINDOW_MIN,
        time_window_max=config.LATENCY_SPIKE_TIME_WINDOW_MAX,
        cooldown_seconds=5  # Short cooldown for testing
    )
    
    def on_price_update(price: float):
        spike_detector.add_price(price)
        spike = spike_detector.detect_spike()
        
        if spike:
            print(f"\n🚨 SPIKE DETECTED!")
            print(f"   Direction: {spike['direction'].upper()}")
            print(f"   Change: ${spike['price_change']:+.2f}")
            print(f"   From ${spike['old_price']:.2f} to ${spike['new_price']:.2f}")
            print(f"   Time window: {spike['time_window']:.1f}s")
    
    monitor = AsyncBinanceMonitor(
        on_price_update=on_price_update,
        ws_url=config.BINANCE_WS_URL
    )
    
    # Start monitor
    await monitor.start()
    
    # Monitor for 60 seconds
    print(f"\nMonitoring for spikes (≥${config.LATENCY_MIN_BTC_MOVE} in {config.LATENCY_SPIKE_TIME_WINDOW_MIN}-{config.LATENCY_SPIKE_TIME_WINDOW_MAX}s)...")
    print("Waiting 60 seconds...\n")
    
    await asyncio.sleep(60)
    
    # Get stats
    stats = spike_detector.get_stats()
    print(f"\nSpike Detection Stats:")
    print(f"  Total Spikes: {stats['total_spikes']}")
    print(f"  Price History Size: {stats['price_history_size']}")
    
    # Stop monitor
    await monitor.stop()
    
    print("\n" + "=" * 60)


async def test_latency_arbitrage_dry_run():
    """Test latency arbitrage strategy in dry-run mode"""
    print("=" * 60)
    print("Testing Latency Arbitrage Strategy (Dry-Run)")
    print("=" * 60)
    
    try:
        from strategies.async_latency_arbitrage import AsyncLatencyArbitrageStrategy
        from py_clob_client.client import ClobClient
        import config
        
        # Initialize client
        client = ClobClient(
            host=config.CLOB_API_URL,
            key=config.POLYGON_PRIVATE_KEY,
            chain_id=config.POLYGON_CHAIN_ID,
            signature_type=config.SIGNATURE_TYPE
        )
        
        # Initialize strategy
        strategy = AsyncLatencyArbitrageStrategy(client)
        
        # Start Binance monitor
        await strategy.start()
        
        print("\nMonitoring for latency arbitrage opportunities...")
        print("Waiting 60 seconds...\n")
        
        # Monitor for opportunities
        for i in range(12):  # 12 x 5 seconds = 60 seconds
            opportunity = await strategy.scan_opportunities()
            
            if opportunity:
                print(f"\n🎯 OPPORTUNITY FOUND!")
                print(f"   Side: {opportunity['side']}")
                print(f"   Entry Price: {opportunity['entry_price']:.4f}")
                print(f"   Expected Exit: {opportunity['expected_exit']:.4f}")
                
                # Execute in dry-run
                position_id = await strategy.execute_trade(opportunity, dry_run=True)
                print(f"   Position ID: {position_id}")
            
            await asyncio.sleep(5)
        
        # Get stats
        stats = strategy.get_stats()
        print(f"\nStrategy Stats:")
        print(f"  Binance Connected: {stats['binance_connected']}")
        print(f"  Binance Latency: {stats['binance_latency_ms']:.2f}ms")
        print(f"  Spikes Detected: {stats['total_spikes_detected']}")
        print(f"  Daily Trades: {stats['daily_trades']}")
        print(f"  Open Positions: {len(strategy.open_positions)}")
        
        # Stop strategy
        await strategy.stop()
        
        print("\n✅ Latency arbitrage strategy test complete")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


async def main():
    """Run all latency arbitrage tests"""
    print("\n🧪 Running Latency Arbitrage Integration Tests\n")
    
    try:
        # Test 1: Binance Connection
        await test_binance_connection()
        await asyncio.sleep(2)
        
        # Test 2: Spike Detection
        await test_spike_detection()
        await asyncio.sleep(2)
        
        # Test 3: Strategy Dry-Run
        await test_latency_arbitrage_dry_run()
        
        print("\n✅ All latency arbitrage tests completed!\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
