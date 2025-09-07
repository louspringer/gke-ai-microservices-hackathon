"""
Real-time Message Delivery Service for Inter-LLM Mailbox System

This module implements real-time message delivery with pub/sub broadcasting,
pattern-based subscriptions with wildcards, and immediate delivery for
subscribed LLMs as specified in requirements 2.2, 2.3, and 5.2.
"""

import asyncio
import json
import logging
import fnmatch
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

from ..models.message import Message, MessageID, LLMID
from ..models.subscription import Subscription, SubscriptionID
from ..models.enums import DeliveryMode, AddressingMode
from .redis_manager import RedisConnectionManager
from .redis_pubsub import RedisPubSubManager, PubSubMessage
from .subscription_manager import SubscriptionManager


logger = logging.getLogger(__name__)


@dataclass
class DeliveryStats:
    """Statistics for real-time delivery"""
    messages_broadcast: int = 0
    subscribers_reached: int = 0
    pattern_matches: int = 0
    delivery_failures: int = 0
    average_latency_ms: float = 0.0


@dataclass
class BroadcastResult:
    """Result of a message broadcast operation"""
    message_id: MessageID
    target: str
    subscribers_reached: int
    pattern_matches: int
    delivery_failures: int
    latency_ms: float
    errors: List[str]


class RealtimeDeliveryService:
    """
    Service for real-time message delivery with pub/sub broadcasting.
    
    Implements requirements:
    - 2.2: Real-time message delivery to active subscribers
    - 2.3: Pattern-based subscription support with wildcards
    - 5.2: Topic-based group communication with immediate delivery
    """
    
    def __init__(self,
                 redis_manager: RedisConnectionManager,
                 pubsub_manager: RedisPubSubManager,
                 subscription_manager: SubscriptionManager):
        self.redis_manager = redis_manager
        self.pubsub_manager = pubsub_manager
        self.subscription_manager = subscription_manager
        
        # Active delivery handlers for LLMs
        self._delivery_handlers: Dict[LLMID, Callable] = {}
        
        # Pattern subscription cache for performance
        self._pattern_cache: Dict[str, List[Subscription]] = {}
        self._cache_last_updated = datetime.utcnow()
        self._cache_ttl_seconds = 60  # Cache patterns for 1 minute
        
        # Statistics tracking
        self._stats = DeliveryStats()
        
        # Configuration
        self.enable_pattern_caching = True
        self.max_broadcast_retries = 3
        self.broadcast_timeout_seconds = 5.0
        
        # Background tasks
        self._pattern_cache_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Locks for thread safety
        self._delivery_lock = asyncio.Lock()
        self._cache_lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the real-time delivery service"""
        if self._running:
            return
        
        logger.info("Starting real-time delivery service")
        self._running = True
        
        # Ensure dependencies are started
        if not self.pubsub_manager.is_running:
            await self.pubsub_manager.start()
        
        if not self.subscription_manager._running:
            await self.subscription_manager.start()
        
        # Start background tasks
        if self.enable_pattern_caching:
            self._pattern_cache_task = asyncio.create_task(self._pattern_cache_refresh_loop())
        
        # Initialize pattern cache
        await self._refresh_pattern_cache()
        
        logger.info("Real-time delivery service started")
    
    async def stop(self) -> None:
        """Stop the real-time delivery service"""
        if not self._running:
            return
        
        logger.info("Stopping real-time delivery service")
        self._running = False
        
        # Cancel background tasks
        if self._pattern_cache_task:
            self._pattern_cache_task.cancel()
            try:
                await self._pattern_cache_task
            except asyncio.CancelledError:
                pass
        
        # Clear state
        self._delivery_handlers.clear()
        self._pattern_cache.clear()
        
        logger.info("Real-time delivery service stopped")
    
    async def register_delivery_handler(self, llm_id: LLMID, handler: Callable) -> None:
        """
        Register a delivery handler for an LLM instance.
        
        Args:
            llm_id: ID of the LLM instance
            handler: Async function to handle message delivery
        """
        async with self._delivery_lock:
            self._delivery_handlers[llm_id] = handler
            
            # Also register with subscription manager for consistency
            await self.subscription_manager.register_delivery_handler(llm_id, handler)
            
        logger.info(f"Registered real-time delivery handler for LLM {llm_id}")
    
    async def unregister_delivery_handler(self, llm_id: LLMID) -> None:
        """
        Unregister a delivery handler for an LLM instance.
        
        Args:
            llm_id: ID of the LLM instance
        """
        async with self._delivery_lock:
            self._delivery_handlers.pop(llm_id, None)
            
            # Also unregister from subscription manager
            await self.subscription_manager.unregister_delivery_handler(llm_id)
            
        logger.info(f"Unregistered real-time delivery handler for LLM {llm_id}")
    
    async def broadcast_message(self, message: Message) -> BroadcastResult:
        """
        Broadcast a message to all matching subscribers in real-time.
        
        Args:
            message: Message to broadcast
            
        Returns:
            BroadcastResult with delivery statistics
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Find all matching subscriptions
            matching_subscriptions = await self._find_matching_subscriptions(message)
            
            if not matching_subscriptions:
                logger.debug(f"No subscribers found for message {message.id}")
                return BroadcastResult(
                    message_id=message.id,
                    target=message.routing_info.target,
                    subscribers_reached=0,
                    pattern_matches=0,
                    delivery_failures=0,
                    latency_ms=0.0,
                    errors=[]
                )
            
            # Group subscriptions by LLM for efficient delivery
            llm_subscriptions = self._group_subscriptions_by_llm(matching_subscriptions)
            
            # Deliver to each LLM
            delivery_tasks = []
            for llm_id, subscriptions in llm_subscriptions.items():
                task = asyncio.create_task(
                    self._deliver_to_llm(message, llm_id, subscriptions)
                )
                delivery_tasks.append(task)
            
            # Wait for all deliveries with timeout
            try:
                delivery_results = await asyncio.wait_for(
                    asyncio.gather(*delivery_tasks, return_exceptions=True),
                    timeout=self.broadcast_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"Broadcast timeout for message {message.id}")
                delivery_results = [Exception("Delivery timeout")] * len(delivery_tasks)
            
            # Process results
            subscribers_reached = 0
            delivery_failures = 0
            errors = []
            pattern_matches = sum(1 for sub in matching_subscriptions if sub.pattern)
            
            for i, result in enumerate(delivery_results):
                if isinstance(result, Exception):
                    delivery_failures += 1
                    errors.append(str(result))
                elif result:  # Successful delivery
                    subscribers_reached += 1
            
            # Calculate latency
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Update statistics
            self._stats.messages_broadcast += 1
            self._stats.subscribers_reached += subscribers_reached
            self._stats.pattern_matches += pattern_matches
            self._stats.delivery_failures += delivery_failures
            
            # Update average latency (simple moving average)
            if self._stats.messages_broadcast == 1:
                self._stats.average_latency_ms = latency_ms
            else:
                alpha = 0.1  # Smoothing factor
                self._stats.average_latency_ms = (
                    alpha * latency_ms + (1 - alpha) * self._stats.average_latency_ms
                )
            
            # Publish to Redis pub/sub for external subscribers
            await self._publish_to_redis_channels(message)
            
            result = BroadcastResult(
                message_id=message.id,
                target=message.routing_info.target,
                subscribers_reached=subscribers_reached,
                pattern_matches=pattern_matches,
                delivery_failures=delivery_failures,
                latency_ms=latency_ms,
                errors=errors
            )
            
            logger.info(f"Broadcast message {message.id} to {subscribers_reached} subscribers "
                       f"({pattern_matches} pattern matches) in {latency_ms:.2f}ms")
            
            return result
            
        except Exception as e:
            logger.error(f"Error broadcasting message {message.id}: {e}")
            return BroadcastResult(
                message_id=message.id,
                target=message.routing_info.target,
                subscribers_reached=0,
                pattern_matches=0,
                delivery_failures=1,
                latency_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                errors=[str(e)]
            )
    
    async def _find_matching_subscriptions(self, message: Message) -> List[Subscription]:
        """Find all subscriptions that match a message"""
        matching = []
        target = message.routing_info.target
        addressing_mode = message.routing_info.addressing_mode
        
        # Get all active subscriptions from subscription manager
        all_subscriptions = []
        for llm_id in self._delivery_handlers.keys():
            llm_subscriptions = await self.subscription_manager.get_active_subscriptions(llm_id)
            all_subscriptions.extend(llm_subscriptions)
        
        for subscription in all_subscriptions:
            if not subscription.active:
                continue
            
            # Skip non-realtime subscriptions for immediate delivery
            if subscription.options.delivery_mode != DeliveryMode.REALTIME:
                continue
            
            # Check if subscription matches the message
            if await self._subscription_matches_message(subscription, message):
                matching.append(subscription)
        
        return matching
    
    async def _subscription_matches_message(self, subscription: Subscription, message: Message) -> bool:
        """Check if a subscription matches a message"""
        target = message.routing_info.target
        addressing_mode = message.routing_info.addressing_mode
        
        # Direct target match (no pattern)
        if not subscription.pattern and subscription.target == target:
            return True
        
        # Pattern-based matching
        if subscription.pattern:
            # Use fnmatch for simple patterns
            if fnmatch.fnmatch(target, subscription.pattern):
                return True
            
            # Use hierarchical matching for dot-separated patterns
            if '.' in subscription.pattern:
                if self._matches_hierarchical_pattern(target, subscription.pattern):
                    return True
            
            # Special handling for broadcast patterns
            if addressing_mode == AddressingMode.BROADCAST:
                if subscription.pattern in ["*", "broadcast:*"]:
                    return True
        
        # Check message filter if configured
        if subscription.options.message_filter:
            message_data = message.to_dict()
            if not subscription.options.message_filter.matches(message_data):
                return False
        
        return False
    
    def _matches_hierarchical_pattern(self, target: str, pattern: str) -> bool:
        """Check if target matches hierarchical pattern (e.g., 'ai.models.*' matches 'ai.models.gpt4')"""
        # Split by dots for hierarchical matching
        target_parts = target.split('.')
        pattern_parts = pattern.split('.')
        
        # Handle double wildcard (**) - matches any depth
        if '**' in pattern_parts:
            # Find the position of **
            wildcard_index = pattern_parts.index('**')
            
            # Check prefix before **
            if wildcard_index > 0:
                prefix_parts = pattern_parts[:wildcard_index]
                if len(target_parts) < len(prefix_parts):
                    return False
                for i, part in enumerate(prefix_parts):
                    if part != target_parts[i]:
                        return False
            
            # ** matches everything after the prefix
            return True
        
        # Handle single wildcard (*) - matches exactly one level
        if '*' in pattern_parts:
            wildcard_index = pattern_parts.index('*')
            
            # * at the end means match one more level
            if wildcard_index == len(pattern_parts) - 1:
                # Check that we have exactly one more level than the pattern prefix
                if len(target_parts) != len(pattern_parts):
                    return False
                
                # Check all parts before the wildcard
                for i in range(wildcard_index):
                    if pattern_parts[i] != target_parts[i]:
                        return False
                
                return True
            else:
                # * in the middle - not supported in this simple implementation
                return False
        
        # No wildcards - exact match required
        if len(pattern_parts) != len(target_parts):
            return False
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part != target_parts[i]:
                return False
        
        return True
    
    def _group_subscriptions_by_llm(self, subscriptions: List[Subscription]) -> Dict[LLMID, List[Subscription]]:
        """Group subscriptions by LLM ID for efficient delivery"""
        grouped = defaultdict(list)
        for subscription in subscriptions:
            grouped[subscription.llm_id].append(subscription)
        return dict(grouped)
    
    async def _deliver_to_llm(self, message: Message, llm_id: LLMID, subscriptions: List[Subscription]) -> bool:
        """Deliver message to a specific LLM with all matching subscriptions"""
        handler = self._delivery_handlers.get(llm_id)
        if not handler:
            logger.warning(f"No delivery handler for LLM {llm_id}")
            return False
        
        try:
            # Create delivery context with subscription information
            delivery_context = {
                'message': message.to_dict(),
                'subscriptions': [sub.to_dict() for sub in subscriptions],
                'delivery_mode': 'realtime',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Call the handler
            if asyncio.iscoroutinefunction(handler):
                await handler(delivery_context)
            else:
                handler(delivery_context)
            
            # Update subscription activity
            for subscription in subscriptions:
                subscription.increment_message_count()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to deliver message {message.id} to LLM {llm_id}: {e}")
            return False
    
    async def _publish_to_redis_channels(self, message: Message) -> None:
        """Publish message to Redis pub/sub channels for external subscribers"""
        try:
            message_data = message.to_dict()
            addressing_mode = message.routing_info.addressing_mode
            target = message.routing_info.target
            
            # Determine channels to publish to
            channels = []
            
            if addressing_mode == AddressingMode.DIRECT:
                channels.append(f"mailbox:{target}")
            elif addressing_mode == AddressingMode.TOPIC:
                channels.append(f"topic:{target}")
            elif addressing_mode == AddressingMode.BROADCAST:
                channels.append("broadcast:all")
                # Also publish to all active mailboxes
                active_mailboxes = await self._get_active_mailboxes()
                for mailbox in active_mailboxes:
                    channels.append(f"mailbox:{mailbox}")
            
            # Publish to each channel
            for channel in channels:
                try:
                    await self.pubsub_manager.publish(channel, message_data)
                except Exception as e:
                    logger.error(f"Failed to publish to Redis channel {channel}: {e}")
                    
        except Exception as e:
            logger.error(f"Error publishing message {message.id} to Redis channels: {e}")
    
    async def _get_active_mailboxes(self) -> List[str]:
        """Get list of active mailboxes for broadcast"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                keys = await redis_conn.keys("mailbox:*:metadata")
                mailboxes = []
                for key in keys:
                    # Extract mailbox name from key pattern "mailbox:name:metadata"
                    parts = key.split(':')
                    if len(parts) >= 3:
                        mailbox_name = parts[1]
                        mailboxes.append(mailbox_name)
                return mailboxes
        except Exception as e:
            logger.error(f"Error getting active mailboxes: {e}")
            return []
    
    async def _refresh_pattern_cache(self) -> None:
        """Refresh the pattern subscription cache"""
        if not self.enable_pattern_caching:
            return
        
        async with self._cache_lock:
            try:
                # Get all subscriptions with patterns
                pattern_subscriptions = []
                for llm_id in self._delivery_handlers.keys():
                    llm_subscriptions = await self.subscription_manager.get_active_subscriptions(llm_id)
                    for sub in llm_subscriptions:
                        if sub.pattern and sub.active:
                            pattern_subscriptions.append(sub)
                
                # Group by pattern
                new_cache = defaultdict(list)
                for sub in pattern_subscriptions:
                    new_cache[sub.pattern].append(sub)
                
                self._pattern_cache = dict(new_cache)
                self._cache_last_updated = datetime.utcnow()
                
                logger.debug(f"Refreshed pattern cache with {len(self._pattern_cache)} patterns")
                
            except Exception as e:
                logger.error(f"Error refreshing pattern cache: {e}")
    
    async def _pattern_cache_refresh_loop(self) -> None:
        """Background task to refresh pattern cache periodically"""
        logger.info("Starting pattern cache refresh loop")
        
        while self._running:
            try:
                await asyncio.sleep(self._cache_ttl_seconds)
                
                if not self._running:
                    break
                
                await self._refresh_pattern_cache()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in pattern cache refresh loop: {e}")
        
        logger.info("Pattern cache refresh loop stopped")
    
    async def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get real-time delivery statistics"""
        return {
            "messages_broadcast": self._stats.messages_broadcast,
            "subscribers_reached": self._stats.subscribers_reached,
            "pattern_matches": self._stats.pattern_matches,
            "delivery_failures": self._stats.delivery_failures,
            "average_latency_ms": round(self._stats.average_latency_ms, 2),
            "active_handlers": len(self._delivery_handlers),
            "pattern_cache_size": len(self._pattern_cache),
            "cache_last_updated": self._cache_last_updated.isoformat(),
            "running": self._running
        }
    
    async def test_pattern_matching(self, pattern: str, targets: List[str]) -> Dict[str, bool]:
        """Test pattern matching against multiple targets (for debugging)"""
        results = {}
        for target in targets:
            # Test simple fnmatch
            simple_match = fnmatch.fnmatch(target, pattern)
            
            # Test hierarchical matching
            hierarchical_match = self._matches_hierarchical_pattern(target, pattern)
            
            results[target] = simple_match or hierarchical_match
        
        return results