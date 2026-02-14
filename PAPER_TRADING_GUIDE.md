# Polymarket Paper Trading Quick Start

## What is Paper Trading?

Paper trading lets you test the bot with **virtual $100 capital** using **real live market data** from Polymarket. Think of it as a flight simulator for trading - you get the full experience without risking actual money.

## How It Works

1. **Starts with $100 virtual capital**
2. **Monitors real Polymarket 5-minute Bitcoin markets**
3. **Simulates placing limit orders** when spreads are profitable
4. **Simulates realistic order fills** based on market conditions
5. **Tracks virtual P&L** as if you were trading real money
6. **Shows performance on dashboard** with real-time updates

## Quick Start

### Step 1: Stop the Current Bot

If the regular bot is running, stop it first (Ctrl+C in the terminal).

### Step 2: Start Paper Trading

```bash
cd /Users/mac/Desktop/polymarket
python3 start_paper_trading.py
```

### Step 3: Open Dashboard

Open your browser to: **http://127.0.0.1:5000**

You'll see:
- Starting capital: $100.00
- Current capital (updates as trades complete)
- P&L (profit/loss)
- Win rate
- Trade history

### Step 4: Let It Run

Let the bot run for 1-4 hours to collect meaningful data. The dashboard updates every 3 seconds.

### Step 5: Review Performance

When you stop the bot (Ctrl+C), you'll see a detailed performance report showing:
- Total profit/loss
- Number of trades
- Win rate
- Final capital

## What You'll Learn

After a few hours of paper trading, you'll know:

✅ **Does the strategy work?** (Is it profitable?)
✅ **How many trades per hour?** (Activity level)
✅ **What's the win rate?** (Success percentage)
✅ **What's the average profit per trade?**
✅ **Are there enough markets?** (Market availability)

## Expected Results

Based on the strategy parameters:

**Conservative Estimate:**
- Trades per hour: 2-4
- Win rate: 70-85%
- Profit per trade: $0.50-$2.00
- Daily profit potential: $20-$60

**If NO profitable trades after 2-3 hours:**
- Markets might not be active
- Spreads might be too tight
- Adjust `MIN_SPREAD_TO_TRADE` in `config.py`

## Dashboard Example

When paper trading is active, you should see:

```
📊 Performance
   Net P&L: +$12.40
   Win Rate: 82.5%
   Total Trades: 18
   Uptime: 2h 15m

💰 Current Capital: $112.40
```

## Adjusting Parameters

Edit `config.py` to test different settings:

```python
# More aggressive (tighter spreads)
MIN_SPREAD_TO_TRADE = 0.03  # 3 cents instead of 5

# Larger position sizes
ORDER_SIZE_USD = 5.0  # $5 instead of $2

# More concurrent positions
MAX_OPEN_POSITIONS = 5  # 5 instead of 3
```

Each change will affect:
- Trade frequency (how often bot trades)
- Profit per trade (larger sizes = more profit/loss)
- Capital usage (more positions = more capital locked)

## When to Go Live

Consider live trading when paper trading shows:

✅ **Positive P&L** after 50+ trades
✅ **Win rate above 65%**
✅ **Consistent profit over 24 hours**
✅ **You understand how it works**

**Still use small sizes ($1-3) when starting live!**

## Troubleshooting

**"No active markets found"**
- 5-minute Bitcoin markets aren't always available
- Try during high-volume trading hours (US market hours)
- Let it run longer - markets appear periodically

**"No trades after 1 hour"**
- Spreads might be too tight
- Lower `MIN_SPREAD_TO_TRADE` to 0.03 or even 0.02
- Check dashboard to see current spreads

**"Losing money in simulation"**
- This is valuable info! Don't go live yet
- Review trade history to see what's wrong
- Adjust parameters or strategy

## Next Steps

1. **Run paper trading for 4-8 hours**
2. **Review performance metrics**
3. **Adjust config if needed**
4. **Run again to validate changes**
5. **If profitable → Consider live trading with small sizes**

---

**Remember:** Paper trading is risk-free testing. Use it extensively before risking real capital!
