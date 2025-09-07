#!/usr/bin/env python3
"""
Validation script for real-time message delivery implementation.

This script validates the implementation of task 8: "Implement real-time message delivery"
by testing the core functionality with actual Redis connections.
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import our modules
from src.core.redis_manager import RedisConnectionManager, RedisConfig
from src.core.redis_pubsub import RedisPubSubManager
from src.core.subscription_manager import SubscriptionManager
from src.core.realtime_delivery import RealtimeDeliveryService
from src.core.enhanced_message_router import EnhancedMessageRouter
from src.models.message import Message, RoutingInfo
from src.models.subscription import SubscriptionOptions
from src.models.enums import ContentType, AddressingMode, Priority, DeliveryMode


class TestLLMHandler:
    """Mock LLM handler for testing"""
    
    def __init__(self, llm_id: str):
        self.llm_id = llm_id
        self.received_messages = []
        self.call_count = 0
    
    async def handle_message(self, delivery_context: Dict[str, Any]):
        """Handle incoming message"""
        self.call_count += 1
        message_data = delivery_context['message']
        subscriptions = delivery_context['subscriptions']
        
        self.received_messages.append({
            'message_id': message_data['id'],
            'content': message_data['payload'],
            'sender': message_data['sender_id'],
            'target': message_data['routing_info']['target'],
            'subscriptions': len(subscriptions),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"LLM {self.llm_id} received message {message_data['id']} "
                   f"from {message_data['sender_id']} (call #{self.call_count})")


async def test_basic_realtime_delivery():
    """Test basic real-time message delivery"""
    logger.info("=== Testing Basic Real-time Delivery ===")
    
    # Initialize components
    redis_config = RedisConfig()
    redis_manager = RedisConnectionManager(redis_config)
    await redis_manager.connect()
    
    pubsub_manager = RedisPubSubManager(redis_manager)
    await pubsub_manager.start()
    
    subscription_manager = SubscriptionManager(redis_manager, pubsub_manager)
    await subscription_manager.start()
    
    realtime_delivery = RealtimeDeliveryService(redis_manager, pubsub_manager, subscription_manager)
    await realtime_delivery.start()
    
    try:
        # Create test LLM handlers
        llm1_handler = TestLLMHandler("test-llm-1")
        llm2_handler = TestLLMHandler("test-llm-2")
        
        # Register handlers
        await realtime_delivery.register_delivery_handler("test-llm-1", llm1_handler.handle_message)
        await realtime_delivery.register_delivery_handler("test-llm-2", llm2_handler.handle_message)
        
        # Create subscriptions
        sub1 = await subscription_manager.create_subscription(
            llm_id="test-llm-1",
            target="test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        sub2 = await subscription_manager.create_subscription(
            llm_id="test-llm-2",
            target="test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        logger.info(f"Created subscriptions: {sub1.id}, {sub2.id}")
        
        # Create and broadcast test message
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test-mailbox",
            priority=Priority.NORMAL
        )
        
        test_message = Message.create(
            sender_id="test-sender",
            content="Hello from real-time delivery test!",
            content_type=ContentType.TEXT,
            routing_info=routing_info
        )
        
        # Broadcast message
        start_time = time.time()
        result = await realtime_delivery.broadcast_message(test_message)
        delivery_time = (time.time() - start_time) * 1000
        
        logger.info(f"Broadcast result: {result.subscribers_reached} subscribers reached in {delivery_time:.2f}ms")
        
        # Wait a moment for async delivery
        await asyncio.sleep(0.1)
        
        # Verify delivery
        assert llm1_handler.call_count == 1, f"LLM1 should receive 1 message, got {llm1_handler.call_count}"
        assert llm2_handler.call_count == 1, f"LLM2 should receive 1 message, got {llm2_handler.call_count}"
        assert result.subscribers_reached == 2, f"Should reach 2 subscribers, got {result.subscribers_reached}"
        
        logger.info("✓ Basic real-time delivery test passed")
        
    finally:
        await realtime_delivery.stop()
        await subscription_manager.stop()
        await pubsub_manager.stop()
        await redis_manager.disconnect()


async def test_pattern_based_subscriptions():
    """Test pattern-based subscription support with wildcards"""
    logger.info("=== Testing Pattern-based Subscriptions ===")
    
    # Initialize components
    redis_config = RedisConfig()
    redis_manager = RedisConnectionManager(redis_config)
    await redis_manager.connect()
    
    pubsub_manager = RedisPubSubManager(redis_manager)
    await pubsub_manager.start()
    
    subscription_manager = SubscriptionManager(redis_manager, pubsub_manager)
    await subscription_manager.start()
    
    realtime_delivery = RealtimeDeliveryService(redis_manager, pubsub_manager, subscription_manager)
    await realtime_delivery.start()
    
    try:
        # Create test LLM handlers
        pattern_handler = TestLLMHandler("pattern-llm")
        wildcard_handler = TestLLMHandler("wildcard-llm")
        
        # Register handlers
        await realtime_delivery.register_delivery_handler("pattern-llm", pattern_handler.handle_message)
        await realtime_delivery.register_delivery_handler("wildcard-llm", wildcard_handler.handle_message)
        
        # Create pattern subscriptions
        pattern_sub = await subscription_manager.create_subscription(
            llm_id="pattern-llm",
            target="ai.models.*",
            pattern="ai.models.*",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        wildcard_sub = await subscription_manager.create_subscription(
            llm_id="wildcard-llm",
            target="*",
            pattern="*",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        logger.info(f"Created pattern subscriptions: {pattern_sub.id}, {wildcard_sub.id}")
        
        # Test messages with different targets
        test_cases = [
            ("ai.models.gpt4", True, True),    # Should match both patterns
            ("ai.models.claude", True, True),  # Should match both patterns
            ("ai.training.data", False, True), # Should match only wildcard
            ("other.service", False, True),    # Should match only wildcard
        ]
        
        for target, should_match_pattern, should_match_wildcard in test_cases:
            # Reset counters
            pattern_handler.call_count = 0
            wildcard_handler.call_count = 0
            
            # Create message
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.TOPIC,
                target=target,
                priority=Priority.NORMAL
            )
            
            test_message = Message.create(
                sender_id="pattern-test-sender",
                content=f"Message for {target}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            
            # Broadcast message
            result = await realtime_delivery.broadcast_message(test_message)
            await asyncio.sleep(0.1)  # Wait for delivery
            
            # Verify pattern matching
            expected_pattern_calls = 1 if should_match_pattern else 0
            expected_wildcard_calls = 1 if should_match_wildcard else 0
            
            assert pattern_handler.call_count == expected_pattern_calls, \
                f"Pattern handler for {target}: expected {expected_pattern_calls}, got {pattern_handler.call_count}"
            
            assert wildcard_handler.call_count == expected_wildcard_calls, \
                f"Wildcard handler for {target}: expected {expected_wildcard_calls}, got {wildcard_handler.call_count}"
            
            logger.info(f"✓ Pattern test for {target}: pattern={pattern_handler.call_count}, wildcard={wildcard_handler.call_count}")
        
        logger.info("✓ Pattern-based subscription test passed")
        
    finally:
        await realtime_delivery.stop()
        await subscription_manager.stop()
        await pubsub_manager.stop()
        await redis_manager.disconnect()


async def test_enhanced_message_router():
    """Test enhanced message router with real-time delivery integration"""
    logger.info("=== Testing Enhanced Message Router ===")
    
    # Initialize components
    redis_config = RedisConfig()
    redis_manager = RedisConnectionManager(redis_config)
    await redis_manager.connect()
    
    pubsub_manager = RedisPubSubManager(redis_manager)
    await pubsub_manager.start()
    
    subscription_manager = SubscriptionManager(redis_manager, pubsub_manager)
    await subscription_manager.start()
    
    enhanced_router = EnhancedMessageRouter(redis_manager, pubsub_manager, subscription_manager)
    await enhanced_router.start()
    
    try:
        # Create test LLM handler
        router_handler = TestLLMHandler("router-test-llm")
        
        # Register handler with router
        await enhanced_router.register_llm_handler("router-test-llm", router_handler.handle_message)
        
        # Create subscription
        sub = await subscription_manager.create_subscription(
            llm_id="router-test-llm",
            target="router-test-mailbox",
            options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
        )
        
        logger.info(f"Created subscription: {sub.id}")
        
        # Create test message
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="router-test-mailbox",
            priority=Priority.NORMAL
        )
        
        test_message = Message.create(
            sender_id="router-test-sender",
            content="Hello from enhanced router!",
            content_type=ContentType.TEXT,
            routing_info=routing_info
        )
        
        # Route message through enhanced router
        start_time = time.time()
        result = await enhanced_router.route_message(test_message)
        routing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Routing result: {result.value} in {routing_time:.2f}ms")
        
        # Wait for delivery
        await asyncio.sleep(0.1)
        
        # Verify delivery
        assert router_handler.call_count == 1, f"Handler should receive 1 message, got {router_handler.call_count}"
        assert result.value == "success", f"Routing should succeed, got {result.value}"
        
        # Get statistics
        stats = await enhanced_router.get_enhanced_statistics()
        logger.info(f"Enhanced router stats: {json.dumps(stats, indent=2, default=str)}")
        
        logger.info("✓ Enhanced message router test passed")
        
    finally:
        await enhanced_router.stop()
        await redis_manager.disconnect()


async def test_performance_and_statistics():
    """Test performance and statistics collection"""
    logger.info("=== Testing Performance and Statistics ===")
    
    # Initialize components
    redis_config = RedisConfig()
    redis_manager = RedisConnectionManager(redis_config)
    await redis_manager.connect()
    
    pubsub_manager = RedisPubSubManager(redis_manager)
    await pubsub_manager.start()
    
    subscription_manager = SubscriptionManager(redis_manager, pubsub_manager)
    await subscription_manager.start()
    
    realtime_delivery = RealtimeDeliveryService(redis_manager, pubsub_manager, subscription_manager)
    await realtime_delivery.start()
    
    try:
        # Create multiple LLM handlers
        handlers = []
        for i in range(5):
            handler = TestLLMHandler(f"perf-test-llm-{i+1}")
            handlers.append(handler)
            await realtime_delivery.register_delivery_handler(f"perf-test-llm-{i+1}", handler.handle_message)
            
            # Create subscription
            await subscription_manager.create_subscription(
                llm_id=f"perf-test-llm-{i+1}",
                target="perf-test-mailbox",
                options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
            )
        
        # Send multiple messages
        message_count = 10
        total_start_time = time.time()
        
        for i in range(message_count):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="perf-test-mailbox",
                priority=Priority.NORMAL
            )
            
            test_message = Message.create(
                sender_id="perf-test-sender",
                content=f"Performance test message {i+1}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            
            result = await realtime_delivery.broadcast_message(test_message)
            assert result.subscribers_reached == 5, f"Should reach 5 subscribers, got {result.subscribers_reached}"
        
        total_time = (time.time() - total_start_time) * 1000
        
        # Wait for all deliveries
        await asyncio.sleep(0.5)
        
        # Verify all handlers received all messages
        for i, handler in enumerate(handlers):
            assert handler.call_count == message_count, \
                f"Handler {i+1} should receive {message_count} messages, got {handler.call_count}"
        
        # Get statistics
        stats = await realtime_delivery.get_delivery_statistics()
        
        logger.info(f"Performance test results:")
        logger.info(f"  Messages sent: {message_count}")
        logger.info(f"  Subscribers: {len(handlers)}")
        logger.info(f"  Total time: {total_time:.2f}ms")
        logger.info(f"  Average per message: {total_time/message_count:.2f}ms")
        logger.info(f"  Messages broadcast: {stats['messages_broadcast']}")
        logger.info(f"  Subscribers reached: {stats['subscribers_reached']}")
        logger.info(f"  Average latency: {stats['average_latency_ms']:.2f}ms")
        
        logger.info("✓ Performance and statistics test passed")
        
    finally:
        await realtime_delivery.stop()
        await subscription_manager.stop()
        await pubsub_manager.stop()
        await redis_manager.disconnect()


async def main():
    """Run all validation tests"""
    logger.info("Starting real-time delivery validation tests...")
    
    try:
        await test_basic_realtime_delivery()
        await test_pattern_based_subscriptions()
        await test_enhanced_message_router()
        await test_performance_and_statistics()
        
        logger.info("🎉 All real-time delivery tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())