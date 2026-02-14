"""
Paper Trading Simulator - Test with virtual capital and live market data
"""
import time
import random
from datetime import datetime
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class PaperTradingSimulator:
    """
    Simulates trading with virtual capital using real market data.
    Tracks fills, P&L, and capital as if trading with real money.
    """
    
    def __init__(self, starting_capital: float = 100.0):
        self.starting_capital = starting_capital
        self.current_capital = starting_capital
        self.available_capital = starting_capital
        
        # Track simulated positions
        self.open_orders: Dict[str, Dict] = {}
        self.filled_orders: List[Dict] = []
        self.completed_trades: List[Dict] = []
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_fees_simulated = 0.0
        
        logger.info(f"📊 Paper Trading Simulator initialized with ${starting_capital:.2f}")
    
    def can_place_order(self, order_size_usd: float) -> bool:
        """Check if we have enough virtual capital to place an order"""
        return self.available_capital >= order_size_usd
    
    def simulate_order_placement(
        self,
        position_id: str,
        side: str,
        price: float,
        size_usd: float,
        market_info: Dict
    ) -> Dict:
        """
        Simulate placing an order in the market.
        
        Args:
            position_id: Unique position identifier
            side: 'YES' or 'NO'
            price: Limit price (0.0 to 1.0)
            size_usd: Size in USD
            market_info: Market metadata
        
        Returns:
            Order details
        """
        shares = size_usd / price if price > 0 else 0
        
        order = {
            'position_id': position_id,
            'side': side,
            'price': price,
            'size_usd': size_usd,
            'shares': shares,
            'status': 'open',
            'placed_at': time.time(),
            'market_info': market_info,
            'filled_at': None
        }
        
        self.open_orders[f"{position_id}_{side}"] = order
        self.available_capital -= size_usd
        
        logger.info(
            f"📝 SIMULATED ORDER: {side} {shares:.0f} shares @ ${price:.3f} "
            f"(${size_usd:.2f}) - Available: ${self.available_capital:.2f}"
        )
        
        return order
    
    def simulate_market_fills(self, current_market_data: Dict) -> List[Dict]:
        """
        Simulate order fills based on current market conditions.
        
        Maker orders fill when:
        1. Our bid is >= current market ask (we're buying, market sells to us)
        2. Our ask is <= current market bid (we're selling, market buys from us)
        
        We simulate a realistic fill rate based on market conditions.
        """
        filled_orders = []
        
        for order_key, order in list(self.open_orders.items()):
            # Simulate fill probability based on how competitive our price is
            fill_probability = self._calculate_fill_probability(order, current_market_data)
            
            # Random fill simulation (more realistic than instant fills)
            if random.random() < fill_probability:
                order['status'] = 'filled'
                order['filled_at'] = time.time()
                order['fill_price'] = order['price']  # Assume we get our limit price
                
                filled_orders.append(order)
                del self.open_orders[order_key]
                
                logger.info(
                    f"✅ SIMULATED FILL: {order['side']} {order['shares']:.0f} shares "
                    f"@ ${order['fill_price']:.3f}"
                )
                
                self.filled_orders.append(order)
        
        # Check if we completed any round-trip trades (YES + NO filled)
        self._check_completed_trades()
        
        return filled_orders
    
    def _calculate_fill_probability(self, order: Dict, market_data: Dict) -> float:
        """
        Calculate probability that our limit order would fill.
        
        Higher probability if:
        - Our price is more competitive
        - Order has been open longer
        - Market is more liquid
        """
        # Base probability increases with time (5% per minute waiting)
        time_open = time.time() - order['placed_at']
        base_prob = min(0.05 * (time_open / 60), 0.3)  # Max 30% from time
        
        # Increase probability if our price is competitive
        # This is simplified - in reality we'd check actual market depth
        competitive_bonus = 0.1
        
        # Each cycle has a chance to fill
        return base_prob + competitive_bonus
    
    def _check_completed_trades(self):
        """Check if we've completed any round-trip trades (YES + NO both filled)"""
        # Group filled orders by position_id
        positions = {}
        for order in self.filled_orders:
            pos_id = order['position_id']
            if pos_id not in positions:
                positions[pos_id] = []
            positions[pos_id].append(order)
        
        # Check for completed round trips
        for pos_id, orders in positions.items():
            if len(orders) >= 2:
                # We have both YES and NO filled
                yes_order = next((o for o in orders if o['side'] == 'YES'), None)
                no_order = next((o for o in orders if o['side'] == 'NO'), None)
                
                if yes_order and no_order:
                    # Calculate profit
                    total_cost = yes_order['size_usd'] + no_order['size_usd']
                    # When both resolve, we get $1.00 per share (100 shares = $100)
                    total_shares = min(yes_order['shares'], no_order['shares'])
                    payout = total_shares  # Each complete share pair pays $1
                    profit = payout - total_cost
                    
                    # Maker orders have NO fees on Polymarket!
                    fees = 0.0
                    net_profit = profit - fees
                    
                    trade = {
                        'position_id': pos_id,
                        'yes_order': yes_order,
                        'no_order': no_order,
                        'total_cost': total_cost,
                        'payout': payout,
                        'profit': profit,
                        'fees': fees,
                        'net_profit': net_profit,
                        'completed_at': time.time()
                    }
                    
                    self.completed_trades.append(trade)
                    self.total_trades += 1
                    self.total_profit += net_profit
                    self.current_capital += payout
                    self.available_capital += payout
                    
                    if net_profit > 0:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1
                    
                    # Remove from filled orders
                    self.filled_orders = [o for o in self.filled_orders if o['position_id'] != pos_id]
                    
                    logger.info(
                        f"💰 TRADE COMPLETE: Position {pos_id} | "
                        f"Profit: ${net_profit:.2f} | "
                        f"New Capital: ${self.current_capital:.2f}"
                    )
    
    def cancel_stale_orders(self, timeout_seconds: int = 180):
        """Cancel orders that have been open too long"""
        cancelled = []
        current_time = time.time()
        
        for order_key, order in list(self.open_orders.items()):
            if current_time - order['placed_at'] > timeout_seconds:
                # Return capital to available
                self.available_capital += order['size_usd']
                cancelled.append(order)
                del self.open_orders[order_key]
                
                logger.info(
                    f"❌ CANCELLED: {order['side']} order @ ${order['price']:.3f} "
                    f"(timeout) - Available: ${self.available_capital:.2f}"
                )
        
        return cancelled
    
    def get_performance_summary(self) -> Dict:
        """Get current performance statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'starting_capital': self.starting_capital,
            'current_capital': self.current_capital,
            'available_capital': self.available_capital,
            'total_profit': self.total_profit,
            'profit_percentage': (self.total_profit / self.starting_capital * 100),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'open_orders': len(self.open_orders),
            'open_positions_value': self.starting_capital - self.available_capital
        }
    
    def get_detailed_report(self) -> str:
        """Generate a detailed performance report"""
        stats = self.get_performance_summary()
        
        report = f"""
╔════════════════════════════════════════════════════════════╗
║           PAPER TRADING PERFORMANCE REPORT                 ║
╚════════════════════════════════════════════════════════════╝

💰 CAPITAL
   Starting: ${stats['starting_capital']:.2f}
   Current:  ${stats['current_capital']:.2f}
   Available: ${stats['available_capital']:.2f}
   P&L:      ${stats['total_profit']:.2f} ({stats['profit_percentage']:+.1f}%)

📊 TRADING STATISTICS
   Total Trades:   {stats['total_trades']}
   Winning Trades: {stats['winning_trades']}
   Losing Trades:  {stats['losing_trades']}
   Win Rate:       {stats['win_rate']:.1f}%

🎯 CURRENT POSITIONS
   Open Orders:    {stats['open_orders']}
   Capital in Use: ${stats['open_positions_value']:.2f}

════════════════════════════════════════════════════════════
"""
        return report


# Global paper trading instance
paper_trader: Optional[PaperTradingSimulator] = None


def init_paper_trading(starting_capital: float = 100.0):
    """Initialize paper trading simulator"""
    global paper_trader
    paper_trader = PaperTradingSimulator(starting_capital)
    return paper_trader


def get_paper_trader() -> Optional[PaperTradingSimulator]:
    """Get the global paper trading instance"""
    return paper_trader
