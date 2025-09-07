"""
Tests for Subscription Manager
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.subscription_manager import SubscriptionManager, ConnectionState, DeliveryResult
from src.core.redis_manager import RedisConnectionManager
from src.core.redis_pubsub import RedisPubSubManager, PubSubMessage
from src.models.subscription import Subscription, SubscriptionOptions, MessageFilter
from src.models.enums import DeliveryMode


@pytest.fixture
async def redis_manager():
    """Mock Redis connection manager"""
    manager = AsyncMock(spec=RedisConnectionManager)
    manager.is_connected = True
    
    # Mock Redis connection
    redis_conn = AsyncMock()
    manager.get_connection.return_value.__aenter__.return_value = redis_conn
    manager.get_connection.return_value.__aexit__.return_value = None
    
    return manager


@pytest.fixture
async def pubsub_manager():
    """Mock Redis pub/sub manager"""
    manager = AsyncMock(spec=RedisPubSubManager)
    manager.is_running = True
    manager.active_subscriptions = {}
    return manager


@pytest.fixture
async def subscription_manager(redis_manager, pubsub_manager):
    """Create subscription manager with mocked dependencies"""
    manager = SubscriptionManager(redis_manager, pubsub_manager)
    
    # Mock the load/save methods to avoid Redis calls during setup
    manager._load_subscriptions = AsyncMock()
    manager._save_subscriptions = AsyncMock()
    
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def sample_subscription_options():
    """Sample subscription options"""
    return SubscriptionOptions(
        delivery_mode=DeliveryMode.REALTIME,
        max_queue_size=100,
        auto_ack=True
    )


class TestSubscriptionManager:
    """Test cases for SubscriptionManager"""
    
    async def test_create_subscription_success(self, subscription_manager, sample_subscription_options):
        """Test successful subscription creation"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        subscription = await subscription_manager.create_subscription(
            llm_id=llm_id,
            target=target,
            options=sample_subscription_options
        )
        
        assert subscription.llm_id == llm_id
        assert subscription.target == target
        assert subscription.active is True
        assert subscription.id in subscription_manager._subscriptions
        assert subscription.id in subscription_manager._llm_subscriptions[llm_id]
        assert subscription.id in subscription_manager._target_subscriptions[target]
        
        # Verify pub/sub subscription was created
        subscription_manager.pubsub_manager.subscribe_channel.assert_called_once()
        call_args = subscription_manager.pubsub_manager.subscribe_channel.call_args
        assert call_args[0][0] == f"mailbox:{target}"
        assert callable(call_args[0][1])  # Handler should be callable
    
    async def test_create_pattern_subscription(self, subscription_manager):
        """Test creating a pattern-based subscription"""
        llm_id = "llm-123"
        target = "test-*"
        pattern = "test-*"
        
        subscription = await subscription_manager.create_subscription(
            llm_id=llm_id,
            target=target,
            pattern=pattern
        )
        
        assert subscription.pattern == pattern
        
        # Verify pattern subscription was created
        subscription_manager.pubsub_manager.subscribe_pattern.assert_called_once()
        call_args = subscription_manager.pubsub_manager.subscribe_pattern.call_args
        assert call_args[0][0] == pattern
        assert callable(call_args[0][1])  # Handler should be callable
    
    async def test_create_duplicate_subscription(self, subscription_manager):
        """Test creating duplicate subscription returns existing one"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Create first subscription
        sub1 = await subscription_manager.create_subscription(llm_id, target)
        
        # Create duplicate subscription
        sub2 = await subscription_manager.create_subscription(llm_id, target)
        
        assert sub1.id == sub2.id
        assert len(subscription_manager._subscriptions) == 1
    
    async def test_remove_subscription_success(self, subscription_manager):
        """Test successful subscription removal"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Create subscription
        subscription = await subscription_manager.create_subscription(llm_id, target)
        sub_id = subscription.id
        
        # Remove subscription
        result = await subscription_manager.remove_subscription(sub_id)
        
        assert result is True
        assert sub_id not in subscription_manager._subscriptions
        assert sub_id not in subscription_manager._llm_subscriptions[llm_id]
        assert sub_id not in subscription_manager._target_subscriptions[target]
        
        # Verify pub/sub unsubscription
        subscription_manager.pubsub_manager.unsubscribe_channel.assert_called_once_with(
            f"mailbox:{target}"
        )
    
    async def test_remove_nonexistent_subscription(self, subscription_manager):
        """Test removing non-existent subscription"""
        result = await subscription_manager.remove_subscription("nonexistent")
        assert result is False
    
    async def test_get_active_subscriptions(self, subscription_manager):
        """Test getting active subscriptions for an LLM"""
        llm_id = "llm-123"
        
        # Create multiple subscriptions
        sub1 = await subscription_manager.create_subscription(llm_id, "mailbox1")
        sub2 = await subscription_manager.create_subscription(llm_id, "mailbox2")
        sub3 = await subscription_manager.create_subscription("llm-456", "mailbox3")
        
        # Deactivate one subscription
        sub2.active = False
        
        active_subs = await subscription_manager.get_active_subscriptions(llm_id)
        
        assert len(active_subs) == 1
        assert active_subs[0].id == sub1.id
    
    async def test_get_subscription(self, subscription_manager):
        """Test getting specific subscription by ID"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        subscription = await subscription_manager.create_subscription(llm_id, target)
        
        retrieved = await subscription_manager.get_subscription(subscription.id)
        assert retrieved is not None
        assert retrieved.id == subscription.id
        
        # Test non-existent subscription
        nonexistent = await subscription_manager.get_subscription("nonexistent")
        assert nonexistent is None
    
    async def test_handle_connection_loss(self, subscription_manager):
        """Test handling connection loss"""
        llm_id = "llm-123"
        
        # Create subscription and connection state
        subscription = await subscription_manager.create_subscription(llm_id, "test-mailbox")
        await subscription_manager._ensure_connection_state(llm_id)
        
        # Handle connection loss
        await subscription_manager.handle_connection_loss(llm_id)
        
        connection_state = subscription_manager._connection_states[llm_id]
        assert connection_state.connected is False
        assert connection_state.reconnect_count == 1
        assert subscription.active is False
    
    async def test_handle_connection_restored(self, subscription_manager):
        """Test handling connection restoration"""
        llm_id = "llm-123"
        
        # Create subscription and simulate connection loss
        subscription = await subscription_manager.create_subscription(llm_id, "test-mailbox")
        await subscription_manager.handle_connection_loss(llm_id)
        
        # Queue a message while offline
        test_message = {"content": "test message"}
        await subscription_manager._queue_message(llm_id, test_message, subscription)
        
        # Register delivery handler
        handler = AsyncMock()
        await subscription_manager.register_delivery_handler(llm_id, handler)
        
        # Restore connection
        await subscription_manager.handle_connection_restored(llm_id)
        
        connection_state = subscription_manager._connection_states[llm_id]
        assert connection_state.connected is True
        assert subscription.active is True
        
        # Verify queued message was delivered
        handler.assert_called_once()
    
    async def test_register_delivery_handler(self, subscription_manager):
        """Test registering delivery handler"""
        llm_id = "llm-123"
        handler = AsyncMock()
        
        await subscription_manager.register_delivery_handler(llm_id, handler)
        
        assert subscription_manager._delivery_handlers[llm_id] == handler
        assert llm_id in subscription_manager._connection_states
    
    async def test_unregister_delivery_handler(self, subscription_manager):
        """Test unregistering delivery handler"""
        llm_id = "llm-123"
        handler = AsyncMock()
        
        await subscription_manager.register_delivery_handler(llm_id, handler)
        await subscription_manager.unregister_delivery_handler(llm_id)
        
        assert llm_id not in subscription_manager._delivery_handlers
    
    async def test_deliver_message_realtime(self, subscription_manager):
        """Test real-time message delivery"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Create subscription with realtime delivery
        options = SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        subscription = await subscription_manager.create_subscription(llm_id, target, options=options)
        
        # Register delivery handler
        handler = AsyncMock()
        await subscription_manager.register_delivery_handler(llm_id, handler)
        
        # Deliver message
        test_message = {"content": "test message"}
        results = await subscription_manager.deliver_message(test_message, target)
        
        assert len(results) == 1
        assert results[0].success is True
        handler.assert_called_once_with(test_message, subscription)
    
    async def test_deliver_message_offline_queuing(self, subscription_manager):
        """Test message queuing for offline LLM"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Create subscription
        subscription = await subscription_manager.create_subscription(llm_id, target)
        
        # Simulate offline state but keep subscription active for this test
        await subscription_manager._ensure_connection_state(llm_id)
        connection_state = subscription_manager._connection_states[llm_id]
        connection_state.connected = False
        
        # Deliver message directly to subscription (simulating pub/sub delivery)
        test_message = {"content": "test message"}
        result = await subscription_manager._deliver_to_subscription(test_message, subscription)
        
        assert result.success is True
        
        # Verify message was queued
        assert len(connection_state.message_queue) == 1
        assert connection_state.message_queue[0]['message'] == test_message
    
    async def test_deliver_message_with_filter(self, subscription_manager):
        """Test message delivery with message filter"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Create subscription with message filter
        message_filter = MessageFilter(content_types=["text/plain"])
        options = SubscriptionOptions(message_filter=message_filter)
        subscription = await subscription_manager.create_subscription(llm_id, target, options=options)
        
        # Register delivery handler
        handler = AsyncMock()
        await subscription_manager.register_delivery_handler(llm_id, handler)
        
        # Deliver message that matches filter
        matching_message = {"content": "test", "content_type": "text/plain"}
        results = await subscription_manager.deliver_message(matching_message, target)
        
        assert len(results) == 1
        assert results[0].success is True
        handler.assert_called_once()
        
        # Reset handler
        handler.reset_mock()
        
        # Deliver message that doesn't match filter
        non_matching_message = {"content": "test", "content_type": "application/json"}
        results = await subscription_manager.deliver_message(non_matching_message, target)
        
        # Should still return result but handler shouldn't be called
        assert len(results) == 0  # No matching subscriptions
        handler.assert_not_called()
    
    async def test_pattern_matching_subscriptions(self, subscription_manager):
        """Test finding subscriptions with pattern matching"""
        llm_id = "llm-123"
        
        # Create pattern subscription
        subscription = await subscription_manager.create_subscription(
            llm_id, "test-*", pattern="test-*"
        )
        
        # Test pattern matching
        matching_subs = await subscription_manager._find_matching_subscriptions("test-mailbox")
        assert len(matching_subs) == 1
        assert matching_subs[0].id == subscription.id
        
        # Test non-matching target
        non_matching_subs = await subscription_manager._find_matching_subscriptions("other-mailbox")
        assert len(non_matching_subs) == 0
    
    async def test_message_queue_size_limit(self, subscription_manager):
        """Test message queue size limiting"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Set small queue size for testing
        subscription_manager.max_queue_size = 2
        
        # Create subscription and go offline
        subscription = await subscription_manager.create_subscription(llm_id, target)
        await subscription_manager.handle_connection_loss(llm_id)
        
        # Queue messages beyond limit
        for i in range(5):
            test_message = {"content": f"message {i}"}
            await subscription_manager._queue_message(llm_id, test_message, subscription)
        
        # Verify queue size is limited
        connection_state = subscription_manager._connection_states[llm_id]
        assert len(connection_state.message_queue) == 2
        
        # Verify newest messages are kept
        assert connection_state.message_queue[0]['message']['content'] == "message 3"
        assert connection_state.message_queue[1]['message']['content'] == "message 4"
    
    async def test_subscription_validation(self, subscription_manager):
        """Test subscription validation"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Test with invalid options
        invalid_options = SubscriptionOptions(max_queue_size=0)  # Invalid
        
        with pytest.raises(ValueError):
            await subscription_manager.create_subscription(
                llm_id, target, options=invalid_options
            )
    
    async def test_statistics(self, subscription_manager):
        """Test getting subscription manager statistics"""
        llm_id1 = "llm-123"
        llm_id2 = "llm-456"
        
        # Create subscriptions
        await subscription_manager.create_subscription(llm_id1, "mailbox1")
        await subscription_manager.create_subscription(llm_id2, "mailbox2")
        
        # Register handlers to create connection states
        await subscription_manager.register_delivery_handler(llm_id1, AsyncMock())
        await subscription_manager.register_delivery_handler(llm_id2, AsyncMock())
        
        # Queue some messages
        await subscription_manager.handle_connection_loss(llm_id1)
        subscription = subscription_manager._subscriptions[list(subscription_manager._subscriptions.keys())[0]]
        await subscription_manager._queue_message(llm_id1, {"test": "message"}, subscription)
        
        stats = await subscription_manager.get_statistics()
        
        assert stats["total_subscriptions"] == 2
        assert stats["active_subscriptions"] == 1  # One is offline
        assert stats["total_llms"] == 2
        assert stats["connected_llms"] == 1  # One is offline
        assert stats["total_queued_messages"] == 1
        assert stats["running"] is True
    
    async def test_cleanup_inactive_subscriptions(self, subscription_manager):
        """Test cleanup of inactive subscriptions"""
        llm_id = "llm-123"
        
        # Create subscription
        subscription = await subscription_manager.create_subscription(llm_id, "test-mailbox")
        
        # Make it inactive and old
        subscription.active = False
        subscription.last_activity = datetime.utcnow() - timedelta(hours=25)
        
        # Run cleanup
        await subscription_manager._cleanup_inactive_subscriptions()
        
        # Verify subscription was removed
        assert subscription.id not in subscription_manager._subscriptions
    
    async def test_connection_heartbeat_timeout(self, subscription_manager):
        """Test connection heartbeat timeout detection"""
        llm_id = "llm-123"
        
        # Create connection state
        await subscription_manager._ensure_connection_state(llm_id)
        connection_state = subscription_manager._connection_states[llm_id]
        
        # Make connection appear stale
        connection_state.last_seen = datetime.utcnow() - timedelta(seconds=120)
        
        # Run heartbeat check
        await subscription_manager._check_connection_heartbeats()
        
        # Verify connection was marked as lost
        assert connection_state.connected is False
    
    async def test_message_handler_creation(self, subscription_manager):
        """Test message handler creation and execution"""
        llm_id = "llm-123"
        target = "test-mailbox"
        
        # Create subscription
        subscription = await subscription_manager.create_subscription(llm_id, target)
        
        # Create message handler
        handler = subscription_manager._create_message_handler(subscription.id)
        
        # Register delivery handler
        delivery_handler = AsyncMock()
        await subscription_manager.register_delivery_handler(llm_id, delivery_handler)
        
        # Create test pub/sub message
        pubsub_message = PubSubMessage(
            type="message",
            channel=f"mailbox:{target}",
            pattern=None,
            data={"content": "test message"},
            timestamp=asyncio.get_event_loop().time()
        )
        
        # Execute handler
        await handler(pubsub_message)
        
        # Verify message was delivered and subscription updated
        delivery_handler.assert_called_once()
        assert subscription.message_count == 1
    
    async def test_start_stop_lifecycle(self, redis_manager, pubsub_manager):
        """Test subscription manager start/stop lifecycle"""
        # Set pubsub manager as not running initially
        pubsub_manager.is_running = False
        
        manager = SubscriptionManager(redis_manager, pubsub_manager)
        
        # Mock the load/save methods
        manager._load_subscriptions = AsyncMock()
        manager._save_subscriptions = AsyncMock()
        
        # Test start
        await manager.start()
        assert manager._running is True
        assert manager._cleanup_task is not None
        assert manager._heartbeat_task is not None
        
        # Verify pub/sub manager was started
        pubsub_manager.start.assert_called_once()
        
        # Test stop
        await manager.stop()
        assert manager._running is False
        
        # Verify cleanup
        manager._save_subscriptions.assert_called_once()


class TestConnectionState:
    """Test cases for ConnectionState"""
    
    def test_connection_state_creation(self):
        """Test connection state creation"""
        llm_id = "llm-123"
        state = ConnectionState(llm_id=llm_id)
        
        assert state.llm_id == llm_id
        assert state.connected is True
        assert state.reconnect_count == 0
        assert isinstance(state.last_seen, datetime)
        assert isinstance(state.message_queue, list)
        assert len(state.message_queue) == 0


class TestDeliveryResult:
    """Test cases for DeliveryResult"""
    
    def test_delivery_result_success(self):
        """Test successful delivery result"""
        result = DeliveryResult("sub-123", True)
        
        assert result.subscription_id == "sub-123"
        assert result.success is True
        assert result.error is None
        assert result.retry_count == 0
    
    def test_delivery_result_failure(self):
        """Test failed delivery result"""
        result = DeliveryResult("sub-123", False, "Connection failed", 2)
        
        assert result.subscription_id == "sub-123"
        assert result.success is False
        assert result.error == "Connection failed"
        assert result.retry_count == 2


if __name__ == "__main__":
    pytest.main([__file__])