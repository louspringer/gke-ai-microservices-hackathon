"""
Redis Pub/Sub Operations Wrapper for Inter-LLM Mailbox System

This module provides a high-level wrapper for Redis pub/sub operations
with error handling, pattern subscriptions, and message processing.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, Set, List, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError

from .redis_manager import RedisConnectionManager


logger = logging.getLogger(__name__)


class SubscriptionType(Enum):
    """Types of Redis subscriptions"""
    CHANNEL = "channel"
    PATTERN = "pattern"


@dataclass
class PubSubMessage:
    """Represents a pub/sub message"""
    type: str
    channel: str
    pattern: Optional[str]
    data: Any
    timestamp: float


class RedisPubSubManager:
    """
    High-level wrapper for Redis pub/sub operations.
    
    Provides:
    - Channel and pattern-based subscriptions
    - Message serialization/deserialization
    - Error handling and reconnection
    - Subscription lifecycle management
    """
    
    def __init__(self, redis_manager: RedisConnectionManager):
        self.redis_manager = redis_manager
        self._pubsub: Optional[redis.client.PubSub] = None
        self._subscriptions: Dict[str, SubscriptionType] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
        self._subscription_lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the pub/sub manager and begin listening for messages"""
        if self._running:
            return
        
        logger.info("Starting Redis pub/sub manager")
        
        async with self.redis_manager.get_connection() as redis_conn:
            self._pubsub = redis_conn.pubsub()
            self._running = True
            
            # Start message listening task
            self._listen_task = asyncio.create_task(self._listen_loop())
            
        logger.info("Redis pub/sub manager started")
    
    async def stop(self) -> None:
        """Stop the pub/sub manager and cleanup resources"""
        if not self._running:
            return
        
        logger.info("Stopping Redis pub/sub manager")
        self._running = False
        
        # Cancel listening task
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        
        # Close pub/sub connection
        if self._pubsub:
            try:
                await self._pubsub.aclose()
            except AttributeError:
                # Fallback for older Redis versions
                await self._pubsub.close()
            self._pubsub = None
        
        # Clear subscriptions
        self._subscriptions.clear()
        self._message_handlers.clear()
        
        logger.info("Redis pub/sub manager stopped")
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish a message to a Redis channel.
        
        Args:
            channel: Target channel name
            message: Message data to publish
            
        Returns:
            Number of subscribers that received the message
            
        Raises:
            ConnectionError: If Redis connection fails
        """
        try:
            serialized_message = json.dumps(message)
            
            async with self.redis_manager.get_connection() as redis_conn:
                result = await redis_conn.publish(channel, serialized_message)
                
            logger.debug(f"Published message to channel '{channel}', {result} subscribers notified")
            return result
            
        except Exception as e:
            logger.error(f"Failed to publish message to channel '{channel}': {e}")
            raise
    
    async def subscribe_channel(self, channel: str, handler: Optional[Callable] = None) -> None:
        """
        Subscribe to a specific Redis channel.
        
        Args:
            channel: Channel name to subscribe to
            handler: Optional message handler function
        """
        async with self._subscription_lock:
            if not self._running:
                raise RuntimeError("Pub/sub manager not started")
            
            if channel in self._subscriptions:
                logger.warning(f"Already subscribed to channel '{channel}'")
                return
            
            try:
                await self._pubsub.subscribe(channel)
                self._subscriptions[channel] = SubscriptionType.CHANNEL
                
                if handler:
                    self._message_handlers[channel] = handler
                
                logger.info(f"Subscribed to channel '{channel}'")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to channel '{channel}': {e}")
                raise
    
    async def subscribe_pattern(self, pattern: str, handler: Optional[Callable] = None) -> None:
        """
        Subscribe to channels matching a pattern.
        
        Args:
            pattern: Pattern to match channel names (supports wildcards)
            handler: Optional message handler function
        """
        async with self._subscription_lock:
            if not self._running:
                raise RuntimeError("Pub/sub manager not started")
            
            if pattern in self._subscriptions:
                logger.warning(f"Already subscribed to pattern '{pattern}'")
                return
            
            try:
                await self._pubsub.psubscribe(pattern)
                self._subscriptions[pattern] = SubscriptionType.PATTERN
                
                if handler:
                    self._message_handlers[pattern] = handler
                
                logger.info(f"Subscribed to pattern '{pattern}'")
                
            except Exception as e:
                logger.error(f"Failed to subscribe to pattern '{pattern}': {e}")
                raise
    
    async def unsubscribe_channel(self, channel: str) -> None:
        """
        Unsubscribe from a specific channel.
        
        Args:
            channel: Channel name to unsubscribe from
        """
        async with self._subscription_lock:
            if channel not in self._subscriptions:
                logger.warning(f"Not subscribed to channel '{channel}'")
                return
            
            if self._subscriptions[channel] != SubscriptionType.CHANNEL:
                logger.warning(f"'{channel}' is not a channel subscription")
                return
            
            try:
                await self._pubsub.unsubscribe(channel)
                del self._subscriptions[channel]
                
                if channel in self._message_handlers:
                    del self._message_handlers[channel]
                
                logger.info(f"Unsubscribed from channel '{channel}'")
                
            except Exception as e:
                logger.error(f"Failed to unsubscribe from channel '{channel}': {e}")
                raise
    
    async def unsubscribe_pattern(self, pattern: str) -> None:
        """
        Unsubscribe from a pattern.
        
        Args:
            pattern: Pattern to unsubscribe from
        """
        async with self._subscription_lock:
            if pattern not in self._subscriptions:
                logger.warning(f"Not subscribed to pattern '{pattern}'")
                return
            
            if self._subscriptions[pattern] != SubscriptionType.PATTERN:
                logger.warning(f"'{pattern}' is not a pattern subscription")
                return
            
            try:
                await self._pubsub.punsubscribe(pattern)
                del self._subscriptions[pattern]
                
                if pattern in self._message_handlers:
                    del self._message_handlers[pattern]
                
                logger.info(f"Unsubscribed from pattern '{pattern}'")
                
            except Exception as e:
                logger.error(f"Failed to unsubscribe from pattern '{pattern}': {e}")
                raise
    
    async def _listen_loop(self) -> None:
        """Main message listening loop"""
        logger.info("Starting pub/sub message listening loop")
        
        while self._running:
            try:
                if not self._pubsub:
                    logger.warning("Pub/sub connection not available, waiting...")
                    await asyncio.sleep(1.0)
                    continue
                
                # Only try to get messages if we have subscriptions
                if not self._subscriptions:
                    await asyncio.sleep(1.0)
                    continue
                
                # Get next message with timeout
                message = await asyncio.wait_for(
                    self._pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0
                )
                
                if message:
                    await self._process_message(message)
                    
            except asyncio.TimeoutError:
                # Timeout is expected, continue listening
                continue
            except asyncio.CancelledError:
                break
            except ConnectionError as e:
                logger.warning(f"Redis connection lost during pub/sub listening: {e}")
                await self._handle_connection_loss()
            except Exception as e:
                logger.error(f"Error in pub/sub listening loop: {e}")
                await asyncio.sleep(1.0)  # Brief pause before retrying
        
        logger.info("Pub/sub message listening loop stopped")
    
    async def _process_message(self, raw_message: Dict[str, Any]) -> None:
        """Process a received pub/sub message"""
        try:
            # Parse message data
            message_data = raw_message.get('data')
            if not message_data:
                return
            
            # Deserialize JSON data
            try:
                parsed_data = json.loads(message_data) if isinstance(message_data, str) else message_data
            except json.JSONDecodeError:
                parsed_data = message_data
            
            # Create structured message
            pubsub_message = PubSubMessage(
                type=raw_message.get('type', 'message'),
                channel=raw_message.get('channel', ''),
                pattern=raw_message.get('pattern'),
                data=parsed_data,
                timestamp=asyncio.get_event_loop().time()
            )
            
            # Find and call appropriate handler
            handler = None
            
            # Check for specific channel handler
            if pubsub_message.channel in self._message_handlers:
                handler = self._message_handlers[pubsub_message.channel]
            
            # Check for pattern handler
            elif pubsub_message.pattern and pubsub_message.pattern in self._message_handlers:
                handler = self._message_handlers[pubsub_message.pattern]
            
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(pubsub_message)
                    else:
                        handler(pubsub_message)
                except Exception as e:
                    logger.error(f"Error in message handler for {pubsub_message.channel}: {e}")
            else:
                logger.debug(f"No handler for message on channel '{pubsub_message.channel}'")
                
        except Exception as e:
            logger.error(f"Error processing pub/sub message: {e}")
    
    async def _handle_connection_loss(self) -> None:
        """Handle Redis connection loss during pub/sub operations"""
        logger.warning("Handling pub/sub connection loss")
        
        # Close current pub/sub connection
        if self._pubsub:
            try:
                await self._pubsub.aclose()
            except AttributeError:
                # Fallback for older Redis versions
                try:
                    await self._pubsub.close()
                except Exception:
                    pass
            except Exception:
                pass
            self._pubsub = None
        
        # Wait for Redis manager to reconnect
        max_wait = 30.0
        wait_interval = 1.0
        waited = 0.0
        
        while waited < max_wait and self._running:
            if self.redis_manager.is_connected:
                break
            await asyncio.sleep(wait_interval)
            waited += wait_interval
        
        if not self.redis_manager.is_connected:
            logger.error("Redis reconnection timeout during pub/sub recovery")
            return
        
        # Recreate pub/sub connection and restore subscriptions
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                self._pubsub = redis_conn.pubsub()
                
                # Restore all subscriptions
                for subscription, sub_type in self._subscriptions.items():
                    if sub_type == SubscriptionType.CHANNEL:
                        await self._pubsub.subscribe(subscription)
                    elif sub_type == SubscriptionType.PATTERN:
                        await self._pubsub.psubscribe(subscription)
                
                logger.info("Pub/sub subscriptions restored after reconnection")
                
        except Exception as e:
            logger.error(f"Failed to restore pub/sub subscriptions: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if pub/sub manager is running"""
        return self._running
    
    @property
    def active_subscriptions(self) -> Dict[str, str]:
        """Get list of active subscriptions"""
        return {sub: sub_type.value for sub, sub_type in self._subscriptions.items()}
    
    async def get_subscription_info(self) -> Dict[str, Any]:
        """Get pub/sub subscription information for monitoring"""
        return {
            "running": self._running,
            "subscriptions": self.active_subscriptions,
            "handlers_count": len(self._message_handlers),
            "pubsub_connected": self._pubsub is not None
        }