"""
Redis Operations Wrapper for Inter-LLM Mailbox System

This module provides a unified interface for all Redis operations including
basic operations, pub/sub, and health monitoring.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timedelta

from .redis_manager import RedisConnectionManager, RedisConfig
from .redis_pubsub import RedisPubSubManager, PubSubMessage


logger = logging.getLogger(__name__)


class RedisOperations:
    """
    Unified Redis operations interface combining connection management,
    basic operations, and pub/sub functionality.
    
    Implements requirements:
    - 8.1: Redis connection management with resilience
    - 8.4: Retry logic and error handling
    - 6.2: Health monitoring
    """
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.connection_manager = RedisConnectionManager(config)
        self.pubsub_manager = RedisPubSubManager(self.connection_manager)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Redis operations"""
        if self._initialized:
            return
        
        logger.info("Initializing Redis operations")
        await self.connection_manager.initialize()
        await self.pubsub_manager.start()
        self._initialized = True
        logger.info("Redis operations initialized")
    
    async def close(self) -> None:
        """Close Redis operations and cleanup resources"""
        if not self._initialized:
            return
        
        logger.info("Closing Redis operations")
        await self.pubsub_manager.stop()
        await self.connection_manager.close()
        self._initialized = False
        logger.info("Redis operations closed")
    
    # Basic Redis Operations
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration"""
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.set(key, serialized_value, ex=ex)
                
            logger.debug(f"Set key '{key}' with expiration {ex}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}")
            raise
    
    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get value by key with optional JSON deserialization"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                value = await redis_conn.get(key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            raise
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.delete(*keys)
                
            logger.debug(f"Deleted {result} keys: {keys}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            raise
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.exists(*keys)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to check existence of keys {keys}: {e}")
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.expire(key, seconds)
                
            logger.debug(f"Set expiration for key '{key}': {seconds}s")
            return result
            
        except Exception as e:
            logger.error(f"Failed to set expiration for key '{key}': {e}")
            raise
    
    async def ttl(self, key: str) -> int:
        """Get time to live for a key"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.ttl(key)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get TTL for key '{key}': {e}")
            raise
    
    async def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.keys(pattern)
                
            # Convert bytes to strings if needed
            if result and isinstance(result[0], bytes):
                result = [key.decode('utf-8') for key in result]
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get keys with pattern '{pattern}': {e}")
            raise
    
    # Hash Operations
    
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """Set hash fields"""
        try:
            # Serialize values
            serialized_mapping = {
                k: json.dumps(v) if not isinstance(v, str) else v
                for k, v in mapping.items()
            }
            
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.hset(name, mapping=serialized_mapping)
                
            logger.debug(f"Set {len(mapping)} fields in hash '{name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to set hash '{name}': {e}")
            raise
    
    async def hget(self, name: str, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get hash field value"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                value = await redis_conn.hget(name, key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to get hash field '{name}.{key}': {e}")
            raise
    
    async def hgetall(self, name: str, deserialize: bool = True) -> Dict[str, Any]:
        """Get all hash fields"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.hgetall(name)
            
            if not result:
                return {}
            
            if deserialize:
                deserialized = {}
                for k, v in result.items():
                    try:
                        deserialized[k] = json.loads(v)
                    except json.JSONDecodeError:
                        deserialized[k] = v
                return deserialized
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all hash fields for '{name}': {e}")
            raise
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.hdel(name, *keys)
                
            logger.debug(f"Deleted {result} fields from hash '{name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete hash fields '{name}': {e}")
            raise
    
    # Sorted Set Operations
    
    async def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        """Add members to sorted set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.zadd(name, mapping)
                
            logger.debug(f"Added {result} members to sorted set '{name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add to sorted set '{name}': {e}")
            raise
    
    async def zrange(self, name: str, start: int, end: int, withscores: bool = False) -> List[Any]:
        """Get range from sorted set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.zrange(name, start, end, withscores=withscores)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get range from sorted set '{name}': {e}")
            raise
    
    async def zrem(self, name: str, *values: str) -> int:
        """Remove members from sorted set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.zrem(name, *values)
                
            logger.debug(f"Removed {result} members from sorted set '{name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to remove from sorted set '{name}': {e}")
            raise
    
    async def zcard(self, name: str) -> int:
        """Get the number of members in a sorted set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.zcard(name)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get cardinality of sorted set '{name}': {e}")
            raise
    
    async def zrevrange(self, name: str, start: int, end: int, withscores: bool = False) -> List[Any]:
        """Get range from sorted set in reverse order (highest to lowest score)"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.zrevrange(name, start, end, withscores=withscores)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get reverse range from sorted set '{name}': {e}")
            raise
    
    # Set Operations
    
    async def sadd(self, name: str, *values: str) -> int:
        """Add members to set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.sadd(name, *values)
                
            logger.debug(f"Added {result} members to set '{name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add to set '{name}': {e}")
            raise
    
    async def smembers(self, name: str) -> set:
        """Get all set members"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.smembers(name)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get set members '{name}': {e}")
            raise
    
    async def srem(self, name: str, *values: str) -> int:
        """Remove members from set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.srem(name, *values)
                
            logger.debug(f"Removed {result} members from set '{name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to remove from set '{name}': {e}")
            raise
    
    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is member of set"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.sismember(name, value)
                
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to check membership in set '{name}': {e}")
            raise
    
    async def scard(self, name: str) -> int:
        """Get set cardinality (number of members)"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.scard(name)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get cardinality of set '{name}': {e}")
            raise
    
    # Pub/Sub Operations
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish message to channel"""
        return await self.pubsub_manager.publish(channel, message)
    
    async def subscribe_channel(self, channel: str, handler: Optional[Callable] = None) -> None:
        """Subscribe to channel"""
        await self.pubsub_manager.subscribe_channel(channel, handler)
    
    async def subscribe_pattern(self, pattern: str, handler: Optional[Callable] = None) -> None:
        """Subscribe to pattern"""
        await self.pubsub_manager.subscribe_pattern(pattern, handler)
    
    async def unsubscribe_channel(self, channel: str) -> None:
        """Unsubscribe from channel"""
        await self.pubsub_manager.unsubscribe_channel(channel)
    
    async def unsubscribe_pattern(self, pattern: str) -> None:
        """Unsubscribe from pattern"""
        await self.pubsub_manager.unsubscribe_pattern(pattern)
    
    # Health and Monitoring
    
    async def ping(self) -> bool:
        """Ping Redis server"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.ping()
                
            return result
            
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get Redis server information"""
        try:
            async with self.connection_manager.get_connection() as redis_conn:
                result = await redis_conn.info(section)
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            raise
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            connection_info = await self.connection_manager.get_connection_info()
            pubsub_info = await self.pubsub_manager.get_subscription_info()
            
            # Test basic operations
            ping_success = await self.ping()
            
            # Get Redis server info
            server_info = {}
            try:
                server_info = await self.info("server")
            except Exception:
                pass
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_healthy": ping_success and connection_info["state"] == "connected",
                "connection": connection_info,
                "pubsub": pubsub_info,
                "server": server_info,
                "ping_success": ping_success
            }
            
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_healthy": False,
                "error": str(e)
            }
    
    @property
    def is_initialized(self) -> bool:
        """Check if Redis operations are initialized"""
        return self._initialized
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self.connection_manager.is_connected