"""
Tests for Topic Models
"""

import pytest
from datetime import datetime

from src.models.topic import (
    TopicInfo, TopicMetadata, TopicPermissions, TopicStatistics,
    validate_topic_name, parse_topic_hierarchy, build_topic_tree,
    find_topic_children, find_topic_descendants
)


class TestTopicMetadata:
    """Test TopicMetadata class"""
    
    def test_metadata_creation(self):
        """Test creating topic metadata"""
        metadata = TopicMetadata(
            tags=["ai", "machine-learning"],
            category="research",
            priority=5,
            custom_fields={"owner": "team-ai", "budget": 10000}
        )
        
        assert metadata.tags == ["ai", "machine-learning"]
        assert metadata.category == "research"
        assert metadata.priority == 5
        assert metadata.custom_fields["owner"] == "team-ai"
    
    def test_metadata_serialization(self):
        """Test metadata serialization"""
        metadata = TopicMetadata(
            tags=["test"],
            category="testing",
            custom_fields={"key": "value"}
        )
        
        data = metadata.to_dict()
        assert data["tags"] == ["test"]
        assert data["category"] == "testing"
        assert data["custom_fields"] == {"key": "value"}
        
        # Test deserialization
        restored = TopicMetadata.from_dict(data)
        assert restored.tags == metadata.tags
        assert restored.category == metadata.category
        assert restored.custom_fields == metadata.custom_fields


class TestTopicPermissions:
    """Test TopicPermissions class"""
    
    def test_permissions_creation(self):
        """Test creating topic permissions"""
        permissions = TopicPermissions(
            public_read=False,
            public_write=False,
            allowed_subscribers=["llm-1", "llm-2"],
            allowed_publishers=["llm-1"],
            admin_users=["admin-llm"]
        )
        
        assert permissions.public_read is False
        assert permissions.public_write is False
        assert "llm-1" in permissions.allowed_subscribers
        assert "admin-llm" in permissions.admin_users
    
    def test_permission_checks(self):
        """Test permission checking methods"""
        permissions = TopicPermissions(
            public_read=False,
            public_write=False,
            allowed_subscribers=["llm-1", "llm-2"],
            allowed_publishers=["llm-1"],
            admin_users=["admin-llm"]
        )
        
        # Test subscription permissions
        assert permissions.can_subscribe("llm-1") is True
        assert permissions.can_subscribe("llm-3") is False
        assert permissions.can_subscribe("admin-llm") is True  # Admin can always subscribe
        
        # Test publishing permissions
        assert permissions.can_publish("llm-1") is True
        assert permissions.can_publish("llm-2") is False  # Can subscribe but not publish
        assert permissions.can_publish("admin-llm") is True  # Admin can always publish
        
        # Test admin permissions
        assert permissions.is_admin("admin-llm") is True
        assert permissions.is_admin("llm-1") is False
    
    def test_public_permissions(self):
        """Test public permission settings"""
        public_permissions = TopicPermissions(
            public_read=True,
            public_write=True
        )
        
        # Anyone should be able to subscribe and publish
        assert public_permissions.can_subscribe("any-llm") is True
        assert public_permissions.can_publish("any-llm") is True
        assert public_permissions.is_admin("any-llm") is False
    
    def test_permissions_serialization(self):
        """Test permissions serialization"""
        permissions = TopicPermissions(
            public_read=False,
            allowed_subscribers=["llm-1"],
            admin_users=["admin"]
        )
        
        data = permissions.to_dict()
        assert data["public_read"] is False
        assert data["allowed_subscribers"] == ["llm-1"]
        assert data["admin_users"] == ["admin"]
        
        # Test deserialization
        restored = TopicPermissions.from_dict(data)
        assert restored.public_read == permissions.public_read
        assert restored.allowed_subscribers == permissions.allowed_subscribers
        assert restored.admin_users == permissions.admin_users


class TestTopicStatistics:
    """Test TopicStatistics class"""
    
    def test_statistics_creation(self):
        """Test creating topic statistics"""
        stats = TopicStatistics(
            total_messages=100,
            total_subscribers=10,
            messages_today=5,
            peak_subscribers=15
        )
        
        assert stats.total_messages == 100
        assert stats.total_subscribers == 10
        assert stats.messages_today == 5
        assert stats.peak_subscribers == 15
    
    def test_record_message(self):
        """Test recording a message"""
        stats = TopicStatistics()
        initial_time = stats.last_message_at
        
        stats.record_message()
        
        assert stats.total_messages == 1
        assert stats.messages_today == 1
        assert stats.messages_this_week == 1
        assert stats.last_message_at != initial_time
    
    def test_update_subscriber_count(self):
        """Test updating subscriber count"""
        stats = TopicStatistics()
        
        # Update to higher count
        stats.update_subscriber_count(5)
        assert stats.total_subscribers == 5
        assert stats.peak_subscribers == 5
        
        # Update to lower count (peak should remain)
        stats.update_subscriber_count(3)
        assert stats.total_subscribers == 3
        assert stats.peak_subscribers == 5
        
        # Update to even higher count
        stats.update_subscriber_count(10)
        assert stats.total_subscribers == 10
        assert stats.peak_subscribers == 10
    
    def test_statistics_serialization(self):
        """Test statistics serialization"""
        stats = TopicStatistics(
            total_messages=50,
            peak_subscribers=20,
            last_message_at=datetime.utcnow()
        )
        
        data = stats.to_dict()
        assert data["total_messages"] == 50
        assert data["peak_subscribers"] == 20
        assert "last_message_at" in data
        
        # Test deserialization
        restored = TopicStatistics.from_dict(data)
        assert restored.total_messages == stats.total_messages
        assert restored.peak_subscribers == stats.peak_subscribers
        assert restored.last_message_at == stats.last_message_at


class TestTopicInfo:
    """Test TopicInfo class"""
    
    def test_topic_info_creation(self):
        """Test creating topic info"""
        topic = TopicInfo.create(
            name="ai.ml.training",
            description="Machine learning training topic",
            max_subscribers=500
        )
        
        assert topic.name == "ai.ml.training"
        assert topic.description == "Machine learning training topic"
        assert topic.max_subscribers == 500
        assert topic.id is not None
        assert topic.active is True
    
    def test_hierarchy_properties(self):
        """Test hierarchy-related properties"""
        topic = TopicInfo.create(name="ai.ml.deep_learning.cnn")
        
        assert topic.is_hierarchical is True
        assert topic.hierarchy_parts == ["ai", "ml", "deep_learning", "cnn"]
        assert topic.parent_topics == ["ai", "ai.ml", "ai.ml.deep_learning"]
        assert topic.depth == 3
        
        # Test root topic
        root_topic = TopicInfo.create(name="root")
        assert root_topic.is_hierarchical is False
        assert root_topic.depth == 0
        assert root_topic.parent_topics == []
    
    def test_pattern_matching(self):
        """Test pattern matching"""
        topic = TopicInfo.create(name="events.user.login")
        
        assert topic.matches_pattern("events.*") is True
        assert topic.matches_pattern("events.user.*") is True
        assert topic.matches_pattern("events.user.login") is True
        assert topic.matches_pattern("events.admin.*") is False
        assert topic.matches_pattern("notifications.*") is False
    
    def test_relationship_methods(self):
        """Test relationship checking methods"""
        parent_topic = TopicInfo.create(name="events")
        child_topic = TopicInfo.create(name="events.user")
        grandchild_topic = TopicInfo.create(name="events.user.login")
        unrelated_topic = TopicInfo.create(name="notifications")
        
        # Test is_child_of
        assert child_topic.is_child_of("events") is True
        assert grandchild_topic.is_child_of("events") is True
        assert grandchild_topic.is_child_of("events.user") is True
        assert unrelated_topic.is_child_of("events") is False
        
        # Test is_ancestor_of
        assert parent_topic.is_ancestor_of("events.user") is True
        assert parent_topic.is_ancestor_of("events.user.login") is True
        assert child_topic.is_ancestor_of("events.user.login") is True
        assert unrelated_topic.is_ancestor_of("events.user") is False
    
    def test_pattern_generation(self):
        """Test pattern generation methods"""
        topic = TopicInfo.create(name="events.user")
        
        immediate_pattern = topic.get_immediate_children_pattern()
        assert immediate_pattern == "events.user.*"
        
        all_descendants_pattern = topic.get_all_descendants_pattern()
        assert all_descendants_pattern == "events.user.**"
    
    def test_validation(self):
        """Test topic validation"""
        # Valid topic
        valid_topic = TopicInfo.create(name="valid.topic")
        assert valid_topic.validate() is True
        
        # Invalid topic - empty name
        invalid_topic = TopicInfo.create(name="valid.topic")
        invalid_topic.name = ""
        assert invalid_topic.validate() is False
        
        # Invalid topic - invalid characters
        invalid_topic.name = "invalid@topic"
        assert invalid_topic.validate() is False
        
        # Invalid topic - negative max_subscribers
        invalid_topic.name = "valid.topic"
        invalid_topic.max_subscribers = -1
        assert invalid_topic.validate() is False
    
    def test_serialization(self):
        """Test topic info serialization"""
        topic = TopicInfo.create(
            name="test.topic",
            description="Test topic",
            max_subscribers=100
        )
        topic.metadata.tags = ["test", "example"]
        topic.permissions.public_read = False
        topic.statistics.total_messages = 50
        
        data = topic.to_dict()
        assert data["name"] == "test.topic"
        assert data["description"] == "Test topic"
        assert data["max_subscribers"] == 100
        assert data["metadata"]["tags"] == ["test", "example"]
        assert data["permissions"]["public_read"] is False
        assert data["statistics"]["total_messages"] == 50
        
        # Test deserialization
        restored = TopicInfo.from_dict(data)
        assert restored.name == topic.name
        assert restored.description == topic.description
        assert restored.max_subscribers == topic.max_subscribers
        assert restored.metadata.tags == topic.metadata.tags
        assert restored.permissions.public_read == topic.permissions.public_read
        assert restored.statistics.total_messages == topic.statistics.total_messages
    
    def test_summary(self):
        """Test topic summary generation"""
        topic = TopicInfo.create(
            name="ai.ml.training",
            description="ML training topic"
        )
        topic.statistics.total_subscribers = 5
        topic.statistics.total_messages = 100
        
        summary = topic.to_summary()
        
        assert summary["name"] == "ai.ml.training"
        assert summary["description"] == "ML training topic"
        assert summary["is_hierarchical"] is True
        assert summary["depth"] == 2
        assert summary["subscriber_count"] == 5
        assert summary["message_count"] == 100


class TestTopicUtilities:
    """Test topic utility functions"""
    
    def test_validate_topic_name(self):
        """Test topic name validation"""
        # Valid names
        assert validate_topic_name("simple") is True
        assert validate_topic_name("ai.ml.training") is True
        assert validate_topic_name("events_user-login") is True
        assert validate_topic_name("topic123") is True
        
        # Invalid names
        assert validate_topic_name("") is False
        assert validate_topic_name("invalid@topic") is False
        assert validate_topic_name("topic with spaces") is False
        assert validate_topic_name("a" * 300) is False  # Too long
    
    def test_parse_topic_hierarchy(self):
        """Test topic hierarchy parsing"""
        hierarchy = parse_topic_hierarchy("ai.ml.deep_learning.cnn")
        
        assert hierarchy["name"] == "ai.ml.deep_learning.cnn"
        assert hierarchy["parts"] == ["ai", "ml", "deep_learning", "cnn"]
        assert hierarchy["depth"] == 3
        assert hierarchy["root"] == "ai"
        assert hierarchy["leaf"] == "cnn"
        assert hierarchy["parents"] == ["ai", "ai.ml", "ai.ml.deep_learning"]
        
        # Test simple topic
        simple = parse_topic_hierarchy("simple")
        assert simple["depth"] == 0
        assert simple["parents"] == []
    
    def test_build_topic_tree(self):
        """Test building topic tree structure"""
        topics = [
            TopicInfo.create(name="ai"),
            TopicInfo.create(name="ai.ml"),
            TopicInfo.create(name="ai.ml.supervised"),
            TopicInfo.create(name="ai.ml.unsupervised"),
            TopicInfo.create(name="ai.nlp"),
            TopicInfo.create(name="web"),
            TopicInfo.create(name="web.frontend")
        ]
        
        tree = build_topic_tree(topics)
        
        # Check root level
        assert "ai" in tree
        assert "web" in tree
        
        # Check AI subtree
        ai_node = tree["ai"]
        assert ai_node["_topic"].name == "ai"
        assert "ml" in ai_node["_children"]
        assert "nlp" in ai_node["_children"]
        
        # Check ML subtree
        ml_node = ai_node["_children"]["ml"]
        assert ml_node["_topic"].name == "ai.ml"
        assert "supervised" in ml_node["_children"]
        assert "unsupervised" in ml_node["_children"]
    
    def test_find_topic_children(self):
        """Test finding topic children"""
        topics = [
            TopicInfo.create(name="events"),
            TopicInfo.create(name="events.user"),
            TopicInfo.create(name="events.user.login"),
            TopicInfo.create(name="events.user.logout"),
            TopicInfo.create(name="events.system"),
            TopicInfo.create(name="notifications")
        ]
        
        # Find direct children of "events"
        children = find_topic_children(topics, "events")
        child_names = [t.name for t in children]
        
        assert "events.user" in child_names
        assert "events.system" in child_names
        assert "events.user.login" not in child_names  # Not direct child
        assert "notifications" not in child_names  # Unrelated
        
        # Find children of "events.user"
        user_children = find_topic_children(topics, "events.user")
        user_child_names = [t.name for t in user_children]
        
        assert "events.user.login" in user_child_names
        assert "events.user.logout" in user_child_names
        assert len(user_children) == 2
    
    def test_find_topic_descendants(self):
        """Test finding topic descendants"""
        topics = [
            TopicInfo.create(name="events"),
            TopicInfo.create(name="events.user"),
            TopicInfo.create(name="events.user.login"),
            TopicInfo.create(name="events.user.logout"),
            TopicInfo.create(name="events.system"),
            TopicInfo.create(name="events.system.startup"),
            TopicInfo.create(name="notifications")
        ]
        
        # Find all descendants of "events"
        descendants = find_topic_descendants(topics, "events")
        descendant_names = [t.name for t in descendants]
        
        expected_descendants = [
            "events.user",
            "events.user.login", 
            "events.user.logout",
            "events.system",
            "events.system.startup"
        ]
        
        for expected in expected_descendants:
            assert expected in descendant_names
        
        assert "notifications" not in descendant_names
        assert len(descendants) == 5
        
        # Find descendants of "events.user"
        user_descendants = find_topic_descendants(topics, "events.user")
        user_descendant_names = [t.name for t in user_descendants]
        
        assert "events.user.login" in user_descendant_names
        assert "events.user.logout" in user_descendant_names
        assert "events.system" not in user_descendant_names
        assert len(user_descendants) == 2


if __name__ == "__main__":
    pytest.main([__file__])