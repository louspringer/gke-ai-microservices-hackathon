"""
Resilience Manager for Inter-LLM Mailbox System

This module provides resilience patterns including graceful degradation,
local message queuing, and fallback mechanisms for Redis unavailability.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenException
from ..models.message import Message, MessageID
from ..models.enums import DeliveryStatus


logger = logging.getLogger(__name__)


class ServiceState(Enum):
    """Service availability states"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class LocalQueueConfig:
    """Configuration for local message queuing"""
    max_queue_size: int = 10000
    max_message_age_hours: int = 24
    persistence_enabled: bool = True
    persistence_file: Optional[str] = None
    flush_interval_seconds: int = 60
    
    def __post_init__(self):
        if self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        if self.max_message_age_hours <= 0:
            raise ValueError("max_message_age_hours must be positive")


@dataclass
class QueuedMessage:
    """Message stored in local queue"""
    message: Dict[str, Any]
    queued_at: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def age_seconds(self) -> float:
        """Get message age in seconds"""
        return time.time() - self.queued_at
    
    @property
    def is_expired(self) -> bool:
        """Check if message has expired"""
        max_age = 24 * 3600  # 24 hours in seconds
        return self.age_seconds > max_age
    
    def can_retry(self) -> bool:
        """Check if message can be retried"""
        return self.retry_count < self.max_retries and not self.is_expired
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1


class LocalMessageQueue:
    """
    Local message queue for storing messages when Redis is unavailable.
    """
    
    def __init__(self, config: LocalQueueConfig):
        self.config = config
        self._queue: deque = deque()
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self.stats = {
            'total_queued': 0,
            'total_flushed': 0,
            'total_expired': 0,
            'total_failed': 0,
            'current_size': 0,
            'oldest_message_age': 0
        }
    
    async def start(self):
        """Start the local queue"""
        if self._running:
            return
        
        self._running = True
        
        # Load persisted messages if enabled
        if self.config.persistence_enabled:
            await self._load_persisted_messages()
        
        # Start flush task
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        logger.info("Local message queue started")
    
    async def stop(self):
        """Stop the local queue"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Persist messages if enabled
        if self.config.persistence_enabled:
            await self._persist_messages()
        
        logger.info("Local message queue stopped")
    
    async def enqueue(self, message: Dict[str, Any]) -> bool:
        """
        Add message to local queue.
        
        Args:
            message: Message to queue
            
        Returns:
            True if queued successfully, False if queue is full
        """
        async with self._lock:
            # Check queue size limit
            if len(self._queue) >= self.config.max_queue_size:
                logger.warning(f"Local queue full ({self.config.max_queue_size}), dropping message")
                return False
            
            # Create queued message
            queued_msg = QueuedMessage(message=message)
            self._queue.append(queued_msg)
            
            # Update statistics
            self.stats['total_queued'] += 1
            self.stats['current_size'] = len(self._queue)
            
            logger.debug(f"Queued message locally (queue size: {len(self._queue)})")
            return True
    
    async def dequeue_batch(self, batch_size: int = 100) -> List[QueuedMessage]:
        """
        Dequeue a batch of messages for processing.
        
        Args:
            batch_size: Maximum number of messages to dequeue
            
        Returns:
            List of queued messages
        """
        async with self._lock:
            batch = []
            
            # Remove expired messages first
            await self._cleanup_expired_messages()
            
            # Dequeue up to batch_size messages
            for _ in range(min(batch_size, len(self._queue))):
                if self._queue:
                    batch.append(self._queue.popleft())
            
            # Update statistics
            self.stats['current_size'] = len(self._queue)
            
            return batch
    
    async def requeue(self, message: QueuedMessage):
        """
        Requeue a message that failed to process.
        
        Args:
            message: Message to requeue
        """
        async with self._lock:
            if message.can_retry():
                message.increment_retry()
                self._queue.appendleft(message)  # Add to front for priority
                logger.debug(f"Requeued message (retry {message.retry_count})")
            else:
                self.stats['total_failed'] += 1
                logger.warning(f"Dropping message after {message.retry_count} retries")
    
    async def _cleanup_expired_messages(self):
        """Remove expired messages from queue"""
        expired_count = 0
        
        # Check messages from the front (oldest first)
        while self._queue:
            message = self._queue[0]
            if message.is_expired:
                self._queue.popleft()
                expired_count += 1
            else:
                break  # Queue is ordered by age, so we can stop here
        
        if expired_count > 0:
            self.stats['total_expired'] += expired_count
            logger.info(f"Removed {expired_count} expired messages from local queue")
    
    async def _flush_loop(self):
        """Background task to periodically flush messages"""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval_seconds)
                
                if not self._running:
                    break
                
                # Update oldest message age statistic
                if self._queue:
                    oldest_message = self._queue[0]
                    self.stats['oldest_message_age'] = oldest_message.age_seconds
                else:
                    self.stats['oldest_message_age'] = 0
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
    
    async def _persist_messages(self):
        """Persist messages to disk"""
        if not self.config.persistence_file:
            return
        
        try:
            messages_data = []
            async with self._lock:
                for queued_msg in self._queue:
                    messages_data.append({
                        'message': queued_msg.message,
                        'queued_at': queued_msg.queued_at,
                        'retry_count': queued_msg.retry_count,
                        'max_retries': queued_msg.max_retries
                    })
            
            # Write to file
            import aiofiles
            async with aiofiles.open(self.config.persistence_file, 'w') as f:
                await f.write(json.dumps(messages_data, indent=2))
            
            logger.info(f"Persisted {len(messages_data)} messages to {self.config.persistence_file}")
            
        except Exception as e:
            logger.error(f"Failed to persist messages: {e}")
    
    async def _load_persisted_messages(self):
        """Load persisted messages from disk"""
        if not self.config.persistence_file:
            return
        
        try:
            import aiofiles
            import os
            
            if not os.path.exists(self.config.persistence_file):
                return
            
            async with aiofiles.open(self.config.persistence_file, 'r') as f:
                content = await f.read()
                messages_data = json.loads(content)
            
            # Restore messages to queue
            async with self._lock:
                for msg_data in messages_data:
                    queued_msg = QueuedMessage(
                        message=msg_data['message'],
                        queued_at=msg_data['queued_at'],
                        retry_count=msg_data['retry_count'],
                        max_retries=msg_data['max_retries']
                    )
                    
                    # Only restore non-expired messages
                    if not queued_msg.is_expired:
                        self._queue.append(queued_msg)
            
            # Update statistics
            self.stats['current_size'] = len(self._queue)
            
            logger.info(f"Loaded {len(self._queue)} persisted messages from {self.config.persistence_file}")
            
            # Remove persistence file after loading
            os.remove(self.config.persistence_file)
            
        except Exception as e:
            logger.error(f"Failed to load persisted messages: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            **self.stats,
            'config': {
                'max_queue_size': self.config.max_queue_size,
                'max_message_age_hours': self.config.max_message_age_hours,
                'persistence_enabled': self.config.persistence_enabled
            }
        }


class ResilienceManager:
    """
    Manages resilience patterns for the Inter-LLM Mailbox System.
    
    Provides:
    - Circuit breaker integration
    - Local message queuing for Redis unavailability
    - Graceful degradation strategies
    - Service health monitoring
    """
    
    def __init__(self, 
                 redis_circuit_breaker: CircuitBreaker,
                 local_queue_config: Optional[LocalQueueConfig] = None):
        self.redis_circuit_breaker = redis_circuit_breaker
        
        # Initialize local queue
        if local_queue_config is None:
            local_queue_config = LocalQueueConfig()
        self.local_queue = LocalMessageQueue(local_queue_config)
        
        # Service state tracking
        self._service_state = ServiceState.HEALTHY
        self._degradation_start_time: Optional[float] = None
        
        # Fallback handlers
        self._fallback_handlers: Dict[str, Callable] = {}
        
        # Background tasks
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self.stats = {
            'redis_calls_total': 0,
            'redis_calls_failed': 0,
            'redis_calls_circuit_open': 0,
            'messages_queued_locally': 0,
            'messages_processed_from_queue': 0,
            'degradation_events': 0,
            'current_service_state': self._service_state.value
        }
    
    async def start(self):
        """Start the resilience manager"""
        if self._running:
            return
        
        self._running = True
        
        # Start local queue
        await self.local_queue.start()
        
        # Start background tasks
        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        self._queue_processor_task = asyncio.create_task(self._queue_processor_loop())
        
        logger.info("Resilience manager started")
    
    async def stop(self):
        """Stop the resilience manager"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        for task in [self._health_monitor_task, self._queue_processor_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Stop local queue
        await self.local_queue.stop()
        
        logger.info("Resilience manager stopped")
    
    async def execute_with_resilience(self, 
                                    operation_name: str,
                                    redis_operation: Callable,
                                    fallback_operation: Optional[Callable] = None,
                                    *args, **kwargs) -> Any:
        """
        Execute a Redis operation with resilience patterns.
        
        Args:
            operation_name: Name of the operation for logging
            redis_operation: Primary Redis operation to execute
            fallback_operation: Optional fallback operation
            *args: Arguments for operations
            **kwargs: Keyword arguments for operations
            
        Returns:
            Operation result
            
        Raises:
            Exception: If both primary and fallback operations fail
        """
        self.stats['redis_calls_total'] += 1
        
        try:
            # Try primary Redis operation through circuit breaker
            result = await self.redis_circuit_breaker.call(redis_operation, *args, **kwargs)
            
            # Update service state on success
            if self._service_state != ServiceState.HEALTHY:
                await self._transition_to_healthy(f"Redis operation '{operation_name}' succeeded")
            
            return result
            
        except CircuitBreakerOpenException:
            self.stats['redis_calls_circuit_open'] += 1
            logger.warning(f"Circuit breaker open for Redis operation '{operation_name}'")
            
            # Transition to degraded state
            if self._service_state == ServiceState.HEALTHY:
                await self._transition_to_degraded(f"Circuit breaker open for '{operation_name}'")
            
            # Try fallback operation
            if fallback_operation:
                try:
                    return await fallback_operation(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Fallback operation failed for '{operation_name}': {e}")
                    raise
            else:
                # No fallback available
                await self._transition_to_unavailable(f"No fallback for '{operation_name}'")
                raise
        
        except Exception as e:
            self.stats['redis_calls_failed'] += 1
            logger.error(f"Redis operation '{operation_name}' failed: {e}")
            
            # Transition to degraded state
            if self._service_state == ServiceState.HEALTHY:
                await self._transition_to_degraded(f"Redis operation '{operation_name}' failed")
            
            # Try fallback operation
            if fallback_operation:
                try:
                    return await fallback_operation(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback operation failed for '{operation_name}': {fallback_error}")
                    await self._transition_to_unavailable(f"Both primary and fallback failed for '{operation_name}'")
                    raise
            else:
                raise
    
    async def queue_message_locally(self, message: Dict[str, Any]) -> bool:
        """
        Queue a message locally when Redis is unavailable.
        
        Args:
            message: Message to queue
            
        Returns:
            True if queued successfully
        """
        success = await self.local_queue.enqueue(message)
        if success:
            self.stats['messages_queued_locally'] += 1
        return success
    
    async def process_queued_messages(self, 
                                    redis_operation: Callable,
                                    batch_size: int = 50) -> int:
        """
        Process messages from local queue when Redis becomes available.
        
        Args:
            redis_operation: Function to send messages to Redis
            batch_size: Number of messages to process in one batch
            
        Returns:
            Number of messages successfully processed
        """
        if not self.redis_circuit_breaker.is_closed:
            return 0
        
        batch = await self.local_queue.dequeue_batch(batch_size)
        if not batch:
            return 0
        
        processed_count = 0
        
        for queued_msg in batch:
            try:
                # Try to send message through Redis
                await redis_operation(queued_msg.message)
                processed_count += 1
                self.stats['messages_processed_from_queue'] += 1
                
            except Exception as e:
                logger.warning(f"Failed to process queued message: {e}")
                # Requeue for retry
                await self.local_queue.requeue(queued_msg)
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} messages from local queue")
        
        return processed_count
    
    def register_fallback_handler(self, operation_name: str, handler: Callable):
        """
        Register a fallback handler for a specific operation.
        
        Args:
            operation_name: Name of the operation
            handler: Fallback handler function
        """
        self._fallback_handlers[operation_name] = handler
        logger.info(f"Registered fallback handler for operation '{operation_name}'")
    
    def get_fallback_handler(self, operation_name: str) -> Optional[Callable]:
        """Get fallback handler for an operation"""
        return self._fallback_handlers.get(operation_name)
    
    async def _transition_to_healthy(self, reason: str):
        """Transition to healthy state"""
        if self._service_state == ServiceState.HEALTHY:
            return
        
        old_state = self._service_state
        self._service_state = ServiceState.HEALTHY
        self._degradation_start_time = None
        self.stats['current_service_state'] = self._service_state.value
        
        logger.info(f"Service state: {old_state.value} -> {self._service_state.value} ({reason})")
    
    async def _transition_to_degraded(self, reason: str):
        """Transition to degraded state"""
        if self._service_state == ServiceState.DEGRADED:
            return
        
        old_state = self._service_state
        self._service_state = ServiceState.DEGRADED
        
        if self._degradation_start_time is None:
            self._degradation_start_time = time.time()
            self.stats['degradation_events'] += 1
        
        self.stats['current_service_state'] = self._service_state.value
        
        logger.warning(f"Service state: {old_state.value} -> {self._service_state.value} ({reason})")
    
    async def _transition_to_unavailable(self, reason: str):
        """Transition to unavailable state"""
        if self._service_state == ServiceState.UNAVAILABLE:
            return
        
        old_state = self._service_state
        self._service_state = ServiceState.UNAVAILABLE
        
        if self._degradation_start_time is None:
            self._degradation_start_time = time.time()
            self.stats['degradation_events'] += 1
        
        self.stats['current_service_state'] = self._service_state.value
        
        logger.error(f"Service state: {old_state.value} -> {self._service_state.value} ({reason})")
    
    async def _health_monitor_loop(self):
        """Background task to monitor service health"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self._running:
                    break
                
                # Check if we should attempt recovery
                if (self._service_state != ServiceState.HEALTHY and 
                    self.redis_circuit_breaker.is_closed):
                    await self._transition_to_healthy("Circuit breaker closed, attempting recovery")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
    
    async def _queue_processor_loop(self):
        """Background task to process queued messages"""
        while self._running:
            try:
                await asyncio.sleep(10)  # Process every 10 seconds
                
                if not self._running:
                    break
                
                # Only process if Redis is available
                if self.redis_circuit_breaker.is_closed:
                    # This would need to be implemented with actual Redis operations
                    # For now, we just check if there are messages to process
                    queue_stats = self.local_queue.get_stats()
                    if queue_stats['current_size'] > 0:
                        logger.info(f"Local queue has {queue_stats['current_size']} messages waiting for processing")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor loop: {e}")
    
    @property
    def service_state(self) -> ServiceState:
        """Get current service state"""
        return self._service_state
    
    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy"""
        return self._service_state == ServiceState.HEALTHY
    
    @property
    def is_degraded(self) -> bool:
        """Check if service is degraded"""
        return self._service_state == ServiceState.DEGRADED
    
    @property
    def is_unavailable(self) -> bool:
        """Check if service is unavailable"""
        return self._service_state == ServiceState.UNAVAILABLE
    
    def get_stats(self) -> Dict[str, Any]:
        """Get resilience manager statistics"""
        degradation_duration = None
        if self._degradation_start_time:
            degradation_duration = time.time() - self._degradation_start_time
        
        return {
            **self.stats,
            'service_state': self._service_state.value,
            'degradation_duration_seconds': degradation_duration,
            'circuit_breaker': self.redis_circuit_breaker.get_stats(),
            'local_queue': self.local_queue.get_stats()
        }