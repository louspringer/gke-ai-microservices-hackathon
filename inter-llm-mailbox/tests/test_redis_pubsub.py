"""
Unit tests for Redis Pub/Sub Manager

Tests Redis pub/sub operations, subscription management, and message handling.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.redis_manager import RedisConnectionManager, RedisConfig
from src.core.redis_pubsub import RedisPubSubManager, PubSubMessage, SubscriptionType


@pytest.fixture
def redis_config():
    """Test Redis configuration"""
    return RedisConfig(host="localhost", port=6379)


@pytest.fixture
async def mock_redis_manager():
    """Mock Redis connection manager"""
    manager = AsyncMock(spec=RedisConnectionManager)
    manager.is_connected = True
    
    # Mock connection context manager
    mock_redis = AsyncMock()
    mock_redis.pubsub = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)
    
    async def mock_get_connection():
        yield mock_redis
    
    manager.get_connection = mock_get_connection
    return manager, mock_redis


@pytest.fixture
async def pubsub_manager(mock_redis_manager):
    """Pub/sub manager fixture"""
    redis_manager, _ = mock_redis_manager
    manager = RedisPubSubManager(redis_manager)
    yield manager
    await manager.stop()


class TestRedisPubSubManager:
    """Test Redis pub/sub manager functionality"""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, pubsub_manager, mock_redis_manager):
        """Test starting and stopping pub/sub manager"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        # Start manager
        await pubsub_manager.start()
        
        assert pubsub_manager.is_running
        assert pubsub_manager._pubsub is mock_pubsub
        assert pubsub_manager._listen_task is not None
        
        # Stop manager
        await pubsub_manager.stop()
        
        assert not pubsub_manager.is_running
        assert pubsub_manager._pubsub is None
        assert pubsub_manager._listen_task is None
        mock_pubsub.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_message(self, pubsub_manager, mock_redis_manager):
        """Test publishing messages to Redis channels"""
        redis_manager, mock_redis = mock_redis_manager
        mock_redis.publish = AsyncMock(return_value=2)
        
        await pubsub_manager.start()
        
        # Publish message
        message = {"type": "test", "data": "hello"}
        result = await pubsub_manager.publish("test_channel", message)
        
        # Verify publish call
        assert result == 2
        mock_redis.publish.assert_called_once_with(
            "test_channel", 
            json.dumps(message)
        )
    
    @pytest.mark.asyncio
    async def test_subscribe_channel(self, pubsub_manager, mock_redis_manager):
        """Test subscribing to Redis channels"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Subscribe to channel
        handler = AsyncMock()
        await pubsub_manager.subscribe_channel("test_channel", handler)
        
        # Verify subscription
        mock_pubsub.subscribe.assert_called_once_with("test_channel")
        assert "test_channel" in pubsub_manager._subscriptions
        assert pubsub_manager._subscriptions["test_channel"] == SubscriptionType.CHANNEL
        assert pubsub_manager._message_handlers["test_channel"] is handler
    
    @pytest.mark.asyncio
    async def test_subscribe_pattern(self, pubsub_manager, mock_redis_manager):
        """Test subscribing to Redis patterns"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Subscribe to pattern
        handler = AsyncMock()
        await pubsub_manager.subscribe_pattern("test_*", handler)
        
        # Verify subscription
        mock_pubsub.psubscribe.assert_called_once_with("test_*")
        assert "test_*" in pubsub_manager._subscriptions
        assert pubsub_manager._subscriptions["test_*"] == SubscriptionType.PATTERN
        assert pubsub_manager._message_handlers["test_*"] is handler
    
    @pytest.mark.asyncio
    async def test_unsubscribe_channel(self, pubsub_manager, mock_redis_manager):
        """Test unsubscribing from Redis channels"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Subscribe first
        await pubsub_manager.subscribe_channel("test_channel")
        
        # Unsubscribe
        await pubsub_manager.unsubscribe_channel("test_channel")
        
        # Verify unsubscription
        mock_pubsub.unsubscribe.assert_called_once_with("test_channel")
        assert "test_channel" not in pubsub_manager._subscriptions
        assert "test_channel" not in pubsub_manager._message_handlers
    
    @pytest.mark.asyncio
    async def test_unsubscribe_pattern(self, pubsub_manager, mock_redis_manager):
        """Test unsubscribing from Redis patterns"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Subscribe first
        await pubsub_manager.subscribe_pattern("test_*")
        
        # Unsubscribe
        await pubsub_manager.unsubscribe_pattern("test_*")
        
        # Verify unsubscription
        mock_pubsub.punsubscribe.assert_called_once_with("test_*")
        assert "test_*" not in pubsub_manager._subscriptions
        assert "test_*" not in pubsub_manager._message_handlers
    
    @pytest.mark.asyncio
    async def test_message_processing(self, pubsub_manager, mock_redis_manager):
        """Test processing received pub/sub messages"""
        redis_manager, mock_redis = mock_redis_manager
        
        await pubsub_manager.start()
        
        # Set up handler
        handler = AsyncMock()
        pubsub_manager._message_handlers["test_channel"] = handler
        
        # Create test message
        raw_message = {
            "type": "message",
            "channel": "test_channel",
            "data": json.dumps({"content": "test message"})
        }
        
        # Process message
        await pubsub_manager._process_message(raw_message)
        
        # Verify handler was called
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert isinstance(call_args, PubSubMessage)
        assert call_args.channel == "test_channel"
        assert call_args.data == {"content": "test message"}
    
    @pytest.mark.asyncio
    async def test_message_processing_with_pattern(self, pubsub_manager, mock_redis_manager):
        """Test processing messages from pattern subscriptions"""
        redis_manager, mock_redis = mock_redis_manager
        
        await pubsub_manager.start()
        
        # Set up pattern handler
        handler = AsyncMock()
        pubsub_manager._message_handlers["test_*"] = handler
        
        # Create test message with pattern
        raw_message = {
            "type": "pmessage",
            "channel": "test_channel",
            "pattern": "test_*",
            "data": json.dumps({"content": "pattern message"})
        }
        
        # Process message
        await pubsub_manager._process_message(raw_message)
        
        # Verify handler was called
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert isinstance(call_args, PubSubMessage)
        assert call_args.channel == "test_channel"
        assert call_args.pattern == "test_*"
        assert call_args.data == {"content": "pattern message"}
    
    @pytest.mark.asyncio
    async def test_message_processing_no_handler(self, pubsub_manager, mock_redis_manager):
        """Test processing messages without handlers"""
        redis_manager, mock_redis = mock_redis_manager
        
        await pubsub_manager.start()
        
        # Create test message without handler
        raw_message = {
            "type": "message",
            "channel": "unknown_channel",
            "data": "test message"
        }
        
        # Should not raise exception
        await pubsub_manager._process_message(raw_message)
    
    @pytest.mark.asyncio
    async def test_message_processing_invalid_json(self, pubsub_manager, mock_redis_manager):
        """Test processing messages with invalid JSON"""
        redis_manager, mock_redis = mock_redis_manager
        
        await pubsub_manager.start()
        
        # Set up handler
        handler = AsyncMock()
        pubsub_manager._message_handlers["test_channel"] = handler
        
        # Create message with invalid JSON
        raw_message = {
            "type": "message",
            "channel": "test_channel",
            "data": "invalid json {"
        }
        
        # Process message
        await pubsub_manager._process_message(raw_message)
        
        # Handler should still be called with raw data
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args.data == "invalid json {"
    
    @pytest.mark.asyncio
    async def test_handler_exception_handling(self, pubsub_manager, mock_redis_manager):
        """Test handling exceptions in message handlers"""
        redis_manager, mock_redis = mock_redis_manager
        
        await pubsub_manager.start()
        
        # Set up handler that raises exception
        handler = AsyncMock(side_effect=Exception("Handler error"))
        pubsub_manager._message_handlers["test_channel"] = handler
        
        # Create test message
        raw_message = {
            "type": "message",
            "channel": "test_channel",
            "data": "test message"
        }
        
        # Should not raise exception
        await pubsub_manager._process_message(raw_message)
        
        # Handler should have been called
        handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_loss_handling(self, pubsub_manager, mock_redis_manager):
        """Test handling Redis connection loss during pub/sub"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Subscribe to channels
        await pubsub_manager.subscribe_channel("test_channel")
        await pubsub_manager.subscribe_pattern("test_*")
        
        # Simulate connection recovery
        redis_manager.is_connected = True
        
        # Handle connection loss
        await pubsub_manager._handle_connection_loss()
        
        # Verify subscriptions were restored
        assert mock_pubsub.subscribe.call_count >= 1
        assert mock_pubsub.psubscribe.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_subscription_info(self, pubsub_manager, mock_redis_manager):
        """Test getting subscription information"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Add subscriptions
        await pubsub_manager.subscribe_channel("test_channel")
        await pubsub_manager.subscribe_pattern("test_*")
        
        # Get subscription info
        info = await pubsub_manager.get_subscription_info()
        
        # Verify info
        assert info["running"] is True
        assert "test_channel" in info["subscriptions"]
        assert "test_*" in info["subscriptions"]
        assert info["subscriptions"]["test_channel"] == "channel"
        assert info["subscriptions"]["test_*"] == "pattern"
        assert info["handlers_count"] == 0  # No handlers set
        assert info["pubsub_connected"] is True
    
    @pytest.mark.asyncio
    async def test_duplicate_subscription_handling(self, pubsub_manager, mock_redis_manager):
        """Test handling duplicate subscription attempts"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Subscribe twice to same channel
        await pubsub_manager.subscribe_channel("test_channel")
        await pubsub_manager.subscribe_channel("test_channel")  # Should be ignored
        
        # Should only subscribe once
        mock_pubsub.subscribe.assert_called_once_with("test_channel")
    
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent(self, pubsub_manager, mock_redis_manager):
        """Test unsubscribing from non-existent subscriptions"""
        redis_manager, mock_redis = mock_redis_manager
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        await pubsub_manager.start()
        
        # Unsubscribe from non-existent channel (should not raise exception)
        await pubsub_manager.unsubscribe_channel("nonexistent_channel")
        
        # Should not call Redis unsubscribe
        mock_pubsub.unsubscribe.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])