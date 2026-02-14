"""
Market Monitor - Identifies and tracks 5-minute Bitcoin markets on Polymarket
"""
import requests
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import config
from utils import setup_logger, time_until_market_close

logger = setup_logger("MarketMonitor")


class MarketMonitor:
    """Monitors Polymarket for active 5-minute Bitcoin markets"""
    
    def __init__(self):
        self.gamma_api_url = config.GAMMA_API_URL
        self.current_market = None
        self.last_market_check = 0
        
    def find_current_5min_btc_market(self) -> Optional[Dict]:
        """
        Find the currently active 5-minute Bitcoin market
        
        Returns:
            Market data dict or None if no active market found
        """
        try:
            # Fetch all active markets from Gamma API
            # Increase limit to ensure we find our target market (default might be too small)
            response = requests.get(
                f"{self.gamma_api_url}/markets",
                params={"active": True, "closed": False, "limit": 500},
                timeout=10
            )
            response.raise_for_status()
            markets = response.json()
            
            # Filter for 5-minute Bitcoin markets
            btc_5min_markets = []
            for market in markets:
                if self._is_5min_btc_market(market):
                    btc_5min_markets.append(market)
            
            if not btc_5min_markets:
                logger.warning("No active 5-minute Bitcoin markets found in top 500")
                return None
            
            # Find the market that's currently active (not about to close)
            now = int(datetime.now().timestamp())
            for market in btc_5min_markets:
                end_time = market.get("end_date_iso")
                if end_time:
                    # Convert ISO to timestamp if needed
                    if isinstance(end_time, str):
                        try:
                            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            end_timestamp = int(end_dt.timestamp())
                        except ValueError:
                             logger.error(f"Failed to parse end_date: {end_time}")
                             continue
                    else:
                        end_timestamp = end_time
                    
                    time_remaining = end_timestamp - now
                    
                    # Only consider markets with enough time remaining
                    if time_remaining > config.MIN_TIME_REMAINING_TO_TRADE:
                        logger.info(f"Found active market: {market.get('question', 'Unknown')}")
                        logger.info(f"Time remaining: {time_remaining} seconds")
                        self.current_market = market
                        return market
            
            # If we get here, all markets are too close to closing
            if btc_5min_markets:
                logger.warning("Found 5-min BTC markets but all are too close to closing")
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching markets from Gamma API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in find_current_5min_btc_market: {e}", exc_info=True)
            return None
    
    def _is_5min_btc_market(self, market: Dict) -> bool:
        """
        Check if a market is a 5-minute Bitcoin prediction market
        
        Args:
            market: Market data dict from Gamma API
            
        Returns:
            True if this is a 5-min BTC market
        """
        question = market.get("question", "").lower()
        description = market.get("description", "").lower()
        slug = market.get("slug", "").lower()
        combined_text = f"{question} {description} {slug}"
        
        # Check for required keywords
        # We need BOTH a Bitcoin reference AND a timeframe reference
        
        # Bitcoin keywords
        btc_keywords = ["btc", "bitcoin"]
        has_bitcoin = any(kw.lower() in combined_text for kw in btc_keywords)
        
        # Timeframe keywords
        # "5m" matches "btc-updown-5m..." slug/title style
        time_keywords = ["5 min", "5min", "five minute", "5m", "5 m"]
        has_5min = any(kw.lower() in combined_text for kw in time_keywords)
        
        # Check for excluded keywords
        has_excluded = any(kw.lower() in combined_text for kw in config.EXCLUDE_KEYWORDS)
        
        if has_bitcoin and not has_5min:
             # Log potential missed markets for debugging
             # logger.debug(f"Ignored potential BTC market (missing 5min): {question}")
             pass
             
        return has_bitcoin and has_5min and not has_excluded
    
    def get_market_tokens(self, market: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract YES and NO token IDs from market data
        
        Args:
            market: Market data dict
            
        Returns:
            Tuple of (yes_token_id, no_token_id) or (None, None) if not found
        """
        try:
            # Market structure varies, check different possible locations
            tokens = market.get("tokens", [])
            
            if len(tokens) >= 2:
                # Typically tokens[0] is YES, tokens[1] is NO
                # But we should verify by checking outcome labels if available
                yes_token = None
                no_token = None
                
                for token in tokens:
                    outcome = token.get("outcome", "").lower()
                    token_id = token.get("token_id")
                    
                    if "yes" in outcome or "up" in outcome or "higher" in outcome:
                        yes_token = token_id
                    elif "no" in outcome or "down" in outcome or "lower" in outcome:
                        no_token = token_id
                
                # Fallback: if we couldn't determine by outcome, use order
                if not yes_token or not no_token:
                    if len(tokens) >= 2:
                        yes_token = tokens[0].get("token_id")
                        no_token = tokens[1].get("token_id")
                
                return yes_token, no_token
            
            # Alternative structure: check for "clobTokenIds"
            clob_token_ids = market.get("clobTokenIds", [])
            if len(clob_token_ids) >= 2:
                return clob_token_ids[0], clob_token_ids[1]
            
            logger.error(f"Could not extract token IDs from market: {market.get('question')}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting token IDs: {e}")
            return None, None
    
    def is_market_still_active(self, market: Dict) -> bool:
        """
        Check if a market is still active and tradeable
        
        Args:
            market: Market data dict
            
        Returns:
            True if market is still active
        """
        try:
            end_time = market.get("end_date_iso")
            if not end_time:
                return False
            
            if isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                end_timestamp = int(end_dt.timestamp())
            else:
                end_timestamp = end_time
            
            time_remaining = time_until_market_close(end_timestamp)
            
            # Market is active if it hasn't closed and has minimum time remaining
            return time_remaining > config.MIN_TIME_REMAINING_TO_TRADE
            
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def get_market_info(self, market: Dict) -> str:
        """
        Get formatted market information for logging
        
        Args:
            market: Market data dict
            
        Returns:
            Formatted string with market details
        """
        question = market.get("question", "Unknown")
        market_id = market.get("id", "Unknown")
        end_time = market.get("end_date_iso", "Unknown")
        
        yes_token, no_token = self.get_market_tokens(market)
        
        info = f"""
Market: {question}
ID: {market_id}
End Time: {end_time}
YES Token: {yes_token}
NO Token: {no_token}
"""
        return info
