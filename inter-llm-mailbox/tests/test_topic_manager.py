"""
Tests for Topic Manager functionality
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.topic_manager import TopicManager, TopicConfig, Topic
from src.core.redis_manager import RedisConnectionManager
from src.core.subscription_manager import SubscriptionManager
from src.models.subscription import SubscriptionOptions, LLMID
from src.models.enums import DeliveryMode, AddressingMode


@pytest.fixture
async def redis_manager():
    """Mock Redis connection manager"""
    manager = MagicMock(spec=RedisConnectionManager)
    
    # Mock Redis connection
    redis_conn = AsyncMock()
    redis_conn.keys.return_value = []
    redis_conn.hgetall.return_value = {}
    redis_conn.hset.return_value = True
    redis_conn.delete.return_value = True
    redis_conn.set.return_value = True
    
    # Mock connection context manager
    async def get_connection():
        return redis_conn
    
    manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=redis_conn)
    manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
    
    return manager


@pytest.fixture
async def subscription_manager():
    """Mock subscription manager"""
    manager = AsyncMock(spec=SubscriptionManager)
    manager.create_subscription.return_value = MagicMock(id="sub-123", llm_id="llm-1", target="test.topic")
    manager.remove_subscription.return_value = True
    manager.get_subscription.return_value = MagicMock(id="sub-123", target="test.topic")
    manager.deliver_message.return_value = []
    return manager


@pytest.fixture
async def topic_manager(redis_manager, subscription_manager):
    """Create topic manager instance"""
    manager = TopicManager(redis_manager, subscription_manager)
    await manager.start()
    yield manager
    await manager.stop()


class TestTopicConfig:
    """Test TopicConfig class"""
    
    def test_topic_config_creation(self):
        """Test creating a topic configuration"""
        config = TopicConfig(
            name="test.topic",
            description="Test topic",
            max_subscribers=500
        )
        
        assert config.name == "test.topic"
        assert config.description == "Test topic"
        assert config.max_subscribers == 500
        assert config.auto_cleanup is True
    
    def test_topic_config_serialization(self):
        """Test topic configuration serialization"""
        config = TopicConfig(
            name="test.topic",
            description="Test topic",
            metadata={"key": "value"}
        )
        
        data = config.to_dict()
        assert data["name"] == "test.topic"
        assert data["description"] == "Test topic"
        assert data["metadata"] == {"key": "value"}
        
        # Test deserialization
        restored_config = TopicConfig.from_dict(data)
        assert restored_config.name == config.name
        assert restored_config.description == config.description
        assert restored_config.metadata == config.metadata


class TestTopic:
    """Test Topic class"""
    
    def test_topic_creation(self):
        """Test creating a topic"""
        config = TopicConfig(name="ai.ml.training")
        topic = Topic(id="topic-123", config=config)
        
        assert topic.id == "topic-123"
        assert topic.name == "ai.ml.training"
        assert topic.is_hierarchical is True
        assert topic.hierarchy_parts == ["ai", "ml", "training"]
        assert topic.parent_topics == ["ai", "ai.ml"]
    
    def test_topic_pattern_matching(self):
        """Test topic pattern matching"""
        config = TopicConfig(name="ai.ml.training")
        topic = Topic(id="topic-123", config=config)
        
        assert topic.matches_pattern("ai.*") is True
        assert topic.matches_pattern("ai.ml.*") is True
        assert topic.matches_pattern("ai.ml.training") is True
        assert topic.matches_pattern("web.*") is False
    
    def test_topic_hierarchy_relationships(self):
        """Test topic hierarchy relationships"""
        config = TopicConfig(name="ai.ml.training")
        topic = Topic(id="topic-123", config=config)
        
        assert topic.is_child_of("ai") is True
        assert topic.is_child_of("ai.ml") is True
        assert topic.is_child_of("web") is False
    
    def test_topic_serialization(self):
        """Test topic serialization"""
        config = TopicConfig(name="test.topic")
        topic = Topic(id="topic-123", config=config)
        topic.message_count = 5
        topic.subscriber_count = 3
        
        data = topic.to_dict()
        assert data["id"] == "topic-123"
        assert data["config"]["name"] == "test.topic"
        assert data["message_count"] == 5
        assert data["subscriber_count"] == 3
        
        # Test deserialization
        restored_topic = Topic.from_dict(data)
        assert restored_topic.id == topic.id
        assert restored_topic.config.name == topic.config.name
        assert restored_topic.message_count == topic.message_count


class TestTopicManager:
    """Test TopicManager class"""
    
    @pytest.mark.asyncio
    async def test_topic_creation(self, topic_manager):
        """Test creating a topic"""
        config = TopicConfig(
            name="test.topic",
            description="Test topic for unit tests"
        )
        
        topic = await topic_manager.create_topic(config)
        
        assert topic.config.name == "test.topic"
        assert topic.config.description == "Test topic for unit tests"
        assert topic.active is True
        assert topic.id is not None
    
    @pytest.mark.asyncio
    async def test_duplicate_topic_creation(self, topic_manager):
        """Test creating duplicate topics"""
        config = TopicConfig(name="duplicate.topic")
        
        # Create first topic
        topic1 = await topic_manager.create_topic(config)
        
        # Try to create duplicate
        topic2 = await topic_manager.create_topic(config)
        
        # Should return the same topic
        assert topic1.id == topic2.id
        assert topic1.config.name == topic2.config.name
    
    @pytest.mark.asyncio
    async def test_invalid_topic_creation(self, topic_manager):
        """Test creating invalid topics"""
        # Empty name
        with pytest.raises(ValueError, match="Topic name is required"):
            await topic_manager.create_topic(TopicConfig(name=""))
        
        # Invalid characters
        with pytest.raises(ValueError, match="Topic name can only contain"):
            await topic_manager.create_topic(TopicConfig(name="invalid@topic"))
        
        # Too long name
        long_name = "a" * 300
        with pytest.raises(ValueError, match="Topic name exceeds maximum length"):
            await topic_manager.create_topic(TopicConfig(name=long_name))
    
    @pytest.mark.asyncio
    async def test_hierarchical_topic_creation(self, topic_manager):
        """Test creating hierarchical topics"""
        config = TopicConfig(name="ai.ml.deep_learning.cnn")
        
        topic = await topic_manager.create_topic(config)
        
        assert topic.is_hierarchical is True
        assert topic.hierarchy_parts == ["ai", "ml", "deep_learning", "cnn"]
        assert topic.parent_topics == ["ai", "ai.ml", "ai.ml.deep_learning"]
        
        # Check that parent topics were auto-created
        ai_topic = await topic_manager.get_topic("ai")
        assert ai_topic is not None
        assert ai_topic.config.description.startswith("Auto-created parent topic")
        
        ml_topic = await topic_manager.get_topic("ai.ml")
        assert ml_topic is not None
    
    @pytest.mark.asyncio
    async def test_topic_subscription(self, topic_manager):
        """Test subscribing to topics"""
        # Create topic
        config = TopicConfig(name="test.subscription")
        topic = await topic_manager.create_topic(config)
        
        # Subscribe to topic
        subscription = await topic_manager.subscribe_to_topic(
            llm_id="llm-1",
            topic_name="test.subscription"
        )
        
        assert subscription is not None
        assert subscription.target == "test.subscription"
        
        # Check topic subscriber count was updated
        updated_topic = await topic_manager.get_topic("test.subscription")
        assert updated_topic.subscriber_count == 1
    
    @pytest.mark.asyncio
    async def test_hierarchical_subscription(self, topic_manager):
        """Test subscribing to hierarchical topics with children"""
        # Create hierarchical topic
        config = TopicConfig(name="ai.ml")
        topic = await topic_manager.create_topic(config)
        
        # Subscribe with children included
        subscription = await topic_manager.subscribe_to_topic(
            llm_id="llm-1",
            topic_name="ai.ml",
            include_children=True
        )
        
        assert subscription.pattern == "ai.ml.*"
    
    @pytest.mark.asyncio
    async def test_topic_unsubscription(self, topic_manager, subscription_manager):
        """Test unsubscribing from topics"""
        # Create topic and subscription
        config = TopicConfig(name="test.unsubscribe")
        topic = await topic_manager.create_topic(config)
        
        subscription = await topic_manager.subscribe_to_topic(
            llm_id="llm-1",
            topic_name="test.unsubscribe"
        )
        
        # Unsubscribe
        success = await topic_manager.unsubscribe_from_topic(subscription.id)
        
        assert success is True
        subscription_manager.remove_subscription.assert_called_with(subscription.id)
    
    @pytest.mark.asyncio
    async def test_topic_publishing(self, topic_manager, subscription_manager):
        """Test publishing messages to topics"""
        # Create topic
        config = TopicConfig(name="test.publish")
        topic = await topic_manager.create_topic(config)
        
        # Publish message
        message = {
            "content": "Test message",
            "routing_info": {"addressing_mode": "direct", "target": "test.publish"}
        }
        
        subscriber_count = await topic_manager.publish_to_topic("test.publish", message)
        
        # Verify message was delivered through subscription manager
        subscription_manager.deliver_message.assert_called_once()
        
        # Check that routing info was updated
        delivered_message = subscription_manager.deliver_message.call_args[0][0]
        assert delivered_message["routing_info"]["addressing_mode"] == AddressingMode.TOPIC.value
        assert delivered_message["routing_info"]["target"] == "test.publish"
        
        # Check topic message count was updated
        updated_topic = await topic_manager.get_topic("test.publish")
        assert updated_topic.message_count == 1
    
    @pytest.mark.asyncio
    async def test_topic_deletion(self, topic_manager):
        """Test deleting topics"""
        # Create topic
        config = TopicConfig(name="test.delete")
        topic = await topic_manager.create_topic(config)
        
        # Delete topic
        success = await topic_manager.delete_topic("test.delete")
        
        assert success is True
        
        # Verify topic is gone
        deleted_topic = await topic_manager.get_topic("test.delete")
        assert deleted_topic is None
    
    @pytest.mark.asyncio
    async def test_topic_deletion_with_subscribers(self, topic_manager):
        """Test deleting topics with active subscribers"""
        # Create topic and subscription
        config = TopicConfig(name="test.delete.with.subs")
        topic = await topic_manager.create_topic(config)
        topic.subscriber_count = 1  # Simulate active subscriber
        
        # Try to delete without force
        with pytest.raises(ValueError, match="has .* active subscribers"):
            await topic_manager.delete_topic("test.delete.with.subs", force=False)
        
        # Delete with force
        success = await topic_manager.delete_topic("test.delete.with.subs", force=True)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_hierarchical_topic_deletion(self, topic_manager):
        """Test deleting hierarchical topics with children"""
        # Create parent and child topics
        parent_config = TopicConfig(name="parent")
        child_config = TopicConfig(name="parent.child")
        
        parent_topic = await topic_manager.create_topic(parent_config)
        child_topic = await topic_manager.create_topic(child_config)
        
        # Delete parent (should delete children too)
        success = await topic_manager.delete_topic("parent", force=True)
        
        assert success is True
        
        # Verify both topics are gone
        assert await topic_manager.get_topic("parent") is None
        assert await topic_manager.get_topic("parent.child") is None
    
    @pytest.mark.asyncio
    async def test_list_topics(self, topic_manager):
        """Test listing topics"""
        # Create multiple topics
        topics_to_create = [
            TopicConfig(name="ai.ml"),
            TopicConfig(name="ai.nlp"),
            TopicConfig(name="web.frontend"),
            TopicConfig(name="web.backend")
        ]
        
        for config in topics_to_create:
            await topic_manager.create_topic(config)
        
        # List all topics
        all_topics = await topic_manager.list_topics()
        topic_names = [t.config.name for t in all_topics]
        
        assert "ai.ml" in topic_names
        assert "ai.nlp" in topic_names
        assert "web.frontend" in topic_names
        assert "web.backend" in topic_names
        
        # List with pattern
        ai_topics = await topic_manager.list_topics(pattern="ai.*")
        ai_topic_names = [t.config.name for t in ai_topics]
        
        assert "ai.ml" in ai_topic_names
        assert "ai.nlp" in ai_topic_names
        assert "web.frontend" not in ai_topic_names
    
    @pytest.mark.asyncio
    async def test_topic_hierarchy_structure(self, topic_manager):
        """Test getting topic hierarchy structure"""
        # Create hierarchical topics
        topics_to_create = [
            TopicConfig(name="ai"),
            TopicConfig(name="ai.ml"),
            TopicConfig(name="ai.ml.supervised"),
            TopicConfig(name="ai.ml.unsupervised"),
            TopicConfig(name="ai.nlp"),
            TopicConfig(name="web")
        ]
        
        for config in topics_to_create:
            await topic_manager.create_topic(config)
        
        # Get full hierarchy
        hierarchy = await topic_manager.get_topic_hierarchy()
        
        assert "ai" in hierarchy
        assert "web" in hierarchy
        assert "children" in hierarchy["ai"]
        
        # Get specific subtree
        ai_hierarchy = await topic_manager.get_topic_hierarchy("ai")
        assert "topic" in ai_hierarchy
        assert ai_hierarchy["topic"]["config"]["name"] == "ai"
    
    @pytest.mark.asyncio
    async def test_topic_subscribers_list(self, topic_manager, subscription_manager):
        """Test getting topic subscribers"""
        # Create topic
        config = TopicConfig(name="test.subscribers")
        topic = await topic_manager.create_topic(config)
        
        # Mock subscription data
        mock_subscription = MagicMock()
        mock_subscription.id = "sub-123"
        mock_subscription.llm_id = "llm-1"
        mock_subscription.created_at = datetime.utcnow()
        mock_subscription.last_activity = datetime.utcnow()
        mock_subscription.message_count = 5
        mock_subscription.active = True
        mock_subscription.options.delivery_mode = DeliveryMode.REALTIME
        
        subscription_manager.get_subscription.return_value = mock_subscription
        
        # Add subscriber to topic
        topic_manager._topic_subscribers["test.subscribers"].add("sub-123")
        
        # Get subscribers
        subscribers = await topic_manager.get_topic_subscribers("test.subscribers")
        
        assert len(subscribers) == 1
        assert subscribers[0]["subscription_id"] == "sub-123"
        assert subscribers[0]["llm_id"] == "llm-1"
        assert subscribers[0]["message_count"] == 5
        assert subscribers[0]["delivery_mode"] == "realtime"
    
    @pytest.mark.asyncio
    async def test_topic_statistics(self, topic_manager):
        """Test getting topic manager statistics"""
        # Create some topics
        for i in range(3):
            config = TopicConfig(name=f"test.stats.{i}")
            topic = await topic_manager.create_topic(config)
            topic.subscriber_count = i + 1
            topic.message_count = (i + 1) * 10
        
        stats = await topic_manager.get_statistics()
        
        assert stats["total_topics"] == 3
        assert stats["active_topics"] == 3
        assert stats["total_subscribers"] == 6  # 1 + 2 + 3
        assert stats["total_messages"] == 60  # 10 + 20 + 30
        assert stats["running"] is True
    
    @pytest.mark.asyncio
    async def test_topic_subscription_limits(self, topic_manager):
        """Test topic subscription limits"""
        # Create topic with low subscriber limit
        config = TopicConfig(name="test.limits", max_subscribers=1)
        topic = await topic_manager.create_topic(config)
        
        # First subscription should succeed
        await topic_manager.subscribe_to_topic("llm-1", "test.limits")
        
        # Update subscriber count to simulate limit reached
        topic.subscriber_count = 1
        
        # Second subscription should fail
        with pytest.raises(ValueError, match="has reached maximum subscribers"):
            await topic_manager.subscribe_to_topic("llm-2", "test.limits")
    
    @pytest.mark.asyncio
    async def test_nonexistent_topic_operations(self, topic_manager):
        """Test operations on nonexistent topics"""
        # Try to subscribe to nonexistent topic
        with pytest.raises(ValueError, match="does not exist or is inactive"):
            await topic_manager.subscribe_to_topic("llm-1", "nonexistent.topic")
        
        # Try to publish to nonexistent topic
        with pytest.raises(ValueError, match="does not exist or is inactive"):
            await topic_manager.publish_to_topic("nonexistent.topic", {"content": "test"})
        
        # Try to delete nonexistent topic
        success = await topic_manager.delete_topic("nonexistent.topic")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_topic_cleanup_functionality(self, topic_manager):
        """Test topic cleanup functionality"""
        # Create topic with short cleanup time
        config = TopicConfig(
            name="test.cleanup",
            auto_cleanup=True,
            cleanup_after_hours=1
        )
        topic = await topic_manager.create_topic(config)
        
        # Simulate old last activity
        topic.last_activity = datetime.utcnow() - timedelta(hours=2)
        topic.subscriber_count = 0  # No active subscribers
        
        # Run cleanup
        await topic_manager._cleanup_inactive_topics()
        
        # Topic should be deleted
        cleaned_topic = await topic_manager.get_topic("test.cleanup")
        assert cleaned_topic is None


class TestTopicIntegration:
    """Integration tests for topic functionality"""
    
    @pytest.mark.asyncio
    async def test_complete_topic_workflow(self, topic_manager, subscription_manager):
        """Test complete topic workflow from creation to deletion"""
        # 1. Create hierarchical topic
        config = TopicConfig(
            name="integration.test.workflow",
            description="Integration test topic",
            max_subscribers=10
        )
        topic = await topic_manager.create_topic(config)
        
        assert topic.config.name == "integration.test.workflow"
        assert topic.is_hierarchical is True
        
        # 2. Subscribe multiple LLMs
        subscriptions = []
        for i in range(3):
            sub = await topic_manager.subscribe_to_topic(
                llm_id=f"llm-{i}",
                topic_name="integration.test.workflow",
                options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
            )
            subscriptions.append(sub)
        
        # 3. Publish messages
        for i in range(5):
            message = {
                "content": f"Test message {i}",
                "routing_info": {"addressing_mode": "topic", "target": "integration.test.workflow"}
            }
            await topic_manager.publish_to_topic("integration.test.workflow", message)
        
        # 4. Verify topic state
        updated_topic = await topic_manager.get_topic("integration.test.workflow")
        assert updated_topic.subscriber_count == 3
        assert updated_topic.message_count == 5
        
        # 5. Get subscribers
        subscribers = await topic_manager.get_topic_subscribers("integration.test.workflow")
        assert len(subscribers) == 3
        
        # 6. Unsubscribe all
        for sub in subscriptions:
            await topic_manager.unsubscribe_from_topic(sub.id)
        
        # 7. Delete topic
        success = await topic_manager.delete_topic("integration.test.workflow")
        assert success is True
        
        # 8. Verify cleanup
        final_topic = await topic_manager.get_topic("integration.test.workflow")
        assert final_topic is None
    
    @pytest.mark.asyncio
    async def test_hierarchical_message_propagation(self, topic_manager, subscription_manager):
        """Test message propagation in hierarchical topics"""
        # Create hierarchical topics
        parent_config = TopicConfig(name="events")
        child_config = TopicConfig(name="events.user")
        grandchild_config = TopicConfig(name="events.user.login")
        
        await topic_manager.create_topic(parent_config)
        await topic_manager.create_topic(child_config)
        await topic_manager.create_topic(grandchild_config)
        
        # Subscribe to parent with children included
        parent_sub = await topic_manager.subscribe_to_topic(
            llm_id="llm-parent",
            topic_name="events",
            include_children=True
        )
        
        # Subscribe to specific child
        child_sub = await topic_manager.subscribe_to_topic(
            llm_id="llm-child",
            topic_name="events.user.login"
        )
        
        # Publish to grandchild topic
        message = {
            "content": "User logged in",
            "routing_info": {"addressing_mode": "topic", "target": "events.user.login"}
        }
        
        await topic_manager.publish_to_topic("events.user.login", message)
        
        # Verify message delivery was attempted
        subscription_manager.deliver_message.assert_called()
        
        # Both subscriptions should receive the message due to pattern matching
        assert parent_sub.pattern == "events.*"
        assert child_sub.target == "events.user.login"


if __name__ == "__main__":
    pytest.main([__file__])