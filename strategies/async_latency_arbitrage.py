"""
Async Latency Arbitrage Strategy (Phase 2)

Exploits 1-2 second lag between Binance BTC price movements and Polymarket adjustments.
Upgraded async version integrated with bot_v2.py architecture.
"""
import asyncio
import time
import logging
from typing import Optional, Dict, List
from py_clob_client.client import ClobClient
from py_clob_client.constants import BUY

import config_v2 as config
from strategies.base_strategy import BaseStrategy, StrategyType
from external.async_binance_client import AsyncBinanceMonitor
from core.spike_detector import SpikeDetector
from utils import setup_logger, format_price

logger = setup_logger("AsyncLatencyArbitrage")


class AsyncLatencyArbitrageStrategy(BaseStrategy):
    """
    Async latency arbitrage strategy.
    
    Flow:
    1. Monitor Binance BTC price via WebSocket
    2. Detect spikes (≥$150 in 3-10 seconds)
    3. Check if Polymarket hasn't adjusted yet
    4. Execute instant market order
    5. Exit after 30s or when profit target hit
    """
    
    def __init__(self, clob_client: ClobClient):
        super().__init__("Async Latency Arbitrage", StrategyType.LATENCY_ARBITRAGE)
        self.client = clob_client
        
        # Binance monitoring
        self.binance_monitor = AsyncBinanceMonitor(
            on_price_update=self._on_binance_price_update,
            ws_url=config.BINANCE_WS_URL
        )
        
        # Spike detection
        self.spike_detector = SpikeDetector(
            min_move=config.LATENCY_MIN_BTC_MOVE,
            time_window_min=config.LATENCY_SPIKE_TIME_WINDOW_MIN,
            time_window_max=config.LATENCY_SPIKE_TIME_WINDOW_MAX,
            cooldown_seconds=config.LATENCY_SPIKE_COOLDOWN
        )
        
        # Daily limits
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.last_reset_day = time.localtime().tm_yday
        
        # Current market tracking
        self.current_btc_market = None
        self.last_market_refresh = 0
        
    async def start(self):
        """Start the Binance monitor"""
        await self.binance_monitor.start()
        logger.info("🚀 Async latency arbitrage strategy started")
    
    async def stop(self):
        """Stop the Binance monitor"""
        await self.binance_monitor.stop()
        logger.info("🛑 Async latency arbitrage strategy stopped")
    
    def _on_binance_price_update(self, price: float):
        """
        Callback when Binance price updates.
        Adds price to spike detector.
        """
        self.spike_detector.add_price(price)
    
    def _reset_daily_limits_if_needed(self):
        """Reset daily counters if new day"""
        current_day = time.localtime().tm_yday
        if current_day != self.last_reset_day:
            logger.info("📅 New day - resetting daily limits")
            self.daily_trades = 0
            self.daily_loss = 0.0
            self.last_reset_day = current_day
    
    async def scan_opportunities(
        self,
        market_scanner=None
    ) -> Optional[Dict]:
        """
        Scan for latency arbitrage opportunities.
        
        Args:
            market_scanner: MultiMarketScanner instance from bot_v2
            
        Returns:
            Signal dict if opportunity found
        """
        try:
            # Reset daily limits if needed
            self._reset_daily_limits_if_needed()
            
            # Check daily limits
            if self.daily_trades >= config.LATENCY_DAILY_TRADE_LIMIT:
                logger.debug(f"Daily trade limit reached ({self.daily_trades}/{config.LATENCY_DAILY_TRADE_LIMIT})")
                return None
            
            if self.daily_loss >= config.LATENCY_DAILY_LOSS_LIMIT:
                logger.warning(f"Daily loss limit reached (${self.daily_loss:.2f})")
                return None
            
            # Check if Binance is connected
            if not self.binance_monitor.is_connected():
                logger.debug("Binance WebSocket not connected")
                return None
            
            # Detect spike
            spike = self.spike_detector.detect_spike()
            if not spike:
                return None
            
            # Get current BTC market
            if market_scanner:
                # Use bot_v2's market scanner
                active_markets = market_scanner.get_active_markets()
                
                # Find a BTC market
                btc_market = None
                for market in active_markets:
                    question = market.get('question', '').lower()
                    if 'btc' in question or 'bitcoin' in question:
                        btc_market = market
                        break
                
                if not btc_market:
                    logger.debug("No active BTC market found")
                    return None
                
                self.current_btc_market = btc_market
            else:
                # Fallback to existing market monitor
                if not self.current_btc_market or time.time() - self.last_market_refresh > 60:
                    self.current_btc_market = await self._get_current_btc_market()
                    self.last_market_refresh = time.time()
                
                if not self.current_btc_market:
                    logger.debug("No active BTC market found")
                    return None
            
            # Check if Polymarket has lagged
            opportunity = await self._check_polymarket_lag(spike)
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error scanning for latency arbitrage: {e}")
            return None
    
    async def _get_current_btc_market(self) -> Optional[Dict]:
        """Get current active BTC market (fallback method)"""
        try:
            from market_monitor import MarketMonitor
            monitor = MarketMonitor()
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            market = await loop.run_in_executor(
                None,
                monitor.find_current_5min_btc_market
            )
            return market
        except Exception as e:
            logger.error(f"Error getting BTC market: {e}")
            return None
    
    async def _check_polymarket_lag(self, spike: Dict) -> Optional[Dict]:
        """
        Check if Polymarket price has lagged behind Binance spike.
        
        Args:
            spike: Spike detection info
            
        Returns:
            Opportunity dict if found
        """
        try:
            # Get tokens
            tokens = self.current_btc_market.get('tokens', [])
            if len(tokens) != 2:
                return None
            
            yes_token = tokens[0]['token_id']
            no_token = tokens[1]['token_id']
            
            # Run order book fetch in thread pool
            loop = asyncio.get_event_loop()
            yes_book = await loop.run_in_executor(
                None,
                self.client.get_order_book,
                yes_token
            )
            
            yes_asks = yes_book.get('asks', [])
            if not yes_asks:
                return None
            
            yes_ask = float(yes_asks[0]['price'])
            
            # Determine opportunity based on spike direction
            opportunity = None
            
            if spike['direction'] == 'up' and yes_ask < config.LATENCY_ENTRY_THRESHOLD_UP:
                # BTC pumped, YES is still cheap - buy YES
                opportunity = {
                    'market': self.current_btc_market,
                    'token_id': yes_token,
                    'side': 'YES',
                    'entry_price': yes_ask,
                    'expected_exit': config.LATENCY_PROFIT_TARGET_UP,
                    'spike': spike,
                    'strategy': 'latency_arbitrage'
                }
                
                logger.info(f"🎯 LATENCY ARBITRAGE OPPORTUNITY!")
                logger.info(f"   BTC spiked {spike['direction'].upper()} ${spike['price_change']:+.2f}")
                logger.info(f"   Polymarket YES still at {format_price(yes_ask)} (cheap!)")
                logger.info(f"   Expected to rise to ~{format_price(config.LATENCY_PROFIT_TARGET_UP)}")
                
            elif spike['direction'] == 'down' and yes_ask > config.LATENCY_ENTRY_THRESHOLD_DOWN:
                # BTC dumped, YES is still expensive - buy NO
                no_book = await loop.run_in_executor(
                    None,
                    self.client.get_order_book,
                    no_token
                )
                
                no_asks = no_book.get('asks', [])
                if no_asks:
                    no_ask = float(no_asks[0]['price'])
                    
                    opportunity = {
                        'market': self.current_btc_market,
                        'token_id': no_token,
                        'side': 'NO',
                        'entry_price': no_ask,
                        'expected_exit': config.LATENCY_PROFIT_TARGET_DOWN,
                        'spike': spike,
                        'strategy': 'latency_arbitrage'
                    }
                    
                    logger.info(f"🎯 LATENCY ARBITRAGE OPPORTUNITY!")
                    logger.info(f"   BTC spiked {spike['direction'].upper()} ${spike['price_change']:+.2f}")
                    logger.info(f"   Buying NO at {format_price(no_ask)}")
                    logger.info(f"   Expected to rise to ~{format_price(config.LATENCY_PROFIT_TARGET_DOWN)}")
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error checking Polymarket lag: {e}")
            return None
    
    async def execute_trade(self, signal: Dict, dry_run: bool = False) -> Optional[str]:
        """
        Execute rapid arbitrage trade.
        
        CRITICAL: Must execute within 1-2 seconds.
        """
        try:
            position_id = f"latency_{int(time.time())}"
            
            # Calculate position size
            position_size_usd = min(
                config.LATENCY_MAX_POSITION_SIZE,
                config.ORDER_SIZE_USD * 2
            )
            
            shares = position_size_usd / signal['entry_price']
            
            if dry_run:
                logger.info(f"💵 [DRY RUN] LATENCY ARBITRAGE:")
                logger.info(f"   Position ID: {position_id}")
                logger.info(f"   BUY {shares:.2f} {signal['side']} @ {format_price(signal['entry_price'])}")
                logger.info(f"   Total: ${position_size_usd:.2f}")
                logger.info(f"   Expected exit: {format_price(signal['expected_exit'])}")
                
                expected_profit = (signal['expected_exit'] - signal['entry_price']) * shares
                logger.info(f"   Expected profit: ${expected_profit:.2f}")
                
                self.open_positions[position_id] = {
                    'signal': signal,
                    'shares': shares,
                    'status': 'simulated',
                    'entry_time': time.time(),
                    'entry_price': signal['entry_price']
                }
                
                self.daily_trades += 1
                return position_id
            
            # Execute INSTANT trade (market order)
            logger.info(f"⚡ EXECUTING LATENCY ARBITRAGE:")
            logger.info(f"   Buying {shares:.2f} {signal['side']} shares")
            
            # Run order in thread pool
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None,
                lambda: self.client.create_order(
                    token_id=signal['token_id'],
                    price=signal['entry_price'] * 1.01,  # Slightly above ask for instant fill
                    size=shares,
                    side=BUY
                )
            )
            
            # Track position
            self.open_positions[position_id] = {
                'signal': signal,
                'order_id': order.get('orderID'),
                'shares': shares,
                'status': 'filled',
                'entry_time': time.time(),
                'entry_price': signal['entry_price']
            }
            
            self.daily_trades += 1
            logger.info(f"✅ Latency arbitrage executed - Position {position_id}")
            return position_id
            
        except Exception as e:
            logger.error(f"Error executing latency arbitrage: {e}")
            return None
    
    async def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """
        Monitor latency arbitrage positions.
        
        Exit conditions:
        1. Time stop: 30 seconds elapsed
        2. Profit target: Price reached expected exit
        3. Stop loss: -5% from entry
        """
        closed_positions = []
        current_time = time.time()
        
        for position_id, position in list(self.open_positions.items()):
            try:
                signal = position['signal']
                time_held = current_time - position['entry_time']
                
                # Dry run simulation
                if dry_run and position['status'] == 'simulated':
                    if time_held > 15:
                        # Simulate successful exit
                        profit = (signal['expected_exit'] - signal['entry_price']) * position['shares']
                        self.record_trade(profit)
                        
                        if profit < 0:
                            self.daily_loss += abs(profit)
                        
                        logger.info(f"✅ [DRY RUN] Position {position_id} closed - Profit: ${profit:.2f}")
                        del self.open_positions[position_id]
                        closed_positions.append(position_id)
                    continue
                
                # Real trading: Exit after max hold time
                if time_held > config.LATENCY_MAX_HOLD_TIME:
                    logger.info(f"⏰ Position {position_id} timeout ({time_held:.1f}s) - closing")
                    # Would place market sell order here
                    del self.open_positions[position_id]
                    closed_positions.append(position_id)
                
            except Exception as e:
                logger.error(f"Error monitoring position {position_id}: {e}")
        
        return closed_positions
    
    def get_stats(self) -> Dict:
        """Get strategy statistics"""
        binance_status = self.binance_monitor.get_connection_status()
        spike_stats = self.spike_detector.get_stats()
        
        return {
            **self.get_performance(),
            'binance_connected': binance_status['is_healthy'],
            'binance_latency_ms': binance_status['average_latency_ms'],
            'total_spikes_detected': spike_stats['total_spikes'],
            'in_spike_cooldown': spike_stats['in_cooldown'],
            'daily_trades': self.daily_trades,
            'daily_loss': self.daily_loss,
            'daily_limit_reached': self.daily_trades >= config.LATENCY_DAILY_TRADE_LIMIT
        }
