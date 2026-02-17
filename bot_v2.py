"""
Polymarket Trading Bot V2 - Async Multi-Strategy Orchestrator

Upgraded version with:
- Real-time WebSocket market data (with REST fallback)
- Multi-market monitoring (20+ markets simultaneously)
- Async/await architecture for concurrent operations
- Event-driven order execution
- <100ms latency for market updates
"""
import asyncio
import argparse
import sys
import logging
from typing import List, Dict
from py_clob_client.client import ClobClient

import config
import config_v2
from utils import setup_logger, PerformanceTracker
from bot_state import bot_state
from strategy import MakerStrategy
from strategies.async_adapter import AsyncStrategyAdapter
from strategies.async_latency_arbitrage import AsyncLatencyArbitrageStrategy
from core.websocket_manager import WebSocketManager
from core.market_scanner import MultiMarketScanner
from core.event_loop import EventLoopManager
from core.connection_pool import ConnectionPool

logger = setup_logger("PolymarketBotV2")


class PolymarketBotV2:
    """
    Async multi-strategy trading bot orchestrator.
    
    Features:
    - WebSocket real-time data with REST fallback
    - Multi-market scanning and monitoring
    - Event-driven strategy execution
    - Concurrent position management
    - Graceful shutdown handling
    """
    
    def __init__(self, dry_run: bool = False, enable_dashboard: bool = False):
        """
        Initialize bot V2.
        
        Args:
            dry_run: If True, simulate trades without executing
            enable_dashboard: If True, start web dashboard
        """
        self.dry_run = dry_run
        self.enable_dashboard = enable_dashboard
        self.running = False
        self.performance = PerformanceTracker()
        
        logger.info("🚀 Initializing Polymarket Trading Bot V2...")
        bot_state.update_status("initializing")
        
        if dry_run:
            logger.info("⚠️  DRY RUN MODE - No real trades will be executed")
        
        # Initialize CLOB client
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
        
        # Initialize core infrastructure
        self.event_loop_manager = EventLoopManager()
        self.connection_pool = ConnectionPool()
        
        # Initialize WebSocket manager
        # Note: Polymarket WebSocket URL may need adjustment based on actual API
        ws_url = getattr(config, 'POLYMARKET_WS_URL', 'wss://ws-subscriptions-clob.polymarket.com/ws/market')
        
        self.websocket_manager = WebSocketManager(
            ws_url=ws_url,
            rest_api_url=config.CLOB_API_URL,
            on_message=self._handle_market_update,
            reconnect_delay=getattr(config, 'WS_RECONNECT_DELAY', 5),
            max_reconnect_attempts=getattr(config, 'WS_MAX_RECONNECT_ATTEMPTS', 10),
            ping_interval=getattr(config, 'WS_PING_INTERVAL', 30)
        )
        
        # Initialize market scanner
        self.market_scanner = MultiMarketScanner(
            gamma_api_url=config.GAMMA_API_URL,
            keywords=getattr(config, 'MARKET_KEYWORDS_EXTENDED', config.MARKET_KEYWORDS),
            exclude_keywords=config.EXCLUDE_KEYWORDS,
            max_markets=getattr(config, 'MAX_CONCURRENT_MARKETS', 25),
            scan_interval=getattr(config, 'MARKET_SCAN_INTERVAL', 10),
            min_time_remaining=config.MIN_TIME_REMAINING_TO_TRADE
        )
        
        # Initialize strategies
        self.strategies: List[AsyncStrategyAdapter] = []
        self._init_strategies()
        
        # Register connections with pool
        self.connection_pool.register_connection("websocket", self.websocket_manager)
        self.connection_pool.register_connection("market_scanner", self.market_scanner)
        
        # Register event handlers
        self.event_loop_manager.register_event_handler("market_update", self._on_market_update)
        self.event_loop_manager.register_event_handler("new_market", self._on_new_market)
        
        # Register shutdown callbacks
        self.event_loop_manager.register_shutdown_callback(self.shutdown)
        
        logger.info("✅ Bot V2 initialized successfully")
    
    def _init_strategies(self):
        """Initialize trading strategies"""
        # Strategy 1: Maker Market Making (Phase 1)
        maker_strategy = MakerStrategy(self.client)
        async_maker = AsyncStrategyAdapter(maker_strategy)
        self.strategies.append(async_maker)
        
        # Strategy 2: Latency Arbitrage (Phase 2)
        latency_arb_strategy = AsyncLatencyArbitrageStrategy(self.client)
        self.strategies.append(latency_arb_strategy)
        self.latency_arb_strategy = latency_arb_strategy  # Keep reference for Binance monitoring
        
        logger.info(f"✅ Initialized {len(self.strategies)} strategies")
    
    async def start(self):
        """Start the async trading bot"""
        logger.info("=" * 60)
        logger.info("🤖 POLYMARKET TRADING BOT V2 - ASYNC MULTI-STRATEGY")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  Order Size: ${config.ORDER_SIZE_USD}")
        logger.info(f"  Min Spread: ${config.MIN_SPREAD_TO_TRADE}")
        logger.info(f"  Max Positions: {config.MAX_OPEN_POSITIONS}")
        logger.info(f"  Max Markets: {getattr(config, 'MAX_CONCURRENT_MARKETS', 25)}")
        logger.info(f"  Target Latency: <{getattr(config, 'TARGET_LATENCY_MS', 100)}ms")
        if self.enable_dashboard:
            logger.info(f"  Dashboard: http://127.0.0.1:5000")
        logger.info("=" * 60)
        
        self.running = True
        bot_state.update_status("running")
        
        try:
            # Start core infrastructure
            await self.websocket_manager.start()
            await self.market_scanner.start()
            
            # Start latency arbitrage Binance monitor
            if hasattr(self, 'latency_arb_strategy'):
                await self.latency_arb_strategy.start()
                logger.info("✅ Binance monitor started for latency arbitrage")
            
            # Start dashboard if enabled
            if self.enable_dashboard:
                await self._start_dashboard()
            
            # Start main trading loops
            await asyncio.gather(
                self._market_discovery_loop(),
                self._strategy_execution_loop(),
                self._position_monitoring_loop(),
                self._health_monitoring_loop()
            )
            
        except Exception as e:
            logger.error(f"❌ Fatal error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def _market_discovery_loop(self):
        """Continuously discover and subscribe to new markets"""
        logger.info("🔍 Starting market discovery loop...")
        
        while self.running:
            try:
                # Scanner runs its own loop, we just need to handle new markets
                active_markets = self.market_scanner.get_active_markets()
                
                # Subscribe to WebSocket updates for each market
                for market in active_markets:
                    market_id = market.get("id")
                    tokens = self.market_scanner.get_market_tokens(market_id)
                    
                    if tokens:
                        yes_token, no_token = tokens
                        # Subscribe to both tokens
                        await self.websocket_manager.subscribe_market(yes_token)
                        await self.websocket_manager.subscribe_market(no_token)
                
                # Emit new market events
                for market in active_markets:
                    await self.event_loop_manager.emit_event("new_market", {"market": market})
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in market discovery loop: {e}")
                await asyncio.sleep(10)
    
    async def _strategy_execution_loop(self):
        """Execute trading strategies on all active markets"""
        logger.info("📈 Starting strategy execution loop...")
        
        while self.running:
            try:
                # Check if we can execute (circuit breaker)
                if not self.connection_pool.can_execute():
                    logger.warning("⚠️  Circuit breaker open, skipping execution")
                    await asyncio.sleep(5)
                    continue
                
                # Get all active markets
                active_markets = self.market_scanner.get_active_markets()
                
                # Execute strategies on each market
                tasks = []
                for market in active_markets:
                    market_id = market.get("id")
                    tokens = self.market_scanner.get_market_tokens(market_id)
                    
                    if tokens:
                        yes_token, no_token = tokens
                        # Run all strategies on this market
                        for strategy in self.strategies:
                            if strategy.enabled:
                                task = self._execute_strategy_on_market(
                                    strategy, market, yes_token, no_token
                                )
                                tasks.append(task)
                
                # Execute all strategy checks concurrently
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # Wait before next execution cycle
                await asyncio.sleep(config.LOOP_SLEEP_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in strategy execution loop: {e}")
                await asyncio.sleep(5)
    
    async def _execute_strategy_on_market(
        self,
        strategy: AsyncStrategyAdapter,
        market: Dict,
        yes_token: str,
        no_token: str
    ):
        """
        Execute a single strategy on a market.
        
        Args:
            strategy: Strategy to execute
            market: Market data
            yes_token: YES token ID
            no_token: NO token ID
        """
        try:
            # Check if strategy has room for more positions
            if len(strategy.open_positions) >= config.MAX_OPEN_POSITIONS:
                return
            
            # Analyze opportunity
            # For MakerStrategy (wrapped in adapter), call analyze_opportunity directly
            if hasattr(strategy, 'sync_strategy') and hasattr(strategy.sync_strategy, 'analyze_opportunity'):
                loop = asyncio.get_event_loop()
                signal = await loop.run_in_executor(
                    strategy.executor,
                    lambda: strategy.sync_strategy.analyze_opportunity(yes_token, no_token)
                )
            # For async strategies like latency arbitrage, pass market scanner
            elif isinstance(strategy, AsyncLatencyArbitrageStrategy):
                signal = await strategy.scan_opportunities(market_scanner=self.market_scanner)
            else:
                signal = await strategy.scan_opportunities()
            
            if signal:
                # Execute trade
                position_id = await strategy.execute_trade(signal, dry_run=self.dry_run)
                
                if position_id:
                    logger.info(f"📈 Position {position_id} created by {strategy.name}")
                    bot_state.add_position({"position_id": position_id, "signal": signal})
                    self.connection_pool.record_success("strategy_execution")
                    
        except Exception as e:
            logger.error(f"Error executing strategy {strategy.name}: {e}")
            self.connection_pool.record_error("strategy_execution")
    
    async def _position_monitoring_loop(self):
        """Monitor and manage open positions"""
        logger.info("👀 Starting position monitoring loop...")
        
        while self.running:
            try:
                # Monitor positions for all strategies
                for strategy in self.strategies:
                    closed = await strategy.monitor_positions(dry_run=self.dry_run)
                    
                    for position_id in closed:
                        # Record performance
                        if self.dry_run:
                            self.performance.record_trade(2.0)  # Simulate profit
                        
                # Wait before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in position monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _health_monitoring_loop(self):
        """Monitor connection health and performance"""
        logger.info("💓 Starting health monitoring loop...")
        
        while self.running:
            try:
                # Check WebSocket health
                ws_status = self.websocket_manager.get_connection_status()
                avg_latency = ws_status.get("average_latency_ms", 0)
                
                if avg_latency > 0:
                    self.connection_pool.record_latency("websocket", avg_latency)
                
                # Check market scanner health
                scanner_stats = self.market_scanner.get_stats()
                
                # Log health status
                health = self.connection_pool.get_health_status()
                logger.info(f"💓 Health: {health['state']} | "
                           f"Markets: {scanner_stats['active_markets']} | "
                           f"Latency: {avg_latency:.1f}ms | "
                           f"Mode: {ws_status['mode']}")
                
                # Update bot state
                bot_state.update_status(f"healthy_{health['state']}")
                
                # Wait before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _handle_market_update(self, message: Dict):
        """
        Handle incoming market update from WebSocket.
        
        Args:
            message: Market update message
        """
        try:
            # Emit market update event
            await self.event_loop_manager.emit_event("market_update", message)
        except Exception as e:
            logger.error(f"Error handling market update: {e}")
    
    async def _on_market_update(self, event_data: Dict):
        """
        Handle market update event.
        
        Args:
            event_data: Event data with market update
        """
        # This is where strategies can react to real-time price changes
        # For now, we'll let the strategy execution loop handle it
        pass
    
    async def _on_new_market(self, event_data: Dict):
        """
        Handle new market discovery event.
        
        Args:
            event_data: Event data with new market
        """
        market = event_data.get("market")
        if market:
            logger.info(f"📊 New market discovered: {market.get('question', 'Unknown')[:60]}")
            bot_state.update_market(market)
    
    async def _start_dashboard(self):
        """Start web dashboard in background"""
        try:
            import web_server
            import threading
            
            dashboard_thread = threading.Thread(
                target=web_server.run_dashboard,
                daemon=True
            )
            dashboard_thread.start()
            logger.info("🌐 Dashboard server started at http://127.0.0.1:5000")
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the bot"""
        if not self.running:
            return
        
        logger.info("🛑 Shutting down bot...")
        self.running = False
        
        # Cancel all orders
        for strategy in self.strategies:
            await strategy.cancel_all_orders(dry_run=self.dry_run)
        
        # Stop infrastructure
        await self.websocket_manager.stop()
        await self.market_scanner.stop()
        
        # Stop latency arbitrage Binance monitor
        if hasattr(self, 'latency_arb_strategy'):
            await self.latency_arb_strategy.stop()
        
        # Shutdown adapters
        for strategy in self.strategies:
            if hasattr(strategy, 'shutdown'):
                await strategy.shutdown()
        
        # Print performance summary
        logger.info(self.performance.get_summary())
        
        logger.info("✅ Bot shutdown complete")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Polymarket Multi-Strategy Trading Bot V2")
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
        "--test-ws",
        action="store_true",
        help="Test WebSocket connection and exit"
    )
    parser.add_argument(
        "--scan-markets",
        action="store_true",
        help="Scan markets and exit"
    )
    
    args = parser.parse_args()
    
    try:
        bot = PolymarketBotV2(
            dry_run=args.dry_run or config.DRY_RUN,
            enable_dashboard=args.dashboard
        )
        
        if args.test_ws:
            # Test WebSocket connection
            logger.info("Testing WebSocket connection...")
            await bot.websocket_manager.start()
            await asyncio.sleep(10)
            status = bot.websocket_manager.get_connection_status()
            logger.info(f"WebSocket Status: {status}")
            await bot.websocket_manager.stop()
            return
        
        if args.scan_markets:
            # Test market scanning
            logger.info("Scanning markets...")
            await bot.market_scanner.start()
            await asyncio.sleep(15)
            markets = bot.market_scanner.get_active_markets()
            logger.info(f"Found {len(markets)} active markets:")
            for market in markets[:10]:  # Show first 10
                logger.info(f"  - {market.get('question', 'Unknown')}")
            await bot.market_scanner.stop()
            return
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("\n👋 Exiting...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
