#!/usr/bin/env python3
"""
Validation script for Mailbox Storage Operations

This script validates the implementation of mailbox storage operations
including mailbox creation, metadata management, message persistence,
and retrieval with pagination support.

Requirements validated:
- 1.4: Automatic mailbox creation
- 3.1: Message persistence and retrieval
- 3.2: Pagination support for message retrieval
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import List

from src.core.mailbox_storage import MailboxStorage, MailboxState, MessageFilter
from src.core.redis_operations import RedisOperations
from src.core.redis_manager import RedisConfig
from src.models.message import Message, RoutingInfo
from src.models.enums import ContentType, AddressingMode, Priority


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MailboxStorageValidator:
    """Validator for mailbox storage operations"""
    
    def __init__(self):
        self.redis_ops = None
        self.mailbox_storage = None
        self.test_results = []
    
    async def setup(self):
        """Setup Redis and mailbox storage"""
        logger.info("Setting up Redis connection and mailbox storage")
        
        config = RedisConfig(
            host="localhost",
            port=6379,
            db=15,  # Use test database
            max_connections=10
        )
        
        self.redis_ops = RedisOperations(config)
        await self.redis_ops.initialize()
        
        self.mailbox_storage = MailboxStorage(self.redis_ops)
        await self.mailbox_storage.initialize()
        
        # Clean up any existing test data
        await self._cleanup_test_data()
        
        logger.info("Setup completed successfully")
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up resources")
        
        if self.mailbox_storage:
            await self.mailbox_storage.close()
        
        if self.redis_ops:
            await self._cleanup_test_data()
            await self.redis_ops.close()
        
        logger.info("Cleanup completed")
    
    async def _cleanup_test_data(self):
        """Clean up test data from Redis"""
        try:
            # Delete test mailbox index
            await self.redis_ops.delete("mailbox_index")
            
            # Delete all test mailbox keys
            async with self.redis_ops.connection_manager.get_connection() as redis_conn:
                keys = await redis_conn.keys("mailbox:validate_*")
                if keys:
                    await self.redis_ops.delete(*keys)
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def _record_test(self, test_name: str, success: bool, message: str = ""):
        """Record test result"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.utcnow()
        })
        
        status = "PASS" if success else "FAIL"
        logger.info(f"[{status}] {test_name}: {message}")
    
    async def validate_mailbox_creation(self):
        """Validate mailbox creation and metadata management"""
        logger.info("=== Validating Mailbox Creation ===")
        
        try:
            # Test basic mailbox creation
            metadata = await self.mailbox_storage.create_mailbox(
                name="validate_basic",
                created_by="validator_llm",
                description="Basic validation mailbox"
            )
            
            assert metadata.name == "validate_basic"
            assert metadata.created_by == "validator_llm"
            assert metadata.state == MailboxState.ACTIVE
            assert metadata.message_count == 0
            
            self._record_test("Basic Mailbox Creation", True, "Created mailbox with correct metadata")
            
        except Exception as e:
            self._record_test("Basic Mailbox Creation", False, f"Error: {e}")
            return
        
        try:
            # Test mailbox with custom options
            metadata = await self.mailbox_storage.create_mailbox(
                name="validate_advanced",
                created_by="validator_llm",
                description="Advanced validation mailbox",
                max_messages=1000,
                message_ttl=3600,
                tags=["validation", "test"],
                custom_metadata={"priority": "high"}
            )
            
            assert metadata.max_messages == 1000
            assert metadata.message_ttl == 3600
            assert "validation" in metadata.tags
            assert metadata.custom_metadata["priority"] == "high"
            
            self._record_test("Advanced Mailbox Creation", True, "Created mailbox with custom options")
            
        except Exception as e:
            self._record_test("Advanced Mailbox Creation", False, f"Error: {e}")
        
        try:
            # Test duplicate mailbox creation
            try:
                await self.mailbox_storage.create_mailbox(
                    name="validate_basic",  # Same name as before
                    created_by="another_llm"
                )
                self._record_test("Duplicate Mailbox Prevention", False, "Should have raised ValueError")
            except ValueError:
                self._record_test("Duplicate Mailbox Prevention", True, "Correctly prevented duplicate creation")
            
        except Exception as e:
            self._record_test("Duplicate Mailbox Prevention", False, f"Unexpected error: {e}")
        
        try:
            # Test mailbox existence check
            exists = await self.mailbox_storage.mailbox_exists("validate_basic")
            assert exists
            
            not_exists = await self.mailbox_storage.mailbox_exists("nonexistent")
            assert not not_exists
            
            self._record_test("Mailbox Existence Check", True, "Correctly identified existing and non-existing mailboxes")
            
        except Exception as e:
            self._record_test("Mailbox Existence Check", False, f"Error: {e}")
        
        try:
            # Test metadata retrieval and updates
            metadata = await self.mailbox_storage.get_mailbox_metadata("validate_basic")
            assert metadata is not None
            assert metadata.name == "validate_basic"
            
            # Update metadata
            success = await self.mailbox_storage.update_mailbox_metadata(
                "validate_basic",
                {"description": "Updated description", "message_count": 5}
            )
            assert success
            
            # Verify update
            updated_metadata = await self.mailbox_storage.get_mailbox_metadata("validate_basic")
            assert updated_metadata.description == "Updated description"
            assert updated_metadata.message_count == 5
            
            self._record_test("Metadata Management", True, "Successfully retrieved and updated metadata")
            
        except Exception as e:
            self._record_test("Metadata Management", False, f"Error: {e}")
    
    async def validate_message_storage(self):
        """Validate message storage operations"""
        logger.info("=== Validating Message Storage ===")
        
        try:
            # Test auto-creation of mailbox when storing message (Requirement 1.4)
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="validate_auto_create",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id="validator_llm",
                content="Test message for auto-creation",
                content_type=ContentType.TEXT,
                routing_info=routing_info,
                metadata={"test": "auto_create"}
            )
            
            # Mailbox doesn't exist yet
            assert not await self.mailbox_storage.mailbox_exists("validate_auto_create")
            
            # Store message should auto-create mailbox
            success = await self.mailbox_storage.store_message("validate_auto_create", message)
            assert success
            
            # Mailbox should now exist
            assert await self.mailbox_storage.mailbox_exists("validate_auto_create")
            
            # Check metadata
            metadata = await self.mailbox_storage.get_mailbox_metadata("validate_auto_create")
            assert metadata.message_count == 1
            assert metadata.total_size_bytes > 0
            
            self._record_test("Auto-Create Mailbox on Message Store", True, "Mailbox auto-created when storing message")
            
        except Exception as e:
            self._record_test("Auto-Create Mailbox on Message Store", False, f"Error: {e}")
            return
        
        try:
            # Test storing multiple messages
            messages = []
            for i in range(10):
                routing_info = RoutingInfo(
                    addressing_mode=AddressingMode.DIRECT,
                    target="validate_multiple",
                    priority=Priority.HIGH if i % 3 == 0 else Priority.NORMAL
                )
                
                message = Message.create(
                    sender_id=f"validator_llm_{i % 2}",
                    content=f"Test message {i}",
                    content_type=ContentType.JSON if i % 2 == 0 else ContentType.TEXT,
                    routing_info=routing_info,
                    metadata={"index": i, "batch": "validation"}
                )
                messages.append(message)
                
                success = await self.mailbox_storage.store_message("validate_multiple", message)
                assert success
                
                # Small delay to ensure different timestamps
                await asyncio.sleep(0.01)
            
            # Check final metadata
            metadata = await self.mailbox_storage.get_mailbox_metadata("validate_multiple")
            assert metadata.message_count == 10
            assert metadata.total_size_bytes > 0
            
            self._record_test("Multiple Message Storage", True, f"Stored {len(messages)} messages successfully")
            
        except Exception as e:
            self._record_test("Multiple Message Storage", False, f"Error: {e}")
            return
        
        try:
            # Test message size limits and cleanup
            await self.mailbox_storage.create_mailbox(
                name="validate_limits",
                created_by="validator_llm",
                max_messages=3  # Small limit for testing
            )
            
            # Store more messages than limit
            for i in range(5):
                routing_info = RoutingInfo(
                    addressing_mode=AddressingMode.DIRECT,
                    target="validate_limits",
                    priority=Priority.NORMAL
                )
                
                message = Message.create(
                    sender_id="validator_llm",
                    content=f"Limit test message {i}",
                    content_type=ContentType.TEXT,
                    routing_info=routing_info
                )
                
                await self.mailbox_storage.store_message("validate_limits", message)
            
            # Should only have max_messages
            metadata = await self.mailbox_storage.get_mailbox_metadata("validate_limits")
            if metadata.message_count != 3:
                raise AssertionError(f"Expected 3 messages, got {metadata.message_count}")
            assert metadata.message_count == 3
            
            self._record_test("Message Limit Enforcement", True, "Correctly enforced message limits with cleanup")
            
        except Exception as e:
            self._record_test("Message Limit Enforcement", False, f"Error: {e}")
    
    async def validate_message_retrieval(self):
        """Validate message retrieval with pagination (Requirement 3.1, 3.2)"""
        logger.info("=== Validating Message Retrieval ===")
        
        try:
            # Setup test messages for retrieval
            test_messages = []
            for i in range(15):
                routing_info = RoutingInfo(
                    addressing_mode=AddressingMode.DIRECT,
                    target="validate_retrieval",
                    priority=Priority.HIGH if i % 4 == 0 else Priority.NORMAL
                )
                
                message = Message.create(
                    sender_id=f"validator_llm_{i % 3}",
                    content=f"Retrieval test message {i}",
                    content_type=ContentType.JSON if i % 2 == 0 else ContentType.TEXT,
                    routing_info=routing_info,
                    metadata={"index": i, "group": f"group_{i % 3}"}
                )
                test_messages.append(message)
                
                await self.mailbox_storage.store_message("validate_retrieval", message)
                await asyncio.sleep(0.01)  # Ensure different timestamps
            
            self._record_test("Test Message Setup", True, f"Created {len(test_messages)} test messages")
            
        except Exception as e:
            self._record_test("Test Message Setup", False, f"Error: {e}")
            return
        
        try:
            # Test basic retrieval
            page = await self.mailbox_storage.get_messages("validate_retrieval")
            
            assert len(page.messages) == 15
            assert page.total_count == 15
            assert page.filtered_count == 15
            assert not page.pagination.has_more
            
            # Messages should be in reverse chronological order (newest first)
            assert page.messages[0].metadata["index"] == 14
            assert page.messages[-1].metadata["index"] == 0
            
            self._record_test("Basic Message Retrieval", True, "Retrieved all messages in correct order")
            
        except Exception as e:
            self._record_test("Basic Message Retrieval", False, f"Error: {e}")
        
        try:
            # Test pagination (Requirement 3.2)
            page1 = await self.mailbox_storage.get_messages("validate_retrieval", offset=0, limit=5)
            assert len(page1.messages) == 5
            assert page1.pagination.offset == 0
            assert page1.pagination.limit == 5
            assert page1.pagination.has_more
            assert page1.total_count == 15
            
            page2 = await self.mailbox_storage.get_messages("validate_retrieval", offset=5, limit=5)
            assert len(page2.messages) == 5
            assert page2.pagination.offset == 5
            assert page2.pagination.has_more
            
            page3 = await self.mailbox_storage.get_messages("validate_retrieval", offset=10, limit=10)
            assert len(page3.messages) == 5  # Only 5 remaining
            assert not page3.pagination.has_more
            
            # Verify no overlap between pages
            all_ids = set()
            for page in [page1, page2, page3]:
                for message in page.messages:
                    assert message.id not in all_ids
                    all_ids.add(message.id)
            
            assert len(all_ids) == 15
            
            self._record_test("Pagination Support", True, "Pagination works correctly with no overlaps")
            
        except Exception as e:
            self._record_test("Pagination Support", False, f"Error: {e}")
        
        try:
            # Test filtering
            sender_filter = MessageFilter(sender_id="validator_llm_1")
            page = await self.mailbox_storage.get_messages("validate_retrieval", message_filter=sender_filter)
            
            # Should have messages with indices 1, 4, 7, 10, 13 (every 3rd starting from 1)
            expected_count = 5
            assert len(page.messages) == expected_count
            
            for message in page.messages:
                assert message.sender_id == "validator_llm_1"
            
            # Test content type filter
            content_filter = MessageFilter(content_type=ContentType.JSON)
            page = await self.mailbox_storage.get_messages("validate_retrieval", message_filter=content_filter)
            
            # Should have messages with even indices
            expected_count = 8  # 0, 2, 4, 6, 8, 10, 12, 14
            assert len(page.messages) == expected_count
            
            for message in page.messages:
                assert message.content_type == ContentType.JSON
            
            # Test priority filter
            priority_filter = MessageFilter(priority=Priority.HIGH)
            page = await self.mailbox_storage.get_messages("validate_retrieval", message_filter=priority_filter)
            
            # Should have messages with indices 0, 4, 8, 12 (every 4th)
            expected_count = 4
            assert len(page.messages) == expected_count
            
            for message in page.messages:
                assert message.routing_info.priority == Priority.HIGH
            
            self._record_test("Message Filtering", True, "All filter types work correctly")
            
        except Exception as e:
            self._record_test("Message Filtering", False, f"Error: {e}")
        
        try:
            # Test chronological order retrieval
            page = await self.mailbox_storage.get_messages("validate_retrieval", reverse=False)
            
            # Messages should be in chronological order (oldest first)
            assert page.messages[0].metadata["index"] == 0
            assert page.messages[-1].metadata["index"] == 14
            
            self._record_test("Chronological Order Retrieval", True, "Retrieved messages in chronological order")
            
        except Exception as e:
            self._record_test("Chronological Order Retrieval", False, f"Error: {e}")
    
    async def validate_read_status_tracking(self):
        """Validate message read status tracking"""
        logger.info("=== Validating Read Status Tracking ===")
        
        try:
            # Create test messages
            messages = []
            for i in range(5):
                routing_info = RoutingInfo(
                    addressing_mode=AddressingMode.DIRECT,
                    target="validate_read_status",
                    priority=Priority.NORMAL
                )
                
                message = Message.create(
                    sender_id="validator_llm",
                    content=f"Read status test message {i}",
                    content_type=ContentType.TEXT,
                    routing_info=routing_info
                )
                messages.append(message)
                
                await self.mailbox_storage.store_message("validate_read_status", message)
            
            # Test initial unread count
            unread_count = await self.mailbox_storage.get_unread_count("validate_read_status", "reader_llm")
            assert unread_count == 5
            
            # Mark some messages as read
            await self.mailbox_storage.mark_message_read("validate_read_status", messages[0].id, "reader_llm")
            await self.mailbox_storage.mark_message_read("validate_read_status", messages[2].id, "reader_llm")
            
            # Check read status
            is_read_0 = await self.mailbox_storage.is_message_read("validate_read_status", messages[0].id, "reader_llm")
            is_read_1 = await self.mailbox_storage.is_message_read("validate_read_status", messages[1].id, "reader_llm")
            is_read_2 = await self.mailbox_storage.is_message_read("validate_read_status", messages[2].id, "reader_llm")
            
            assert is_read_0  # Should be read
            assert not is_read_1  # Should be unread
            assert is_read_2  # Should be read
            
            # Check updated unread count
            unread_count = await self.mailbox_storage.get_unread_count("validate_read_status", "reader_llm")
            assert unread_count == 3
            
            # Different LLM should have all unread
            unread_count_other = await self.mailbox_storage.get_unread_count("validate_read_status", "other_llm")
            assert unread_count_other == 5
            
            self._record_test("Read Status Tracking", True, "Read status tracking works correctly per LLM")
            
        except Exception as e:
            self._record_test("Read Status Tracking", False, f"Error: {e}")
    
    async def validate_message_operations(self):
        """Validate individual message operations"""
        logger.info("=== Validating Message Operations ===")
        
        try:
            # Create test message
            routing_info = RoutingInfo(
                addressing_mode=AddressingMode.DIRECT,
                target="validate_operations",
                priority=Priority.NORMAL
            )
            
            message = Message.create(
                sender_id="validator_llm",
                content="Message operations test",
                content_type=ContentType.TEXT,
                routing_info=routing_info
            )
            
            await self.mailbox_storage.store_message("validate_operations", message)
            
            # Test get specific message
            retrieved = await self.mailbox_storage.get_message("validate_operations", message.id)
            assert retrieved is not None
            assert retrieved.id == message.id
            assert retrieved.sender_id == message.sender_id
            assert retrieved.payload == message.payload
            
            # Test get non-existent message
            non_existent = await self.mailbox_storage.get_message("validate_operations", "nonexistent_id")
            assert non_existent is None
            
            # Test delete message
            success = await self.mailbox_storage.delete_message("validate_operations", message.id)
            assert success
            
            # Verify message deleted
            deleted = await self.mailbox_storage.get_message("validate_operations", message.id)
            assert deleted is None
            
            # Check metadata updated
            metadata = await self.mailbox_storage.get_mailbox_metadata("validate_operations")
            assert metadata.message_count == 0
            
            self._record_test("Individual Message Operations", True, "Get and delete operations work correctly")
            
        except Exception as e:
            self._record_test("Individual Message Operations", False, f"Error: {e}")
    
    async def validate_mailbox_listing(self):
        """Validate mailbox listing with filtering"""
        logger.info("=== Validating Mailbox Listing ===")
        
        try:
            # Create test mailboxes with different properties
            await self.mailbox_storage.create_mailbox(
                name="validate_list_1",
                created_by="llm_1",
                tags=["tag1", "tag2"]
            )
            
            await self.mailbox_storage.create_mailbox(
                name="validate_list_2",
                created_by="llm_2",
                tags=["tag2", "tag3"]
            )
            
            await self.mailbox_storage.create_mailbox(
                name="validate_list_3",
                created_by="llm_1",
                tags=["tag1"]
            )
            
            # Mark one as deleted
            await self.mailbox_storage.delete_mailbox("validate_list_3", permanent=False)
            
            # Test listing all mailboxes
            all_mailboxes = await self.mailbox_storage.list_mailboxes()
            validate_mailboxes = [m for m in all_mailboxes if m.name.startswith("validate_list_")]
            assert len(validate_mailboxes) == 3
            
            # Test filtering by creator
            llm1_mailboxes = await self.mailbox_storage.list_mailboxes(created_by="llm_1")
            validate_llm1 = [m for m in llm1_mailboxes if m.name.startswith("validate_list_")]
            assert len(validate_llm1) == 2
            
            # Test filtering by state
            active_mailboxes = await self.mailbox_storage.list_mailboxes(state=MailboxState.ACTIVE)
            validate_active = [m for m in active_mailboxes if m.name.startswith("validate_list_")]
            assert len(validate_active) == 2
            
            deleted_mailboxes = await self.mailbox_storage.list_mailboxes(state=MailboxState.DELETED)
            validate_deleted = [m for m in deleted_mailboxes if m.name.startswith("validate_list_")]
            assert len(validate_deleted) == 1
            
            # Test filtering by tags
            tag1_mailboxes = await self.mailbox_storage.list_mailboxes(tags=["tag1"])
            validate_tag1 = [m for m in tag1_mailboxes if m.name.startswith("validate_list_")]
            assert len(validate_tag1) == 2
            
            self._record_test("Mailbox Listing and Filtering", True, "All listing filters work correctly")
            
        except Exception as e:
            self._record_test("Mailbox Listing and Filtering", False, f"Error: {e}")
    
    async def run_validation(self):
        """Run all validation tests"""
        logger.info("Starting Mailbox Storage Validation")
        
        try:
            await self.setup()
            
            # Run validation tests
            await self.validate_mailbox_creation()
            await self.validate_message_storage()
            await self.validate_message_retrieval()
            await self.validate_read_status_tracking()
            await self.validate_message_operations()
            await self.validate_mailbox_listing()
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}")
            self._record_test("Overall Validation", False, f"Critical error: {e}")
        
        finally:
            await self.cleanup()
        
        # Print results summary
        self._print_results()
    
    def _print_results(self):
        """Print validation results summary"""
        logger.info("=== Validation Results Summary ===")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            logger.info("\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    logger.info(f"  - {result['test']}: {result['message']}")
        
        # Print requirement validation status
        logger.info("\n=== Requirements Validation Status ===")
        
        # Check requirement 1.4 (Automatic mailbox creation)
        auto_create_tests = [r for r in self.test_results if "Auto-Create" in r['test']]
        req_1_4_status = all(r['success'] for r in auto_create_tests) if auto_create_tests else False
        logger.info(f"Requirement 1.4 (Automatic mailbox creation): {'PASS' if req_1_4_status else 'FAIL'}")
        
        # Check requirement 3.1 (Message persistence and retrieval)
        persistence_tests = [r for r in self.test_results if any(keyword in r['test'] for keyword in ['Storage', 'Retrieval', 'Operations'])]
        req_3_1_status = all(r['success'] for r in persistence_tests) if persistence_tests else False
        logger.info(f"Requirement 3.1 (Message persistence and retrieval): {'PASS' if req_3_1_status else 'FAIL'}")
        
        # Check requirement 3.2 (Pagination support)
        pagination_tests = [r for r in self.test_results if "Pagination" in r['test']]
        req_3_2_status = all(r['success'] for r in pagination_tests) if pagination_tests else False
        logger.info(f"Requirement 3.2 (Pagination support): {'PASS' if req_3_2_status else 'FAIL'}")
        
        overall_success = failed_tests == 0
        logger.info(f"\nOverall Validation: {'PASS' if overall_success else 'FAIL'}")
        
        return overall_success


async def main():
    """Main validation function"""
    validator = MailboxStorageValidator()
    success = await validator.run_validation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())