"""
Tests for Circuit Breaker functionality
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from src.core.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, 
    CircuitBreakerOpenException, CircuitBreakerManager
)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig class"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 3
        assert config.timeout == 30.0
        assert config.expected_exceptions == (Exception,)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=15.0,
            expected_exceptions=(ValueError, ConnectionError)
        )
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.success_threshold == 2
        assert config.timeout == 15.0
        assert config.expected_exceptions == (ValueError, ConnectionError)
    
    def test_invalid_config(self):
        """Test invalid configuration values"""
        with pytest.raises(ValueError, match="failure_threshold must be positive"):
            CircuitBreakerConfig(failure_threshold=0)
        
        with pytest.raises(ValueError, match="recovery_timeout must be positive"):
            CircuitBreakerConfig(recovery_timeout=0)
        
        with pytest.raises(ValueError, match="success_threshold must be positive"):
            CircuitBreakerConfig(success_threshold=0)


class TestCircuitBreaker:
    """Test CircuitBreaker class"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,  # Short timeout for testing
            success_threshold=2,
            timeout=1.0
        )
        return CircuitBreaker("test_breaker", config)
    
    @pytest.mark.asyncio
    async def test_successful_calls(self, circuit_breaker):
        """Test successful function calls"""
        async def success_func():
            return "success"
        
        # Multiple successful calls
        for i in range(5):
            result = await circuit_breaker.call(success_func)
            assert result == "success"
        
        # Circuit should remain closed
        assert circuit_breaker.is_closed
        assert circuit_breaker.stats.total_successes == 5
        assert circuit_breaker.stats.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_failure_threshold(self, circuit_breaker):
        """Test circuit opening on failure threshold"""
        async def failing_func():
            raise ValueError("Test failure")
        
        # First few failures should not open circuit
        for i in range(2):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)
            assert circuit_breaker.is_closed
        
        # Third failure should open circuit
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.is_open
        assert circuit_breaker.stats.failure_count == 3
        assert circuit_breaker.stats.total_failures == 3
    
    @pytest.mark.asyncio
    async def test_circuit_open_rejection(self, circuit_breaker):
        """Test that open circuit rejects calls"""
        async def failing_func():
            raise ValueError("Test failure")
        
        # Trigger circuit opening
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.is_open
        
        # Next call should be rejected immediately
        async def any_func():
            return "should not execute"
        
        with pytest.raises(CircuitBreakerOpenException):
            await circuit_breaker.call(any_func)
    
    @pytest.mark.asyncio
    async def test_recovery_timeout(self, circuit_breaker):
        """Test circuit recovery after timeout"""
        async def failing_func():
            raise ValueError("Test failure")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.is_open
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to half-open
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_half_open
    
    @pytest.mark.asyncio
    async def test_half_open_to_closed(self, circuit_breaker):
        """Test transition from half-open to closed"""
        async def failing_func():
            raise ValueError("Test failure")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Successful calls in half-open state
        for i in range(2):  # success_threshold = 2
            result = await circuit_breaker.call(success_func)
            assert result == "success"
        
        # Circuit should now be closed
        assert circuit_breaker.is_closed
        assert circuit_breaker.stats.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_to_open(self, circuit_breaker):
        """Test transition from half-open back to open on failure"""
        async def failing_func():
            raise ValueError("Test failure")
        
        async def success_func():
            return "success"
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(ValueError):
                await circuit_breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # One successful call (half-open)
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_half_open
        
        # Failure should open circuit again
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_func)
        
        assert circuit_breaker.is_open
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, circuit_breaker):
        """Test function timeout handling"""
        async def slow_func():
            await asyncio.sleep(2.0)  # Longer than timeout
            return "too slow"
        
        # Should timeout and count as failure
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_func)
        
        assert circuit_breaker.stats.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_non_async_function(self, circuit_breaker):
        """Test calling non-async functions"""
        def sync_func(x, y):
            return x + y
        
        result = await circuit_breaker.call(sync_func, 2, 3)
        assert result == 5
        
        def failing_sync_func():
            raise ValueError("Sync failure")
        
        with pytest.raises(ValueError):
            await circuit_breaker.call(failing_sync_func)
        
        assert circuit_breaker.stats.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_expected_exceptions_filter(self, circuit_breaker):
        """Test that only expected exceptions count as failures"""
        # Configure to only count ValueError as failure
        circuit_breaker.config.expected_exceptions = (ValueError,)
        
        async def value_error_func():
            raise ValueError("Expected failure")
        
        async def type_error_func():
            raise TypeError("Unexpected failure")
        
        # ValueError should count as failure
        with pytest.raises(ValueError):
            await circuit_breaker.call(value_error_func)
        assert circuit_breaker.stats.failure_count == 1
        
        # TypeError should not count as failure
        with pytest.raises(TypeError):
            await circuit_breaker.call(type_error_func)
        assert circuit_breaker.stats.failure_count == 1  # Still 1
    
    @pytest.mark.asyncio
    async def test_manual_control(self, circuit_breaker):
        """Test manual circuit control"""
        # Force open
        await circuit_breaker.force_open("Manual test")
        assert circuit_breaker.is_open
        
        # Force close
        await circuit_breaker.force_close("Manual test")
        assert circuit_breaker.is_closed
        
        # Reset
        circuit_breaker.stats.failure_count = 5
        await circuit_breaker.reset()
        assert circuit_breaker.stats.failure_count == 0
        assert circuit_breaker.is_closed
    
    def test_statistics(self, circuit_breaker):
        """Test statistics collection"""
        # Set some test data
        circuit_breaker.stats.total_requests = 10
        circuit_breaker.stats.total_failures = 3
        circuit_breaker.stats.total_successes = 7
        
        stats = circuit_breaker.get_stats()
        
        assert stats['name'] == 'test_breaker'
        assert stats['state'] == 'closed'
        assert stats['total_requests'] == 10
        assert stats['total_failures'] == 3
        assert stats['total_successes'] == 7
        assert stats['failure_rate'] == 0.3
        assert 'config' in stats
        assert 'recent_state_changes' in stats
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_concurrent_calls(self, circuit_breaker):
        """Test concurrent function calls"""
        async def success_func(delay=0.01):  # Shorter delay
            await asyncio.sleep(delay)
            return "success"
        
        # Execute multiple concurrent calls
        tasks = [circuit_breaker.call(success_func) for _ in range(5)]  # Fewer tasks
        results = await asyncio.gather(*tasks)
        
        assert all(result == "success" for result in results)
        assert circuit_breaker.stats.total_successes == 5
        assert circuit_breaker.is_closed


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager class"""
    
    @pytest.fixture
    def manager(self):
        """Create circuit breaker manager for testing"""
        return CircuitBreakerManager()
    
    @pytest.mark.asyncio
    async def test_get_breaker_default_config(self, manager):
        """Test getting breaker with default config"""
        breaker = await manager.get_breaker("test_breaker")
        
        assert breaker.name == "test_breaker"
        assert breaker.config.failure_threshold == 5  # Default value
        assert "test_breaker" in manager.list_breakers()
    
    @pytest.mark.asyncio
    async def test_get_breaker_custom_config(self, manager):
        """Test getting breaker with custom config"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = await manager.get_breaker("custom_breaker", config)
        
        assert breaker.name == "custom_breaker"
        assert breaker.config.failure_threshold == 3
    
    @pytest.mark.asyncio
    async def test_get_existing_breaker(self, manager):
        """Test getting existing breaker returns same instance"""
        breaker1 = await manager.get_breaker("same_breaker")
        breaker2 = await manager.get_breaker("same_breaker")
        
        assert breaker1 is breaker2
    
    @pytest.mark.asyncio
    async def test_remove_breaker(self, manager):
        """Test removing circuit breaker"""
        await manager.get_breaker("removable_breaker")
        assert "removable_breaker" in manager.list_breakers()
        
        success = await manager.remove_breaker("removable_breaker")
        assert success is True
        assert "removable_breaker" not in manager.list_breakers()
        
        # Try to remove non-existent breaker
        success = await manager.remove_breaker("non_existent")
        assert success is False
    
    @pytest.mark.asyncio
    async def test_list_breakers(self, manager):
        """Test listing circuit breakers"""
        assert manager.list_breakers() == []
        
        await manager.get_breaker("breaker1")
        await manager.get_breaker("breaker2")
        
        breakers = manager.list_breakers()
        assert "breaker1" in breakers
        assert "breaker2" in breakers
        assert len(breakers) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_stats(self, manager):
        """Test getting statistics for all breakers"""
        await manager.get_breaker("breaker1")
        await manager.get_breaker("breaker2")
        
        all_stats = manager.get_all_stats()
        
        assert "breaker1" in all_stats
        assert "breaker2" in all_stats
        assert all_stats["breaker1"]["name"] == "breaker1"
        assert all_stats["breaker2"]["name"] == "breaker2"
    
    @pytest.mark.asyncio
    async def test_reset_all(self, manager):
        """Test resetting all circuit breakers"""
        breaker1 = await manager.get_breaker("breaker1")
        breaker2 = await manager.get_breaker("breaker2")
        
        # Set some test data
        breaker1.stats.failure_count = 5
        breaker2.stats.failure_count = 3
        
        await manager.reset_all()
        
        assert breaker1.stats.failure_count == 0
        assert breaker2.stats.failure_count == 0


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_realistic_failure_scenario(self):
        """Test realistic failure and recovery scenario"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=0.5,
            success_threshold=2,
            timeout=1.0
        )
        breaker = CircuitBreaker("integration_test", config)
        
        # Simulate service that fails then recovers
        call_count = 0
        
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 5:  # First 5 calls fail
                raise ConnectionError("Service unavailable")
            else:  # Subsequent calls succeed
                return f"success_{call_count}"
        
        # Phase 1: Initial failures (circuit should open)
        for i in range(3):
            with pytest.raises(ConnectionError):
                await breaker.call(flaky_service)
        
        assert breaker.is_open
        
        # Phase 2: Circuit open (calls rejected)
        with pytest.raises(CircuitBreakerOpenException):
            await breaker.call(flaky_service)
        
        # Phase 3: Wait for recovery timeout
        await asyncio.sleep(0.6)
        
        # Phase 4: Half-open state (service still failing)
        with pytest.raises(ConnectionError):
            await breaker.call(flaky_service)
        
        assert breaker.is_open  # Should go back to open
        
        # Phase 5: Wait again and service recovers
        await asyncio.sleep(0.6)
        
        # Phase 6: Successful recovery (service should now work)
        call_count = 5  # Reset to ensure service works
        result1 = await breaker.call(flaky_service)
        assert result1.startswith("success_")
        assert breaker.is_half_open
        
        result2 = await breaker.call(flaky_service)
        assert result2.startswith("success_")
        assert breaker.is_closed  # Should close after success threshold
        
        # Phase 7: Normal operation
        result3 = await breaker.call(flaky_service)
        assert result3 == "success_8"
        assert breaker.is_closed
        
        # Verify statistics
        stats = breaker.get_stats()
        assert stats['total_requests'] == 8
        assert stats['total_failures'] == 4
        assert stats['total_successes'] == 3
        assert len(stats['recent_state_changes']) > 0


if __name__ == "__main__":
    pytest.main([__file__])