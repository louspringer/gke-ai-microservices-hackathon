"""
Unit tests for data models
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.message import Message, RoutingInfo, DeliveryOptions, RetryPolicy
from models.subscription import Subscription, SubscriptionOptions, MessageFilter
from models.permission import Permission, LLMCredentials, AuthTokenData, AccessAuditLog
from models.enums import AddressingMode, ContentType, Priority, DeliveryMode, OperationType


class TestMessage:
    """Test cases for Message model"""
    
    def test_message_creation(self):
        """Test creating a new message"""
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test-mailbox",
            priority=Priority.NORMAL
        )
        
        message = Message.create(
            sender_id="llm-001",
            content="Hello, World!",
            content_type=ContentType.TEXT,
            routing_info=routing_info
        )
        
        assert message.id is not None
        assert message.sender_id == "llm-001"
        assert message.payload == "Hello, World!"
        assert message.content_type == ContentType.TEXT
        assert isinstance(message.timestamp, datetime)
    
    def test_message_validation(self):
        """Test message validation"""
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test-mailbox"
        )
        
        # Valid message
        message = Message.create(
            sender_id="llm-001",
            content="Test",
            content_type=ContentType.TEXT,
            routing_info=routing_info
        )
        result = message.validate(strict=False)
        assert result.is_valid is True
        
        # Invalid message (no sender)
        message.sender_id = ""
        result = message.validate(strict=False)
        assert result.is_valid is False
    
    def test_message_serialization(self):
        """Test message to/from dict conversion"""
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.TOPIC,
            target="ai-collaboration",
            priority=Priority.HIGH
        )
        
        original = Message.create(
            sender_id="llm-002",
            content={"type": "request", "data": "test"},
            content_type=ContentType.JSON,
            routing_info=routing_info
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.id == original.id
        assert restored.sender_id == original.sender_id
        assert restored.content_type == original.content_type
        assert restored.routing_info.addressing_mode == original.routing_info.addressing_mode
    
    def test_message_size_calculation(self):
        """Test message size calculation"""
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test"
        )
        
        message = Message.create(
            sender_id="llm-001",
            content="x" * 1000,  # 1000 character string
            content_type=ContentType.TEXT,
            routing_info=routing_info
        )
        
        size = message.size_bytes()
        assert size > 1000  # Should be larger due to metadata


class TestSubscription:
    """Test cases for Subscription model"""
    
    def test_subscription_creation(self):
        """Test creating a new subscription"""
        options = SubscriptionOptions(
            delivery_mode=DeliveryMode.REALTIME,
            max_queue_size=500
        )
        
        subscription = Subscription.create(
            llm_id="llm-001",
            target="test-mailbox",
            options=options
        )
        
        assert subscription.id is not None
        assert subscription.llm_id == "llm-001"
        assert subscription.target == "test-mailbox"
        assert subscription.active is True
        assert subscription.message_count == 0
    
    def test_pattern_matching(self):
        """Test pattern-based subscription matching"""
        subscription = Subscription.create(
            llm_id="llm-001",
            target="ai.*",
            pattern="ai.*"
        )
        
        assert subscription.matches_target("ai.collaboration") is True
        assert subscription.matches_target("ai.research") is True
        assert subscription.matches_target("human.chat") is False
    
    def test_message_filter(self):
        """Test message filtering"""
        message_filter = MessageFilter(
            content_types=["text/plain"],
            sender_ids=["llm-002"],
            keywords=["urgent"]
        )
        
        # Message that matches filter
        matching_msg = {
            "content_type": "text/plain",
            "sender_id": "llm-002",
            "payload": "This is urgent!"
        }
        assert message_filter.matches(matching_msg) is True
        
        # Message that doesn't match
        non_matching_msg = {
            "content_type": "application/json",
            "sender_id": "llm-002",
            "payload": "Regular message"
        }
        assert message_filter.matches(non_matching_msg) is False
    
    def test_subscription_serialization(self):
        """Test subscription to/from dict conversion"""
        options = SubscriptionOptions(
            delivery_mode=DeliveryMode.BATCH,
            batch_size=20
        )
        
        original = Subscription.create(
            llm_id="llm-003",
            target="notifications",
            options=options
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = Subscription.from_dict(data)
        
        assert restored.id == original.id
        assert restored.llm_id == original.llm_id
        assert restored.options.delivery_mode == original.options.delivery_mode
        assert restored.options.batch_size == original.options.batch_size


class TestPermission:
    """Test cases for Permission model"""
    
    def test_permission_creation(self):
        """Test creating a new permission"""
        permission = Permission.create(
            llm_id="llm-001",
            resource="test-mailbox",
            operation=OperationType.READ,
            granted_by="admin"
        )
        
        assert permission.id is not None
        assert permission.llm_id == "llm-001"
        assert permission.resource == "test-mailbox"
        assert permission.operation == OperationType.READ
        assert permission.active is True
    
    def test_permission_expiration(self):
        """Test permission expiration"""
        # Create permission that expires in 1 hour
        permission = Permission.create(
            llm_id="llm-001",
            resource="temp-mailbox",
            operation=OperationType.WRITE,
            granted_by="admin",
            expires_hours=1
        )
        
        assert permission.is_valid() is True
        
        # Manually set expiration to past
        permission.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert permission.is_valid() is False
    
    def test_resource_matching(self):
        """Test resource pattern matching"""
        permission = Permission.create(
            llm_id="llm-001",
            resource="ai.*",
            operation=OperationType.READ,
            granted_by="admin"
        )
        
        assert permission.matches_resource("ai.collaboration") is True
        assert permission.matches_resource("ai.research") is True
        assert permission.matches_resource("human.chat") is False
        
        # Test global permission
        global_permission = Permission.create(
            llm_id="llm-001",
            resource="*",
            operation=OperationType.ADMIN,
            granted_by="admin"
        )
        assert global_permission.matches_resource("any.resource") is True


class TestCredentials:
    """Test cases for authentication models"""
    
    def test_credentials_creation(self):
        """Test creating LLM credentials"""
        credentials = LLMCredentials.create(
            llm_id="llm-001",
            secret="my-secret-key"
        )
        
        assert credentials.llm_id == "llm-001"
        assert credentials.api_key is not None
        assert credentials.secret_hash is not None
        assert credentials.verify_secret("my-secret-key") is True
        assert credentials.verify_secret("wrong-key") is False
    
    def test_auth_token_creation(self):
        """Test creating authentication tokens"""
        token_data = AuthTokenData.create(
            llm_id="llm-001",
            validity_hours=24
        )
        
        assert token_data.llm_id == "llm-001"
        assert token_data.token is not None
        assert token_data.is_valid() is True
        assert token_data.is_expired() is False
        
        # Test expired token
        token_data.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert token_data.is_valid() is False
        assert token_data.is_expired() is True
    
    def test_audit_log_creation(self):
        """Test creating audit log entries"""
        log_entry = AccessAuditLog.create(
            llm_id="llm-001",
            operation=OperationType.READ,
            resource="test-mailbox",
            success=True,
            ip_address="192.168.1.1"
        )
        
        assert log_entry.id is not None
        assert log_entry.llm_id == "llm-001"
        assert log_entry.operation == OperationType.READ
        assert log_entry.success is True
        assert isinstance(log_entry.timestamp, datetime)


if __name__ == "__main__":
    pytest.main([__file__])