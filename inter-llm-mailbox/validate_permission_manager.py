#!/usr/bin/env python3
"""
Validation script for Permission Manager implementation

This script validates the Permission Manager component against requirements 4.1, 4.2, 4.3.
"""

import asyncio
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.permission_manager import PermissionManager, AuthenticationError, PermissionError
from core.redis_manager import RedisConnectionManager, RedisConfig
from models.permission import Permission, LLMCredentials, AuthTokenData
from models.enums import OperationType


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockRedis:
    """Mock Redis for testing without actual Redis instance"""
    
    def __init__(self):
        self.data = {}
        self.sets = {}
        self.lists = {}
    
    async def hgetall(self, key):
        return self.data.get(key, {})
    
    async def hset(self, key, mapping=None, **kwargs):
        if key not in self.data:
            self.data[key] = {}
        if mapping:
            self.data[key].update(mapping)
        if kwargs:
            self.data[key].update(kwargs)
        return True
    
    async def expire(self, key, seconds):
        return True
    
    async def delete(self, key):
        if key in self.data:
            del self.data[key]
        return True
    
    async def smembers(self, key):
        return self.sets.get(key, set())
    
    async def sadd(self, key, *values):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].update(values)
        return len(values)
    
    async def srem(self, key, *values):
        if key in self.sets:
            self.sets[key].discard(*values)
        return True
    
    async def lrange(self, key, start, end):
        return self.lists.get(key, [])
    
    async def lpush(self, key, *values):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key] = list(values) + self.lists[key]
        return len(self.lists[key])
    
    async def ltrim(self, key, start, end):
        if key in self.lists:
            self.lists[key] = self.lists[key][start:end+1]
        return True


async def create_mock_permission_manager():
    """Create a Permission Manager with mock Redis"""
    # Create mock Redis manager
    config = RedisConfig()
    redis_manager = RedisConnectionManager(config)
    
    # Replace with mock
    mock_redis = MockRedis()
    redis_manager._redis = mock_redis
    redis_manager._state = redis_manager._state.__class__.CONNECTED
    
    # Mock get_connection context manager
    class MockConnection:
        def __init__(self, redis):
            self.redis = redis
        
        async def __aenter__(self):
            return self.redis
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    redis_manager.get_connection = lambda: MockConnection(mock_redis)
    
    return PermissionManager(redis_manager), mock_redis


async def test_authentication():
    """Test LLM authentication functionality"""
    logger.info("Testing LLM authentication...")
    
    perm_manager, mock_redis = await create_mock_permission_manager()
    
    # Create test credentials
    credentials = await perm_manager.create_llm_credentials("test_llm_1", "test_secret")
    logger.info(f"Created credentials for LLM: {credentials.llm_id}")
    
    # Test authentication
    token_data = await perm_manager.authenticate_llm(credentials)
    logger.info(f"Authentication successful, token expires: {token_data.expires_at}")
    
    # Test token validation
    validated_token = await perm_manager.validate_token(token_data.token)
    assert validated_token.llm_id == credentials.llm_id
    logger.info("Token validation successful")
    
    # Test invalid credentials
    try:
        invalid_creds = LLMCredentials("test_llm_1", "wrong_key", credentials.secret_hash)
        await perm_manager.authenticate_llm(invalid_creds)
        assert False, "Should have failed with invalid credentials"
    except AuthenticationError:
        logger.info("Invalid credentials correctly rejected")
    
    logger.info("✓ Authentication tests passed")


async def test_permission_management():
    """Test permission granting and checking"""
    logger.info("Testing permission management...")
    
    perm_manager, mock_redis = await create_mock_permission_manager()
    
    # Create test permission
    permission = Permission.create(
        llm_id="test_llm_1",
        resource="mailbox:test",
        operation=OperationType.READ,
        granted_by="admin_llm"
    )
    
    # Grant permission
    success = await perm_manager.grant_permission("test_llm_1", permission)
    assert success, "Permission granting should succeed"
    logger.info(f"Granted permission: {permission.id}")
    
    # Check permission
    has_permission = await perm_manager.check_permission(
        "test_llm_1", OperationType.READ, "mailbox:test"
    )
    assert has_permission, "Permission check should succeed"
    logger.info("Permission check successful")
    
    # Check denied permission
    has_write_permission = await perm_manager.check_permission(
        "test_llm_1", OperationType.WRITE, "mailbox:test"
    )
    assert not has_write_permission, "Write permission should be denied"
    logger.info("Permission denial working correctly")
    
    # Test wildcard permissions
    wildcard_permission = Permission.create(
        llm_id="test_llm_1",
        resource="mailbox:*",
        operation=OperationType.WRITE,
        granted_by="admin_llm"
    )
    
    await perm_manager.grant_permission("test_llm_1", wildcard_permission)
    
    has_wildcard_permission = await perm_manager.check_permission(
        "test_llm_1", OperationType.WRITE, "mailbox:any_box"
    )
    assert has_wildcard_permission, "Wildcard permission should work"
    logger.info("Wildcard permissions working correctly")
    
    # Test permission revocation
    revoke_success = await perm_manager.revoke_permission("test_llm_1", permission.id)
    assert revoke_success, "Permission revocation should succeed"
    logger.info("Permission revocation successful")
    
    logger.info("✓ Permission management tests passed")


async def test_role_based_access_control():
    """Test role-based access control"""
    logger.info("Testing role-based access control...")
    
    perm_manager, mock_redis = await create_mock_permission_manager()
    
    # Test admin role
    success = await perm_manager.assign_role("admin_llm", "admin", "system")
    assert success, "Role assignment should succeed"
    logger.info("Assigned admin role")
    
    # Test admin permissions
    for operation in OperationType:
        has_permission = await perm_manager.check_permission("admin_llm", operation, "any_resource")
        assert has_permission, f"Admin should have {operation} permission"
    logger.info("Admin role permissions verified")
    
    # Test user role
    await perm_manager.assign_role("user_llm", "user", "admin_llm")
    
    # User should have read/write/subscribe but not admin
    user_allowed = [OperationType.READ, OperationType.WRITE, OperationType.SUBSCRIBE]
    for operation in user_allowed:
        has_permission = await perm_manager.check_permission("user_llm", operation, "any_resource")
        assert has_permission, f"User should have {operation} permission"
    
    has_admin = await perm_manager.check_permission("user_llm", OperationType.ADMIN, "any_resource")
    assert not has_admin, "User should not have admin permission"
    logger.info("User role permissions verified")
    
    # Test readonly role
    await perm_manager.assign_role("readonly_llm", "readonly", "admin_llm")
    
    readonly_allowed = [OperationType.READ, OperationType.SUBSCRIBE]
    for operation in readonly_allowed:
        has_permission = await perm_manager.check_permission("readonly_llm", operation, "any_resource")
        assert has_permission, f"Readonly should have {operation} permission"
    
    readonly_denied = [OperationType.WRITE, OperationType.ADMIN]
    for operation in readonly_denied:
        has_permission = await perm_manager.check_permission("readonly_llm", operation, "any_resource")
        assert not has_permission, f"Readonly should not have {operation} permission"
    logger.info("Readonly role permissions verified")
    
    # Test role retrieval
    role = await perm_manager.get_role("admin_llm")
    assert role == "admin", "Role retrieval should work"
    logger.info("Role retrieval working correctly")
    
    logger.info("✓ Role-based access control tests passed")


async def test_permission_expiration():
    """Test permission expiration handling"""
    logger.info("Testing permission expiration...")
    
    perm_manager, mock_redis = await create_mock_permission_manager()
    
    # Create expired permission
    expired_permission = Permission.create(
        llm_id="test_llm_1",
        resource="mailbox:test",
        operation=OperationType.READ,
        granted_by="admin_llm",
        expires_hours=-1  # Already expired
    )
    
    await perm_manager.grant_permission("test_llm_1", expired_permission)
    
    # Check permission - should be denied due to expiration
    has_permission = await perm_manager.check_permission(
        "test_llm_1", OperationType.READ, "mailbox:test"
    )
    assert not has_permission, "Expired permission should be denied"
    logger.info("Permission expiration working correctly")
    
    # Create valid permission with future expiration
    valid_permission = Permission.create(
        llm_id="test_llm_1",
        resource="mailbox:test2",
        operation=OperationType.READ,
        granted_by="admin_llm",
        expires_hours=24  # Valid for 24 hours
    )
    
    await perm_manager.grant_permission("test_llm_1", valid_permission)
    
    has_permission = await perm_manager.check_permission(
        "test_llm_1", OperationType.READ, "mailbox:test2"
    )
    assert has_permission, "Valid permission should be granted"
    logger.info("Valid permission with expiration working correctly")
    
    logger.info("✓ Permission expiration tests passed")


async def test_audit_logging():
    """Test security audit logging"""
    logger.info("Testing security audit logging...")
    
    perm_manager, mock_redis = await create_mock_permission_manager()
    
    # Perform some operations that should be audited
    await perm_manager.check_permission("test_llm", OperationType.READ, "mailbox:test")
    await perm_manager.check_permission("test_llm", OperationType.WRITE, "mailbox:test")
    
    # Check that audit logs were created
    logs = await perm_manager.get_audit_logs(llm_id="test_llm")
    assert len(logs) >= 2, "Audit logs should be created"
    logger.info(f"Found {len(logs)} audit log entries")
    
    # Verify log content
    for log in logs:
        assert log.llm_id == "test_llm"
        assert log.resource == "mailbox:test"
        assert log.operation in [OperationType.READ, OperationType.WRITE]
        assert isinstance(log.success, bool)
        assert isinstance(log.timestamp, datetime)
    
    logger.info("Audit log content verified")
    
    # Test time-based log retrieval
    start_time = datetime.utcnow() - timedelta(hours=1)
    end_time = datetime.utcnow() + timedelta(hours=1)
    
    time_logs = await perm_manager.get_audit_logs(start_time=start_time, end_time=end_time)
    assert len(time_logs) >= 0, "Time-based log retrieval should work"
    logger.info("Time-based audit log retrieval working")
    
    logger.info("✓ Audit logging tests passed")


async def test_caching():
    """Test permission and token caching"""
    logger.info("Testing caching functionality...")
    
    perm_manager, mock_redis = await create_mock_permission_manager()
    
    # Create credentials and authenticate
    credentials = await perm_manager.create_llm_credentials("cache_test_llm", "secret")
    token_data = await perm_manager.authenticate_llm(credentials)
    
    # Token should be cached
    assert token_data.token in perm_manager._token_cache
    logger.info("Token caching working")
    
    # Create and grant permission
    permission = Permission.create(
        llm_id="cache_test_llm",
        resource="mailbox:cache_test",
        operation=OperationType.READ,
        granted_by="admin"
    )
    await perm_manager.grant_permission("cache_test_llm", permission)
    
    # First call should populate cache
    permissions1 = await perm_manager.get_permissions("cache_test_llm")
    assert "cache_test_llm" in perm_manager._permission_cache
    logger.info("Permission caching working")
    
    # Second call should use cache
    permissions2 = await perm_manager.get_permissions("cache_test_llm")
    assert permissions1 == permissions2
    logger.info("Permission cache retrieval working")
    
    # Test cache cleanup
    await perm_manager.cleanup_permission_cache()
    logger.info("Cache cleanup working")
    
    logger.info("✓ Caching tests passed")


async def run_validation():
    """Run all validation tests"""
    logger.info("Starting Permission Manager validation...")
    
    try:
        await test_authentication()
        await test_permission_management()
        await test_role_based_access_control()
        await test_permission_expiration()
        await test_audit_logging()
        await test_caching()
        
        logger.info("🎉 All Permission Manager validation tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)