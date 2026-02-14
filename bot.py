"""
Main Bot Orchestrator - Coordinates market monitoring and trading strategy
"""
import argparse
import signal
import sys
import time
import threading
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

import config
from utils import setup_logger, PerformanceTracker
from market_monitor import MarketMonitor
from strategy import MakerStrategy
from bot_state import bot_state
import web_server

logger = setup_logger("PolymarketBot")


class PolymarketBot:
    """Main trading bot orchestrator"""
    
    def __init__(self, dry_run: bool = False, enable_dashboard: bool = False):
        self.dry_run = dry_run
        self.enable_dashboard = enable_dashboard
        self.running = False
        self.performance = PerformanceTracker()
        self.dashboard_thread = None
        
        # Initialize components
        logger.info("🚀 Initializing Polymarket Trading Bot...")
        bot_state.update_status("initializing")
        
        if dry_run:
            logger.info("⚠️  DRY RUN MODE - No real trades will be executed")
        
        # Initialize Polymarket CLOB client
        try:
            # Create API credentials
            # py-clob-client handles the L1/L2 authentication internally
            self.client = ClobClient(
                host=config.CLOB_API_URL,
                key=config.POLYGON_PRIVATE_KEY,
                chain_id=config.POLYGON_CHAIN_ID,
                signature_type=config.SIGNATURE_TYPE,
                funder=config.FUNDER_ADDRESS if config.FUNDER_ADDRESS else None
            )
            
            logger.info("✅ CLOB Client initialized")
            
            # Check if we need to approve tokens
            if not dry_run:
                logger.info("ℹ️  Make sure you have approved token allowances!")
                logger.info("   Run: python bot.py --approve-tokens")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize CLOB client: {e}")
            raise
        
        # Initialize market monitor and strategy
        self.market_monitor = MarketMonitor()
        self.strategy = MakerStrategy(self.client)
        
        # State tracking
        self.current_market = None
        self.last_heartbeat = time.time()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("✅ Bot initialized successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("\n🛑 Shutdown signal received...")
        self.stop()
    
    def start(self):
        """Start the main trading loop"""
        logger.info("=" * 60)
        logger.info("🤖 POLYMARKET MAKER MARKET MAKING BOT - PHASE 1")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  Order Size: ${config.ORDER_SIZE_USD}")
        logger.info(f"  Min Spread: ${config.MIN_SPREAD_TO_TRADE}")
        logger.info(f"  Max Positions: {config.MAX_OPEN_POSITIONS}")
        logger.info(f"  Position Timeout: {config.POSITION_TIMEOUT_SECONDS}s")
        if self.enable_dashboard:
            logger.info(f"  Dashboard: http://127.0.0.1:5000")
        logger.info("=" * 60)
        
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
            logger.error(f"❌ Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.stop()
    
    def _trading_cycle(self):
        """Execute one cycle of the trading loop"""
        try:
            # Heartbeat logging
            if time.time() - self.last_heartbeat > config.HEARTBEAT_INTERVAL:
                logger.info(f"💓 Heartbeat - Open positions: {len(self.strategy.open_positions)}")
                self.last_heartbeat = time.time()
            
            # 1. Check risk limits
            if self._check_risk_limits():
                logger.warning("⚠️  Risk limits reached, stopping trading")
                self.stop()
                return
            
            # 2. Find current active market
            if not self.current_market or not self.market_monitor.is_market_still_active(self.current_market):
                logger.info("🔍 Searching for active 5-minute Bitcoin market...")
                self.current_market = self.market_monitor.find_current_5min_btc_market()
                
                if not self.current_market:
                    logger.debug("No active market found, waiting...")
                    bot_state.update_status("waiting_for_market")
                    return
                
                logger.info(f"📊 Found market: {self.current_market.get('question', 'Unknown')}")
                bot_state.update_market(self.current_market)
                bot_state.update_status("trading")
            
            # 3. Get market tokens
            yes_token, no_token = self.market_monitor.get_market_tokens(self.current_market)
            if not yes_token or not no_token:
                logger.error("Could not extract token IDs from market")
                self.current_market = None
                return
            
            # 4. Monitor existing positions
            closed = self.strategy.monitor_positions(dry_run=self.dry_run)
            for position_id in closed:
                # In a real implementation, we'd track actual P&L here
                if self.dry_run:
                    self.performance.record_trade(2.0)  # Simulate profit
            
            # 5. Analyze new opportunity
            if len(self.strategy.open_positions) < config.MAX_OPEN_POSITIONS:
                signal = self.strategy.analyze_opportunity(yes_token, no_token)
                
                if signal:
                    bot_state.update_spread(signal)
                    bot_state.log_opportunity(signal)
                    
                    # 6. Place maker orders
                    position_id = self.strategy.place_maker_orders(signal, dry_run=self.dry_run)
                    if position_id:
                        logger.info(f"📈 Position {position_id} created")
                        bot_state.add_position({"position_id": position_id, "signal": signal})
            
        except Exception as e:
            error_msg = f"Error in trading cycle: {e}"
            logger.error(error_msg, exc_info=True)
            bot_state.add_error(error_msg)
    
    def _check_risk_limits(self) -> bool:
        """
        Check if any risk limits have been reached
        
        Returns:
            True if limits reached, False otherwise
        """
        # Check daily loss limit
        if config.DAILY_LOSS_LIMIT and self.performance.net_profit < -config.DAILY_LOSS_LIMIT:
            logger.warning(f"Daily loss limit reached: {self.performance.net_profit:.2f}")
            return True
        
        # Check daily profit target
        if config.DAILY_PROFIT_TARGET and self.performance.net_profit >= config.DAILY_PROFIT_TARGET:
            logger.info(f"Daily profit target reached: {self.performance.net_profit:.2f}")
            return True
        
        return False
    
    def stop(self):
        """Stop the bot gracefully"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping bot...")
        self.running = False
        
        # Cancel all open orders
        self.strategy.cancel_all_orders(dry_run=self.dry_run)
        
        # Print performance summary
        logger.info(self.performance.get_summary())
        
        logger.info("✅ Bot stopped gracefully")
        sys.exit(0)
    
    def approve_tokens(self):
        """Approve token allowances for trading (one-time setup)"""
        try:
            logger.info("🔐 Approving token allowances...")
            
            # Use py-clob-client's built-in allowance methods
            # This needs to be called before first trade
            logger.info("Approving USDC allowance...")
            self.client.set_approval_amount()
            
            logger.info("✅ Allowances approved successfully")
            logger.info("You can now run the bot with: python bot.py")
            
        except Exception as e:
            logger.error(f"❌ Error approving allowances: {e}")
            logger.error("Make sure your wallet has USDC on Polygon network")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Polymarket 5-min Bitcoin Maker Market Making Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in simulation mode without executing real trades"
    )
    parser.add_argument(
        "--approve-tokens",
        action="store_true",
        help="Approve token allowances (one-time setup)"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Enable web dashboard at http://127.0.0.1:5000"
    )
    
    args = parser.parse_args()
    
    try:
        bot = PolymarketBot(
            dry_run=args.dry_run or config.DRY_RUN,
            enable_dashboard=args.dashboard
        )
        
        if args.approve_tokens:
            bot.approve_tokens()
        else:
            bot.start()
            
    except KeyboardInterrupt:
        logger.info("\n👋 Exiting...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
