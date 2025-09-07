"""
Permission Manager for Inter-LLM Mailbox System

This module implements permission checking logic, role-based access control,
and security audit logging as specified in requirements 4.1, 4.2, 4.3.
"""

import asyncio
import logging
import time
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from ..models.permission import (
    Permission, LLMCredentials, AuthTokenData, AccessAuditLog,
    LLMID, AuthToken, PermissionID
)
from ..models.enums import OperationType
from .redis_manager import RedisConnectionManager


logger = logging.getLogger(__name__)


class PermissionError(Exception):
    """Permission-related errors"""
    pass


class AuthenticationError(Exception):
    """Authentication-related errors"""
    pass


class AuthorizationError(Exception):
    """Authorization-related errors"""
    pass


class PermissionManager:
    """
    Manages permissions, authentication, and authorization for the mailbox system.
    
    Implements requirements:
    - 4.1: Access control lists for read/write permissions
    - 4.2: Authentication, authorization, and audit logging
    - 4.3: Role-based access control
    """
    
    def __init__(self, redis_manager: RedisConnectionManager):
        self.redis_manager = redis_manager
        self._token_cache: Dict[AuthToken, AuthTokenData] = {}
        self._permission_cache: Dict[LLMID, List[Permission]] = {}
        self._cache_lock = asyncio.Lock()
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_cleanup = time.time()
        
        # Predefined roles with their permissions
        self._roles = {
            "admin": {
                OperationType.READ, OperationType.WRITE, 
                OperationType.SUBSCRIBE, OperationType.ADMIN
            },
            "user": {
                OperationType.READ, OperationType.WRITE, OperationType.SUBSCRIBE
            },
            "readonly": {
                OperationType.READ, OperationType.SUBSCRIBE
            },
            "subscriber": {
                OperationType.SUBSCRIBE
            }
        }
    
    async def authenticate_llm(self, credentials: LLMCredentials) -> AuthTokenData:
        """
        Authenticate an LLM and return an auth token.
        
        Args:
            credentials: LLM credentials to verify
            
        Returns:
            AuthTokenData: Valid authentication token
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            async with self.redis_manager.get_connection() as redis:
                # Retrieve stored credentials
                stored_creds_data = await redis.hgetall(f"llm:credentials:{credentials.llm_id}")
                
                if not stored_creds_data:
                    await self._audit_access(
                        credentials.llm_id, OperationType.ADMIN, "authentication", 
                        False, details={"reason": "credentials_not_found"}
                    )
                    raise AuthenticationError(f"Credentials not found for LLM {credentials.llm_id}")
                
                # Verify API key
                if stored_creds_data.get("api_key") != credentials.api_key:
                    await self._audit_access(
                        credentials.llm_id, OperationType.ADMIN, "authentication", 
                        False, details={"reason": "invalid_api_key"}
                    )
                    raise AuthenticationError("Invalid API key")
                
                # Create auth token
                token_data = AuthTokenData.create(credentials.llm_id)
                
                # Store token in Redis with expiration
                token_key = f"auth:token:{token_data.token}"
                await redis.hset(token_key, mapping=token_data.to_dict())
                await redis.expire(token_key, int((token_data.expires_at - datetime.utcnow()).total_seconds()))
                
                # Cache token locally
                async with self._cache_lock:
                    self._token_cache[token_data.token] = token_data
                
                await self._audit_access(
                    credentials.llm_id, OperationType.ADMIN, "authentication", 
                    True, details={"token_expires": token_data.expires_at.isoformat()}
                )
                
                logger.info(f"Successfully authenticated LLM {credentials.llm_id}")
                return token_data
                
        except Exception as e:
            logger.error(f"Authentication failed for LLM {credentials.llm_id}: {e}")
            if not isinstance(e, AuthenticationError):
                raise AuthenticationError(f"Authentication failed: {e}")
            raise
    
    async def validate_token(self, token: AuthToken) -> AuthTokenData:
        """
        Validate an authentication token.
        
        Args:
            token: Authentication token to validate
            
        Returns:
            AuthTokenData: Valid token data
            
        Raises:
            AuthenticationError: If token is invalid or expired
        """
        # Check local cache first
        async with self._cache_lock:
            if token in self._token_cache:
                token_data = self._token_cache[token]
                if token_data.is_valid():
                    return token_data
                else:
                    # Remove expired token from cache
                    del self._token_cache[token]
        
        try:
            async with self.redis_manager.get_connection() as redis:
                # Retrieve token from Redis
                token_key = f"auth:token:{token}"
                token_dict = await redis.hgetall(token_key)
                
                if not token_dict:
                    raise AuthenticationError("Invalid or expired token")
                
                token_data = AuthTokenData.from_dict(token_dict)
                
                if not token_data.is_valid():
                    # Clean up expired token
                    await redis.delete(token_key)
                    raise AuthenticationError("Token has expired")
                
                # Cache valid token
                async with self._cache_lock:
                    self._token_cache[token] = token_data
                
                return token_data
                
        except Exception as e:
            if not isinstance(e, AuthenticationError):
                raise AuthenticationError(f"Token validation failed: {e}")
            raise
    
    async def check_permission(self, llm_id: LLMID, operation: OperationType, resource: str) -> bool:
        """
        Check if an LLM has permission to perform an operation on a resource.
        
        Args:
            llm_id: LLM identifier
            operation: Operation to check
            resource: Resource being accessed
            
        Returns:
            bool: True if permission granted, False otherwise
        """
        try:
            permissions = await self._get_llm_permissions(llm_id)
            
            # Check each permission
            for permission in permissions:
                if (permission.is_valid() and 
                    permission.operation == operation and 
                    permission.matches_resource(resource)):
                    
                    await self._audit_access(llm_id, operation, resource, True)
                    return True
            
            # Check role-based permissions
            if await self._check_role_permission(llm_id, operation, resource):
                await self._audit_access(llm_id, operation, resource, True)
                return True
            
            await self._audit_access(llm_id, operation, resource, False, 
                                   details={"reason": "permission_denied"})
            return False
            
        except Exception as e:
            logger.error(f"Permission check failed for {llm_id}: {e}")
            await self._audit_access(llm_id, operation, resource, False, 
                                   details={"reason": "check_error", "error": str(e)})
            return False
    
    async def grant_permission(self, llm_id: LLMID, permission: Permission) -> bool:
        """
        Grant a permission to an LLM.
        
        Args:
            llm_id: LLM identifier
            permission: Permission to grant
            
        Returns:
            bool: True if permission granted successfully
        """
        try:
            async with self.redis_manager.get_connection() as redis:
                # Store permission in Redis
                permission_key = f"permission:{permission.id}"
                await redis.hset(permission_key, mapping=permission.to_dict())
                
                # Add to LLM's permission set
                llm_permissions_key = f"llm:permissions:{llm_id}"
                await redis.sadd(llm_permissions_key, permission.id)
                
                # Invalidate cache
                async with self._cache_lock:
                    if llm_id in self._permission_cache:
                        del self._permission_cache[llm_id]
                
                await self._audit_access(
                    permission.granted_by, OperationType.ADMIN, f"grant_permission:{llm_id}", 
                    True, details={
                        "permission_id": permission.id,
                        "resource": permission.resource,
                        "operation": permission.operation.value
                    }
                )
                
                logger.info(f"Granted permission {permission.id} to LLM {llm_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to grant permission to {llm_id}: {e}")
            return False
    
    async def revoke_permission(self, llm_id: LLMID, permission_id: PermissionID) -> bool:
        """
        Revoke a permission from an LLM.
        
        Args:
            llm_id: LLM identifier
            permission_id: Permission ID to revoke
            
        Returns:
            bool: True if permission revoked successfully
        """
        try:
            async with self.redis_manager.get_connection() as redis:
                # Get permission details for audit
                permission_key = f"permission:{permission_id}"
                permission_data = await redis.hgetall(permission_key)
                
                if permission_data:
                    # Mark permission as inactive
                    await redis.hset(permission_key, "active", "false")
                    
                    # Remove from LLM's permission set
                    llm_permissions_key = f"llm:permissions:{llm_id}"
                    await redis.srem(llm_permissions_key, permission_id)
                    
                    # Invalidate cache
                    async with self._cache_lock:
                        if llm_id in self._permission_cache:
                            del self._permission_cache[llm_id]
                    
                    await self._audit_access(
                        "system", OperationType.ADMIN, f"revoke_permission:{llm_id}", 
                        True, details={
                            "permission_id": permission_id,
                            "resource": permission_data.get("resource"),
                            "operation": permission_data.get("operation")
                        }
                    )
                    
                    logger.info(f"Revoked permission {permission_id} from LLM {llm_id}")
                    return True
                else:
                    logger.warning(f"Permission {permission_id} not found for revocation")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to revoke permission from {llm_id}: {e}")
            return False
    
    async def get_permissions(self, llm_id: LLMID) -> List[Permission]:
        """
        Get all permissions for an LLM.
        
        Args:
            llm_id: LLM identifier
            
        Returns:
            List[Permission]: List of permissions
        """
        return await self._get_llm_permissions(llm_id)
    
    async def assign_role(self, llm_id: LLMID, role: str, granted_by: LLMID) -> bool:
        """
        Assign a role to an LLM.
        
        Args:
            llm_id: LLM identifier
            role: Role name to assign
            granted_by: LLM granting the role
            
        Returns:
            bool: True if role assigned successfully
        """
        if role not in self._roles:
            logger.error(f"Unknown role: {role}")
            return False
        
        try:
            async with self.redis_manager.get_connection() as redis:
                # Store role assignment
                role_key = f"llm:role:{llm_id}"
                await redis.hset(role_key, mapping={
                    "role": role,
                    "granted_by": granted_by,
                    "granted_at": datetime.utcnow().isoformat()
                })
                
                await self._audit_access(
                    granted_by, OperationType.ADMIN, f"assign_role:{llm_id}", 
                    True, details={"role": role}
                )
                
                logger.info(f"Assigned role {role} to LLM {llm_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to assign role to {llm_id}: {e}")
            return False
    
    async def get_role(self, llm_id: LLMID) -> Optional[str]:
        """
        Get the role assigned to an LLM.
        
        Args:
            llm_id: LLM identifier
            
        Returns:
            Optional[str]: Role name if assigned, None otherwise
        """
        try:
            async with self.redis_manager.get_connection() as redis:
                role_key = f"llm:role:{llm_id}"
                role_data = await redis.hgetall(role_key)
                return role_data.get("role")
                
        except Exception as e:
            logger.error(f"Failed to get role for {llm_id}: {e}")
            return None
    
    async def create_llm_credentials(self, llm_id: LLMID, secret: str) -> LLMCredentials:
        """
        Create and store credentials for an LLM.
        
        Args:
            llm_id: LLM identifier
            secret: Secret for authentication
            
        Returns:
            LLMCredentials: Created credentials
        """
        credentials = LLMCredentials.create(llm_id, secret)
        
        try:
            async with self.redis_manager.get_connection() as redis:
                # Store credentials
                creds_key = f"llm:credentials:{llm_id}"
                await redis.hset(creds_key, mapping={
                    "llm_id": credentials.llm_id,
                    "api_key": credentials.api_key,
                    "secret_hash": credentials.secret_hash,
                    "created_at": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Created credentials for LLM {llm_id}")
                return credentials
                
        except Exception as e:
            logger.error(f"Failed to create credentials for {llm_id}: {e}")
            raise PermissionError(f"Failed to create credentials: {e}")
    
    async def _get_llm_permissions(self, llm_id: LLMID) -> List[Permission]:
        """Get all permissions for an LLM with caching"""
        # Check cache first
        async with self._cache_lock:
            if llm_id in self._permission_cache:
                return self._permission_cache[llm_id]
        
        try:
            async with self.redis_manager.get_connection() as redis:
                # Get permission IDs for the LLM
                llm_permissions_key = f"llm:permissions:{llm_id}"
                permission_ids = await redis.smembers(llm_permissions_key)
                
                permissions = []
                for permission_id in permission_ids:
                    permission_key = f"permission:{permission_id}"
                    permission_data = await redis.hgetall(permission_key)
                    
                    if permission_data:
                        try:
                            permission = Permission.from_dict(permission_data)
                            permissions.append(permission)
                        except Exception as e:
                            logger.warning(f"Failed to parse permission {permission_id}: {e}")
                
                # Cache permissions
                async with self._cache_lock:
                    self._permission_cache[llm_id] = permissions
                
                return permissions
                
        except Exception as e:
            logger.error(f"Failed to get permissions for {llm_id}: {e}")
            return []
    
    async def _check_role_permission(self, llm_id: LLMID, operation: OperationType, resource: str) -> bool:
        """Check if LLM's role allows the operation"""
        role = await self.get_role(llm_id)
        if not role or role not in self._roles:
            return False
        
        role_permissions = self._roles[role]
        return operation in role_permissions
    
    async def _audit_access(self, llm_id: LLMID, operation: OperationType, resource: str, 
                          success: bool, ip_address: Optional[str] = None, 
                          user_agent: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Log access attempt for audit purposes"""
        try:
            audit_log = AccessAuditLog.create(
                llm_id=llm_id,
                operation=operation,
                resource=resource,
                success=success,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            async with self.redis_manager.get_connection() as redis:
                # Store audit log
                audit_key = f"audit:log:{audit_log.id}"
                await redis.hset(audit_key, mapping=audit_log.to_dict())
                
                # Add to time-based index for cleanup
                timestamp_key = f"audit:timestamp:{audit_log.timestamp.strftime('%Y-%m-%d')}"
                await redis.sadd(timestamp_key, audit_log.id)
                await redis.expire(timestamp_key, 86400 * 30)  # Keep for 30 days
                
                # Add to LLM-specific audit log
                llm_audit_key = f"audit:llm:{llm_id}"
                await redis.lpush(llm_audit_key, audit_log.id)
                await redis.ltrim(llm_audit_key, 0, 999)  # Keep last 1000 entries
                
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")
    
    async def get_audit_logs(self, llm_id: Optional[LLMID] = None, 
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           limit: int = 100) -> List[AccessAuditLog]:
        """
        Retrieve audit logs with optional filtering.
        
        Args:
            llm_id: Filter by LLM ID
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of logs to return
            
        Returns:
            List[AccessAuditLog]: Filtered audit logs
        """
        try:
            async with self.redis_manager.get_connection() as redis:
                audit_logs = []
                
                if llm_id:
                    # Get logs for specific LLM
                    llm_audit_key = f"audit:llm:{llm_id}"
                    log_ids = await redis.lrange(llm_audit_key, 0, limit - 1)
                else:
                    # Get logs from time-based index
                    log_ids = []
                    if start_time:
                        current_date = start_time.date()
                        end_date = end_time.date() if end_time else datetime.utcnow().date()
                        
                        while current_date <= end_date and len(log_ids) < limit:
                            timestamp_key = f"audit:timestamp:{current_date.strftime('%Y-%m-%d')}"
                            daily_logs = await redis.smembers(timestamp_key)
                            log_ids.extend(daily_logs)
                            current_date += timedelta(days=1)
                    else:
                        # Get recent logs (fallback)
                        today = datetime.utcnow().date()
                        for i in range(7):  # Last 7 days
                            date = today - timedelta(days=i)
                            timestamp_key = f"audit:timestamp:{date.strftime('%Y-%m-%d')}"
                            daily_logs = await redis.smembers(timestamp_key)
                            log_ids.extend(daily_logs)
                            if len(log_ids) >= limit:
                                break
                
                # Retrieve and parse audit logs
                for log_id in log_ids[:limit]:
                    audit_key = f"audit:log:{log_id}"
                    log_data = await redis.hgetall(audit_key)
                    
                    if log_data:
                        try:
                            audit_log = AccessAuditLog.from_dict(log_data)
                            
                            # Apply time filtering
                            if start_time and audit_log.timestamp < start_time:
                                continue
                            if end_time and audit_log.timestamp > end_time:
                                continue
                            
                            audit_logs.append(audit_log)
                        except Exception as e:
                            logger.warning(f"Failed to parse audit log {log_id}: {e}")
                
                # Sort by timestamp (newest first)
                audit_logs.sort(key=lambda x: x.timestamp, reverse=True)
                return audit_logs[:limit]
                
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []
    
    async def cleanup_expired_tokens(self):
        """Clean up expired tokens from cache"""
        async with self._cache_lock:
            expired_tokens = [
                token for token, token_data in self._token_cache.items()
                if token_data.is_expired()
            ]
            
            for token in expired_tokens:
                del self._token_cache[token]
            
            if expired_tokens:
                logger.info(f"Cleaned up {len(expired_tokens)} expired tokens from cache")
    
    async def cleanup_permission_cache(self):
        """Clean up permission cache periodically"""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > self._cache_ttl:
            async with self._cache_lock:
                self._permission_cache.clear()
                self._last_cache_cleanup = current_time
                logger.debug("Cleared permission cache")