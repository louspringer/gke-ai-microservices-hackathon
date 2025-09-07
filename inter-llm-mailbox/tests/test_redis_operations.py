"""
Unit tests for Redis Operations

Tests the unified Redis operations interface including basic operations,
pub/sub, and health monitoring.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.core.redis_operations import RedisOperations
from src.core.redis_manager import RedisConfig, ConnectionState


@pytest.fixture
def redis_config():
    """Test Redis configuration"""
    return RedisConfig(
        host="localhost",
        port=6379,
        max_connections=5,
        health_check_interval=0.1
    )


@pytest.fixture
async def redis_ops(redis_config):
    """Redis operations fixture"""
    ops = RedisOperations(redis_config)
    yield ops
    await ops.close()


class TestRedisOperations:
    """Test unified Redis operations interface"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, redis_ops):
        """Test Redis operations initialization"""
        with patch.object(redis_ops.connection_manager, 'initialize') as mock_conn_init, \
             patch.object(redis_ops.pubsub_manager, 'start') as mock_pubsub_start:
            
            await redis_ops.initialize()
            
            assert redis_ops.is_initialized
            mock_conn_init.assert_called_once()
            mock_pubsub_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, redis_ops):
        """Test Redis operations cleanup"""
        with patch.object(redis_ops.connection_manager, 'initialize'), \
             patch.object(redis_ops.pubsub_manager, 'start'), \
             patch.object(redis_ops.connection_manager, 'close') as mock_conn_close, \
             patch.object(redis_ops.pubsub_manager, 'stop') as mock_pubsub_stop:
            
            await redis_ops.initialize()
            await redis_ops.close()
            
            assert not redis_ops.is_initialized
            mock_conn_close.assert_called_once()
            mock_pubsub_stop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_get_operations(self, redis_ops):
        """Test basic set/get operations"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value='{"key": "value"}')
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            # Test set operation
            result = await redis_ops.set("test_key", {"key": "value"}, ex=60)
            assert result is True
            mock_redis.set.assert_called_once_with("test_key", '{"key": "value"}', ex=60)
            
            # Test get operation
            result = await redis_ops.get("test_key")
            assert result == {"key": "value"}
            mock_redis.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_set_get_string_values(self, redis_ops):
        """Test set/get operations with string values"""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value="string_value")
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            # Test set with string
            result = await redis_ops.set("test_key", "string_value")
            assert result is True
            mock_redis.set.assert_called_once_with("test_key", "string_value", ex=None)
            
            # Test get with no deserialization
            result = await redis_ops.get("test_key", deserialize=False)
            assert result == "string_value"
    
    @pytest.mark.asyncio
    async def test_delete_operations(self, redis_ops):
        """Test delete operations"""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=2)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            result = await redis_ops.delete("key1", "key2")
            assert result == 2
            mock_redis.delete.assert_called_once_with("key1", "key2")
    
    @pytest.mark.asyncio
    async def test_exists_operations(self, redis_ops):
        """Test exists operations"""
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            result = await redis_ops.exists("test_key")
            assert result == 1
            mock_redis.exists.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_expire_operations(self, redis_ops):
        """Test expire operations"""
        mock_redis = AsyncMock()
        mock_redis.expire = AsyncMock(return_value=True)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            result = await redis_ops.expire("test_key", 300)
            assert result is True
            mock_redis.expire.assert_called_once_with("test_key", 300)
    
    @pytest.mark.asyncio
    async def test_hash_operations(self, redis_ops):
        """Test Redis hash operations"""
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock(return_value=2)
        mock_redis.hget = AsyncMock(return_value='{"nested": "value"}')
        mock_redis.hgetall = AsyncMock(return_value={"field1": "value1", "field2": '{"nested": "value"}'})
        mock_redis.hdel = AsyncMock(return_value=1)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            # Test hset
            mapping = {"field1": "value1", "field2": {"nested": "value"}}
            result = await redis_ops.hset("test_hash", mapping)
            assert result == 2
            
            # Test hget
            result = await redis_ops.hget("test_hash", "field2")
            assert result == {"nested": "value"}
            
            # Test hgetall
            result = await redis_ops.hgetall("test_hash")
            assert result["field1"] == "value1"
            assert result["field2"] == {"nested": "value"}
            
            # Test hdel
            result = await redis_ops.hdel("test_hash", "field1")
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_sorted_set_operations(self, redis_ops):
        """Test Redis sorted set operations"""
        mock_redis = AsyncMock()
        mock_redis.zadd = AsyncMock(return_value=2)
        mock_redis.zrange = AsyncMock(return_value=["member1", "member2"])
        mock_redis.zrem = AsyncMock(return_value=1)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            # Test zadd
            mapping = {"member1": 1.0, "member2": 2.0}
            result = await redis_ops.zadd("test_zset", mapping)
            assert result == 2
            
            # Test zrange
            result = await redis_ops.zrange("test_zset", 0, -1)
            assert result == ["member1", "member2"]
            
            # Test zrem
            result = await redis_ops.zrem("test_zset", "member1")
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_set_operations(self, redis_ops):
        """Test Redis set operations"""
        mock_redis = AsyncMock()
        mock_redis.sadd = AsyncMock(return_value=2)
        mock_redis.smembers = AsyncMock(return_value={"member1", "member2"})
        mock_redis.srem = AsyncMock(return_value=1)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            # Test sadd
            result = await redis_ops.sadd("test_set", "member1", "member2")
            assert result == 2
            
            # Test smembers
            result = await redis_ops.smembers("test_set")
            assert result == {"member1", "member2"}
            
            # Test srem
            result = await redis_ops.srem("test_set", "member1")
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_pubsub_operations(self, redis_ops):
        """Test pub/sub operations delegation"""
        with patch.object(redis_ops.pubsub_manager, 'publish') as mock_publish, \
             patch.object(redis_ops.pubsub_manager, 'subscribe_channel') as mock_sub_channel, \
             patch.object(redis_ops.pubsub_manager, 'subscribe_pattern') as mock_sub_pattern, \
             patch.object(redis_ops.pubsub_manager, 'unsubscribe_channel') as mock_unsub_channel, \
             patch.object(redis_ops.pubsub_manager, 'unsubscribe_pattern') as mock_unsub_pattern:
            
            mock_publish.return_value = 1
            
            # Test publish
            message = {"type": "test"}
            result = await redis_ops.publish("test_channel", message)
            assert result == 1
            mock_publish.assert_called_once_with("test_channel", message)
            
            # Test subscribe channel
            handler = AsyncMock()
            await redis_ops.subscribe_channel("test_channel", handler)
            mock_sub_channel.assert_called_once_with("test_channel", handler)
            
            # Test subscribe pattern
            await redis_ops.subscribe_pattern("test_*", handler)
            mock_sub_pattern.assert_called_once_with("test_*", handler)
            
            # Test unsubscribe channel
            await redis_ops.unsubscribe_channel("test_channel")
            mock_unsub_channel.assert_called_once_with("test_channel")
            
            # Test unsubscribe pattern
            await redis_ops.unsubscribe_pattern("test_*")
            mock_unsub_pattern.assert_called_once_with("test_*")
    
    @pytest.mark.asyncio
    async def test_ping_operation(self, redis_ops):
        """Test Redis ping operation"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            result = await redis_ops.ping()
            assert result is True
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ping_failure(self, redis_ops):
        """Test Redis ping failure handling"""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            result = await redis_ops.ping()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_info_operation(self, redis_ops):
        """Test Redis info operation"""
        mock_redis = AsyncMock()
        mock_info = {"redis_version": "6.2.0", "connected_clients": "1"}
        mock_redis.info = AsyncMock(return_value=mock_info)
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            result = await redis_ops.info("server")
            assert result == mock_info
            mock_redis.info.assert_called_once_with("server")
    
    @pytest.mark.asyncio
    async def test_health_status(self, redis_ops):
        """Test getting comprehensive health status"""
        # Mock connection manager
        connection_info = {
            "state": "connected",
            "host": "localhost",
            "port": 6379,
            "reconnect_attempts": 0
        }
        
        # Mock pubsub manager
        pubsub_info = {
            "running": True,
            "subscriptions": {"test_channel": "channel"},
            "handlers_count": 1
        }
        
        # Mock server info
        server_info = {"redis_version": "6.2.0"}
        
        with patch.object(redis_ops.connection_manager, 'get_connection_info') as mock_conn_info, \
             patch.object(redis_ops.pubsub_manager, 'get_subscription_info') as mock_pubsub_info, \
             patch.object(redis_ops, 'ping') as mock_ping, \
             patch.object(redis_ops, 'info') as mock_info:
            
            mock_conn_info.return_value = connection_info
            mock_pubsub_info.return_value = pubsub_info
            mock_ping.return_value = True
            mock_info.return_value = server_info
            
            health_status = await redis_ops.get_health_status()
            
            assert health_status["overall_healthy"] is True
            assert health_status["connection"] == connection_info
            assert health_status["pubsub"] == pubsub_info
            assert health_status["server"] == server_info
            assert health_status["ping_success"] is True
            assert "timestamp" in health_status
    
    @pytest.mark.asyncio
    async def test_health_status_failure(self, redis_ops):
        """Test health status during failures"""
        with patch.object(redis_ops.connection_manager, 'get_connection_info') as mock_conn_info:
            mock_conn_info.side_effect = Exception("Connection error")
            
            health_status = await redis_ops.get_health_status()
            
            assert health_status["overall_healthy"] is False
            assert "error" in health_status
            assert "timestamp" in health_status
    
    @pytest.mark.asyncio
    async def test_is_connected_property(self, redis_ops):
        """Test is_connected property delegation"""
        with patch.object(redis_ops.connection_manager, 'is_connected', True):
            assert redis_ops.is_connected is True
        
        with patch.object(redis_ops.connection_manager, 'is_connected', False):
            assert redis_ops.is_connected is False
    
    @pytest.mark.asyncio
    async def test_operation_error_handling(self, redis_ops):
        """Test error handling in Redis operations"""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch.object(redis_ops.connection_manager, 'get_connection') as mock_get_conn:
            async def mock_connection():
                yield mock_redis
            mock_get_conn.return_value = mock_connection()
            
            with pytest.raises(Exception, match="Redis error"):
                await redis_ops.get("test_key")


if __name__ == "__main__":
    pytest.main([__file__])