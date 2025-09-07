"""
Redis Connection Manager for Inter-LLM Mailbox System

This module provides Redis connection management with connection pooling,
health checks, reconnection logic, and resilience patterns as specified 
in requirements 8.1, 8.4, 6.2.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, circuit_breaker_manager
from .resilience_manager import ResilienceManager, LocalQueueConfig


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Redis connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class RedisConfig:
    """Redis configuration settings"""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 20
    retry_on_timeout: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    health_check_interval: float = 30.0
    max_reconnect_attempts: int = 5
    reconnect_backoff_base: float = 1.0
    reconnect_backoff_max: float = 60.0


class RedisConnectionManager:
    """
    Manages Redis connections with pooling, health checks, automatic reconnection,
    and resilience patterns including circuit breaker and local queuing.
    
    Implements requirements:
    - 8.1: Redis connection management with resilience
    - 8.4: Retry logic with exponential backoff
    - 6.2: Health monitoring for Redis connections
    - 8.2: Circuit breaker pattern for Redis failures
    - 8.3: Local message queuing for Redis unavailability
    """
    
    def __init__(self, config: RedisConfig, enable_resilience: bool = True):
        self.config = config
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self._state = ConnectionState.DISCONNECTED
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._last_health_check = 0.0
        self._connection_lock = asyncio.Lock()
        
        # Resilience components
        self._resilience_enabled = enable_resilience
        self._circuit_breaker: Optional[CircuitBreaker] = None
        self._resilience_manager: Optional[ResilienceManager] = None
        
        if self._resilience_enabled:
            self._setup_resilience_components()
        
    async def initialize(self) -> None:
        """Initialize Redis connection pool and establish connection"""
        async with self._connection_lock:
            if self._state != ConnectionState.DISCONNECTED:
                return
                
            self._state = ConnectionState.CONNECTING
            logger.info("Initializing Redis connection manager")
            
            try:
                # Create connection pool
                self._pool = ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    password=self.config.password,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    retry_on_timeout=self.config.retry_on_timeout,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    decode_responses=True
                )
                
                # Create Redis client
                self._redis = Redis(connection_pool=self._pool)
                
                # Test connection
                await self._redis.ping()
                
                self._state = ConnectionState.CONNECTED
                self._reconnect_attempts = 0
                logger.info("Redis connection established successfully")
                
                # Start health check task
                self._health_check_task = asyncio.create_task(self._health_check_loop())
                
                # Start resilience components
                await self.start_resilience()
                
            except Exception as e:
                self._state = ConnectionState.FAILED
                logger.error(f"Failed to initialize Redis connection: {e}")
                raise
    
    async def close(self) -> None:
        """Close Redis connections and cleanup resources"""
        async with self._connection_lock:
            logger.info("Closing Redis connection manager")
            
            # Stop resilience components first
            await self.stop_resilience()
            
            # Cancel health check task
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
                self._health_check_task = None
            
            # Close Redis connection
            if self._redis:
                await self._redis.aclose()
                self._redis = None
            
            # Close connection pool
            if self._pool:
                await self._pool.disconnect()
                self._pool = None
            
            self._state = ConnectionState.DISCONNECTED
            logger.info("Redis connection manager closed")
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Redis, None]:
        """
        Get a Redis connection from the pool with automatic reconnection.
        
        Yields:
            Redis: Active Redis connection
            
        Raises:
            ConnectionError: If unable to establish connection after retries
        """
        if self._state == ConnectionState.DISCONNECTED:
            await self.initialize()
        
        if self._state != ConnectionState.CONNECTED:
            await self._ensure_connection()
        
        if not self._redis:
            raise ConnectionError("Redis connection not available")
        
        try:
            yield self._redis
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis connection error during operation: {e}")
            # Trigger reconnection for next use
            self._state = ConnectionState.RECONNECTING
            raise
    
    async def _ensure_connection(self) -> None:
        """Ensure Redis connection is available, reconnect if necessary"""
        if self._state == ConnectionState.CONNECTED:
            return
        
        if self._state in (ConnectionState.CONNECTING, ConnectionState.RECONNECTING):
            # Wait for ongoing connection attempt
            max_wait = 30.0  # Maximum wait time
            wait_interval = 0.1
            waited = 0.0
            
            while self._state in (ConnectionState.CONNECTING, ConnectionState.RECONNECTING) and waited < max_wait:
                await asyncio.sleep(wait_interval)
                waited += wait_interval
            
            if self._state == ConnectionState.CONNECTED:
                return
        
        # Attempt reconnection
        await self._reconnect()
    
    async def _reconnect(self) -> None:
        """Reconnect to Redis with exponential backoff"""
        async with self._connection_lock:
            if self._state == ConnectionState.CONNECTED:
                return
            
            self._state = ConnectionState.RECONNECTING
            
            while self._reconnect_attempts < self.config.max_reconnect_attempts:
                try:
                    logger.info(f"Attempting Redis reconnection (attempt {self._reconnect_attempts + 1})")
                    
                    # Close existing connections
                    if self._redis:
                        await self._redis.aclose()
                    if self._pool:
                        await self._pool.disconnect()
                    
                    # Recreate connection pool and client
                    self._pool = ConnectionPool(
                        host=self.config.host,
                        port=self.config.port,
                        password=self.config.password,
                        db=self.config.db,
                        max_connections=self.config.max_connections,
                        retry_on_timeout=self.config.retry_on_timeout,
                        socket_timeout=self.config.socket_timeout,
                        socket_connect_timeout=self.config.socket_connect_timeout,
                        decode_responses=True
                    )
                    
                    self._redis = Redis(connection_pool=self._pool)
                    
                    # Test connection
                    await self._redis.ping()
                    
                    self._state = ConnectionState.CONNECTED
                    self._reconnect_attempts = 0
                    logger.info("Redis reconnection successful")
                    return
                    
                except Exception as e:
                    self._reconnect_attempts += 1
                    logger.warning(f"Redis reconnection attempt {self._reconnect_attempts} failed: {e}")
                    
                    if self._reconnect_attempts < self.config.max_reconnect_attempts:
                        # Calculate backoff delay
                        delay = min(
                            self.config.reconnect_backoff_base * (2 ** (self._reconnect_attempts - 1)),
                            self.config.reconnect_backoff_max
                        )
                        logger.info(f"Waiting {delay:.1f}s before next reconnection attempt")
                        await asyncio.sleep(delay)
            
            # All reconnection attempts failed
            self._state = ConnectionState.FAILED
            logger.error("All Redis reconnection attempts failed")
            raise ConnectionError("Unable to reconnect to Redis after maximum attempts")
    
    async def _health_check_loop(self) -> None:
        """Background task for periodic health checks"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _perform_health_check(self) -> None:
        """Perform Redis health check"""
        try:
            if self._redis and self._state == ConnectionState.CONNECTED:
                await self._redis.ping()
                self._last_health_check = time.time()
                logger.debug("Redis health check passed")
            else:
                logger.warning("Redis health check skipped - not connected")
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._state = ConnectionState.RECONNECTING
            # Health check failure will trigger reconnection on next operation
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is currently connected"""
        return self._state == ConnectionState.CONNECTED
    
    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state"""
        return self._state
    
    @property
    def last_health_check(self) -> float:
        """Get timestamp of last successful health check"""
        return self._last_health_check
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """Get Redis connection information for monitoring"""
        info = {
            "state": self._state.value,
            "host": self.config.host,
            "port": self.config.port,
            "db": self.config.db,
            "reconnect_attempts": self._reconnect_attempts,
            "last_health_check": self._last_health_check,
            "pool_created_connections": 0,
            "pool_available_connections": 0,
            "pool_in_use_connections": 0
        }
        
        if self._pool:
            try:
                info.update({
                    "pool_created_connections": getattr(self._pool, 'created_connections', 0),
                    "pool_available_connections": len(getattr(self._pool, '_available_connections', [])),
                    "pool_in_use_connections": len(getattr(self._pool, '_in_use_connections', []))
                })
            except (AttributeError, TypeError):
                # Handle different Redis versions or connection pool implementations
                info.update({
                    "pool_created_connections": 0,
                    "pool_available_connections": 0,
                    "pool_in_use_connections": 0
                })
        
        return info
    
    def _setup_resilience_components(self):
        """Setup circuit breaker and resilience manager"""
        # Create circuit breaker configuration
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3,
            timeout=self.config.socket_timeout,
            expected_exceptions=(ConnectionError, TimeoutError, RedisError)
        )
        
        # Get or create circuit breaker
        circuit_name = f"redis_{self.config.host}_{self.config.port}"
        self._circuit_breaker = CircuitBreaker(circuit_name, circuit_config)
        
        # Create resilience manager
        queue_config = LocalQueueConfig(
            max_queue_size=10000,
            max_message_age_hours=24,
            persistence_enabled=True,
            persistence_file=f"/tmp/redis_queue_{self.config.host}_{self.config.port}.json"
        )
        
        self._resilience_manager = ResilienceManager(
            self._circuit_breaker,
            queue_config
        )
    
    async def start_resilience(self):
        """Start resilience components"""
        if self._resilience_enabled and self._resilience_manager:
            await self._resilience_manager.start()
            logger.info("Redis resilience components started")
    
    async def stop_resilience(self):
        """Stop resilience components"""
        if self._resilience_enabled and self._resilience_manager:
            await self._resilience_manager.stop()
            logger.info("Redis resilience components stopped")
    
    async def execute_with_resilience(self, operation_name: str, redis_operation, *args, **kwargs):
        """
        Execute a Redis operation with resilience patterns.
        
        Args:
            operation_name: Name of the operation for logging
            redis_operation: Redis operation to execute
            *args: Operation arguments
            **kwargs: Operation keyword arguments
            
        Returns:
            Operation result
        """
        if not self._resilience_enabled or not self._resilience_manager:
            # Fallback to direct execution
            return await redis_operation(*args, **kwargs)
        
        return await self._resilience_manager.execute_with_resilience(
            operation_name,
            redis_operation,
            *args, **kwargs
        )
    
    async def queue_message_for_later(self, message: Dict[str, Any]) -> bool:
        """
        Queue a message locally when Redis is unavailable.
        
        Args:
            message: Message to queue
            
        Returns:
            True if queued successfully
        """
        if not self._resilience_enabled or not self._resilience_manager:
            return False
        
        return await self._resilience_manager.queue_message_locally(message)
    
    async def process_queued_messages(self, redis_operation, batch_size: int = 50) -> int:
        """
        Process messages from local queue when Redis becomes available.
        
        Args:
            redis_operation: Function to send messages to Redis
            batch_size: Number of messages to process in one batch
            
        Returns:
            Number of messages successfully processed
        """
        if not self._resilience_enabled or not self._resilience_manager:
            return 0
        
        return await self._resilience_manager.process_queued_messages(
            redis_operation,
            batch_size
        )
    
    def get_resilience_stats(self) -> Optional[Dict[str, Any]]:
        """Get resilience manager statistics"""
        if not self._resilience_enabled or not self._resilience_manager:
            return None
        
        return self._resilience_manager.get_stats()
    
    @property
    def is_resilience_healthy(self) -> bool:
        """Check if resilience manager reports healthy state"""
        if not self._resilience_enabled or not self._resilience_manager:
            return True  # No resilience = assume healthy
        
        return self._resilience_manager.is_healthy