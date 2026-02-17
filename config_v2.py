"""
Extended Configuration for Polymarket Trading Bot V2

Adds WebSocket and multi-market settings while preserving all existing config.
"""
from config import *  # Import all existing config

# ============================================================================
# PHASE 1: WEBSOCKET CONFIGURATION
# ============================================================================

# WebSocket URL for Polymarket (may need adjustment based on actual API)
# If WebSocket is unavailable, the bot will fall back to REST polling
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# WebSocket reconnection settings
WS_RECONNECT_DELAY = 5  # Base delay between reconnection attempts (seconds)
WS_MAX_RECONNECT_ATTEMPTS = 10  # Max attempts before falling back to REST
WS_PING_INTERVAL = 30  # Ping/pong interval for health checks (seconds)

# ============================================================================
# MULTI-MARKET MONITORING
# ============================================================================

# Maximum number of markets to monitor simultaneously
MAX_CONCURRENT_MARKETS = 25

# How often to scan for new markets (seconds)
MARKET_SCAN_INTERVAL = 10

# Extended keywords for market filtering
# Includes 5-minute, hourly, and multiple crypto assets
MARKET_KEYWORDS_EXTENDED = [
    "5 min", "5min", "5m", "5 m",  # 5-minute markets
    "hourly", "1h", "1 hour",       # Hourly markets
    "BTC", "Bitcoin",                # Bitcoin
    "ETH", "Ethereum",               # Ethereum
    "SOL", "Solana"                  # Solana
]

# ============================================================================
# PERFORMANCE TARGETS
# ============================================================================

# Target latency for market updates (milliseconds)
TARGET_LATENCY_MS = 100  # <100ms for real-time trading

# Event queue size for async operations
EVENT_QUEUE_SIZE = 1000

# ============================================================================
# CONNECTION HEALTH
# ============================================================================

# Latency threshold for degraded connection state (milliseconds)
LATENCY_THRESHOLD_MS = 200

# Number of errors before circuit breaker opens
ERROR_THRESHOLD = 5

# Time to wait before retrying after circuit opens (seconds)
CIRCUIT_TIMEOUT = 60

# ============================================================================
# STRATEGY ALLOCATION (for future multi-strategy)
# ============================================================================

# Capital allocation per strategy (must sum to 1.0)
STRATEGY_ALLOCATION = {
    'maker': 0.40,              # 40% to maker market making
    'latency_arb': 0.30,        # 30% to latency arbitrage
    'sum_to_one': 0.20,         # 20% to sum-to-one arbitrage
    'ml_pattern': 0.10          # 10% to ML pattern recognition
}

# Global risk limits across all strategies
GLOBAL_MAX_POSITIONS = 15             # Max 15 concurrent positions
GLOBAL_DAILY_LOSS_LIMIT = 200.0       # Stop all trading at -$200
GLOBAL_POSITION_SIZE_MAX = 100.0      # No single position >$100

# ============================================================================
# ASYNC EXECUTION SETTINGS
# ============================================================================

# Number of thread pool workers for sync strategy adapter
ASYNC_ADAPTER_WORKERS = 4

# Concurrent execution limits
MAX_CONCURRENT_STRATEGY_EXECUTIONS = 10

# ============================================================================
# PHASE 2: LATENCY ARBITRAGE CONFIGURATION
# ============================================================================

# Binance WebSocket URL
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"

# Spike detection thresholds
LATENCY_MIN_BTC_MOVE = 150.0  # Minimum BTC price change to detect ($)
LATENCY_SPIKE_TIME_WINDOW_MIN = 3  # Minimum seconds for comparison
LATENCY_SPIKE_TIME_WINDOW_MAX = 10  # Maximum seconds for comparison
LATENCY_SPIKE_COOLDOWN = 30  # Seconds between spike detections

# Position sizing
LATENCY_MAX_POSITION_SIZE = 50.0  # Maximum per trade ($)
LATENCY_MAX_CONCURRENT_POSITIONS = 3  # Max open latency arb positions

# Risk management
LATENCY_DAILY_TRADE_LIMIT = 20  # Max trades per day
LATENCY_DAILY_LOSS_LIMIT = 100.0  # Stop trading if daily loss exceeds ($)
LATENCY_MAX_HOLD_TIME = 30  # Max seconds to hold position
LATENCY_STOP_LOSS_PCT = 0.05  # 5% stop loss

# Exit targets
LATENCY_PROFIT_TARGET_UP = 0.80  # Target YES price after pump
LATENCY_PROFIT_TARGET_DOWN = 0.70  # Target NO price after dump
LATENCY_ENTRY_THRESHOLD_UP = 0.60  # Max YES price to enter on pump
LATENCY_ENTRY_THRESHOLD_DOWN = 0.40  # Min YES price to enter on dump
