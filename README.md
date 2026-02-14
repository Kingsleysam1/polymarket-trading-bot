# Polymarket 5-Minute Bitcoin Trading Bot - Phase 1

A maker market making bot for Polymarket's 5-minute Bitcoin price prediction markets. The bot monitors markets, detects profitable spread opportunities, and places limit orders inside the spread to capture profit as a maker.

## ⚠️ Disclaimer

**This bot trades with real money.** While maker market making is relatively low-risk, you can still lose money. Always start with small position sizes and thoroughly test in dry-run mode first.

## 🎯 Strategy Overview

**Maker Market Making:**
1. Monitor current 5-minute Bitcoin prediction market
2. Detect when bid-ask spread is wide enough to profit from
3. Place limit orders INSIDE the spread (becoming a maker, 0% fees)
4. When orders fill, capture the spread as profit
5. Repeat continuously

**Target Metrics (conservative estimates):**
- 20-30 successful round-trips per day
- $2-4 average profit per cycle
- $60-100 daily target
- 85%+ win rate

## 📋 Requirements

- Python 3.9 or higher
- Polygon wallet with private key
- USDC on Polygon network ($100+ recommended)
- Basic understanding of Polymarket and prediction markets

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download this repository
cd polymarket

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```
POLYGON_PRIVATE_KEY=your_private_key_here
SIGNATURE_TYPE=0
FUNDER_ADDRESS=
```

**Important:**
- Use a wallet with USDC on Polygon network
- Never share or commit your `.env` file
- `SIGNATURE_TYPE`: Use `0` for standard wallets, `1` for Magic wallet

### 3. Approve Token Allowances (One-Time Setup)

Before trading, you must approve Polymarket's contracts to use your USDC:

```bash
python bot.py --approve-tokens
```

This is a one-time setup step. You'll need to confirm the transaction in your wallet.

### 4. Test in Dry-Run Mode

**Always test first!** Run in simulation mode to validate the bot:

```bash
python bot.py --dry-run
```

Let it run for 10-15 minutes and observe:
- ✅ Bot finds active 5-minute Bitcoin markets
- ✅ Bot detects spread opportunities
- ✅ Bot logs "WOULD PLACE ORDER" messages with reasonable prices
- ✅ Bot switches markets when one closes
- ✅ No errors or crashes

### 4.5. Monitor with Web Dashboard (Optional)

Want a beautiful web interface to monitor your bot? Start it with the dashboard enabled:

```bash
# Dry-run with dashboard
python bot.py --dry-run --dashboard

# Or use the quick start script
python start_with_dashboard.py
```

Then open your browser to **http://127.0.0.1:5000**

The dashboard shows:
- 📊 Real-time performance metrics (P&L, win rate, trades)
- 📈 Current market and spread data
- 🎯 Open positions
- 📝 Recent trade history
- ⚠️ Error log

**Auto-refreshes every 3 seconds!**

### 5. Start Live Trading (Small Size)

**Start with very small orders:**

1. Edit `config.py` and set:
   ```python
   ORDER_SIZE_USD = 1.0  # Start with $1 orders
   ```

2. Run the bot:
   ```bash
   python bot.py
   ```

3. Monitor for 1-2 hours with small sizes

4. Gradually increase `ORDER_SIZE_USD` only if profitable

## ⚙️ Configuration

Edit `config.py` to adjust bot behavior:

### Trading Parameters

```python
MIN_SPREAD_TO_TRADE = 0.05        # Minimum 5-cent spread to trade
ORDER_SIZE_USD = 2.0               # Order size in USDC
MAX_OPEN_POSITIONS = 3             # Maximum concurrent positions
POSITION_TIMEOUT_SECONDS = 180     # Cancel unfilled orders after 3 minutes
PRICE_IMPROVEMENT_OFFSET = 0.01    # Place orders 1 cent inside spread
MIN_TIME_REMAINING_TO_TRADE = 120  # Don't trade if <2min left in market
```

### Risk Management

```python
DAILY_LOSS_LIMIT = 50.0      # Stop if losses exceed $50
DAILY_PROFIT_TARGET = 150.0  # Stop if profit reaches $150
```

### Operational Settings

```python
LOOP_SLEEP_INTERVAL = 5      # Seconds between cycles
HEARTBEAT_INTERVAL = 60      # Log status every 60 seconds
LOG_LEVEL = "INFO"           # DEBUG, INFO, WARNING, ERROR
```

## 📊 Monitoring

### Console Output

The bot logs all activity to console and `polymarket_bot.log`:

```
2026-02-14 21:00:00 - INFO - 🔍 Searching for active 5-minute Bitcoin market...
2026-02-14 21:00:01 - INFO - 📊 Found market: Will BTC be higher in 5 min?
2026-02-14 21:00:02 - INFO - 📊 OPPORTUNITY DETECTED!
2026-02-14 21:00:02 - INFO -    Spread: $0.06
2026-02-14 21:00:02 - INFO -    Profit Potential: $0.12
2026-02-14 21:00:03 - INFO - 💵 PLACING MARKET MAKING ORDERS:
2026-02-14 21:00:03 - INFO -    YES: BUY 4.00 shares @ $0.50
2026-02-14 21:00:03 - INFO -    NO:  BUY 4.35 shares @ $0.46
2026-02-14 21:00:04 - INFO - ✅ Orders placed successfully
```

### Performance Summary

Press `Ctrl+C` to stop the bot gracefully. It will display performance stats:

```
╔══════════════════════════════════════════════════════════╗
║              PERFORMANCE SUMMARY                         ║
╠══════════════════════════════════════════════════════════╣
║ Runtime:          2:34:15                                ║
║ Total Trades:     28                                     ║
║ Winning Trades:   24                                     ║
║ Losing Trades:    4                                      ║
║ Win Rate:         85.71%                                 ║
║                                                          ║
║ Total Profit:     $78.40                                 ║
║ Total Loss:       $6.20                                  ║
║ Net P&L:          $72.20                                 ║
║                                                          ║
║ Avg Win:          $3.27                                  ║
║ Avg Loss:         $1.55                                  ║
╚══════════════════════════════════════════════════════════╝
```

## 🔍 How It Works

### Market Identification

- Uses Gamma API to find active 5-minute Bitcoin markets
- Filters for markets with "5 min" and "BTC"/"Bitcoin" keywords
- Automatically switches when current market closes

### Spread Analysis

- Fetches order books for YES and NO tokens
- Calculates spread: `1.00 - (YES_ask + NO_ask)`
- Only trades if spread > `MIN_SPREAD_TO_TRADE`

### Order Placement

- Places limit orders slightly inside the current spread
- Acts as a maker (provides liquidity) → 0% trading fees
- Example:
  - YES ask: $0.52, NO ask: $0.46 (spread = $0.02)
  - Bot places: YES bid @ $0.50, NO bid @ $0.45
  - If both fill, profit = $0.05 per share

### Position Management

- Monitors open orders for fills
- Cancels unfilled orders after timeout
- Closes positions when both YES/NO fill

## 🛡️ Safety Features

- **Dry-run mode**: Test without real trades
- **Position limits**: Maximum concurrent positions
- **Daily loss limit**: Auto-stop if losses exceed threshold
- **Timeout handling**: Cancel stale orders
- **Graceful shutdown**: Cancel all orders on Ctrl+C

## 📁 Project Structure

```
polymarket/
├── .env.example        # Environment template
├── .env               # Your credentials (gitignored)
├── .gitignore         # Git ignore rules
├── requirements.txt   # Python dependencies
├── config.py         # Configuration settings
├── utils.py          # Helper functions
├── market_monitor.py # Market scanning logic
├── strategy.py       # Maker market making strategy
├── bot.py           # Main orchestrator
└── README.md        # This file
```

## 🐛 Troubleshooting

### "POLYGON_PRIVATE_KEY is required"
- Make sure you created `.env` file with your private key

### "No active 5-minute Bitcoin markets found"
- These markets may not always be active
- Wait a few minutes and the bot will keep checking

### "Failed to place order"
- Check that you approved token allowances: `python bot.py --approve-tokens`
- Ensure wallet has USDC on Polygon network
- Check Polymarket API status

### Orders not filling
- Spread may be too narrow (increase `MIN_SPREAD_TO_TRADE`)
- Market may be illiquid
- Try adjusting `PRICE_IMPROVEMENT_OFFSET`

## 🚧 Future Enhancements (Phase 2+)

- Latency arbitrage strategy
- Extreme probability arbitrage
- ML pattern recognition
- Multi-market support
- Advanced position sizing
- Historical backtesting

## 📄 License

MIT License - Trade at your own risk

## 🤝 Contributing

This is a personal trading bot. Use and modify as needed for your own trading.

## ⚖️ Legal

- This bot is for educational purposes
- Trading involves substantial risk of loss
- You are responsible for your own trades and compliance with local laws
- No warranty or guarantee of profits

---

**Good luck and trade responsibly! 🚀**
