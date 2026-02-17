"""
Multi-Market Scanner for Polymarket

Scans and monitors multiple markets simultaneously for trading opportunities.
Extends the existing MarketMonitor functionality with async support.
"""
import asyncio
import aiohttp
import time
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiMarketScanner:
    """
    Scans and monitors multiple Polymarket markets simultaneously.
    
    Features:
    - Async market discovery from Gamma API
    - Filter markets by keywords (BTC, ETH, SOL, 5min, hourly)
    - Maintain active market registry
    - Detect market closures and remove from registry
    - Support 20+ concurrent market subscriptions
    """
    
    def __init__(
        self,
        gamma_api_url: str,
        keywords: List[str],
        exclude_keywords: List[str],
        max_markets: int = 25,
        scan_interval: int = 10,
        min_time_remaining: int = 120
    ):
        """
        Initialize multi-market scanner.
        
        Args:
            gamma_api_url: Polymarket Gamma API URL
            keywords: Keywords to filter markets (e.g., ["BTC", "5min"])
            exclude_keywords: Keywords to exclude (e.g., ["test", "demo"])
            max_markets: Maximum number of markets to monitor
            scan_interval: How often to scan for new markets (seconds)
            min_time_remaining: Minimum time remaining to trade (seconds)
        """
        self.gamma_api_url = gamma_api_url
        self.keywords = [kw.lower() for kw in keywords]
        self.exclude_keywords = [kw.lower() for kw in exclude_keywords]
        self.max_markets = max_markets
        self.scan_interval = scan_interval
        self.min_time_remaining = min_time_remaining
        
        # Market registry
        self.active_markets: Dict[str, Dict] = {}  # market_id -> market_data
        self.market_tokens: Dict[str, tuple] = {}  # market_id -> (yes_token, no_token)
        
        # State
        self.running = False
        self.session = None
        self.last_scan_time = 0
        
    async def start(self):
        """Start the market scanner"""
        if self.running:
            logger.warning("Market scanner already running")
            return
        
        self.running = True
        self.session = aiohttp.ClientSession()
        
        logger.info("🔍 Starting multi-market scanner...")
        
        # Initial scan
        await self.scan_markets()
        
        # Start background scanning loop
        asyncio.create_task(self._scanning_loop())
    
    async def stop(self):
        """Stop the market scanner"""
        logger.info("🛑 Stopping market scanner...")
        self.running = False
        
        if self.session:
            await self.session.close()
        
        logger.info("✅ Market scanner stopped")
    
    async def scan_markets(self) -> List[Dict]:
        """
        Scan for active markets matching criteria.
        
        Returns:
            List of newly discovered markets
        """
        try:
            logger.debug("Scanning for active markets...")
            
            # Fetch markets from Gamma API
            url = f"{self.gamma_api_url}/markets"
            params = {
                "active": "true",  # Use string instead of boolean
                "closed": "false",  # Use string instead of boolean
                "limit": 500  # Fetch large batch to find all relevant markets
            }
            
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch markets: HTTP {response.status}")
                    return []
                
                markets = await response.json()
            
            # Filter markets
            new_markets = []
            for market in markets:
                market_id = market.get("id")
                
                # Skip if already tracking
                if market_id in self.active_markets:
                    continue
                
                # Check if market matches criteria
                if not self._matches_criteria(market):
                    continue
                
                # Check time remaining
                if not self._has_sufficient_time(market):
                    continue
                
                # Extract tokens
                yes_token, no_token = self._extract_tokens(market)
                if not yes_token or not no_token:
                    logger.warning(f"Could not extract tokens from market: {market.get('question')}")
                    continue
                
                # Add to registry
                self.active_markets[market_id] = market
                self.market_tokens[market_id] = (yes_token, no_token)
                new_markets.append(market)
                
                logger.info(f"📊 New market: {market.get('question', 'Unknown')[:80]}")
                
                # Stop if we've reached max markets
                if len(self.active_markets) >= self.max_markets:
                    logger.info(f"Reached max markets ({self.max_markets}), stopping scan")
                    break
            
            self.last_scan_time = time.time()
            
            if new_markets:
                logger.info(f"✅ Found {len(new_markets)} new markets (total: {len(self.active_markets)})")
            
            return new_markets
            
        except Exception as e:
            logger.error(f"Error scanning markets: {e}")
            return []
    
    async def _scanning_loop(self):
        """Background loop to periodically scan for new markets"""
        while self.running:
            try:
                # Remove closed markets
                await self._cleanup_closed_markets()
                
                # Scan for new markets if below max
                if len(self.active_markets) < self.max_markets:
                    await self.scan_markets()
                
                # Wait for next scan
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in scanning loop: {e}")
                await asyncio.sleep(self.scan_interval)
    
    async def _cleanup_closed_markets(self):
        """Remove markets that have closed or expired"""
        now = int(datetime.now().timestamp())
        closed_markets = []
        
        for market_id, market in list(self.active_markets.items()):
            # Check if market has closed
            end_time = self._get_end_timestamp(market)
            if end_time:
                time_remaining = end_time - now
                
                if time_remaining <= 0:
                    closed_markets.append(market_id)
                    logger.info(f"🔴 Market closed: {market.get('question', 'Unknown')[:60]}")
        
        # Remove closed markets
        for market_id in closed_markets:
            del self.active_markets[market_id]
            if market_id in self.market_tokens:
                del self.market_tokens[market_id]
    
    def _matches_criteria(self, market: Dict) -> bool:
        """
        Check if market matches keyword criteria.
        
        Args:
            market: Market data dict
            
        Returns:
            True if market matches criteria
        """
        question = market.get("question", "").lower()
        description = market.get("description", "").lower()
        slug = market.get("slug", "").lower()
        combined_text = f"{question} {description} {slug}"
        
        # Check for required keywords
        has_keyword = any(kw in combined_text for kw in self.keywords)
        
        # Check for excluded keywords
        has_excluded = any(kw in combined_text for kw in self.exclude_keywords)
        
        return has_keyword and not has_excluded
    
    def _has_sufficient_time(self, market: Dict) -> bool:
        """
        Check if market has sufficient time remaining to trade.
        
        Args:
            market: Market data dict
            
        Returns:
            True if market has enough time remaining
        """
        end_time = self._get_end_timestamp(market)
        if not end_time:
            return False
        
        now = int(datetime.now().timestamp())
        time_remaining = end_time - now
        
        return time_remaining > self.min_time_remaining
    
    def _get_end_timestamp(self, market: Dict) -> Optional[int]:
        """
        Extract end timestamp from market data.
        
        Args:
            market: Market data dict
            
        Returns:
            End timestamp or None
        """
        end_time = market.get("end_date_iso")
        if not end_time:
            return None
        
        try:
            if isinstance(end_time, str):
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                return int(end_dt.timestamp())
            else:
                return int(end_time)
        except Exception as e:
            logger.error(f"Failed to parse end_date: {e}")
            return None
    
    def _extract_tokens(self, market: Dict) -> tuple:
        """
        Extract YES and NO token IDs from market data.
        
        Args:
            market: Market data dict
            
        Returns:
            Tuple of (yes_token_id, no_token_id) or (None, None)
        """
        try:
            # Try tokens array first
            tokens = market.get("tokens", [])
            
            if len(tokens) >= 2:
                yes_token = None
                no_token = None
                
                for token in tokens:
                    outcome = token.get("outcome", "").lower()
                    token_id = token.get("token_id")
                    
                    if "yes" in outcome or "up" in outcome or "higher" in outcome:
                        yes_token = token_id
                    elif "no" in outcome or "down" in outcome or "lower" in outcome:
                        no_token = token_id
                
                # Fallback: use order if we couldn't determine by outcome
                if not yes_token or not no_token:
                    if len(tokens) >= 2:
                        yes_token = tokens[0].get("token_id")
                        no_token = tokens[1].get("token_id")
                
                return yes_token, no_token
            
            # Alternative: check clobTokenIds
            clob_token_ids = market.get("clobTokenIds", [])
            if len(clob_token_ids) >= 2:
                return clob_token_ids[0], clob_token_ids[1]
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting tokens: {e}")
            return None, None
    
    def get_active_markets(self) -> List[Dict]:
        """
        Get list of all active markets.
        
        Returns:
            List of active market data dicts
        """
        return list(self.active_markets.values())
    
    def get_market_tokens(self, market_id: str) -> Optional[tuple]:
        """
        Get token IDs for a specific market.
        
        Args:
            market_id: Market ID
            
        Returns:
            Tuple of (yes_token_id, no_token_id) or None
        """
        return self.market_tokens.get(market_id)
    
    def get_market_by_id(self, market_id: str) -> Optional[Dict]:
        """
        Get market data by ID.
        
        Args:
            market_id: Market ID
            
        Returns:
            Market data dict or None
        """
        return self.active_markets.get(market_id)
    
    def get_stats(self) -> Dict:
        """
        Get scanner statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "active_markets": len(self.active_markets),
            "max_markets": self.max_markets,
            "last_scan_age_seconds": time.time() - self.last_scan_time if self.last_scan_time > 0 else None,
            "running": self.running
        }
