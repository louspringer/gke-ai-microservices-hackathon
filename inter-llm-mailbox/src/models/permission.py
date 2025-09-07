"""
Permission and authentication models for the Inter-LLM Mailbox System
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional
import uuid
import hashlib
import secrets

from .enums import OperationType


# Type aliases
LLMID = str
AuthToken = str
PermissionID = str


@dataclass
class LLMCredentials:
    """Credentials for LLM authentication"""
    llm_id: LLMID
    api_key: str
    secret_hash: Optional[str] = None
    
    def verify_secret(self, secret: str) -> bool:
        """Verify the provided secret against stored hash"""
        if not self.secret_hash:
            return False
        
        # Simple hash verification (in production, use proper password hashing)
        computed_hash = hashlib.sha256(secret.encode()).hexdigest()
        return computed_hash == self.secret_hash
    
    @classmethod
    def create(cls, llm_id: LLMID, secret: str) -> 'LLMCredentials':
        """Create credentials with hashed secret"""
        api_key = secrets.token_urlsafe(32)
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        
        return cls(
            llm_id=llm_id,
            api_key=api_key,
            secret_hash=secret_hash
        )


@dataclass
class AuthTokenData:
    """Authentication token data"""
    token: AuthToken
    llm_id: LLMID
    issued_at: datetime
    expires_at: datetime
    permissions: Set[str] = field(default_factory=set)
    
    def is_valid(self) -> bool:
        """Check if token is still valid"""
        return datetime.utcnow() < self.expires_at
    
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.utcnow() >= self.expires_at
    
    @classmethod
    def create(cls, llm_id: LLMID, validity_hours: int = 24) -> 'AuthTokenData':
        """Create a new auth token"""
        now = datetime.utcnow()
        token = secrets.token_urlsafe(32)
        
        return cls(
            token=token,
            llm_id=llm_id,
            issued_at=now,
            expires_at=now + timedelta(hours=validity_hours)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'token': self.token,
            'llm_id': self.llm_id,
            'issued_at': self.issued_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'permissions': list(self.permissions)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthTokenData':
        """Create from dictionary"""
        return cls(
            token=data['token'],
            llm_id=data['llm_id'],
            issued_at=datetime.fromisoformat(data['issued_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            permissions=set(data.get('permissions', []))
        )


@dataclass
class Permission:
    """Permission for mailbox operations"""
    id: PermissionID
    llm_id: LLMID
    resource: str  # mailbox name, topic, or wildcard pattern
    operation: OperationType
    granted_at: datetime
    granted_by: LLMID
    expires_at: Optional[datetime] = None
    active: bool = True
    
    @classmethod
    def create(cls,
               llm_id: LLMID,
               resource: str,
               operation: OperationType,
               granted_by: LLMID,
               expires_hours: Optional[int] = None) -> 'Permission':
        """Create a new permission"""
        now = datetime.utcnow()
        expires_at = None
        if expires_hours:
            expires_at = now + timedelta(hours=expires_hours)
        
        return cls(
            id=str(uuid.uuid4()),
            llm_id=llm_id,
            resource=resource,
            operation=operation,
            granted_at=now,
            granted_by=granted_by,
            expires_at=expires_at
        )
    
    def is_valid(self) -> bool:
        """Check if permission is still valid"""
        if not self.active:
            return False
        
        if self.expires_at and datetime.utcnow() >= self.expires_at:
            return False
        
        return True
    
    def matches_resource(self, resource: str) -> bool:
        """Check if permission applies to a resource"""
        if self.resource == "*":  # Global permission
            return True
        
        # Simple wildcard matching
        import fnmatch
        return fnmatch.fnmatch(resource, self.resource)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'llm_id': self.llm_id,
            'resource': self.resource,
            'operation': self.operation.value,
            'granted_at': self.granted_at.isoformat(),
            'granted_by': self.granted_by,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Permission':
        """Create from dictionary"""
        expires_at = None
        if data.get('expires_at'):
            expires_at = datetime.fromisoformat(data['expires_at'])
        
        return cls(
            id=data['id'],
            llm_id=data['llm_id'],
            resource=data['resource'],
            operation=OperationType(data['operation']),
            granted_at=datetime.fromisoformat(data['granted_at']),
            granted_by=data['granted_by'],
            expires_at=expires_at,
            active=data.get('active', True)
        )


@dataclass
class AccessAuditLog:
    """Audit log entry for access attempts"""
    id: str
    llm_id: LLMID
    operation: OperationType
    resource: str
    timestamp: datetime
    success: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def create(cls,
               llm_id: LLMID,
               operation: OperationType,
               resource: str,
               success: bool,
               ip_address: Optional[str] = None,
               user_agent: Optional[str] = None,
               details: Optional[Dict[str, Any]] = None) -> 'AccessAuditLog':
        """Create a new audit log entry"""
        return cls(
            id=str(uuid.uuid4()),
            llm_id=llm_id,
            operation=operation,
            resource=resource,
            timestamp=datetime.utcnow(),
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'llm_id': self.llm_id,
            'operation': self.operation.value,
            'resource': self.resource,
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'details': self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessAuditLog':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            llm_id=data['llm_id'],
            operation=OperationType(data['operation']),
            resource=data['resource'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            success=data['success'],
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent'),
            details=data.get('details', {})
        )