#!/usr/bin/env python3
"""
Validation script for Topic Manager functionality
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, 'src')

from src.core.topic_manager import TopicManager, TopicConfig
from src.core.subscription_manager import SubscriptionManager
from src.core.redis_manager import RedisConnectionManager, RedisConfig
from src.core.redis_pubsub import RedisPubSubManager
from src.models.subscription import SubscriptionOptions
from src.models.enums import DeliveryMode, AddressingMode


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopicValidationTest:
    """Comprehensive validation test for topic functionality"""
    
    def __init__(self):
        self.redis_manager = None
        self.pubsub_manager = None
        self.subscription_manager = None
        self.topic_manager = None
        self.test_results = []
    
    async def setup(self):
        """Set up test environment"""
        logger.info("Setting up test environment...")
        
        # Configure Redis connection
        redis_config = RedisConfig(
            host='localhost',
            port=6379,
            db=15,  # Use test database
            decode_responses=True
        )
        
        # Initialize managers
        self.redis_manager = RedisConnectionManager(redis_config)
        await self.redis_manager.start()
        
        self.pubsub_manager = RedisPubSubManager(self.redis_manager)
        await self.pubsub_manager.start()
        
        self.subscription_manager = SubscriptionManager(
            self.redis_manager, 
            self.pubsub_manager
        )
        await self.subscription_manager.start()
        
        self.topic_manager = TopicManager(
            self.redis_manager,
            self.subscription_manager
        )
        await self.topic_manager.start()
        
        logger.info("Test environment setup complete")
    
    async def cleanup(self):
        """Clean up test environment"""
        logger.info("Cleaning up test environment...")
        
        if self.topic_manager:
            await self.topic_manager.stop()
        
        if self.subscription_manager:
            await self.subscription_manager.stop()
        
        if self.pubsub_manager:
            await self.pubsub_manager.stop()
        
        if self.redis_manager:
            # Clean up test data
            async with self.redis_manager.get_connection() as redis_conn:
                await redis_conn.flushdb()
            await self.redis_manager.stop()
        
        logger.info("Cleanup complete")
    
    def record_test(self, test_name: str, success: bool, details: str = ""):
        """Record test result"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        status = "PASS" if success else "FAIL"
        logger.info(f"Test {test_name}: {status} - {details}")
    
    async def test_basic_topic_operations(self):
        """Test basic topic creation, retrieval, and deletion"""
        try:
            # Test topic creation
            config = TopicConfig(
                name="test.basic.operations",
                description="Basic operations test topic",
                max_subscribers=100
            )
            
            topic = await self.topic_manager.create_topic(config)
            assert topic.config.name == "test.basic.operations"
            assert topic.config.description == "Basic operations test topic"
            assert topic.active is True
            
            self.record_test("basic_topic_creation", True, f"Created topic {topic.id}")
            
            # Test topic retrieval
            retrieved_topic = await self.topic_manager.get_topic("test.basic.operations")
            assert retrieved_topic is not None
            assert retrieved_topic.id == topic.id
            
            self.record_test("basic_topic_retrieval", True, "Retrieved topic successfully")
            
            # Test topic deletion
            success = await self.topic_manager.delete_topic("test.basic.operations")
            assert success is True
            
            deleted_topic = await self.topic_manager.get_topic("test.basic.operations")
            assert deleted_topic is None
            
            self.record_test("basic_topic_deletion", True, "Deleted topic successfully")
            
        except Exception as e:
            self.record_test("basic_topic_operations", False, f"Error: {str(e)}")
    
    async def test_hierarchical_topics(self):
        """Test hierarchical topic functionality"""
        try:
            # Create hierarchical topic
            config = TopicConfig(name="ai.ml.deep_learning.cnn")
            topic = await self.topic_manager.create_topic(config)
            
            assert topic.is_hierarchical is True
            assert topic.hierarchy_parts == ["ai", "ml", "deep_learning", "cnn"]
            assert topic.parent_topics == ["ai", "ai.ml", "ai.ml.deep_learning"]
            
            self.record_test("hierarchical_topic_creation", True, "Created hierarchical topic")
            
            # Check that parent topics were auto-created
            ai_topic = await self.topic_manager.get_topic("ai")
            assert ai_topic is not None
            assert "Auto-created parent topic" in ai_topic.config.description
            
            ml_topic = await self.topic_manager.get_topic("ai.ml")
            assert ml_topic is not None
            
            self.record_test("parent_topic_auto_creation", True, "Parent topics auto-created")
            
            # Test hierarchy structure
            hierarchy = await self.topic_manager.get_topic_hierarchy("ai")
            assert "topic" in hierarchy
            assert hierarchy["topic"]["config"]["name"] == "ai"
            assert "children" in hierarchy
            
            self.record_test("topic_hierarchy_structure", True, "Hierarchy structure correct")
            
            # Clean up
            await self.topic_manager.delete_topic("ai", force=True)
            
        except Exception as e:
            self.record_test("hierarchical_topics", False, f"Error: {str(e)}")
    
    async def test_topic_subscriptions(self):
        """Test topic subscription functionality"""
        try:
            # Create topic
            config = TopicConfig(name="test.subscriptions")
            topic = await self.topic_manager.create_topic(config)
            
            # Subscribe to topic
            subscription = await self.topic_manager.subscribe_to_topic(
                llm_id="test-llm-1",
                topic_name="test.subscriptions",
                options=SubscriptionOptions(delivery_mode=DeliveryMode.REALTIME)
            )
            
            assert subscription.target == "test.subscriptions"
            assert subscription.llm_id == "test-llm-1"
            
            self.record_test("topic_subscription", True, f"Created subscription {subscription.id}")
            
            # Check topic subscriber count
            updated_topic = await self.topic_manager.get_topic("test.subscriptions")
            assert updated_topic.subscriber_count == 1
            
            self.record_test("subscriber_count_tracking", True, "Subscriber count updated")
            
            # Test hierarchical subscription with children
            hierarchical_config = TopicConfig(name="events.user")
            hierarchical_topic = await self.topic_manager.create_topic(hierarchical_config)
            
            hierarchical_sub = await self.topic_manager.subscribe_to_topic(
                llm_id="test-llm-2",
                topic_name="events.user",
                include_children=True
            )
            
            assert hierarchical_sub.pattern == "events.user.*"
            
            self.record_test("hierarchical_subscription", True, "Hierarchical subscription with pattern")
            
            # Test unsubscription
            unsub_success = await self.topic_manager.unsubscribe_from_topic(subscription.id)
            assert unsub_success is True
            
            self.record_test("topic_unsubscription", True, "Unsubscribed successfully")
            
            # Clean up
            await self.topic_manager.delete_topic("test.subscriptions", force=True)
            await self.topic_manager.delete_topic("events", force=True)
            
        except Exception as e:
            self.record_test("topic_subscriptions", False, f"Error: {str(e)}")
    
    async def test_message_publishing(self):
        """Test message publishing to topics"""
        try:
            # Create topic
            config = TopicConfig(name="test.publishing")
            topic = await self.topic_manager.create_topic(config)
            
            # Subscribe to topic
            subscription = await self.topic_manager.subscribe_to_topic(
                llm_id="test-llm-publisher",
                topic_name="test.publishing"
            )
            
            # Publish message
            message = {
                "id": "msg-123",
                "content": "Test message for publishing",
                "sender_id": "test-sender",
                "timestamp": datetime.utcnow().isoformat(),
                "routing_info": {
                    "addressing_mode": "direct",
                    "target": "test.publishing"
                }
            }
            
            subscriber_count = await self.topic_manager.publish_to_topic("test.publishing", message)
            
            self.record_test("message_publishing", True, f"Published to {subscriber_count} subscribers")
            
            # Check that message count was updated
            updated_topic = await self.topic_manager.get_topic("test.publishing")
            assert updated_topic.message_count == 1
            
            self.record_test("message_count_tracking", True, "Message count updated")
            
            # Verify routing info was updated
            # Note: In a real scenario, we'd check the delivered message
            # For this test, we just verify the topic state
            
            # Clean up
            await self.topic_manager.delete_topic("test.publishing", force=True)
            
        except Exception as e:
            self.record_test("message_publishing", False, f"Error: {str(e)}")
    
    async def test_topic_listing_and_filtering(self):
        """Test topic listing and filtering functionality"""
        try:
            # Create multiple topics
            topics_to_create = [
                TopicConfig(name="ai.ml.supervised"),
                TopicConfig(name="ai.ml.unsupervised"),
                TopicConfig(name="ai.nlp.tokenization"),
                TopicConfig(name="web.frontend.react"),
                TopicConfig(name="web.backend.nodejs")
            ]
            
            created_topics = []
            for config in topics_to_create:
                topic = await self.topic_manager.create_topic(config)
                created_topics.append(topic)
            
            self.record_test("multiple_topic_creation", True, f"Created {len(created_topics)} topics")
            
            # List all topics
            all_topics = await self.topic_manager.list_topics()
            topic_names = [t.config.name for t in all_topics]
            
            for config in topics_to_create:
                assert config.name in topic_names
            
            self.record_test("list_all_topics", True, f"Listed {len(all_topics)} topics")
            
            # List with pattern filter
            ai_topics = await self.topic_manager.list_topics(pattern="ai.*")
            ai_topic_names = [t.config.name for t in ai_topics]
            
            assert "ai.ml.supervised" in ai_topic_names
            assert "ai.nlp.tokenization" in ai_topic_names
            assert "web.frontend.react" not in ai_topic_names
            
            self.record_test("pattern_filtering", True, f"Filtered to {len(ai_topics)} AI topics")
            
            # Test hierarchy listing
            hierarchy = await self.topic_manager.get_topic_hierarchy()
            assert "ai" in hierarchy
            assert "web" in hierarchy
            
            self.record_test("hierarchy_listing", True, "Generated hierarchy structure")
            
            # Clean up
            for config in topics_to_create:
                await self.topic_manager.delete_topic(config.name, force=True)
            
            # Clean up auto-created parents
            await self.topic_manager.delete_topic("ai", force=True)
            await self.topic_manager.delete_topic("web", force=True)
            
        except Exception as e:
            self.record_test("topic_listing_and_filtering", False, f"Error: {str(e)}")
    
    async def test_topic_permissions_and_limits(self):
        """Test topic permissions and subscriber limits"""
        try:
            # Create topic with low subscriber limit
            config = TopicConfig(
                name="test.limits",
                max_subscribers=2
            )
            topic = await self.topic_manager.create_topic(config)
            
            # Subscribe first LLM
            sub1 = await self.topic_manager.subscribe_to_topic("llm-1", "test.limits")
            assert sub1 is not None
            
            # Subscribe second LLM
            sub2 = await self.topic_manager.subscribe_to_topic("llm-2", "test.limits")
            assert sub2 is not None
            
            self.record_test("subscriber_limit_normal", True, "Subscribed within limits")
            
            # Try to subscribe third LLM (should fail)
            try:
                await self.topic_manager.subscribe_to_topic("llm-3", "test.limits")
                self.record_test("subscriber_limit_exceeded", False, "Should have failed")
            except ValueError as e:
                if "maximum subscribers" in str(e):
                    self.record_test("subscriber_limit_exceeded", True, "Correctly rejected excess subscriber")
                else:
                    self.record_test("subscriber_limit_exceeded", False, f"Wrong error: {e}")
            
            # Clean up
            await self.topic_manager.delete_topic("test.limits", force=True)
            
        except Exception as e:
            self.record_test("topic_permissions_and_limits", False, f"Error: {str(e)}")
    
    async def test_topic_statistics(self):
        """Test topic statistics functionality"""
        try:
            # Create topics with different activity levels
            configs = [
                TopicConfig(name="stats.topic.1"),
                TopicConfig(name="stats.topic.2"),
                TopicConfig(name="stats.topic.3")
            ]
            
            topics = []
            for config in configs:
                topic = await self.topic_manager.create_topic(config)
                topics.append(topic)
            
            # Add some activity
            for i, topic in enumerate(topics):
                # Add subscribers
                for j in range(i + 1):
                    await self.topic_manager.subscribe_to_topic(f"llm-{i}-{j}", topic.config.name)
                
                # Publish messages
                for k in range((i + 1) * 5):
                    message = {
                        "content": f"Message {k}",
                        "routing_info": {"addressing_mode": "topic", "target": topic.config.name}
                    }
                    await self.topic_manager.publish_to_topic(topic.config.name, message)
            
            # Get statistics
            stats = await self.topic_manager.get_statistics()
            
            assert stats["total_topics"] == 3
            assert stats["active_topics"] == 3
            assert stats["total_subscribers"] == 6  # 1 + 2 + 3
            assert stats["total_messages"] == 30  # 5 + 10 + 15
            assert stats["running"] is True
            
            self.record_test("topic_statistics", True, f"Stats: {stats}")
            
            # Clean up
            for topic in topics:
                await self.topic_manager.delete_topic(topic.config.name, force=True)
            
        except Exception as e:
            self.record_test("topic_statistics", False, f"Error: {str(e)}")
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        try:
            # Test operations on nonexistent topics
            try:
                await self.topic_manager.subscribe_to_topic("llm-1", "nonexistent.topic")
                self.record_test("nonexistent_topic_subscription", False, "Should have failed")
            except ValueError:
                self.record_test("nonexistent_topic_subscription", True, "Correctly rejected")
            
            try:
                await self.topic_manager.publish_to_topic("nonexistent.topic", {"content": "test"})
                self.record_test("nonexistent_topic_publishing", False, "Should have failed")
            except ValueError:
                self.record_test("nonexistent_topic_publishing", True, "Correctly rejected")
            
            # Test invalid topic configurations
            try:
                invalid_config = TopicConfig(name="")
                await self.topic_manager.create_topic(invalid_config)
                self.record_test("invalid_topic_config", False, "Should have failed")
            except ValueError:
                self.record_test("invalid_topic_config", True, "Correctly rejected empty name")
            
            try:
                invalid_config = TopicConfig(name="invalid@topic")
                await self.topic_manager.create_topic(invalid_config)
                self.record_test("invalid_topic_characters", False, "Should have failed")
            except ValueError:
                self.record_test("invalid_topic_characters", True, "Correctly rejected invalid characters")
            
        except Exception as e:
            self.record_test("error_handling", False, f"Unexpected error: {str(e)}")
    
    async def run_all_tests(self):
        """Run all validation tests"""
        logger.info("Starting topic manager validation tests...")
        
        try:
            await self.setup()
            
            # Run individual test suites
            await self.test_basic_topic_operations()
            await self.test_hierarchical_topics()
            await self.test_topic_subscriptions()
            await self.test_message_publishing()
            await self.test_topic_listing_and_filtering()
            await self.test_topic_permissions_and_limits()
            await self.test_topic_statistics()
            await self.test_error_handling()
            
        finally:
            await self.cleanup()
        
        # Print results summary
        self.print_results_summary()
    
    def print_results_summary(self):
        """Print test results summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*60)
        print("TOPIC MANAGER VALIDATION RESULTS")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("="*60)
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\nDETAILED RESULTS:")
        for result in self.test_results:
            status = "PASS" if result['success'] else "FAIL"
            print(f"  [{status}] {result['test']}: {result['details']}")
        
        return failed_tests == 0


async def main():
    """Main validation function"""
    validator = TopicValidationTest()
    success = await validator.run_all_tests()
    
    if success:
        logger.info("All topic manager validation tests passed!")
        sys.exit(0)
    else:
        logger.error("Some topic manager validation tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())