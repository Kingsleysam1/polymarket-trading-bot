"""
Async Adapter for Existing Strategies

Wraps synchronous strategies to work with async bot_v2.py architecture.
Maintains backward compatibility while enabling async execution.
"""
import asyncio
import logging
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class AsyncStrategyAdapter:
    """
    Adapter to run synchronous strategies in async context.
    
    Features:
    - Convert sync strategy methods to async
    - Maintain backward compatibility
    - Thread pool executor for blocking operations
    """
    
    def __init__(self, sync_strategy, executor_workers: int = 4):
        """
        Initialize async adapter.
        
        Args:
            sync_strategy: Synchronous strategy instance
            executor_workers: Number of thread pool workers
        """
        self.sync_strategy = sync_strategy
        self.executor = ThreadPoolExecutor(max_workers=executor_workers)
        self.name = getattr(sync_strategy, 'name', 'Unknown')
        
        logger.info(f"✅ Async adapter created for strategy: {self.name}")
    
    async def scan_opportunities(self) -> Optional[Dict]:
        """
        Async wrapper for scan_opportunities.
        
        Returns:
            Signal dict if opportunity found, None otherwise
        """
        loop = asyncio.get_event_loop()
        
        try:
            # Run sync method in thread pool
            result = await loop.run_in_executor(
                self.executor,
                self.sync_strategy.scan_opportunities
            )
            return result
        except Exception as e:
            logger.error(f"Error in async scan_opportunities: {e}")
            return None
    
    async def execute_trade(self, signal: Dict, dry_run: bool = False) -> Optional[str]:
        """
        Async wrapper for execute_trade.
        
        Args:
            signal: Trade signal
            dry_run: If True, simulate trade
            
        Returns:
            Position ID if successful, None otherwise
        """
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sync_strategy.execute_trade(signal, dry_run)
            )
            return result
        except Exception as e:
            logger.error(f"Error in async execute_trade: {e}")
            return None
    
    async def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """
        Async wrapper for monitor_positions.
        
        Args:
            dry_run: If True, simulate monitoring
            
        Returns:
            List of closed position IDs
        """
        loop = asyncio.get_event_loop()
        
        try:
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.sync_strategy.monitor_positions(dry_run)
            )
            return result
        except Exception as e:
            logger.error(f"Error in async monitor_positions: {e}")
            return []
    
    async def cancel_all_orders(self, dry_run: bool = False):
        """
        Async wrapper for cancel_all_orders.
        
        Args:
            dry_run: If True, simulate cancellation
        """
        loop = asyncio.get_event_loop()
        
        try:
            await loop.run_in_executor(
                self.executor,
                lambda: self.sync_strategy.cancel_all_orders(dry_run)
            )
        except Exception as e:
            logger.error(f"Error in async cancel_all_orders: {e}")
    
    def get_performance(self) -> Dict:
        """
        Get strategy performance (synchronous, safe to call directly).
        
        Returns:
            Performance statistics dict
        """
        try:
            return self.sync_strategy.get_performance()
        except Exception as e:
            logger.error(f"Error getting performance: {e}")
            return {}
    
    def __getattr__(self, name):
        """
        Delegate attribute access to wrapped strategy.
        
        Args:
            name: Attribute name
            
        Returns:
            Attribute value from wrapped strategy
        """
        return getattr(self.sync_strategy, name)
    
    async def shutdown(self):
        """Shutdown the adapter and thread pool"""
        logger.info(f"Shutting down async adapter for {self.name}")
        self.executor.shutdown(wait=True)
