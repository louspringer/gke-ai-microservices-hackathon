"""
Topic Manager for Inter-LLM Mailbox System

This module manages topic-based group communication, including topic creation,
hierarchical topic structures, and message broadcasting to topic subscribers.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import fnmatch

from ..models.subscription import Subscription, SubscriptionOptions, LLMID, SubscriptionID
from ..models.enums import AddressingMode, DeliveryMode
from .redis_manager import RedisConnectionManager
from .subscription_manager import SubscriptionManager


logger = logging.getLogger(__name__)


# Type aliases
TopicID = str
TopicName = str


@dataclass
class TopicConfig:
    """Configuration for a topic"""
    name: TopicName
    description: Optional[str] = None
    parent_topic: Optional[TopicName] = None
    auto_cleanup: bool = True
    cleanup_after_hours: int = 24
    max_subscribers: int = 1000
    message_retention_hours: int = 168  # 7 days
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'parent_topic': self.parent_topic,
            'auto_cleanup': self.auto_cleanup,
            'cleanup_after_hours': self.cleanup_after_hours,
            'max_subscribers': self.max_subscribers,
            'message_retention_hours': self.message_retention_hours,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicConfig':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            description=data.get('description'),
            parent_topic=data.get('parent_topic'),
            auto_cleanup=data.get('auto_cleanup', True),
            cleanup_after_hours=data.get('cleanup_after_hours', 24),
            max_subscribers=data.get('max_subscribers', 1000),
            message_retention_hours=data.get('message_retention_hours', 168),
            metadata=data.get('metadata', {})
        )


@dataclass
class Topic:
    """Represents a topic in the system"""
    id: TopicID
    config: TopicConfig
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    subscriber_count: int = 0
    message_count: int = 0
    active: bool = True
    
    @property
    def name(self) -> str:
        """Get topic name"""
        return self.config.name
    
    @property
    def is_hierarchical(self) -> bool:
        """Check if topic is part of a hierarchy"""
        return '.' in self.config.name or self.config.parent_topic is not None
    
    @property
    def hierarchy_parts(self) -> List[str]:
        """Get hierarchy parts (e.g., 'ai.ml.training' -> ['ai', 'ml', 'training'])"""
        return self.config.name.split('.')
    
    @property
    def parent_topics(self) -> List[str]:
        """Get all parent topic names in hierarchy"""
        parts = self.hierarchy_parts
        parents = []
        for i in range(1, len(parts)):
            parent = '.'.join(parts[:i])
            parents.append(parent)
        return parents
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if topic matches a subscription pattern"""
        return fnmatch.fnmatch(self.config.name, pattern)
    
    def is_child_of(self, parent_name: str) -> bool:
        """Check if this topic is a child of the given parent"""
        if self.config.parent_topic == parent_name:
            return True
        return self.config.name.startswith(f"{parent_name}.")
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def increment_message_count(self):
        """Increment message counter and update activity"""
        self.message_count += 1
        self.update_activity()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'config': self.config.to_dict(),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'subscriber_count': self.subscriber_count,
            'message_count': self.message_count,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Topic':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            config=TopicConfig.from_dict(data['config']),
            created_at=datetime.fromisoformat(data['created_at']),
            last_activity=datetime.fromisoformat(data['last_activity']),
            subscriber_count=data.get('subscriber_count', 0),
            message_count=data.get('message_count', 0),
            active=data.get('active', True)
        )


class TopicManager:
    """
    Manages topic-based group communication.
    
    Responsibilities:
    - Topic creation and lifecycle management
    - Hierarchical topic structure support
    - Topic subscription coordination
    - Message broadcasting to topic subscribers
    """
    
    def __init__(self, 
                 redis_manager: RedisConnectionManager,
                 subscription_manager: SubscriptionManager):
        self.redis_manager = redis_manager
        self.subscription_manager = subscription_manager
        
        # Topic storage
        self._topics: Dict[TopicName, Topic] = {}
        self._topic_hierarchy: Dict[TopicName, Set[TopicName]] = defaultdict(set)  # parent -> children
        self._topic_subscribers: Dict[TopicName, Set[SubscriptionID]] = defaultdict(set)
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Configuration
        self.cleanup_interval = 3600  # 1 hour
        self.max_topic_name_length = 256
        self.max_hierarchy_depth = 10
        
        # Locks for thread safety
        self._topic_lock = asyncio.Lock()
    
    async def start(self) -> None:
        """Start the topic manager"""
        if self._running:
            return
        
        logger.info("Starting topic manager")
        self._running = True
        
        # Load existing topics from Redis
        await self._load_topics()
        
        # Start background cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Topic manager started")
    
    async def stop(self) -> None:
        """Stop the topic manager"""
        if not self._running:
            return
        
        logger.info("Stopping topic manager")
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save topics to Redis
        await self._save_topics()
        
        # Clear in-memory state
        self._topics.clear()
        self._topic_hierarchy.clear()
        self._topic_subscribers.clear()
        
        logger.info("Topic manager stopped")
    
    async def create_topic(self, config: TopicConfig) -> Topic:
        """
        Create a new topic.
        
        Args:
            config: Topic configuration
            
        Returns:
            Created topic object
            
        Raises:
            ValueError: If topic configuration is invalid
        """
        async with self._topic_lock:
            # Validate topic configuration
            await self._validate_topic_config(config)
            
            # Check if topic already exists
            if config.name in self._topics:
                existing_topic = self._topics[config.name]
                if existing_topic.active:
                    logger.warning(f"Topic {config.name} already exists")
                    return existing_topic
                else:
                    # Reactivate inactive topic
                    existing_topic.active = True
                    existing_topic.config = config
                    existing_topic.update_activity()
                    await self._save_topic(existing_topic)
                    logger.info(f"Reactivated topic {config.name}")
                    return existing_topic
            
            # Create new topic
            import uuid
            topic = Topic(
                id=str(uuid.uuid4()),
                config=config
            )
            
            # Store topic
            self._topics[config.name] = topic
            
            # Update hierarchy if applicable
            if config.parent_topic:
                self._topic_hierarchy[config.parent_topic].add(config.name)
            
            # Handle hierarchical topic creation
            if topic.is_hierarchical:
                await self._ensure_parent_topics(topic)
            
            # Save to Redis
            await self._save_topic(topic)
            
            logger.info(f"Created topic {config.name} with ID {topic.id}")
            return topic
    
    async def delete_topic(self, topic_name: TopicName, force: bool = False) -> bool:
        """
        Delete a topic.
        
        Args:
            topic_name: Name of the topic to delete
            force: If True, delete even if there are active subscribers
            
        Returns:
            True if topic was deleted, False if not found
            
        Raises:
            ValueError: If topic has active subscribers and force=False
        """
        async with self._topic_lock:
            topic = self._topics.get(topic_name)
            if not topic:
                logger.warning(f"Topic {topic_name} not found for deletion")
                return False
            
            # Check for active subscribers
            if not force and topic.subscriber_count > 0:
                raise ValueError(f"Topic {topic_name} has {topic.subscriber_count} active subscribers")
            
            # Remove all subscriptions to this topic
            await self._remove_topic_subscriptions(topic_name)
            
            # Remove from hierarchy
            if topic.config.parent_topic:
                self._topic_hierarchy[topic.config.parent_topic].discard(topic_name)
            
            # Remove child topics if any
            children = self._topic_hierarchy.get(topic_name, set()).copy()
            for child_name in children:
                await self.delete_topic(child_name, force=True)
            
            # Remove from storage
            self._topics.pop(topic_name, None)
            self._topic_hierarchy.pop(topic_name, None)
            self._topic_subscribers.pop(topic_name, None)
            
            # Delete from Redis
            await self._delete_topic(topic.id)
            
            logger.info(f"Deleted topic {topic_name}")
            return True
    
    async def get_topic(self, topic_name: TopicName) -> Optional[Topic]:
        """
        Get a topic by name.
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            Topic object or None if not found
        """
        return self._topics.get(topic_name)
    
    async def list_topics(self, pattern: Optional[str] = None, include_inactive: bool = False) -> List[Topic]:
        """
        List topics, optionally filtered by pattern.
        
        Args:
            pattern: Optional pattern to filter topics (supports wildcards)
            include_inactive: Whether to include inactive topics
            
        Returns:
            List of matching topics
        """
        topics = []
        
        for topic in self._topics.values():
            if not include_inactive and not topic.active:
                continue
            
            if pattern and not topic.matches_pattern(pattern):
                continue
            
            topics.append(topic)
        
        return sorted(topics, key=lambda t: t.config.name)
    
    async def get_topic_hierarchy(self, root_topic: Optional[TopicName] = None) -> Dict[str, Any]:
        """
        Get topic hierarchy structure.
        
        Args:
            root_topic: Optional root topic to start from
            
        Returns:
            Hierarchical structure of topics
        """
        def build_hierarchy(topic_name: str) -> Dict[str, Any]:
            topic = self._topics.get(topic_name)
            if not topic:
                return {}
            
            children = {}
            for child_name in self._topic_hierarchy.get(topic_name, set()):
                children[child_name] = build_hierarchy(child_name)
            
            return {
                'topic': topic.to_dict(),
                'children': children
            }
        
        if root_topic:
            return build_hierarchy(root_topic)
        
        # Build full hierarchy starting from root topics
        hierarchy = {}
        for topic_name, topic in self._topics.items():
            if not topic.config.parent_topic and not topic.parent_topics:
                hierarchy[topic_name] = build_hierarchy(topic_name)
        
        return hierarchy
    
    async def subscribe_to_topic(self, 
                                llm_id: LLMID, 
                                topic_name: TopicName,
                                options: Optional[SubscriptionOptions] = None,
                                include_children: bool = False) -> Subscription:
        """
        Subscribe an LLM to a topic.
        
        Args:
            llm_id: ID of the subscribing LLM
            topic_name: Name of the topic to subscribe to
            options: Subscription options
            include_children: Whether to include child topics in subscription
            
        Returns:
            Created subscription object
            
        Raises:
            ValueError: If topic doesn't exist or subscription fails
        """
        topic = self._topics.get(topic_name)
        if not topic or not topic.active:
            raise ValueError(f"Topic {topic_name} does not exist or is inactive")
        
        # Check subscriber limit
        if topic.subscriber_count >= topic.config.max_subscribers:
            raise ValueError(f"Topic {topic_name} has reached maximum subscribers ({topic.config.max_subscribers})")
        
        # Create subscription pattern for hierarchical topics if requested
        pattern = None
        if include_children and topic.is_hierarchical:
            pattern = f"{topic_name}.*"
        
        # Create subscription through subscription manager
        subscription = await self.subscription_manager.create_subscription(
            llm_id=llm_id,
            target=topic_name,
            pattern=pattern,
            options=options
        )
        
        # Update topic subscriber tracking
        async with self._topic_lock:
            self._topic_subscribers[topic_name].add(subscription.id)
            topic.subscriber_count = len(self._topic_subscribers[topic_name])
            topic.update_activity()
            await self._save_topic(topic)
        
        logger.info(f"LLM {llm_id} subscribed to topic {topic_name} (subscription: {subscription.id})")
        return subscription
    
    async def unsubscribe_from_topic(self, subscription_id: SubscriptionID) -> bool:
        """
        Unsubscribe from a topic.
        
        Args:
            subscription_id: ID of the subscription to remove
            
        Returns:
            True if unsubscribed successfully, False if subscription not found
        """
        # Get subscription details
        subscription = await self.subscription_manager.get_subscription(subscription_id)
        if not subscription:
            return False
        
        topic_name = subscription.target
        
        # Remove subscription through subscription manager
        success = await self.subscription_manager.remove_subscription(subscription_id)
        
        if success:
            # Update topic subscriber tracking
            async with self._topic_lock:
                self._topic_subscribers[topic_name].discard(subscription_id)
                topic = self._topics.get(topic_name)
                if topic:
                    topic.subscriber_count = len(self._topic_subscribers[topic_name])
                    topic.update_activity()
                    await self._save_topic(topic)
            
            logger.info(f"Unsubscribed from topic {topic_name} (subscription: {subscription_id})")
        
        return success
    
    async def publish_to_topic(self, topic_name: TopicName, message: Dict[str, Any]) -> int:
        """
        Publish a message to a topic.
        
        Args:
            topic_name: Name of the topic to publish to
            message: Message data to publish
            
        Returns:
            Number of subscribers the message was delivered to
            
        Raises:
            ValueError: If topic doesn't exist
        """
        topic = self._topics.get(topic_name)
        if not topic or not topic.active:
            raise ValueError(f"Topic {topic_name} does not exist or is inactive")
        
        # Update message routing info to indicate topic addressing
        if 'routing_info' in message:
            message['routing_info']['addressing_mode'] = AddressingMode.TOPIC.value
            message['routing_info']['target'] = topic_name
        
        # Deliver message through subscription manager
        delivery_results = await self.subscription_manager.deliver_message(message, topic_name)
        
        # Update topic statistics
        async with self._topic_lock:
            topic.increment_message_count()
            await self._save_topic(topic)
        
        successful_deliveries = sum(1 for result in delivery_results if result.success)
        
        logger.info(f"Published message to topic {topic_name}, delivered to {successful_deliveries} subscribers")
        return successful_deliveries
    
    async def get_topic_subscribers(self, topic_name: TopicName) -> List[Dict[str, Any]]:
        """
        Get list of subscribers for a topic.
        
        Args:
            topic_name: Name of the topic
            
        Returns:
            List of subscriber information
        """
        topic = self._topics.get(topic_name)
        if not topic:
            return []
        
        subscribers = []
        subscription_ids = self._topic_subscribers.get(topic_name, set())
        
        for sub_id in subscription_ids:
            subscription = await self.subscription_manager.get_subscription(sub_id)
            if subscription:
                subscribers.append({
                    'subscription_id': subscription.id,
                    'llm_id': subscription.llm_id,
                    'created_at': subscription.created_at.isoformat(),
                    'last_activity': subscription.last_activity.isoformat(),
                    'message_count': subscription.message_count,
                    'active': subscription.active,
                    'delivery_mode': subscription.options.delivery_mode.value
                })
        
        return subscribers
    
    async def _validate_topic_config(self, config: TopicConfig) -> None:
        """Validate topic configuration"""
        if not config.name:
            raise ValueError("Topic name is required")
        
        if len(config.name) > self.max_topic_name_length:
            raise ValueError(f"Topic name exceeds maximum length ({self.max_topic_name_length})")
        
        # Validate topic name format
        if not config.name.replace('.', '').replace('_', '').replace('-', '').isalnum():
            raise ValueError("Topic name can only contain alphanumeric characters, dots, underscores, and hyphens")
        
        # Validate hierarchy depth
        if config.name.count('.') >= self.max_hierarchy_depth:
            raise ValueError(f"Topic hierarchy depth exceeds maximum ({self.max_hierarchy_depth})")
        
        # Validate parent topic exists if specified
        if config.parent_topic and config.parent_topic not in self._topics:
            raise ValueError(f"Parent topic {config.parent_topic} does not exist")
        
        # Validate configuration values
        if config.max_subscribers <= 0:
            raise ValueError("max_subscribers must be positive")
        
        if config.cleanup_after_hours <= 0:
            raise ValueError("cleanup_after_hours must be positive")
        
        if config.message_retention_hours <= 0:
            raise ValueError("message_retention_hours must be positive")
    
    async def _ensure_parent_topics(self, topic: Topic) -> None:
        """Ensure all parent topics exist in the hierarchy"""
        parent_names = topic.parent_topics
        
        for parent_name in parent_names:
            if parent_name not in self._topics:
                # Create implicit parent topic
                parent_config = TopicConfig(
                    name=parent_name,
                    description=f"Auto-created parent topic for {topic.config.name}",
                    auto_cleanup=False  # Don't auto-cleanup parent topics
                )
                
                parent_topic = Topic(
                    id=str(__import__('uuid').uuid4()),
                    config=parent_config
                )
                
                self._topics[parent_name] = parent_topic
                await self._save_topic(parent_topic)
                
                logger.info(f"Auto-created parent topic {parent_name}")
        
        # Update hierarchy relationships
        for i, parent_name in enumerate(parent_names):
            if i == 0:
                # First parent has no parent
                continue
            else:
                # Set up parent-child relationship
                grandparent_name = parent_names[i-1]
                self._topic_hierarchy[grandparent_name].add(parent_name)
        
        # Add the topic itself to its immediate parent
        if parent_names:
            immediate_parent = parent_names[-1]
            self._topic_hierarchy[immediate_parent].add(topic.config.name)
    
    async def _remove_topic_subscriptions(self, topic_name: TopicName) -> None:
        """Remove all subscriptions to a topic"""
        subscription_ids = self._topic_subscribers.get(topic_name, set()).copy()
        
        for sub_id in subscription_ids:
            await self.subscription_manager.remove_subscription(sub_id)
        
        self._topic_subscribers[topic_name].clear()
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up inactive topics"""
        logger.info("Starting topic cleanup loop")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self._running:
                    break
                
                await self._cleanup_inactive_topics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in topic cleanup loop: {e}")
        
        logger.info("Topic cleanup loop stopped")
    
    async def _cleanup_inactive_topics(self) -> None:
        """Clean up inactive topics based on their configuration"""
        current_time = datetime.utcnow()
        
        topics_to_cleanup = []
        
        for topic in self._topics.values():
            if not topic.config.auto_cleanup or not topic.active:
                continue
            
            # Check if topic has been inactive for too long
            inactive_duration = current_time - topic.last_activity
            if inactive_duration.total_seconds() > (topic.config.cleanup_after_hours * 3600):
                # Only cleanup if no active subscribers
                if topic.subscriber_count == 0:
                    topics_to_cleanup.append(topic.config.name)
        
        for topic_name in topics_to_cleanup:
            try:
                await self.delete_topic(topic_name, force=True)
                logger.info(f"Auto-cleaned up inactive topic {topic_name}")
            except Exception as e:
                logger.error(f"Failed to cleanup topic {topic_name}: {e}")
    
    async def _load_topics(self) -> None:
        """Load topics from Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Get all topic keys
                keys = await redis_conn.keys("topic:*")
                
                for key in keys:
                    try:
                        data = await redis_conn.hgetall(key)
                        if data:
                            # Convert bytes to strings
                            str_data = {k.decode() if isinstance(k, bytes) else k: 
                                      v.decode() if isinstance(v, bytes) else v 
                                      for k, v in data.items()}
                            
                            # Parse JSON fields
                            if 'config' in str_data:
                                str_data['config'] = json.loads(str_data['config'])
                            
                            topic = Topic.from_dict(str_data)
                            
                            # Restore in-memory indices
                            self._topics[topic.config.name] = topic
                            
                            # Rebuild hierarchy
                            if topic.config.parent_topic:
                                self._topic_hierarchy[topic.config.parent_topic].add(topic.config.name)
                            
                    except Exception as e:
                        logger.error(f"Failed to load topic from {key}: {e}")
                
                logger.info(f"Loaded {len(self._topics)} topics from Redis")
                
        except Exception as e:
            logger.error(f"Failed to load topics from Redis: {e}")
    
    async def _save_topics(self) -> None:
        """Save all topics to Redis storage"""
        try:
            for topic in self._topics.values():
                await self._save_topic(topic)
            
            logger.info(f"Saved {len(self._topics)} topics to Redis")
            
        except Exception as e:
            logger.error(f"Failed to save topics to Redis: {e}")
    
    async def _save_topic(self, topic: Topic, redis_conn=None) -> None:
        """Save a single topic to Redis"""
        if redis_conn is None:
            async with self.redis_manager.get_connection() as redis_conn:
                await self._save_topic(topic, redis_conn)
                return
        
        key = f"topic:{topic.id}"
        data = topic.to_dict()
        
        # Convert complex objects to JSON strings for Redis storage
        redis_data = {}
        for k, v in data.items():
            if isinstance(v, dict):
                redis_data[k] = json.dumps(v)
            elif isinstance(v, (list, tuple)):
                redis_data[k] = json.dumps(list(v))
            elif v is None:
                redis_data[k] = ""
            else:
                redis_data[k] = str(v)
        
        await redis_conn.hset(key, mapping=redis_data)
        
        # Also create a name-to-id mapping for easy lookup
        await redis_conn.set(f"topic_name:{topic.config.name}", topic.id)
    
    async def _delete_topic(self, topic_id: TopicID) -> None:
        """Delete a topic from Redis storage"""
        try:
            async with self.redis_manager.get_connection() as redis_conn:
                # Get topic name for cleanup
                topic_data = await redis_conn.hgetall(f"topic:{topic_id}")
                if topic_data:
                    config_data = json.loads(topic_data.get(b'config', b'{}').decode())
                    topic_name = config_data.get('name')
                    if topic_name:
                        await redis_conn.delete(f"topic_name:{topic_name}")
                
                # Delete main topic data
                await redis_conn.delete(f"topic:{topic_id}")
                
        except Exception as e:
            logger.error(f"Failed to delete topic {topic_id} from Redis: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get topic manager statistics"""
        active_topics = sum(1 for topic in self._topics.values() if topic.active)
        total_subscribers = sum(topic.subscriber_count for topic in self._topics.values())
        total_messages = sum(topic.message_count for topic in self._topics.values())
        
        hierarchy_stats = {
            'root_topics': len([t for t in self._topics.values() if not t.config.parent_topic and not t.parent_topics]),
            'hierarchical_topics': len([t for t in self._topics.values() if t.is_hierarchical]),
            'max_depth': max((len(t.hierarchy_parts) for t in self._topics.values()), default=0)
        }
        
        return {
            "total_topics": len(self._topics),
            "active_topics": active_topics,
            "total_subscribers": total_subscribers,
            "total_messages": total_messages,
            "hierarchy": hierarchy_stats,
            "running": self._running
        }