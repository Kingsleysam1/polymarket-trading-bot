"""
Strategy 2: Latency Arbitrage (Binance → Polymarket)

Detects when BTC price moves significantly on Binance before Polymarket adjusts,
allowing for rapid arbitrage execution within 1-2 seconds.
"""
from typing import Optional, Dict, List
import time
from py_clob_client.client import ClobClient

import config
from strategies.base_strategy import BaseStrategy, StrategyType
from external.binance_client import BinanceMonitor
from utils import setup_logger, format_price

logger = setup_logger("LatencyArbitrage")


class LatencyArbitrageStrategy(BaseStrategy):
    """
    Monitors Binance BTC price and executes rapid trades on Polymarket
    when detecting price lag.
    
    Key concept: When BTC pumps/dumps $200+ on Binance, Polymarket takes
    1-2 seconds to adjust. We buy YES (if pump) or NO (if dump) before
    the price adjusts, then sell when it catches up.
    """
    
    def __init__(self, clob_client: ClobClient):
        super().__init__("Latency Arbitrage", StrategyType.LATENCY_ARBITRAGE)
        self.client = clob_client
        
        # Binance monitoring
        self.binance_monitor = BinanceMonitor(
            on_price_update=self._on_binance_price_update,
            ws_url=config.BINANCE_WS_URL
        )
        
        # Price tracking
        self.btc_price_history = []
        self.max_history_size = 100
        self.last_btc_price = None
        self.last_significant_move_time = 0
        self.cooldown_seconds = 30  # Wait 30s between opportunities
        
        # Polymarket market tracking
        self.current_btc_market = None
        self.last_market_refresh = 0
        
    def start(self):
        """Start the Binance WebSocket monitor"""
        self.binance_monitor.start()
        logger.info("🚀 Latency arbitrage strategy started")
    
    def stop(self):
        """Stop the Binance WebSocket monitor"""
        self.binance_monitor.stop()
        logger.info("🛑 Latency arbitrage strategy stopped")
    
    def _on_binance_price_update(self, btc_price: float):
        """
        Callback when Binance BTC price updates.
        Stores price in history for movement detection.
        """
        # Add to history
        self.btc_price_history.append({
            'price': btc_price,
            'timestamp': time.time()
        })
        
        # Trim history to max size
        if len(self.btc_price_history) > self.max_history_size:
            self.btc_price_history.pop(0)
        
        self.last_btc_price = btc_price
    
    def scan_opportunities(self) -> Optional[Dict]:
        """
        Scan for latency arbitrage opportunities.
        
        Detects when BTC has moved significantly on Binance and checks
        if Polymarket hasn't adjusted yet.
        """
        try:
            # Check if Binance is connected
            if not self.binance_monitor.is_connected():
                logger.debug("Binance WebSocket not connected")
                return None
            
            # Check cooldown
            if time.time() - self.last_significant_move_time < self.cooldown_seconds:
                return None
            
            # Check if we have enough price history
            if len(self.btc_price_history) < 10:
                return None
            
            # Detect significant BTC movement
            movement = self._detect_significant_movement()
            if not movement:
                return None
            
            # Get current Polymarket BTC market
            if not self.current_btc_market or time.time() - self.last_market_refresh > 60:
                self.current_btc_market = self._get_current_btc_market()
                self.last_market_refresh = time.time()
            
            if not self.current_btc_market:
                logger.debug("No active BTC market found")
                return None
            
            # Check if Polymarket price has lagged
            poly_opportunity = self._check_polymarket_lag(movement)
            if poly_opportunity:
                self.last_significant_move_time = time.time()
                return poly_opportunity
            
            return None
            
        except Exception as e:
            logger.error(f"Error scanning for latency arbitrage: {e}")
            return None
    
    def _detect_significant_movement(self) -> Optional[Dict]:
        """
        Detect if BTC has moved significantly in the last few seconds.
        
        Returns dict with movement info if movement > threshold
        """
        if len(self.btc_price_history) < 2:
            return None
        
        # Get price from 5 seconds ago vs now
        current = self.btc_price_history[-1]
        past = None
        
        for entry in reversed(self.btc_price_history[:-1]):
            if current['timestamp'] - entry['timestamp'] >= 3:  # 3+ seconds ago
                past = entry
                break
        
        if not past:
            return None
        
        price_change = current['price'] - past['price']
        
        # Check if movement exceeds threshold
        if abs(price_change) >= config.LATENCY_MIN_BTC_MOVE:
            direction = "up" if price_change > 0 else "down"
            
            logger.info(f"🚨 SIGNIFICANT BTC MOVE DETECTED!")
            logger.info(f"   Direction: {direction}")
            logger.info(f"   Change: ${price_change:+.2f}")
            logger.info(f"   From ${past['price']:.2f} to ${current['price']:.2f}")
            
            return {
                'direction': direction,
                'price_change': price_change,
                'old_price': past['price'],
                'new_price': current['price'],
                'detection_time': time.time()
            }
        
        return None
    
    def _get_current_btc_market(self) -> Optional[Dict]:
        """Get the current active 5-minute BTC market from Polymarket"""
        # This would use the existing market_monitor.py
        # For now, placeholder
        try:
            from market_monitor import MarketMonitor
            monitor = MarketMonitor()
            return monitor.find_current_5min_btc_market()
        except Exception as e:
            logger.error(f"Error getting BTC market: {e}")
            return None
    
    def _check_polymarket_lag(self, movement: Dict) -> Optional[Dict]:
        """
        Check if Polymarket price has lagged behind Binance movement.
        
        If BTC went up on Binance, we expect YES price to rise.
        If it hasn't yet, we can buy YES cheap and sell when it adjusts.
        """
        try:
            # Get YES/NO tokens
            tokens = self.current_btc_market.get('tokens', [])
            if len(tokens) != 2:
                return None
            
            yes_token = tokens[0]['token_id']
            
            # Get current Polymarket YES price
            yes_book = self.client.get_order_book(yes_token)
            yes_asks = yes_book.get('asks', [])
            
            if not yes_asks:
                return None
            
            yes_ask = float(yes_asks[0]['price'])
            
            # Determine if there's an opportunity
            # If BTC went UP and YES price is still low (<0.60), buy YES
            # If BTC went DOWN and YES price is still high (>0.40), buy NO
            
            opportunity = None
            
            if movement['direction'] == 'up' and yes_ask < 0.60:
                # BTC pumped, YES is still cheap
                opportunity = {
                    'market': self.current_btc_market,
                    'token_id': yes_token,
                    'side': 'YES',
                    'entry_price': yes_ask,
                    'expected_exit': 0.80,  # Expect it to rise
                    'movement': movement,
                    'strategy': 'latency_arbitrage'
                }
                
                logger.info(f"🎯 LATENCY ARBITRAGE OPPORTUNITY!")
                logger.info(f"   BTC moved UP ${movement['price_change']:+.2f}")
                logger.info(f"   Polymarket YES still at {format_price(yes_ask)} (cheap!)")
                logger.info(f"   Expected to rise to ~{format_price(0.80)}")
                
            elif movement['direction'] == 'down' and yes_ask > 0.40:
                # BTC dumped, YES is still expensive (buy NO instead)
                # Get NO token
                no_token = tokens[1]['token_id']
                no_book = self.client.get_order_book(no_token)
                no_asks = no_book.get('asks', [])
                
                if no_asks:
                    no_ask = float(no_asks[0]['price'])
                    
                    opportunity = {
                        'market': self.current_btc_market,
                        'token_id': no_token,
                        'side': 'NO',
                        'entry_price': no_ask,
                        'expected_exit': 0.70,
                        'movement': movement,
                        'strategy': 'latency_arbitrage'
                    }
                    
                    logger.info(f"🎯 LATENCY ARBITRAGE OPPORTUNITY!")
                    logger.info(f"   BTC moved DOWN ${movement['price_change']:+.2f}")
                    logger.info(f"   Buying NO at {format_price(no_ask)}")
            
            return opportunity
            
        except Exception as e:
            logger.error(f"Error checking Polymarket lag: {e}")
            return None
    
    def execute_trade(self, signal: Dict, dry_run: bool = False) -> Optional[str]:
        """
        Execute rapid arbitrage trade.
        
        CRITICAL: Must execute within 1-2 seconds of Binance signal.
        Uses market orders (taker) for instant fill.
        """
        try:
            position_id = f"latency_{int(time.time())}"
            
            # Calculate position size
            position_size_usd = min(
                config.LATENCY_MAX_POSITION_SIZE,
                config.ORDER_SIZE_USD * 2  # Allow larger sizes for high-conviction trades
            )
            
            shares = position_size_usd / signal['entry_price']
            
            if dry_run:
                logger.info(f"💵 [DRY RUN] WOULD EXECUTE LATENCY ARBITRAGE:")
                logger.info(f"   Position ID: {position_id}")
                logger.info(f"   BUY {shares:.2f} {signal['side']} @ {format_price(signal['entry_price'])}")
                logger.info(f"   Total: ${position_size_usd:.2f}")
                logger.info(f"   Expected exit: {format_price(signal['expected_exit'])}")
                logger.info(f"   Expected profit: {format_price((signal['expected_exit'] - signal['entry_price']) * shares)}")
                
                self.open_positions[position_id] = {
                    'signal': signal,
                    'shares': shares,
                    'status': 'simulated',
                    'entry_time': time.time()
                }
                
                return position_id
            
            # Execute INSTANT trade (market order)
            logger.info(f"⚡ EXECUTING LATENCY ARBITRAGE (INSTANT):")
            logger.info(f"   Buying {shares:.2f} {signal['side']} shares")
            
            order = self.client.create_market_order(
                token_id=signal['token_id'],
                size=shares
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
            
            logger.info(f"✅ Latency arbitrage executed - Position {position_id}")
            return position_id
            
        except Exception as e:
            logger.error(f"Error executing latency arbitrage: {e}")
            return None
    
    def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """
        Monitor latency arbitrage positions.
        
        Exit when:
        1. Price reaches expected exit target (take profit)
        2. Position has been open for > 30 seconds (exit at market)
        3. Price moves against us > 5% (stop loss)
        """
        closed_positions = []
        current_time = time.time()
        
        for position_id, position in list(self.open_positions.items()):
            try:
                signal = position['signal']
                time_held = current_time - position['entry_time']
                
                # For dry run, simulate profit after 15 seconds
                if dry_run and position['status'] == 'simulated':
                    if time_held > 15:
                        # Simulate successful exit
                        profit = (signal['expected_exit'] - signal['entry_price']) * position['shares']
                        self.record_trade(profit)
                        logger.info(f"✅ [DRY RUN] Position {position_id} closed - Profit: ${profit:.2f}")
                        del self.open_positions[position_id]
                        closed_positions.append(position_id)
                    continue
                
                # Check if we should exit (real trading)
                # In real implementation, would check current price and execute
                # exit logic based on profit target, time, or stop loss
                
                if time_held > 30:
                    # Exit after 30 seconds regardless
                    logger.info(f"⏰ Position {position_id} timeout - closing")
                    # Would place market sell order here
                    del self.open_positions[position_id]
                    closed_positions.append(position_id)
                
            except Exception as e:
                logger.error(f"Error monitoring position {position_id}: {e}")
        
        return closed_positions

