"""
Unit tests for Redis Connection Manager

Tests Redis connection management, health checks, and reconnection logic
as specified in requirements 8.1, 8.4, 6.2.
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from redis.exceptions import ConnectionError, TimeoutError

from src.core.redis_manager import RedisConnectionManager, RedisConfig, ConnectionState


@pytest.fixture
def redis_config():
    """Test Redis configuration"""
    return RedisConfig(
        host="localhost",
        port=6379,
        max_connections=5,
        health_check_interval=0.1,  # Fast for testing
        max_reconnect_attempts=3,
        reconnect_backoff_base=0.1,
        reconnect_backoff_max=1.0
    )


@pytest.fixture
async def redis_manager(redis_config):
    """Redis manager fixture"""
    manager = RedisConnectionManager(redis_config)
    yield manager
    await manager.close()


class TestRedisConnectionManager:
    """Test Redis connection manager functionality"""
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, redis_manager):
        """Test successful Redis connection initialization"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            # Mock successful connection
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            # Initialize
            await redis_manager.initialize()
            
            # Verify state
            assert redis_manager.connection_state == ConnectionState.CONNECTED
            assert redis_manager.is_connected
            
            # Verify pool creation
            mock_pool_class.assert_called_once()
            mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self, redis_manager):
        """Test Redis connection initialization failure"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class:
            mock_pool_class.side_effect = ConnectionError("Connection failed")
            
            # Should raise exception
            with pytest.raises(ConnectionError):
                await redis_manager.initialize()
            
            # Verify state
            assert redis_manager.connection_state == ConnectionState.FAILED
            assert not redis_manager.is_connected
    
    @pytest.mark.asyncio
    async def test_get_connection_success(self, redis_manager):
        """Test getting Redis connection successfully"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Test getting connection
            async with redis_manager.get_connection() as conn:
                assert conn is mock_redis
    
    @pytest.mark.asyncio
    async def test_get_connection_with_reconnection(self, redis_manager):
        """Test getting connection triggers reconnection when needed"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            # Set state to disconnected
            redis_manager._state = ConnectionState.DISCONNECTED
            
            # Should initialize automatically
            async with redis_manager.get_connection() as conn:
                assert conn is mock_redis
                assert redis_manager.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, redis_manager):
        """Test connection error handling during operations"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Simulate connection error during operation
            with pytest.raises(ConnectionError):
                async with redis_manager.get_connection() as conn:
                    raise ConnectionError("Connection lost")
            
            # State should be set to reconnecting
            assert redis_manager.connection_state == ConnectionState.RECONNECTING
    
    @pytest.mark.asyncio
    async def test_reconnection_logic(self, redis_manager):
        """Test Redis reconnection with exponential backoff"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            
            # First attempt fails, second succeeds
            ping_calls = [AsyncMock(side_effect=ConnectionError("Failed")), 
                         AsyncMock(return_value=True)]
            mock_redis.ping = AsyncMock(side_effect=lambda: ping_calls.pop(0)())
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            # Set state to trigger reconnection
            redis_manager._state = ConnectionState.RECONNECTING
            
            # Should reconnect successfully
            await redis_manager._reconnect()
            
            # Verify reconnection attempts
            assert redis_manager.connection_state == ConnectionState.CONNECTED
            assert redis_manager._reconnect_attempts == 0
            
            # Verify backoff sleep was called
            mock_sleep.assert_called()
    
    @pytest.mark.asyncio
    async def test_max_reconnection_attempts(self, redis_manager):
        """Test maximum reconnection attempts limit"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=ConnectionError("Always fails"))
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            redis_manager._state = ConnectionState.RECONNECTING
            
            # Should fail after max attempts
            with pytest.raises(ConnectionError, match="Unable to reconnect"):
                await redis_manager._reconnect()
            
            # Verify state and attempts
            assert redis_manager.connection_state == ConnectionState.FAILED
            assert redis_manager._reconnect_attempts == redis_manager.config.max_reconnect_attempts
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, redis_manager):
        """Test successful health check"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Perform health check
            await redis_manager._perform_health_check()
            
            # Verify health check was performed
            assert redis_manager.last_health_check > 0
            assert redis_manager.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, redis_manager):
        """Test health check failure handling"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=[True, ConnectionError("Health check failed")])
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Health check should fail and trigger reconnection state
            await redis_manager._perform_health_check()
            
            assert redis_manager.connection_state == ConnectionState.RECONNECTING
    
    @pytest.mark.asyncio
    async def test_connection_info(self, redis_manager):
        """Test getting connection information"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_pool.created_connections = 3
            mock_pool._available_connections = [1, 2]
            mock_pool._in_use_connections = [3]
            
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Get connection info
            info = await redis_manager.get_connection_info()
            
            # Verify info structure
            assert info["state"] == "connected"
            assert info["host"] == redis_manager.config.host
            assert info["port"] == redis_manager.config.port
            assert info["pool_created_connections"] == 3
            assert info["pool_available_connections"] == 2
            assert info["pool_in_use_connections"] == 1
    
    @pytest.mark.asyncio
    async def test_close_cleanup(self, redis_manager):
        """Test proper cleanup on close"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.close = AsyncMock()
            mock_pool.disconnect = AsyncMock()
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Close should cleanup everything
            await redis_manager.close()
            
            # Verify cleanup
            mock_redis.close.assert_called_once()
            mock_pool.disconnect.assert_called_once()
            assert redis_manager.connection_state == ConnectionState.DISCONNECTED
            assert not redis_manager.is_connected
    
    @pytest.mark.asyncio
    async def test_concurrent_initialization(self, redis_manager):
        """Test concurrent initialization attempts"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            # Start multiple initialization tasks
            tasks = [redis_manager.initialize() for _ in range(3)]
            await asyncio.gather(*tasks)
            
            # Should only initialize once
            assert mock_pool_class.call_count == 1
            assert redis_manager.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_health_check_loop_cancellation(self, redis_manager):
        """Test health check loop proper cancellation"""
        with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
             patch('redis.asyncio.Redis') as mock_redis_class:
            
            mock_pool = AsyncMock()
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            
            mock_pool_class.return_value = mock_pool
            mock_redis_class.return_value = mock_redis
            
            await redis_manager.initialize()
            
            # Health check task should be running
            assert redis_manager._health_check_task is not None
            assert not redis_manager._health_check_task.done()
            
            # Close should cancel the task
            await redis_manager.close()
            
            # Task should be cancelled
            assert redis_manager._health_check_task.cancelled()


if __name__ == "__main__":
    pytest.main([__file__])