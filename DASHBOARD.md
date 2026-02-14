# Web Dashboard - Quick Reference

## What It Does

The web dashboard provides a beautiful real-time interface to monitor your Polymarket trading bot without having to watch console logs.

## Features

### Real-Time Monitoring (Auto-refresh every 3 seconds)
- **Performance Metrics**: Net P&L, win rate, total trades, uptime
- **Current Market**: Active 5-minute Bitcoin market info
- **Current Spread**: Bid-ask spread and profit potential
- **Open Positions**: All active trading positions
- **Recent Trades**: Trade history with win/loss indicators
- **Error Log**: Recent errors and warnings

### Modern Design
- Glassmorphism UI with purple gradient background
- Color-coded metrics (green for profits, red for losses)
- Responsive layout that works on mobile and desktop
- Smooth animations and transitions

## How to Use

### Start Bot with Dashboard

```bash
# Dry-run mode with dashboard
python bot.py --dry-run --dashboard

# Live trading with dashboard
python bot.py --dashboard

# Quick start script (dry-run + dashboard)
python start_with_dashboard.py
```

### Access Dashboard

Open your browser to: **http://127.0.0.1:5000**

The dashboard will immediately start showing:
- Bot status (initializing → running → trading)
- Real-time market data
- Trading activity as it happens

### Without Dashboard

If you don't need the web interface, just run the bot normally:

```bash
# Console logging only
python bot.py --dry-run
```

## Architecture

**Components:**
1. `bot_state.py` - Thread-safe state manager (shared between bot and web server)
2. `web_server.py` - Flask server with REST API endpoints
3. `templates/dashboard.html` - Frontend with auto-refresh
4. `bot.py` - Main bot (updated to push state changes)

**How it works:**
1. Bot runs in main thread
2. Dashboard server runs in background daemon thread  
3. Bot pushes state updates to `bot_state` manager
4. Dashboard polls `/api/status` every 3 seconds
5. Frontend updates UI with new data

**Thread-safe:** All state access is protected by locks, so bot and dashboard can run concurrently without conflicts.

## API Endpoints

The dashboard server exposes these REST endpoints:

- `GET /` - Serve dashboard HTML
- `GET /api/status` - Full bot state (all data)
- `GET /api/performance` - Performance metrics only
- `GET /api/market` - Current market info
- `GET /api/positions` - Open positions
- `GET /api/trades` - Recent trade history

You can call these directly from other tools:

```bash
# Get bot status as JSON
curl http://127.0.0.1:5000/api/status

# Get just performance metrics
curl http://127.0.0.1:5000/api/performance
```

## Customization

### Change Port

Edit `web_server.py`:
```python
def run_dashboard(host='127.0.0.1', port=5000):  # Change port here
```

### Change Refresh Rate

Edit `templates/dashboard.html`:
```javascript
refreshInterval = setInterval(fetchData, 3000);  // 3000ms = 3 seconds
```

### Add More Metrics

1. Update `bot_state.py` to track new data
2. Update `bot.py` to push the data
3. Update `templates/dashboard.html` to display it

## Troubleshooting

**Dashboard won't load:**
- Make sure Flask is installed: `pip install flask flask-cors`
- Check if port 5000 is already in use: `lsof -i :5000`
- Try a different port in `web_server.py`

**No data showing:**
- Wait a few seconds for initial data
- Check bot console for errors
- Verify bot is actually running (not crashed)

**Old data / not updating:**
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
- Check browser console for JavaScript errors
- Verify `/api/status` endpoint returns JSON

---

**Enjoy monitoring your bot! 🚀**
