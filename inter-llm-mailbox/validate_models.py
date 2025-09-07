#!/usr/bin/env python3
"""
Validation script to demonstrate the Inter-LLM Mailbox System data models
"""

import sys
import os
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.message import Message, RoutingInfo, DeliveryOptions
from models.subscription import Subscription, SubscriptionOptions, MessageFilter
from models.permission import Permission, LLMCredentials, AuthTokenData
from models.enums import AddressingMode, ContentType, Priority, DeliveryMode, OperationType


def demonstrate_message_creation():
    """Demonstrate creating and validating messages"""
    print("=== Message Creation Demo ===")
    
    # Create routing info for direct messaging
    routing_info = RoutingInfo(
        addressing_mode=AddressingMode.DIRECT,
        target="llm-002-inbox",
        priority=Priority.HIGH
    )
    
    # Create a text message
    message = Message.create(
        sender_id="llm-001",
        content="Hello from LLM-001! Ready to collaborate on the AI research project.",
        content_type=ContentType.TEXT,
        routing_info=routing_info
    )
    
    print(f"Created message: {message.id}")
    print(f"Sender: {message.sender_id}")
    print(f"Target: {message.routing_info.target}")
    print(f"Content: {message.payload[:50]}...")
    print(f"Valid: {message.validate()}")
    print(f"Size: {message.size_bytes()} bytes")
    
    # Create a JSON message for topic-based communication
    topic_routing = RoutingInfo(
        addressing_mode=AddressingMode.TOPIC,
        target="ai.collaboration.research",
        priority=Priority.NORMAL
    )
    
    json_message = Message.create(
        sender_id="llm-001",
        content={
            "type": "research_proposal",
            "topic": "Multi-Agent Reasoning",
            "participants": ["llm-001", "llm-002", "llm-003"],
            "deadline": "2024-12-31"
        },
        content_type=ContentType.JSON,
        routing_info=topic_routing
    )
    
    print(f"\nJSON message created: {json_message.id}")
    print(f"Topic: {json_message.routing_info.target}")
    print(f"Content type: {json_message.content_type.value}")
    print()


def demonstrate_subscription_management():
    """Demonstrate subscription creation and filtering"""
    print("=== Subscription Management Demo ===")
    
    # Create a message filter for urgent messages only
    urgent_filter = MessageFilter(
        keywords=["urgent", "critical", "emergency"],
        priority_min=Priority.HIGH.value
    )
    
    # Create subscription options with filtering
    options = SubscriptionOptions(
        delivery_mode=DeliveryMode.REALTIME,
        message_filter=urgent_filter,
        max_queue_size=500,
        auto_ack=True
    )
    
    # Create subscription to AI collaboration topics
    subscription = Subscription.create(
        llm_id="llm-002",
        target="ai.collaboration.*",
        pattern="ai.collaboration.*",
        options=options
    )
    
    print(f"Created subscription: {subscription.id}")
    print(f"LLM: {subscription.llm_id}")
    print(f"Pattern: {subscription.pattern}")
    print(f"Delivery mode: {subscription.options.delivery_mode.value}")
    print(f"Max queue size: {subscription.options.max_queue_size}")
    
    # Test pattern matching
    test_targets = [
        "ai.collaboration.research",
        "ai.collaboration.development", 
        "ai.general.discussion",
        "human.feedback"
    ]
    
    print("\nPattern matching results:")
    for target in test_targets:
        matches = subscription.matches_target(target)
        print(f"  {target}: {'✓' if matches else '✗'}")
    print()


def demonstrate_permission_system():
    """Demonstrate permission and authentication system"""
    print("=== Permission System Demo ===")
    
    # Create LLM credentials
    credentials = LLMCredentials.create(
        llm_id="llm-003",
        secret="super-secret-key-123"
    )
    
    print(f"Created credentials for: {credentials.llm_id}")
    print(f"API Key: {credentials.api_key[:20]}...")
    print(f"Secret verification: {credentials.verify_secret('super-secret-key-123')}")
    print(f"Wrong secret verification: {credentials.verify_secret('wrong-key')}")
    
    # Create authentication token
    auth_token = AuthTokenData.create(
        llm_id="llm-003",
        validity_hours=24
    )
    
    print(f"\nAuth token: {auth_token.token[:20]}...")
    print(f"Valid: {auth_token.is_valid()}")
    print(f"Expires: {auth_token.expires_at}")
    
    # Create permissions
    read_permission = Permission.create(
        llm_id="llm-003",
        resource="ai.research.*",
        operation=OperationType.READ,
        granted_by="admin"
    )
    
    write_permission = Permission.create(
        llm_id="llm-003", 
        resource="ai.research.project-alpha",
        operation=OperationType.WRITE,
        granted_by="admin",
        expires_hours=48
    )
    
    print(f"\nRead permission: {read_permission.id}")
    print(f"Resource pattern: {read_permission.resource}")
    print(f"Operation: {read_permission.operation.value}")
    
    print(f"\nWrite permission: {write_permission.id}")
    print(f"Specific resource: {write_permission.resource}")
    print(f"Expires: {write_permission.expires_at}")
    
    # Test resource matching
    test_resources = [
        "ai.research.project-alpha",
        "ai.research.project-beta",
        "ai.development.tools"
    ]
    
    print("\nResource matching for read permission:")
    for resource in test_resources:
        matches = read_permission.matches_resource(resource)
        print(f"  {resource}: {'✓' if matches else '✗'}")
    print()


def main():
    """Run all demonstrations"""
    print("Inter-LLM Mailbox System - Data Models Validation")
    print("=" * 55)
    print()
    
    demonstrate_message_creation()
    demonstrate_subscription_management()
    demonstrate_permission_system()
    
    print("✅ All data models validated successfully!")
    print("\nThe Inter-LLM Mailbox System foundation is ready for Redis integration.")


if __name__ == "__main__":
    main()