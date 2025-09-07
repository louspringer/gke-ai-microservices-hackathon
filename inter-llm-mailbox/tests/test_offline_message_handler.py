"""
Tests for Offline Message Handler

Tests offline message queuing, read/unread status tracking, and message filtering.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import List

from src.core.offline_message_handler import (
    OfflineMessageHandler, 
    OfflineMessage, 
    MessageFilter, 
    MessageStatus,
    ReadStatus
)
from src.core.redis_operations import RedisOperations
from src.core.redis_manager import RedisConfig
from src.core.mailbox_storage import MailboxStorage
from src.models.message import Message, RoutingInfo
from src.models.enums import AddressingMode, ContentType, Priority


@pytest.fixture
async def redis_ops():
    """Create Redis operations instance for testing"""
    redis_config = RedisConfig()  # Use default configuration
    redis_ops = RedisOperations(redis_config)
    await redis_ops.initialize()
    
    # Clean up any existing test data
    async with redis_ops.connection_manager.get_connection() as redis_conn:
        await redis_conn.flushdb()
    
    yield redis_ops
    
    # Cleanup
    async with redis_ops.connection_manager.get_connection() as redis_conn:
        await redis_conn.flushdb()
    await redis_ops.close()


@pytest.fixture
async def mailbox_storage(redis_ops):
    """Create mailbox storage instance for testing"""
    storage = MailboxStorage(redis_ops)
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.fixture
async def offline_handler(redis_ops, mailbox_storage):
    """Create offline message handler for testing"""
    handler = OfflineMessageHandler(redis_ops, mailbox_storage)
    await handler.initialize()
    await handler.start()
    
    yield handler
    
    await handler.stop()
    await handler.close()


@pytest.fixture
def sample_message():
    """Create a sample message for testing"""
    routing_info = RoutingInfo(
        addressing_mode=AddressingMode.DIRECT,
        target="test_mailbox",
        priority=Priority.NORMAL
    )
    
    return Message.create(
        sender_id="test_sender",
        content="Test message content",
        content_type=ContentType.TEXT,
        routing_info=routing_info,
        metadata={"test": "data"}
    )


@pytest.fixture
def sample_messages():
    """Create multiple sample messages for testing"""
    messages = []
    
    for i in range(5):
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test_mailbox",
            priority=Priority.NORMAL if i % 2 == 0 else Priority.HIGH
        )
        
        message = Message.create(
            sender_id=f"sender_{i}",
            content=f"Test message {i}",
            content_type=ContentType.TEXT,
            routing_info=routing_info,
            metadata={"index": i, "tags": [f"tag_{i}"]}
        )
        
        # Adjust timestamps to create a sequence
        message.timestamp = datetime.utcnow() - timedelta(minutes=5-i)
        messages.append(message)
    
    return messages


class TestOfflineMessageQueuing:
    """Test offline message queuing functionality"""
    
    async def test_queue_message_for_offline_llm(self, offline_handler, sample_message):
        """Test queuing a message for an offline LLM"""
        llm_id = "offline_llm_1"
        mailbox_name = "test_mailbox"
        
        # Queue message
        result = await offline_handler.queue_message_for_offline_llm(
            message=sample_message,
            target_llm=llm_id,
            mailbox_name=mailbox_name
        )
        
        assert result is True
        
        # Verify message is queued
        queued_count = await offline_handler.get_queued_message_count(llm_id)
        assert queued_count == 1
        
        # Verify message data
        queued_messages = await offline_handler.get_queued_messages(llm_id)
        assert len(queued_messages) == 1
        
        offline_msg = queued_messages[0]
        assert offline_msg.message.id == sample_message.id
        assert offline_msg.target_llm == llm_id
        assert offline_msg.mailbox_name == mailbox_name
        assert offline_msg.status == MessageStatus.QUEUED
    
    async def test_queue_multiple_messages(self, offline_handler, sample_messages):
        """Test queuing multiple messages"""
        llm_id = "offline_llm_2"
        mailbox_name = "test_mailbox"
        
        # Queue all messages
        for message in sample_messages:
            await offline_handler.queue_message_for_offline_llm(
                message=message,
                target_llm=llm_id,
                mailbox_name=mailbox_name
            )
        
        # Verify all messages are queued
        queued_count = await offline_handler.get_queued_message_count(llm_id)
        assert queued_count == len(sample_messages)
        
        # Verify messages are ordered by timestamp (newest first)
        queued_messages = await offline_handler.get_queued_messages(llm_id)
        assert len(queued_messages) == len(sample_messages)
        
        # Should be in reverse chronological order (newest first)
        for i in range(len(queued_messages) - 1):
            assert queued_messages[i].queued_at >= queued_messages[i + 1].queued_at
    
    async def test_queue_size_limit(self, offline_handler, redis_ops):
        """Test queue size limit enforcement"""
        llm_id = "offline_llm_3"
        mailbox_name = "test_mailbox"
        
        # Set a small queue size limit for testing
        offline_handler.max_queue_size = 3
        
        # Create and queue more messages than the limit
        messages = []
        for i in range(5):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target=mailbox_name,
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id=f"sender_{i}",
                content=f"Message {i}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            messages.append(message)
            
            await offline_handler.queue_message_for_offline_llm(
                message=message,
                target_llm=llm_id,
                mailbox_name=mailbox_name
            )
        
        # Verify queue size is limited
        queued_count = await offline_handler.get_queued_message_count(llm_id)
        assert queued_count == 3  # Should be limited to max_queue_size
        
        # Verify newest messages are kept
        queued_messages = await offline_handler.get_queued_messages(llm_id)
        queued_ids = [msg.message.id for msg in queued_messages]
        
        # Should contain the last 3 messages
        expected_ids = [msg.id for msg in messages[-3:]]
        for expected_id in expected_ids:
            assert expected_id in queued_ids
    
    async def test_mark_message_delivered(self, offline_handler, sample_message):
        """Test marking a message as delivered"""
        llm_id = "offline_llm_4"
        mailbox_name = "test_mailbox"
        
        # Queue message
        await offline_handler.queue_message_for_offline_llm(
            message=sample_message,
            target_llm=llm_id,
            mailbox_name=mailbox_name
        )
        
        # Mark as delivered
        result = await offline_handler.mark_message_delivered(sample_message.id, llm_id)
        assert result is True
        
        # Verify status is updated
        queued_messages = await offline_handler.get_queued_messages(llm_id)
        assert len(queued_messages) == 1
        assert queued_messages[0].status == MessageStatus.DELIVERED
    
    async def test_remove_delivered_messages(self, offline_handler, sample_messages):
        """Test removing delivered messages from queue"""
        llm_id = "offline_llm_5"
        mailbox_name = "test_mailbox"
        
        # Queue messages
        for message in sample_messages:
            await offline_handler.queue_message_for_offline_llm(
                message=message,
                target_llm=llm_id,
                mailbox_name=mailbox_name
            )
        
        # Mark some as delivered
        delivered_ids = [msg.id for msg in sample_messages[:2]]
        for message_id in delivered_ids:
            await offline_handler.mark_message_delivered(message_id, llm_id)
        
        # Remove delivered messages
        removed_count = await offline_handler.remove_delivered_messages(llm_id, delivered_ids)
        assert removed_count == 2
        
        # Verify remaining messages
        remaining_count = await offline_handler.get_queued_message_count(llm_id)
        assert remaining_count == len(sample_messages) - 2


class TestMessageReadStatus:
    """Test message read/unread status tracking"""
    
    async def test_mark_message_read(self, offline_handler, mailbox_storage, sample_message):
        """Test marking a message as read"""
        llm_id = "reader_llm_1"
        mailbox_name = "test_mailbox"
        
        # Store message in mailbox first
        await mailbox_storage.store_message(mailbox_name, sample_message)
        
        # Mark as read
        result = await offline_handler.mark_message_read(
            mailbox_name=mailbox_name,
            message_id=sample_message.id,
            llm_id=llm_id
        )
        assert result is True
        
        # Verify read status
        is_read = await offline_handler.is_message_read(mailbox_name, sample_message.id, llm_id)
        assert is_read is True
        
        # Verify detailed read status
        read_status = await offline_handler.get_read_status(mailbox_name, sample_message.id, llm_id)
        assert read_status is not None
        assert read_status.message_id == sample_message.id
        assert read_status.llm_id == llm_id
        assert read_status.mailbox_name == mailbox_name
        assert isinstance(read_status.read_at, datetime)
    
    async def test_message_readers_tracking(self, offline_handler, mailbox_storage, sample_message):
        """Test tracking multiple readers for a message"""
        mailbox_name = "test_mailbox"
        llm_ids = ["reader_1", "reader_2", "reader_3"]
        
        # Store message in mailbox
        await mailbox_storage.store_message(mailbox_name, sample_message)
        
        # Mark as read by multiple LLMs
        for llm_id in llm_ids:
            await offline_handler.mark_message_read(
                mailbox_name=mailbox_name,
                message_id=sample_message.id,
                llm_id=llm_id
            )
        
        # Verify all readers are tracked
        readers = await offline_handler.get_message_readers(sample_message.id)
        assert len(readers) == len(llm_ids)
        
        for llm_id in llm_ids:
            assert llm_id in readers
    
    async def test_unread_count(self, offline_handler, mailbox_storage, sample_messages):
        """Test counting unread messages"""
        llm_id = "reader_llm_2"
        mailbox_name = "test_mailbox"
        
        # Store messages in mailbox
        for message in sample_messages:
            await mailbox_storage.store_message(mailbox_name, message)
        
        # Initially all messages should be unread
        unread_count = await offline_handler.get_unread_count(mailbox_name, llm_id)
        assert unread_count == len(sample_messages)
        
        # Mark some messages as read
        read_count = 2
        for i in range(read_count):
            await offline_handler.mark_message_read(
                mailbox_name=mailbox_name,
                message_id=sample_messages[i].id,
                llm_id=llm_id
            )
        
        # Verify unread count is updated
        unread_count = await offline_handler.get_unread_count(mailbox_name, llm_id)
        assert unread_count == len(sample_messages) - read_count
    
    async def test_get_unread_messages(self, offline_handler, mailbox_storage, sample_messages):
        """Test retrieving unread messages"""
        llm_id = "reader_llm_3"
        mailbox_name = "test_mailbox"
        
        # Store messages in mailbox
        for message in sample_messages:
            await mailbox_storage.store_message(mailbox_name, message)
        
        # Mark some messages as read
        read_indices = [0, 2]  # Mark first and third messages as read
        for i in read_indices:
            await offline_handler.mark_message_read(
                mailbox_name=mailbox_name,
                message_id=sample_messages[i].id,
                llm_id=llm_id
            )
        
        # Get unread messages
        unread_messages = await offline_handler.get_unread_messages(mailbox_name, llm_id)
        
        # Verify only unread messages are returned
        expected_unread_count = len(sample_messages) - len(read_indices)
        assert len(unread_messages) == expected_unread_count
        
        # Verify read messages are not included
        unread_ids = [msg.id for msg in unread_messages]
        for i in read_indices:
            assert sample_messages[i].id not in unread_ids


class TestMessageFiltering:
    """Test time-based and ID-based message filtering"""
    
    async def test_time_based_filtering(self, offline_handler, mailbox_storage, sample_messages):
        """Test filtering messages by time range"""
        mailbox_name = "test_mailbox"
        
        # Store messages with different timestamps
        base_time = datetime.utcnow()
        for i, message in enumerate(sample_messages):
            message.timestamp = base_time - timedelta(hours=i)
            await mailbox_storage.store_message(mailbox_name, message)
        
        # Filter messages from last 2 hours
        start_time = base_time - timedelta(hours=2)
        end_time = base_time + timedelta(hours=1)
        
        filtered_messages = await offline_handler.get_messages_by_time_range(
            mailbox_name=mailbox_name,
            start_time=start_time,
            end_time=end_time
        )
        
        # Should include messages from hours 0, 1, and 2
        assert len(filtered_messages) == 3
        
        # Verify all returned messages are within time range
        for message in filtered_messages:
            assert start_time <= message.timestamp <= end_time
    
    async def test_id_based_filtering(self, offline_handler, mailbox_storage, sample_messages):
        """Test filtering messages by ID range"""
        mailbox_name = "test_mailbox"
        
        # Store messages
        for message in sample_messages:
            await mailbox_storage.store_message(mailbox_name, message)
        
        # Sort message IDs for range testing
        sorted_ids = sorted([msg.id for msg in sample_messages])
        
        # Filter by ID range (middle 3 messages)
        start_id = sorted_ids[1]
        end_id = sorted_ids[3]
        
        filtered_messages = await offline_handler.get_messages_by_id_range(
            mailbox_name=mailbox_name,
            start_message_id=start_id,
            end_message_id=end_id
        )
        
        # Verify messages are within ID range
        filtered_ids = [msg.id for msg in filtered_messages]
        for message_id in filtered_ids:
            assert start_id <= message_id <= end_id
    
    async def test_messages_since_last_read(self, offline_handler, mailbox_storage, sample_messages):
        """Test getting messages since last read"""
        llm_id = "reader_llm_4"
        mailbox_name = "test_mailbox"
        
        # Store messages with sequential timestamps
        base_time = datetime.utcnow()
        for i, message in enumerate(sample_messages):
            message.timestamp = base_time - timedelta(minutes=len(sample_messages) - i)
            await mailbox_storage.store_message(mailbox_name, message)
        
        # Mark first two messages as read
        for i in range(2):
            await offline_handler.mark_message_read(
                mailbox_name=mailbox_name,
                message_id=sample_messages[i].id,
                llm_id=llm_id
            )
        
        # Get messages since last read
        new_messages = await offline_handler.get_messages_since_last_read(
            mailbox_name=mailbox_name,
            llm_id=llm_id
        )
        
        # Should return messages after the last read message
        # Note: This might include some overlap depending on implementation
        assert len(new_messages) >= len(sample_messages) - 2
    
    async def test_message_filter_with_queued_messages(self, offline_handler, sample_messages):
        """Test filtering queued messages"""
        llm_id = "offline_llm_filter"
        mailbox_name = "test_mailbox"
        
        # Queue messages with different priorities
        for message in sample_messages:
            await offline_handler.queue_message_for_offline_llm(
                message=message,
                target_llm=llm_id,
                mailbox_name=mailbox_name
            )
        
        # Filter by priority
        high_priority_filter = MessageFilter(priority=Priority.HIGH)
        filtered_messages = await offline_handler.get_queued_messages(
            llm_id=llm_id,
            message_filter=high_priority_filter
        )
        
        # Verify only high priority messages are returned
        for offline_msg in filtered_messages:
            assert offline_msg.message.routing_info.priority == Priority.HIGH
    
    async def test_unread_only_filter(self, offline_handler, mailbox_storage, sample_messages):
        """Test filtering for unread messages only"""
        llm_id = "reader_llm_5"
        mailbox_name = "test_mailbox"
        
        # Store messages
        for message in sample_messages:
            await mailbox_storage.store_message(mailbox_name, message)
        
        # Mark some messages as read
        for i in range(2):
            await offline_handler.mark_message_read(
                mailbox_name=mailbox_name,
                message_id=sample_messages[i].id,
                llm_id=llm_id
            )
        
        # Create filter for unread messages only
        unread_filter = MessageFilter(unread_only=True)
        
        # This would be used in a more complete implementation
        # For now, we test the filter logic directly
        read_status_map = {}
        for message in sample_messages:
            is_read = await offline_handler.is_message_read(mailbox_name, message.id, llm_id)
            read_status_map[message.id] = is_read
        
        # Apply filter
        matching_messages = []
        for message in sample_messages:
            is_read = read_status_map[message.id]
            if unread_filter.matches_message(message, is_read):
                matching_messages.append(message)
        
        # Should only include unread messages
        assert len(matching_messages) == len(sample_messages) - 2


class TestOfflineMessageIntegration:
    """Integration tests for offline message handling"""
    
    async def test_complete_offline_workflow(self, offline_handler, mailbox_storage, sample_messages):
        """Test complete offline message workflow"""
        llm_id = "integration_llm"
        mailbox_name = "integration_mailbox"
        
        # Step 1: Queue messages for offline LLM
        for message in sample_messages:
            await offline_handler.queue_message_for_offline_llm(
                message=message,
                target_llm=llm_id,
                mailbox_name=mailbox_name
            )
        
        # Verify messages are queued
        queued_count = await offline_handler.get_queued_message_count(llm_id)
        assert queued_count == len(sample_messages)
        
        # Step 2: Simulate LLM coming online and receiving messages
        queued_messages = await offline_handler.get_queued_messages(llm_id)
        delivered_ids = []
        
        for offline_msg in queued_messages:
            # Mark as delivered
            await offline_handler.mark_message_delivered(offline_msg.message.id, llm_id)
            delivered_ids.append(offline_msg.message.id)
            
            # Store in mailbox for read tracking
            await mailbox_storage.store_message(mailbox_name, offline_msg.message)
        
        # Step 3: Remove delivered messages from queue
        removed_count = await offline_handler.remove_delivered_messages(llm_id, delivered_ids)
        assert removed_count == len(sample_messages)
        
        # Verify queue is empty
        final_count = await offline_handler.get_queued_message_count(llm_id)
        assert final_count == 0
        
        # Step 4: Mark some messages as read
        read_count = 2
        for i in range(read_count):
            await offline_handler.mark_message_read(
                mailbox_name=mailbox_name,
                message_id=sample_messages[i].id,
                llm_id=llm_id
            )
        
        # Step 5: Verify read/unread counts
        unread_count = await offline_handler.get_unread_count(mailbox_name, llm_id)
        assert unread_count == len(sample_messages) - read_count
        
        # Step 6: Get unread messages
        unread_messages = await offline_handler.get_unread_messages(mailbox_name, llm_id)
        assert len(unread_messages) == len(sample_messages) - read_count
    
    async def test_statistics(self, offline_handler, sample_messages):
        """Test getting handler statistics"""
        llm_id = "stats_llm"
        mailbox_name = "stats_mailbox"
        
        # Queue some messages
        for message in sample_messages[:3]:
            await offline_handler.queue_message_for_offline_llm(
                message=message,
                target_llm=llm_id,
                mailbox_name=mailbox_name
            )
        
        # Get statistics
        stats = await offline_handler.get_statistics()
        
        assert "total_queued_messages" in stats
        assert "active_llm_queues" in stats
        assert "llm_queue_counts" in stats
        assert "running" in stats
        assert "initialized" in stats
        
        assert stats["total_queued_messages"] >= 3
        assert stats["active_llm_queues"] >= 1
        assert llm_id in stats["llm_queue_counts"]
        assert stats["llm_queue_counts"][llm_id] == 3
        assert stats["running"] is True
        assert stats["initialized"] is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])