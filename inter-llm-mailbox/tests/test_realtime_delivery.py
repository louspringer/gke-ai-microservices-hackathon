"""
Integration tests for real-time message delivery functionality.

Tests requirements 2.2, 2.3, and 5.2:
- Real-time message delivery to active subscribers
- Pattern-based subscription support with wildcards
- Immediate delivery for subscribed LLMs
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from src.core.realtime_delivery import RealtimeDeliveryService, BroadcastResult
from src.core.enhanced_message_router import EnhancedMessageRouter
from src.core.redis_manager import RedisConnectionManager
from src.core.redis_pubsub import RedisPubSubManager
from src.core.subscription_manager import SubscriptionManager
from src.models.message import Message, RoutingInfo
from src.models.subscription import Subscription, SubscriptionOptions
from src.models.enums import (
    ContentType, AddressingMode, Priority, DeliveryMode
)


class MockRedisConnection:
    """Mock Redis connection for testing"""
    
    def __init__(self):
        self.data = {}
        self.pubsub_channels = {}
        self.published_messages = []
    
    async def hset(self, key, mapping=None, **kwargs):
        if mapping:
            self.data[key] = mapping
        else:
            self.data[key] = kwargs
        return len(mapping) if mapping else len(kwargs)
    
    async def hgetall(self, key):
        return self.data.get(key, {})
    
    async def keys(self, pattern):
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def zadd(self, key, mapping):
        if key not in self.data:
            self.data[key] = {}
        self.data[key].update(mapping)
        return len(mapping)
    
    async def zcard(self, key):
        return len(self.data.get(key, {}))
    
    async def publish(self, channel, message):
        self.published_messages.append({'channel': channel, 'message': message})
        return len(self.pubsub_channels.get(channel, []))
    
    async def delete(self, *keys):
        for key in keys:
            self.data.pop(key, None)
        return len(keys)
    
    async def expire(self, key, seconds):
        return True


class MockRedisManager:
    """Mock Redis manager for testing"""
    
    def __init__(self):
        self.connection = MockRedisConnection()
        self.is_connected = True
    
    def get_connection(self):
        return self
    
    async def __aenter__(self):
        return self.connection
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockPubSubManager:
    """Mock pub/sub manager for testing"""
    
    def __init__(self):
        self.subscriptions = {}
        self.published_messages = []
        self.is_running = True
        self.active_subscriptions = {}
    
    async def start(self):
        self.is_running = True
    
    async def stop(self):
        self.is_running = False
    
    async def publish(self, channel, message):
        self.published_messages.append({'channel': channel, 'message': message})
        return len(self.subscriptions.get(channel, []))
    
    async def subscribe_channel(self, channel, handler=None):
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        if handler:
            self.subscriptions[channel].append(handler)
        self.active_subscriptions[channel] = 'channel'
    
    async def subscribe_pattern(self, pattern, handler=None):
        if pattern not in self.subscriptions:
            self.subscriptions[pattern] = []
        if handler:
            self.subscriptions[pattern].append(handler)
        self.active_subscriptions[pattern] = 'pattern'
    
    async def unsubscribe_channel(self, channel):
        self.subscriptions.pop(channel, None)
        self.active_subscriptions.pop(channel, None)
    
    async def unsubscribe_pattern(self, pattern):
        self.subscriptions.pop(pattern, None)
        self.active_subscriptions.pop(pattern, None)


@pytest.fixture
async def redis_manager():
    """Create mock Redis manager"""
    return MockRedisManager()


@pytest.fixture
async def pubsub_manager():
    """Create mock pub/sub manager"""
    return MockPubSubManager()


@pytest.fixture
async def subscription_manager(redis_manager, pubsub_manager):
    """Create subscription manager with mocks"""
    manager = SubscriptionManager(redis_manager, pubsub_manager)
    await manager.start()
    return manager


@pytest.fixture
async def realtime_delivery(redis_manager, pubsub_manager, subscription_manager):
    """Create real-time delivery service"""
    service = RealtimeDeliveryService(redis_manager, pubsub_manager, subscription_manager)
    await service.start()
    return service


@pytest.fixture
async def enhanced_router(redis_manager, pubsub_manager, subscription_manager):
    """Create enhanced message router"""
    router = EnhancedMessageRouter(redis_manager, pubsub_manager, subscription_manager)
    await router.start()
    return router


@pytest.fixture
def sample_message():
    """Create a sample message for testing"""
    routing_info = RoutingInfo(
        addressing_mode=AddressingMode.DIRECT,
        target="test-mailbox",
        priority=Priority.NORMAL
    )
    
    return Message.create(
        sender_id="test-llm-1",
        content="Hello, World!",
        content_type=ContentType.TEXT,
        routing_info=routing_info
    )


@pytest.fixture
def topic_message():
    """Create a topic message for testing"""
    routing_info = RoutingInfo(
        addressing_mode=AddressingMode.TOPIC,
        target="ai.models.gpt4",
        priority=Priority.NORMAL
    )
    
    return Message.create(
        sender_id="test-llm-1",
        content={"query": "What is AI?", "model": "gpt4"},
        content_type=ContentType.JSON,
        routing_info=routing_info
    )


class TestRealtimeDeliveryService:
    """Test the real-time delivery service"""
    
    async def test_service_lifecycle(self, realtime_delivery):
        """Test service start/stop lifecycle"""
        assert realtime_delivery._running
        
        await realtime_delivery.stop()
        assert not realtime_delivery._running
        
        await realtime_delivery.start()
        assert realtime_delivery._running
    
    async def test_register_delivery_handler(self, realtime_delivery):
        """Test registering and unregistering delivery handlers"""
        handler = AsyncMock()
        llm_id = "test-llm-1"
        
        # Register handler
        await realtime_delivery.register_delivery_handler(llm_id, handler)
        assert llm_id in realtime_delivery._delivery_handlers
        
        # Unregister handler
        await realtime_delivery.unregister_delivery_handler(llm_id)
        assert llm_id not in realtime_delivery._delivery_handlers
    
    async def test_broadcast_message_no_subscribers(self, realtime_delivery, sample_message):
        """Test broadcasting message with no subscribers"""
        result = await realtime_delivery.broadcast_message(sample_message)
        
        assert isinstance(result, BroadcastResult)
        assert result.message_id == sample_message.id
        assert result.subscribers_reached == 0
        assert result.pattern_matches == 0
        assert result.delivery_failures == 0
    
    async def test_broadcast_message_with_subscribers(self, realtime_delivery, subscription_manager, sample_message):
        """Test broadcasting message to active subscribers"""
        # Create mock handler
        handler = AsyncMock()
        llm_id = "test-llm-1"
        
        # Register handler
        await realtime_delivery.register_delivery_handler(llm_id, handler)
        
        # Create subscription
        subscription = await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Broadcast message
        result = await realtime_delivery.broadcast_message(sample_message)
        
        # Verify results
        assert result.subscribers_reached == 1
        assert result.delivery_failures == 0
        
        # Verify handler was called
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args['message']['id'] == sample_message.id
        assert len(call_args['subscriptions']) == 1
    
    async def test_pattern_based_subscription(self, realtime_delivery, subscription_manager, topic_message):
        """Test pattern-based subscription matching"""
        # Create mock handler
        handler = AsyncMock()
        llm_id = "test-llm-1"
        
        # Register handler
        await realtime_delivery.register_delivery_handler(llm_id, handler)
        
        # Create pattern subscription
        subscription = await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="ai.models.*",  # This should match "ai.models.gpt4"
            pattern="ai.models.*",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Broadcast message
        result = await realtime_delivery.broadcast_message(topic_message)
        
        # Verify pattern matching worked
        assert result.subscribers_reached == 1
        assert result.pattern_matches == 1
        
        # Verify handler was called
        handler.assert_called_once()
    
    async def test_hierarchical_pattern_matching(self, realtime_delivery):
        """Test hierarchical pattern matching"""
        # Test various pattern matching scenarios
        test_cases = [
            ("ai.models.*", ["ai.models.gpt4", "ai.models.claude"], [True, True]),
            ("ai.models.gpt*", ["ai.models.gpt4", "ai.models.gpt3"], [True, True]),
            ("ai.*", ["ai.models", "ai.training"], [True, True]),
            ("ai.**", ["ai.models.gpt4.turbo", "ai.training.data"], [True, True]),
            ("specific", ["specific", "specific.sub"], [True, False]),
        ]
        
        for pattern, targets, expected in test_cases:
            results = await realtime_delivery.test_pattern_matching(pattern, targets)
            for target, expected_match in zip(targets, expected):
                assert results[target] == expected_match, f"Pattern {pattern} vs {target}"
    
    async def test_wildcard_patterns(self, realtime_delivery, subscription_manager):
        """Test wildcard pattern subscriptions"""
        handler = AsyncMock()
        llm_id = "test-llm-1"
        
        await realtime_delivery.register_delivery_handler(llm_id, handler)
        
        # Create wildcard subscription
        subscription = await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="*",
            pattern="*",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Test with different message types
        messages = [
            Message.create("sender1", "test1", ContentType.TEXT, 
                         RoutingInfo(AddressingMode.DIRECT, "mailbox1")),
            Message.create("sender2", "test2", ContentType.TEXT,
                         RoutingInfo(AddressingMode.TOPIC, "topic1")),
        ]
        
        for message in messages:
            result = await realtime_delivery.broadcast_message(message)
            assert result.subscribers_reached >= 1  # Should match wildcard
    
    async def test_delivery_statistics(self, realtime_delivery, subscription_manager, sample_message):
        """Test delivery statistics tracking"""
        # Get initial stats
        initial_stats = await realtime_delivery.get_delivery_statistics()
        
        # Register handler and subscription
        handler = AsyncMock()
        llm_id = "test-llm-1"
        await realtime_delivery.register_delivery_handler(llm_id, handler)
        
        await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Broadcast message
        await realtime_delivery.broadcast_message(sample_message)
        
        # Check updated stats
        updated_stats = await realtime_delivery.get_delivery_statistics()
        assert updated_stats['messages_broadcast'] > initial_stats['messages_broadcast']
        assert updated_stats['subscribers_reached'] > initial_stats['subscribers_reached']


class TestEnhancedMessageRouter:
    """Test the enhanced message router with real-time delivery"""
    
    async def test_enhanced_routing_with_realtime_delivery(self, enhanced_router, subscription_manager, sample_message):
        """Test enhanced routing with real-time delivery"""
        # Register handler and subscription
        handler = AsyncMock()
        llm_id = "test-llm-1"
        await enhanced_router.register_llm_handler(llm_id, handler)
        
        await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Route message
        result = await enhanced_router.route_message(sample_message)
        
        # Should succeed with real-time delivery
        assert result.value == "success"
        
        # Handler should have been called
        handler.assert_called_once()
    
    async def test_enhanced_routing_fallback(self, enhanced_router, sample_message):
        """Test enhanced routing fallback when no real-time subscribers"""
        # Route message without any subscribers
        result = await enhanced_router.route_message(sample_message)
        
        # Should still succeed (queued for offline delivery)
        assert result.value in ["success", "queued"]
    
    async def test_get_active_subscribers(self, enhanced_router, subscription_manager):
        """Test getting active subscribers for a target"""
        # Create subscriptions
        llm_id = "test-llm-1"
        handler = AsyncMock()
        await enhanced_router.register_llm_handler(llm_id, handler)
        
        # Direct subscription
        await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Pattern subscription
        await subscription_manager.create_subscription(
            llm_id=llm_id,
            target="test-*",
            pattern="test-*",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        # Get subscribers
        subscribers = await enhanced_router.get_active_subscribers("test-mailbox")
        
        # Should find both subscriptions (direct and pattern match)
        assert len(subscribers) == 2
        assert all(sub['llm_id'] == llm_id for sub in subscribers)
    
    async def test_enhanced_statistics(self, enhanced_router):
        """Test enhanced statistics collection"""
        stats = await enhanced_router.get_enhanced_statistics()
        
        # Should include base router stats
        assert 'messages_routed' in stats
        
        # Should include real-time delivery stats
        assert 'realtime_delivery' in stats
        assert 'enhanced_routing' in stats
        
        # Real-time delivery stats should have expected fields
        rt_stats = stats['realtime_delivery']
        assert 'messages_broadcast' in rt_stats
        assert 'subscribers_reached' in rt_stats
        assert 'pattern_matches' in rt_stats


class TestIntegrationScenarios:
    """Integration tests for complex real-time messaging scenarios"""
    
    async def test_multi_llm_broadcast(self, enhanced_router, subscription_manager, sample_message):
        """Test broadcasting to multiple LLM instances"""
        # Register multiple LLMs
        llm_handlers = {}
        for i in range(3):
            llm_id = f"test-llm-{i+1}"
            handler = AsyncMock()
            llm_handlers[llm_id] = handler
            await enhanced_router.register_llm_handler(llm_id, handler)
            
            # Each LLM subscribes to the same mailbox
            await subscription_manager.create_subscription(
                llm_id=llm_id,
                target="test-mailbox",
                options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
            )
        
        # Route message
        result = await enhanced_router.route_message(sample_message)
        assert result.value == "success"
        
        # All handlers should have been called
        for handler in llm_handlers.values():
            handler.assert_called_once()
    
    async def test_topic_based_group_communication(self, enhanced_router, subscription_manager):
        """Test topic-based group communication (requirement 5.2)"""
        # Create topic message
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.TOPIC,
            target="ai.discussion.ethics",
            priority=Priority.NORMAL
        )
        
        topic_message = Message.create(
            sender_id="moderator-llm",
            content={"topic": "AI Ethics", "question": "Should AI have rights?"},
            content_type=ContentType.JSON,
            routing_info=routing_info
        )
        
        # Register LLMs with different subscription patterns
        subscriptions = [
            ("ethics-expert", "ai.discussion.ethics"),  # Direct subscription
            ("general-ai", "ai.discussion.*"),          # Pattern subscription
            ("all-topics", "ai.*"),                     # Broader pattern
        ]
        
        handlers = {}
        for llm_id, pattern in subscriptions:
            handler = AsyncMock()
            handlers[llm_id] = handler
            await enhanced_router.register_llm_handler(llm_id, handler)
            
            await subscription_manager.create_subscription(
                llm_id=llm_id,
                target=pattern,
                pattern=pattern if "*" in pattern else None,
                options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
            )
        
        # Route topic message
        result = await enhanced_router.route_message(topic_message)
        assert result.value == "success"
        
        # All LLMs should receive the message
        for handler in handlers.values():
            handler.assert_called_once()
    
    async def test_mixed_delivery_modes(self, enhanced_router, subscription_manager, sample_message):
        """Test mixed delivery modes (realtime vs batch vs polling)"""
        # Register LLMs with different delivery modes
        delivery_modes = [
            ("realtime-llm", DeliveryMode.REALTIME),
            ("batch-llm", DeliveryMode.BATCH),
            ("polling-llm", DeliveryMode.POLLING),
        ]
        
        realtime_handler = None
        for llm_id, mode in delivery_modes:
            handler = AsyncMock()
            if mode == DeliveryMode.REALTIME:
                realtime_handler = handler
                await enhanced_router.register_llm_handler(llm_id, handler)
            
            await subscription_manager.create_subscription(
                llm_id=llm_id,
                target="test-mailbox",
                options=SubscriptionOptions(delivery_mode=mode)
            )
        
        # Route message
        result = await enhanced_router.route_message(sample_message)
        
        # Only realtime LLM should receive immediate delivery
        if realtime_handler:
            realtime_handler.assert_called_once()
    
    async def test_error_handling_in_delivery(self, enhanced_router, subscription_manager, sample_message):
        """Test error handling during message delivery"""
        # Create handler that raises exception
        failing_handler = AsyncMock(side_effect=Exception("Delivery failed"))
        working_handler = AsyncMock()
        
        # Register both handlers
        await enhanced_router.register_llm_handler("failing-llm", failing_handler)
        await enhanced_router.register_llm_handler("working-llm", working_handler)
        
        # Create subscriptions
        for llm_id in ["failing-llm", "working-llm"]:
            await subscription_manager.create_subscription(
                llm_id=llm_id,
                target="test-mailbox",
                options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
            )
        
        # Route message - should not fail completely due to one handler error
        result = await enhanced_router.route_message(sample_message)
        
        # Working handler should still be called
        working_handler.assert_called_once()
        
        # Check statistics for delivery failures
        stats = await enhanced_router.get_enhanced_statistics()
        rt_stats = stats['realtime_delivery']
        assert rt_stats['delivery_failures'] > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])