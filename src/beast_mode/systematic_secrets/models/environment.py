"""Environment models for systematic secrets management."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import uuid


class EnvironmentType(str, Enum):
    """Types of environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    SANDBOX = "sandbox"


class EnvironmentSecurity(str, Enum):
    """Security levels for environments."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EnvironmentConfig:
    """Configuration for an environment."""
    
    # Encryption settings
    encryption_key_id: Optional[str] = None
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_days: int = 90
    
    # Access settings
    require_mfa: bool = False
    allowed_ip_ranges: List[str] = field(default_factory=list)
    session_timeout_minutes: int = 60
    
    # Audit settings
    audit_level: str = "standard"  # minimal, standard, verbose
    retention_days: int = 365
    
    # Backup settings
    backup_enabled: bool = True
    backup_frequency_hours: int = 24
    backup_retention_days: int = 30
    
    # Compliance settings
    compliance_frameworks: Set[str] = field(default_factory=set)
    data_classification: str = "internal"
    
    def add_compliance_framework(self, framework: str) -> None:
        """Add a compliance framework requirement."""
        self.compliance_frameworks.add(framework)
    
    def remove_compliance_framework(self, framework: str) -> None:
        """Remove a compliance framework requirement."""
        self.compliance_frameworks.discard(framework)
    
    def is_high_security(self) -> bool:
        """Check if this is a high security environment."""
        return (self.require_mfa or 
                self.audit_level == "verbose" or
                "SOX" in self.compliance_frameworks or
                "PCI-DSS" in self.compliance_frameworks)


class Environment(BaseModel):
    """
    An environment for secret isolation and management.
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    
    # Environment classification
    environment_type: EnvironmentType
    security_level: EnvironmentSecurity = EnvironmentSecurity.MEDIUM
    
    # Configuration
    config: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    
    # Relationships
    parent_environment: Optional[str] = None  # For environment hierarchies
    child_environments: Set[str] = Field(default_factory=set)
    
    # Access control
    administrators: Set[str] = Field(default_factory=set)
    allowed_principals: Set[str] = Field(default_factory=set)
    allowed_groups: Set[str] = Field(default_factory=set)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = ""
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    modified_by: str = ""
    is_active: bool = True
    
    # Tags and attributes
    tags: Dict[str, str] = Field(default_factory=dict)
    attributes: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @validator('name')
    def validate_name(cls, v):
        """Validate environment name format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Environment name must contain only alphanumeric characters, underscores, and hyphens')
        return v.lower()
    
    @validator('security_level')
    def validate_security_level(cls, v, values):
        """Validate security level matches environment type."""
        if 'environment_type' in values:
            env_type = values['environment_type']
            if env_type == EnvironmentType.PRODUCTION and v not in [EnvironmentSecurity.HIGH, EnvironmentSecurity.CRITICAL]:
                raise ValueError('Production environments must have HIGH or CRITICAL security level')
        return v
    
    def add_administrator(self, principal_id: str) -> None:
        """Add an administrator to the environment."""
        self.administrators.add(principal_id)
        self.allowed_principals.add(principal_id)
        self._update_modified()
    
    def remove_administrator(self, principal_id: str) -> None:
        """Remove an administrator from the environment."""
        self.administrators.discard(principal_id)
        self._update_modified()
    
    def add_principal(self, principal_id: str) -> None:
        """Add a principal to the allowed list."""
        self.allowed_principals.add(principal_id)
        self._update_modified()
    
    def remove_principal(self, principal_id: str) -> None:
        """Remove a principal from the allowed list."""
        self.allowed_principals.discard(principal_id)
        if principal_id in self.administrators:
            self.administrators.discard(principal_id)
        self._update_modified()
    
    def add_group(self, group: str) -> None:
        """Add a group to the allowed list."""
        self.allowed_groups.add(group)
        self._update_modified()
    
    def remove_group(self, group: str) -> None:
        """Remove a group from the allowed list."""
        self.allowed_groups.discard(group)
        self._update_modified()
    
    def is_principal_allowed(self, principal_id: str, groups: Optional[Set[str]] = None) -> bool:
        """
        Check if a principal is allowed access to this environment.
        
        Args:
            principal_id: The principal ID to check
            groups: Optional set of groups the principal belongs to
            
        Returns:
            True if the principal is allowed access
        """
        # Check direct principal access
        if principal_id in self.allowed_principals:
            return True
        
        # Check group membership
        if groups and self.allowed_groups.intersection(groups):
            return True
        
        return False
    
    def is_administrator(self, principal_id: str) -> bool:
        """Check if a principal is an administrator of this environment."""
        return principal_id in self.administrators
    
    def add_child_environment(self, child_id: str) -> None:
        """Add a child environment."""
        self.child_environments.add(child_id)
        self._update_modified()
    
    def remove_child_environment(self, child_id: str) -> None:
        """Remove a child environment."""
        self.child_environments.discard(child_id)
        self._update_modified()
    
    def set_parent_environment(self, parent_id: str) -> None:
        """Set the parent environment."""
        self.parent_environment = parent_id
        self._update_modified()
    
    def add_tag(self, key: str, value: str) -> None:
        """Add a tag to the environment."""
        self.tags[key] = value
        self._update_modified()
    
    def remove_tag(self, key: str) -> None:
        """Remove a tag from the environment."""
        self.tags.pop(key, None)
        self._update_modified()
    
    def set_attribute(self, key: str, value: str) -> None:
        """Set an attribute on the environment."""
        self.attributes[key] = value
        self._update_modified()
    
    def get_attribute(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an attribute value."""
        return self.attributes.get(key, default)
    
    def requires_mfa(self) -> bool:
        """Check if this environment requires MFA."""
        return (self.config.require_mfa or 
                self.security_level in [EnvironmentSecurity.HIGH, EnvironmentSecurity.CRITICAL])
    
    def get_audit_level(self) -> str:
        """Get the audit level for this environment."""
        if self.security_level == EnvironmentSecurity.CRITICAL:
            return "verbose"
        elif self.security_level == EnvironmentSecurity.HIGH:
            return "standard"
        else:
            return self.config.audit_level
    
    def is_production_like(self) -> bool:
        """Check if this is a production-like environment."""
        return self.environment_type in [EnvironmentType.PRODUCTION, EnvironmentType.STAGING]
    
    def get_encryption_requirements(self) -> Dict[str, str]:
        """Get encryption requirements for this environment."""
        return {
            'algorithm': self.config.encryption_algorithm,
            'key_rotation_days': str(self.config.key_rotation_days),
            'key_id': self.config.encryption_key_id or f"env-{self.name}-key",
        }
    
    def _update_modified(self) -> None:
        """Update the last modified timestamp."""
        self.last_modified = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'environment_type': self.environment_type.value,
            'security_level': self.security_level.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'tags': self.tags,
            'attributes': self.attributes,
            'requires_mfa': self.requires_mfa(),
            'audit_level': self.get_audit_level(),
            'is_production_like': self.is_production_like(),
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"Environment(name={self.name}, type={self.environment_type}, security={self.security_level})"