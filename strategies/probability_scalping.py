"""
Strategy 3: Probability Scalping (Extreme Probability Arbitrage)

This strategy scans multiple markets simultaneously looking for opportunities where
YES + NO price < $0.992, allowing for risk-free arbitrage by buying both sides.
"""
from typing import Optional, Dict, List
import time
import requests
from py_clob_client.client import ClobClient

import config
from strategies.base_strategy import BaseStrategy, StrategyType
from utils import setup_logger, format_price

logger = setup_logger("ProbabilityScalping")


class ProbabilityScalpingStrategy(BaseStrategy):
    """
    Scans multiple markets for probability arbitrage opportunities.
    
    When YES_ask + NO_ask < $0.992, we can buy both sides and guarantee profit
    when the market resolves (total payout = $1.00 per share set).
    """
    
    def __init__(self, clob_client: ClobClient):
        super().__init__("Probability Scalping", StrategyType.PROBABILITY_SCALPING)
        self.client = clob_client
        self.gamma_api_url = config.GAMMA_API_URL
        self.scanned_markets_cache = []
        self.last_market_refresh = 0
        self.market_refresh_interval = 60  # Refresh market list every 60 seconds
        
    def scan_opportunities(self) -> Optional[Dict]:
        """
        Scan multiple markets for probability arbitrage opportunities.
        
        Returns:
            Signal dict if arbitrage opportunity found, None otherwise
        """
        try:
            # Refresh market list if needed
            if time.time() - self.last_market_refresh > self.market_refresh_interval:
                self.scanned_markets_cache = self._get_active_markets()
                self.last_market_refresh = time.time()
            
            if not self.scanned_markets_cache:
                logger.debug("No active markets to scan")
                return None
            
            # Scan markets for arbitrage opportunities
            for market in self.scanned_markets_cache[:config.PROBABILITY_MAX_MARKETS_TO_SCAN]:
                opportunity = self._check_market_for_arbitrage(market)
                if opportunity:
                    return opportunity
            
            return None
            
        except Exception as e:
            logger.error(f"Error scanning for opportunities: {e}")
            return None
    
    def _get_active_markets(self) -> List[Dict]:
        """Fetch active markets from Gamma API"""
        try:
            response = requests.get(
                f"{self.gamma_api_url}/markets",
                params={
                    'active': 'true',
                    'closed': 'false',
                    'limit': 100  # Get more markets
                },
                timeout=5
            )
            
            if response.status_code == 200:
                markets = response.json()
                
                # Filter for binary markets with sufficient liquidity
                active_markets = []
                for market in markets:
                    if self._is_suitable_market(market):
                        active_markets.append(market)
                
                logger.info(f"📊 Found {len(active_markets)} suitable markets for probability scalping")
                return active_markets
            else:
                logger.error(f"Failed to fetch markets: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching active markets: {e}")
            return []
    
    def _is_suitable_market(self, market: Dict) -> bool:
        """Check if market is suitable for probability scalping"""
        try:
            # Must be a binary market (YES/NO)
            tokens = market.get('tokens', [])
            if len(tokens) != 2:
                return False
            
            # Check volume (avoid illiquid markets)
            volume = float(market.get('volume', 0))
            if volume < 100:  # At least $100 volume
                return False
            
            # Check if market is still active
            if market.get('closed', True):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _check_market_for_arbitrage(self, market: Dict) -> Optional[Dict]:
        """
        Check a single market for probability arbitrage opportunity.
        
        Returns signal if YES_ask + NO_ask < threshold
        """
        try:
            tokens = market.get('tokens', [])
            if len(tokens) != 2:
                return None
            
            yes_token = tokens[0]
            no_token = tokens[1]
            
            # Get order books
            yes_book = self.client.get_order_book(yes_token['token_id'])
            no_book = self.client.get_order_book(no_token['token_id'])
            
            yes_asks = yes_book.get('asks', [])
            no_asks = no_book.get('asks', [])
            
            if not yes_asks or not no_asks:
                return None
            
            # Get best ask prices (what we'd pay to buy)
            yes_ask = float(yes_asks[0]['price'])
            no_ask = float(no_asks[0]['price'])
            
            # Calculate total cost
            total_cost = yes_ask + no_ask
            
            # Check if arbitrage opportunity exists
            # Total cost must be less than $0.992 to be profitable after potential fees
            if total_cost < config.PROBABILITY_PRICE_SUM_THRESHOLD:
                # Calculate profit potential
                # When market resolves: payout = $1.00 per share
                # Profit = $1.00 - total_cost
                profit_per_share = 1.00 - total_cost
                
                # Check if profit meets minimum threshold
                if profit_per_share >= config.PROBABILITY_MIN_PROFIT_THRESHOLD:
                    logger.info(f"🎯 ARBITRAGE OPPORTUNITY FOUND!")
                    logger.info(f"   Market: {market.get('question', 'Unknown')}")
                    logger.info(f"   YES ask: {format_price(yes_ask)}")
                    logger.info(f"   NO ask: {format_price(no_ask)}")
                    logger.info(f"   Total: {format_price(total_cost)}")
                    logger.info(f"   Profit potential: {format_price(profit_per_share)} per share")
                    
                    return {
                        'market': market,
                        'yes_token_id': yes_token['token_id'],
                        'no_token_id': no_token['token_id'],
                        'yes_ask': yes_ask,
                        'no_ask': no_ask,
                        'total_cost': total_cost,
                        'profit_per_share': profit_per_share,
                        'strategy': 'probability_scalping'
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error checking market {market.get('question', 'Unknown')}: {e}")
            return None
    
    def execute_trade(self, signal: Dict, dry_run: bool = False) -> Optional[str]:
        """
        Execute probability arbitrage trade by buying both YES and NO.
        
        This is an instant execution (taker orders) to capture the arbitrage quickly.
        """
        try:
            position_id = f"prob_{int(time.time())}"
            
            # Calculate position size
            position_size_usd = min(
                config.PROBABILITY_MAX_POSITION_SIZE,
                config.ORDER_SIZE_USD
            )
            
            # Calculate shares to buy
            yes_shares = position_size_usd / signal['yes_ask']
            no_shares = position_size_usd / signal['no_ask']
            
            # Use the smaller amount to ensure we have complete sets
            shares_to_buy = min(yes_shares, no_shares)
            
            if dry_run:
                logger.info(f"💵 [DRY RUN] WOULD EXECUTE ARBITRAGE:")
                logger.info(f"   Position ID: {position_id}")
                logger.info(f"   BUY {shares_to_buy:.2f} YES @ {format_price(signal['yes_ask'])}")
                logger.info(f"   BUY {shares_to_buy:.2f} NO @ {format_price(signal['no_ask'])}")
                logger.info(f"   Total Cost: {format_price(shares_to_buy * signal['total_cost'])}")
                logger.info(f"   Expected Profit: {format_price(shares_to_buy * signal['profit_per_share'])}")
                
                # Track in open positions
                self.open_positions[position_id] = {
                    'signal': signal,
                    'shares': shares_to_buy,
                    'status': 'simulated',
                    'placed_at': time.time()
                }
                
                return position_id
            
            # Execute real trades (market orders for instant fill)
            logger.info(f"💵 EXECUTING PROBABILITY ARBITRAGE:")
            logger.info(f"   Market: {signal['market'].get('question', 'Unknown')}")
            
            # Buy YES
            logger.info(f"   Buying {shares_to_buy:.2f} YES shares @ {format_price(signal['yes_ask'])}")
            yes_order = self.client.create_market_order(
                token_id=signal['yes_token_id'],
                size=shares_to_buy
            )
            
            # Buy NO
            logger.info(f"   Buying {shares_to_buy:.2f} NO shares @ {format_price(signal['no_ask'])}")
            no_order = self.client.create_market_order(
                token_id=signal['no_token_id'],
                size=shares_to_buy
            )
            
            # Track position
            self.open_positions[position_id] = {
                'signal': signal,
                'yes_order_id': yes_order.get('orderID'),
                'no_order_id': no_order.get('orderID'),
                'shares': shares_to_buy,
                'status': 'filled',
                'placed_at': time.time()
            }
            
            logger.info(f"✅ Arbitrage executed - Position {position_id}")
            return position_id
            
        except Exception as e:
            logger.error(f"Error executing arbitrage trade: {e}")
            return None
    
    def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """
        Monitor arbitrage positions.
        
        For probability scalping, we mostly just wait for market resolution.
        Both YES and NO are held until market closes.
        """
        closed_positions = []
        
        for position_id, position in list(self.open_positions.items()):
            try:
                # For arbitrage positions, we hold until market resolves
                # In practice, we could check if market is closed and calculate P&L
                
                if dry_run and position['status'] == 'simulated':
                    # Simulate that position will profit when market closes
                    # For now, just track it
                    pass
                
                # In a real implementation, we'd check market resolution
                # and calculate actual profit
                
            except Exception as e:
                logger.error(f"Error monitoring position {position_id}: {e}")
        
        return closed_positions
    
    def cancel_all_orders(self, dry_run: bool = False):
        """
        Probability scalping doesn't use limit orders, so nothing to cancel.
        Positions are held until market resolution.
        """
        logger.info(f"Probability scalping has {len(self.open_positions)} positions held until resolution")
