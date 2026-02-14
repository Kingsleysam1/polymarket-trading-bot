"""
Base Strategy Class - Abstract interface for all trading strategies
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Enum for different strategy types"""
    MAKER = "maker"
    PROBABILITY_SCALPING = "probability_scalping"
    LATENCY_ARBITRAGE = "latency_arbitrage"
    ML_PATTERN = "ml_pattern"


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    All strategies must implement these methods.
    """
    
    def __init__(self, name: str, strategy_type: StrategyType):
        self.name = name
        self.strategy_type = strategy_type
        self.enabled = True
        self.open_positions = {}
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'last_trade_time': None
        }
        logger.info(f"✅ {self.name} strategy initialized")
    
    @abstractmethod
    def scan_opportunities(self) -> Optional[Dict]:
        """
        Scan for trading opportunities.
        
        Returns:
            Signal dict if opportunity found, None otherwise
        """
        pass
    
    @abstractmethod
    def execute_trade(self, signal: Dict, dry_run: bool = False) -> Optional[str]:
        """
        Execute a trade based on the signal.
        
        Args:
            signal: Trade signal from scan_opportunities
            dry_run: If True, simulate trade without executing
            
        Returns:
            Position ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """
        Monitor and manage open positions.
        
        Args:
            dry_run: If True, simulate position monitoring
            
        Returns:
            List of closed position IDs
        """
        pass
    
    def record_trade(self, profit: float):
        """Record trade performance"""
        self.performance_stats['total_trades'] += 1
        self.performance_stats['total_profit'] += profit
        self.performance_stats['last_trade_time'] = time.time()
        
        if profit > 0:
            self.performance_stats['winning_trades'] += 1
        else:
            self.performance_stats['losing_trades'] += 1
    
    def get_performance(self) -> Dict:
        """Get strategy performance statistics"""
        total = self.performance_stats['total_trades']
        win_rate = (self.performance_stats['winning_trades'] / total * 100) if total > 0 else 0
        
        return {
            'strategy_name': self.name,
            'strategy_type': self.strategy_type.value,
            'enabled': self.enabled,
            'total_trades': total,
            'winning_trades': self.performance_stats['winning_trades'],
            'losing_trades': self.performance_stats['losing_trades'],
            'win_rate': win_rate,
            'total_profit': self.performance_stats['total_profit'],
            'open_positions': len(self.open_positions)
        }
    
    def enable(self):
        """Enable this strategy"""
        self.enabled = True
        logger.info(f"✅ {self.name} enabled")
    
    def disable(self):
        """Disable this strategy"""
        self.enabled = False
        logger.info(f"⏸️  {self.name} disabled")
    
    def cancel_all_orders(self, dry_run: bool = False):
        """Cancel all open orders - must be implemented by subclass if needed"""
        pass
