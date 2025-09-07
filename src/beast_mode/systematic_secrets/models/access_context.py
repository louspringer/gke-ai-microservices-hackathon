"""Access control models for systematic secrets management."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import uuid


class PrincipalType(str, Enum):
    """Types of principals that can access secrets."""
    USER = "user"
    SERVICE = "service"
    APPLICATION = "application"
    PIPELINE = "pipeline"
    SYSTEM = "system"


class AccessLevel(str, Enum):
    """Levels of access to secrets."""
    READ = "read"
    WRITE = "write"
    ROTATE = "rotate"
    DELETE = "delete"
    ADMIN = "admin"


class AuthenticationMethod(str, Enum):
    """Methods of authentication."""
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    MFA = "mfa"
    API_KEY = "api_key"


@dataclass
class Principal:
    """
    A principal (user, service, etc.) that can access secrets.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    principal_type: PrincipalType = PrincipalType.USER
    email: Optional[str] = None
    groups: Set[str] = field(default_factory=set)
    attributes: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def add_to_group(self, group: str) -> None:
        """Add principal to a group."""
        self.groups.add(group)
    
    def remove_from_group(self, group: str) -> None:
        """Remove principal from a group."""
        self.groups.discard(group)
    
    def has_group(self, group: str) -> bool:
        """Check if principal belongs to a group."""
        return group in self.groups
    
    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()


class AccessPolicy(BaseModel):
    """
    Access policy defining permissions for secrets.
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Principal matching
    principals: Set[str] = Field(default_factory=set)
    groups: Set[str] = Field(default_factory=set)
    principal_types: Set[PrincipalType] = Field(default_factory=set)
    
    # Resource matching
    secret_patterns: Set[str] = Field(default_factory=set)
    environments: Set[str] = Field(default_factory=set)
    secret_types: Set[str] = Field(default_factory=set)
    
    # Permissions
    access_levels: Set[AccessLevel] = Field(default_factory=set)
    
    # Conditions
    time_restrictions: Optional[Dict[str, str]] = None
    ip_restrictions: Optional[List[str]] = None
    require_mfa: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = ""
    is_active: bool = True
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @validator('secret_patterns')
    def validate_secret_patterns(cls, v):
        """Validate secret patterns."""
        for pattern in v:
            if not pattern or len(pattern) > 255:
                raise ValueError('Secret patterns must be non-empty and <= 255 characters')
        return v
    
    def matches_principal(self, principal: Principal) -> bool:
        """
        Check if this policy matches a principal.
        
        Args:
            principal: The principal to check
            
        Returns:
            True if the policy matches the principal
        """
        # Check direct principal match
        if principal.id in self.principals:
            return True
        
        # Check group membership
        if self.groups and principal.groups.intersection(self.groups):
            return True
        
        # Check principal type
        if principal.principal_type in self.principal_types:
            return True
        
        return False
    
    def matches_secret(self, secret_name: str, environment: str, secret_type: str) -> bool:
        """
        Check if this policy matches a secret.
        
        Args:
            secret_name: Name of the secret
            environment: Environment of the secret
            secret_type: Type of the secret
            
        Returns:
            True if the policy matches the secret
        """
        # Check environment
        if self.environments and environment not in self.environments:
            return False
        
        # Check secret type
        if self.secret_types and secret_type not in self.secret_types:
            return False
        
        # Check secret name patterns
        if self.secret_patterns:
            import fnmatch
            for pattern in self.secret_patterns:
                if fnmatch.fnmatch(secret_name, pattern):
                    return True
            return False
        
        return True
    
    def has_access_level(self, level: AccessLevel) -> bool:
        """Check if policy grants a specific access level."""
        return level in self.access_levels or AccessLevel.ADMIN in self.access_levels
    
    def add_principal(self, principal_id: str) -> None:
        """Add a principal to the policy."""
        self.principals.add(principal_id)
    
    def remove_principal(self, principal_id: str) -> None:
        """Remove a principal from the policy."""
        self.principals.discard(principal_id)
    
    def add_group(self, group: str) -> None:
        """Add a group to the policy."""
        self.groups.add(group)
    
    def remove_group(self, group: str) -> None:
        """Remove a group from the policy."""
        self.groups.discard(group)


class AccessContext(BaseModel):
    """
    Context for a secret access request.
    """
    
    principal: Principal
    requested_access: AccessLevel
    secret_name: str
    environment: str
    secret_type: str
    
    # Request metadata
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Authentication info
    authentication_method: Optional[AuthenticationMethod] = None
    mfa_verified: bool = False
    
    # Additional context
    purpose: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def requires_mfa(self, policies: List[AccessPolicy]) -> bool:
        """
        Check if any matching policy requires MFA.
        
        Args:
            policies: List of policies to check
            
        Returns:
            True if MFA is required
        """
        for policy in policies:
            if (policy.matches_principal(self.principal) and 
                policy.matches_secret(self.secret_name, self.environment, self.secret_type) and
                policy.require_mfa):
                return True
        return False
    
    def is_authorized(self, policies: List[AccessPolicy]) -> bool:
        """
        Check if the access request is authorized by any policy.
        
        Args:
            policies: List of policies to check against
            
        Returns:
            True if access is authorized
        """
        for policy in policies:
            if not policy.is_active:
                continue
                
            if (policy.matches_principal(self.principal) and
                policy.matches_secret(self.secret_name, self.environment, self.secret_type) and
                policy.has_access_level(self.requested_access)):
                
                # Check MFA requirement
                if policy.require_mfa and not self.mfa_verified:
                    continue
                
                # Check IP restrictions
                if policy.ip_restrictions and self.source_ip:
                    import ipaddress
                    ip_allowed = False
                    for allowed_ip in policy.ip_restrictions:
                        try:
                            if ipaddress.ip_address(self.source_ip) in ipaddress.ip_network(allowed_ip):
                                ip_allowed = True
                                break
                        except ValueError:
                            continue
                    if not ip_allowed:
                        continue
                
                return True
        
        return False
    
    def to_audit_dict(self) -> Dict[str, str]:
        """Convert to dictionary for audit logging."""
        return {
            'request_id': self.request_id,
            'principal_id': self.principal.id,
            'principal_name': self.principal.name,
            'principal_type': self.principal.principal_type.value,
            'requested_access': self.requested_access.value,
            'secret_name': self.secret_name,
            'environment': self.environment,
            'secret_type': self.secret_type,
            'timestamp': self.timestamp.isoformat(),
            'source_ip': self.source_ip or 'unknown',
            'user_agent': self.user_agent or 'unknown',
            'authentication_method': self.authentication_method.value if self.authentication_method else 'unknown',
            'mfa_verified': str(self.mfa_verified),
            'purpose': self.purpose or 'not_specified',
        }