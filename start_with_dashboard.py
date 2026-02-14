#!/usr/bin/env python3
"""
Quick start script for Polymarket bot with dashboard
"""
import subprocess
import sys

print("""
╔══════════════════════════════════════════════════════════╗
║        POLYMARKET BOT - MONITORING DASHBOARD             ║
╚══════════════════════════════════════════════════════════╝

Starting bot with web dashboard enabled...

Dashboard will be available at: http://127.0.0.1:5000

Press Ctrl+C to stop the bot and dashboard.
""")

try:
    subprocess.run([
        sys.executable, "bot.py", "--dry-run", "--dashboard"
    ])
except KeyboardInterrupt:
    print("\n\n✅ Bot stopped!")
