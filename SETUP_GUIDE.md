# Polymarket Bot Setup Guide

## What You Need

To run the Polymarket bot, you need:

1. **Polygon Wallet Private Key** ✅ (You already have this configured!)
2. **USDC on Polygon Network** ⚠️ (Need to verify)
3. **Token Allowances Approved** ⚠️ (Need to do this)

---

## Current Configuration Status

### ✅ Private Key Configured
Your `.env` file has a private key set:
```
POLYGON_PRIVATE_KEY=0x7dd68fe6069116bcf80d7a8ee5095f89f7e2e1837c3636d346a66da5d13d69d6
```

**Important Security Note:**
- This private key is now visible in your `.env` file
- **NEVER** commit this file to GitHub or share it
- Make sure `.gitignore` includes `.env` (already configured ✅)

### ⚠️ Need to Check: Wallet Balance

Your wallet needs USDC on the Polygon network to trade. Let's check:

**Wallet Address (derived from your private key):**
We can check this by running a connection test.

**Minimum Recommended:**
- $100 USDC on Polygon for initial testing
- Start with smaller amounts if you prefer ($20-50)

### ⚠️ Need to Do: Approve Token Allowances

Before the bot can trade, you must approve Polymarket's contracts to use your USDC. This is a one-time setup step.

---

## Next Steps

### 1. Verify Wallet Has USDC

Run the connection test to check your wallet:
```bash
python3 test_connection.py
```

This will:
- Verify your private key works
- Check if you can connect to Polymarket
- Show if markets are available

### 2. Get USDC on Polygon (if needed)

If you don't have USDC on Polygon yet:

**Option A: Bridge from Ethereum**
- Use [Polygon Bridge](https://wallet.polygon.technology/bridge)
- Bridge USDC from Ethereum to Polygon

**Option B: Buy directly on Polygon**
- Use [Uniswap on Polygon](https://app.uniswap.org/)
- Swap MATIC for USDC

**Option C: Use a CEX**
- Withdraw USDC from Coinbase/Binance/etc.
- Select "Polygon" network when withdrawing

### 3. Approve Token Allowances (Required!)

Once you have USDC, run this **ONE TIME**:
```bash
python3 bot.py --approve-tokens
```

This will:
- Ask Polymarket's contracts for permission to use your USDC
- You'll need to confirm the transaction
- Cost a small amount of MATIC for gas (≈$0.01)

### 4. Start Trading!

After approval:
```bash
# Test in dry-run mode first (recommended)
python3 bot.py --dry-run --dashboard

# When ready for live trading (start small!)
python3 bot.py --dashboard
```

---

## Configuration Parameters

Want to adjust the bot's behavior? Edit `config.py`:

### Trading Parameters
```python
MIN_SPREAD_TO_TRADE = 0.05        # Minimum 5-cent spread to trade
ORDER_SIZE_USD = 2.0               # Order size in USDC (start small!)
MAX_OPEN_POSITIONS = 3             # Max concurrent positions
POSITION_TIMEOUT_SECONDS = 180     # Cancel after 3 minutes
```

### Risk Management
```python
DAILY_LOSS_LIMIT = 50.0      # Stop if losses exceed $50
DAILY_PROFIT_TARGET = 150.0  # Stop if profit reaches $150
```

**Recommendation:** Keep `ORDER_SIZE_USD = 1.0` or `2.0` for your first day of testing!

---

## Troubleshooting

### "Invalid private key"
- Make sure your private key starts with `0x`
- Check for extra spaces or quotes
- Verify it's 66 characters total (0x + 64 hex chars)

### "No USDC balance"
- Check your wallet on [PolygonScan](https://polygonscan.com/)
- Make sure you're on Polygon network (not Ethereum)
- Get USDC using one of the methods above

### "Token allowance not approved"
- Run `python3 bot.py --approve-tokens`
- Make sure you have MATIC for gas fees
- Confirm the transaction in your wallet

### "No active markets found"
- This is normal! 5-minute Bitcoin markets aren't always active
- The bot will keep checking and start trading when markets appear
- Try running during high-volume trading hours

---

## Security Checklist

- ✅ `.env` file is in `.gitignore`
- ⚠️ Use a dedicated wallet (not your main wallet)
- ⚠️ Only keep necessary funds in the trading wallet
- ⚠️ Start with small position sizes
- ⚠️ Monitor the bot closely for the first few hours

---

## Quick Reference Commands

```bash
# Test connection
python3 test_connection.py

# Approve tokens (one-time)
python3 bot.py --approve-tokens

# Dry-run with dashboard
python3 start_with_dashboard.py

# Live trading small size
python3 bot.py --dashboard
```

---

**Ready to proceed?** Let's run the connection test to verify everything!
