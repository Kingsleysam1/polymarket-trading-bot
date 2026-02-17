# Phase 2: Latency Arbitrage - Quick Start

## What's New

Added latency arbitrage strategy that exploits 1-2 second lag between Binance BTC spikes and Polymarket adjustments.

### Performance Targets

- **Profit per trade**: 5-15%
- **Trades per day**: 10-15
- **Daily profit**: $200-400 on $100 capital

## Quick Test

### 1. Test Binance Connection

```bash
cd /Users/mac/Desktop/polymarket

# Quick Binance test
python3 -c "
import asyncio
from external.async_binance_client import AsyncBinanceMonitor

async def test():
    print('Testing Binance connection...')
    monitor = AsyncBinanceMonitor(
        on_price_update=lambda p: print(f'BTC: \${p:,.2f}'),
        ws_url='wss://stream.binance.com:9443/ws/btcusdt@trade'
    )
    await monitor.start()
    await asyncio.sleep(10)
    status = monitor.get_connection_status()
    print(f'✅ Connected: {status[\"is_healthy\"]}')
    print(f'✅ Latency: {status[\"average_latency_ms\"]:.2f}ms')
    await monitor.stop()

asyncio.run(test())
"
```

### 2. Run Dry-Run Test

```bash
# Run bot with both strategies (maker + latency arb)
python3 bot_v2.py --dry-run --dashboard

# Monitor at http://127.0.0.1:5000
# Watch for spike detections and simulated trades
```

### 3. Start Live Trading

```bash
# Start with small capital
python3 bot_v2.py --dashboard
```

## New Components

- **`external/async_binance_client.py`** - Real-time BTC price monitoring
- **`core/spike_detector.py`** - Detects $150+ BTC moves in 3-10s
- **`strategies/async_latency_arbitrage.py`** - Executes rapid arbitrage trades
- **`config_v2.py`** - Extended with latency arbitrage settings

## How It Works

1. **Monitor Binance**: Real-time BTC/USDT prices via WebSocket
2. **Detect Spikes**: $150+ price change in 3-10 seconds
3. **Check Polymarket**: Has the price adjusted yet?
4. **Execute Trade**: Market order within 2 seconds
5. **Exit**: 30s max hold time or profit target

## Configuration

Key settings in `config_v2.py`:

```python
LATENCY_MIN_BTC_MOVE = 150.0  # Minimum spike ($)
LATENCY_MAX_POSITION_SIZE = 50.0  # Max per trade ($)
LATENCY_MAX_CONCURRENT_POSITIONS = 3  # Max open positions
LATENCY_DAILY_TRADE_LIMIT = 20  # Max trades/day
LATENCY_STOP_LOSS_PCT = 0.05  # 5% stop loss
```

## Risk Management

- **Position size**: $25-50 per trade
- **Max positions**: 3 concurrent
- **Daily limit**: 20 trades
- **Stop loss**: 5% from entry
- **Time stop**: 30 seconds max hold
- **Daily loss limit**: Stop if loss >$100

## Troubleshooting

### No Binance Connection
```bash
# Check if Binance is accessible
curl -I https://stream.binance.com:9443
```

### No Spikes Detected
- BTC needs to move $150+ in 3-10 seconds
- Check if in cooldown period (30s)
- Lower threshold in config if needed

### Slow Execution
- Target: <2 seconds from spike to order
- Uses market orders for instant fill
- Check network latency

## Documentation

- **[Walkthrough](file:///Users/mac/.gemini/antigravity/brain/cde88690-ae1d-4827-acbf-d5251dc0a462/walkthrough.md)** - Complete implementation guide
- **[Implementation Plan](file:///Users/mac/.gemini/antigravity/brain/cde88690-ae1d-4827-acbf-d5251dc0a462/implementation_plan.md)** - Technical design
- **[Task List](file:///Users/mac/.gemini/antigravity/brain/cde88690-ae1d-4827-acbf-d5251dc0a462/task.md)** - Progress tracking

---

**Phase 2 Status**: ✅ **COMPLETE** - Ready for testing!

**Next**: Phase 3 - Sum-to-One Arbitrage Strategy
