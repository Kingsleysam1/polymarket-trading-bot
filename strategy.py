"""
Trading Strategy - Maker Market Making for Polymarket 5-minute Bitcoin markets
"""
from typing import Optional, Dict, List, Tuple
from py_clob_client.client import ClobClient
from py_clob_client.order_builder.constants import BUY, SELL
import time
import config
from utils import (
    setup_logger, 
    calculate_spread, 
    calculate_profit_potential,
    format_price
)

logger = setup_logger("Strategy")


class MakerStrategy:
    """
    Implements maker market making strategy:
    1. Detect wide spreads
    2. Place limit orders inside the spread
    3. Capture spread as profit when orders fill
    """
    
    def __init__(self, clob_client: ClobClient):
        self.client = clob_client
        self.open_positions = {}  # Track active positions
        self.order_timestamps = {}  # Track when orders were placed
        
    def analyze_opportunity(
        self, 
        yes_token_id: str, 
        no_token_id: str
    ) -> Optional[Dict]:
        """
        Analyze if there's a profitable spread opportunity
        
        Args:
            yes_token_id: Token ID for YES outcome
            no_token_id: Token ID for NO outcome
            
        Returns:
            Trade signal dict with parameters, or None if no opportunity
        """
        try:
            # Get order books for both tokens
            yes_book = self.client.get_order_book(yes_token_id)
            no_book = self.client.get_order_book(no_token_id)
            
            # Extract best bid/ask
            yes_asks = yes_book.get("asks", [])
            no_asks = no_book.get("asks", [])
            
            if not yes_asks or not no_asks:
                logger.debug("Insufficient liquidity in order book")
                return None
            
            # Best ask prices (what we'd pay to buy)
            yes_ask_price = float(yes_asks[0]["price"])
            no_ask_price = float(no_asks[0]["price"])
            
            # Calculate spread opportunity
            spread = calculate_spread(yes_ask_price, no_ask_price)
            
            logger.debug(f"YES ask: {format_price(yes_ask_price)}, NO ask: {format_price(no_ask_price)}, Spread: {format_price(spread)}")
            
            # Check if spread is wide enough to trade
            if spread < config.MIN_SPREAD_TO_TRADE:
                logger.debug(f"Spread too narrow: {format_price(spread)} < {format_price(config.MIN_SPREAD_TO_TRADE)}")
                return None
            
            # Calculate potential profit
            profit_potential = calculate_profit_potential(
                spread, 
                config.ORDER_SIZE_USD,
                fee_rate=0.0  # Maker orders have 0% fee
            )
            
            if profit_potential <= 0:
                logger.debug("No profit potential after fees")
                return None
            
            # Calculate our limit order prices (inside the spread)
            # We want to buy YES/NO at prices better than the current asks
            # by placing our bids slightly higher than current best bids
            yes_bids = yes_book.get("bids", [])
            no_bids = no_book.get("bids", [])
            
            if yes_bids and no_bids:
                yes_best_bid = float(yes_bids[0]["price"])
                no_best_bid = float(no_bids[0]["price"])
                
                # Place our buy orders at current best bid + offset
                our_yes_bid = min(
                    yes_best_bid + config.PRICE_IMPROVEMENT_OFFSET,
                    yes_ask_price - 0.01  # Don't cross the spread
                )
                our_no_bid = min(
                    no_best_bid + config.PRICE_IMPROVEMENT_OFFSET,
                    no_ask_price - 0.01
                )
            else:
                # No existing bids, place orders below the asks
                our_yes_bid = yes_ask_price - config.PRICE_IMPROVEMENT_OFFSET
                our_no_bid = no_ask_price - config.PRICE_IMPROVEMENT_OFFSET
            
            # Ensure prices are valid (between 0 and 1)
            our_yes_bid = max(0.01, min(0.99, our_yes_bid))
            our_no_bid = max(0.01, min(0.99, our_no_bid))
            
            logger.info(f"📊 OPPORTUNITY DETECTED!")
            logger.info(f"   Spread: {format_price(spread)}")
            logger.info(f"   Profit Potential: {format_price(profit_potential)}")
            logger.info(f"   YES bid: {format_price(our_yes_bid)} (ask: {format_price(yes_ask_price)})")
            logger.info(f"   NO bid: {format_price(our_no_bid)} (ask: {format_price(no_ask_price)})")
            
            return {
                "yes_token_id": yes_token_id,
                "no_token_id": no_token_id,
                "yes_bid_price": our_yes_bid,
                "no_bid_price": our_no_bid,
                "spread": spread,
                "profit_potential": profit_potential,
                "yes_ask": yes_ask_price,
                "no_ask": no_ask_price
            }
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {e}")
            return None
    
    def place_maker_orders(
        self, 
        signal: Dict, 
        dry_run: bool = False
    ) -> Optional[str]:
        """
        Place maker limit orders for both YES and NO tokens
        
        Args:
            signal: Trade signal from analyze_opportunity
            dry_run: If True, simulate orders without executing
            
        Returns:
            Position ID if successful, None otherwise
        """
        try:
            # Check if we have room for more positions
            if len(self.open_positions) >= config.MAX_OPEN_POSITIONS:
                logger.warning(f"Max positions ({config.MAX_OPEN_POSITIONS}) reached, skipping trade")
                return None
            
            position_id = f"pos_{int(time.time())}"
            
            if dry_run:
                logger.info(f"💵 [DRY RUN] WOULD PLACE ORDERS:")
                logger.info(f"   Position ID: {position_id}")
                logger.info(f"   YES: BUY {config.ORDER_SIZE_USD} @ {format_price(signal['yes_bid_price'])}")
                logger.info(f"   NO:  BUY {config.ORDER_SIZE_USD} @ {format_price(signal['no_bid_price'])}")
                
                # Simulate position tracking
                self.open_positions[position_id] = {
                    "signal": signal,
                    "orders": ["dry_run_yes", "dry_run_no"],
                    "status": "simulated"
                }
                self.order_timestamps[position_id] = time.time()
                return position_id
            
            # Calculate order sizes in shares
            # In Polymarket, shares are denominated in USDC
            # If buying at $0.50, you get 2 shares for $1
            yes_size = config.ORDER_SIZE_USD / signal['yes_bid_price']
            no_size = config.ORDER_SIZE_USD / signal['no_bid_price']
            
            logger.info(f"💵 PLACING MARKET MAKING ORDERS:")
            logger.info(f"   Position ID: {position_id}")
            
            # Place YES buy order
            logger.info(f"   Placing YES buy order: {yes_size:.2f} shares @ {format_price(signal['yes_bid_price'])}")
            yes_order = self.client.create_order(
                token_id=signal['yes_token_id'],
                price=signal['yes_bid_price'],
                size=yes_size,
                side=BUY
            )
            
            # Place NO buy order
            logger.info(f"   Placing NO buy order: {no_size:.2f} shares @ {format_price(signal['no_bid_price'])}")
            no_order = self.client.create_order(
                token_id=signal['no_token_id'],
                price=signal['no_bid_price'],
                size=no_size,
                side=BUY
            )
            
            # Track position
            self.open_positions[position_id] = {
                "signal": signal,
                "yes_order_id": yes_order.get("orderID"),
                "no_order_id": no_order.get("orderID"),
                "yes_size": yes_size,
                "no_size": no_size,
                "status": "pending",
                "filled_yes": False,
                "filled_no": False
            }
            self.order_timestamps[position_id] = time.time()
            
            logger.info(f"✅ Orders placed successfully")
            return position_id
            
        except Exception as e:
            logger.error(f"Error placing maker orders: {e}")
            return None
    
    def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """
        Monitor open positions and manage exits
        
        Args:
            dry_run: If True, simulate position monitoring
            
        Returns:
            List of closed position IDs
        """
        closed_positions = []
        current_time = time.time()
        
        for position_id, position in list(self.open_positions.items()):
            try:
                # Check if position has timed out
                order_age = current_time - self.order_timestamps.get(position_id, current_time)
                
                if order_age > config.POSITION_TIMEOUT_SECONDS:
                    logger.info(f"⏰ Position {position_id} timed out after {order_age:.0f}s")
                    self._close_position(position_id, reason="timeout", dry_run=dry_run)
                    closed_positions.append(position_id)
                    continue
                
                if dry_run and position["status"] == "simulated":
                    # In dry run, simulate random fills
                    import random
                    if random.random() > 0.7:  # 30% chance to "fill"
                        logger.info(f"✅ [DRY RUN] Position {position_id} simulated fill")
                        self._close_position(position_id, reason="filled", dry_run=True)
                        closed_positions.append(position_id)
                    continue
                
                # Check order status for live positions
                if not dry_run:
                    yes_order_id = position.get("yes_order_id")
                    no_order_id = position.get("no_order_id")
                    
                    # Get order status
                    yes_status = self.client.get_order(yes_order_id)
                    no_status = self.client.get_order(no_order_id)
                    
                    yes_filled = yes_status.get("status") == "FILLED"
                    no_filled = no_status.get("status") == "FILLED"
                    
                    position["filled_yes"] = yes_filled
                    position["filled_no"] = no_filled
                    
                    # If both filled, close position (take profit)
                    if yes_filled and no_filled:
                        logger.info(f"✅ Position {position_id} fully filled!")
                        self._close_position(position_id, reason="filled", dry_run=False)
                        closed_positions.append(position_id)
                    
            except Exception as e:
                logger.error(f"Error monitoring position {position_id}: {e}")
        
        return closed_positions
    
    def _close_position(self, position_id: str, reason: str, dry_run: bool = False):
        """Close a position and calculate P&L"""
        try:
            position = self.open_positions.get(position_id)
            if not position:
                return
            
            if dry_run:
                logger.info(f"🔴 [DRY RUN] Closing position {position_id} ({reason})")
                profit = position['signal']['profit_potential'] if reason == "filled" else -0.50
            else:
                # Cancel any unfilled orders
                if not position.get("filled_yes"):
                    self.client.cancel_order(position.get("yes_order_id"))
                if not position.get("filled_no"):
                    self.client.cancel_order(position.get("no_order_id"))
                
                # Calculate actual P&L
                if position.get("filled_yes") and position.get("filled_no"):
                    # Both filled - we should profit from the spread
                    profit = position['signal']['profit_potential']
                else:
                    # Partial fill or timeout - potential small loss
                    profit = -0.25  # Estimate
                
                logger.info(f"🔴 Closing position {position_id} ({reason}) - P&L: {format_price(profit)}")
            
            # Remove from tracking
            del self.open_positions[position_id]
            if position_id in self.order_timestamps:
                del self.order_timestamps[position_id]
            
            return profit
            
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return 0.0
    
    def cancel_all_orders(self, dry_run: bool = False):
        """Cancel all open orders - used for graceful shutdown"""
        logger.info("🛑 Canceling all open orders...")
        for position_id in list(self.open_positions.keys()):
            self._close_position(position_id, reason="shutdown", dry_run=dry_run)
        logger.info("✅ All orders canceled")
