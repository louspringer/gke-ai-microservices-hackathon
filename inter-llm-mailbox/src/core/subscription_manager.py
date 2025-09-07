"""
Subscription Manager for Inter-LLM Mailbox System

This module manages LLM subscriptions to mailboxes and topics, handles connection
lifecycle, and coordinates message delivery to subscribers.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from ..models.subscription import Subscription, SubscriptionOptions, LLMID, SubscriptionID
from ..models.enums import DeliveryMode
from .redis_manager import RedisConnectionManager
from .redis_pubsub import RedisPubSubManager, PubSubMessage


logger = logging.getLogger(__name__)


@dataclass
class ConnectionState:
    """Tracks connection state for an LLM instance"""
    llm_id: LLMID
    connected: bool = True
    last_seen: datetime = None
    reconnect_count: int = 0
    message_queue: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.utcnow()
        if self.message_queue is None:
            self.message_queue = []


@dataclass
class DeliveryResult:
    """Result of message delivery attempt"""
    subscription_id: SubscriptionID
    success: bool
    error: Optional[str] = None
    retry_count: int = 0


class SubscriptionManager:
    """
    Manages LLM subscriptions to mailboxes and topics.
    
    Responsibilities:
    - Subscription lifecycle management
    - Connection state tracking
    - Message delivery coordination
    - Reconnection and recovery handling
    """
    
    def __init__(self, 
                 redis_manager: RedisConnectionManager,
                 pubsub_manager: RedisPubSubManager):
        self.redis_manager = redis_manager
        self.pubsub_manager = pubsub_manager
        
        # Subscription storage
        self._subscriptions: Dict[SubscriptionID, Subscription] = {}
        self._llm_subscriptions: Dict[LLMID, Set[SubscriptionID]] = defaultdict(set)
        self._target_subscriptions: Dict[str, Set[SubscriptionID]] = defaultdict(set)
        
        # Connection state tracking
        self._connection_states: Dict[LLMID, ConnectionState] = {}
        
        # Message delivery handlers
        self._delivery_handlers: Dict[LLMID, Callable] = {}
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Configuration
        self.cleanup_interval = 300  # 5 minutes
        self.heartbeat_interval = 30  # 30 seconds
        self.offline_timeout = 300  # 5 minutes
        self.max_queue_size = 10000  # Maximum queued messages per LLM
        
        # Locks for thread safety
        self._subscription_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the subscription manager"""
        if self._running:
            return
        
        logger.info("Starting subscription manager")
        
        # Ensure pub/sub manager is started
        if not self.pubsub_manager.is_running:
            await self.pubsub_manager.start()
        
        self._running = True
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Load existing subscriptions from Redis
        await self._load_subscriptions()
        
        logger.info("Subscription manager started")
    
    async def stop(self) -> None:
        """Stop the subscription manager"""
        if not self._running:
            return
        
        logger.info("Stopping subscription manager")
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Save subscriptions to Redis
        await self._save_subscriptions()
        
        # Clear in-memory state
        self._subscriptions.clear()
        self._llm_subscriptions.clear()
        self._target_subscriptions.clear()
        self._connection_states.clear()
        self._delivery_handlers.clear()
        
        logger.info("Subscription manager stopped")
    
    async def create_subscription(self,
                                llm_id: LLMID,
                                target: str,
                                pattern: Optional[str] = None,
                                options: Optional[SubscriptionOptions] = None) -> Subscription:
        """
        Create a new subscription for an LLM.
        
        Args:
            llm_id: ID of the subscribing LLM
            target: Target mailbox or topic name
            pattern: Optional pattern for pattern-based subscriptions
            options: Subscription configuration options
            
        Returns:
            Created subscription object
            
        Raises:
            ValueError: If subscription parameters are invalid
        """
        async with self._subscription_lock:
            # Create subscription object
            subscription = Subscription.create(
                llm_id=llm_id,
                target=target,
                pattern=pattern,
                options=options or SubscriptionOptions()
            )
            
            # Validate subscription
            if not subscription.validate():
                raise ValueError("Invalid subscription parameters")
            
            # Check for duplicate subscriptions
            existing_subs = self._llm_subscriptions.get(llm_id, set())
            for sub_id in existing_subs:
                existing_sub = self._subscriptions.get(sub_id)
                if (existing_sub and 
                    existing_sub.target == target and 
                    existing_sub.pattern == pattern):
                    logger.warning(f"Duplicate subscription for LLM {llm_id} to {target}")
                    return existing_sub
            
            # Store subscription
            self._subscriptions[subscription.id] = subscription
            self._llm_subscriptions[llm_id].add(subscription.id)
            
            # Add to target index
            index_key = pattern if pattern else target
            self._target_subscriptions[index_key].add(subscription.id)
            
            # Set up Redis pub/sub subscription
            try:
                if pattern:
                    await self.pubsub_manager.subscribe_pattern(
                        pattern, 
                        self._create_message_handler(subscription.id)
                    )
                else:
                    await self.pubsub_manager.subscribe_channel(
                        f"mailbox:{target}",
                        self._create_message_handler(subscription.id)
                    )
                
                logger.info(f"Created subscription {subscription.id} for LLM {llm_id} to {target}")
                
                # Ensure connection state exists
                await self._ensure_connection_state(llm_id)
                
                # Save to Redis
                await self._save_subscription(subscription)
                
                return subscription
                
            except Exception as e:
                # Cleanup on failure
                self._subscriptions.pop(subscription.id, None)
                self._llm_subscriptions[llm_id].discard(subscription.id)
                self._target_subscriptions[index_key].discard(subscription.id)
                
                logger.error(f"Failed to create subscription {subscription.id}: {e}")
                raise
    
    async def remove_subscription(self, subscription_id: SubscriptionID) -> bool:
        """
        Remove a subscription.
        
        Args:
            subscription_id: ID of subscription to remove
            
        Returns:
            True if subscription was removed, False if not found
        """
        async with self._subscription_lock:
            subscription = self._subscriptions.get(subscription_id)
            if not subscription:
                logger.warning(f"Subscription {subscription_id} not found for removal")
                return False
            
            try:
                # Remove from Redis pub/sub
                if subscription.pattern:
                    await self.pubsub_manager.unsubscribe_pattern(subscription.pattern)
                else:
                    await self.pubsub_manager.unsubscribe_channel(f"mailbox:{subscription.target}")
                
                # Remove from indices
                self._subscriptions.pop(subscription_id, None)
                self._llm_subscriptions[subscription.llm_id].discard(subscription_id)
                
                index_key = subscription.pattern if subscription.pattern else subscription.target
                self._target_subscriptions[index_key].discard(subscription_id)
                
                # Remove from Redis storage
                await self._delete_subscription(subscription_id)
                
                logger.info(f"Removed subscription {subscription_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to remove subscription {subscription_id}: {e}")
                raise
    
    async def get_active_subscriptions(self, llm_id: LLMID) -> List[Subscription]:
        """
        Get all active subscriptions for an LLM.
        
        Args:
            llm_id: ID of the LLM
            
        Returns:
            List of active subscriptions
        """
        subscription_ids = self._llm_subscriptions.get(llm_id, set())
        subscriptions = []
        
        for sub_id in subscription_ids:
            subscription = self._subscriptions.get(sub_id)
            if subscription and subscription.active:
                subscriptions.append(subscription)
        
        return subscriptions
    
    async def get_subscription(self, subscription_id: SubscriptionID) -> Optional[Subscription]:
        """
        Get a specific subscription by ID.
        
        Args:
            subscription_id: ID of the subscription
            
        Returns:
            Subscription object or None if not found
        """
        return self._subscriptions.get(subscription_id)
    
    async def handle_connection_loss(self, llm_id: LLMID) -> None:
        """
        Handle connection loss for an LLM.
        
        Args:
            llm_id: ID of the disconnected LLM
        """
        async with self._connection_lock:
            connection_state = self._connection_states.get(llm_id)
            if not connection_state:
                return
            
            connection_state.connected = False
            connection_state.reconnect_count += 1
            
            logger.warning(f"LLM {llm_id} connection lost (reconnect count: {connection_state.reconnect_count})")
            
            # Mark subscriptions as inactive but don't remove them
            subscription_ids = self._llm_subscriptions.get(llm_id, set())
            for sub_id in subscription_ids:
                subscription = self._subscriptions.get(sub_id)
                if subscription:
                    subscription.active = False
    
    async def handle_connection_restored(self, llm_id: LLMID) -> None:
        """
        Handle connection restoration for an LLM.
        
        Args:
            llm_id: ID of the reconnected LLM
        """
        async with self._connection_lock:
            connection_state = self._connection_states.get(llm_id)
            if not connection_state:
                await self._ensure_connection_state(llm_id)
                connection_state = self._connection_states[llm_id]
            
            connection_state.connected = True
            connection_state.last_seen = datetime.utcnow()
            
            logger.info(f"LLM {llm_id} connection restored")
            
            # Reactivate subscriptions
            subscription_ids = self._llm_subscriptions.get(llm_id, set())
            for sub_id in subscription_ids:
                subscription = self._subscriptions.get(sub_id)
                if subscription:
                    subscription.active = True
            
            # Deliver queued messages
            await self._deliver_queued_messages(llm_id)
    
    async def register_delivery_handler(self, llm_id: LLMID, handler: Callable) -> None:
        """
        Register a message delivery handler for an LLM.
        
        Args:
            llm_id: ID of the LLM
            handler: Async function to handle message delivery
        """
        self._delivery_handlers[llm_id] = handler
        await self._ensure_connection_state(llm_id)
        logger.info(f"Registered delivery handler for LLM {llm_id}")
    
    async def unregister_delivery_handler(self, llm_id: LLMID) -> None:
        """
        Unregister a message delivery handler for an LLM.
        
        Args:
            llm_id: ID of the LLM
        """
        self._delivery_handlers.pop(llm_id, None)
        logger.info(f"Unregistered delivery handler for LLM {llm_id}")
    
    async def deliver_message(self, message: Dict[str, Any], target: str) -> List[DeliveryResult]:
        """
        Deliver a message to all subscribers of a target.
        
        Args:
            message: Message data to deliver
            target: Target mailbox or topic
            
        Returns:
            List of delivery results
        """
        results = []
        
        # Find matching subscriptions
        matching_subscriptions = await self._find_matching_subscriptions(target)
        
        for subscription in matching_subscriptions:
            if not subscription.active:
                continue
            
            # Apply message filter if configured
            if subscription.options.message_filter:
                if not subscription.options.message_filter.matches(message):
                    continue
            
            # Deliver based on delivery mode
            result = await self._deliver_to_subscription(message, subscription)
            results.append(result)
        
        return results
    
    def _create_message_handler(self, subscription_id: SubscriptionID) -> Callable:
        """Create a message handler for a specific subscription"""
        async def handler(pubsub_message: PubSubMessage):
            subscription = self._subscriptions.get(subscription_id)
            if not subscription or not subscription.active:
                return
            
            try:
                # Update subscription activity
                subscription.increment_message_count()
                
                # Deliver message
                await self._deliver_to_subscription(pubsub_message.data, subscription)
                
            except Exception as e:
                logger.error(f"Error handling message for subscription {subscription_id}: {e}")
        
        return handler
    
    async def _deliver_to_subscription(self, message: Dict[str, Any], subscription: Subscription) -> DeliveryResult:
        """Deliver a message to a specific subscription"""
        try:
            connection_state = self._connection_states.get(subscription.llm_id)
            
            if not connection_state or not connection_state.connected:
                # Queue message for offline delivery
                await self._queue_message(subscription.llm_id, message, subscription)
                return DeliveryResult(subscription.id, True)
            
            # Get delivery handler
            handler = self._delivery_handlers.get(subscription.llm_id)
            if not handler:
                logger.warning(f"No delivery handler for LLM {subscription.llm_id}")
                await self._queue_message(subscription.llm_id, message, subscription)
                return DeliveryResult(subscription.id, False, "No delivery handler")
            
            # Deliver based on mode
            if subscription.options.delivery_mode == DeliveryMode.REALTIME:
                await handler(message, subscription)
            elif subscription.options.delivery_mode == DeliveryMode.BATCH:
                await self._queue_for_batch_delivery(subscription.llm_id, message, subscription)
            else:  # POLLING
                await self._queue_message(subscription.llm_id, message, subscription)
            
            return DeliveryResult(subscription.id, True)
            
        except Exception as e:
            logger.error(f"Failed to deliver message to subscription {subscription.id}: {e}")
            return DeliveryResult(subscription.id, False, str(e))
    
    async def _find_matching_subscriptions(self, target: str) -> List[Subscription]:
        """Find all subscriptions that match a target"""
        matching = []
        
        # Direct target matches
        subscription_ids = self._target_subscriptions.get(target, set())
        for sub_id in subscription_ids:
            subscription = self._subscriptions.get(sub_id)
            if subscription and subscription.active:
                matching.append(subscription)
        
        # Pattern matches
        for pattern, sub_ids in self._target_subscriptions.items():
            if '*' in pattern or '?' in pattern:  # Simple pattern check
                for sub_id in sub_ids:
                    subscription = self._subscriptions.get(sub_id)
                    if subscription and subscription.active and subscription.matches_target(target):
                        matching.append(subscription)
        
        return matching
    
    async def _queue_message(self, llm_id: LLMID, message: Dict[str, Any], subscription: Subscription) -> None:
        """Queue a message for offline delivery"""
        connection_state = self._connection_states.get(llm_id)
        if not connection_state:
            await self._ensure_connection_state(llm_id)
            connection_state = self._connection_states[llm_id]
        
        # Check queue size limit
        if len(connection_state.message_queue) >= self.max_queue_size:
            # Remove oldest message
            connection_state.message_queue.pop(0)
            logger.warning(f"Message queue full for LLM {llm_id}, dropped oldest message")
        
        # Add message with metadata
        queued_message = {
            'message': message,
            'subscription_id': subscription.id,
            'queued_at': datetime.utcnow().isoformat(),
            'target': subscription.target
        }
        
        connection_state.message_queue.append(queued_message)
    
    async def _queue_for_batch_delivery(self, llm_id: LLMID, message: Dict[str, Any], subscription: Subscription) -> None:
        """Queue message for batch delivery (simplified implementation)"""
        # For now, treat batch delivery same as queuing
        # In a full implementation, this would accumulate messages and deliver in batches
        await self._queue_message(llm_id, message, subscription)
    
    async def _deliver_queued_messages(self, llm_id: LLMID) -> None:
        """Deliver all queued messages for an LLM"""
        connection_state = self._connection_states.get(llm_id)
        if not connection_state or not connection_state.message_queue:
            return
        
        handler = self._delivery_handlers.get(llm_id)
        if not handler:
            logger.warning(f"No delivery handler for queued messages to LLM {llm_id}")
            return
        
        messages_to_deliver = connection_state.message_queue.copy()
        connection_state.message_queue.clear()
        
        logger.info(f"Delivering {len(messages_to_deliver)} queued messages to LLM {llm_id}")
        
        for queued_msg in messages_to_deliver:
            try:
                subscription = self._subscriptions.get(queued_msg['subscription_id'])
                if subscription:
                    await handler(queued_msg['message'], subscription)
            except Exception as e:
                logger.error(f"Failed to deliver queued message to LLM {llm_id}: {e}")
                # Re-queue failed message
                connection_state.message_queue.append(queued_msg)
    
    async def _ensure_connection_state(self, llm_id: LLMID) -> None:
        """Ensure connection state exists for an LLM"""
        if llm_id not in self._connection_states:
            self._connection_states[llm_id] = ConnectionState(llm_id=llm_id)
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up inactive subscriptions and connections"""
        logger.info("Starting subscription cleanup loop")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self._running:
                    break
                
                await self._cleanup_inactive_subscriptions()
                await self._cleanup_offline_connections()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
        
        logger.info("Subscription cleanup loop stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Background task for connection heartbeat monitoring"""
        logger.info("Starting connection heartbeat loop")
        
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if not self._running:
                    break
                
                await self._check_connection_heartbeats()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
        
        logger.info("Connection heartbeat loop stopped")
    
    async def _cleanup_inactive_subscriptions(self) -> None:
        """Clean up inactive subscriptions"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # 24 hour cutoff
        
        to_remove = []
        for sub_id, subscription in self._subscriptions.items():
            if not subscription.active and subscription.last_activity < cutoff_time:
                to_remove.append(sub_id)
        
        for sub_id in to_remove:
            await self.remove_subscription(sub_id)
            logger.info(f"Cleaned up inactive subscription {sub_id}")
    
    async def _cleanup_offline_connections(self) -> None:
        """Clean up connections that have been offline too long"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.offline_timeout)
        
        to_cleanup = []
        for llm_id, state in self._connection_states.items():
            if not state.connected and state.last_seen < cutoff_time:
                to_cleanup.append(llm_id)
        
        for llm_id in to_cleanup:
            # Clear message queue for offline connections
            state = self._connection_states[llm_id]
            if state.message_queue:
                logger.info(f"Clearing {len(state.message_queue)} queued messages for offline LLM {llm_id}")
                state.message_queue.clear()
    
    async def _check_connection_heartbeats(self) -> None:
        """Check connection heartbeats and mark stale connections as offline"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.heartbeat_interval * 2)
        
        for llm_id, state in self._connection_states.items():
            if state.connected and state.last_seen < cutoff_time:
                logger.warning(f"LLM {llm_id} heartbeat timeout, marking as disconnected")
                await self.handle_connection_loss(llm_id)
    
    async def _load_subscriptions(self) -> None:
        """Load subscriptions from Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Get all subscription keys
                keys = await redis_conn.keys("subscription:*")
                
                for key in keys:
                    try:
                        data = await redis_conn.hgetall(key)
                        if data:
                            # Convert bytes to strings
                            str_data = {k.decode() if isinstance(k, bytes) else k: 
                                      v.decode() if isinstance(v, bytes) else v 
                                      for k, v in data.items()}
                            
                            subscription = Subscription.from_dict(str_data)
                            
                            # Restore in-memory indices
                            self._subscriptions[subscription.id] = subscription
                            self._llm_subscriptions[subscription.llm_id].add(subscription.id)
                            
                            index_key = subscription.pattern if subscription.pattern else subscription.target
                            self._target_subscriptions[index_key].add(subscription.id)
                            
                    except Exception as e:
                        logger.error(f"Failed to load subscription from {key}: {e}")
                
                logger.info(f"Loaded {len(self._subscriptions)} subscriptions from Redis")
                
        except Exception as e:
            logger.error(f"Failed to load subscriptions from Redis: {e}")
    
    async def _save_subscriptions(self) -> None:
        """Save all subscriptions to Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                for subscription in self._subscriptions.values():
                    await self._save_subscription(subscription, redis_conn)
                
                logger.info(f"Saved {len(self._subscriptions)} subscriptions to Redis")
                
        except Exception as e:
            logger.error(f"Failed to save subscriptions to Redis: {e}")
    
    async def _save_subscription(self, subscription: Subscription, redis_conn=None) -> None:
        """Save a single subscription to Redis"""
        if redis_conn is None:
            async with self.redis_manager.get_connection() as redis_conn:
                await self._save_subscription(subscription, redis_conn)
                return
        
        key = f"subscription:{subscription.id}"
        data = subscription.to_dict()
        
        # Convert datetime objects to strings for Redis storage
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
        
        await redis_conn.hset(key, mapping=data)
    
    async def _delete_subscription(self, subscription_id: SubscriptionID) -> None:
        """Delete a subscription from Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                key = f"subscription:{subscription_id}"
                await redis_conn.delete(key)
                
        except Exception as e:
            logger.error(f"Failed to delete subscription {subscription_id} from Redis: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get subscription manager statistics"""
        active_subscriptions = sum(1 for sub in self._subscriptions.values() if sub.active)
        connected_llms = sum(1 for state in self._connection_states.values() if state.connected)
        total_queued_messages = sum(len(state.message_queue) for state in self._connection_states.values())
        
        return {
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": active_subscriptions,
            "total_llms": len(self._connection_states),
            "connected_llms": connected_llms,
            "total_queued_messages": total_queued_messages,
            "running": self._running,
            "pubsub_subscriptions": len(self.pubsub_manager.active_subscriptions)
        }