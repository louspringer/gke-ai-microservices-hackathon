#!/usr/bin/env python3
"""
Simple validation script for Permission Manager implementation

This script validates the Permission Manager component against requirements 4.1, 4.2, 4.3.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_permission_models():
    """Test permission data models"""
    logger.info("Testing permission data models...")
    
    from models.permission import Permission, LLMCredentials, AuthTokenData, AccessAuditLog
    from models.enums import OperationType
    
    # Test LLMCredentials creation
    credentials = LLMCredentials.create("test_llm", "secret123")
    assert credentials.llm_id == "test_llm"
    assert credentials.api_key is not None
    assert credentials.secret_hash is not None
    assert credentials.verify_secret("secret123")
    assert not credentials.verify_secret("wrong_secret")
    logger.info("✓ LLMCredentials working correctly")
    
    # Test AuthTokenData creation
    token_data = AuthTokenData.create("test_llm", validity_hours=1)
    assert token_data.llm_id == "test_llm"
    assert token_data.is_valid()
    assert not token_data.is_expired()
    logger.info("✓ AuthTokenData working correctly")
    
    # Test expired token
    expired_token = AuthTokenData.create("test_llm", validity_hours=-1)
    assert not expired_token.is_valid()
    assert expired_token.is_expired()
    logger.info("✓ Token expiration working correctly")
    
    # Test Permission creation
    permission = Permission.create(
        llm_id="test_llm",
        resource="mailbox:test",
        operation=OperationType.READ,
        granted_by="admin"
    )
    assert permission.llm_id == "test_llm"
    assert permission.resource == "mailbox:test"
    assert permission.operation == OperationType.READ
    assert permission.is_valid()
    logger.info("✓ Permission creation working correctly")
    
    # Test permission resource matching
    assert permission.matches_resource("mailbox:test")
    assert not permission.matches_resource("mailbox:other")
    
    # Test wildcard permission
    wildcard_permission = Permission.create(
        llm_id="test_llm",
        resource="mailbox:*",
        operation=OperationType.READ,
        granted_by="admin"
    )
    assert wildcard_permission.matches_resource("mailbox:test")
    assert wildcard_permission.matches_resource("mailbox:anything")
    logger.info("✓ Wildcard permissions working correctly")
    
    # Test global permission
    global_permission = Permission.create(
        llm_id="test_llm",
        resource="*",
        operation=OperationType.ADMIN,
        granted_by="system"
    )
    assert global_permission.matches_resource("anything")
    assert global_permission.matches_resource("mailbox:test")
    logger.info("✓ Global permissions working correctly")
    
    # Test expired permission
    expired_permission = Permission.create(
        llm_id="test_llm",
        resource="mailbox:test",
        operation=OperationType.READ,
        granted_by="admin",
        expires_hours=-1
    )
    assert not expired_permission.is_valid()
    logger.info("✓ Permission expiration working correctly")
    
    # Test AccessAuditLog creation
    audit_log = AccessAuditLog.create(
        llm_id="test_llm",
        operation=OperationType.READ,
        resource="mailbox:test",
        success=True
    )
    assert audit_log.llm_id == "test_llm"
    assert audit_log.operation == OperationType.READ
    assert audit_log.success is True
    assert isinstance(audit_log.timestamp, datetime)
    logger.info("✓ AccessAuditLog working correctly")
    
    # Test serialization/deserialization
    permission_dict = permission.to_dict()
    restored_permission = Permission.from_dict(permission_dict)
    assert restored_permission.id == permission.id
    assert restored_permission.llm_id == permission.llm_id
    assert restored_permission.resource == permission.resource
    logger.info("✓ Permission serialization working correctly")
    
    token_dict = token_data.to_dict()
    restored_token = AuthTokenData.from_dict(token_dict)
    assert restored_token.token == token_data.token
    assert restored_token.llm_id == token_data.llm_id
    logger.info("✓ Token serialization working correctly")
    
    audit_dict = audit_log.to_dict()
    restored_audit = AccessAuditLog.from_dict(audit_dict)
    assert restored_audit.id == audit_log.id
    assert restored_audit.llm_id == audit_log.llm_id
    logger.info("✓ Audit log serialization working correctly")
    
    logger.info("✓ All permission model tests passed")


def test_permission_manager_structure():
    """Test Permission Manager class structure"""
    logger.info("Testing Permission Manager class structure...")
    
    from core.permission_manager import PermissionManager, PermissionError, AuthenticationError, AuthorizationError
    from core.redis_manager import RedisConnectionManager, RedisConfig
    
    # Test class can be instantiated
    config = RedisConfig()
    redis_manager = RedisConnectionManager(config)
    perm_manager = PermissionManager(redis_manager)
    
    # Test required attributes exist
    assert hasattr(perm_manager, 'redis_manager')
    assert hasattr(perm_manager, '_token_cache')
    assert hasattr(perm_manager, '_permission_cache')
    assert hasattr(perm_manager, '_roles')
    logger.info("✓ Permission Manager attributes present")
    
    # Test predefined roles
    expected_roles = ["admin", "user", "readonly", "subscriber"]
    for role in expected_roles:
        assert role in perm_manager._roles
    logger.info("✓ Predefined roles present")
    
    # Test role permissions
    from models.enums import OperationType
    
    admin_perms = perm_manager._roles["admin"]
    assert OperationType.READ in admin_perms
    assert OperationType.WRITE in admin_perms
    assert OperationType.SUBSCRIBE in admin_perms
    assert OperationType.ADMIN in admin_perms
    logger.info("✓ Admin role permissions correct")
    
    user_perms = perm_manager._roles["user"]
    assert OperationType.READ in user_perms
    assert OperationType.WRITE in user_perms
    assert OperationType.SUBSCRIBE in user_perms
    assert OperationType.ADMIN not in user_perms
    logger.info("✓ User role permissions correct")
    
    readonly_perms = perm_manager._roles["readonly"]
    assert OperationType.READ in readonly_perms
    assert OperationType.SUBSCRIBE in readonly_perms
    assert OperationType.WRITE not in readonly_perms
    assert OperationType.ADMIN not in readonly_perms
    logger.info("✓ Readonly role permissions correct")
    
    subscriber_perms = perm_manager._roles["subscriber"]
    assert OperationType.SUBSCRIBE in subscriber_perms
    assert OperationType.READ not in subscriber_perms
    assert OperationType.WRITE not in subscriber_perms
    assert OperationType.ADMIN not in subscriber_perms
    logger.info("✓ Subscriber role permissions correct")
    
    # Test required methods exist
    required_methods = [
        'authenticate_llm', 'validate_token', 'check_permission',
        'grant_permission', 'revoke_permission', 'get_permissions',
        'assign_role', 'get_role', 'create_llm_credentials',
        'get_audit_logs', 'cleanup_expired_tokens', 'cleanup_permission_cache'
    ]
    
    for method in required_methods:
        assert hasattr(perm_manager, method)
        assert callable(getattr(perm_manager, method))
    logger.info("✓ All required methods present")
    
    # Test exception classes exist
    assert issubclass(PermissionError, Exception)
    assert issubclass(AuthenticationError, Exception)
    assert issubclass(AuthorizationError, Exception)
    logger.info("✓ Exception classes defined")
    
    logger.info("✓ All Permission Manager structure tests passed")


def test_enums():
    """Test operation type enums"""
    logger.info("Testing operation type enums...")
    
    from models.enums import OperationType
    
    # Test all required operation types exist
    required_ops = ["READ", "WRITE", "SUBSCRIBE", "ADMIN"]
    for op in required_ops:
        assert hasattr(OperationType, op)
    logger.info("✓ All operation types present")
    
    # Test enum values
    assert OperationType.READ.value == "read"
    assert OperationType.WRITE.value == "write"
    assert OperationType.SUBSCRIBE.value == "subscribe"
    assert OperationType.ADMIN.value == "admin"
    logger.info("✓ Operation type values correct")
    
    logger.info("✓ All enum tests passed")


def run_validation():
    """Run all validation tests"""
    logger.info("Starting Permission Manager validation...")
    
    try:
        test_enums()
        test_permission_models()
        test_permission_manager_structure()
        
        logger.info("🎉 All Permission Manager validation tests passed!")
        logger.info("✓ Requirements 4.1, 4.2, 4.3 implementation validated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_validation()
    sys.exit(0 if success else 1)