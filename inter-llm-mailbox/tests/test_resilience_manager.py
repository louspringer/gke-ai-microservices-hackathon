"""
Tests for Resilience Manager functionality
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.resilience_manager import (
    ResilienceManager, LocalMessageQueue, LocalQueueConfig, 
    QueuedMessage, ServiceState
)
from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenException


class TestLocalQueueConfig:
    """Test LocalQueueConfig class"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = LocalQueueConfig()
        
        assert config.max_queue_size == 10000
        assert config.max_message_age_hours == 24
        assert config.persistence_enabled is True
        assert config.persistence_file is None
        assert config.flush_interval_seconds == 60
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = LocalQueueConfig(
            max_queue_size=5000,
            max_message_age_hours=12,
            persistence_enabled=False,
            persistence_file="/tmp/test_queue.json",
            flush_interval_seconds=30
        )
        
        assert config.max_queue_size == 5000
        assert config.max_message_age_hours == 12
        assert config.persistence_enabled is False
        assert config.persistence_file == "/tmp/test_queue.json"
        assert config.flush_interval_seconds == 30
    
    def test_invalid_config(self):
        """Test invalid configuration values"""
        with pytest.raises(ValueError, match="max_queue_size must be positive"):
            LocalQueueConfig(max_queue_size=0)
        
        with pytest.raises(ValueError, match="max_message_age_hours must be positive"):
            LocalQueueConfig(max_message_age_hours=0)


class TestQueuedMessage:
    """Test QueuedMessage class"""
    
    def test_message_creation(self):
        """Test creating a queued message"""
        message_data = {"content": "test message", "id": "msg-123"}
        queued_msg = QueuedMessage(message=message_data)
        
        assert queued_msg.message == message_data
        assert queued_msg.retry_count == 0
        assert queued_msg.max_retries == 3
        assert queued_msg.age_seconds >= 0
        assert not queued_msg.is_expired
        assert queued_msg.can_retry()
    
    def test_retry_logic(self):
        """Test retry logic"""
        message_data = {"content": "test"}
        queued_msg = QueuedMessage(message=message_data, max_retries=2)
        
        # Initial state
        assert queued_msg.can_retry()
        
        # First retry
        queued_msg.increment_retry()
        assert queued_msg.retry_count == 1
        assert queued_msg.can_retry()
        
        # Second retry
        queued_msg.increment_retry()
        assert queued_msg.retry_count == 2
        assert not queued_msg.can_retry()  # Exceeded max retries
    
    def test_expiration(self):
        """Test message expiration"""
        import time
        
        message_data = {"content": "test"}
        queued_msg = QueuedMessage(message=message_data)
        
        # Simulate old message
        queued_msg.queued_at = time.time() - (25 * 3600)  # 25 hours ago
        
        assert queued_msg.is_expired
        assert not queued_msg.can_retry()  # Expired messages can't retry


class TestLocalMessageQueue:
    """Test LocalMessageQueue class"""
    
    @pytest.fixture
    async def queue(self):
        """Create local message queue for testing"""
        config = LocalQueueConfig(
            max_queue_size=100,
            flush_interval_seconds=1  # Fast for testing
        )
        queue = LocalMessageQueue(config)
        await queue.start()
        yield queue
        await queue.stop()
    
    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue):
        """Test basic enqueue and dequeue operations"""
        message1 = {"content": "message 1", "id": "msg-1"}
        message2 = {"content": "message 2", "id": "msg-2"}
        
        # Enqueue messages
        success1 = await queue.enqueue(message1)
        success2 = await queue.enqueue(message2)
        
        assert success1 is True
        assert success2 is True
        assert queue.stats['current_size'] == 2
        
        # Dequeue messages
        batch = await queue.dequeue_batch(10)
        
        assert len(batch) == 2
        assert batch[0].message == message1
        assert batch[1].message == message2
        assert queue.stats['current_size'] == 0
    
    @pytest.mark.asyncio
    async def test_queue_size_limit(self, queue):
        """Test queue size limit enforcement"""
        # Fill queue to capacity
        for i in range(100):
            message = {"content": f"message {i}", "id": f"msg-{i}"}
            success = await queue.enqueue(message)
            assert success is True
        
        # Try to add one more (should fail)
        overflow_message = {"content": "overflow", "id": "overflow"}
        success = await queue.enqueue(overflow_message)
        assert success is False
        assert queue.stats['current_size'] == 100
    
    @pytest.mark.asyncio
    async def test_requeue_functionality(self, queue):
        """Test message requeuing"""
        message = {"content": "test message", "id": "msg-1"}
        
        # Enqueue and dequeue
        await queue.enqueue(message)
        batch = await queue.dequeue_batch(1)
        queued_msg = batch[0]
        
        assert queue.stats['current_size'] == 0
        
        # Requeue the message
        await queue.requeue(queued_msg)
        
        assert queue.stats['current_size'] == 1
        assert queued_msg.retry_count == 1
        
        # Dequeue again (should be at front of queue)
        batch = await queue.dequeue_batch(1)
        requeued_msg = batch[0]
        
        assert requeued_msg.message == message
        assert requeued_msg.retry_count == 1
    
    @pytest.mark.asyncio
    async def test_expired_message_cleanup(self, queue):
        """Test cleanup of expired messages"""
        import time
        
        # Add normal message
        normal_message = {"content": "normal", "id": "normal"}
        await queue.enqueue(normal_message)
        
        # Add expired message by manipulating queue directly
        expired_message = QueuedMessage(
            message={"content": "expired", "id": "expired"},
            queued_at=time.time() - (25 * 3600)  # 25 hours ago
        )
        queue._queue.appendleft(expired_message)  # Add to front
        
        assert len(queue._queue) == 2
        
        # Dequeue should clean up expired message
        batch = await queue.dequeue_batch(10)
        
        assert len(batch) == 1  # Only normal message
        assert batch[0].message == normal_message
        assert queue.stats['total_expired'] == 1
    
    @pytest.mark.asyncio
    async def test_batch_dequeue_limit(self, queue):
        """Test batch dequeue size limit"""
        # Add multiple messages
        for i in range(10):
            message = {"content": f"message {i}", "id": f"msg-{i}"}
            await queue.enqueue(message)
        
        # Dequeue with smaller batch size
        batch = await queue.dequeue_batch(5)
        
        assert len(batch) == 5
        assert queue.stats['current_size'] == 5
    
    @pytest.mark.asyncio
    async def test_statistics(self, queue):
        """Test queue statistics"""
        # Add and process some messages
        for i in range(3):
            message = {"content": f"message {i}", "id": f"msg-{i}"}
            await queue.enqueue(message)
        
        stats = queue.get_stats()
        
        assert stats['total_queued'] == 3
        assert stats['current_size'] == 3
        assert stats['total_flushed'] == 0
        assert stats['total_expired'] == 0
        assert 'config' in stats
    
    @pytest.mark.asyncio
    async def test_persistence_disabled(self):
        """Test queue with persistence disabled"""
        config = LocalQueueConfig(persistence_enabled=False)
        queue = LocalMessageQueue(config)
        
        await queue.start()
        
        # Add message
        message = {"content": "test", "id": "test"}
        await queue.enqueue(message)
        
        # Stop should not try to persist
        await queue.stop()
        
        # No persistence file should be created
        assert config.persistence_file is None
    
    @pytest.mark.asyncio
    async def test_persistence_enabled(self):
        """Test queue with persistence enabled"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            persistence_file = tmp_file.name
        
        try:
            config = LocalQueueConfig(
                persistence_enabled=True,
                persistence_file=persistence_file
            )
            queue = LocalMessageQueue(config)
            
            await queue.start()
            
            # Add messages
            messages = [
                {"content": "message 1", "id": "msg-1"},
                {"content": "message 2", "id": "msg-2"}
            ]
            
            for message in messages:
                await queue.enqueue(message)
            
            # Stop should persist messages
            await queue.stop()
            
            # Check persistence file exists and has content
            assert os.path.exists(persistence_file)
            
            with open(persistence_file, 'r') as f:
                persisted_data = json.load(f)
            
            assert len(persisted_data) == 2
            assert persisted_data[0]['message'] == messages[0]
            assert persisted_data[1]['message'] == messages[1]
            
        finally:
            if os.path.exists(persistence_file):
                os.unlink(persistence_file)


class TestResilienceManager:
    """Test ResilienceManager class"""
    
    @pytest.fixture
    async def circuit_breaker(self):
        """Create circuit breaker for testing"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.5,
            success_threshold=1
        )
        return CircuitBreaker("test_redis", config)
    
    @pytest.fixture
    async def resilience_manager(self, circuit_breaker):
        """Create resilience manager for testing"""
        queue_config = LocalQueueConfig(max_queue_size=100)
        manager = ResilienceManager(circuit_breaker, queue_config)
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_successful_redis_operation(self, resilience_manager):
        """Test successful Redis operation execution"""
        async def redis_operation():
            return "redis_success"
        
        result = await resilience_manager.execute_with_resilience(
            "test_operation",
            redis_operation
        )
        
        assert result == "redis_success"
        assert resilience_manager.service_state == ServiceState.HEALTHY
        assert resilience_manager.stats['redis_calls_total'] == 1
        assert resilience_manager.stats['redis_calls_failed'] == 0
    
    @pytest.mark.asyncio
    async def test_redis_failure_with_fallback(self, resilience_manager):
        """Test Redis failure with successful fallback"""
        async def failing_redis_operation():
            raise ConnectionError("Redis unavailable")
        
        async def fallback_operation():
            return "fallback_success"
        
        result = await resilience_manager.execute_with_resilience(
            "test_operation",
            failing_redis_operation,
            fallback_operation
        )
        
        assert result == "fallback_success"
        assert resilience_manager.service_state == ServiceState.DEGRADED
        assert resilience_manager.stats['redis_calls_failed'] == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_open(self, resilience_manager):
        """Test behavior when circuit breaker is open"""
        async def failing_redis_operation():
            raise ConnectionError("Redis unavailable")
        
        async def fallback_operation():
            return "fallback_success"
        
        # Trigger circuit breaker opening
        for _ in range(2):  # failure_threshold = 2
            try:
                await resilience_manager.execute_with_resilience(
                    "test_operation",
                    failing_redis_operation,
                    fallback_operation
                )
            except:
                pass
        
        # Circuit should be open now
        assert resilience_manager.redis_circuit_breaker.is_open
        
        # Next call should use fallback immediately
        result = await resilience_manager.execute_with_resilience(
            "test_operation",
            failing_redis_operation,
            fallback_operation
        )
        
        assert result == "fallback_success"
        assert resilience_manager.stats['redis_calls_circuit_open'] >= 1
    
    @pytest.mark.asyncio
    async def test_no_fallback_available(self, resilience_manager):
        """Test behavior when no fallback is available"""
        async def failing_redis_operation():
            raise ConnectionError("Redis unavailable")
        
        # Should propagate the original exception
        with pytest.raises(ConnectionError):
            await resilience_manager.execute_with_resilience(
                "test_operation",
                failing_redis_operation
            )
        
        assert resilience_manager.service_state == ServiceState.DEGRADED
    
    @pytest.mark.asyncio
    async def test_local_message_queuing(self, resilience_manager):
        """Test local message queuing functionality"""
        message = {"content": "test message", "id": "msg-1"}
        
        success = await resilience_manager.queue_message_locally(message)
        
        assert success is True
        assert resilience_manager.stats['messages_queued_locally'] == 1
        
        # Check queue statistics
        queue_stats = resilience_manager.local_queue.get_stats()
        assert queue_stats['current_size'] == 1
    
    @pytest.mark.asyncio
    async def test_process_queued_messages(self, resilience_manager):
        """Test processing messages from local queue"""
        # Queue some messages
        messages = [
            {"content": "message 1", "id": "msg-1"},
            {"content": "message 2", "id": "msg-2"}
        ]
        
        for message in messages:
            await resilience_manager.queue_message_locally(message)
        
        # Mock Redis operation
        processed_messages = []
        
        async def mock_redis_operation(message):
            processed_messages.append(message)
        
        # Process queued messages
        count = await resilience_manager.process_queued_messages(
            mock_redis_operation,
            batch_size=10
        )
        
        assert count == 2
        assert len(processed_messages) == 2
        assert resilience_manager.stats['messages_processed_from_queue'] == 2
    
    @pytest.mark.asyncio
    async def test_process_queued_messages_circuit_open(self, resilience_manager):
        """Test that queued messages are not processed when circuit is open"""
        # Open the circuit
        await resilience_manager.redis_circuit_breaker.force_open("Test")
        
        # Queue a message
        message = {"content": "test", "id": "test"}
        await resilience_manager.queue_message_locally(message)
        
        async def mock_redis_operation(message):
            pass
        
        # Should not process messages when circuit is open
        count = await resilience_manager.process_queued_messages(mock_redis_operation)
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_fallback_handler_registration(self, resilience_manager):
        """Test fallback handler registration and retrieval"""
        async def custom_fallback():
            return "custom_fallback_result"
        
        # Register fallback handler
        resilience_manager.register_fallback_handler("custom_operation", custom_fallback)
        
        # Retrieve handler
        handler = resilience_manager.get_fallback_handler("custom_operation")
        assert handler is custom_fallback
        
        # Non-existent handler
        handler = resilience_manager.get_fallback_handler("non_existent")
        assert handler is None
    
    @pytest.mark.asyncio
    async def test_service_state_transitions(self, resilience_manager):
        """Test service state transitions"""
        # Start healthy
        assert resilience_manager.is_healthy
        
        # Simulate failure
        async def failing_operation():
            raise ConnectionError("Test failure")
        
        try:
            await resilience_manager.execute_with_resilience(
                "test_operation",
                failing_operation
            )
        except:
            pass
        
        # Should transition to degraded
        assert resilience_manager.is_degraded
        
        # Simulate recovery
        async def success_operation():
            return "success"
        
        await resilience_manager.execute_with_resilience(
            "test_operation",
            success_operation
        )
        
        # Should transition back to healthy
        assert resilience_manager.is_healthy
    
    @pytest.mark.asyncio
    async def test_statistics_collection(self, resilience_manager):
        """Test comprehensive statistics collection"""
        # Perform various operations
        async def success_operation():
            return "success"
        
        async def failing_operation():
            raise ConnectionError("failure")
        
        # Successful operation
        await resilience_manager.execute_with_resilience(
            "success_op",
            success_operation
        )
        
        # Failed operation
        try:
            await resilience_manager.execute_with_resilience(
                "fail_op",
                failing_operation
            )
        except:
            pass
        
        # Queue a message
        await resilience_manager.queue_message_locally({"test": "message"})
        
        # Get statistics
        stats = resilience_manager.get_stats()
        
        assert stats['redis_calls_total'] == 2
        assert stats['redis_calls_failed'] == 1
        assert stats['messages_queued_locally'] == 1
        assert stats['service_state'] == 'degraded'
        assert 'circuit_breaker' in stats
        assert 'local_queue' in stats
        assert stats['degradation_duration_seconds'] is not None
    
    @pytest.mark.asyncio
    async def test_health_monitoring(self, resilience_manager):
        """Test health monitoring functionality"""
        # Force degraded state
        resilience_manager._service_state = ServiceState.DEGRADED
        
        # Close circuit breaker (simulate recovery)
        await resilience_manager.redis_circuit_breaker.force_close("Test recovery")
        
        # Wait for health monitor to detect recovery
        await asyncio.sleep(0.1)  # Short wait for test
        
        # Health monitor should detect closed circuit and attempt recovery
        # (In real implementation, this would happen in the background loop)
        assert resilience_manager.redis_circuit_breaker.is_closed


class TestResilienceIntegration:
    """Integration tests for resilience functionality"""
    
    @pytest.mark.asyncio
    async def test_complete_failure_recovery_cycle(self):
        """Test complete failure and recovery cycle"""
        # Setup
        circuit_config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.2,
            success_threshold=1
        )
        circuit_breaker = CircuitBreaker("integration_test", circuit_config)
        
        queue_config = LocalQueueConfig(max_queue_size=100)
        resilience_manager = ResilienceManager(circuit_breaker, queue_config)
        
        await resilience_manager.start()
        
        try:
            # Phase 1: Normal operation
            async def redis_operation():
                return "redis_success"
            
            result = await resilience_manager.execute_with_resilience(
                "normal_op",
                redis_operation
            )
            assert result == "redis_success"
            assert resilience_manager.is_healthy
            
            # Phase 2: Service starts failing
            call_count = 0
            
            async def flaky_redis_operation():
                nonlocal call_count
                call_count += 1
                if call_count <= 3:
                    raise ConnectionError("Redis down")
                return "redis_recovered"
            
            async def fallback_operation():
                return "fallback_used"
            
            # First failures (should use fallback)
            for _ in range(2):
                result = await resilience_manager.execute_with_resilience(
                    "flaky_op",
                    flaky_redis_operation,
                    fallback_operation
                )
                assert result == "fallback_used"
            
            assert resilience_manager.is_degraded
            assert circuit_breaker.is_open
            
            # Phase 3: Circuit open (immediate fallback)
            result = await resilience_manager.execute_with_resilience(
                "circuit_open_op",
                flaky_redis_operation,
                fallback_operation
            )
            assert result == "fallback_used"
            
            # Phase 4: Wait for recovery timeout
            await asyncio.sleep(0.3)
            
            # Phase 5: Service recovery
            result = await resilience_manager.execute_with_resilience(
                "recovery_op",
                flaky_redis_operation
            )
            assert result == "redis_recovered"
            assert resilience_manager.is_healthy
            assert circuit_breaker.is_closed
            
            # Verify statistics
            stats = resilience_manager.get_stats()
            assert stats['redis_calls_total'] >= 5
            assert stats['redis_calls_failed'] >= 2
            assert stats['degradation_events'] >= 1
            
        finally:
            await resilience_manager.stop()
    
    @pytest.mark.asyncio
    async def test_message_queuing_during_outage(self):
        """Test message queuing and processing during Redis outage"""
        circuit_config = CircuitBreakerConfig(failure_threshold=1)
        circuit_breaker = CircuitBreaker("queue_test", circuit_config)
        
        queue_config = LocalQueueConfig(max_queue_size=10)
        resilience_manager = ResilienceManager(circuit_breaker, queue_config)
        
        await resilience_manager.start()
        
        try:
            # Simulate Redis outage
            await circuit_breaker.force_open("Simulated outage")
            
            # Queue messages during outage
            messages = []
            for i in range(5):
                message = {"content": f"message {i}", "id": f"msg-{i}"}
                messages.append(message)
                success = await resilience_manager.queue_message_locally(message)
                assert success is True
            
            # Verify messages are queued
            queue_stats = resilience_manager.local_queue.get_stats()
            assert queue_stats['current_size'] == 5
            
            # Simulate Redis recovery
            await circuit_breaker.force_close("Simulated recovery")
            
            # Process queued messages
            processed_messages = []
            
            async def mock_redis_send(message):
                processed_messages.append(message)
            
            count = await resilience_manager.process_queued_messages(mock_redis_send)
            
            assert count == 5
            assert len(processed_messages) == 5
            
            # Verify all messages were processed
            for i, message in enumerate(processed_messages):
                assert message["content"] == f"message {i}"
            
        finally:
            await resilience_manager.stop()


if __name__ == "__main__":
    pytest.main([__file__])