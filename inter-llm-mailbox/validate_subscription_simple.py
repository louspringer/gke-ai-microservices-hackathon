#!/usr/bin/env python3
"""
Simple validation script for Subscription Manager implementation
"""

import asyncio
import logging
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.subscription_manager import SubscriptionManager, ConnectionState, DeliveryResult
from src.models.subscription import Subscription, SubscriptionOptions, MessageFilter
from src.models.enums import DeliveryMode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """Test basic subscription manager functionality"""
    logger.info("Testing basic subscription manager functionality...")
    
    # Create mock dependencies
    redis_manager = AsyncMock()
    redis_manager.is_connected = True
    redis_manager.get_connection.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
    redis_manager.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
    
    pubsub_manager = AsyncMock()
    pubsub_manager.is_running = True
    pubsub_manager.active_subscriptions = {}
    
    # Create subscription manager
    sub_manager = SubscriptionManager(redis_manager, pubsub_manager)
    
    # Mock Redis operations
    sub_manager._load_subscriptions = AsyncMock()
    sub_manager._save_subscriptions = AsyncMock()
    sub_manager._save_subscription = AsyncMock()
    sub_manager._delete_subscription = AsyncMock()
    
    try:
        # Start the manager
        await sub_manager.start()
        logger.info("✓ Subscription manager started successfully")
        
        # Test subscription creation
        llm_id = "test-llm-001"
        target = "test-mailbox"
        
        subscription = await sub_manager.create_subscription(llm_id, target)
        
        assert subscription is not None
        assert subscription.llm_id == llm_id
        assert subscription.target == target
        assert subscription.active is True
        
        logger.info(f"✓ Created subscription: {subscription.id}")
        
        # Test subscription retrieval
        retrieved = await sub_manager.get_subscription(subscription.id)
        assert retrieved is not None
        assert retrieved.id == subscription.id
        
        logger.info("✓ Subscription retrieval works")
        
        # Test active subscriptions
        active_subs = await sub_manager.get_active_subscriptions(llm_id)
        assert len(active_subs) == 1
        assert active_subs[0].id == subscription.id
        
        logger.info("✓ Active subscriptions listing works")
        
        # Test connection state management
        await sub_manager._ensure_connection_state(llm_id)
        assert llm_id in sub_manager._connection_states
        
        connection_state = sub_manager._connection_states[llm_id]
        assert connection_state.connected is True
        
        logger.info("✓ Connection state management works")
        
        # Test connection loss handling
        await sub_manager.handle_connection_loss(llm_id)
        assert connection_state.connected is False
        assert subscription.active is False
        
        logger.info("✓ Connection loss handling works")
        
        # Test connection restoration
        await sub_manager.handle_connection_restored(llm_id)
        assert connection_state.connected is True
        assert subscription.active is True
        
        logger.info("✓ Connection restoration works")
        
        # Test delivery handler registration
        handler = AsyncMock()
        await sub_manager.register_delivery_handler(llm_id, handler)
        assert sub_manager._delivery_handlers[llm_id] == handler
        
        logger.info("✓ Delivery handler registration works")
        
        # Test message queuing
        test_message = {"content": "test message"}
        await sub_manager._queue_message(llm_id, test_message, subscription)
        
        assert len(connection_state.message_queue) == 1
        assert connection_state.message_queue[0]['message'] == test_message
        
        logger.info("✓ Message queuing works")
        
        # Test subscription removal
        removed = await sub_manager.remove_subscription(subscription.id)
        assert removed is True
        assert subscription.id not in sub_manager._subscriptions
        
        logger.info("✓ Subscription removal works")
        
        # Test statistics
        stats = await sub_manager.get_statistics()
        assert isinstance(stats, dict)
        assert "total_subscriptions" in stats
        assert "running" in stats
        assert stats["running"] is True
        
        logger.info("✓ Statistics collection works")
        
        logger.info("🎉 All basic functionality tests passed!")
        
    finally:
        await sub_manager.stop()
        logger.info("✓ Subscription manager stopped successfully")


async def test_subscription_options():
    """Test subscription options and filtering"""
    logger.info("Testing subscription options...")
    
    # Test SubscriptionOptions creation
    options = SubscriptionOptions(
        delivery_mode=DeliveryMode.REALTIME,
        max_queue_size=100,
        auto_ack=True
    )
    
    assert options.delivery_mode == DeliveryMode.REALTIME
    assert options.max_queue_size == 100
    assert options.auto_ack is True
    
    logger.info("✓ SubscriptionOptions creation works")
    
    # Test MessageFilter
    message_filter = MessageFilter(
        content_types=["text/plain"],
        keywords=["important"]
    )
    
    # Test filter matching
    matching_message = {
        "payload": "This is an important message",
        "content_type": "text/plain"
    }
    
    non_matching_message = {
        "payload": "This is a regular message",
        "content_type": "application/json"
    }
    
    assert message_filter.matches(matching_message) is True
    assert message_filter.matches(non_matching_message) is False
    
    logger.info("✓ MessageFilter works correctly")
    
    # Test serialization
    filter_dict = message_filter.to_dict()
    restored_filter = MessageFilter.from_dict(filter_dict)
    
    assert restored_filter.content_types == message_filter.content_types
    assert restored_filter.keywords == message_filter.keywords
    
    logger.info("✓ MessageFilter serialization works")


async def test_subscription_model():
    """Test Subscription model functionality"""
    logger.info("Testing Subscription model...")
    
    # Test subscription creation
    llm_id = "test-llm"
    target = "test-mailbox"
    
    subscription = Subscription.create(llm_id, target)
    
    assert subscription.llm_id == llm_id
    assert subscription.target == target
    assert subscription.active is True
    assert subscription.message_count == 0
    
    logger.info("✓ Subscription creation works")
    
    # Test pattern matching
    pattern_sub = Subscription.create(llm_id, "test-*", pattern="test-*")
    
    assert pattern_sub.matches_target("test-mailbox") is True
    assert pattern_sub.matches_target("other-mailbox") is False
    
    logger.info("✓ Pattern matching works")
    
    # Test activity tracking
    subscription.increment_message_count()
    assert subscription.message_count == 1
    
    logger.info("✓ Activity tracking works")
    
    # Test validation
    assert subscription.validate() is True
    
    # Test invalid subscription
    invalid_sub = Subscription("", "", "")  # Empty required fields
    assert invalid_sub.validate() is False
    
    logger.info("✓ Subscription validation works")
    
    # Test serialization
    sub_dict = subscription.to_dict()
    restored_sub = Subscription.from_dict(sub_dict)
    
    assert restored_sub.id == subscription.id
    assert restored_sub.llm_id == subscription.llm_id
    assert restored_sub.target == subscription.target
    
    logger.info("✓ Subscription serialization works")


async def test_connection_state():
    """Test ConnectionState functionality"""
    logger.info("Testing ConnectionState...")
    
    llm_id = "test-llm"
    state = ConnectionState(llm_id=llm_id)
    
    assert state.llm_id == llm_id
    assert state.connected is True
    assert state.reconnect_count == 0
    assert len(state.message_queue) == 0
    
    logger.info("✓ ConnectionState creation works")


async def test_delivery_result():
    """Test DeliveryResult functionality"""
    logger.info("Testing DeliveryResult...")
    
    # Test successful result
    success_result = DeliveryResult("sub-123", True)
    assert success_result.subscription_id == "sub-123"
    assert success_result.success is True
    assert success_result.error is None
    
    # Test failed result
    failed_result = DeliveryResult("sub-456", False, "Connection failed", 2)
    assert failed_result.subscription_id == "sub-456"
    assert failed_result.success is False
    assert failed_result.error == "Connection failed"
    assert failed_result.retry_count == 2
    
    logger.info("✓ DeliveryResult works correctly")


async def run_all_tests():
    """Run all validation tests"""
    logger.info("Starting Subscription Manager validation tests...")
    
    tests = [
        test_subscription_model,
        test_subscription_options,
        test_connection_state,
        test_delivery_result,
        test_basic_functionality
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            logger.error(f"Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
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