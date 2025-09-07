#!/usr/bin/env python3
"""
Simple test for Message Router implementation

This script tests the basic functionality of the Message Router
without requiring a full Redis setup.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from core.message_router import MessageRouter, RoutingResult, DeliveryConfirmation, RoutingInfo
    from models.message import Message, RoutingInfo as MessageRoutingInfo, DeliveryOptions
    from models.enums import AddressingMode, ContentType, Priority, DeliveryStatus
    print("✓ Successfully imported Message Router components")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


async def test_message_router_basic():
    """Test basic Message Router functionality"""
    print("\n=== Testing Message Router Basic Functionality ===")
    
    # Create mock dependencies
    redis_manager = AsyncMock()
    redis_manager.is_connected = True
    
    # Mock Redis connection
    redis_conn = AsyncMock()
    redis_manager.get_connection.return_value.__aenter__.return_value = redis_conn
    redis_manager.get_connection.return_value.__aexit__.return_value = None
    
    pubsub_manager = AsyncMock()
    pubsub_manager.is_running = True
    pubsub_manager.publish.return_value = 1  # Mock 1 subscriber
    
    # Create message router
    router = MessageRouter(redis_manager, pubsub_manager)
    
    try:
        # Test router lifecycle
        print("Testing router lifecycle...")
        await router.start()
        assert router._running is True
        print("✓ Router started successfully")
        
        # Create test message
        routing_info = MessageRoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test-mailbox",
            priority=Priority.NORMAL
        )
        
        message = Message.create(
            sender_id="test-llm",
            content="Hello, World!",
            content_type=ContentType.TEXT,
            routing_info=routing_info
        )
        
        print("✓ Test message created")
        
        # Test message validation
        print("Testing message validation...")
        validation_result = await router.validate_message(message)
        assert validation_result.is_valid is True
        print("✓ Message validation passed")
        
        # Test message enrichment
        print("Testing message enrichment...")
        enriched = await router.enrich_message(message)
        assert enriched.id == message.id
        assert enriched is not message  # Should be a clone
        assert enriched.get_system_metadata('routed_at') is not None
        print("✓ Message enrichment passed")
        
        # Test message routing
        print("Testing message routing...")
        result = await router.route_message(message)
        assert result in [RoutingResult.SUCCESS, RoutingResult.QUEUED]
        print(f"✓ Message routing passed (result: {result.value})")
        
        # Test delivery confirmation
        print("Testing delivery confirmation...")
        await router.handle_delivery_confirmation(
            message.id, DeliveryStatus.DELIVERED, "test-mailbox", latency_ms=25.5
        )
        
        confirmation = await router.get_delivery_status(message.id)
        if confirmation:
            assert confirmation.message_id == message.id
            assert confirmation.status == DeliveryStatus.DELIVERED
            print("✓ Delivery confirmation passed")
        else:
            print("✓ Delivery confirmation handling passed (no tracking enabled)")
        
        # Test statistics
        print("Testing statistics collection...")
        stats = await router.get_statistics()
        assert 'messages_routed' in stats
        assert 'running' in stats
        assert stats['running'] is True
        print("✓ Statistics collection passed")
        
        # Stop router
        await router.stop()
        assert router._running is False
        print("✓ Router stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_delivery_confirmation():
    """Test DeliveryConfirmation class"""
    print("\n=== Testing DeliveryConfirmation Class ===")
    
    try:
        # Create delivery confirmation
        confirmation = DeliveryConfirmation(
            message_id="test-123",
            target="test-target",
            status=DeliveryStatus.PENDING
        )
        
        assert confirmation.message_id == "test-123"
        assert confirmation.target == "test-target"
        assert confirmation.status == DeliveryStatus.PENDING
        assert len(confirmation.attempts) == 0
        print("✓ DeliveryConfirmation creation passed")
        
        # Test adding attempts
        confirmation.add_attempt("test-target", DeliveryStatus.DELIVERED, latency_ms=25.5)
        
        assert len(confirmation.attempts) == 1
        assert confirmation.attempts[0].status == DeliveryStatus.DELIVERED
        assert confirmation.attempts[0].latency_ms == 25.5
        assert confirmation.status == DeliveryStatus.DELIVERED
        print("✓ Adding delivery attempts passed")
        
        # Test retry logic
        failed_confirmation = DeliveryConfirmation(
            message_id="test-456",
            target="test-target",
            status=DeliveryStatus.FAILED
        )
        
        assert failed_confirmation.should_retry(3) is True
        
        # Add max attempts
        for i in range(3):
            failed_confirmation.add_attempt("test-target", DeliveryStatus.FAILED)
        
        assert failed_confirmation.should_retry(3) is False
        print("✓ Retry logic passed")
        
        return True
        
    except Exception as e:
        print(f"✗ DeliveryConfirmation test failed: {e}")
        return False


async def test_routing_info():
    """Test RoutingInfo class"""
    print("\n=== Testing RoutingInfo Class ===")
    
    try:
        # Test non-expiring routing info
        routing_info = RoutingInfo(
            message_id="test-123",
            sender_id="test-llm",
            addressing_mode=AddressingMode.DIRECT,
            target="test-target",
            priority=Priority.NORMAL
        )
        
        assert routing_info.is_expired() is False
        print("✓ Non-expiring routing info passed")
        
        # Test expiring routing info
        expired_routing = RoutingInfo(
            message_id="test-456",
            sender_id="test-llm",
            addressing_mode=AddressingMode.DIRECT,
            target="test-target",
            priority=Priority.NORMAL,
            ttl=1,
            created_at=datetime.utcnow() - timedelta(seconds=2)
        )
        
        assert expired_routing.is_expired() is True
        print("✓ Expiring routing info passed")
        
        return True
        
    except Exception as e:
        print(f"✗ RoutingInfo test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("Starting Message Router Simple Tests")
    print("=" * 50)
    
    tests = [
        ("Message Router Basic", test_message_router_basic),
        ("DeliveryConfirmation", test_delivery_confirmation),
        ("RoutingInfo", test_routing_info),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"✓ {test_name} test PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} test FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print("MESSAGE ROUTER TEST SUMMARY")
    print("=" * 50)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All Message Router tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} Message Router tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)