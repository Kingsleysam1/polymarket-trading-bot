"""
Web Dashboard Server - Monitor bot trades via web interface
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
from bot_state import bot_state

app = Flask(__name__)
CORS(app)

# Serve the dashboard HTML
@app.route('/')
def index():
    """Serve main dashboard page"""
    return render_template('dashboard.html')

# API endpoint for bot state
@app.route('/api/status')
def get_status():
    """Get current bot status"""
    return jsonify(bot_state.get_state())

# API endpoint for performance metrics
@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    state = bot_state.get_state()
    return jsonify(state.get("performance", {}))

# API endpoint for current market
@app.route('/api/market')
def get_market():
    """Get current market information"""
    state = bot_state.get_state()
    return jsonify(state.get("current_market", {}))

# API endpoint for open positions
@app.route('/api/positions')
def get_positions():
    """Get open positions"""
    state = bot_state.get_state()
    return jsonify(state.get("open_positions", []))

# API endpoint for recent trades
@app.route('/api/trades')
def get_trades():
    """Get recent trades"""
    state = bot_state.get_state()
    return jsonify(state.get("recent_trades", []))

def run_dashboard(host='0.0.0.0', port=None):
    """Run the dashboard server"""
    if port is None:
        port = int(os.environ.get("PORT", 8000))
        
    print(f"🌐 Dashboard starting at http://{host}:{port}")
    print(f"📊 Open your browser to view the monitoring dashboard")
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_dashboard()
