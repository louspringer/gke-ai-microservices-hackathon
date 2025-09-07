"""
Offline Message Handler for Inter-LLM Mailbox System

This module handles message queuing for offline subscribers, message marking
system (read/unread status), and time-based/ID-based message filtering.

Implements requirements:
- 3.1: Message persistence and retrieval for offline LLMs
- 3.3: Message marking (read/unread status)
- 3.5: Time-based and ID-based message filtering
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Set
from enum import Enum

from ..models.message import Message, MessageID, LLMID
from ..models.enums import ContentType, Priority
from .redis_operations import RedisOperations
from .mailbox_storage import MailboxStorage


logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Message status for offline handling"""
    QUEUED = "queued"
    DELIVERED = "delivered"
    READ = "read"
    EXPIRED = "expired"


@dataclass
class OfflineMessage:
    """Offline message with metadata"""
    message: Message
    queued_at: datetime
    target_llm: LLMID
    mailbox_name: str
    status: MessageStatus = MessageStatus.QUEUED
    delivery_attempts: int = 0
    last_attempt: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            'message': self.message.to_dict(),
            'queued_at': self.queued_at.isoformat(),
            'target_llm': self.target_llm,
            'mailbox_name': self.mailbox_name,
            'status': self.status.value,
            'delivery_attempts': self.delivery_attempts,
            'last_attempt': self.last_attempt.isoformat() if self.last_attempt else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OfflineMessage':
        """Create from dictionary"""
        return cls(
            message=Message.from_dict(data['message']),
            queued_at=datetime.fromisoformat(data['queued_at']),
            target_llm=data['target_llm'],
            mailbox_name=data['mailbox_name'],
            status=MessageStatus(data.get('status', 'queued')),
            delivery_attempts=data.get('delivery_attempts', 0),
            last_attempt=datetime.fromisoformat(data['last_attempt']) if data.get('last_attempt') else None,
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
        )


@dataclass
class MessageFilter:
    """Enhanced message filtering criteria"""
    sender_id: Optional[LLMID] = None
    content_type: Optional[ContentType] = None
    priority: Optional[Priority] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    start_message_id: Optional[MessageID] = None
    end_message_id: Optional[MessageID] = None
    tags: Optional[List[str]] = None
    unread_only: bool = False
    read_only: bool = False
    status: Optional[MessageStatus] = None
    max_age_hours: Optional[int] = None
    
    def matches_message(self, message: Message, read_status: bool = False) -> bool:
        """Check if message matches filter criteria"""
        # Sender filter
        if self.sender_id and message.sender_id != self.sender_id:
            return False
        
        # Content type filter
        if self.content_type and message.content_type != self.content_type:
            return False
        
        # Priority filter
        if self.priority and message.routing_info.priority != self.priority:
            return False
        
        # Time-based filters
        if self.start_time and message.timestamp < self.start_time:
            return False
        
        if self.end_time and message.timestamp > self.end_time:
            return False
        
        # Age filter
        if self.max_age_hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.max_age_hours)
            if message.timestamp < cutoff_time:
                return False
        
        # Read status filters
        if self.unread_only and read_status:
            return False
        
        if self.read_only and not read_status:
            return False
        
        # Tags filter
        if self.tags:
            message_tags = message.metadata.get('tags', [])
            if not all(tag in message_tags for tag in self.tags):
                return False
        
        return True
    
    def matches_offline_message(self, offline_msg: OfflineMessage, read_status: bool = False) -> bool:
        """Check if offline message matches filter criteria"""
        # Status filter
        if self.status and offline_msg.status != self.status:
            return False
        
        # Check message-level filters
        return self.matches_message(offline_msg.message, read_status)


@dataclass
class ReadStatus:
    """Message read status tracking"""
    message_id: MessageID
    llm_id: LLMID
    read_at: datetime
    mailbox_name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            'message_id': self.message_id,
            'llm_id': self.llm_id,
            'read_at': self.read_at.isoformat(),
            'mailbox_name': self.mailbox_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReadStatus':
        """Create from dictionary"""
        return cls(
            message_id=data['message_id'],
            llm_id=data['llm_id'],
            read_at=datetime.fromisoformat(data['read_at']),
            mailbox_name=data['mailbox_name']
        )


class OfflineMessageHandler:
    """
    Handles offline message queuing, delivery, and read status tracking.
    
    Redis Key Patterns:
    - offline_queue:{llm_id} - Sorted set of queued message IDs by timestamp
    - offline_message:{message_id}:{llm_id} - Hash containing offline message data
    - read_status:{llm_id}:{mailbox}:{message_id} - Hash containing read status
    - llm_read_index:{llm_id} - Set of read message IDs for quick lookup
    - message_readers:{message_id} - Set of LLM IDs that have read the message
    """
    
    def __init__(self, redis_ops: RedisOperations, mailbox_storage: MailboxStorage):
        self.redis_ops = redis_ops
        self.mailbox_storage = mailbox_storage
        self._initialized = False
        
        # Configuration
        self.max_queue_size = 10000  # Maximum queued messages per LLM
        self.default_message_ttl = 7 * 24 * 3600  # 7 days in seconds
        self.cleanup_interval = 3600  # 1 hour
        self.max_delivery_attempts = 3
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self) -> None:
        """Initialize offline message handler"""
        if self._initialized:
            return
        
        logger.info("Initializing offline message handler")
        
        if not self.redis_ops.is_initialized:
            await self.redis_ops.initialize()
        
        if not self.mailbox_storage.is_initialized:
            await self.mailbox_storage.initialize()
        
        self._initialized = True
        logger.info("Offline message handler initialized")
    
    async def start(self) -> None:
        """Start background tasks"""
        if self._running:
            return
        
        if not self._initialized:
            await self.initialize()
        
        self._running = True
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Offline message handler started")
    
    async def stop(self) -> None:
        """Stop background tasks"""
        if not self._running:
            return
        
        logger.info("Stopping offline message handler")
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Offline message handler stopped")
    
    async def close(self) -> None:
        """Close offline message handler"""
        await self.stop()
        self._initialized = False
        logger.info("Offline message handler closed")
    
    # Message Queuing for Offline Subscribers
    
    async def queue_message_for_offline_llm(self, 
                                          message: Message, 
                                          target_llm: LLMID,
                                          mailbox_name: str,
                                          ttl_seconds: Optional[int] = None) -> bool:
        """
        Queue a message for an offline LLM.
        
        Args:
            message: Message to queue
            target_llm: Target LLM ID
            mailbox_name: Mailbox name
            ttl_seconds: Message TTL in seconds (default: 7 days)
            
        Returns:
            bool: True if queued successfully
        """
        logger.debug(f"Queuing message {message.id} for offline LLM {target_llm}")
        
        # Check queue size limit
        queue_key = f"offline_queue:{target_llm}"
        current_size = await self.redis_ops.zcard(queue_key)
        
        if current_size >= self.max_queue_size:
            # Remove oldest message to make space
            oldest_messages = await self.redis_ops.zrange(queue_key, 0, 0)
            if oldest_messages:
                oldest_id = oldest_messages[0]
                await self._remove_queued_message(target_llm, oldest_id)
                logger.warning(f"Queue full for LLM {target_llm}, removed oldest message {oldest_id}")
        
        # Create offline message
        ttl = ttl_seconds or self.default_message_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        offline_msg = OfflineMessage(
            message=message,
            queued_at=datetime.utcnow(),
            target_llm=target_llm,
            mailbox_name=mailbox_name,
            expires_at=expires_at
        )
        
        # Store offline message data
        offline_key = f"offline_message:{message.id}:{target_llm}"
        await self.redis_ops.hset(offline_key, offline_msg.to_dict())
        
        # Set TTL on the offline message
        await self.redis_ops.expire(offline_key, ttl)
        
        # Add to queue with timestamp as score
        timestamp_score = offline_msg.queued_at.timestamp()
        await self.redis_ops.zadd(queue_key, {message.id: timestamp_score})
        
        logger.debug(f"Message {message.id} queued for offline LLM {target_llm}")
        return True
    
    async def get_queued_messages(self, 
                                llm_id: LLMID,
                                limit: int = 50,
                                offset: int = 0,
                                message_filter: Optional[MessageFilter] = None) -> List[OfflineMessage]:
        """
        Get queued messages for an LLM.
        
        Args:
            llm_id: LLM ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            message_filter: Optional filtering criteria
            
        Returns:
            List of offline messages
        """
        queue_key = f"offline_queue:{llm_id}"
        
        # Get message IDs from queue (newest first)
        message_ids = await self.redis_ops.zrevrange(queue_key, offset, offset + limit - 1)
        
        if not message_ids:
            return []
        
        # Retrieve offline message data
        offline_messages = []
        for message_id in message_ids:
            offline_key = f"offline_message:{message_id}:{llm_id}"
            data = await self.redis_ops.hgetall(offline_key)
            
            if not data:
                # Clean up orphaned queue entry
                await self.redis_ops.zrem(queue_key, message_id)
                continue
            
            try:
                offline_msg = OfflineMessage.from_dict(data)
                
                # Apply filters
                if message_filter:
                    # Check if message is read
                    is_read = await self.is_message_read(offline_msg.mailbox_name, message_id, llm_id)
                    
                    if not message_filter.matches_offline_message(offline_msg, is_read):
                        continue
                
                offline_messages.append(offline_msg)
                
            except Exception as e:
                logger.warning(f"Failed to deserialize offline message {message_id}: {e}")
                continue
        
        return offline_messages
    
    async def get_queued_message_count(self, llm_id: LLMID) -> int:
        """Get count of queued messages for an LLM"""
        queue_key = f"offline_queue:{llm_id}"
        return await self.redis_ops.zcard(queue_key)
    
    async def mark_message_delivered(self, message_id: MessageID, llm_id: LLMID) -> bool:
        """
        Mark a queued message as delivered.
        
        Args:
            message_id: Message ID
            llm_id: LLM ID
            
        Returns:
            bool: True if marked successfully
        """
        offline_key = f"offline_message:{message_id}:{llm_id}"
        
        # Check if offline message exists
        if not await self.redis_ops.exists(offline_key):
            logger.warning(f"Offline message {message_id} for LLM {llm_id} not found")
            return False
        
        # Update status
        updates = {
            'status': MessageStatus.DELIVERED.value,
            'last_attempt': datetime.utcnow().isoformat()
        }
        
        await self.redis_ops.hset(offline_key, updates)
        
        logger.debug(f"Marked message {message_id} as delivered to LLM {llm_id}")
        return True
    
    async def remove_delivered_messages(self, llm_id: LLMID, message_ids: List[MessageID]) -> int:
        """
        Remove delivered messages from the offline queue.
        
        Args:
            llm_id: LLM ID
            message_ids: List of message IDs to remove
            
        Returns:
            int: Number of messages removed
        """
        if not message_ids:
            return 0
        
        removed_count = 0
        
        for message_id in message_ids:
            if await self._remove_queued_message(llm_id, message_id):
                removed_count += 1
        
        logger.debug(f"Removed {removed_count} delivered messages from LLM {llm_id} queue")
        return removed_count
    
    # Message Read/Unread Status System
    
    async def mark_message_read(self, 
                              mailbox_name: str, 
                              message_id: MessageID, 
                              llm_id: LLMID) -> bool:
        """
        Mark a message as read by an LLM.
        
        Args:
            mailbox_name: Mailbox name
            message_id: Message ID
            llm_id: LLM ID that read the message
            
        Returns:
            bool: True if marked successfully
        """
        logger.debug(f"Marking message {message_id} as read by LLM {llm_id}")
        
        # Create read status
        read_status = ReadStatus(
            message_id=message_id,
            llm_id=llm_id,
            read_at=datetime.utcnow(),
            mailbox_name=mailbox_name
        )
        
        # Store read status
        read_key = f"read_status:{llm_id}:{mailbox_name}:{message_id}"
        await self.redis_ops.hset(read_key, read_status.to_dict())
        
        # Add to LLM read index for quick lookup
        read_index_key = f"llm_read_index:{llm_id}"
        await self.redis_ops.sadd(read_index_key, message_id)
        
        # Add to message readers index
        readers_key = f"message_readers:{message_id}"
        await self.redis_ops.sadd(readers_key, llm_id)
        
        # Update offline message status if it exists
        offline_key = f"offline_message:{message_id}:{llm_id}"
        if await self.redis_ops.exists(offline_key):
            await self.redis_ops.hset(offline_key, {'status': MessageStatus.READ.value})
        
        logger.debug(f"Message {message_id} marked as read by LLM {llm_id}")
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
        # Quick check using read index
        read_index_key = f"llm_read_index:{llm_id}"
        return await self.redis_ops.sismember(read_index_key, message_id)
    
    async def get_read_status(self, mailbox_name: str, message_id: MessageID, llm_id: LLMID) -> Optional[ReadStatus]:
        """
        Get detailed read status for a message.
        
        Args:
            mailbox_name: Mailbox name
            message_id: Message ID
            llm_id: LLM ID
            
        Returns:
            ReadStatus or None if not read
        """
        read_key = f"read_status:{llm_id}:{mailbox_name}:{message_id}"
        data = await self.redis_ops.hgetall(read_key)
        
        if not data:
            return None
        
        return ReadStatus.from_dict(data)
    
    async def get_message_readers(self, message_id: MessageID) -> List[LLMID]:
        """
        Get list of LLMs that have read a message.
        
        Args:
            message_id: Message ID
            
        Returns:
            List of LLM IDs that have read the message
        """
        readers_key = f"message_readers:{message_id}"
        return await self.redis_ops.smembers(readers_key)
    
    async def get_unread_count(self, mailbox_name: str, llm_id: LLMID) -> int:
        """
        Get count of unread messages for an LLM in a mailbox.
        
        Args:
            mailbox_name: Mailbox name
            llm_id: LLM ID
            
        Returns:
            int: Number of unread messages
        """
        # Get all messages in mailbox
        messages_page = await self.mailbox_storage.get_messages(
            mailbox_name=mailbox_name,
            limit=10000  # Large limit to get all messages
        )
        
        unread_count = 0
        for message in messages_page.messages:
            if not await self.is_message_read(mailbox_name, message.id, llm_id):
                unread_count += 1
        
        return unread_count
    
    async def get_unread_messages(self, 
                                mailbox_name: str, 
                                llm_id: LLMID,
                                limit: int = 50,
                                offset: int = 0) -> List[Message]:
        """
        Get unread messages for an LLM in a mailbox.
        
        Args:
            mailbox_name: Mailbox name
            llm_id: LLM ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            
        Returns:
            List of unread messages
        """
        # Get messages from mailbox
        messages_page = await self.mailbox_storage.get_messages(
            mailbox_name=mailbox_name,
            limit=limit * 2,  # Get more to account for filtering
            offset=offset
        )
        
        unread_messages = []
        for message in messages_page.messages:
            if not await self.is_message_read(mailbox_name, message.id, llm_id):
                unread_messages.append(message)
                
                if len(unread_messages) >= limit:
                    break
        
        return unread_messages
    
    # Time-based and ID-based Message Filtering
    
    async def get_messages_by_time_range(self, 
                                       mailbox_name: str,
                                       start_time: datetime,
                                       end_time: datetime,
                                       llm_id: Optional[LLMID] = None,
                                       limit: int = 50) -> List[Message]:
        """
        Get messages within a specific time range.
        
        Args:
            mailbox_name: Mailbox name
            start_time: Start of time range
            end_time: End of time range
            llm_id: Optional LLM ID for read status filtering
            limit: Maximum number of messages to return
            
        Returns:
            List of messages in time range
        """
        # Create time-based filter
        message_filter = MessageFilter(
            start_time=start_time,
            end_time=end_time
        )
        
        # Get messages from mailbox
        messages_page = await self.mailbox_storage.get_messages(
            mailbox_name=mailbox_name,
            limit=limit * 2,  # Get more to account for filtering
            message_filter=message_filter
        )
        
        filtered_messages = []
        for message in messages_page.messages:
            # Apply additional filtering if LLM ID provided
            if llm_id:
                is_read = await self.is_message_read(mailbox_name, message.id, llm_id)
                if not message_filter.matches_message(message, is_read):
                    continue
            
            filtered_messages.append(message)
            
            if len(filtered_messages) >= limit:
                break
        
        return filtered_messages
    
    async def get_messages_by_id_range(self, 
                                     mailbox_name: str,
                                     start_message_id: Optional[MessageID] = None,
                                     end_message_id: Optional[MessageID] = None,
                                     llm_id: Optional[LLMID] = None,
                                     limit: int = 50) -> List[Message]:
        """
        Get messages within a specific ID range.
        
        Args:
            mailbox_name: Mailbox name
            start_message_id: Start message ID (inclusive)
            end_message_id: End message ID (inclusive)
            llm_id: Optional LLM ID for read status filtering
            limit: Maximum number of messages to return
            
        Returns:
            List of messages in ID range
        """
        # Get all messages from mailbox
        messages_page = await self.mailbox_storage.get_messages(
            mailbox_name=mailbox_name,
            limit=limit * 2  # Get more to account for filtering
        )
        
        filtered_messages = []
        for message in messages_page.messages:
            # Apply ID range filtering
            if start_message_id and message.id < start_message_id:
                continue
            
            if end_message_id and message.id > end_message_id:
                continue
            
            # Apply read status filtering if LLM ID provided
            if llm_id:
                is_read = await self.is_message_read(mailbox_name, message.id, llm_id)
                # Additional filtering can be applied here if needed
            
            filtered_messages.append(message)
            
            if len(filtered_messages) >= limit:
                break
        
        return filtered_messages
    
    async def get_messages_since_last_read(self, 
                                         mailbox_name: str, 
                                         llm_id: LLMID,
                                         limit: int = 50) -> List[Message]:
        """
        Get messages since the last read message for an LLM.
        
        Args:
            mailbox_name: Mailbox name
            llm_id: LLM ID
            limit: Maximum number of messages to return
            
        Returns:
            List of messages since last read
        """
        # Find the most recent read message timestamp
        read_index_key = f"llm_read_index:{llm_id}"
        read_message_ids = await self.redis_ops.smembers(read_index_key)
        
        latest_read_time = None
        if read_message_ids:
            # Get timestamps of read messages
            for message_id in read_message_ids:
                read_key = f"read_status:{llm_id}:{mailbox_name}:{message_id}"
                read_data = await self.redis_ops.hgetall(read_key)
                
                if read_data and 'read_at' in read_data:
                    read_time = datetime.fromisoformat(read_data['read_at'])
                    if latest_read_time is None or read_time > latest_read_time:
                        latest_read_time = read_time
        
        # Get messages after the latest read time
        if latest_read_time:
            return await self.get_messages_by_time_range(
                mailbox_name=mailbox_name,
                start_time=latest_read_time,
                end_time=datetime.utcnow(),
                llm_id=llm_id,
                limit=limit
            )
        else:
            # No read messages, return all unread messages
            return await self.get_unread_messages(mailbox_name, llm_id, limit)
    
    # Helper Methods
    
    async def _remove_queued_message(self, llm_id: LLMID, message_id: MessageID) -> bool:
        """Remove a message from the offline queue"""
        queue_key = f"offline_queue:{llm_id}"
        offline_key = f"offline_message:{message_id}:{llm_id}"
        
        # Remove from queue and delete offline message data
        removed_from_queue = await self.redis_ops.zrem(queue_key, message_id)
        await self.redis_ops.delete(offline_key)
        
        return removed_from_queue > 0
    
    async def _cleanup_loop(self) -> None:
        """Background task for cleaning up expired messages"""
        logger.info("Starting offline message cleanup loop")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self._running:
                    break
                
                await self._cleanup_expired_messages()
                await self._cleanup_old_read_status()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
        
        logger.info("Offline message cleanup loop stopped")
    
    async def _cleanup_expired_messages(self) -> None:
        """Clean up expired offline messages"""
        try:
            # Find all offline queue keys
            queue_pattern = "offline_queue:*"
            queue_keys = await self.redis_ops.keys(queue_pattern)
            
            total_cleaned = 0
            
            for queue_key in queue_keys:
                llm_id = queue_key.split(':', 2)[2]  # Extract LLM ID from key
                
                # Get all message IDs in queue
                message_ids = await self.redis_ops.zrange(queue_key, 0, -1)
                
                for message_id in message_ids:
                    offline_key = f"offline_message:{message_id}:{llm_id}"
                    
                    # Check if message exists and is expired
                    ttl = await self.redis_ops.ttl(offline_key)
                    
                    if ttl == -2:  # Key doesn't exist
                        # Remove from queue
                        await self.redis_ops.zrem(queue_key, message_id)
                        total_cleaned += 1
                    elif ttl == 0:  # Key expired
                        # Remove from queue and delete key
                        await self.redis_ops.zrem(queue_key, message_id)
                        await self.redis_ops.delete(offline_key)
                        total_cleaned += 1
            
            if total_cleaned > 0:
                logger.info(f"Cleaned up {total_cleaned} expired offline messages")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired messages: {e}")
    
    async def _cleanup_old_read_status(self) -> None:
        """Clean up old read status entries"""
        try:
            # Clean up read status older than 30 days
            cutoff_time = datetime.utcnow() - timedelta(days=30)
            
            # Find all read status keys
            read_pattern = "read_status:*"
            read_keys = await self.redis_ops.keys(read_pattern)
            
            cleaned_count = 0
            
            for read_key in read_keys:
                data = await self.redis_ops.hgetall(read_key)
                
                if data and 'read_at' in data:
                    read_time = datetime.fromisoformat(data['read_at'])
                    
                    if read_time < cutoff_time:
                        # Extract IDs from key
                        key_parts = read_key.split(':')
                        if len(key_parts) >= 4:
                            llm_id = key_parts[1]
                            message_id = key_parts[3]
                            
                            # Remove from indices
                            read_index_key = f"llm_read_index:{llm_id}"
                            readers_key = f"message_readers:{message_id}"
                            
                            await self.redis_ops.srem(read_index_key, message_id)
                            await self.redis_ops.srem(readers_key, llm_id)
                            
                            # Delete read status
                            await self.redis_ops.delete(read_key)
                            cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old read status entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up old read status: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get offline message handler statistics"""
        try:
            # Count total queued messages
            queue_pattern = "offline_queue:*"
            queue_keys = await self.redis_ops.keys(queue_pattern)
            
            total_queued = 0
            llm_queue_counts = {}
            
            for queue_key in queue_keys:
                key_parts = queue_key.split(':')
                if len(key_parts) >= 3:
                    llm_id = ':'.join(key_parts[2:])  # Handle LLM IDs with colons
                    count = await self.redis_ops.zcard(queue_key)
                    llm_queue_counts[llm_id] = count
                    total_queued += count
            
            # Count total read status entries
            read_pattern = "llm_read_index:*"
            read_keys = await self.redis_ops.keys(read_pattern)
            
            total_read_entries = 0
            for read_key in read_keys:
                count = await self.redis_ops.scard(read_key)
                total_read_entries += count
            
            return {
                "total_queued_messages": total_queued,
                "active_llm_queues": len(queue_keys),
                "llm_queue_counts": llm_queue_counts,
                "total_read_entries": total_read_entries,
                "running": self._running,
                "initialized": self._initialized
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "error": str(e),
                "running": self._running,
                "initialized": self._initialized
            }
    
    @property
    def is_initialized(self) -> bool:
        """Check if offline message handler is initialized"""
        return self._initialized