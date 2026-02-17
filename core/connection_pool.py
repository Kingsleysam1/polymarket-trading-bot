"""
Connection Pool Manager for Polymarket Trading Bot V2

Manages connection health and implements circuit breaker pattern.
"""
import time
import logging
from typing import Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection health states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"


class ConnectionPool:
    """
    Manages connection health and pooling.
    
    Features:
    - Track WebSocket connection status
    - Monitor latency metrics
    - Implement circuit breaker pattern
    - Health check endpoints
    """
    
    def __init__(
        self,
        latency_threshold_ms: float = 200,
        error_threshold: int = 5,
        circuit_timeout: int = 60
    ):
        """
        Initialize connection pool.
        
        Args:
            latency_threshold_ms: Latency threshold for degraded state (ms)
            error_threshold: Number of errors before circuit opens
            circuit_timeout: Time to wait before retrying after circuit opens (seconds)
        """
        self.latency_threshold_ms = latency_threshold_ms
        self.error_threshold = error_threshold
        self.circuit_timeout = circuit_timeout
        
        # Connection tracking
        self.connections: Dict[str, Dict[str, Any]] = {}
        
        # Circuit breaker state
        self.error_count = 0
        self.circuit_opened_at = 0
        self.state = ConnectionState.HEALTHY
    
    def register_connection(self, name: str, connection: Any):
        """
        Register a connection for monitoring.
        
        Args:
            name: Connection name (e.g., "websocket", "binance")
            connection: Connection object
        """
        self.connections[name] = {
            "connection": connection,
            "registered_at": time.time(),
            "last_check": 0,
            "error_count": 0
        }
        logger.info(f"📡 Registered connection: {name}")
    
    def unregister_connection(self, name: str):
        """
        Unregister a connection.
        
        Args:
            name: Connection name
        """
        if name in self.connections:
            del self.connections[name]
            logger.info(f"Unregistered connection: {name}")
    
    def record_success(self, name: str):
        """
        Record a successful operation.
        
        Args:
            name: Connection name
        """
        if name in self.connections:
            self.connections[name]["error_count"] = 0
            self.connections[name]["last_check"] = time.time()
        
        # Reset global error count
        if self.error_count > 0:
            self.error_count = max(0, self.error_count - 1)
        
        # Update state
        self._update_state()
    
    def record_error(self, name: str):
        """
        Record an error for a connection.
        
        Args:
            name: Connection name
        """
        if name in self.connections:
            self.connections[name]["error_count"] += 1
            self.connections[name]["last_check"] = time.time()
        
        # Increment global error count
        self.error_count += 1
        
        # Update state
        self._update_state()
        
        # Check if circuit should open
        if self.error_count >= self.error_threshold:
            self._open_circuit()
    
    def record_latency(self, name: str, latency_ms: float):
        """
        Record latency measurement.
        
        Args:
            name: Connection name
            latency_ms: Latency in milliseconds
        """
        if name in self.connections:
            if "latency_samples" not in self.connections[name]:
                self.connections[name]["latency_samples"] = []
            
            samples = self.connections[name]["latency_samples"]
            samples.append(latency_ms)
            
            # Keep only last 100 samples
            if len(samples) > 100:
                samples.pop(0)
            
            # Update state based on latency
            avg_latency = sum(samples) / len(samples)
            if avg_latency > self.latency_threshold_ms:
                if self.state == ConnectionState.HEALTHY:
                    self.state = ConnectionState.DEGRADED
                    logger.warning(f"⚠️  Connection degraded: high latency ({avg_latency:.1f}ms)")
    
    def _update_state(self):
        """Update overall connection state"""
        if self.state == ConnectionState.CIRCUIT_OPEN:
            # Check if circuit timeout has passed
            if time.time() - self.circuit_opened_at > self.circuit_timeout:
                logger.info("🔄 Circuit breaker timeout passed, attempting recovery")
                self.state = ConnectionState.DEGRADED
                self.error_count = 0
            return
        
        # Check error counts
        if self.error_count >= self.error_threshold:
            self._open_circuit()
        elif self.error_count > 0:
            self.state = ConnectionState.DEGRADED
        else:
            self.state = ConnectionState.HEALTHY
    
    def _open_circuit(self):
        """Open the circuit breaker"""
        if self.state != ConnectionState.CIRCUIT_OPEN:
            logger.error("🔴 Circuit breaker opened due to errors")
            self.state = ConnectionState.CIRCUIT_OPEN
            self.circuit_opened_at = time.time()
    
    def is_healthy(self) -> bool:
        """
        Check if connection pool is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return self.state in (ConnectionState.HEALTHY, ConnectionState.DEGRADED)
    
    def can_execute(self) -> bool:
        """
        Check if operations can be executed (circuit not open).
        
        Returns:
            True if operations allowed, False if circuit is open
        """
        return self.state != ConnectionState.CIRCUIT_OPEN
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status for all connections.
        
        Returns:
            Health status dictionary
        """
        connection_stats = {}
        
        for name, conn_data in self.connections.items():
            latency_samples = conn_data.get("latency_samples", [])
            avg_latency = sum(latency_samples) / len(latency_samples) if latency_samples else 0
            
            connection_stats[name] = {
                "error_count": conn_data.get("error_count", 0),
                "average_latency_ms": avg_latency,
                "last_check_age_seconds": time.time() - conn_data.get("last_check", time.time())
            }
        
        return {
            "state": self.state.value,
            "healthy": self.is_healthy(),
            "can_execute": self.can_execute(),
            "global_error_count": self.error_count,
            "connections": connection_stats
        }
