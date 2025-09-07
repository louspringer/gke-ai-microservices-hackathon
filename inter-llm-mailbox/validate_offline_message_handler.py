#!/usr/bin/env python3
"""
Validation script for Offline Message Handler

This script validates the offline message handling functionality including:
- Message queuing for offline subscribers
- Message marking system (read/unread status)
- Time-based and ID-based message filtering
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List

from src.core.offline_message_handler import OfflineMessageHandler, MessageFilter
from src.core.redis_operations import RedisOperations
from src.core.redis_manager import RedisConfig
from src.core.mailbox_storage import MailboxStorage
from src.models.message import Message, RoutingInfo
from src.models.enums import AddressingMode, ContentType, Priority


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_test_messages(count: int = 5) -> List[Message]:
    """Create test messages with different properties"""
    messages = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        routing_info = RoutingInfo(
            addressing_mode=AddressingMode.DIRECT,
            target="test_mailbox",
            priority=Priority.HIGH if i % 2 == 0 else Priority.NORMAL
        )
        
        message = Message.create(
            sender_id=f"test_sender_{i}",
            content=f"Test message content {i}",
            content_type=ContentType.TEXT,
            routing_info=routing_info,
            metadata={
                "index": i,
                "tags": [f"tag_{i}", "test"],
                "category": "validation"
            }
        )
        
        # Set different timestamps
        message.timestamp = base_time - timedelta(minutes=count - i)
        messages.append(message)
    
    return messages


async def test_offline_message_queuing(handler: OfflineMessageHandler, messages: List[Message]):
    """Test offline message queuing functionality"""
    logger.info("Testing offline message queuing...")
    
    llm_id = "offline_test_llm"
    mailbox_name = "test_mailbox"
    
    # Queue messages for offline LLM
    for i, message in enumerate(messages):
        result = await handler.queue_message_for_offline_llm(
            message=message,
            target_llm=llm_id,
            mailbox_name=mailbox_name,
            ttl_seconds=3600  # 1 hour TTL
        )
        assert result, f"Failed to queue message {i}"
        logger.info(f"Queued message {i}: {message.id}")
    
    # Verify queue count
    queued_count = await handler.get_queued_message_count(llm_id)
    assert queued_count == len(messages), f"Expected {len(messages)} messages, got {queued_count}"
    logger.info(f"Queue count verified: {queued_count} messages")
    
    # Retrieve queued messages
    queued_messages = await handler.get_queued_messages(llm_id, limit=10)
    assert len(queued_messages) == len(messages), "Mismatch in retrieved message count"
    logger.info(f"Retrieved {len(queued_messages)} queued messages")
    
    # Verify message order (should be newest first)
    for i in range(len(queued_messages) - 1):
        assert queued_messages[i].queued_at >= queued_messages[i + 1].queued_at, \
            "Messages not ordered correctly"
    
    # Mark some messages as delivered
    delivered_count = 2
    delivered_ids = []
    
    for i in range(delivered_count):
        message_id = queued_messages[i].message.id
        result = await handler.mark_message_delivered(message_id, llm_id)
        assert result, f"Failed to mark message {message_id} as delivered"
        delivered_ids.append(message_id)
        logger.info(f"Marked message as delivered: {message_id}")
    
    # Remove delivered messages
    removed_count = await handler.remove_delivered_messages(llm_id, delivered_ids)
    assert removed_count == delivered_count, f"Expected to remove {delivered_count}, removed {removed_count}"
    logger.info(f"Removed {removed_count} delivered messages")
    
    # Verify remaining queue count
    remaining_count = await handler.get_queued_message_count(llm_id)
    expected_remaining = len(messages) - delivered_count
    assert remaining_count == expected_remaining, \
        f"Expected {expected_remaining} remaining messages, got {remaining_count}"
    
    logger.info("✓ Offline message queuing tests passed")


async def test_read_status_tracking(handler: OfflineMessageHandler, 
                                  storage: MailboxStorage, 
                                  messages: List[Message]):
    """Test message read/unread status tracking"""
    logger.info("Testing read status tracking...")
    
    llm_id = "reader_test_llm"
    mailbox_name = "read_test_mailbox"
    
    # Store messages in mailbox
    for message in messages:
        await storage.store_message(mailbox_name, message)
        logger.info(f"Stored message in mailbox: {message.id}")
    
    # Initially all messages should be unread
    unread_count = await handler.get_unread_count(mailbox_name, llm_id)
    assert unread_count == len(messages), f"Expected {len(messages)} unread messages, got {unread_count}"
    logger.info(f"Initial unread count: {unread_count}")
    
    # Mark some messages as read
    read_count = 3
    read_message_ids = []
    
    for i in range(read_count):
        message_id = messages[i].id
        result = await handler.mark_message_read(mailbox_name, message_id, llm_id)
        assert result, f"Failed to mark message {message_id} as read"
        read_message_ids.append(message_id)
        logger.info(f"Marked message as read: {message_id}")
    
    # Verify read status
    for message_id in read_message_ids:
        is_read = await handler.is_message_read(mailbox_name, message_id, llm_id)
        assert is_read, f"Message {message_id} should be marked as read"
        
        # Get detailed read status
        read_status = await handler.get_read_status(mailbox_name, message_id, llm_id)
        assert read_status is not None, f"Read status not found for message {message_id}"
        assert read_status.llm_id == llm_id
        assert read_status.message_id == message_id
        assert isinstance(read_status.read_at, datetime)
    
    # Verify unread count is updated
    updated_unread_count = await handler.get_unread_count(mailbox_name, llm_id)
    expected_unread = len(messages) - read_count
    assert updated_unread_count == expected_unread, \
        f"Expected {expected_unread} unread messages, got {updated_unread_count}"
    logger.info(f"Updated unread count: {updated_unread_count}")
    
    # Get unread messages
    unread_messages = await handler.get_unread_messages(mailbox_name, llm_id, limit=10)
    assert len(unread_messages) == expected_unread, \
        f"Expected {expected_unread} unread messages, got {len(unread_messages)}"
    
    # Verify unread messages don't include read ones
    unread_ids = [msg.id for msg in unread_messages]
    for read_id in read_message_ids:
        assert read_id not in unread_ids, f"Read message {read_id} found in unread list"
    
    # Test message readers tracking
    for message_id in read_message_ids:
        readers = await handler.get_message_readers(message_id)
        assert llm_id in readers, f"LLM {llm_id} not found in readers for message {message_id}"
    
    logger.info("✓ Read status tracking tests passed")


async def test_message_filtering(handler: OfflineMessageHandler, 
                               storage: MailboxStorage, 
                               messages: List[Message]):
    """Test time-based and ID-based message filtering"""
    logger.info("Testing message filtering...")
    
    mailbox_name = "filter_test_mailbox"
    
    # Store messages with specific timestamps
    base_time = datetime.utcnow()
    for i, message in enumerate(messages):
        message.timestamp = base_time - timedelta(hours=i)
        await storage.store_message(mailbox_name, message)
    
    # Test time-based filtering
    logger.info("Testing time-based filtering...")
    
    # Filter messages from last 2 hours
    start_time = base_time - timedelta(hours=2)
    end_time = base_time + timedelta(minutes=30)
    
    time_filtered = await handler.get_messages_by_time_range(
        mailbox_name=mailbox_name,
        start_time=start_time,
        end_time=end_time
    )
    
    # Should include messages from hours 0, 1, and 2
    expected_count = 3
    assert len(time_filtered) == expected_count, \
        f"Expected {expected_count} messages in time range, got {len(time_filtered)}"
    
    # Verify all messages are within time range
    for message in time_filtered:
        assert start_time <= message.timestamp <= end_time, \
            f"Message {message.id} timestamp {message.timestamp} not in range"
    
    logger.info(f"Time-based filtering returned {len(time_filtered)} messages")
    
    # Test ID-based filtering
    logger.info("Testing ID-based filtering...")
    
    # Get all message IDs and sort them
    all_ids = sorted([msg.id for msg in messages])
    
    # Filter by ID range (middle messages)
    if len(all_ids) >= 3:
        start_id = all_ids[1]
        end_id = all_ids[3] if len(all_ids) > 3 else all_ids[-1]
        
        id_filtered = await handler.get_messages_by_id_range(
            mailbox_name=mailbox_name,
            start_message_id=start_id,
            end_message_id=end_id
        )
        
        # Verify messages are within ID range
        for message in id_filtered:
            assert start_id <= message.id <= end_id, \
                f"Message ID {message.id} not in range [{start_id}, {end_id}]"
        
        logger.info(f"ID-based filtering returned {len(id_filtered)} messages")
    
    # Test messages since last read
    logger.info("Testing messages since last read...")
    
    llm_id = "filter_reader_llm"
    
    # Mark first message as read
    if messages:
        await handler.mark_message_read(mailbox_name, messages[0].id, llm_id)
        
        # Get messages since last read
        since_read = await handler.get_messages_since_last_read(mailbox_name, llm_id)
        
        # Should return messages after the read one
        logger.info(f"Messages since last read: {len(since_read)}")
    
    # Test filter with queued messages
    logger.info("Testing filter with queued messages...")
    
    queue_llm = "filter_queue_llm"
    
    # Queue messages with different priorities
    for message in messages:
        await handler.queue_message_for_offline_llm(
            message=message,
            target_llm=queue_llm,
            mailbox_name=mailbox_name
        )
    
    # Filter by high priority
    high_priority_filter = MessageFilter(priority=Priority.HIGH)
    high_priority_queued = await handler.get_queued_messages(
        llm_id=queue_llm,
        message_filter=high_priority_filter
    )
    
    # Verify only high priority messages
    for offline_msg in high_priority_queued:
        assert offline_msg.message.routing_info.priority == Priority.HIGH, \
            f"Message {offline_msg.message.id} is not high priority"
    
    logger.info(f"High priority filter returned {len(high_priority_queued)} messages")
    
    logger.info("✓ Message filtering tests passed")


async def test_statistics_and_cleanup(handler: OfflineMessageHandler):
    """Test statistics and cleanup functionality"""
    logger.info("Testing statistics and cleanup...")
    
    # Get initial statistics
    stats = await handler.get_statistics()
    
    assert "total_queued_messages" in stats
    assert "active_llm_queues" in stats
    assert "running" in stats
    assert "initialized" in stats
    
    logger.info(f"Statistics: {stats}")
    
    # Verify handler is running and initialized
    assert stats["running"] is True, "Handler should be running"
    assert stats["initialized"] is True, "Handler should be initialized"
    
    logger.info("✓ Statistics and cleanup tests passed")


async def main():
    """Main validation function"""
    logger.info("Starting Offline Message Handler validation...")
    
    # Initialize components
    redis_config = RedisConfig()  # Use default configuration
    redis_ops = RedisOperations(redis_config)
    await redis_ops.initialize()
    
    # Clean up any existing test data
    async with redis_ops.connection_manager.get_connection() as redis_conn:
        await redis_conn.flushdb()
    
    try:
        # Initialize mailbox storage
        mailbox_storage = MailboxStorage(redis_ops)
        await mailbox_storage.initialize()
        
        # Initialize offline message handler
        offline_handler = OfflineMessageHandler(redis_ops, mailbox_storage)
        await offline_handler.initialize()
        await offline_handler.start()
        
        # Create test messages
        test_messages = await create_test_messages(5)
        logger.info(f"Created {len(test_messages)} test messages")
        
        # Run validation tests
        await test_offline_message_queuing(offline_handler, test_messages)
        await test_read_status_tracking(offline_handler, mailbox_storage, test_messages)
        await test_message_filtering(offline_handler, mailbox_storage, test_messages)
        await test_statistics_and_cleanup(offline_handler)
        
        logger.info("🎉 All offline message handler validation tests passed!")
        
        # Display final statistics
        final_stats = await offline_handler.get_statistics()
        logger.info(f"Final statistics: {final_stats}")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise
    
    finally:
        # Cleanup
        try:
            await offline_handler.stop()
            await offline_handler.close()
            await mailbox_storage.close()
            async with redis_ops.connection_manager.get_connection() as redis_conn:
                await redis_conn.flushdb()
            await redis_ops.close()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(main())