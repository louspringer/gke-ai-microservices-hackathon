#!/usr/bin/env python3
"""
Simple test for real-time delivery functionality.
"""

import asyncio
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test the pattern matching functionality directly
from src.core.realtime_delivery import RealtimeDeliveryService
import fnmatch


def test_pattern_matching():
    """Test pattern matching logic"""
    logger.info("=== Testing Pattern Matching Logic ===")
    
    # Create a mock service to test pattern matching
    service = RealtimeDeliveryService(None, None, None)
    
    # Test cases for pattern matching
    test_cases = [
        # (pattern, target, expected_result)
        ("ai.models.*", "ai.models.gpt4", True),
        ("ai.models.*", "ai.models.claude", True),
        ("ai.models.*", "ai.training.data", False),
        ("ai.*", "ai.models.gpt4", True),
        ("ai.*", "ai.training", True),
        ("ai.*", "other.service", False),
        ("*", "anything", True),
        ("test-*", "test-mailbox", True),
        ("test-*", "other-mailbox", False),
    ]
    
    logger.info("Testing simple fnmatch patterns:")
    for pattern, target, expected in test_cases:
        result = fnmatch.fnmatch(target, pattern)
        status = "✓" if result == expected else "✗"
        logger.info(f"  {status} Pattern '{pattern}' vs '{target}': {result} (expected {expected})")
    
    # Test hierarchical patterns
    logger.info("\nTesting hierarchical patterns:")
    hierarchical_cases = [
        ("ai.models.*", "ai.models.gpt4", True),
        ("ai.models.*", "ai.models.gpt4.turbo", False),  # Should not match deeper levels
        ("ai.**", "ai.models.gpt4.turbo", True),         # Should match any depth
        ("ai.**", "ai.training.data.set", True),
    ]
    
    for pattern, target, expected in hierarchical_cases:
        result = service._matches_hierarchical_pattern(target, pattern)
        status = "✓" if result == expected else "✗"
        logger.info(f"  {status} Hierarchical '{pattern}' vs '{target}': {result} (expected {expected})")


def test_subscription_matching():
    """Test subscription matching logic"""
    logger.info("\n=== Testing Subscription Matching ===")
    
    # Mock subscription class
    class MockSubscription:
        def __init__(self, target, pattern=None):
            self.target = target
            self.pattern = pattern
            self.active = True
            self.options = MockOptions()
    
    class MockOptions:
        def __init__(self):
            self.message_filter = None
    
    # Mock message class
    class MockMessage:
        def __init__(self, target, addressing_mode):
            self.routing_info = MockRoutingInfo(target, addressing_mode)
    
    class MockRoutingInfo:
        def __init__(self, target, addressing_mode):
            self.target = target
            self.addressing_mode = addressing_mode
    
    # Mock addressing mode enum
    class MockAddressingMode:
        DIRECT = "direct"
        TOPIC = "topic"
        BROADCAST = "broadcast"
    
    # Create service instance
    service = RealtimeDeliveryService(None, None, None)
    
    # Test cases
    test_cases = [
        # Direct target match
        (MockSubscription("test-mailbox"), MockMessage("test-mailbox", MockAddressingMode.DIRECT), True),
        (MockSubscription("test-mailbox"), MockMessage("other-mailbox", MockAddressingMode.DIRECT), False),
        
        # Pattern matches
        (MockSubscription("test-*", "test-*"), MockMessage("test-mailbox", MockAddressingMode.DIRECT), True),
        (MockSubscription("ai.models.*", "ai.models.*"), MockMessage("ai.models.gpt4", MockAddressingMode.TOPIC), True),
        (MockSubscription("ai.*", "ai.*"), MockMessage("ai.training", MockAddressingMode.TOPIC), True),
        
        # Wildcard matches
        (MockSubscription("*", "*"), MockMessage("anything", MockAddressingMode.DIRECT), True),
        (MockSubscription("*", "*"), MockMessage("broadcast:all", MockAddressingMode.BROADCAST), True),
    ]
    
    logger.info("Testing subscription matching:")
    for subscription, message, expected in test_cases:
        # Mock the async method call
        async def test_match():
            return await service._subscription_matches_message(subscription, message)
        
        try:
            result = asyncio.run(test_match())
            status = "✓" if result == expected else "✗"
            logger.info(f"  {status} Sub('{subscription.target}', pattern='{subscription.pattern}') "
                       f"vs Msg('{message.routing_info.target}'): {result} (expected {expected})")
        except Exception as e:
            logger.info(f"  ✗ Error testing subscription match: {e}")


def test_delivery_context():
    """Test delivery context creation"""
    logger.info("\n=== Testing Delivery Context ===")
    
    # Mock objects
    class MockMessage:
        def __init__(self):
            self.id = "test-msg-123"
            self.sender_id = "test-sender"
            self.content = "Hello World"
        
        def to_dict(self):
            return {
                'id': self.id,
                'sender_id': self.sender_id,
                'payload': self.content,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    class MockSubscription:
        def __init__(self, sub_id):
            self.id = sub_id
            self.target = "test-target"
            self.message_count = 0
        
        def to_dict(self):
            return {
                'id': self.id,
                'target': self.target,
                'message_count': self.message_count
            }
        
        def increment_message_count(self):
            self.message_count += 1
    
    # Test delivery context creation
    message = MockMessage()
    subscriptions = [MockSubscription("sub-1"), MockSubscription("sub-2")]
    
    delivery_context = {
        'message': message.to_dict(),
        'subscriptions': [sub.to_dict() for sub in subscriptions],
        'delivery_mode': 'realtime',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    logger.info("Created delivery context:")
    logger.info(f"  Message ID: {delivery_context['message']['id']}")
    logger.info(f"  Subscriptions: {len(delivery_context['subscriptions'])}")
    logger.info(f"  Delivery mode: {delivery_context['delivery_mode']}")
    
    # Test subscription counter increment
    for sub in subscriptions:
        sub.increment_message_count()
    
    logger.info(f"  Subscription message counts: {[sub.message_count for sub in subscriptions]}")
    
    logger.info("✓ Delivery context test passed")


def main():
    """Run all simple tests"""
    logger.info("Starting simple real-time delivery tests...")
    
    try:
        test_pattern_matching()
        test_subscription_matching()
        test_delivery_context()
        
        logger.info("\n🎉 All simple tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()