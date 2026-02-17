"""
Event Loop Manager for Polymarket Trading Bot V2

Coordinates all async operations and routes events to strategies.
"""
import asyncio
import logging
from typing import Dict, List, Callable, Any
import signal

logger = logging.getLogger(__name__)


class EventLoopManager:
    """
    Central async event loop manager.
    
    Features:
    - Coordinate all async operations
    - Route market events to appropriate strategies
    - Handle graceful shutdown
    - Manage concurrent tasks
    """
    
    def __init__(self):
        """Initialize event loop manager"""
        self.running = False
        self.tasks: List[asyncio.Task] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.shutdown_callbacks: List[Callable] = []
        
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: Type of event (e.g., "market_update", "order_fill")
            handler: Async callback function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered handler for event: {event_type}")
    
    def register_shutdown_callback(self, callback: Callable):
        """
        Register a callback to be called on shutdown.
        
        Args:
            callback: Async callback function
        """
        self.shutdown_callbacks.append(callback)
    
    async def emit_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Emit an event to all registered handlers.
        
        Args:
            event_type: Type of event
            event_data: Event data dictionary
        """
        handlers = self.event_handlers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event_type}")
            return
        
        # Call all handlers concurrently
        tasks = [handler(event_data) for handler in handlers]
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error emitting event {event_type}: {e}")
    
    def create_task(self, coro, name: str = None):
        """
        Create and track an async task.
        
        Args:
            coro: Coroutine to run
            name: Optional task name for debugging
        """
        task = asyncio.create_task(coro, name=name)
        self.tasks.append(task)
        
        # Remove task from list when done
        task.add_done_callback(lambda t: self.tasks.remove(t) if t in self.tasks else None)
        
        return task
    
    async def run(self):
        """Start the event loop manager"""
        if self.running:
            logger.warning("Event loop manager already running")
            return
        
        self.running = True
        logger.info("🔄 Event loop manager started")
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        try:
            # Keep running until shutdown
            while self.running:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in event loop: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the event loop manager"""
        if not self.running:
            return
        
        logger.info("🛑 Shutting down event loop manager...")
        self.running = False
        
        # Call shutdown callbacks
        for callback in self.shutdown_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")
        
        # Cancel all running tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("✅ Event loop manager shutdown complete")
