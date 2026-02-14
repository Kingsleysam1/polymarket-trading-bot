"""
Utility functions for Polymarket Trading Bot
"""
import logging
import sys
from datetime import datetime
from typing import Optional
import config


def setup_logger(name: str = "PolymarketBot") -> logging.Logger:
    """
    Set up logger with console and file handlers
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    if config.LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if config.LOG_TO_FILE:
        file_handler = logging.FileHandler(config.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def format_price(price: float, decimals: int = 4) -> str:
    """Format price for display"""
    return f"${price:.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage for display"""
    return f"{value * 100:.{decimals}f}%"


def calculate_spread(yes_ask: float, no_ask: float) -> float:
    """
    Calculate the spread opportunity
    
    In Polymarket, YES + NO should equal $1.00
    If YES ask = 0.52 and NO ask = 0.46, the combined cost is 0.98
    The spread is 1.00 - 0.98 = 0.02 ($0.02 profit potential)
    
    Args:
        yes_ask: Best ask price for YES token
        no_ask: Best ask price for NO token
        
    Returns:
        Spread in USD (profit potential before fees)
    """
    combined_cost = yes_ask + no_ask
    spread = 1.0 - combined_cost
    return spread


def calculate_profit_potential(spread: float, order_size: float, fee_rate: float = 0.0) -> float:
    """
    Calculate expected profit from a spread trade
    
    Args:
        spread: Spread in USD
        order_size: Size of order in USDC
        fee_rate: Trading fee rate (maker orders have 0% fee on Polymarket)
        
    Returns:
        Expected profit in USD
    """
    gross_profit = spread * order_size
    fees = order_size * fee_rate * 2  # Buy and sell
    net_profit = gross_profit - fees
    return net_profit


def time_until_market_close(end_time: int) -> int:
    """
    Calculate seconds until market closes
    
    Args:
        end_time: Market end time in Unix timestamp
        
    Returns:
        Seconds remaining (negative if market already closed)
    """
    now = int(datetime.now().timestamp())
    return end_time - now


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to readable format"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def truncate_string(s: str, max_length: int = 50) -> str:
    """Truncate long strings for logging"""
    if len(s) <= max_length:
        return s
    return s[:max_length-3] + "..."


class PerformanceTracker:
    """Track trading performance metrics"""
    
    def __init__(self):
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.start_time = datetime.now()
        
    def record_trade(self, profit: float):
        """Record a completed trade"""
        self.total_trades += 1
        if profit > 0:
            self.winning_trades += 1
            self.total_profit += profit
        else:
            self.losing_trades += 1
            self.total_loss += abs(profit)
    
    @property
    def net_profit(self) -> float:
        """Calculate net profit"""
        return self.total_profit - self.total_loss
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    @property
    def average_win(self) -> float:
        """Calculate average winning trade"""
        if self.winning_trades == 0:
            return 0.0
        return self.total_profit / self.winning_trades
    
    @property
    def average_loss(self) -> float:
        """Calculate average losing trade"""
        if self.losing_trades == 0:
            return 0.0
        return self.total_loss / self.losing_trades
    
    def get_summary(self) -> str:
        """Get performance summary string"""
        runtime = datetime.now() - self.start_time
        
        summary = f"""
╔══════════════════════════════════════════════════════════╗
║              PERFORMANCE SUMMARY                         ║
╠══════════════════════════════════════════════════════════╣
║ Runtime:          {str(runtime).split('.')[0]:<35} ║
║ Total Trades:     {self.total_trades:<35} ║
║ Winning Trades:   {self.winning_trades:<35} ║
║ Losing Trades:    {self.losing_trades:<35} ║
║ Win Rate:         {format_percentage(self.win_rate):<35} ║
║                                                          ║
║ Total Profit:     {format_price(self.total_profit):<35} ║
║ Total Loss:       {format_price(self.total_loss):<35} ║
║ Net P&L:          {format_price(self.net_profit):<35} ║
║                                                          ║
║ Avg Win:          {format_price(self.average_win):<35} ║
║ Avg Loss:         {format_price(self.average_loss):<35} ║
╚══════════════════════════════════════════════════════════╝
"""
        return summary
