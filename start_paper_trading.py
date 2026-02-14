#!/usr/bin/env python3
"""
Paper Trading Mode - Test bot with $100 virtual capital using live market data
"""
import subprocess
import sys

print("""
╔══════════════════════════════════════════════════════════╗
║      POLYMARKET BOT - PAPER TRADING MODE                 ║
╠══════════════════════════════════════════════════════════╣
║  Starting Capital: $100.00 (Virtual)                     ║
║  Uses: LIVE MARKET DATA                                  ║
║  Simulates: Order fills & P&L tracking                   ║
║  Risk: ZERO (No real money)                              ║
╚══════════════════════════════════════════════════════════╝

✅ Paper Trading Features:
   • Starts with $100 virtual capital
   • Uses real-time market data from Polymarket
   • Simulates realistic order fills
   • Tracks virtual P&L as if trading real money
   • Shows performance on dashboard

📊 Dashboard: http://127.0.0.1:5000

🎯 Goal: Validate strategy effectiveness before risking real capital

Press Ctrl+C to stop and see final performance report.
""")

try:
    # Run bot in dry-run mode with paper trading enabled
    # The bot will automatically use paper trading when DRY_RUN is active
    subprocess.run([
        sys.executable, "bot_paper.py", "--dashboard"
    ])
except KeyboardInterrupt:
    print("\n\n✅ Paper trading session ended!")
    print("Check the dashboard for your final performance report.")
