#!/usr/bin/env python3
"""
Validation script for Message Router implementation

This script validates the Message Router implementation against the requirements:
- 1.1: Message routing based on addressing modes
- 1.3: Delivery confirmation tracking
- 8.4: Retry logic with exponential backoff
- 8.5: Message delivery guarantees
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, 'src')

from core.message_router import MessageRouter, RoutingResult, DeliveryConfirmation
from core.redis_manager import RedisConnectionManager, RedisConfig
from core.redis_pubsub import RedisPubSubManager
from models.message import Message, RoutingInfo, DeliveryOptions
from models.enums import AddressingMode, ContentType, Priority, DeliveryStatus


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MessageRouterValidator:
    """Validates Message Router functionality"""
    
    def __init__(self):
        self.redis_manager = None
        self.pubsub_manager = None
        self.message_router = None
        self.test_results = []
    
    async def setup(self):
        """Set up test environment"""
        logger.info("Setting up Message Router validation environment")
        
        # Create Redis manager
        redis_config = RedisConfig(
            host="localhost",
            port=6379,
            db=1,  # Use test database
            max_connections=10
        )
        
        self.redis_manager = RedisConnectionManager(redis_config)
        await self.redis_manager.initialize()
        
        # Create pub/sub manager
        self.pubsub_manager = RedisPubSubManager(self.redis_manager)
        await self.pubsub_manager.start()
        
        # Create message router
        self.message_router = MessageRouter(self.redis_manager, self.pubsub_manager)
        await self.message_router.start()
        
        logger.info("Message Router validation environment ready")
    
    async def cleanup(self):
        """Clean up test environment"""
        logger.info("Cleaning up Message Router validation environment")
        
        if self.message_router:
            await self.message_router.stop()
        
        if self.pubsub_manager:
            await self.pubsub_manager.stop()
        
        if self.redis_manager:
            # Clean up test data
            try:
                async with self.redis_manager.get_connection() as redis_conn:
                    # Delete test keys
                    keys = await redis_conn.keys("test:*")
                    keys.extend(await redis_conn.keys("mailbox:test-*"))
                    keys.extend(await redis_conn.keys("topic:test-*"))
                    keys.extend(await redis_conn.keys("message:*"))
                    keys.extend(await redis_conn.keys("delivery_confirmation:*"))
                    
                    if keys:
                        await redis_conn.delete(*keys)
                        logger.info(f"Cleaned up {len(keys)} test keys")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
            
            await self.redis_manager.close()
        
        logger.info("Cleanup completed")
    
    def create_test_message(self, addressing_mode: AddressingMode, target: str, 
                          priority: Priority = Priority.NORMAL, ttl: int = None,
                          confirmation_required: bool = False) -> Message:
        """Create a test message"""
        routing_info = RoutingInfo(
            addressing_mode=addressing_mode,
            target=target,
            priority=priority,
            ttl=ttl
        )
        
        delivery_options = DeliveryOptions(
            confirmation_required=confirmation_required,
            persistence=True
        )
        
        return Message.create(
            sender_id="test-llm-validator",
            content=f"Test message for {addressing_mode.value} to {target}",
            content_type=ContentType.TEXT,
            routing_info=routing_info,
            delivery_options=delivery_options
        )
    
    async def test_direct_routing(self) -> bool:
        """Test direct message routing (Requirement 1.1)"""
        logger.info("Testing direct message routing")
        
        try:
            # Create direct message
            message = self.create_test_message(
                AddressingMode.DIRECT, 
                "test-mailbox-direct"
            )
            
            # Route message
            result = await self.message_router.route_message(message)
            
            # Verify routing result
            if result not in [RoutingResult.SUCCESS, RoutingResult.QUEUED]:
                logger.error(f"Direct routing failed: {result}")
                return False
            
            # Verify message was stored
            async with self.redis_manager.get_connection() as redis_conn:
                # Check message storage
                message_exists = await redis_conn.exists(f"message:{message.id}")
                if not message_exists:
                    logger.error("Message was not stored in Redis")
                    return False
                
                # Check mailbox storage
                mailbox_key = f"mailbox:{message.routing_info.target}:messages"
                message_in_mailbox = await redis_conn.zscore(mailbox_key, message.id)
                if message_in_mailbox is None:
                    logger.error("Message was not added to mailbox")
                    return False
            
            logger.info("✓ Direct routing test passed")
            return True
            
        except Exception as e:
            logger.error(f"Direct routing test failed: {e}")
            return False
    
    async def test_broadcast_routing(self) -> bool:
        """Test broadcast message routing (Requirement 1.1)"""
        logger.info("Testing broadcast message routing")
        
        try:
            # Create some test mailboxes first
            test_mailboxes = ["test-mailbox-1", "test-mailbox-2", "test-mailbox-3"]
            
            async with self.redis_manager.get_connection() as redis_conn:
                for mailbox in test_mailboxes:
                    metadata_key = f"mailbox:{mailbox}:metadata"
                    await redis_conn.hset(metadata_key, mapping={
                        'created_at': datetime.utcnow().isoformat(),
                        'message_count': 0
                    })
            
            # Create broadcast message
            message = self.create_test_message(
                AddressingMode.BROADCAST,
                "all"
            )
            
            # Route message
            result = await self.message_router.route_message(message)
            
            # Verify routing result
            if result not in [RoutingResult.SUCCESS, RoutingResult.QUEUED]:
                logger.error(f"Broadcast routing failed: {result}")
                return False
            
            # Verify message was stored in all mailboxes
            async with self.redis_manager.get_connection() as redis_conn:
                for mailbox in test_mailboxes:
                    mailbox_key = f"mailbox:{mailbox}:messages"
                    message_in_mailbox = await redis_conn.zscore(mailbox_key, message.id)
                    if message_in_mailbox is None:
                        logger.error(f"Message was not broadcast to mailbox {mailbox}")
                        return False
            
            logger.info("✓ Broadcast routing test passed")
            return True
            
        except Exception as e:
            logger.error(f"Broadcast routing test failed: {e}")
            return False
    
    async def test_topic_routing(self) -> bool:
        """Test topic message routing (Requirement 1.1)"""
        logger.info("Testing topic message routing")
        
        try:
            # Create topic message
            message = self.create_test_message(
                AddressingMode.TOPIC,
                "test-topic"
            )
            
            # Route message
            result = await self.message_router.route_message(message)
            
            # Verify routing result
            if result not in [RoutingResult.SUCCESS, RoutingResult.QUEUED]:
                logger.error(f"Topic routing failed: {result}")
                return False
            
            # Verify message was stored in topic
            async with self.redis_manager.get_connection() as redis_conn:
                # Check message storage
                message_exists = await redis_conn.exists(f"message:{message.id}")
                if not message_exists:
                    logger.error("Message was not stored in Redis")
                    return False
                
                # Check topic storage
                topic_key = f"topic:{message.routing_info.target}:messages"
                message_in_topic = await redis_conn.zscore(topic_key, message.id)
                if message_in_topic is None:
                    logger.error("Message was not added to topic")
                    return False
            
            logger.info("✓ Topic routing test passed")
            return True
            
        except Exception as e:
            logger.error(f"Topic routing test failed: {e}")
            return False
    
    async def test_delivery_confirmation_tracking(self) -> bool:
        """Test delivery confirmation tracking (Requirement 1.3)"""
        logger.info("Testing delivery confirmation tracking")
        
        try:
            # Create message with confirmation required
            message = self.create_test_message(
                AddressingMode.DIRECT,
                "test-mailbox-confirmation",
                confirmation_required=True
            )
            
            # Route message
            result = await self.message_router.route_message(message)
            
            if result == RoutingResult.REJECTED:
                logger.error("Message routing was rejected")
                return False
            
            # Check delivery confirmation was created
            confirmation = await self.message_router.get_delivery_status(message.id)
            if not confirmation:
                logger.error("Delivery confirmation was not created")
                return False
            
            if confirmation.message_id != message.id:
                logger.error("Delivery confirmation has wrong message ID")
                return False
            
            if confirmation.target != message.routing_info.target:
                logger.error("Delivery confirmation has wrong target")
                return False
            
            # Test confirmation handling
            await self.message_router.handle_delivery_confirmation(
                message.id, DeliveryStatus.DELIVERED, message.routing_info.target, latency_ms=25.5
            )
            
            # Verify confirmation was updated
            updated_confirmation = await self.message_router.get_delivery_status(message.id)
            if not updated_confirmation:
                logger.error("Delivery confirmation was lost after update")
                return False
            
            if updated_confirmation.status != DeliveryStatus.DELIVERED:
                logger.error("Delivery confirmation status was not updated")
                return False
            
            if len(updated_confirmation.attempts) == 0:
                logger.error("Delivery attempts were not recorded")
                return False
            
            if updated_confirmation.attempts[0].latency_ms != 25.5:
                logger.error("Delivery latency was not recorded correctly")
                return False
            
            logger.info("✓ Delivery confirmation tracking test passed")
            return True
            
        except Exception as e:
            logger.error(f"Delivery confirmation tracking test failed: {e}")
            return False
    
    async def test_retry_logic(self) -> bool:
        """Test retry logic with exponential backoff (Requirement 8.4)"""
        logger.info("Testing retry logic with exponential backoff")
        
        try:
            message_id = "test-retry-message"
            target = "test-retry-target"
            
            # Simulate failed delivery
            await self.message_router.handle_delivery_confirmation(
                message_id, DeliveryStatus.FAILED, target, error="Connection timeout"
            )
            
            confirmation = await self.message_router.get_delivery_status(message_id)
            if not confirmation:
                logger.error("Delivery confirmation was not created for retry test")
                return False
            
            # Verify retry was scheduled
            if confirmation.next_retry_at is None:
                logger.error("Retry was not scheduled")
                return False
            
            if confirmation.next_retry_at <= datetime.utcnow():
                logger.error("Retry was scheduled in the past")
                return False
            
            # Test multiple failures for exponential backoff
            first_retry_time = confirmation.next_retry_at
            
            # Simulate second failure
            await self.message_router.handle_delivery_confirmation(
                message_id, DeliveryStatus.FAILED, target, error="Second failure"
            )
            
            updated_confirmation = await self.message_router.get_delivery_status(message_id)
            second_retry_time = updated_confirmation.next_retry_at
            
            # Verify exponential backoff (second retry should be later)
            if second_retry_time <= first_retry_time:
                logger.error("Exponential backoff is not working correctly")
                return False
            
            # Test max retry attempts
            max_attempts = self.message_router.max_retry_attempts
            
            # Simulate failures up to max attempts
            for i in range(max_attempts):
                await self.message_router.handle_delivery_confirmation(
                    message_id, DeliveryStatus.FAILED, target, error=f"Failure {i+1}"
                )
            
            final_confirmation = await self.message_router.get_delivery_status(message_id)
            
            # Should not retry after max attempts
            if final_confirmation.should_retry(max_attempts):
                logger.error("Message should not retry after max attempts")
                return False
            
            logger.info("✓ Retry logic test passed")
            return True
            
        except Exception as e:
            logger.error(f"Retry logic test failed: {e}")
            return False
    
    async def test_message_validation(self) -> bool:
        """Test message validation"""
        logger.info("Testing message validation")
        
        try:
            # Test valid message
            valid_message = self.create_test_message(
                AddressingMode.DIRECT,
                "test-validation"
            )
            
            validation_result = await self.message_router.validate_message(valid_message)
            if not validation_result.is_valid:
                logger.error(f"Valid message failed validation: {validation_result.errors}")
                return False
            
            # Test invalid message - no target
            invalid_message = valid_message.clone()
            invalid_message.routing_info.target = ""
            
            validation_result = await self.message_router.validate_message(invalid_message)
            if validation_result.is_valid:
                logger.error("Invalid message (no target) passed validation")
                return False
            
            # Test invalid message - negative TTL
            invalid_ttl_message = valid_message.clone()
            invalid_ttl_message.routing_info.ttl = -1
            
            validation_result = await self.message_router.validate_message(invalid_ttl_message)
            if validation_result.is_valid:
                logger.error("Invalid message (negative TTL) passed validation")
                return False
            
            logger.info("✓ Message validation test passed")
            return True
            
        except Exception as e:
            logger.error(f"Message validation test failed: {e}")
            return False
    
    async def test_message_enrichment(self) -> bool:
        """Test message enrichment"""
        logger.info("Testing message enrichment")
        
        try:
            original_message = self.create_test_message(
                AddressingMode.DIRECT,
                "test-enrichment"
            )
            
            enriched_message = await self.message_router.enrich_message(original_message)
            
            # Verify enrichment
            if enriched_message.id != original_message.id:
                logger.error("Enriched message has different ID")
                return False
            
            if enriched_message is original_message:
                logger.error("Message was not cloned during enrichment")
                return False
            
            # Check system metadata
            routed_at = enriched_message.get_system_metadata('routed_at')
            if not routed_at:
                logger.error("Routing timestamp not added")
                return False
            
            router_version = enriched_message.get_system_metadata('router_version')
            if router_version != '1.0':
                logger.error("Router version not added correctly")
                return False
            
            routing_mode = enriched_message.get_system_metadata('routing_mode')
            if routing_mode != AddressingMode.DIRECT.value:
                logger.error("Routing mode not added correctly")
                return False
            
            logger.info("✓ Message enrichment test passed")
            return True
            
        except Exception as e:
            logger.error(f"Message enrichment test failed: {e}")
            return False
    
    async def test_ttl_expiration(self) -> bool:
        """Test TTL expiration handling"""
        logger.info("Testing TTL expiration handling")
        
        try:
            # Create message with short TTL
            message = self.create_test_message(
                AddressingMode.DIRECT,
                "test-ttl",
                ttl=1  # 1 second TTL
            )
            
            # Wait for expiration
            await asyncio.sleep(1.1)
            
            # Try to route expired message
            result = await self.message_router.route_message(message)
            
            if result != RoutingResult.REJECTED:
                logger.error(f"Expired message was not rejected: {result}")
                return False
            
            logger.info("✓ TTL expiration test passed")
            return True
            
        except Exception as e:
            logger.error(f"TTL expiration test failed: {e}")
            return False
    
    async def test_statistics_collection(self) -> bool:
        """Test statistics collection"""
        logger.info("Testing statistics collection")
        
        try:
            # Route some messages to generate statistics
            for i in range(5):
                message = self.create_test_message(
                    AddressingMode.DIRECT,
                    f"test-stats-{i}"
                )
                await self.message_router.route_message(message)
            
            # Get statistics
            stats = await self.message_router.get_statistics()
            
            # Verify statistics structure
            required_stats = [
                'messages_routed', 'messages_delivered', 'messages_failed',
                'messages_retried', 'routing_errors', 'validation_errors',
                'pending_deliveries', 'active_confirmations', 'running',
                'retry_config'
            ]
            
            for stat in required_stats:
                if stat not in stats:
                    logger.error(f"Missing statistic: {stat}")
                    return False
            
            # Verify some values
            if stats['messages_routed'] < 5:
                logger.error(f"Incorrect messages_routed count: {stats['messages_routed']}")
                return False
            
            if not stats['running']:
                logger.error("Router should be running")
                return False
            
            logger.info("✓ Statistics collection test passed")
            return True
            
        except Exception as e:
            logger.error(f"Statistics collection test failed: {e}")
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all validation tests"""
        logger.info("Starting Message Router validation tests")
        
        tests = [
            ("Message Validation", self.test_message_validation),
            ("Message Enrichment", self.test_message_enrichment),
            ("Direct Routing", self.test_direct_routing),
            ("Broadcast Routing", self.test_broadcast_routing),
            ("Topic Routing", self.test_topic_routing),
            ("Delivery Confirmation Tracking", self.test_delivery_confirmation_tracking),
            ("Retry Logic", self.test_retry_logic),
            ("TTL Expiration", self.test_ttl_expiration),
            ("Statistics Collection", self.test_statistics_collection),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} Test ---")
            try:
                if await test_func():
                    passed += 1
                    self.test_results.append((test_name, "PASSED", None))
                else:
                    failed += 1
                    self.test_results.append((test_name, "FAILED", "Test returned False"))
            except Exception as e:
                failed += 1
                self.test_results.append((test_name, "FAILED", str(e)))
                logger.error(f"{test_name} test failed with exception: {e}")
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info("MESSAGE ROUTER VALIDATION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total tests: {len(tests)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success rate: {(passed/len(tests)*100):.1f}%")
        
        logger.info(f"\nDetailed Results:")
        for test_name, status, error in self.test_results:
            status_symbol = "✓" if status == "PASSED" else "✗"
            logger.info(f"  {status_symbol} {test_name}: {status}")
            if error:
                logger.info(f"    Error: {error}")
        
        return failed == 0


async def main():
    """Main validation function"""
    validator = MessageRouterValidator()
    
    try:
        await validator.setup()
        success = await validator.run_all_tests()
        
        if success:
            logger.info("\n🎉 All Message Router validation tests passed!")
            return 0
        else:
            logger.error("\n❌ Some Message Router validation tests failed!")
            return 1
            
    except Exception as e:
        logger.error(f"Validation setup failed: {e}")
        return 1
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)