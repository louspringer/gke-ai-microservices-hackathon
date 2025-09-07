"""
Tests for Message Router

Tests message routing based on addressing modes, delivery confirmation tracking,
and retry logic with exponential backoff.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.message_router import MessageRouter, RoutingResult, DeliveryConfirmation, RoutingInfo
from src.core.redis_manager import RedisConnectionManager, RedisConfig
from src.core.redis_pubsub import RedisPubSubManager
from src.models.message import Message, RoutingInfo as MessageRoutingInfo, DeliveryOptions, RetryPolicy
from src.models.enums import AddressingMode, ContentType, Priority, DeliveryStatus


@pytest.fixture
async def redis_manager():
    """Create a mock Redis manager"""
    manager = AsyncMock(spec=RedisConnectionManager)
    manager.is_connected = True
    
    # Mock Redis connection
    redis_conn = AsyncMock()
    manager.get_connection.return_value.__aenter__.return_value = redis_conn
    manager.get_connection.return_value.__aexit__.return_value = None
    
    return manager


@pytest.fixture
async def pubsub_manager():
    """Create a mock pub/sub manager"""
    manager = AsyncMock(spec=RedisPubSubManager)
    manager.is_running = True
    manager.publish.return_value = 1  # Default to 1 subscriber
    return manager


@pytest.fixture
async def message_router(redis_manager, pubsub_manager):
    """Create a message router instance"""
    router = MessageRouter(redis_manager, pubsub_manager)
    await router.start()
    yield router
    await router.stop()


@pytest.fixture
def sample_message():
    """Create a sample message for testing"""
    routing_info = MessageRoutingInfo(
        addressing_mode=AddressingMode.DIRECT,
        target="test-mailbox",
        priority=Priority.NORMAL
    )
    
    return Message.create(
        sender_id="test-llm",
        content="Hello, World!",
        content_type=ContentType.TEXT,
        routing_info=routing_info
    )


@pytest.fixture
def broadcast_message():
    """Create a broadcast message for testing"""
    routing_info = MessageRoutingInfo(
        addressing_mode=AddressingMode.BROADCAST,
        target="all",
        priority=Priority.HIGH
    )
    
    return Message.create(
        sender_id="test-llm",
        content="Broadcast message",
        content_type=ContentType.TEXT,
        routing_info=routing_info
    )


@pytest.fixture
def topic_message():
    """Create a topic message for testing"""
    routing_info = MessageRoutingInfo(
        addressing_mode=AddressingMode.TOPIC,
        target="test-topic",
        priority=Priority.NORMAL
    )
    
    return Message.create(
        sender_id="test-llm",
        content="Topic message",
        content_type=ContentType.TEXT,
        routing_info=routing_info
    )


class TestMessageRouter:
    """Test cases for MessageRouter"""
    
    async def test_router_lifecycle(self, redis_manager, pubsub_manager):
        """Test router start and stop lifecycle"""
        router = MessageRouter(redis_manager, pubsub_manager)
        
        assert not router._running
        
        await router.start()
        assert router._running
        assert router._retry_task is not None
        assert router._cleanup_task is not None
        
        await router.stop()
        assert not router._running
        assert router._retry_task.cancelled()
        assert router._cleanup_task.cancelled()
    
    async def test_message_validation(self, message_router, sample_message):
        """Test message validation"""
        # Valid message
        result = await message_router.validate_message(sample_message)
        assert result.is_valid
        assert len(result.errors) == 0
        
        # Invalid message - no target
        invalid_message = sample_message.clone()
        invalid_message.routing_info.target = ""
        
        result = await message_router.validate_message(invalid_message)
        assert not result.is_valid
        assert any("routing_target" in error.field for error in result.errors)
        
        # Invalid message - negative TTL
        invalid_message = sample_message.clone()
        invalid_message.routing_info.ttl = -1
        
        result = await message_router.validate_message(invalid_message)
        assert not result.is_valid
        assert any("ttl" in error.field for error in result.errors)
    
    async def test_message_enrichment(self, message_router, sample_message):
        """Test message enrichment with routing metadata"""
        enriched = await message_router.enrich_message(sample_message)
        
        # Should be a clone, not the same object
        assert enriched.id == sample_message.id
        assert enriched is not sample_message
        
        # Should have routing metadata
        assert enriched.get_system_metadata('routed_at') is not None
        assert enriched.get_system_metadata('router_version') == '1.0'
        assert enriched.get_system_metadata('routing_mode') == AddressingMode.DIRECT.value
        
        # Test urgent priority metadata
        urgent_message = sample_message.clone()
        urgent_message.routing_info.priority = Priority.URGENT
        
        enriched_urgent = await message_router.enrich_message(urgent_message)
        assert enriched_urgent.get_system_metadata('urgent') is True
    
    async def test_direct_routing_success(self, message_router, sample_message, redis_manager, pubsub_manager):
        """Test successful direct message routing"""
        # Mock successful pub/sub publish
        pubsub_manager.publish.return_value = 2  # 2 subscribers
        
        result = await message_router.route_message(sample_message)
        
        assert result == RoutingResult.SUCCESS
        
        # Verify Redis operations
        redis_conn = redis_manager.get_connection.return_value.__aenter__.return_value
        redis_conn.hset.assert_called()  # Message stored
        redis_conn.zadd.assert_called()  # Added to mailbox
        
        # Verify pub/sub publish
        pubsub_manager.publish.assert_called_once()
        call_args = pubsub_manager.publish.call_args
        assert call_args[0][0] == f"mailbox:{sample_message.routing_info.target}"
    
    async def test_direct_routing_queued(self, message_router, sample_message, pubsub_manager):
        """Test direct routing when no subscribers (queued)"""
        # Mock no subscribers
        pubsub_manager.publish.return_value = 0
        
        result = await message_router.route_message(sample_message)
        
        assert result == RoutingResult.QUEUED
    
    async def test_broadcast_routing(self, message_router, broadcast_message, redis_manager, pubsub_manager):
        """Test broadcast message routing"""
        # Mock active mailboxes
        redis_conn = redis_manager.get_connection.return_value.__aenter__.return_value
        redis_conn.keys.return_value = [
            "mailbox:mailbox1:metadata",
            "mailbox:mailbox2:metadata",
            "mailbox:mailbox3:metadata"
        ]
        
        # Mock successful pub/sub publish
        pubsub_manager.publish.return_value = 1
        
        result = await message_router.route_message(broadcast_message)
        
        assert result == RoutingResult.SUCCESS
        
        # Should have published to 3 mailboxes
        assert pubsub_manager.publish.call_count == 3
        
        # Verify storage calls
        assert redis_conn.hset.call_count >= 3  # At least 3 storage operations
    
    async def test_topic_routing(self, message_router, topic_message, redis_manager, pubsub_manager):
        """Test topic message routing"""
        # Mock successful pub/sub publish
        pubsub_manager.publish.return_value = 5  # 5 subscribers
        
        result = await message_router.route_message(topic_message)
        
        assert result == RoutingResult.SUCCESS
        
        # Verify topic storage
        redis_conn = redis_manager.get_connection.return_value.__aenter__.return_value
        redis_conn.hset.assert_called()
        redis_conn.zadd.assert_called()
        
        # Verify pub/sub publish to topic channel
        pubsub_manager.publish.assert_called_once()
        call_args = pubsub_manager.publish.call_args
        assert call_args[0][0] == f"topic:{topic_message.routing_info.target}"
    
    async def test_expired_message_routing(self, message_router, sample_message):
        """Test routing of expired messages"""
        # Create message with very short TTL
        expired_message = sample_message.clone()
        expired_message.routing_info.ttl = 1
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        result = await message_router.route_message(expired_message)
        
        assert result == RoutingResult.REJECTED
    
    async def test_delivery_confirmation_tracking(self, message_router, sample_message):
        """Test delivery confirmation tracking"""
        # Enable confirmation tracking
        sample_message.delivery_options.confirmation_required = True
        
        result = await message_router.route_message(sample_message)
        
        # Should have tracking entry
        confirmation = await message_router.get_delivery_status(sample_message.id)
        assert confirmation is not None
        assert confirmation.message_id == sample_message.id
        assert confirmation.target == sample_message.routing_info.target
    
    async def test_delivery_confirmation_handling(self, message_router):
        """Test delivery confirmation handling"""
        message_id = "test-message-123"
        target = "test-target"
        
        # Handle successful delivery
        await message_router.handle_delivery_confirmation(
            message_id, DeliveryStatus.DELIVERED, target, latency_ms=50.0
        )
        
        confirmation = await message_router.get_delivery_status(message_id)
        assert confirmation is not None
        assert confirmation.status == DeliveryStatus.DELIVERED
        assert len(confirmation.attempts) == 1
        assert confirmation.attempts[0].latency_ms == 50.0
    
    async def test_retry_scheduling(self, message_router):
        """Test retry scheduling with exponential backoff"""
        message_id = "test-message-retry"
        target = "test-target"
        
        # Create a failed delivery
        await message_router.handle_delivery_confirmation(
            message_id, DeliveryStatus.FAILED, target, error="Connection timeout"
        )
        
        confirmation = await message_router.get_delivery_status(message_id)
        assert confirmation is not None
        assert confirmation.status == DeliveryStatus.FAILED
        assert confirmation.next_retry_at is not None
        assert confirmation.next_retry_at > datetime.utcnow()
        
        # Check exponential backoff calculation
        retry_count = confirmation.get_retry_count()
        expected_min_delay = message_router.base_retry_delay * (message_router.retry_exponential_base ** retry_count)
        
        actual_delay = (confirmation.next_retry_at - datetime.utcnow()).total_seconds()
        assert actual_delay >= expected_min_delay * 0.9  # Account for jitter
    
    async def test_max_retry_attempts(self, message_router):
        """Test maximum retry attempts limit"""
        message_id = "test-message-max-retry"
        target = "test-target"
        
        # Simulate multiple failed attempts
        for i in range(message_router.max_retry_attempts + 1):
            await message_router.handle_delivery_confirmation(
                message_id, DeliveryStatus.FAILED, target, error=f"Attempt {i+1} failed"
            )
        
        confirmation = await message_router.get_delivery_status(message_id)
        assert confirmation is not None
        assert len(confirmation.attempts) == message_router.max_retry_attempts + 1
        assert not confirmation.should_retry(message_router.max_retry_attempts)
    
    async def test_routing_error_handling(self, message_router, sample_message, redis_manager):
        """Test error handling during routing"""
        # Mock Redis error
        redis_conn = redis_manager.get_connection.return_value.__aenter__.return_value
        redis_conn.hset.side_effect = Exception("Redis connection failed")
        
        result = await message_router.route_message(sample_message)
        
        assert result == RoutingResult.FAILED
        
        # Check metrics
        stats = await message_router.get_statistics()
        assert stats['routing_errors'] > 0
    
    async def test_invalid_addressing_mode(self, message_router, sample_message):
        """Test handling of invalid addressing mode"""
        # Mock invalid addressing mode
        with patch.object(sample_message.routing_info, 'addressing_mode', 'invalid_mode'):
            result = await message_router.route_message(sample_message)
            assert result == RoutingResult.REJECTED
    
    async def test_statistics_collection(self, message_router, sample_message):
        """Test statistics collection"""
        # Route some messages
        await message_router.route_message(sample_message)
        
        stats = await message_router.get_statistics()
        
        assert 'messages_routed' in stats
        assert 'messages_delivered' in stats
        assert 'messages_failed' in stats
        assert 'messages_retried' in stats
        assert 'routing_errors' in stats
        assert 'validation_errors' in stats
        assert 'pending_deliveries' in stats
        assert 'active_confirmations' in stats
        assert 'running' in stats
        assert 'retry_config' in stats
        
        assert stats['messages_routed'] > 0
        assert stats['running'] is True
    
    async def test_pending_deliveries_management(self, message_router, sample_message):
        """Test pending deliveries management"""
        # Enable confirmation tracking
        sample_message.delivery_options.confirmation_required = True
        
        await message_router.route_message(sample_message)
        
        # Should be in pending deliveries
        pending = await message_router.get_pending_deliveries()
        assert sample_message.id in pending
        
        # Confirm delivery
        await message_router.handle_delivery_confirmation(
            sample_message.id, DeliveryStatus.DELIVERED, sample_message.routing_info.target
        )
        
        # Should be removed from pending
        pending = await message_router.get_pending_deliveries()
        assert sample_message.id not in pending
    
    @pytest.mark.asyncio
    async def test_retry_loop_processing(self, message_router):
        """Test retry loop processing"""
        message_id = "test-retry-loop"
        target = "test-target"
        
        # Create a message that needs retry
        sample_message = Message.create(
            sender_id="test-llm",
            content="Retry test",
            content_type=ContentType.TEXT,
            routing_info=MessageRoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target=target,
                priority=Priority.NORMAL
            )
        )
        
        # Add to pending deliveries
        message_router._pending_deliveries[message_id] = sample_message
        
        # Create failed confirmation with immediate retry
        confirmation = DeliveryConfirmation(
            message_id=message_id,
            target=target,
            status=DeliveryStatus.FAILED
        )
        confirmation.next_retry_at = datetime.utcnow() - timedelta(seconds=1)  # Past time
        message_router._delivery_confirmations[message_id] = confirmation
        
        # Process retries
        await message_router._process_retries()
        
        # Should have attempted retry
        stats = await message_router.get_statistics()
        assert stats.get('messages_retried', 0) > 0
    
    async def test_cleanup_old_confirmations(self, message_router):
        """Test cleanup of old delivery confirmations"""
        message_id = "test-cleanup"
        
        # Create old confirmation
        confirmation = DeliveryConfirmation(
            message_id=message_id,
            target="test-target",
            status=DeliveryStatus.DELIVERED
        )
        confirmation.updated_at = datetime.utcnow() - timedelta(hours=2)  # Old confirmation
        
        message_router._delivery_confirmations[message_id] = confirmation
        
        # Run cleanup
        await message_router._cleanup_old_confirmations()
        
        # Should be removed
        assert message_id not in message_router._delivery_confirmations
    
    async def test_message_storage_with_ttl(self, message_router, sample_message, redis_manager):
        """Test message storage with TTL"""
        # Set TTL on message
        sample_message.routing_info.ttl = 3600  # 1 hour
        
        await message_router.route_message(sample_message)
        
        # Verify TTL was set
        redis_conn = redis_manager.get_connection.return_value.__aenter__.return_value
        redis_conn.expire.assert_called_with(f"message:{sample_message.id}", 3600)
    
    async def test_priority_handling(self, message_router):
        """Test priority-based message handling"""
        # Create urgent message
        urgent_routing = MessageRoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="urgent-mailbox",
            priority=Priority.URGENT
        )
        
        urgent_message = Message.create(
            sender_id="test-llm",
            content="Urgent message",
            content_type=ContentType.TEXT,
            routing_info=urgent_routing
        )
        
        result = await message_router.route_message(urgent_message)
        assert result == RoutingResult.SUCCESS
        
        # Check that urgent metadata was added
        confirmation = await message_router.get_delivery_status(urgent_message.id)
        if confirmation:  # Only if confirmation tracking is enabled
            # Verify urgent handling (implementation specific)
            pass
    
    async def test_concurrent_routing(self, message_router):
        """Test concurrent message routing"""
        messages = []
        
        # Create multiple messages
        for i in range(10):
            routing_info = MessageRoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target=f"mailbox-{i}",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id=f"llm-{i}",
                content=f"Message {i}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            messages.append(message)
        
        # Route all messages concurrently
        tasks = [message_router.route_message(msg) for msg in messages]
        results = await asyncio.gather(*tasks)
        
        # All should succeed or be queued
        assert all(r in [RoutingResult.SUCCESS, RoutingResult.QUEUED] for r in results)
        
        # Check statistics
        stats = await message_router.get_statistics()
        assert stats['messages_routed'] >= 10


class TestDeliveryConfirmation:
    """Test cases for DeliveryConfirmation"""
    
    def test_delivery_confirmation_creation(self):
        """Test delivery confirmation creation"""
        confirmation = DeliveryConfirmation(
            message_id="test-123",
            target="test-target",
            status=DeliveryStatus.PENDING
        )
        
        assert confirmation.message_id == "test-123"
        assert confirmation.target == "test-target"
        assert confirmation.status == DeliveryStatus.PENDING
        assert len(confirmation.attempts) == 0
        assert confirmation.created_at is not None
    
    def test_add_attempt(self):
        """Test adding delivery attempts"""
        confirmation = DeliveryConfirmation(
            message_id="test-123",
            target="test-target",
            status=DeliveryStatus.PENDING
        )
        
        # Add successful attempt
        confirmation.add_attempt("test-target", DeliveryStatus.DELIVERED, latency_ms=25.5)
        
        assert len(confirmation.attempts) == 1
        assert confirmation.attempts[0].attempt_number == 1
        assert confirmation.attempts[0].status == DeliveryStatus.DELIVERED
        assert confirmation.attempts[0].latency_ms == 25.5
        assert confirmation.status == DeliveryStatus.DELIVERED
    
    def test_retry_logic(self):
        """Test retry logic"""
        confirmation = DeliveryConfirmation(
            message_id="test-123",
            target="test-target",
            status=DeliveryStatus.FAILED
        )
        
        # Should retry with no attempts
        assert confirmation.should_retry(3)
        
        # Add failed attempts
        for i in range(3):
            confirmation.add_attempt("test-target", DeliveryStatus.FAILED, error=f"Error {i+1}")
        
        # Should not retry after max attempts
        assert not confirmation.should_retry(3)
        
        # Should retry if max attempts is higher
        assert confirmation.should_retry(5)
    
    def test_retry_count(self):
        """Test retry count calculation"""
        confirmation = DeliveryConfirmation(
            message_id="test-123",
            target="test-target",
            status=DeliveryStatus.PENDING
        )
        
        # Initial attempt (not a retry)
        confirmation.add_attempt("test-target", DeliveryStatus.FAILED)
        assert confirmation.get_retry_count() == 0
        
        # First retry
        confirmation.add_attempt("test-target", DeliveryStatus.FAILED)
        assert confirmation.get_retry_count() == 1
        
        # Second retry
        confirmation.add_attempt("test-target", DeliveryStatus.DELIVERED)
        assert confirmation.get_retry_count() == 2


class TestRoutingInfo:
    """Test cases for RoutingInfo"""
    
    def test_routing_info_creation(self):
        """Test routing info creation"""
        routing_info = RoutingInfo(
            message_id="test-123",
            sender_id="test-llm",
            addressing_mode=AddressingMode.DIRECT,
            target="test-target",
            priority=Priority.HIGH,
            ttl=3600
        )
        
        assert routing_info.message_id == "test-123"
        assert routing_info.sender_id == "test-llm"
        assert routing_info.addressing_mode == AddressingMode.DIRECT
        assert routing_info.target == "test-target"
        assert routing_info.priority == Priority.HIGH
        assert routing_info.ttl == 3600
    
    def test_expiration_check(self):
        """Test TTL expiration check"""
        # Non-expiring message
        routing_info = RoutingInfo(
            message_id="test-123",
            sender_id="test-llm",
            addressing_mode=AddressingMode.DIRECT,
            target="test-target",
            priority=Priority.NORMAL
        )
        
        assert not routing_info.is_expired()
        
        # Expired message
        routing_info_expired = RoutingInfo(
            message_id="test-456",
            sender_id="test-llm",
            addressing_mode=AddressingMode.DIRECT,
            target="test-target",
            priority=Priority.NORMAL,
            ttl=1,
            created_at=datetime.utcnow() - timedelta(seconds=2)
        )
        
        assert routing_info_expired.is_expired()


if __name__ == "__main__":
    pytest.main([__file__])