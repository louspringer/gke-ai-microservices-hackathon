"""
Tests for Permission Manager component

Tests permission checking logic, role-based access control,
and security audit logging as specified in requirements 4.1, 4.2, 4.3.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.permission_manager import (
    PermissionManager, PermissionError, AuthenticationError, AuthorizationError
)
from src.core.redis_manager import RedisConnectionManager, RedisConfig
from src.models.permission import (
    Permission, LLMCredentials, AuthTokenData, AccessAuditLog
)
from src.models.enums import OperationType


@pytest.fixture
async def redis_manager():
    """Create a mock Redis manager for testing"""
    config = RedisConfig(host="localhost", port=6379)
    manager = RedisConnectionManager(config)
    
    # Mock the Redis connection
    mock_redis = AsyncMock()
    manager._redis = mock_redis
    manager._state = manager._state.__class__.CONNECTED
    
    # Mock get_connection context manager properly
    class MockConnection:
        def __init__(self, redis):
            self.redis = redis
        
        async def __aenter__(self):
            return self.redis
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    manager.get_connection = lambda: MockConnection(mock_redis)
    
    return manager, mock_redis


@pytest.fixture
async def permission_manager(redis_manager):
    """Create a Permission Manager instance for testing"""
    redis_mgr, mock_redis = redis_manager
    return PermissionManager(redis_mgr), mock_redis


@pytest.fixture
def sample_credentials():
    """Create sample LLM credentials"""
    return LLMCredentials.create("test_llm_1", "test_secret")


@pytest.fixture
def sample_permission():
    """Create sample permission"""
    return Permission.create(
        llm_id="test_llm_1",
        resource="mailbox:test",
        operation=OperationType.READ,
        granted_by="admin_llm"
    )


class TestPermissionManager:
    """Test cases for Permission Manager"""
    
    async def test_authenticate_llm_success(self, permission_manager, sample_credentials):
        """Test successful LLM authentication"""
        perm_manager, mock_redis = permission_manager
        
        # Mock stored credentials
        mock_redis.hgetall.return_value = {
            "api_key": sample_credentials.api_key,
            "secret_hash": sample_credentials.secret_hash
        }
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        
        # Authenticate
        token_data = await perm_manager.authenticate_llm(sample_credentials)
        
        # Verify results
        assert token_data.llm_id == sample_credentials.llm_id
        assert token_data.is_valid()
        assert mock_redis.hgetall.called
        assert mock_redis.hset.called
        assert mock_redis.expire.called
    
    async def test_authenticate_llm_invalid_credentials(self, permission_manager, sample_credentials):
        """Test authentication with invalid credentials"""
        perm_manager, mock_redis = permission_manager
        
        # Mock no stored credentials
        mock_redis.hgetall.return_value = {}
        
        # Attempt authentication
        with pytest.raises(AuthenticationError, match="Credentials not found"):
            await perm_manager.authenticate_llm(sample_credentials)
    
    async def test_authenticate_llm_wrong_api_key(self, permission_manager, sample_credentials):
        """Test authentication with wrong API key"""
        perm_manager, mock_redis = permission_manager
        
        # Mock stored credentials with different API key
        mock_redis.hgetall.return_value = {
            "api_key": "wrong_api_key",
            "secret_hash": sample_credentials.secret_hash
        }
        
        # Attempt authentication
        with pytest.raises(AuthenticationError, match="Invalid API key"):
            await perm_manager.authenticate_llm(sample_credentials)
    
    async def test_validate_token_success(self, permission_manager):
        """Test successful token validation"""
        perm_manager, mock_redis = permission_manager
        
        # Create valid token
        token_data = AuthTokenData.create("test_llm_1")
        
        # Mock Redis response
        mock_redis.hgetall.return_value = token_data.to_dict()
        
        # Validate token
        result = await perm_manager.validate_token(token_data.token)
        
        # Verify results
        assert result.llm_id == token_data.llm_id
        assert result.token == token_data.token
        assert result.is_valid()
    
    async def test_validate_token_expired(self, permission_manager):
        """Test validation of expired token"""
        perm_manager, mock_redis = permission_manager
        
        # Create expired token
        token_data = AuthTokenData.create("test_llm_1", validity_hours=-1)  # Expired
        
        # Mock Redis response
        mock_redis.hgetall.return_value = token_data.to_dict()
        mock_redis.delete.return_value = True
        
        # Attempt validation
        with pytest.raises(AuthenticationError, match="Token has expired"):
            await perm_manager.validate_token(token_data.token)
        
        # Verify cleanup was called
        assert mock_redis.delete.called
    
    async def test_validate_token_not_found(self, permission_manager):
        """Test validation of non-existent token"""
        perm_manager, mock_redis = permission_manager
        
        # Mock no token found
        mock_redis.hgetall.return_value = {}
        
        # Attempt validation
        with pytest.raises(AuthenticationError, match="Invalid or expired token"):
            await perm_manager.validate_token("invalid_token")
    
    async def test_check_permission_granted(self, permission_manager, sample_permission):
        """Test permission check when permission is granted"""
        perm_manager, mock_redis = permission_manager
        
        # Mock permission retrieval
        mock_redis.smembers.return_value = [sample_permission.id]
        mock_redis.hgetall.return_value = sample_permission.to_dict()
        
        # Check permission
        result = await perm_manager.check_permission(
            sample_permission.llm_id,
            sample_permission.operation,
            sample_permission.resource
        )
        
        # Verify permission granted
        assert result is True
    
    async def test_check_permission_denied(self, permission_manager):
        """Test permission check when permission is denied"""
        perm_manager, mock_redis = permission_manager
        
        # Mock no permissions
        mock_redis.smembers.return_value = []
        mock_redis.hgetall.return_value = {}  # No role
        
        # Check permission
        result = await perm_manager.check_permission(
            "test_llm_1",
            OperationType.WRITE,
            "mailbox:test"
        )
        
        # Verify permission denied
        assert result is False
    
    async def test_check_permission_wildcard_resource(self, permission_manager):
        """Test permission check with wildcard resource"""
        perm_manager, mock_redis = permission_manager
        
        # Create wildcard permission
        wildcard_permission = Permission.create(
            llm_id="test_llm_1",
            resource="mailbox:*",
            operation=OperationType.READ,
            granted_by="admin_llm"
        )
        
        # Mock permission retrieval
        mock_redis.smembers.return_value = [wildcard_permission.id]
        mock_redis.hgetall.return_value = wildcard_permission.to_dict()
        
        # Check permission for specific mailbox
        result = await perm_manager.check_permission(
            "test_llm_1",
            OperationType.READ,
            "mailbox:specific_box"
        )
        
        # Verify permission granted
        assert result is True
    
    async def test_check_permission_role_based(self, permission_manager):
        """Test role-based permission checking"""
        perm_manager, mock_redis = permission_manager
        
        # Mock no direct permissions but has role
        mock_redis.smembers.return_value = []
        mock_redis.hgetall.side_effect = [
            {},  # No direct permissions
            {"role": "user", "granted_by": "admin", "granted_at": datetime.utcnow().isoformat()}  # Has user role
        ]
        
        # Check permission (user role should allow READ)
        result = await perm_manager.check_permission(
            "test_llm_1",
            OperationType.READ,
            "mailbox:test"
        )
        
        # Verify permission granted through role
        assert result is True
    
    async def test_grant_permission_success(self, permission_manager, sample_permission):
        """Test successful permission granting"""
        perm_manager, mock_redis = permission_manager
        
        # Mock Redis operations
        mock_redis.hset.return_value = True
        mock_redis.sadd.return_value = True
        
        # Grant permission
        result = await perm_manager.grant_permission(
            sample_permission.llm_id,
            sample_permission
        )
        
        # Verify success
        assert result is True
        assert mock_redis.hset.called
        assert mock_redis.sadd.called
    
    async def test_revoke_permission_success(self, permission_manager, sample_permission):
        """Test successful permission revocation"""
        perm_manager, mock_redis = permission_manager
        
        # Mock permission exists
        mock_redis.hgetall.return_value = sample_permission.to_dict()
        mock_redis.hset.return_value = True
        mock_redis.srem.return_value = True
        
        # Revoke permission
        result = await perm_manager.revoke_permission(
            sample_permission.llm_id,
            sample_permission.id
        )
        
        # Verify success
        assert result is True
        assert mock_redis.hset.called
        assert mock_redis.srem.called
    
    async def test_revoke_permission_not_found(self, permission_manager):
        """Test revoking non-existent permission"""
        perm_manager, mock_redis = permission_manager
        
        # Mock permission not found
        mock_redis.hgetall.return_value = {}
        
        # Attempt revocation
        result = await perm_manager.revoke_permission("test_llm_1", "nonexistent_id")
        
        # Verify failure
        assert result is False
    
    async def test_assign_role_success(self, permission_manager):
        """Test successful role assignment"""
        perm_manager, mock_redis = permission_manager
        
        # Mock Redis operations
        mock_redis.hset.return_value = True
        
        # Assign role
        result = await perm_manager.assign_role("test_llm_1", "user", "admin_llm")
        
        # Verify success
        assert result is True
        assert mock_redis.hset.called
    
    async def test_assign_role_invalid(self, permission_manager):
        """Test assigning invalid role"""
        perm_manager, mock_redis = permission_manager
        
        # Attempt to assign invalid role
        result = await perm_manager.assign_role("test_llm_1", "invalid_role", "admin_llm")
        
        # Verify failure
        assert result is False
    
    async def test_get_role_success(self, permission_manager):
        """Test successful role retrieval"""
        perm_manager, mock_redis = permission_manager
        
        # Mock role data
        mock_redis.hgetall.return_value = {
            "role": "user",
            "granted_by": "admin",
            "granted_at": datetime.utcnow().isoformat()
        }
        
        # Get role
        role = await perm_manager.get_role("test_llm_1")
        
        # Verify result
        assert role == "user"
    
    async def test_get_role_not_found(self, permission_manager):
        """Test role retrieval when no role assigned"""
        perm_manager, mock_redis = permission_manager
        
        # Mock no role data
        mock_redis.hgetall.return_value = {}
        
        # Get role
        role = await perm_manager.get_role("test_llm_1")
        
        # Verify result
        assert role is None
    
    async def test_create_llm_credentials(self, permission_manager):
        """Test LLM credentials creation"""
        perm_manager, mock_redis = permission_manager
        
        # Mock Redis operations
        mock_redis.hset.return_value = True
        
        # Create credentials
        credentials = await perm_manager.create_llm_credentials("test_llm_1", "test_secret")
        
        # Verify results
        assert credentials.llm_id == "test_llm_1"
        assert credentials.api_key is not None
        assert credentials.secret_hash is not None
        assert mock_redis.hset.called
    
    async def test_get_permissions_with_cache(self, permission_manager, sample_permission):
        """Test permission retrieval with caching"""
        perm_manager, mock_redis = permission_manager
        
        # First call - should hit Redis
        mock_redis.smembers.return_value = [sample_permission.id]
        mock_redis.hgetall.return_value = sample_permission.to_dict()
        
        permissions1 = await perm_manager.get_permissions("test_llm_1")
        
        # Second call - should hit cache
        permissions2 = await perm_manager.get_permissions("test_llm_1")
        
        # Verify results
        assert len(permissions1) == 1
        assert len(permissions2) == 1
        assert permissions1[0].id == sample_permission.id
        assert permissions2[0].id == sample_permission.id
        
        # Redis should only be called once due to caching
        assert mock_redis.smembers.call_count == 1
    
    async def test_audit_access_logging(self, permission_manager):
        """Test access audit logging"""
        perm_manager, mock_redis = permission_manager
        
        # Mock Redis operations
        mock_redis.hset.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.expire.return_value = True
        mock_redis.lpush.return_value = True
        mock_redis.ltrim.return_value = True
        
        # Trigger audit logging through permission check
        mock_redis.smembers.return_value = []
        mock_redis.hgetall.return_value = {}
        
        await perm_manager.check_permission("test_llm_1", OperationType.READ, "mailbox:test")
        
        # Verify audit logging was called
        assert mock_redis.hset.called
        assert mock_redis.sadd.called
        assert mock_redis.lpush.called
    
    async def test_get_audit_logs_by_llm(self, permission_manager):
        """Test audit log retrieval by LLM ID"""
        perm_manager, mock_redis = permission_manager
        
        # Create sample audit log
        audit_log = AccessAuditLog.create(
            llm_id="test_llm_1",
            operation=OperationType.READ,
            resource="mailbox:test",
            success=True
        )
        
        # Mock Redis responses
        mock_redis.lrange.return_value = [audit_log.id]
        mock_redis.hgetall.return_value = audit_log.to_dict()
        
        # Get audit logs
        logs = await perm_manager.get_audit_logs(llm_id="test_llm_1")
        
        # Verify results
        assert len(logs) == 1
        assert logs[0].llm_id == "test_llm_1"
        assert logs[0].operation == OperationType.READ
        assert logs[0].success is True
    
    async def test_get_audit_logs_by_time_range(self, permission_manager):
        """Test audit log retrieval by time range"""
        perm_manager, mock_redis = permission_manager
        
        # Create sample audit log
        audit_log = AccessAuditLog.create(
            llm_id="test_llm_1",
            operation=OperationType.READ,
            resource="mailbox:test",
            success=True
        )
        
        # Mock Redis responses
        mock_redis.smembers.return_value = [audit_log.id]
        mock_redis.hgetall.return_value = audit_log.to_dict()
        
        # Get audit logs with time range
        start_time = datetime.utcnow() - timedelta(hours=1)
        end_time = datetime.utcnow() + timedelta(hours=1)
        
        logs = await perm_manager.get_audit_logs(
            start_time=start_time,
            end_time=end_time
        )
        
        # Verify results
        assert len(logs) == 1
        assert logs[0].llm_id == "test_llm_1"
    
    async def test_cleanup_expired_tokens(self, permission_manager):
        """Test expired token cleanup"""
        perm_manager, mock_redis = permission_manager
        
        # Add expired token to cache
        expired_token = AuthTokenData.create("test_llm_1", validity_hours=-1)
        valid_token = AuthTokenData.create("test_llm_2")
        
        perm_manager._token_cache[expired_token.token] = expired_token
        perm_manager._token_cache[valid_token.token] = valid_token
        
        # Cleanup
        await perm_manager.cleanup_expired_tokens()
        
        # Verify expired token removed, valid token remains
        assert expired_token.token not in perm_manager._token_cache
        assert valid_token.token in perm_manager._token_cache
    
    async def test_cleanup_permission_cache(self, permission_manager):
        """Test permission cache cleanup"""
        perm_manager, mock_redis = permission_manager
        
        # Add data to cache
        perm_manager._permission_cache["test_llm_1"] = []
        
        # Force cache cleanup by setting old timestamp
        perm_manager._last_cache_cleanup = 0
        
        # Cleanup
        await perm_manager.cleanup_permission_cache()
        
        # Verify cache cleared
        assert len(perm_manager._permission_cache) == 0
    
    async def test_permission_expiration(self, permission_manager):
        """Test permission expiration handling"""
        perm_manager, mock_redis = permission_manager
        
        # Create expired permission
        expired_permission = Permission.create(
            llm_id="test_llm_1",
            resource="mailbox:test",
            operation=OperationType.READ,
            granted_by="admin_llm",
            expires_hours=-1  # Expired
        )
        
        # Mock permission retrieval
        mock_redis.smembers.return_value = [expired_permission.id]
        mock_redis.hgetall.return_value = expired_permission.to_dict()
        
        # Check permission
        result = await perm_manager.check_permission(
            "test_llm_1",
            OperationType.READ,
            "mailbox:test"
        )
        
        # Verify permission denied due to expiration
        assert result is False


class TestRoleBasedAccessControl:
    """Test cases for role-based access control"""
    
    async def test_admin_role_permissions(self, permission_manager):
        """Test admin role has all permissions"""
        perm_manager, mock_redis = permission_manager
        
        # Mock admin role
        mock_redis.smembers.return_value = []  # No direct permissions
        mock_redis.hgetall.return_value = {"role": "admin"}
        
        # Test all operations
        for operation in OperationType:
            result = await perm_manager.check_permission("admin_llm", operation, "any_resource")
            assert result is True, f"Admin should have {operation} permission"
    
    async def test_user_role_permissions(self, permission_manager):
        """Test user role permissions"""
        perm_manager, mock_redis = permission_manager
        
        # Mock user role
        mock_redis.smembers.return_value = []  # No direct permissions
        mock_redis.hgetall.return_value = {"role": "user"}
        
        # Test allowed operations
        allowed_ops = [OperationType.READ, OperationType.WRITE, OperationType.SUBSCRIBE]
        for operation in allowed_ops:
            result = await perm_manager.check_permission("user_llm", operation, "any_resource")
            assert result is True, f"User should have {operation} permission"
        
        # Test denied operations
        result = await perm_manager.check_permission("user_llm", OperationType.ADMIN, "any_resource")
        assert result is False, "User should not have ADMIN permission"
    
    async def test_readonly_role_permissions(self, permission_manager):
        """Test readonly role permissions"""
        perm_manager, mock_redis = permission_manager
        
        # Mock readonly role
        mock_redis.smembers.return_value = []  # No direct permissions
        mock_redis.hgetall.return_value = {"role": "readonly"}
        
        # Test allowed operations
        allowed_ops = [OperationType.READ, OperationType.SUBSCRIBE]
        for operation in allowed_ops:
            result = await perm_manager.check_permission("readonly_llm", operation, "any_resource")
            assert result is True, f"Readonly should have {operation} permission"
        
        # Test denied operations
        denied_ops = [OperationType.WRITE, OperationType.ADMIN]
        for operation in denied_ops:
            result = await perm_manager.check_permission("readonly_llm", operation, "any_resource")
            assert result is False, f"Readonly should not have {operation} permission"
    
    async def test_subscriber_role_permissions(self, permission_manager):
        """Test subscriber role permissions"""
        perm_manager, mock_redis = permission_manager
        
        # Mock subscriber role
        mock_redis.smembers.return_value = []  # No direct permissions
        mock_redis.hgetall.return_value = {"role": "subscriber"}
        
        # Test allowed operations
        result = await perm_manager.check_permission("subscriber_llm", OperationType.SUBSCRIBE, "any_resource")
        assert result is True, "Subscriber should have SUBSCRIBE permission"
        
        # Test denied operations
        denied_ops = [OperationType.READ, OperationType.WRITE, OperationType.ADMIN]
        for operation in denied_ops:
            result = await perm_manager.check_permission("subscriber_llm", operation, "any_resource")
            assert result is False, f"Subscriber should not have {operation} permission"


class TestSecurityAuditLogging:
    """Test cases for security audit logging"""
    
    async def test_successful_access_logged(self, permission_manager, sample_permission):
        """Test successful access is logged"""
        perm_manager, mock_redis = permission_manager
        
        # Mock successful permission check
        mock_redis.smembers.return_value = [sample_permission.id]
        mock_redis.hgetall.return_value = sample_permission.to_dict()
        
        # Mock audit logging
        mock_redis.hset.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.expire.return_value = True
        mock_redis.lpush.return_value = True
        mock_redis.ltrim.return_value = True
        
        # Perform operation
        await perm_manager.check_permission(
            sample_permission.llm_id,
            sample_permission.operation,
            sample_permission.resource
        )
        
        # Verify audit logging was called
        assert mock_redis.hset.called
        assert mock_redis.lpush.called
    
    async def test_failed_access_logged(self, permission_manager):
        """Test failed access is logged"""
        perm_manager, mock_redis = permission_manager
        
        # Mock failed permission check
        mock_redis.smembers.return_value = []
        mock_redis.hgetall.return_value = {}
        
        # Mock audit logging
        mock_redis.hset.return_value = True
        mock_redis.sadd.return_value = True
        mock_redis.expire.return_value = True
        mock_redis.lpush.return_value = True
        mock_redis.ltrim.return_value = True
        
        # Perform operation
        await perm_manager.check_permission("test_llm", OperationType.WRITE, "mailbox:test")
        
        # Verify audit logging was called
        assert mock_redis.hset.called
        assert mock_redis.lpush.called
    
    async def test_authentication_events_logged(self, permission_manager, sample_credentials):
        """Test authentication events are logged"""
        perm_manager, mock_redis = permission_manager
        
        # Mock successful authentication
        mock_redis.hgetall.return_value = {
            "api_key": sample_credentials.api_key,
            "secret_hash": sample_credentials.secret_hash
        }
        mock_redis.hset.return_value = True
        mock_redis.expire.return_value = True
        
        # Authenticate
        await perm_manager.authenticate_llm(sample_credentials)
        
        # Verify audit logging was called
        assert mock_redis.hset.called
        assert mock_redis.lpush.called


if __name__ == "__main__":
    pytest.main([__file__])