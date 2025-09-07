"""
Tests for Mailbox Storage Operations

Tests mailbox creation, metadata management, message persistence,
and retrieval operations as specified in requirements 1.4, 3.1, 3.2.
"""

import asyncio
import pytest
import json
from datetime import datetime, timedelta
from typing import List

from src.core.mailbox_storage import (
    MailboxStorage, MailboxMetadata, MailboxState, 
    MessageFilter, PaginationInfo, MessagePage
)
from src.core.redis_operations import RedisOperations
from src.core.redis_manager import RedisConfig
from src.models.message import Message, RoutingInfo, DeliveryOptions
from src.models.enums import ContentType, AddressingMode, Priority


@pytest.fixture
async def redis_ops():
    """Create Redis operations instance for testing"""
    config = RedisConfig(
        host="localhost",
        port=6379,
        db=15,  # Use test database
        max_connections=20  # Increased for concurrent tests
    )
    
    ops = RedisOperations(config)
    await ops.initialize()
    
    # Clean up test data
    await ops.delete("mailbox_index")
    keys_to_delete = []
    
    # Get all test mailbox keys
    async with ops.connection_manager.get_connection() as redis_conn:
        keys = await redis_conn.keys("mailbox:test_*")
        keys_to_delete.extend(keys)
    
    if keys_to_delete:
        await ops.delete(*keys_to_delete)
    
    yield ops
    
    # Cleanup after tests
    await ops.delete("mailbox_index")
    async with ops.connection_manager.get_connection() as redis_conn:
        keys = await redis_conn.keys("mailbox:test_*")
        if keys:
            await ops.delete(*keys)
    
    await ops.close()


@pytest.fixture
async def mailbox_storage(redis_ops):
    """Create mailbox storage instance for testing"""
    storage = MailboxStorage(redis_ops)
    await storage.initialize()
    
    yield storage
    
    await storage.close()


@pytest.fixture
def sample_message():
    """Create a sample message for testing"""
    routing_info = RoutingInfo(
        addressing_mode=AddressingMode.DIRECT,
        target="test_mailbox",
        priority=Priority.NORMAL
    )
    
    return Message.create(
        sender_id="test_llm_1",
        content="Hello, this is a test message!",
        content_type=ContentType.TEXT,
        routing_info=routing_info,
        metadata={"test": True, "tags": ["test", "sample"]}
    )


class TestMailboxCreation:
    """Test mailbox creation and metadata management"""
    
    async def test_create_mailbox_basic(self, mailbox_storage):
        """Test basic mailbox creation"""
        metadata = await mailbox_storage.create_mailbox(
            name="test_mailbox_1",
            created_by="test_llm_1",
            description="Test mailbox"
        )
        
        assert metadata.name == "test_mailbox_1"
        assert metadata.created_by == "test_llm_1"
        assert metadata.description == "Test mailbox"
        assert metadata.state == MailboxState.ACTIVE
        assert metadata.message_count == 0
        assert metadata.total_size_bytes == 0
        assert isinstance(metadata.created_at, datetime)
    
    async def test_create_mailbox_with_options(self, mailbox_storage):
        """Test mailbox creation with custom options"""
        metadata = await mailbox_storage.create_mailbox(
            name="test_mailbox_2",
            created_by="test_llm_2",
            description="Advanced test mailbox",
            max_messages=5000,
            message_ttl=3600,
            tags=["test", "advanced"],
            custom_metadata={"priority": "high", "team": "test"}
        )
        
        assert metadata.max_messages == 5000
        assert metadata.message_ttl == 3600
        assert metadata.tags == ["test", "advanced"]
        assert metadata.custom_metadata == {"priority": "high", "team": "test"}
    
    async def test_create_duplicate_mailbox(self, mailbox_storage):
        """Test that creating duplicate mailbox raises error"""
        await mailbox_storage.create_mailbox(
            name="test_duplicate",
            created_by="test_llm_1"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            await mailbox_storage.create_mailbox(
                name="test_duplicate",
                created_by="test_llm_2"
            )
    
    async def test_mailbox_exists(self, mailbox_storage):
        """Test mailbox existence check"""
        assert not await mailbox_storage.mailbox_exists("nonexistent")
        
        await mailbox_storage.create_mailbox(
            name="test_exists",
            created_by="test_llm_1"
        )
        
        assert await mailbox_storage.mailbox_exists("test_exists")
    
    async def test_get_mailbox_metadata(self, mailbox_storage):
        """Test retrieving mailbox metadata"""
        # Non-existent mailbox
        metadata = await mailbox_storage.get_mailbox_metadata("nonexistent")
        assert metadata is None
        
        # Existing mailbox
        created_metadata = await mailbox_storage.create_mailbox(
            name="test_get_metadata",
            created_by="test_llm_1",
            description="Test description"
        )
        
        retrieved_metadata = await mailbox_storage.get_mailbox_metadata("test_get_metadata")
        assert retrieved_metadata is not None
        assert retrieved_metadata.name == created_metadata.name
        assert retrieved_metadata.created_by == created_metadata.created_by
        assert retrieved_metadata.description == created_metadata.description
    
    async def test_update_mailbox_metadata(self, mailbox_storage):
        """Test updating mailbox metadata"""
        await mailbox_storage.create_mailbox(
            name="test_update",
            created_by="test_llm_1"
        )
        
        # Update metadata
        success = await mailbox_storage.update_mailbox_metadata(
            "test_update",
            {
                "description": "Updated description",
                "message_count": 5,
                "total_size_bytes": 1024
            }
        )
        assert success
        
        # Verify updates
        metadata = await mailbox_storage.get_mailbox_metadata("test_update")
        assert metadata.description == "Updated description"
        assert metadata.message_count == 5
        assert metadata.total_size_bytes == 1024
        
        # Update non-existent mailbox
        success = await mailbox_storage.update_mailbox_metadata(
            "nonexistent",
            {"description": "Should fail"}
        )
        assert not success
    
    async def test_delete_mailbox_soft(self, mailbox_storage):
        """Test soft delete (mark as deleted)"""
        await mailbox_storage.create_mailbox(
            name="test_soft_delete",
            created_by="test_llm_1"
        )
        
        success = await mailbox_storage.delete_mailbox("test_soft_delete", permanent=False)
        assert success
        
        # Mailbox should still exist but marked as deleted
        assert await mailbox_storage.mailbox_exists("test_soft_delete")
        metadata = await mailbox_storage.get_mailbox_metadata("test_soft_delete")
        assert metadata.state == MailboxState.DELETED
    
    async def test_delete_mailbox_permanent(self, mailbox_storage):
        """Test permanent delete"""
        await mailbox_storage.create_mailbox(
            name="test_permanent_delete",
            created_by="test_llm_1"
        )
        
        success = await mailbox_storage.delete_mailbox("test_permanent_delete", permanent=True)
        assert success
        
        # Mailbox should not exist
        assert not await mailbox_storage.mailbox_exists("test_permanent_delete")
        metadata = await mailbox_storage.get_mailbox_metadata("test_permanent_delete")
        assert metadata is None
    
    async def test_list_mailboxes(self, mailbox_storage):
        """Test listing mailboxes with filtering"""
        # Create test mailboxes
        await mailbox_storage.create_mailbox(
            name="test_list_1",
            created_by="llm_1",
            tags=["tag1", "tag2"]
        )
        
        await mailbox_storage.create_mailbox(
            name="test_list_2",
            created_by="llm_2",
            tags=["tag2", "tag3"]
        )
        
        await mailbox_storage.create_mailbox(
            name="test_list_3",
            created_by="llm_1",
            tags=["tag1"]
        )
        
        # Mark one as deleted
        await mailbox_storage.delete_mailbox("test_list_3", permanent=False)
        
        # List all
        all_mailboxes = await mailbox_storage.list_mailboxes()
        assert len(all_mailboxes) == 3
        
        # Filter by creator
        llm1_mailboxes = await mailbox_storage.list_mailboxes(created_by="llm_1")
        assert len(llm1_mailboxes) == 2
        
        # Filter by state
        active_mailboxes = await mailbox_storage.list_mailboxes(state=MailboxState.ACTIVE)
        assert len(active_mailboxes) == 2
        
        deleted_mailboxes = await mailbox_storage.list_mailboxes(state=MailboxState.DELETED)
        assert len(deleted_mailboxes) == 1
        
        # Filter by tags
        tag1_mailboxes = await mailbox_storage.list_mailboxes(tags=["tag1"])
        assert len(tag1_mailboxes) == 2
        
        tag2_mailboxes = await mailbox_storage.list_mailboxes(tags=["tag2"])
        assert len(tag2_mailboxes) == 2
        
        both_tags_mailboxes = await mailbox_storage.list_mailboxes(tags=["tag1", "tag2"])
        assert len(both_tags_mailboxes) == 1


class TestMessageStorage:
    """Test message storage and retrieval operations"""
    
    async def test_store_message_new_mailbox(self, mailbox_storage, sample_message):
        """Test storing message in new mailbox (auto-creation)"""
        # Mailbox doesn't exist yet
        assert not await mailbox_storage.mailbox_exists("test_auto_create")
        
        # Store message should auto-create mailbox
        success = await mailbox_storage.store_message("test_auto_create", sample_message)
        assert success
        
        # Mailbox should now exist
        assert await mailbox_storage.mailbox_exists("test_auto_create")
        
        # Check metadata
        metadata = await mailbox_storage.get_mailbox_metadata("test_auto_create")
        assert metadata.message_count == 1
        assert metadata.total_size_bytes > 0
        assert metadata.last_activity is not None
    
    async def test_store_message_existing_mailbox(self, mailbox_storage, sample_message):
        """Test storing message in existing mailbox"""
        # Create mailbox first
        await mailbox_storage.create_mailbox(
            name="test_existing",
            created_by="test_llm_1"
        )
        
        # Store message
        success = await mailbox_storage.store_message("test_existing", sample_message)
        assert success
        
        # Check metadata updated
        metadata = await mailbox_storage.get_mailbox_metadata("test_existing")
        assert metadata.message_count == 1
        assert metadata.total_size_bytes > 0
    
    async def test_store_multiple_messages(self, mailbox_storage):
        """Test storing multiple messages"""
        await mailbox_storage.create_mailbox(
            name="test_multiple",
            created_by="test_llm_1"
        )
        
        # Create and store multiple messages
        messages = []
        for i in range(5):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="test_multiple",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id=f"test_llm_{i % 2 + 1}",
                content=f"Test message {i}",
                content_type=ContentType.TEXT,
                routing_info=routing_info,
                metadata={"index": i}
            )
            messages.append(message)
            
            success = await mailbox_storage.store_message("test_multiple", message)
            assert success
        
        # Check metadata
        metadata = await mailbox_storage.get_mailbox_metadata("test_multiple")
        assert metadata.message_count == 5
        assert metadata.total_size_bytes > 0
    
    async def test_mailbox_size_limit(self, mailbox_storage):
        """Test mailbox size limit and cleanup"""
        # Create mailbox with small limit
        await mailbox_storage.create_mailbox(
            name="test_limit",
            created_by="test_llm_1",
            max_messages=3
        )
        
        # Store messages up to limit
        for i in range(5):  # Store more than limit
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="test_limit",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id="test_llm_1",
                content=f"Message {i}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            
            await mailbox_storage.store_message("test_limit", message)
        
        # Should only have max_messages
        metadata = await mailbox_storage.get_mailbox_metadata("test_limit")
        assert metadata.message_count == 3
    
    async def test_get_message(self, mailbox_storage, sample_message):
        """Test retrieving specific message"""
        await mailbox_storage.store_message("test_get_message", sample_message)
        
        # Get existing message
        retrieved = await mailbox_storage.get_message("test_get_message", sample_message.id)
        assert retrieved is not None
        assert retrieved.id == sample_message.id
        assert retrieved.sender_id == sample_message.sender_id
        assert retrieved.payload == sample_message.payload
        
        # Get non-existent message
        retrieved = await mailbox_storage.get_message("test_get_message", "nonexistent_id")
        assert retrieved is None
        
        # Get from non-existent mailbox
        retrieved = await mailbox_storage.get_message("nonexistent_mailbox", sample_message.id)
        assert retrieved is None
    
    async def test_delete_message(self, mailbox_storage, sample_message):
        """Test deleting message"""
        await mailbox_storage.store_message("test_delete_message", sample_message)
        
        # Verify message exists
        retrieved = await mailbox_storage.get_message("test_delete_message", sample_message.id)
        assert retrieved is not None
        
        # Delete message
        success = await mailbox_storage.delete_message("test_delete_message", sample_message.id)
        assert success
        
        # Verify message deleted
        retrieved = await mailbox_storage.get_message("test_delete_message", sample_message.id)
        assert retrieved is None
        
        # Check metadata updated
        metadata = await mailbox_storage.get_mailbox_metadata("test_delete_message")
        assert metadata.message_count == 0
        
        # Delete non-existent message
        success = await mailbox_storage.delete_message("test_delete_message", "nonexistent")
        assert not success


class TestMessageRetrieval:
    """Test message retrieval with pagination and filtering"""
    
    async def setup_test_messages(self, mailbox_storage) -> List[Message]:
        """Setup test messages for retrieval tests"""
        await mailbox_storage.create_mailbox(
            name="test_retrieval",
            created_by="test_llm_1"
        )
        
        messages = []
        for i in range(10):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="test_retrieval",
                priority=Priority.HIGH if i % 3 == 0 else Priority.NORMAL
            )
            
            message = Message.create(
                sender_id=f"test_llm_{i % 3 + 1}",
                content=f"Test message {i}",
                content_type=ContentType.JSON if i % 2 == 0 else ContentType.TEXT,
                routing_info=routing_info,
                metadata={"index": i, "tags": ["test", f"group_{i % 2}"]}
            )
            messages.append(message)
            
            await mailbox_storage.store_message("test_retrieval", message)
            
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)
        
        return messages
    
    async def test_get_messages_basic(self, mailbox_storage):
        """Test basic message retrieval"""
        messages = await self.setup_test_messages(mailbox_storage)
        
        # Get all messages
        page = await mailbox_storage.get_messages("test_retrieval")
        
        assert len(page.messages) == 10
        assert page.total_count == 10
        assert page.filtered_count == 10
        assert not page.pagination.has_more
        
        # Messages should be in reverse chronological order (newest first)
        assert page.messages[0].metadata["index"] == 9
        assert page.messages[-1].metadata["index"] == 0
    
    async def test_get_messages_pagination(self, mailbox_storage):
        """Test message retrieval with pagination"""
        await self.setup_test_messages(mailbox_storage)
        
        # First page
        page1 = await mailbox_storage.get_messages("test_retrieval", offset=0, limit=3)
        assert len(page1.messages) == 3
        assert page1.pagination.offset == 0
        assert page1.pagination.limit == 3
        assert page1.pagination.has_more
        assert page1.total_count == 10
        
        # Second page
        page2 = await mailbox_storage.get_messages("test_retrieval", offset=3, limit=3)
        assert len(page2.messages) == 3
        assert page2.pagination.offset == 3
        assert page2.pagination.has_more
        
        # Last page
        page3 = await mailbox_storage.get_messages("test_retrieval", offset=6, limit=10)
        assert len(page3.messages) == 4  # Only 4 remaining
        assert not page3.pagination.has_more
        
        # Verify no overlap
        all_ids = set()
        for page in [page1, page2, page3]:
            for message in page.messages:
                assert message.id not in all_ids  # No duplicates
                all_ids.add(message.id)
        
        assert len(all_ids) == 10  # All messages retrieved
    
    async def test_get_messages_reverse_order(self, mailbox_storage):
        """Test message retrieval in chronological order"""
        await self.setup_test_messages(mailbox_storage)
        
        # Get messages in chronological order (oldest first)
        page = await mailbox_storage.get_messages("test_retrieval", reverse=False)
        
        assert len(page.messages) == 10
        # Messages should be in chronological order (oldest first)
        assert page.messages[0].metadata["index"] == 0
        assert page.messages[-1].metadata["index"] == 9
    
    async def test_get_messages_with_filter(self, mailbox_storage):
        """Test message retrieval with filtering"""
        await self.setup_test_messages(mailbox_storage)
        
        # Filter by sender
        sender_filter = MessageFilter(sender_id="test_llm_1")
        page = await mailbox_storage.get_messages("test_retrieval", message_filter=sender_filter)
        
        # Should have messages with indices 0, 3, 6, 9 (every 3rd message)
        assert len(page.messages) == 4
        for message in page.messages:
            assert message.sender_id == "test_llm_1"
        
        # Filter by content type
        content_filter = MessageFilter(content_type=ContentType.JSON)
        page = await mailbox_storage.get_messages("test_retrieval", message_filter=content_filter)
        
        # Should have messages with even indices (0, 2, 4, 6, 8)
        assert len(page.messages) == 5
        for message in page.messages:
            assert message.content_type == ContentType.JSON
        
        # Filter by priority
        priority_filter = MessageFilter(priority=Priority.HIGH)
        page = await mailbox_storage.get_messages("test_retrieval", message_filter=priority_filter)
        
        # Should have messages with indices 0, 3, 6, 9 (every 3rd message)
        assert len(page.messages) == 4
        for message in page.messages:
            assert message.routing_info.priority == Priority.HIGH
    
    async def test_get_messages_time_filter(self, mailbox_storage):
        """Test message retrieval with time-based filtering"""
        messages = await self.setup_test_messages(mailbox_storage)
        
        # Get middle timestamp
        middle_time = messages[5].timestamp
        
        # Filter messages after middle time
        time_filter = MessageFilter(start_time=middle_time)
        page = await mailbox_storage.get_messages("test_retrieval", message_filter=time_filter)
        
        # Should include messages from index 5 onwards
        assert len(page.messages) >= 5
        for message in page.messages:
            assert message.timestamp >= middle_time
        
        # Filter messages before middle time
        time_filter = MessageFilter(end_time=middle_time)
        page = await mailbox_storage.get_messages("test_retrieval", message_filter=time_filter)
        
        # Should include messages up to index 5
        assert len(page.messages) >= 1
        for message in page.messages:
            assert message.timestamp <= middle_time
    
    async def test_get_messages_nonexistent_mailbox(self, mailbox_storage):
        """Test retrieving messages from non-existent mailbox"""
        page = await mailbox_storage.get_messages("nonexistent_mailbox")
        
        assert len(page.messages) == 0
        assert page.total_count == 0
        assert page.filtered_count == 0
        assert not page.pagination.has_more


class TestReadStatus:
    """Test message read status tracking"""
    
    async def test_mark_message_read(self, mailbox_storage, sample_message):
        """Test marking message as read"""
        await mailbox_storage.store_message("test_read_status", sample_message)
        
        # Initially not read
        is_read = await mailbox_storage.is_message_read("test_read_status", sample_message.id, "test_llm_2")
        assert not is_read
        
        # Mark as read
        success = await mailbox_storage.mark_message_read("test_read_status", sample_message.id, "test_llm_2")
        assert success
        
        # Should now be read
        is_read = await mailbox_storage.is_message_read("test_read_status", sample_message.id, "test_llm_2")
        assert is_read
        
        # Different LLM should not see it as read
        is_read = await mailbox_storage.is_message_read("test_read_status", sample_message.id, "test_llm_3")
        assert not is_read
    
    async def test_mark_nonexistent_message_read(self, mailbox_storage):
        """Test marking non-existent message as read"""
        await mailbox_storage.create_mailbox("test_nonexistent_read", "test_llm_1")
        
        success = await mailbox_storage.mark_message_read("test_nonexistent_read", "nonexistent_id", "test_llm_1")
        assert not success
    
    async def test_get_unread_count(self, mailbox_storage):
        """Test getting unread message count"""
        await mailbox_storage.create_mailbox("test_unread_count", "test_llm_1")
        
        # Store multiple messages
        messages = []
        for i in range(5):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="test_unread_count",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id="test_llm_1",
                content=f"Message {i}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            messages.append(message)
            await mailbox_storage.store_message("test_unread_count", message)
        
        # All messages should be unread for test_llm_2
        unread_count = await mailbox_storage.get_unread_count("test_unread_count", "test_llm_2")
        assert unread_count == 5
        
        # Mark some messages as read
        await mailbox_storage.mark_message_read("test_unread_count", messages[0].id, "test_llm_2")
        await mailbox_storage.mark_message_read("test_unread_count", messages[2].id, "test_llm_2")
        
        # Should have 3 unread messages
        unread_count = await mailbox_storage.get_unread_count("test_unread_count", "test_llm_2")
        assert unread_count == 3
        
        # Different LLM should still have all unread
        unread_count = await mailbox_storage.get_unread_count("test_unread_count", "test_llm_3")
        assert unread_count == 5
    
    async def test_unread_count_nonexistent_mailbox(self, mailbox_storage):
        """Test unread count for non-existent mailbox"""
        unread_count = await mailbox_storage.get_unread_count("nonexistent", "test_llm_1")
        assert unread_count == 0


class TestStorageIntegration:
    """Integration tests for mailbox storage operations"""
    
    async def test_full_mailbox_lifecycle(self, mailbox_storage):
        """Test complete mailbox lifecycle"""
        # Create mailbox
        metadata = await mailbox_storage.create_mailbox(
            name="test_lifecycle",
            created_by="test_llm_1",
            description="Lifecycle test",
            max_messages=100
        )
        
        # Store messages
        messages = []
        for i in range(10):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="test_lifecycle",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id=f"test_llm_{i % 2 + 1}",
                content=f"Lifecycle message {i}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            messages.append(message)
            await mailbox_storage.store_message("test_lifecycle", message)
        
        # Retrieve messages with pagination
        page1 = await mailbox_storage.get_messages("test_lifecycle", limit=5)
        assert len(page1.messages) == 5
        assert page1.pagination.has_more
        
        page2 = await mailbox_storage.get_messages("test_lifecycle", offset=5, limit=5)
        assert len(page2.messages) == 5
        assert not page2.pagination.has_more
        
        # Mark some messages as read
        for i in range(3):
            await mailbox_storage.mark_message_read("test_lifecycle", messages[i].id, "test_llm_3")
        
        # Check unread count
        unread_count = await mailbox_storage.get_unread_count("test_lifecycle", "test_llm_3")
        assert unread_count == 7
        
        # Delete some messages
        for i in range(2):
            await mailbox_storage.delete_message("test_lifecycle", messages[i].id)
        
        # Check updated counts
        updated_metadata = await mailbox_storage.get_mailbox_metadata("test_lifecycle")
        assert updated_metadata.message_count == 8
        
        # Soft delete mailbox
        await mailbox_storage.delete_mailbox("test_lifecycle", permanent=False)
        
        # Verify state
        final_metadata = await mailbox_storage.get_mailbox_metadata("test_lifecycle")
        assert final_metadata.state == MailboxState.DELETED
    
    async def test_concurrent_operations(self, mailbox_storage):
        """Test concurrent mailbox operations"""
        await mailbox_storage.create_mailbox("test_concurrent", "test_llm_1")
        
        # Create multiple messages concurrently
        async def store_message(index):
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="test_concurrent",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id=f"test_llm_{index % 3 + 1}",
                content=f"Concurrent message {index}",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            
            return await mailbox_storage.store_message("test_concurrent", message)
        
        # Store messages concurrently (reduced count to avoid connection limits)
        tasks = [store_message(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        
        # Check final count
        metadata = await mailbox_storage.get_mailbox_metadata("test_concurrent")
        assert metadata.message_count == 10
        
        # Retrieve all messages
        page = await mailbox_storage.get_messages("test_concurrent", limit=15)
        assert len(page.messages) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])