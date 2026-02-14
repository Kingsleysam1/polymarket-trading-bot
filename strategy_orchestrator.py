"""
Strategy Orchestrator - Coordinates multiple trading strategies

Manages execution of all enabled strategies, capital allocation,
and performance tracking across strategies.
"""
from typing import List, Dict, Optional
import time
from py_clob_client.client import ClobClient

import config
from strategies.base_strategy import BaseStrategy
from strategies.probability_scalping import ProbabilityScalpingStrategy
from strategies.latency_arbitrage import LatencyArbitrageStrategy
from strategies.ml_pattern import MLPatternStrategy
from utils import setup_logger

logger = setup_logger("StrategyOrchestrator")


class StrategyOrchestrator:
    """
    Orchestrates multiple trading strategies with capital allocation.
    
    Responsibilities:
    - Initialize enabled strategies
    - Allocate capital across strategies
    - Run strategy scans in priority order
    - Track performance per strategy
    - Coordinate position management
    """
    
    def __init__(self, clob_client: ClobClient, total_capital: float):
        self.client = clob_client
        self.total_capital = total_capital
        self.strategies: List[BaseStrategy] = []
        self.capital_allocated = {}
        
        logger.info("🎯 Initializing Multi-Strategy Orchestrator")
        logger.info(f"💰 Total Capital: ${total_capital:.2f}")
        
        # Initialize enabled strategies
        self._initialize_strategies()
        
        # Allocate capital
        self._allocate_capital()
        
        logger.info(f"✅ Orchestrator initialized with {len(self.strategies)} active strategies")
    
    def _initialize_strategies(self):
        """Initialize all enabled strategies"""
        
        # Strategy 1: Maker Market Making (use legacy strategy.py)
        if config.STRATEGY_MAKER_ENABLED:
            try:
                # Import the legacy MakerStrategy from strategy.py
                import strategy as legacy_strategy
                maker = legacy_strategy.MakerStrategy(self.client)
                self.strategies.append(maker)
                logger.info("✅ Maker Market Making enabled")
            except Exception as e:
                logger.warning(f"Could not load Maker strategy: {e}")
        
        # Strategy 3: Probability Scalping
        if config.STRATEGY_PROBABILITY_ENABLED:
            try:
                prob_strategy = ProbabilityScalpingStrategy(self.client)
                self.strategies.append(prob_strategy)
                logger.info("✅ Probability Scalping enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Probability Scalping: {e}")
        
        # Strategy 2: Latency Arbitrage
        if config.STRATEGY_LATENCY_ENABLED:
            try:
                latency_strategy = LatencyArbitrageStrategy(self.client)
                latency_strategy.start()  # Start Binance WebSocket
                self.strategies.append(latency_strategy)
                logger.info("✅ Latency Arbitrage enabled")
            except Exception as e:
                logger.error(f"Failed to initialize Latency Arbitrage: {e}")
        
        # Strategy 4: ML Pattern Recognition
        if config.STRATEGY_ML_ENABLED:
            try:
                ml_strategy = MLPatternStrategy(self.client)
                if ml_strategy.enabled:  # Only add if model loaded
                    self.strategies.append(ml_strategy)
                    logger.info("✅ ML Pattern Recognition enabled")
                else:
                    logger.warning("ML Pattern Recognition disabled (no trained model)")
            except Exception as e:
                logger.error(f"Failed to initialize ML Pattern: {e}")
    
    def _allocate_capital(self):
        """Allocate capital to each strategy based on config"""
        allocation = config.CAPITAL_ALLOCATION
        
        for strategy in self.strategies:
            strategy_key = self._get_strategy_key(strategy)
            if strategy_key in allocation:
                allocated = self.total_capital * allocation[strategy_key]
                self.capital_allocated[strategy_key] = allocated
                strategy_name = getattr(strategy, 'name', type(strategy).__name__)
                logger.info(f"   {strategy_name}: ${allocated:.2f} ({allocation[strategy_key]:.0%})")
    
    def _get_strategy_key(self, strategy) -> str:
        """Get capital allocation key for a strategy"""
        # Check class name first (works for all strategies)
        class_name = type(strategy).__name__
        
        if 'Maker' in class_name:
            return 'maker'
        elif 'Probability' in class_name:
            return 'probability'
        elif 'Latency' in class_name:
            return 'latency'
        elif 'ML' in class_name or 'Pattern' in class_name:
            return 'ml_pattern'
        
        # Fallback: check name attribute if exists
        if hasattr(strategy, 'name'):
            name = strategy.name
            if 'Maker' in name:
                return 'maker'
            elif 'Probability' in name:
                return 'probability'
            elif 'Latency' in name:
                return 'latency'
            elif 'ML' in name or 'Pattern' in name:
                return 'ml_pattern'
        
        return 'maker'  # Default
    
    def run_cycle(self, dry_run: bool = False) -> Dict:
        """
        Run one orchestration cycle.
        
        1. Each strategy scans for opportunities
        2. Execute highest priority opportunities
        3. Monitor existing positions
        4. Return cycle statistics
        """
        cycle_stats = {
            'opportunities_found': 0,
            'trades_executed': 0,
            'positions_closed': 0,
            'strategies_active': 0
        }
        
        try:
            # Phase 1: Scan for opportunities (all strategies)
            opportunities = []
            
            for strategy in self.strategies:
                # Legacy strategies don't have 'enabled' attribute, assume enabled
                if not getattr(strategy, 'enabled', True):
                    continue
                
                cycle_stats['strategies_active'] += 1
                
                try:
                    signal = strategy.scan_opportunities()
                    if signal:
                        opportunities.append({
                            'strategy': strategy,
                            'signal': signal
                        })
                        cycle_stats['opportunities_found'] += 1
                except Exception as e:
                    strategy_name = getattr(strategy, 'name', type(strategy).__name__)
                    logger.error(f"Error scanning {strategy_name}: {e}")
            
            # Phase 2: Execute opportunities (priority order)
            # Priority: Latency > Probability > Maker > ML
            priority_order = ['latency', 'probability', 'maker', 'ml_pattern']
            
            for priority_key in priority_order:
                for opp in opportunities:
                    strategy = opp['strategy']
                    strategy_key = self._get_strategy_key(strategy)
                    
                    if strategy_key == priority_key:
                        # Check if strategy has capital available
                        allocated = self.capital_allocated.get(strategy_key, 0)
                        if allocated > 0:
                            # Execute trade
                            position_id = strategy.execute_trade(opp['signal'], dry_run=dry_run)
                            if position_id:
                                cycle_stats['trades_executed'] += 1
                                strategy_name = getattr(strategy, 'name', type(strategy).__name__)
                                logger.info(f"📈 {strategy_name} executed: {position_id}")
            
            # Phase 3: Monitor positions (all strategies)
            for strategy in self.strategies:
                # Legacy strategies don't have 'enabled' attribute, assume enabled
                if not getattr(strategy, 'enabled', True):
                    continue
                
                try:
                    closed = strategy.monitor_positions(dry_run=dry_run)
                    cycle_stats['positions_closed'] += len(closed)
                except Exception as e:
                    strategy_name = getattr(strategy, 'name', type(strategy).__name__)
                    logger.error(f"Error monitoring {strategy_name}: {e}")
            
        except Exception as e:
            logger.error(f"Error in orchestration cycle: {e}")
        
        return cycle_stats
    
    def get_performance_summary(self) -> Dict:
        """Get combined performance across all strategies"""
        summary = {
            'total_strategies': len(self.strategies),
            'enabled_strategies': sum(1 for s in self.strategies if getattr(s, 'enabled', True)),
            'total_capital': self.total_capital,
            'strategies': []
        }
        
        total_trades = 0
        total_profit = 0.0
        total_winning = 0
        total_losing = 0
        
        for strategy in self.strategies:
            # Legacy strategies may not have get_performance() method
            if hasattr(strategy, 'get_performance'):
                perf = strategy.get_performance()
            else:
                # Create default performance for legacy strategies
                perf = {
                    'strategy_name': type(strategy).__name__,
                    'enabled': getattr(strategy, 'enabled', True),
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_profit': 0.0,
                    'win_rate': 0.0
                }
            
            summary['strategies'].append(perf)
            
            total_trades += perf['total_trades']
            total_profit += perf['total_profit']
            total_winning += perf['winning_trades']
            total_losing += perf['losing_trades']
        
        summary['combined'] = {
            'total_trades': total_trades,
            'total_profit': total_profit,
            'winning_trades': total_winning,
            'losing_trades': total_losing,
            'overall_win_rate': (total_winning / total_trades * 100) if total_trades > 0 else 0
        }
        
        return summary
    
    def stop_all(self, dry_run: bool = False):
        """Stop all strategies gracefully"""
        logger.info("🛑 Stopping all strategies...")
        
        for strategy in self.strategies:
            try:
                # Stop strategy-specific services (e.g., Binance WebSocket)
                if hasattr(strategy, 'stop'):
                    strategy.stop()
                
                # Cancel all orders
                strategy.cancel_all_orders(dry_run=dry_run)
            except Exception as e:
                strategy_name = getattr(strategy, 'name', type(strategy).__name__)
                logger.error(f"Error stopping {strategy_name}: {e}")
        
        logger.info("✅ All strategies stopped")
