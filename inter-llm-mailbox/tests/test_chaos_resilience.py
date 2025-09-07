"""
Chaos Testing for Resilience Patterns

This module provides chaos testing scenarios to validate the resilience
of the Inter-LLM Mailbox System under various failure conditions.
"""

import pytest
import asyncio
import random
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.core.resilience_manager import ResilienceManager, LocalQueueConfig
from src.core.redis_manager import RedisConnectionManager, RedisConfig


class ChaosScenario:
    """Base class for chaos testing scenarios"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.results: Dict[str, Any] = {}
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the chaos scenario"""
        raise NotImplementedError
    
    def validate_results(self) -> bool:
        """Validate that the system behaved correctly during chaos"""
        raise NotImplementedError


class RedisOutageScenario(ChaosScenario):
    """Simulate Redis complete outage"""
    
    def __init__(self, outage_duration: float = 5.0):
        super().__init__(
            "Redis Complete Outage",
            f"Simulate Redis being completely unavailable for {outage_duration}s"
        )
        self.outage_duration = outage_duration
    
    async def execute(self) -> Dict[str, Any]:
        """Execute Redis outage scenario"""
        # Setup resilience manager
        circuit_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2
        )
        circuit_breaker = CircuitBreaker("chaos_redis", circuit_config)
        
        queue_config = LocalQueueConfig(max_queue_size=1000)
        resilience_manager = ResilienceManager(circuit_breaker, queue_config)
        
        await resilience_manager.start()
        
        try:
            # Phase 1: Normal operation
            async def redis_operation():
                return "success"
            
            # Verify normal operation
            for _ in range(5):
                result = await resilience_manager.execute_with_resilience(
                    "normal_op", redis_operation
                )
                assert result == "success"
            
            # Phase 2: Simulate Redis outage
            outage_start = time.time()
            
            async def failing_redis_operation():
                raise ConnectionError("Redis unavailable during outage")
            
            async def fallback_operation():
                return "fallback_success"
            
            # Operations during outage should use fallback
            fallback_count = 0
            for _ in range(10):
                result = await resilience_manager.execute_with_resilience(
                    "outage_op",
                    failing_redis_operation,
                    fallback_operation
                )
                if result == "fallback_success":
                    fallback_count += 1
            
            # Queue messages during outage
            queued_messages = []
            for i in range(20):
                message = {"id": f"msg_{i}", "content": f"Message {i}"}
                queued_messages.append(message)
                success = await resilience_manager.queue_message_locally(message)
                assert success is True
            
            # Wait for outage duration
            await asyncio.sleep(self.outage_duration)
            
            # Phase 3: Redis recovery
            async def recovered_redis_operation():
                return "redis_recovered"
            
            # Simulate gradual recovery
            recovery_attempts = 0
            for _ in range(5):
                try:
                    result = await resilience_manager.execute_with_resilience(
                        "recovery_op", recovered_redis_operation
                    )
                    if result == "redis_recovered":
                        recovery_attempts += 1
                        break
                except:
                    recovery_attempts += 1
                    await asyncio.sleep(0.5)
            
            # Process queued messages
            processed_messages = []
            
            async def process_message(message):
                processed_messages.append(message)
            
            processed_count = await resilience_manager.process_queued_messages(
                process_message, batch_size=50
            )
            
            outage_end = time.time()
            
            self.results = {
                "outage_duration": outage_end - outage_start,
                "fallback_operations": fallback_count,
                "messages_queued": len(queued_messages),
                "messages_processed": processed_count,
                "recovery_attempts": recovery_attempts,
                "final_service_state": resilience_manager.service_state.value,
                "circuit_breaker_stats": circuit_breaker.get_stats(),
                "resilience_stats": resilience_manager.get_stats()
            }
            
            return self.results
            
        finally:
            await resilience_manager.stop()
    
    def validate_results(self) -> bool:
        """Validate Redis outage scenario results"""
        if not self.results:
            return False
        
        # Check that fallback operations were used
        if self.results["fallback_operations"] < 5:
            return False
        
        # Check that messages were queued
        if self.results["messages_queued"] != 20:
            return False
        
        # Check that messages were processed after recovery
        if self.results["messages_processed"] != 20:
            return False
        
        # Check that system recovered
        if self.results["final_service_state"] not in ["healthy", "degraded"]:
            return False
        
        return True


class IntermittentFailuresScenario(ChaosScenario):
    """Simulate intermittent Redis failures"""
    
    def __init__(self, failure_rate: float = 0.3, duration: float = 10.0):
        super().__init__(
            "Intermittent Redis Failures",
            f"Simulate {failure_rate*100}% failure rate for {duration}s"
        )
        self.failure_rate = failure_rate
        self.duration = duration
    
    async def execute(self) -> Dict[str, Any]:
        """Execute intermittent failures scenario"""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=2.0,
            success_threshold=3
        )
        circuit_breaker = CircuitBreaker("chaos_intermittent", circuit_config)
        
        queue_config = LocalQueueConfig(max_queue_size=500)
        resilience_manager = ResilienceManager(circuit_breaker, queue_config)
        
        await resilience_manager.start()
        
        try:
            start_time = time.time()
            operation_count = 0
            success_count = 0
            failure_count = 0
            fallback_count = 0
            
            async def flaky_redis_operation():
                if random.random() < self.failure_rate:
                    raise ConnectionError("Intermittent failure")
                return "redis_success"
            
            async def fallback_operation():
                return "fallback_success"
            
            # Run operations for specified duration
            while time.time() - start_time < self.duration:
                operation_count += 1
                
                try:
                    result = await resilience_manager.execute_with_resilience(
                        "flaky_op",
                        flaky_redis_operation,
                        fallback_operation
                    )
                    
                    if result == "redis_success":
                        success_count += 1
                    elif result == "fallback_success":
                        fallback_count += 1
                        
                except Exception:
                    failure_count += 1
                
                # Small delay between operations
                await asyncio.sleep(0.1)
            
            end_time = time.time()
            
            self.results = {
                "duration": end_time - start_time,
                "total_operations": operation_count,
                "redis_successes": success_count,
                "fallback_uses": fallback_count,
                "total_failures": failure_count,
                "success_rate": (success_count + fallback_count) / operation_count if operation_count > 0 else 0,
                "circuit_breaker_stats": circuit_breaker.get_stats(),
                "resilience_stats": resilience_manager.get_stats()
            }
            
            return self.results
            
        finally:
            await resilience_manager.stop()
    
    def validate_results(self) -> bool:
        """Validate intermittent failures scenario results"""
        if not self.results:
            return False
        
        # Check that operations were attempted
        if self.results["total_operations"] < 50:
            return False
        
        # Check that success rate is reasonable (should be high due to fallbacks)
        if self.results["success_rate"] < 0.8:
            return False
        
        # Check that fallbacks were used
        if self.results["fallback_uses"] == 0:
            return False
        
        return True


class HighLoadScenario(ChaosScenario):
    """Simulate high load with concurrent operations"""
    
    def __init__(self, concurrent_operations: int = 100, operations_per_worker: int = 50):
        super().__init__(
            "High Load Concurrent Operations",
            f"Run {concurrent_operations} concurrent workers, {operations_per_worker} ops each"
        )
        self.concurrent_operations = concurrent_operations
        self.operations_per_worker = operations_per_worker
    
    async def execute(self) -> Dict[str, Any]:
        """Execute high load scenario"""
        circuit_config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=1.0,
            success_threshold=5
        )
        circuit_breaker = CircuitBreaker("chaos_load", circuit_config)
        
        queue_config = LocalQueueConfig(max_queue_size=5000)
        resilience_manager = ResilienceManager(circuit_breaker, queue_config)
        
        await resilience_manager.start()
        
        try:
            async def worker_task(worker_id: int) -> Dict[str, int]:
                """Individual worker task"""
                worker_stats = {
                    "operations": 0,
                    "successes": 0,
                    "failures": 0,
                    "fallbacks": 0
                }
                
                async def redis_operation():
                    # Simulate occasional failures under load
                    if random.random() < 0.1:  # 10% failure rate
                        raise ConnectionError(f"Load failure in worker {worker_id}")
                    await asyncio.sleep(0.01)  # Simulate work
                    return f"success_{worker_id}"
                
                async def fallback_operation():
                    return f"fallback_{worker_id}"
                
                for _ in range(self.operations_per_worker):
                    worker_stats["operations"] += 1
                    
                    try:
                        result = await resilience_manager.execute_with_resilience(
                            f"load_op_{worker_id}",
                            redis_operation,
                            fallback_operation
                        )
                        
                        if result.startswith("success"):
                            worker_stats["successes"] += 1
                        elif result.startswith("fallback"):
                            worker_stats["fallbacks"] += 1
                            
                    except Exception:
                        worker_stats["failures"] += 1
                
                return worker_stats
            
            # Start all workers concurrently
            start_time = time.time()
            
            tasks = [
                worker_task(i) for i in range(self.concurrent_operations)
            ]
            
            worker_results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            
            # Aggregate results
            total_operations = sum(w["operations"] for w in worker_results)
            total_successes = sum(w["successes"] for w in worker_results)
            total_fallbacks = sum(w["fallbacks"] for w in worker_results)
            total_failures = sum(w["failures"] for w in worker_results)
            
            self.results = {
                "duration": end_time - start_time,
                "concurrent_workers": self.concurrent_operations,
                "operations_per_worker": self.operations_per_worker,
                "total_operations": total_operations,
                "total_successes": total_successes,
                "total_fallbacks": total_fallbacks,
                "total_failures": total_failures,
                "operations_per_second": total_operations / (end_time - start_time),
                "success_rate": (total_successes + total_fallbacks) / total_operations if total_operations > 0 else 0,
                "circuit_breaker_stats": circuit_breaker.get_stats(),
                "resilience_stats": resilience_manager.get_stats()
            }
            
            return self.results
            
        finally:
            await resilience_manager.stop()
    
    def validate_results(self) -> bool:
        """Validate high load scenario results"""
        if not self.results:
            return False
        
        # Check that all operations were attempted
        expected_operations = self.concurrent_operations * self.operations_per_worker
        if self.results["total_operations"] != expected_operations:
            return False
        
        # Check that success rate is reasonable
        if self.results["success_rate"] < 0.85:
            return False
        
        # Check that throughput is reasonable
        if self.results["operations_per_second"] < 100:
            return False
        
        return True


class CascadingFailuresScenario(ChaosScenario):
    """Simulate cascading failures across multiple components"""
    
    def __init__(self):
        super().__init__(
            "Cascading Failures",
            "Simulate failures that cascade across multiple system components"
        )
    
    async def execute(self) -> Dict[str, Any]:
        """Execute cascading failures scenario"""
        # Create multiple circuit breakers for different components
        redis_circuit = CircuitBreaker("redis", CircuitBreakerConfig(failure_threshold=3))
        pubsub_circuit = CircuitBreaker("pubsub", CircuitBreakerConfig(failure_threshold=2))
        storage_circuit = CircuitBreaker("storage", CircuitBreakerConfig(failure_threshold=4))
        
        queue_config = LocalQueueConfig(max_queue_size=1000)
        resilience_manager = ResilienceManager(redis_circuit, queue_config)
        
        await resilience_manager.start()
        
        try:
            failure_sequence = []
            
            # Phase 1: Redis starts failing
            async def failing_redis():
                raise ConnectionError("Redis cascade failure")
            
            for _ in range(5):
                try:
                    await redis_circuit.call(failing_redis)
                except:
                    pass
            
            failure_sequence.append({
                "component": "redis",
                "state": redis_circuit.stats.state.value,
                "time": time.time()
            })
            
            # Phase 2: PubSub fails due to Redis dependency
            async def failing_pubsub():
                if redis_circuit.is_open:
                    raise ConnectionError("PubSub depends on Redis")
                return "pubsub_success"
            
            for _ in range(3):
                try:
                    await pubsub_circuit.call(failing_pubsub)
                except:
                    pass
            
            failure_sequence.append({
                "component": "pubsub",
                "state": pubsub_circuit.stats.state.value,
                "time": time.time()
            })
            
            # Phase 3: Storage overwhelmed by fallback traffic
            storage_load = 0
            
            async def overloaded_storage():
                nonlocal storage_load
                storage_load += 1
                if storage_load > 10:  # Simulate overload
                    raise ConnectionError("Storage overloaded")
                return "storage_success"
            
            for _ in range(15):
                try:
                    await storage_circuit.call(overloaded_storage)
                except:
                    pass
            
            failure_sequence.append({
                "component": "storage",
                "state": storage_circuit.stats.state.value,
                "time": time.time()
            })
            
            # Phase 4: Gradual recovery
            await asyncio.sleep(2.0)  # Wait for recovery timeouts
            
            # Redis recovers first
            async def recovered_redis():
                return "redis_recovered"
            
            await redis_circuit.call(recovered_redis)
            
            # PubSub can now recover
            recovery_result = await pubsub_circuit.call(failing_pubsub)
            
            # Storage load decreases
            storage_load = 0
            await storage_circuit.call(overloaded_storage)
            
            self.results = {
                "failure_sequence": failure_sequence,
                "redis_final_state": redis_circuit.stats.state.value,
                "pubsub_final_state": pubsub_circuit.stats.state.value,
                "storage_final_state": storage_circuit.stats.state.value,
                "recovery_successful": (
                    redis_circuit.is_closed and 
                    pubsub_circuit.is_closed and 
                    storage_circuit.is_closed
                ),
                "resilience_stats": resilience_manager.get_stats()
            }
            
            return self.results
            
        finally:
            await resilience_manager.stop()
    
    def validate_results(self) -> bool:
        """Validate cascading failures scenario results"""
        if not self.results:
            return False
        
        # Check that failures cascaded in sequence
        if len(self.results["failure_sequence"]) != 3:
            return False
        
        # Check that all components eventually recovered
        if not self.results["recovery_successful"]:
            return False
        
        return True


class TestChaosResilience:
    """Test suite for chaos resilience scenarios"""
    
    @pytest.mark.asyncio
    async def test_redis_outage_scenario(self):
        """Test Redis complete outage scenario"""
        scenario = RedisOutageScenario(outage_duration=2.0)
        
        results = await scenario.execute()
        
        assert scenario.validate_results()
        assert results["fallback_operations"] > 0
        assert results["messages_queued"] > 0
        assert results["messages_processed"] > 0
    
    @pytest.mark.asyncio
    async def test_intermittent_failures_scenario(self):
        """Test intermittent failures scenario"""
        scenario = IntermittentFailuresScenario(
            failure_rate=0.2, 
            duration=3.0
        )
        
        results = await scenario.execute()
        
        assert scenario.validate_results()
        assert results["success_rate"] > 0.8
        assert results["fallback_uses"] > 0
    
    @pytest.mark.asyncio
    async def test_high_load_scenario(self):
        """Test high load scenario"""
        scenario = HighLoadScenario(
            concurrent_operations=20,
            operations_per_worker=25
        )
        
        results = await scenario.execute()
        
        assert scenario.validate_results()
        assert results["total_operations"] == 500
        assert results["success_rate"] > 0.85
        assert results["operations_per_second"] > 50
    
    @pytest.mark.asyncio
    async def test_cascading_failures_scenario(self):
        """Test cascading failures scenario"""
        scenario = CascadingFailuresScenario()
        
        results = await scenario.execute()
        
        assert scenario.validate_results()
        assert len(results["failure_sequence"]) == 3
        assert results["recovery_successful"] is True
    
    @pytest.mark.asyncio
    async def test_multiple_scenarios_sequence(self):
        """Test running multiple chaos scenarios in sequence"""
        scenarios = [
            RedisOutageScenario(outage_duration=1.0),
            IntermittentFailuresScenario(failure_rate=0.15, duration=2.0),
            HighLoadScenario(concurrent_operations=10, operations_per_worker=20)
        ]
        
        all_results = []
        
        for scenario in scenarios:
            results = await scenario.execute()
            all_results.append({
                "scenario": scenario.name,
                "results": results,
                "validation_passed": scenario.validate_results()
            })
        
        # All scenarios should pass validation
        for result in all_results:
            assert result["validation_passed"] is True
        
        # Check that we have results from all scenarios
        assert len(all_results) == 3


class TestResilienceMetrics:
    """Test resilience metrics and monitoring"""
    
    @pytest.mark.asyncio
    async def test_resilience_metrics_collection(self):
        """Test that resilience metrics are properly collected"""
        circuit_config = CircuitBreakerConfig(failure_threshold=2)
        circuit_breaker = CircuitBreaker("metrics_test", circuit_config)
        
        queue_config = LocalQueueConfig(max_queue_size=100)
        resilience_manager = ResilienceManager(circuit_breaker, queue_config)
        
        await resilience_manager.start()
        
        try:
            # Generate some activity
            async def success_op():
                return "success"
            
            async def fail_op():
                raise ConnectionError("test failure")
            
            async def fallback_op():
                return "fallback"
            
            # Successful operations
            for _ in range(5):
                await resilience_manager.execute_with_resilience(
                    "success", success_op
                )
            
            # Failed operations with fallback
            for _ in range(3):
                await resilience_manager.execute_with_resilience(
                    "fail", fail_op, fallback_op
                )
            
            # Queue some messages
            for i in range(10):
                await resilience_manager.queue_message_locally(
                    {"id": i, "content": f"message {i}"}
                )
            
            # Get comprehensive stats
            stats = resilience_manager.get_stats()
            
            # Validate stats structure
            assert "redis_calls_total" in stats
            assert "redis_calls_failed" in stats
            assert "messages_queued_locally" in stats
            assert "service_state" in stats
            assert "circuit_breaker" in stats
            assert "local_queue" in stats
            
            # Validate stats values
            assert stats["redis_calls_total"] == 8
            assert stats["redis_calls_failed"] == 3
            assert stats["messages_queued_locally"] == 10
            
            # Circuit breaker stats
            cb_stats = stats["circuit_breaker"]
            assert cb_stats["total_requests"] >= 3
            assert cb_stats["total_failures"] >= 3
            
            # Queue stats
            queue_stats = stats["local_queue"]
            assert queue_stats["total_queued"] == 10
            assert queue_stats["current_size"] == 10
            
        finally:
            await resilience_manager.stop()


if __name__ == "__main__":
    pytest.main([__file__])