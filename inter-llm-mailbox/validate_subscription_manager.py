#!/usr/bin/env python3
"""
Validation script for Subscription Manager implementation

This script validates the Subscription Manager functionality including:
- Subscription creation and lifecycle management
- Redis pub/sub subscription handling
- Connection state tracking and recovery logic
- Message delivery and queuing
"""

import asyncio
import logging
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock

# Add src to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.subscription_manager import SubscriptionManager, ConnectionState, DeliveryResult
from src.core.redis_manager import RedisConnectionManager
from src.core.redis_pubsub import RedisPubSubManager
from src.models.subscription import Subscription, SubscriptionOptions, MessageFilter
from src.models.enums import DeliveryMode


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockRedisConnection:
    """Mock Redis connection for testing"""
    
    def __init__(self):
        self.data = {}
        self.pubsub_channels = set()
        self.pubsub_patterns = set()
    
    async def hset(self, key: str, mapping: Dict[str, Any]) -> int:
        """Mock hset operation"""
        self.data[key] = mapping.copy()
        return len(mapping)
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Mock hgetall operation"""
        return self.data.get(key, {})
    
    async def delete(self, key: str) -> int:
        """Mock delete operation"""
        if key in self.data:
            del self.data[key]
            return 1
        return 0
    
    async def keys(self, pattern: str) -> list:
        """Mock keys operation"""
        if pattern == "subscription:*":
            return [k for k in self.data.keys() if k.startswith("subscription:")]
        return []
    
    async def publish(self, channel: str, message: str) -> int:
        """Mock publish operation"""
        logger.info(f"Published to {channel}: {message}")
        return 1


class MockPubSub:
    """Mock Redis pub/sub for testing"""
    
    def __init__(self):
        self.subscriptions = set()
        self.pattern_subscriptions = set()
        self.messages = []
    
    async def subscribe(self, channel: str):
        """Mock subscribe operation"""
        self.subscriptions.add(channel)
        logger.info(f"Subscribed to channel: {channel}")
    
    async def psubscribe(self, pattern: str):
        """Mock pattern subscribe operation"""
        self.pattern_subscriptions.add(pattern)
        logger.info(f"Subscribed to pattern: {pattern}")
    
    async def unsubscribe(self, channel: str):
        """Mock unsubscribe operation"""
        self.subscriptions.discard(channel)
        logger.info(f"Unsubscribed from channel: {channel}")
    
    async def punsubscribe(self, pattern: str):
        """Mock pattern unsubscribe operation"""
        self.pattern_subscriptions.discard(pattern)
        logger.info(f"Unsubscribed from pattern: {pattern}")
    
    async def get_message(self, ignore_subscribe_messages=True):
        """Mock get message operation"""
        if self.messages:
            return self.messages.pop(0)
        return None
    
    async def aclose(self):
        """Mock close operation"""
        pass


class MockRedisManager:
    """Mock Redis connection manager"""
    
    def __init__(self):
        self.connection = MockRedisConnection()
        self.is_connected = True
    
    def get_connection(self):
        """Return mock connection context manager"""
        return MockConnectionContext(self.connection)


class MockConnectionContext:
    """Mock connection context manager"""
    
    def __init__(self, connection):
        self.connection = connection
    
    async def __aenter__(self):
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockPubSubManager:
    """Mock pub/sub manager"""
    
    def __init__(self):
        self.pubsub = MockPubSub()
        self.is_running = False
        self.active_subscriptions = {}
        self.handlers = {}
    
    async def start(self):
        """Start mock pub/sub manager"""
        self.is_running = True
        logger.info("Mock pub/sub manager started")
    
    async def stop(self):
        """Stop mock pub/sub manager"""
        self.is_running = False
        logger.info("Mock pub/sub manager stopped")
    
    async def subscribe_channel(self, channel: str, handler=None):
        """Mock channel subscription"""
        await self.pubsub.subscribe(channel)
        self.active_subscriptions[channel] = "channel"
        if handler:
            self.handlers[channel] = handler
    
    async def subscribe_pattern(self, pattern: str, handler=None):
        """Mock pattern subscription"""
        await self.pubsub.psubscribe(pattern)
        self.active_subscriptions[pattern] = "pattern"
        if handler:
            self.handlers[pattern] = handler
    
    async def unsubscribe_channel(self, channel: str):
        """Mock channel unsubscription"""
        await self.pubsub.unsubscribe(channel)
        self.active_subscriptions.pop(channel, None)
        self.handlers.pop(channel, None)
    
    async def unsubscribe_pattern(self, pattern: str):
        """Mock pattern unsubscription"""
        await self.pubsub.punsubscribe(pattern)
        self.active_subscriptions.pop(pattern, None)
        self.handlers.pop(pattern, None)
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Mock publish operation"""
        return await self.pubsub.connection.publish(channel, json.dumps(message))


async def test_subscription_creation():
    """Test subscription creation and management"""
    logger.info("Testing subscription creation...")
    
    redis_manager = MockRedisManager()
    pubsub_manager = MockPubSubManager()
    
    # Create subscription manager
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    
    # Mock the load/save methods to avoid Redis calls
    sub_manager._load_subscriptions = AsyncMock()
    sub_manager._save_subscriptions = AsyncMock()
    sub_manager._save_subscription = AsyncMock()
    sub_manager._delete_subscription = AsyncMock()
    
    await sub_manager.start()
    
    try:
        # Test basic subscription creation
        llm_id = "llm-test-001"
        target = "test-mailbox"
        
        subscription = await sub_manager.create_subscription(llm_id, target)
        
        assert subscription.llm_id == llm_id
        assert subscription.target == target
        assert subscription.active is True
        assert subscription.id in sub_manager._subscriptions
        
        logger.info(f"✓ Created subscription: {subscription.id}")
        
        # Test pattern subscription
        pattern_sub = await sub_manager.create_subscription(
            llm_id, "pattern-*", pattern="pattern-*"
        )
        
        assert pattern_sub.pattern == "pattern-*"
        logger.info(f"✓ Created pattern subscription: {pattern_sub.id}")
        
        # Test subscription retrieval
        retrieved = await sub_manager.get_subscription(subscription.id)
        assert retrieved is not None
        assert retrieved.id == subscription.id
        
        logger.info("✓ Subscription retrieval works")
        
        # Test active subscriptions listing
        active_subs = await sub_manager.get_active_subscriptions(llm_id)
        assert len(active_subs) == 2
        
        logger.info("✓ Active subscriptions listing works")
        
        # Test subscription removal
        removed = await sub_manager.remove_subscription(subscription.id)
        assert removed is True
        assert subscription.id not in sub_manager._subscriptions
        
        logger.info("✓ Subscription removal works")
        
        logger.info("✓ Subscription creation tests passed")
        
    finally:
        await sub_manager.stop()


async def test_connection_state_management():
    """Test connection state tracking and recovery"""
    logger.info("Testing connection state management...")
    
    redis_manager = MockRedisManager()
    pubsub_manager = MockPubSubManager()
    
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    sub_manager._load_subscriptions = lambda: None
    sub_manager._save_subscriptions = lambda: None
    
    await sub_manager.start()
    
    try:
        llm_id = "llm-test-002"
        target = "test-mailbox"
        
        # Create subscription
        subscription = await sub_manager.create_subscription(llm_id, target)
        
        # Test connection state creation
        await sub_manager._ensure_connection_state(llm_id)
        assert llm_id in sub_manager._connection_states
        
        connection_state = sub_manager._connection_states[llm_id]
        assert connection_state.connected is True
        assert connection_state.reconnect_count == 0
        
        logger.info("✓ Connection state created")
        
        # Test connection loss handling
        await sub_manager.handle_connection_loss(llm_id)
        
        assert connection_state.connected is False
        assert connection_state.reconnect_count == 1
        assert subscription.active is False
        
        logger.info("✓ Connection loss handled")
        
        # Test connection restoration
        await sub_manager.handle_connection_restored(llm_id)
        
        assert connection_state.connected is True
        assert subscription.active is True
        
        logger.info("✓ Connection restoration handled")
        
        logger.info("✓ Connection state management tests passed")
        
    finally:
        await sub_manager.stop()


async def test_message_delivery():
    """Test message delivery functionality"""
    logger.info("Testing message delivery...")
    
    redis_manager = MockRedisManager()
    pubsub_manager = MockPubSubManager()
    
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    sub_manager._load_subscriptions = lambda: None
    sub_manager._save_subscriptions = lambda: None
    
    await sub_manager.start()
    
    try:
        llm_id = "llm-test-003"
        target = "test-mailbox"
        
        # Create subscription with realtime delivery
        options = SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        subscription = await sub_manager.create_subscription(llm_id, target, options=options)
        
        # Track delivered messages
        delivered_messages = []
        
        async def delivery_handler(message, subscription):
            delivered_messages.append((message, subscription))
            logger.info(f"Delivered message: {message}")
        
        # Register delivery handler
        await sub_manager.register_delivery_handler(llm_id, delivery_handler)
        
        # Test message delivery
        test_message = {"content": "Hello, LLM!", "timestamp": datetime.utcnow().isoformat()}
        results = await sub_manager.deliver_message(test_message, target)
        
        assert len(results) == 1
        assert results[0].success is True
        assert len(delivered_messages) == 1
        assert delivered_messages[0][0] == test_message
        
        logger.info("✓ Real-time message delivery works")
        
        # Test offline message queuing
        await sub_manager.handle_connection_loss(llm_id)
        
        offline_message = {"content": "Offline message", "timestamp": datetime.utcnow().isoformat()}
        results = await sub_manager.deliver_message(offline_message, target)
        
        assert len(results) == 1
        assert results[0].success is True
        
        # Check message was queued
        connection_state = sub_manager._connection_states[llm_id]
        assert len(connection_state.message_queue) == 1
        assert connection_state.message_queue[0]['message'] == offline_message
        
        logger.info("✓ Offline message queuing works")
        
        # Test message delivery on reconnection
        delivered_messages.clear()
        await sub_manager.handle_connection_restored(llm_id)
        
        # Give a moment for async delivery
        await asyncio.sleep(0.1)
        
        assert len(delivered_messages) == 1
        assert delivered_messages[0][0] == offline_message
        assert len(connection_state.message_queue) == 0
        
        logger.info("✓ Queued message delivery on reconnection works")
        
        logger.info("✓ Message delivery tests passed")
        
    finally:
        await sub_manager.stop()


async def test_message_filtering():
    """Test message filtering functionality"""
    logger.info("Testing message filtering...")
    
    redis_manager = MockRedisManager()
    pubsub_manager = MockPubSubManager()
    
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    sub_manager._load_subscriptions = lambda: None
    sub_manager._save_subscriptions = lambda: None
    
    await sub_manager.start()
    
    try:
        llm_id = "llm-test-004"
        target = "test-mailbox"
        
        # Create subscription with message filter
        message_filter = MessageFilter(
            content_types=["text/plain"],
            keywords=["important"]
        )
        options = SubscriptionOptions(message_filter=message_filter)
        subscription = await sub_manager.create_subscription(llm_id, target, options=options)
        
        # Track delivered messages
        delivered_messages = []
        
        async def delivery_handler(message, subscription):
            delivered_messages.append(message)
        
        await sub_manager.register_delivery_handler(llm_id, delivery_handler)
        
        # Test message that matches filter
        matching_message = {
            "content": "This is an important message",
            "content_type": "text/plain"
        }
        results = await sub_manager.deliver_message(matching_message, target)
        
        assert len(results) == 1
        assert results[0].success is True
        assert len(delivered_messages) == 1
        
        logger.info("✓ Message filter allows matching messages")
        
        # Test message that doesn't match filter
        delivered_messages.clear()
        non_matching_message = {
            "content": "This is a regular message",
            "content_type": "application/json"
        }
        results = await sub_manager.deliver_message(non_matching_message, target)
        
        # Should have no results since message doesn't match filter
        assert len(results) == 0
        assert len(delivered_messages) == 0
        
        logger.info("✓ Message filter blocks non-matching messages")
        
        logger.info("✓ Message filtering tests passed")
        
    finally:
        await sub_manager.stop()


async def test_pattern_matching():
    """Test pattern-based subscription matching"""
    logger.info("Testing pattern matching...")
    
    redis_manager = MockRedisManager()
    pubsub_manager = MockPubSubManager()
    
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    sub_manager._load_subscriptions = lambda: None
    sub_manager._save_subscriptions = lambda: None
    
    await sub_manager.start()
    
    try:
        llm_id = "llm-test-005"
        
        # Create pattern subscription
        pattern = "test-*"
        subscription = await sub_manager.create_subscription(llm_id, pattern, pattern=pattern)
        
        # Test pattern matching
        matching_targets = ["test-mailbox", "test-topic", "test-123"]
        non_matching_targets = ["other-mailbox", "prod-test"]
        
        for target in matching_targets:
            matches = subscription.matches_target(target)
            assert matches is True, f"Pattern should match {target}"
        
        for target in non_matching_targets:
            matches = subscription.matches_target(target)
            assert matches is False, f"Pattern should not match {target}"
        
        logger.info("✓ Pattern matching works correctly")
        
        # Test finding matching subscriptions
        matching_subs = await sub_manager._find_matching_subscriptions("test-mailbox")
        assert len(matching_subs) == 1
        assert matching_subs[0].id == subscription.id
        
        non_matching_subs = await sub_manager._find_matching_subscriptions("other-mailbox")
        assert len(non_matching_subs) == 0
        
        logger.info("✓ Subscription pattern matching works")
        
        logger.info("✓ Pattern matching tests passed")
        
    finally:
        await sub_manager.stop()


async def test_statistics_and_monitoring():
    """Test statistics and monitoring functionality"""
    logger.info("Testing statistics and monitoring...")
    
    redis_manager = MockRedisManager()
    pubsub_manager = MockPubSubManager()
    
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    sub_manager._load_subscriptions = lambda: None
    sub_manager._save_subscriptions = lambda: None
    
    await sub_manager.start()
    
    try:
        # Create multiple subscriptions and connections
        llm1 = "llm-001"
        llm2 = "llm-002"
        
        sub1 = await sub_manager.create_subscription(llm1, "mailbox1")
        sub2 = await sub_manager.create_subscription(llm2, "mailbox2")
        
        await sub_manager.register_delivery_handler(llm1, lambda m, s: None)
        await sub_manager.register_delivery_handler(llm2, lambda m, s: None)
        
        # Simulate one LLM going offline
        await sub_manager.handle_connection_loss(llm1)
        
        # Queue a message
        await sub_manager._queue_message(llm1, {"test": "message"}, sub1)
        
        # Get statistics
        stats = await sub_manager.get_statistics()
        
        assert stats["total_subscriptions"] == 2
        assert stats["active_subscriptions"] == 1  # One is offline
        assert stats["total_llms"] == 2
        assert stats["connected_llms"] == 1  # One is offline
        assert stats["total_queued_messages"] == 1
        assert stats["running"] is True
        
        logger.info(f"✓ Statistics: {stats}")
        
        logger.info("✓ Statistics and monitoring tests passed")
        
    finally:
        await sub_manager.stop()


async def run_all_tests():
    """Run all validation tests"""
    logger.info("Starting Subscription Manager validation tests...")
    
    tests = [
        test_subscription_creation,
        test_connection_state_management,
        test_message_delivery,
        test_message_filtering,
        test_pattern_matching,
        test_statistics_and_monitoring
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
            failed += 1
    
    logger.info(f"\nValidation Results:")
    logger.info(f"✓ Passed: {passed}")
    logger.info(f"✗ Failed: {failed}")
    logger.info(f"Total: {len(tests)}")
    
    if failed == 0:
        logger.info("🎉 All Subscription Manager validation tests passed!")
        return True
    else:
        logger.error("❌ Some validation tests failed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)