"""
Paper Trading Bot - Enhanced dry-run mode with virtual capital tracking

This wraps the existing bot with paper trading simulation:
- Starts with $100 virtual capital
- Uses LIVE market data
- Simulates realistic order fills  
- Tracks P&L as if trading real money
- Updates dashboard with performance

Usage: python3 bot_paper.py --dashboard
"""
import argparse
import signal
import sys
import time
import threading
from py_clob_client.client import ClobClient

import config
from utils import setup_logger
from market_monitor import MarketMonitor
from bot_state import bot_state
import web_server
from paper_trading import init_paper_trading, get_paper_trader

logger = setup_logger("PaperTradingBot")


class PaperTradingBot:
    """
    Bot that uses live market data but simulates all trades with virtual capital.
    Perfect for testing strategy effectiveness before risking real money.
    """
    
    def __init__(self, enable_dashboard: bool = False, starting_capital: float = 100.0):
        self.enable_dashboard = enable_dashboard
        self.running = False
        self.dashboard_thread = None
        
        # Initialize paper trading simulator
        self.paper_trader = init_paper_trading(starting_capital)
        
        logger.info("🚀 Initializing Paper Trading Bot...")
        logger.info(f"💰 Starting Capital: ${starting_capital:.2f} (VIRTUAL)")
        bot_state.update_status("initializing")
        
        # Initialize Polymarket client (read-only access for market data)
        try:
            self.client = ClobClient(
                host=config.CLOB_API_URL,
                key=config.POLYGON_PRIVATE_KEY,
                chain_id=config.POLYGON_CHAIN_ID,
                signature_type=config.SIGNATURE_TYPE,
                funder=config.FUNDER_ADDRESS if config.FUNDER_ADDRESS else None
            )
            logger.info("✅ Connected to Polymarket (read-only)")
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            raise
        
        # Initialize market monitor
        self.market_monitor = MarketMonitor()
        
        # State tracking
        self.current_market = None
        self.last_heartbeat = time.time()
        self.cycle_count = 0
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("✅ Paper Trading Bot initialized")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info("\n🛑 Shutdown signal received...")
        self.stop()
    
    def start(self):
        """Start the paper trading loop"""
        logger.info("=" * 70)
        logger.info("📊 POLYMARKET PAPER TRADING BOT - $100 VIRTUAL CAPITAL")
        logger.info("=" * 70)
        logger.info(f"Configuration:")
        logger.info(f"  Starting Capital: ${self.paper_trader.starting_capital:.2f} (VIRTUAL)")
        logger.info(f"  Order Size: ${config.ORDER_SIZE_USD}")
        logger.info(f"  Min Spread: ${config.MIN_SPREAD_TO_TRADE}")
        logger.info(f"  Max Positions: {config.MAX_OPEN_POSITIONS}")
        if self.enable_dashboard:
            logger.info(f"  Dashboard: http://127.0.0.1:5000")
        logger.info("=" * 70)
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
        """Execute one cycle of paper trading"""
        try:
            self.cycle_count += 1
            
            # Heartbeat
            if time.time() - self.last_heartbeat > config.HEARTBEAT_INTERVAL:
                stats = self.paper_trader.get_performance_summary()
                logger.info(
                    f"💓 Heartbeat | Capital: ${stats['current_capital']:.2f} | "
                    f"P&L: ${stats['total_profit']:+.2f} | "
                    f"Trades: {stats['total_trades']} | "
                    f"Open: {stats['open_orders']}"
                )
                self.last_heartbeat = time.time()
            
            # Find active market
            if not self.current_market or not self.market_monitor.is_market_still_active(self.current_market):
                logger.info("🔍 Searching for active 5-minute Bitcoin market...")
                self.current_market = self.market_monitor.find_current_5min_btc_market()
                
                if not self.current_market:
                    logger.debug("No active market found")
                    bot_state.update_status("waiting_for_market")
                    return
                
                logger.info(f"📊 Found market: {self.current_market.get('question', 'Unknown')}")
                bot_state.update_market(self.current_market)
                bot_state.update_status("trading")
            
            # Get market tokens
            yes_token, no_token = self.market_monitor.get_market_tokens(self.current_market)
            if not yes_token or not no_token:
                logger.error("Could not extract token IDs")
                self.current_market = None
                return
            
            # Get order books
            yes_book = self.client.get_order_book(yes_token)
            no_book = self.client.get_order_book(no_token)
            
            # Calculate spread
            spread_data = self.market_monitor.calculate_spread_opportunity(yes_book, no_book)
            
            if spread_data and spread_data['spread'] >= config.MIN_SPREAD_TO_TRADE:
                bot_state.update_spread(spread_data)
                
                # Check if we can place new orders
                if (len(self.paper_trader.open_orders) < config.MAX_OPEN_POSITIONS and 
                    self.paper_trader.can_place_order(config.ORDER_SIZE_USD * 2)):
                    
                    # Calculate optimal prices
                    yes_price = spread_data['yes_bid'] + config.PRICE_IMPROVEMENT_OFFSET
                    no_price = spread_data['no_bid'] + config.PRICE_IMPROVEMENT_OFFSET
                    
                    # Simulate placing orders
                    position_id = f"pos_{int(time.time())}"
                    
                    self.paper_trader.simulate_order_placement(
                        position_id=position_id,
                        side='YES',
                        price=yes_price,
                        size_usd=config.ORDER_SIZE_USD,
                        market_info=self.current_market
                    )
                    
                    self.paper_trader.simulate_order_placement(
                        position_id=position_id,
                        side='NO',
                        price=no_price,
                        size_usd=config.ORDER_SIZE_USD,
                        market_info=self.current_market
                    )
                    
                    bot_state.add_position({
                        "position_id": position_id,
                        "signal": spread_data
                    })
            
            # Simulate fills based on market conditions
            filled = self.paper_trader.simulate_market_fills({'spread': spread_data})
            
            # Cancel stale orders
            cancelled = self.paper_trader.cancel_stale_orders(config.POSITION_TIMEOUT_SECONDS)
            
            # Update dashboard with latest performance
            self._update_dashboard_performance()
            
        except Exception as e:
            error_msg = f"Error in trading cycle: {e}"
            logger.error(error_msg, exc_info=True)
            bot_state.add_error(error_msg)
    
    def _update_dashboard_performance(self):
        """Update dashboard with paper trading performance"""
        stats = self.paper_trader.get_performance_summary()
        
        # Update bot_state with paper trading stats
        bot_state.state['performance']['total_trades'] = stats['total_trades']
        bot_state.state['performance']['winning_trades'] = stats['winning_trades']
        bot_state.state['performance']['losing_trades'] = stats['losing_trades']
        bot_state.state['performance']['net_profit'] = stats['total_profit']
        bot_state.state['performance']['win_rate'] = stats['win_rate'] / 100
        
        # Add capital info
        bot_state.state['paper_trading'] = {
            'starting_capital': stats['starting_capital'],
            'current_capital': stats['current_capital'],
            'profit_percentage': stats['profit_percentage']
        }
    
    def stop(self):
        """Stop the bot and show final report"""
        if not self.running:
            return
        
        logger.info("🛑 Stopping paper trading bot...")
        self.running = False
        
        # Print final performance report
        logger.info("\n" + self.paper_trader.get_detailed_report())
        
        logger.info("✅ Paper trading session ended")
        sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Polymarket Paper Trading Bot")
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Enable web dashboard at http://127.0.0.1:5000"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100.0,
        help="Starting virtual capital (default: $100.00)"
    )
    
    args = parser.parse_args()
    
    try:
        bot = PaperTradingBot(
            enable_dashboard=args.dashboard,
            starting_capital=args.capital
        )
        bot.start()
    except KeyboardInterrupt:
        logger.info("\n👋 Exiting...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
