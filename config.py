"""
Configuration settings for Polymarket Trading Bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# API CREDENTIALS
# ============================================================================
POLYGON_PRIVATE_KEY = os.getenv("POLYGON_PRIVATE_KEY", "")
SIGNATURE_TYPE = int(os.getenv("SIGNATURE_TYPE", "0"))
FUNDER_ADDRESS = os.getenv("FUNDER_ADDRESS", "")

# Validate required credentials
if not POLYGON_PRIVATE_KEY:
    raise ValueError("POLYGON_PRIVATE_KEY is required in .env file")

# ============================================================================
# POLYMARKET API ENDPOINTS
# ============================================================================
CLOB_API_URL = "https://clob.polymarket.com"
GAMMA_API_URL = "https://gamma-api.polymarket.com"
POLYGON_CHAIN_ID = 137  # Polygon Mainnet

# ============================================================================
# TRADING PARAMETERS
# ============================================================================

# Minimum spread required to consider trading (in USD)
# Example: 0.05 means the spread must be at least 5 cents
MIN_SPREAD_TO_TRADE = 0.05

# Base order size in USDC
# Start small! Recommended: $1-3 for initial testing
ORDER_SIZE_USD = 2.0

# Maximum number of concurrent open positions
# Each position is a pair of YES/NO orders
MAX_OPEN_POSITIONS = 3

# How long to wait for orders to fill before canceling (seconds)
# 5-minute markets are fast, so don't wait too long
POSITION_TIMEOUT_SECONDS = 180

# How often to scan for new markets (seconds)
MARKET_SEARCH_INTERVAL = 30

# Price improvement offset (place orders this much inside the spread)
# Example: 0.01 means place buy orders 1 cent higher than current best bid
PRICE_IMPROVEMENT_OFFSET = 0.01

# Minimum time remaining in market to place new trades (seconds)
# Don't enter positions too close to market close
MIN_TIME_REMAINING_TO_TRADE = 120

# ============================================================================
# RISK MANAGEMENT
# ============================================================================

# Maximum total capital to allocate at once
MAX_TOTAL_POSITION_SIZE = ORDER_SIZE_USD * MAX_OPEN_POSITIONS * 2

# Stop trading if total loss exceeds this amount (USD)
# Set to None to disable
DAILY_LOSS_LIMIT = 50.0

# Stop trading if total profit exceeds this amount (USD) - take profits and rest
# Set to None to disable
DAILY_PROFIT_TARGET = 150.0

# ============================================================================
# MARKET IDENTIFICATION
# ============================================================================

# Keywords to identify 5-minute Bitcoin markets
MARKET_KEYWORDS = ["5 min", "BTC", "Bitcoin", "5m", "5 m"]

# Markets to exclude (if there are test markets or other variants)
EXCLUDE_KEYWORDS = ["test", "demo"]

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE = "polymarket_bot.log"
LOG_TO_CONSOLE = True
LOG_TO_FILE = True

# ============================================================================
# OPERATIONAL SETTINGS
# ============================================================================

# Dry run mode - simulates trades without actually executing them
# Override via command line: python bot.py --dry-run
DRY_RUN = False

# Main loop sleep interval (seconds)
# How long to wait between cycles
LOOP_SLEEP_INTERVAL = 5

# Heartbeat interval - log status every N seconds
HEARTBEAT_INTERVAL = 60

# ============================================================================
# PAPER TRADING (Simulation with Virtual Capital)
# ============================================================================

# Enable paper trading mode (uses live data, simulates fills and tracks virtual P&L)
PAPER_TRADING_ENABLED = True

# Starting virtual capital for paper trading
PAPER_TRADING_START_CAPITAL = 100.0

# Simulated fill probability parameters
# Higher = orders fill more easily (less realistic)
# Lower = orders take longer to fill (more realistic)
PAPER_TRADING_FILL_RATE = 0.15  # 15% chance per cycle if price is competitive

# ============================================================================
# MULTI-STRATEGY CONFIGURATION
# ============================================================================

# Strategy Enablement (turn strategies on/off)
STRATEGY_MAKER_ENABLED = True
STRATEGY_PROBABILITY_ENABLED = True
STRATEGY_LATENCY_ENABLED = False  # Requires Binance setup
STRATEGY_ML_ENABLED = False  # Requires trained model

# Capital Allocation (must sum to 1.0)
CAPITAL_ALLOCATION = {
    'maker': 0.40,              # 40% to maker market making
    'probability': 0.30,        # 30% to probability scalping
    'latency': 0.20,            # 20% to latency arbitrage
    'ml_pattern': 0.10          # 10% to ML pattern recognition
}

# ============================================================================
# STRATEGY 2: LATENCY ARBITRAGE SETTINGS
# ============================================================================

LATENCY_MIN_BTC_MOVE = 200.0          # Minimum BTC price movement ($)
LATENCY_MAX_EXECUTION_TIME = 2.0      # Maximum execution time (seconds)
LATENCY_MAX_POSITION_SIZE = 100.0     # Max position size for latency trades
LATENCY_STOP_LOSS_PERCENT = 0.05      # 5% stop loss
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"

# ============================================================================
# STRATEGY 3: PROBABILITY SCALPING SETTINGS
# ============================================================================

PROBABILITY_MAX_MARKETS_TO_SCAN = 50       # How many markets to monitor
PROBABILITY_MIN_PROFIT_THRESHOLD = 0.005   # Minimum $0.005 profit per share
PROBABILITY_MAX_POSITION_SIZE = 100.0      # Max position size
PROBABILITY_PRICE_SUM_THRESHOLD = 0.992    # YES+NO must be < this for arbitrage

# ============================================================================
# STRATEGY 4: ML PATTERN RECOGNITION SETTINGS
# ============================================================================

ML_MIN_CONFIDENCE = 0.65                    # Minimum confidence threshold (65%)
ML_MODEL_PATH = "data/models/pattern_classifier.pkl"
ML_RETRAIN_INTERVAL = 86400                 # Retrain every 24 hours
ML_MAX_POSITION_SIZE = 50.0                 # Max position size for ML trades
ML_PATTERN_TYPES = ["breakout_continuation", "spike_reversal"]
