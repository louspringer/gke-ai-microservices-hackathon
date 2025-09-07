"""
Message Router for Inter-LLM Mailbox System

This module implements message routing based on addressing modes, delivery confirmation
tracking, and retry logic with exponential backoff as specified in requirements
1.1, 1.3, 8.4, and 8.5.
"""

import asyncio
import json
import logging
import time
import random
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

try:
    from ..models.message import Message, MessageID, LLMID, ValidationResult
    from ..models.enums import AddressingMode, DeliveryStatus, Priority
    from .redis_manager import RedisConnectionManager
    from .redis_pubsub import RedisPubSubManager
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from models.message import Message, MessageID, LLMID, ValidationResult
    from models.enums import AddressingMode, DeliveryStatus, Priority
    from core.redis_manager import RedisConnectionManager
    from core.redis_pubsub import RedisPubSubManager


logger = logging.getLogger(__name__)


class RoutingResult(Enum):
    """Result of message routing operation"""
    SUCCESS = "success"
    FAILED = "failed"
    QUEUED = "queued"
    REJECTED = "rejected"


@dataclass
class DeliveryAttempt:
    """Represents a delivery attempt for a message"""
    attempt_number: int
    timestamp: datetime
    target: str
    status: DeliveryStatus
    error: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class DeliveryConfirmation:
    """Delivery confirmation tracking"""
    message_id: MessageID
    target: str
    status: DeliveryStatus
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    next_retry_at: Optional[datetime] = None
    
    def add_attempt(self, target: str, status: DeliveryStatus, error: Optional[str] = None, latency_ms: Optional[float] = None):
        """Add a delivery attempt"""
        attempt = DeliveryAttempt(
            attempt_number=len(self.attempts) + 1,
            timestamp=datetime.utcnow(),
            target=target,
            status=status,
            error=error,
            latency_ms=latency_ms
        )
        self.attempts.append(attempt)
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def get_retry_count(self) -> int:
        """Get number of retry attempts"""
        return len([a for a in self.attempts if a.attempt_number > 1])
    
    def should_retry(self, max_attempts: int) -> bool:
        """Check if message should be retried"""
        return (self.status == DeliveryStatus.FAILED and 
                len(self.attempts) < max_attempts and
                (self.next_retry_at is None or datetime.utcnow() >= self.next_retry_at))


@dataclass
class RoutingInfo:
    """Extended routing information for message processing"""
    message_id: MessageID
    sender_id: LLMID
    addressing_mode: AddressingMode
    target: str
    priority: Priority
    ttl: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_expired(self) -> bool:
        """Check if message has expired based on TTL"""
        if self.ttl is None:
            return False
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl)


class MessageRouter:
    """
    Handles message routing, delivery confirmation tracking, and retry logic.
    
    Implements requirements:
    - 1.1: Message routing based on addressing modes
    - 1.3: Delivery confirmation tracking
    - 8.4: Retry logic with exponential backoff
    - 8.5: Message delivery guarantees
    """
    
    def __init__(self, 
                 redis_manager: RedisConnectionManager,
                 pubsub_manager: RedisPubSubManager):
        self.redis_manager = redis_manager
        self.pubsub_manager = pubsub_manager
        
        # Delivery tracking
        self._delivery_confirmations: Dict[MessageID, DeliveryConfirmation] = {}
        self._pending_deliveries: Dict[MessageID, Message] = {}
        
        # Retry configuration
        self.max_retry_attempts = 3
        self.base_retry_delay = 1.0  # seconds
        self.max_retry_delay = 60.0  # seconds
        self.retry_exponential_base = 2.0
        self.retry_jitter = True
        
        # Message validation
        self.max_message_size = 16 * 1024 * 1024  # 16MB
        self.validate_messages = True
        
        # Background tasks
        self._retry_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Configuration
        self.retry_check_interval = 10.0  # seconds
        self.cleanup_interval = 300.0  # 5 minutes
        self.confirmation_ttl = 3600  # 1 hour
        
        # Metrics
        self._metrics = {
            'messages_routed': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'messages_retried': 0,
            'routing_errors': 0,
            'validation_errors': 0
        }
        
        # Locks for thread safety
        self._delivery_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the message router"""
        if self._running:
            return
        
        logger.info("Starting message router")
        self._running = True
        
        # Start background tasks
        self._retry_task = asyncio.create_task(self._retry_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Load pending deliveries from Redis
        await self._load_pending_deliveries()
        
        logger.info("Message router started")
    
    async def stop(self) -> None:
        """Stop the message router"""
        if not self._running:
            return
        
        logger.info("Stopping message router")
        self._running = False
        
        # Cancel background tasks
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save pending deliveries to Redis
        await self._save_pending_deliveries()
        
        # Clear in-memory state
        self._delivery_confirmations.clear()
        self._pending_deliveries.clear()
        
        logger.info("Message router stopped")
    
    async def route_message(self, message: Message) -> RoutingResult:
        """
        Route a message based on its addressing mode.
        
        Args:
            message: Message to route
            
        Returns:
            RoutingResult indicating the outcome
        """
        start_time = time.time()
        
        try:
            # Validate message
            if self.validate_messages:
                validation_result = await self.validate_message(message)
                if not validation_result.is_valid:
                    await self._increment_metric('validation_errors')
                    logger.error(f"Message validation failed for {message.id}: {validation_result.errors}")
                    return RoutingResult.REJECTED
            
            # Enrich message with routing metadata
            enriched_message = await self.enrich_message(message)
            
            # Create routing info
            routing_info = RoutingInfo(
                message_id=message.id,
                sender_id=message.sender_id,
                addressing_mode=message.routing_info.addressing_mode,
                target=message.routing_info.target,
                priority=message.routing_info.priority,
                ttl=message.routing_info.ttl
            )
            
            # Check if message has expired
            if routing_info.is_expired():
                logger.warning(f"Message {message.id} expired before routing")
                await self._handle_delivery_confirmation(message.id, routing_info.target, DeliveryStatus.EXPIRED)
                return RoutingResult.REJECTED
            
            # Route based on addressing mode
            result = await self._route_by_addressing_mode(enriched_message, routing_info)
            
            # Update metrics
            await self._increment_metric('messages_routed')
            
            # Track delivery if confirmation required
            if message.delivery_options.confirmation_required:
                await self._track_delivery(message, routing_info)
            
            # Log routing result
            latency_ms = (time.time() - start_time) * 1000
            logger.info(f"Routed message {message.id} to {routing_info.target} "
                       f"({result.value}) in {latency_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            await self._increment_metric('routing_errors')
            logger.error(f"Error routing message {message.id}: {e}")
            return RoutingResult.FAILED
    
    async def validate_message(self, message: Message) -> ValidationResult:
        """
        Validate a message before routing.
        
        Args:
            message: Message to validate
            
        Returns:
            ValidationResult with validation status and errors
        """
        try:
            # Use the message's built-in validation
            result = message.validate(strict=False)
            
            # Additional routing-specific validations
            if message.size_bytes() > self.max_message_size:
                result.add_error("size", f"Message size exceeds maximum allowed ({self.max_message_size} bytes)")
            
            # Validate routing target
            if not message.routing_info.target:
                result.add_error("routing_target", "Routing target is required")
            elif len(message.routing_info.target) > 256:
                result.add_error("routing_target", "Routing target exceeds maximum length (256 characters)")
            
            # Validate TTL
            if message.routing_info.ttl is not None and message.routing_info.ttl <= 0:
                result.add_error("ttl", "TTL must be positive")
            
            return result
            
        except Exception as e:
            result = ValidationResult(is_valid=False)
            result.add_error("validation", f"Validation error: {str(e)}")
            return result
    
    async def enrich_message(self, message: Message) -> Message:
        """
        Enrich message with routing metadata.
        
        Args:
            message: Original message
            
        Returns:
            Enriched message with additional metadata
        """
        # Clone message to avoid modifying original
        enriched = message.clone(new_id=False)
        
        # Add routing metadata
        enriched.add_system_metadata('routed_at', datetime.utcnow().isoformat())
        enriched.add_system_metadata('router_version', '1.0')
        enriched.add_system_metadata('routing_mode', message.routing_info.addressing_mode.value)
        
        # Add priority-based metadata
        if message.routing_info.priority == Priority.URGENT:
            enriched.add_system_metadata('urgent', True)
        
        return enriched
    
    async def handle_delivery_confirmation(self, message_id: MessageID, status: DeliveryStatus, 
                                         target: Optional[str] = None, error: Optional[str] = None,
                                         latency_ms: Optional[float] = None) -> None:
        """
        Handle delivery confirmation for a message.
        
        Args:
            message_id: ID of the message
            status: Delivery status
            target: Target that was delivered to
            error: Error message if delivery failed
            latency_ms: Delivery latency in milliseconds
        """
        await self._handle_delivery_confirmation(message_id, target or "", status, error, latency_ms)
    
    async def _route_by_addressing_mode(self, message: Message, routing_info: RoutingInfo) -> RoutingResult:
        """Route message based on addressing mode"""
        try:
            if routing_info.addressing_mode == AddressingMode.DIRECT:
                return await self._route_direct(message, routing_info)
            elif routing_info.addressing_mode == AddressingMode.BROADCAST:
                return await self._route_broadcast(message, routing_info)
            elif routing_info.addressing_mode == AddressingMode.TOPIC:
                return await self._route_topic(message, routing_info)
            else:
                logger.error(f"Unknown addressing mode: {routing_info.addressing_mode}")
                return RoutingResult.REJECTED
                
        except Exception as e:
            logger.error(f"Error in addressing mode routing: {e}")
            return RoutingResult.FAILED
    
    async def _route_direct(self, message: Message, routing_info: RoutingInfo) -> RoutingResult:
        """Route message directly to a specific mailbox"""
        try:
            # Store message in target mailbox
            await self._store_message_in_mailbox(message, routing_info.target)
            
            # Publish to mailbox channel for real-time delivery
            channel = f"mailbox:{routing_info.target}"
            message_data = message.to_dict()
            
            subscribers = await self.pubsub_manager.publish(channel, message_data)
            
            if subscribers > 0:
                logger.debug(f"Direct message {message.id} delivered to {subscribers} subscribers")
                await self._increment_metric('messages_delivered')
                return RoutingResult.SUCCESS
            else:
                logger.debug(f"Direct message {message.id} stored for offline delivery")
                return RoutingResult.QUEUED
                
        except Exception as e:
            logger.error(f"Error in direct routing: {e}")
            return RoutingResult.FAILED
    
    async def _route_broadcast(self, message: Message, routing_info: RoutingInfo) -> RoutingResult:
        """Route message to all available mailboxes (broadcast)"""
        try:
            # Get all active mailboxes
            active_mailboxes = await self._get_active_mailboxes()
            
            if not active_mailboxes:
                logger.warning(f"No active mailboxes for broadcast message {message.id}")
                return RoutingResult.QUEUED
            
            success_count = 0
            
            for mailbox in active_mailboxes:
                try:
                    # Store in each mailbox
                    await self._store_message_in_mailbox(message, mailbox)
                    
                    # Publish to mailbox channel
                    channel = f"mailbox:{mailbox}"
                    message_data = message.to_dict()
                    
                    subscribers = await self.pubsub_manager.publish(channel, message_data)
                    if subscribers > 0:
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"Error broadcasting to mailbox {mailbox}: {e}")
            
            if success_count > 0:
                logger.info(f"Broadcast message {message.id} delivered to {success_count} mailboxes")
                await self._increment_metric('messages_delivered')
                return RoutingResult.SUCCESS
            else:
                return RoutingResult.QUEUED
                
        except Exception as e:
            logger.error(f"Error in broadcast routing: {e}")
            return RoutingResult.FAILED
    
    async def _route_topic(self, message: Message, routing_info: RoutingInfo) -> RoutingResult:
        """Route message to a topic"""
        try:
            # Store message in topic storage
            await self._store_message_in_topic(message, routing_info.target)
            
            # Publish to topic channel
            channel = f"topic:{routing_info.target}"
            message_data = message.to_dict()
            
            subscribers = await self.pubsub_manager.publish(channel, message_data)
            
            if subscribers > 0:
                logger.debug(f"Topic message {message.id} delivered to {subscribers} subscribers")
                await self._increment_metric('messages_delivered')
                return RoutingResult.SUCCESS
            else:
                logger.debug(f"Topic message {message.id} stored for offline delivery")
                return RoutingResult.QUEUED
                
        except Exception as e:
            logger.error(f"Error in topic routing: {e}")
            return RoutingResult.FAILED
    
    async def _store_message_in_mailbox(self, message: Message, mailbox: str) -> None:
        """Store message in a mailbox for persistence"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Store message data
                message_key = f"message:{message.id}"
                await redis_conn.hset(message_key, mapping=message.to_redis_hash())
                
                # Add to mailbox sorted set (sorted by timestamp)
                mailbox_key = f"mailbox:{mailbox}:messages"
                score = message.timestamp.timestamp()
                await redis_conn.zadd(mailbox_key, {message.id: score})
                
                # Update mailbox metadata
                metadata_key = f"mailbox:{mailbox}:metadata"
                await redis_conn.hset(metadata_key, mapping={
                    'last_message_at': message.timestamp.isoformat(),
                    'message_count': await redis_conn.zcard(mailbox_key)
                })
                
                # Set TTL if specified
                if message.routing_info.ttl:
                    await redis_conn.expire(message_key, message.routing_info.ttl)
                
        except Exception as e:
            logger.error(f"Error storing message {message.id} in mailbox {mailbox}: {e}")
            raise
    
    async def _store_message_in_topic(self, message: Message, topic: str) -> None:
        """Store message in a topic for persistence"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Store message data
                message_key = f"message:{message.id}"
                await redis_conn.hset(message_key, mapping=message.to_redis_hash())
                
                # Add to topic sorted set
                topic_key = f"topic:{topic}:messages"
                score = message.timestamp.timestamp()
                await redis_conn.zadd(topic_key, {message.id: score})
                
                # Update topic metadata
                metadata_key = f"topic:{topic}:metadata"
                await redis_conn.hset(metadata_key, mapping={
                    'last_message_at': message.timestamp.isoformat(),
                    'message_count': await redis_conn.zcard(topic_key)
                })
                
                # Set TTL if specified
                if message.routing_info.ttl:
                    await redis_conn.expire(message_key, message.routing_info.ttl)
                
        except Exception as e:
            logger.error(f"Error storing message {message.id} in topic {topic}: {e}")
            raise
    
    async def _get_active_mailboxes(self) -> List[str]:
        """Get list of active mailboxes for broadcast routing"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Get all mailbox metadata keys
                keys = await redis_conn.keys("mailbox:*:metadata")
                
                active_mailboxes = []
                for key in keys:
                    # Extract mailbox name from key
                    mailbox_name = key.split(':')[1]
                    active_mailboxes.append(mailbox_name)
                
                return active_mailboxes
                
        except Exception as e:
            logger.error(f"Error getting active mailboxes: {e}")
            return []
    
    async def _track_delivery(self, message: Message, routing_info: RoutingInfo) -> None:
        """Track delivery for confirmation"""
        async with self._delivery_lock:
            confirmation = DeliveryConfirmation(
                message_id=message.id,
                target=routing_info.target,
                status=DeliveryStatus.PENDING
            )
            
            self._delivery_confirmations[message.id] = confirmation
            self._pending_deliveries[message.id] = message
    
    async def _handle_delivery_confirmation(self, message_id: MessageID, target: str, 
                                          status: DeliveryStatus, error: Optional[str] = None,
                                          latency_ms: Optional[float] = None) -> None:
        """Handle delivery confirmation"""
        async with self._delivery_lock:
            confirmation = self._delivery_confirmations.get(message_id)
            if not confirmation:
                # Create new confirmation if not exists
                confirmation = DeliveryConfirmation(
                    message_id=message_id,
                    target=target,
                    status=status
                )
                self._delivery_confirmations[message_id] = confirmation
            
            # Add delivery attempt
            confirmation.add_attempt(target, status, error, latency_ms)
            
            # Handle retry logic for failed deliveries
            if status == DeliveryStatus.FAILED and confirmation.should_retry(self.max_retry_attempts):
                await self._schedule_retry(confirmation)
            elif status in [DeliveryStatus.DELIVERED, DeliveryStatus.EXPIRED]:
                # Remove from pending deliveries
                self._pending_deliveries.pop(message_id, None)
                await self._increment_metric('messages_delivered' if status == DeliveryStatus.DELIVERED else 'messages_failed')
            elif status == DeliveryStatus.FAILED and not confirmation.should_retry(self.max_retry_attempts):
                # Max retries exceeded
                self._pending_deliveries.pop(message_id, None)
                await self._increment_metric('messages_failed')
                logger.error(f"Message {message_id} failed delivery after {len(confirmation.attempts)} attempts")
    
    async def _schedule_retry(self, confirmation: DeliveryConfirmation) -> None:
        """Schedule message retry with exponential backoff"""
        retry_count = confirmation.get_retry_count()
        
        # Calculate delay with exponential backoff
        delay = min(
            self.base_retry_delay * (self.retry_exponential_base ** retry_count),
            self.max_retry_delay
        )
        
        # Add jitter to prevent thundering herd
        if self.retry_jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        confirmation.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        logger.info(f"Scheduled retry for message {confirmation.message_id} "
                   f"in {delay:.1f}s (attempt {retry_count + 2})")
    
    async def _retry_loop(self) -> None:
        """Background task for processing message retries"""
        logger.info("Starting message retry loop")
        
        while self._running:
            try:
                await asyncio.sleep(self.retry_check_interval)
                
                if not self._running:
                    break
                
                await self._process_retries()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry loop: {e}")
        
        logger.info("Message retry loop stopped")
    
    async def _process_retries(self) -> None:
        """Process pending message retries"""
        now = datetime.utcnow()
        
        async with self._delivery_lock:
            to_retry = []
            
            for message_id, confirmation in self._delivery_confirmations.items():
                if (confirmation.status == DeliveryStatus.FAILED and
                    confirmation.next_retry_at and
                    now >= confirmation.next_retry_at and
                    confirmation.should_retry(self.max_retry_attempts)):
                    
                    message = self._pending_deliveries.get(message_id)
                    if message:
                        to_retry.append((message, confirmation))
        
        # Process retries outside the lock
        for message, confirmation in to_retry:
            try:
                logger.info(f"Retrying delivery for message {message.id}")
                
                # Reset next retry time
                confirmation.next_retry_at = None
                
                # Attempt routing again
                result = await self.route_message(message)
                
                if result == RoutingResult.SUCCESS:
                    await self._handle_delivery_confirmation(
                        message.id, confirmation.target, DeliveryStatus.DELIVERED
                    )
                else:
                    await self._handle_delivery_confirmation(
                        message.id, confirmation.target, DeliveryStatus.FAILED, 
                        f"Retry failed: {result.value}"
                    )
                
                await self._increment_metric('messages_retried')
                
            except Exception as e:
                logger.error(f"Error retrying message {message.id}: {e}")
                await self._handle_delivery_confirmation(
                    message.id, confirmation.target, DeliveryStatus.FAILED, str(e)
                )
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up old confirmations"""
        logger.info("Starting delivery confirmation cleanup loop")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self._running:
                    break
                
                await self._cleanup_old_confirmations()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
        
        logger.info("Delivery confirmation cleanup loop stopped")
    
    async def _cleanup_old_confirmations(self) -> None:
        """Clean up old delivery confirmations"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.confirmation_ttl)
        
        async with self._delivery_lock:
            to_remove = []
            
            for message_id, confirmation in self._delivery_confirmations.items():
                if (confirmation.status in [DeliveryStatus.DELIVERED, DeliveryStatus.EXPIRED, DeliveryStatus.FAILED] and
                    confirmation.updated_at < cutoff_time):
                    to_remove.append(message_id)
            
            for message_id in to_remove:
                self._delivery_confirmations.pop(message_id, None)
                self._pending_deliveries.pop(message_id, None)
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old delivery confirmations")
    
    async def _load_pending_deliveries(self) -> None:
        """Load pending deliveries from Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Load pending delivery confirmations
                keys = await redis_conn.keys("delivery_confirmation:*")
                
                for key in keys:
                    try:
                        data = await redis_conn.hgetall(key)
                        if data:
                            # Parse confirmation data
                            message_id = key.split(':')[1]
                            
                            # Load associated message if exists
                            message_key = f"message:{message_id}"
                            message_data = await redis_conn.hgetall(message_key)
                            
                            if message_data:
                                message = Message.from_redis_hash(message_data)
                                self._pending_deliveries[message_id] = message
                    
                    except Exception as e:
                        logger.error(f"Error loading pending delivery from {key}: {e}")
                
                logger.info(f"Loaded {len(self._pending_deliveries)} pending deliveries")
                
        except Exception as e:
            logger.error(f"Error loading pending deliveries: {e}")
    
    async def _save_pending_deliveries(self) -> None:
        """Save pending deliveries to Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                for message_id, confirmation in self._delivery_confirmations.items():
                    if confirmation.status == DeliveryStatus.PENDING:
                        key = f"delivery_confirmation:{message_id}"
                        data = {
                            'message_id': message_id,
                            'target': confirmation.target,
                            'status': confirmation.status.value,
                            'created_at': confirmation.created_at.isoformat(),
                            'updated_at': confirmation.updated_at.isoformat(),
                            'attempt_count': len(confirmation.attempts)
                        }
                        await redis_conn.hset(key, mapping=data)
                        await redis_conn.expire(key, self.confirmation_ttl)
                
                logger.info(f"Saved {len(self._delivery_confirmations)} delivery confirmations")
                
        except Exception as e:
            logger.error(f"Error saving pending deliveries: {e}")
    
    async def _increment_metric(self, metric_name: str) -> None:
        """Thread-safe metric increment"""
        async with self._metrics_lock:
            self._metrics[metric_name] = self._metrics.get(metric_name, 0) + 1
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get message router statistics"""
        async with self._metrics_lock:
            metrics = self._metrics.copy()
        
        async with self._delivery_lock:
            pending_count = len(self._pending_deliveries)
            confirmation_count = len(self._delivery_confirmations)
            
            # Count confirmations by status
            status_counts = defaultdict(int)
            for confirmation in self._delivery_confirmations.values():
                status_counts[confirmation.status.value] += 1
        
        return {
            **metrics,
            'pending_deliveries': pending_count,
            'active_confirmations': confirmation_count,
            'confirmations_by_status': dict(status_counts),
            'running': self._running,
            'retry_config': {
                'max_attempts': self.max_retry_attempts,
                'base_delay': self.base_retry_delay,
                'max_delay': self.max_retry_delay,
                'exponential_base': self.retry_exponential_base,
                'jitter_enabled': self.retry_jitter
            }
        }
    
    async def get_delivery_status(self, message_id: MessageID) -> Optional[DeliveryConfirmation]:
        """Get delivery status for a specific message"""
        return self._delivery_confirmations.get(message_id)
    
    async def get_pending_deliveries(self) -> List[MessageID]:
        """Get list of pending delivery message IDs"""
        return list(self._pending_deliveries.keys())