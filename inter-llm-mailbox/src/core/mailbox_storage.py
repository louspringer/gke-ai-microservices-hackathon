"""
Mailbox Storage Operations for Inter-LLM Mailbox System

This module provides mailbox creation, metadata management, message persistence,
and retrieval operations using Redis as the storage backend.

Implements requirements:
- 1.4: Automatic mailbox creation
- 3.1: Message persistence and retrieval
- 3.2: Pagination support for message retrieval
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
from enum import Enum

from ..models.message import Message, MessageID, LLMID
from ..models.enums import ContentType, AddressingMode, Priority
from .redis_operations import RedisOperations


logger = logging.getLogger(__name__)


class MailboxState(Enum):
    """Mailbox states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class MailboxMetadata:
    """Mailbox metadata structure"""
    name: str
    created_at: datetime
    created_by: LLMID
    state: MailboxState = MailboxState.ACTIVE
    description: Optional[str] = None
    max_messages: int = 10000
    message_ttl: Optional[int] = None  # TTL in seconds
    last_activity: Optional[datetime] = None
    message_count: int = 0
    total_size_bytes: int = 0
    subscribers: List[LLMID] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'state': self.state.value,
            'description': self.description,
            'max_messages': self.max_messages,
            'message_ttl': self.message_ttl,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'message_count': self.message_count,
            'total_size_bytes': self.total_size_bytes,
            'subscribers': self.subscribers,
            'tags': self.tags,
            'custom_metadata': self.custom_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MailboxMetadata':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            state=MailboxState(data.get('state', 'active')),
            description=data.get('description'),
            max_messages=data.get('max_messages', 10000),
            message_ttl=data.get('message_ttl'),
            last_activity=datetime.fromisoformat(data['last_activity']) if data.get('last_activity') else None,
            message_count=data.get('message_count', 0),
            total_size_bytes=data.get('total_size_bytes', 0),
            subscribers=data.get('subscribers', []),
            tags=data.get('tags', []),
            custom_metadata=data.get('custom_metadata', {})
        )


@dataclass
class MessageFilter:
    """Message filtering criteria"""
    sender_id: Optional[LLMID] = None
    content_type: Optional[ContentType] = None
    priority: Optional[Priority] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Optional[List[str]] = None
    unread_only: bool = False


@dataclass
class PaginationInfo:
    """Pagination information for message retrieval"""
    offset: int = 0
    limit: int = 50
    total_count: Optional[int] = None
    has_more: bool = False


@dataclass
class MessagePage:
    """Paginated message results"""
    messages: List[Message]
    pagination: PaginationInfo
    total_count: int
    filtered_count: int


class MailboxStorage:
    """
    Mailbox storage operations using Redis as backend.
    
    Redis Key Patterns:
    - mailbox:{name}:metadata - Hash containing mailbox metadata
    - mailbox:{name}:messages - Sorted set of message IDs by timestamp
    - mailbox:{name}:message_data - Hash containing message data
    - mailbox:{name}:read_status - Hash tracking read status per LLM
    - mailbox_index - Set of all mailbox names
    """
    
    def __init__(self, redis_ops: RedisOperations):
        self.redis_ops = redis_ops
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize mailbox storage"""
        if self._initialized:
            return
        
        logger.info("Initializing mailbox storage")
        if not self.redis_ops.is_initialized:
            await self.redis_ops.initialize()
        
        self._initialized = True
        logger.info("Mailbox storage initialized")
    
    async def close(self) -> None:
        """Close mailbox storage"""
        if not self._initialized:
            return
        
        logger.info("Closing mailbox storage")
        self._initialized = False
        logger.info("Mailbox storage closed")
    
    # Mailbox Management
    
    async def create_mailbox(self, 
                           name: str, 
                           created_by: LLMID,
                           description: Optional[str] = None,
                           max_messages: int = 10000,
                           message_ttl: Optional[int] = None,
                           tags: Optional[List[str]] = None,
                           custom_metadata: Optional[Dict[str, Any]] = None) -> MailboxMetadata:
        """
        Create a new mailbox with metadata.
        
        Args:
            name: Mailbox name
            created_by: LLM ID that created the mailbox
            description: Optional description
            max_messages: Maximum number of messages to store
            message_ttl: Message TTL in seconds
            tags: Optional tags for categorization
            custom_metadata: Additional custom metadata
            
        Returns:
            MailboxMetadata: Created mailbox metadata
            
        Raises:
            ValueError: If mailbox already exists
        """
        logger.info(f"Creating mailbox '{name}' by {created_by}")
        
        # Check if mailbox already exists
        if await self.mailbox_exists(name):
            raise ValueError(f"Mailbox '{name}' already exists")
        
        # Create metadata
        metadata = MailboxMetadata(
            name=name,
            created_at=datetime.utcnow(),
            created_by=created_by,
            description=description,
            max_messages=max_messages,
            message_ttl=message_ttl,
            tags=tags or [],
            custom_metadata=custom_metadata or {}
        )
        
        # Store metadata in Redis
        metadata_key = f"mailbox:{name}:metadata"
        await self.redis_ops.hset(metadata_key, metadata.to_dict())
        
        # Add to mailbox index
        await self.redis_ops.sadd("mailbox_index", name)
        
        logger.info(f"Mailbox '{name}' created successfully")
        return metadata
    
    async def get_mailbox_metadata(self, name: str) -> Optional[MailboxMetadata]:
        """
        Get mailbox metadata.
        
        Args:
            name: Mailbox name
            
        Returns:
            MailboxMetadata or None if mailbox doesn't exist
        """
        metadata_key = f"mailbox:{name}:metadata"
        data = await self.redis_ops.hgetall(metadata_key)
        
        if not data:
            return None
        
        return MailboxMetadata.from_dict(data)
    
    async def update_mailbox_metadata(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update mailbox metadata.
        
        Args:
            name: Mailbox name
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if updated, False if mailbox doesn't exist
        """
        if not await self.mailbox_exists(name):
            return False
        
        metadata_key = f"mailbox:{name}:metadata"
        
        # Handle datetime fields
        if 'last_activity' in updates and isinstance(updates['last_activity'], datetime):
            updates['last_activity'] = updates['last_activity'].isoformat()
        
        await self.redis_ops.hset(metadata_key, updates)
        logger.debug(f"Updated metadata for mailbox '{name}'")
        return True
    
    async def delete_mailbox(self, name: str, permanent: bool = False) -> bool:
        """
        Delete a mailbox.
        
        Args:
            name: Mailbox name
            permanent: If True, permanently delete; if False, mark as deleted
            
        Returns:
            bool: True if deleted, False if mailbox doesn't exist
        """
        if not await self.mailbox_exists(name):
            return False
        
        if permanent:
            # Permanently delete all mailbox data
            keys_to_delete = [
                f"mailbox:{name}:metadata",
                f"mailbox:{name}:messages",
                f"mailbox:{name}:message_data",
                f"mailbox:{name}:read_status"
            ]
            
            await self.redis_ops.delete(*keys_to_delete)
            await self.redis_ops.srem("mailbox_index", name)
            logger.info(f"Permanently deleted mailbox '{name}'")
        else:
            # Mark as deleted
            await self.update_mailbox_metadata(name, {'state': MailboxState.DELETED.value})
            logger.info(f"Marked mailbox '{name}' as deleted")
        
        return True
    
    async def mailbox_exists(self, name: str) -> bool:
        """Check if mailbox exists"""
        metadata_key = f"mailbox:{name}:metadata"
        return await self.redis_ops.exists(metadata_key) > 0
    
    async def list_mailboxes(self, 
                           state: Optional[MailboxState] = None,
                           created_by: Optional[LLMID] = None,
                           tags: Optional[List[str]] = None) -> List[MailboxMetadata]:
        """
        List mailboxes with optional filtering.
        
        Args:
            state: Filter by mailbox state
            created_by: Filter by creator
            tags: Filter by tags (mailbox must have all specified tags)
            
        Returns:
            List[MailboxMetadata]: List of matching mailboxes
        """
        # Get all mailbox names
        mailbox_names = await self.redis_ops.smembers("mailbox_index")
        
        mailboxes = []
        for name in mailbox_names:
            metadata = await self.get_mailbox_metadata(name)
            if not metadata:
                continue
            
            # Apply filters
            if state and metadata.state != state:
                continue
            
            if created_by and metadata.created_by != created_by:
                continue
            
            if tags and not all(tag in metadata.tags for tag in tags):
                continue
            
            mailboxes.append(metadata)
        
        # Sort by creation time
        mailboxes.sort(key=lambda m: m.created_at, reverse=True)
        return mailboxes
    
    # Message Storage Operations
    
    async def store_message(self, mailbox_name: str, message: Message) -> bool:
        """
        Store a message in the specified mailbox.
        
        Args:
            mailbox_name: Target mailbox name
            message: Message to store
            
        Returns:
            bool: True if stored successfully
            
        Raises:
            ValueError: If mailbox doesn't exist or is full
        """
        logger.debug(f"Storing message {message.id} in mailbox '{mailbox_name}'")
        
        # Get mailbox metadata
        metadata = await self.get_mailbox_metadata(mailbox_name)
        if not metadata:
            # Auto-create mailbox if it doesn't exist (requirement 1.4)
            metadata = await self.create_mailbox(
                name=mailbox_name,
                created_by=message.sender_id,
                description=f"Auto-created mailbox for {message.sender_id}"
            )
        
        # Store message data first
        message_data_key = f"mailbox:{mailbox_name}:message_data"
        message_hash = message.to_redis_hash()
        await self.redis_ops.hset(message_data_key, {message.id: json.dumps(message_hash)})
        
        # Add to sorted set with timestamp as score
        messages_key = f"mailbox:{mailbox_name}:messages"
        timestamp_score = message.timestamp.timestamp()
        await self.redis_ops.zadd(messages_key, {message.id: timestamp_score})
        
        # Check if mailbox is full and cleanup if needed
        current_count = await self.redis_ops.zcard(messages_key)
        if current_count > metadata.max_messages:
            # Remove oldest messages to stay within limit
            await self._cleanup_old_messages(mailbox_name, metadata.max_messages)
            current_count = metadata.max_messages
        
        # Update mailbox metadata with actual current count
        message_size = message.size_bytes()
        updates = {
            'message_count': current_count,
            'total_size_bytes': metadata.total_size_bytes + message_size,
            'last_activity': datetime.utcnow()
        }
        await self.update_mailbox_metadata(mailbox_name, updates)
        
        # Set TTL if configured
        if metadata.message_ttl:
            await self.redis_ops.expire(f"mailbox:{mailbox_name}:message_data", metadata.message_ttl)
        
        logger.debug(f"Message {message.id} stored successfully in mailbox '{mailbox_name}'")
        return True
    
    async def get_messages(self, 
                         mailbox_name: str,
                         offset: int = 0,
                         limit: int = 50,
                         message_filter: Optional[MessageFilter] = None,
                         reverse: bool = True) -> MessagePage:
        """
        Retrieve messages from mailbox with pagination and filtering.
        
        Args:
            mailbox_name: Mailbox name
            offset: Number of messages to skip
            limit: Maximum number of messages to return
            message_filter: Optional filtering criteria
            reverse: If True, return newest messages first
            
        Returns:
            MessagePage: Paginated message results
        """
        logger.debug(f"Retrieving messages from mailbox '{mailbox_name}' (offset={offset}, limit={limit})")
        
        if not await self.mailbox_exists(mailbox_name):
            return MessagePage(
                messages=[],
                pagination=PaginationInfo(offset=offset, limit=limit, total_count=0),
                total_count=0,
                filtered_count=0
            )
        
        messages_key = f"mailbox:{mailbox_name}:messages"
        
        # Get total count
        total_count = await self.redis_ops.zcard(messages_key)
        
        # Get message IDs with pagination
        if reverse:
            # Newest first (highest scores first)
            message_ids = await self.redis_ops.zrevrange(
                messages_key, 
                offset, 
                offset + limit - 1
            )
        else:
            # Oldest first (lowest scores first)
            message_ids = await self.redis_ops.zrange(
                messages_key, 
                offset, 
                offset + limit - 1
            )
        
        # Retrieve message data
        messages = []
        if message_ids:
            message_data_key = f"mailbox:{mailbox_name}:message_data"
            
            for message_id in message_ids:
                message_json = await self.redis_ops.hget(message_data_key, message_id, deserialize=False)
                if message_json:
                    try:
                        message_hash = json.loads(message_json)
                        message = Message.from_redis_hash(message_hash)
                        
                        # Apply filters
                        if message_filter and not self._message_matches_filter(message, message_filter):
                            continue
                        
                        messages.append(message)
                    except Exception as e:
                        logger.warning(f"Failed to deserialize message {message_id}: {e}")
                        continue
        
        # Calculate pagination info
        filtered_count = len(messages)
        has_more = (offset + limit) < total_count
        
        pagination = PaginationInfo(
            offset=offset,
            limit=limit,
            total_count=total_count,
            has_more=has_more
        )
        
        return MessagePage(
            messages=messages,
            pagination=pagination,
            total_count=total_count,
            filtered_count=filtered_count
        )
    
    async def get_message(self, mailbox_name: str, message_id: MessageID) -> Optional[Message]:
        """
        Get a specific message from mailbox.
        
        Args:
            mailbox_name: Mailbox name
            message_id: Message ID
            
        Returns:
            Message or None if not found
        """
        if not await self.mailbox_exists(mailbox_name):
            return None
        
        message_data_key = f"mailbox:{mailbox_name}:message_data"
        message_json = await self.redis_ops.hget(message_data_key, message_id, deserialize=False)
        
        if not message_json:
            return None
        
        try:
            message_hash = json.loads(message_json)
            return Message.from_redis_hash(message_hash)
        except Exception as e:
            logger.warning(f"Failed to deserialize message {message_id}: {e}")
            return None
    
    async def delete_message(self, mailbox_name: str, message_id: MessageID) -> bool:
        """
        Delete a message from mailbox.
        
        Args:
            mailbox_name: Mailbox name
            message_id: Message ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not await self.mailbox_exists(mailbox_name):
            return False
        
        # Get message size for metadata update
        message = await self.get_message(mailbox_name, message_id)
        if not message:
            return False
        
        message_size = message.size_bytes()
        
        # Remove from sorted set and hash
        messages_key = f"mailbox:{mailbox_name}:messages"
        message_data_key = f"mailbox:{mailbox_name}:message_data"
        
        removed_from_set = await self.redis_ops.zrem(messages_key, message_id)
        removed_from_hash = await self.redis_ops.hdel(message_data_key, message_id)
        
        if removed_from_set > 0 or removed_from_hash > 0:
            # Update mailbox metadata
            metadata = await self.get_mailbox_metadata(mailbox_name)
            if metadata:
                updates = {
                    'message_count': max(0, metadata.message_count - 1),
                    'total_size_bytes': max(0, metadata.total_size_bytes - message_size),
                    'last_activity': datetime.utcnow()
                }
                await self.update_mailbox_metadata(mailbox_name, updates)
            
            logger.debug(f"Deleted message {message_id} from mailbox '{mailbox_name}'")
            return True
        
        return False
    
    async def mark_message_read(self, mailbox_name: str, message_id: MessageID, llm_id: LLMID) -> bool:
        """
        Mark a message as read by an LLM.
        
        Args:
            mailbox_name: Mailbox name
            message_id: Message ID
            llm_id: LLM ID that read the message
            
        Returns:
            bool: True if marked, False if message not found
        """
        if not await self.mailbox_exists(mailbox_name):
            return False
        
        # Check if message exists
        if not await self.get_message(mailbox_name, message_id):
            return False
        
        # Mark as read
        read_status_key = f"mailbox:{mailbox_name}:read_status"
        read_key = f"{message_id}:{llm_id}"
        await self.redis_ops.hset(read_status_key, {read_key: datetime.utcnow().isoformat()})
        
        logger.debug(f"Marked message {message_id} as read by {llm_id} in mailbox '{mailbox_name}'")
        return True
    
    async def is_message_read(self, mailbox_name: str, message_id: MessageID, llm_id: LLMID) -> bool:
        """
        Check if a message has been read by an LLM.
        
        Args:
            mailbox_name: Mailbox name
            message_id: Message ID
            llm_id: LLM ID
            
        Returns:
            bool: True if read, False otherwise
        """
        read_status_key = f"mailbox:{mailbox_name}:read_status"
        read_key = f"{message_id}:{llm_id}"
        
        read_time = await self.redis_ops.hget(read_status_key, read_key)
        return read_time is not None
    
    async def get_unread_count(self, mailbox_name: str, llm_id: LLMID) -> int:
        """
        Get count of unread messages for an LLM.
        
        Args:
            mailbox_name: Mailbox name
            llm_id: LLM ID
            
        Returns:
            int: Number of unread messages
        """
        if not await self.mailbox_exists(mailbox_name):
            return 0
        
        # Get all message IDs
        messages_key = f"mailbox:{mailbox_name}:messages"
        all_message_ids = await self.redis_ops.zrange(messages_key, 0, -1)
        
        if not all_message_ids:
            return 0
        
        # Count unread messages
        unread_count = 0
        for message_id in all_message_ids:
            if not await self.is_message_read(mailbox_name, message_id, llm_id):
                unread_count += 1
        
        return unread_count
    
    # Helper Methods
    
    def _message_matches_filter(self, message: Message, message_filter: MessageFilter) -> bool:
        """Check if message matches filter criteria"""
        if message_filter.sender_id and message.sender_id != message_filter.sender_id:
            return False
        
        if message_filter.content_type and message.content_type != message_filter.content_type:
            return False
        
        if message_filter.priority and message.routing_info.priority != message_filter.priority:
            return False
        
        if message_filter.start_time and message.timestamp < message_filter.start_time:
            return False
        
        if message_filter.end_time and message.timestamp > message_filter.end_time:
            return False
        
        if message_filter.tags:
            message_tags = message.metadata.get('tags', [])
            if not all(tag in message_tags for tag in message_filter.tags):
                return False
        
        return True
    
    async def _cleanup_old_messages(self, mailbox_name: str, keep_count: int) -> int:
        """
        Remove oldest messages to keep only the specified count.
        
        Args:
            mailbox_name: Mailbox name
            keep_count: Number of messages to keep
            
        Returns:
            int: Number of messages removed
        """
        messages_key = f"mailbox:{mailbox_name}:messages"
        
        # Get current count
        current_count = await self.redis_ops.zcard(messages_key)
        
        if current_count <= keep_count:
            return 0
        
        # Get oldest message IDs to remove
        remove_count = current_count - keep_count
        oldest_message_ids = await self.redis_ops.zrange(messages_key, 0, remove_count - 1)
        
        if not oldest_message_ids:
            return 0
        
        # Remove from sorted set and message data
        message_data_key = f"mailbox:{mailbox_name}:message_data"
        
        removed_count = 0
        total_size_removed = 0
        
        for message_id in oldest_message_ids:
            # Get message size before deletion
            message = await self.get_message(mailbox_name, message_id)
            if message:
                total_size_removed += message.size_bytes()
            
            # Remove from both structures
            await self.redis_ops.zrem(messages_key, message_id)
            await self.redis_ops.hdel(message_data_key, message_id)
            removed_count += 1
        
        # Update mailbox metadata
        metadata = await self.get_mailbox_metadata(mailbox_name)
        if metadata:
            updates = {
                'message_count': max(0, metadata.message_count - removed_count),
                'total_size_bytes': max(0, metadata.total_size_bytes - total_size_removed)
            }
            await self.update_mailbox_metadata(mailbox_name, updates)
        
        logger.info(f"Cleaned up {removed_count} old messages from mailbox '{mailbox_name}'")
        return removed_count
    
    @property
    def is_initialized(self) -> bool:
        """Check if mailbox storage is initialized"""
        return self._initialized