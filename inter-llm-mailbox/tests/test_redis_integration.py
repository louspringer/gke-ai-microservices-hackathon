"""
Integration tests for Redis components

Tests the complete Redis infrastructure with real Redis operations
(requires Redis server for full integration testing).
"""

import asyncio
import pytest
import json
from unittest.mock import patch

from src.core.redis_operations import RedisOperations
from src.core.redis_manager import RedisConfig
from src.core.redis_pubsub import PubSubMessage


@pytest.fixture
def redis_config():
    """Test Redis configuration"""
    return RedisConfig(
        host="localhost",
        port=6379,
        db=15,  # Use test database
        max_connections=5,
        health_check_interval=0.5,
        max_reconnect_attempts=2,
        reconnect_backoff_base=0.1
    )


@pytest.fixture
async def redis_ops(redis_config):
    """Redis operations fixture with cleanup"""
    ops = RedisOperations(redis_config)
    
    # Mock Redis for testing without actual server
    with patch('redis.asyncio.ConnectionPool') as mock_pool_class, \
         patch('redis.asyncio.Redis') as mock_redis_class:
        
        # Create mock objects
        mock_pool = MockConnectionPool()
        mock_redis = MockRedis()
        mock_pubsub = MockPubSub()
        
        mock_pool_class.return_value = mock_pool
        mock_redis_class.return_value = mock_redis
        mock_redis.pubsub.return_value = mock_pubsub
        
        yield ops
        
    await ops.close()


class MockConnectionPool:
    """Mock Redis connection pool"""
    def __init__(self):
        self.created_connections = 1
        self._available_connections = []
        self._in_use_connections = []
    
    async def disconnect(self):
        pass


class MockRedis:
    """Mock Redis client"""
    def __init__(self):
        self._data = {}
        self._hashes = {}
        self._sets = {}
        self._zsets = {}
        self._pubsub_channels = {}
    
    async def ping(self):
        return True
    
    async def close(self):
        pass
    
    async def aclose(self):
        pass
    
    # Basic operations
    async def set(self, key, value, ex=None):
        self._data[key] = value
        return True
    
    async def get(self, key):
        return self._data.get(key)
    
    async def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                count += 1
        return count
    
    async def exists(self, *keys):
        return sum(1 for key in keys if key in self._data)
    
    async def expire(self, key, seconds):
        return key in self._data
    
    # Hash operations
    async def hset(self, name, mapping=None, **kwargs):
        if name not in self._hashes:
            self._hashes[name] = {}
        if mapping:
            self._hashes[name].update(mapping)
        if kwargs:
            self._hashes[name].update(kwargs)
        return len(mapping or kwargs)
    
    async def hget(self, name, key):
        return self._hashes.get(name, {}).get(key)
    
    async def hgetall(self, name):
        return self._hashes.get(name, {})
    
    async def hdel(self, name, *keys):
        if name not in self._hashes:
            return 0
        count = 0
        for key in keys:
            if key in self._hashes[name]:
                del self._hashes[name][key]
                count += 1
        return count
    
    # Set operations
    async def sadd(self, name, *values):
        if name not in self._sets:
            self._sets[name] = set()
        old_size = len(self._sets[name])
        self._sets[name].update(values)
        return len(self._sets[name]) - old_size
    
    async def smembers(self, name):
        return self._sets.get(name, set())
    
    async def srem(self, name, *values):
        if name not in self._sets:
            return 0
        count = 0
        for value in values:
            if value in self._sets[name]:
                self._sets[name].remove(value)
                count += 1
        return count
    
    # Sorted set operations
    async def zadd(self, name, mapping):
        if name not in self._zsets:
            self._zsets[name] = {}
        old_size = len(self._zsets[name])
        self._zsets[name].update(mapping)
        return len(self._zsets[name]) - old_size
    
    async def zrange(self, name, start, end, withscores=False):
        if name not in self._zsets:
            return []
        items = sorted(self._zsets[name].items(), key=lambda x: x[1])
        if withscores:
            return items[start:end+1 if end != -1 else None]
        else:
            return [item[0] for item in items[start:end+1 if end != -1 else None]]
    
    async def zrem(self, name, *values):
        if name not in self._zsets:
            return 0
        count = 0
        for value in values:
            if value in self._zsets[name]:
                del self._zsets[name][value]
                count += 1
        return count
    
    # Pub/sub operations
    async def publish(self, channel, message):
        # Simulate publishing to subscribers
        return 1
    
    def pubsub(self):
        return MockPubSub()
    
    async def info(self, section=None):
        return {
            "redis_version": "6.2.0",
            "connected_clients": "1",
            "used_memory": "1000000"
        }


class MockPubSub:
    """Mock Redis pub/sub client"""
    def __init__(self):
        self._subscriptions = set()
        self._pattern_subscriptions = set()
        self._message_queue = []
    
    async def subscribe(self, *channels):
        self._subscriptions.update(channels)
    
    async def psubscribe(self, *patterns):
        self._pattern_subscriptions.update(patterns)
    
    async def unsubscribe(self, *channels):
        self._subscriptions.difference_update(channels)
    
    async def punsubscribe(self, *patterns):
        self._pattern_subscriptions.difference_update(patterns)
    
    async def get_message(self, ignore_subscribe_messages=False):
        if self._message_queue:
            return self._message_queue.pop(0)
        return None
    
    async def close(self):
        pass
    
    async def aclose(self):
        pass


class TestRedisIntegration:
    """Integration tests for Redis components"""
    
    @pytest.mark.asyncio
    async def test_full_initialization_and_cleanup(self, redis_ops):
        """Test complete initialization and cleanup cycle"""
        # Initialize
        await redis_ops.initialize()
        
        assert redis_ops.is_initialized
        assert redis_ops.connection_manager._state.value == "connected"
        assert redis_ops.pubsub_manager.is_running
        
        # Cleanup
        await redis_ops.close()
        
        assert not redis_ops.is_initialized
        assert not redis_ops.pubsub_manager.is_running
    
    @pytest.mark.asyncio
    async def test_basic_operations_workflow(self, redis_ops):
        """Test complete basic operations workflow"""
        await redis_ops.initialize()
        
        # Test string operations
        await redis_ops.set("test_key", "test_value")
        value = await redis_ops.get("test_key", deserialize=False)
        assert value == "test_value"
        
        # Test JSON operations
        test_data = {"name": "test", "value": 123}
        await redis_ops.set("json_key", test_data)
        retrieved_data = await redis_ops.get("json_key")
        assert retrieved_data == test_data
        
        # Test existence and expiration
        exists = await redis_ops.exists("test_key", "json_key")
        assert exists == 2
        
        await redis_ops.expire("test_key", 300)
        
        # Test deletion
        deleted = await redis_ops.delete("test_key", "json_key")
        assert deleted == 2
    
    @pytest.mark.asyncio
    async def test_hash_operations_workflow(self, redis_ops):
        """Test complete hash operations workflow"""
        await redis_ops.initialize()
        
        # Set hash fields
        hash_data = {
            "field1": "value1",
            "field2": {"nested": "data"},
            "field3": 42
        }
        
        result = await redis_ops.hset("test_hash", hash_data)
        assert result == 3
        
        # Get individual field
        field_value = await redis_ops.hget("test_hash", "field2")
        assert field_value == {"nested": "data"}
        
        # Get all fields
        all_fields = await redis_ops.hgetall("test_hash")
        assert all_fields["field1"] == "value1"
        assert all_fields["field2"] == {"nested": "data"}
        assert all_fields["field3"] == 42
        
        # Delete field
        deleted = await redis_ops.hdel("test_hash", "field1")
        assert deleted == 1
        
        # Verify deletion
        remaining_fields = await redis_ops.hgetall("test_hash")
        assert "field1" not in remaining_fields
        assert len(remaining_fields) == 2
    
    @pytest.mark.asyncio
    async def test_set_operations_workflow(self, redis_ops):
        """Test complete set operations workflow"""
        await redis_ops.initialize()
        
        # Add members
        added = await redis_ops.sadd("test_set", "member1", "member2", "member3")
        assert added == 3
        
        # Get members
        members = await redis_ops.smembers("test_set")
        assert members == {"member1", "member2", "member3"}
        
        # Remove member
        removed = await redis_ops.srem("test_set", "member2")
        assert removed == 1
        
        # Verify removal
        remaining_members = await redis_ops.smembers("test_set")
        assert remaining_members == {"member1", "member3"}
    
    @pytest.mark.asyncio
    async def test_sorted_set_operations_workflow(self, redis_ops):
        """Test complete sorted set operations workflow"""
        await redis_ops.initialize()
        
        # Add scored members
        members = {"member1": 1.0, "member2": 2.0, "member3": 3.0}
        added = await redis_ops.zadd("test_zset", members)
        assert added == 3
        
        # Get range
        range_result = await redis_ops.zrange("test_zset", 0, -1)
        assert range_result == ["member1", "member2", "member3"]
        
        # Get range with scores
        range_with_scores = await redis_ops.zrange("test_zset", 0, -1, withscores=True)
        assert range_with_scores == [("member1", 1.0), ("member2", 2.0), ("member3", 3.0)]
        
        # Remove member
        removed = await redis_ops.zrem("test_zset", "member2")
        assert removed == 1
        
        # Verify removal
        remaining = await redis_ops.zrange("test_zset", 0, -1)
        assert remaining == ["member1", "member3"]
    
    @pytest.mark.asyncio
    async def test_pubsub_workflow(self, redis_ops):
        """Test complete pub/sub workflow"""
        await redis_ops.initialize()
        
        # Set up message handler
        received_messages = []
        
        async def message_handler(message: PubSubMessage):
            received_messages.append(message)
        
        # Subscribe to channel
        await redis_ops.subscribe_channel("test_channel", message_handler)
        
        # Subscribe to pattern
        await redis_ops.subscribe_pattern("test_*", message_handler)
        
        # Verify subscriptions
        pubsub_info = await redis_ops.pubsub_manager.get_subscription_info()
        assert "test_channel" in pubsub_info["subscriptions"]
        assert "test_*" in pubsub_info["subscriptions"]
        
        # Publish message
        test_message = {"type": "test", "content": "Hello World"}
        subscribers = await redis_ops.publish("test_channel", test_message)
        assert subscribers == 1
        
        # Unsubscribe
        await redis_ops.unsubscribe_channel("test_channel")
        await redis_ops.unsubscribe_pattern("test_*")
        
        # Verify unsubscription
        pubsub_info = await redis_ops.pubsub_manager.get_subscription_info()
        assert len(pubsub_info["subscriptions"]) == 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring_workflow(self, redis_ops):
        """Test complete health monitoring workflow"""
        await redis_ops.initialize()
        
        # Test ping
        ping_result = await redis_ops.ping()
        assert ping_result is True
        
        # Get server info
        server_info = await redis_ops.info("server")
        assert "redis_version" in server_info
        
        # Get comprehensive health status
        health_status = await redis_ops.get_health_status()
        
        assert health_status["overall_healthy"] is True
        assert health_status["ping_success"] is True
        assert "connection" in health_status
        assert "pubsub" in health_status
        assert "server" in health_status
        assert "timestamp" in health_status
        
        # Verify connection info
        connection_info = health_status["connection"]
        assert connection_info["state"] == "connected"
        assert connection_info["host"] == "localhost"
        assert connection_info["port"] == 6379
        
        # Verify pubsub info
        pubsub_info = health_status["pubsub"]
        assert pubsub_info["running"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, redis_ops):
        """Test error handling in various scenarios"""
        await redis_ops.initialize()
        
        # Test operation on non-existent key
        result = await redis_ops.get("non_existent_key")
        assert result is None
        
        # Test hash operation on non-existent hash
        hash_result = await redis_ops.hgetall("non_existent_hash")
        assert hash_result == {}
        
        # Test set operation on non-existent set
        set_result = await redis_ops.smembers("non_existent_set")
        assert set_result == set()
        
        # Test sorted set operation on non-existent zset
        zset_result = await redis_ops.zrange("non_existent_zset", 0, -1)
        assert zset_result == []
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, redis_ops):
        """Test concurrent Redis operations"""
        await redis_ops.initialize()
        
        # Concurrent set operations
        async def set_operation(key, value):
            await redis_ops.set(f"concurrent_{key}", value)
            return await redis_ops.get(f"concurrent_{key}")
        
        # Run multiple operations concurrently
        tasks = [set_operation(i, f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed successfully
        for i, result in enumerate(results):
            assert result == f"value_{i}"
        
        # Cleanup
        keys_to_delete = [f"concurrent_{i}" for i in range(10)]
        deleted = await redis_ops.delete(*keys_to_delete)
        assert deleted == 10


if __name__ == "__main__":
    pytest.main([__file__])