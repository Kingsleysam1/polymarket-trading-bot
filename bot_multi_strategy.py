"""
Multi-Strategy Trading Bot - Combines all four trading strategies

Runs all enabled strategies simultaneously with proper capital allocation:
1. Maker Market Making
2. Latency Arbitrage (Binance → Polymarket)
3. Probability Scalping
4. ML Pattern Recognition
"""
import argparse
import signal
import sys
import time
import threading
from py_clob_client.client import ClobClient

import config
from utils import setup_logger
from strategy_orchestrator import StrategyOrchestrator
from bot_state import bot_state
import web_server
from paper_trading import init_paper_trading, get_paper_trader

logger = setup_logger("MultiStrategyBot")


class MultiStrategyBot:
    """
    Multi-strategy trading bot with unified orchestration.
    Supports both live trading and paper trading modes.
    """
    
    def __init__(self, dry_run: bool = False, enable_dashboard: bool = False, starting_capital: float = 100.0):
        self.dry_run = dry_run
        self.enable_dashboard = enable_dashboard
        self.running = False
        self.dashboard_thread = None
        
        # Initialize paper trading if enabled
        self.paper_trader = None
        if config.PAPER_TRADING_ENABLED or dry_run:
            self.paper_trader = init_paper_trading(starting_capital)
            logger.info(f"💰 Paper Trading Mode: ${starting_capital:.2f} virtual capital")
        
        logger.info("🚀 Initializing Multi-Strategy Bot...")
        bot_state.update_status("initializing")
        
        if dry_run:
            logger.info("⚠️  DRY RUN MODE - No real trades will be executed")
        
        # Initialize Polymarket CLOB client
        try:
            self.client = ClobClient(
                host=config.CLOB_API_URL,
                key=config.POLYGON_PRIVATE_KEY,
                chain_id=config.POLYGON_CHAIN_ID,
                signature_type=config.SIGNATURE_TYPE,
                funder=config.FUNDER_ADDRESS if config.FUNDER_ADDRESS else None
            )
            logger.info("✅ CLOB Client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CLOB client: {e}")
            raise
        
        # Initialize strategy orchestrator
        self.orchestrator = StrategyOrchestrator(self.client, starting_capital)
        
        # State tracking
        self.last_heartbeat = time.time()
        self.cycle_count = 0
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("✅ Multi-Strategy Bot initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("\\n🛑 Shutdown signal received...")
        self.stop()
    
    def start(self):
        """Start the multi-strategy trading loop"""
        logger.info("=" * 70)
        logger.info("🤖 POLYMARKET MULTI-STRATEGY TRADING BOT")
        logger.info("=" * 70)
        
        # Show enabled strategies
        perf = self.orchestrator.get_performance_summary()
        logger.info(f"Enabled Strategies ({perf['enabled_strategies']}/{perf['total_strategies']}):")
        for strat in perf['strategies']:
            if strat['enabled']:
                logger.info(f"  ✅ {strat['strategy_name']}")
        
        logger.info("=" * 70)
        logger.info(f"Configuration:")
        logger.info(f"  Total Capital: ${self.orchestrator.total_capital:.2f}")
        logger.info(f"  Order Size: ${config.ORDER_SIZE_USD}")
        logger.info(f"  Max Positions: {config.MAX_OPEN_POSITIONS}")
        if self.enable_dashboard:
            logger.info(f"  Dashboard: http://127.0.0.1:5000")
        logger.info("=" * 70)
        
        if self.dry_run or config.PAPER_TRADING_ENABLED:
            logger.info("⚠️  PAPER TRADING MODE - Uses live data, simulates fills")
            logger.info("=" * 70)
        
        # Start dashboard if enabled
        if self.enable_dashboard:
            self.dashboard_thread = threading.Thread(
                target=web_server.run_dashboard,
                daemon=True
            )
            self.dashboard_thread.start()
            logger.info("🌐 Dashboard server started")
        
        self.running = True
        bot_state.update_status("running")
        
        try:
            while self.running:
                self._trading_cycle()
                time.sleep(config.LOOP_SLEEP_INTERVAL)
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _trading_cycle(self):
        """Execute one cycle of multi-strategy trading"""
        try:
            self.cycle_count += 1
            
            # Heartbeat
            if time.time() - self.last_heartbeat > config.HEARTBEAT_INTERVAL:
                perf = self.orchestrator.get_performance_summary()
                combined = perf['combined']
                
                logger.info(
                    f"💓 Heartbeat | Cycle: {self.cycle_count} | "
                    f"Strategies: {perf['enabled_strategies']} | "
                    f"Trades: {combined['total_trades']} | "
                    f"P&L: ${combined['total_profit']:+.2f} | "
                    f"Win Rate: {combined['overall_win_rate']:.1f}%"
                )
                self.last_heartbeat = time.time()
            
            # Run orchestrated cycle
            cycle_stats = self.orchestrator.run_cycle(dry_run=self.dry_run)
            
            # Log significant activity
            if cycle_stats['opportunities_found'] > 0:
                logger.debug(
                    f"Cycle {self.cycle_count}: "
                    f"{cycle_stats['opportunities_found']} opportunities, "
                    f"{cycle_stats['trades_executed']} executed, "
                    f"{cycle_stats['positions_closed']} closed"
                )
            
            # Update bot state for dashboard
            self._update_dashboard()
            
        except Exception as e:
            error_msg = f"Error in trading cycle: {e}"
            logger.error(error_msg, exc_info=True)
            bot_state.add_error(error_msg)
    
    def _update_dashboard(self):
        """Update dashboard with latest performance"""
        perf = self.orchestrator.get_performance_summary()
        combined = perf['combined']
        
        bot_state.state['performance']['total_trades'] = combined['total_trades']
        bot_state.state['performance']['winning_trades'] = combined['winning_trades']
        bot_state.state['performance']['losing_trades'] = combined['losing_trades']
        bot_state.state['performance']['net_profit'] = combined['total_profit']
        bot_state.state['performance']['win_rate'] = combined['overall_win_rate'] / 100
        
        if self.paper_trader:
            stats = self.paper_trader.get_performance_summary()
            bot_state.state['paper_trading'] = {
                'starting_capital': stats['starting_capital'],
                'current_capital': stats['current_capital'],
                'profit_percentage': stats['profit_percentage']
            }
    
    def stop(self):
        """Stop the bot gracefully"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping multi-strategy bot...")
        self.running = False
        
        # Stop all strategies
        self.orchestrator.stop_all(dry_run=self.dry_run)
        
        # Print final performance report
        logger.info("\\n" + "=" * 70)
        logger.info("📊 FINAL PERFORMANCE REPORT")
        logger.info("=" * 70)
        
        perf = self.orchestrator.get_performance_summary()
        
        for strat_perf in perf['strategies']:
            if strat_perf['total_trades'] > 0:
                logger.info(f"\\n{strat_perf['strategy_name']}:")
                logger.info(f"  Trades: {strat_perf['total_trades']}")
                logger.info(f"  Win Rate: {strat_perf['win_rate']:.1f}%")
                logger.info(f"  Profit: ${strat_perf['total_profit']:+.2f}")
        
        combined = perf['combined']
        logger.info(f"\\nCOMBINED:")
        logger.info(f"  Total Trades: {combined['total_trades']}")
        logger.info(f"  Overall Win Rate: {combined['overall_win_rate']:.1f}%")
        logger.info(f"  Total Profit: ${combined['total_profit']:+.2f}")
        
        if self.paper_trader:
            logger.info("\\n" + self.paper_trader.get_detailed_report())
        
        logger.info("=" * 70)
        logger.info("✅ Bot stopped gracefully")
        sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Polymarket Multi-Strategy Trading Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in simulation mode without executing real trades"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Enable web dashboard at http://127.0.0.1:5000"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100.0,
        help="Starting capital (default: $100.00)"
    )
    
    args = parser.parse_args()
    
    try:
        bot = MultiStrategyBot(
            dry_run=args.dry_run or config.DRY_RUN,
            enable_dashboard=args.dashboard,
            starting_capital=args.capital
        )
        bot.start()
    except KeyboardInterrupt:
        logger.info("\\n👋 Exiting...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
