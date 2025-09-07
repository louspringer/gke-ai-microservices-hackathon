"""Secret data models with comprehensive validation and metadata."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import uuid


class SecretType(str, Enum):
    """Types of secrets supported by the system."""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    TOKEN = "token"
    CONNECTION_STRING = "connection_string"
    GENERIC = "generic"


class SecretStatus(str, Enum):
    """Status of a secret in its lifecycle."""
    ACTIVE = "active"
    PENDING_ROTATION = "pending_rotation"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


@dataclass
class SecretMetadata:
    """Metadata associated with a secret."""
    created_at: datetime
    created_by: str
    last_accessed: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    rotation_count: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None
    
    def add_tag(self, key: str, value: str) -> None:
        """Add a tag to the secret metadata."""
        self.tags[key] = value
    
    def remove_tag(self, key: str) -> None:
        """Remove a tag from the secret metadata."""
        self.tags.pop(key, None)
    
    def update_access_time(self) -> None:
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.utcnow()
    
    def update_rotation_info(self) -> None:
        """Update rotation metadata."""
        self.last_rotated = datetime.utcnow()
        self.rotation_count += 1


class Secret(BaseModel):
    """
    A secret with comprehensive validation and metadata.
    
    This class represents a secret in the systematic secrets management system,
    providing validation, encryption support, and comprehensive metadata tracking.
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    secret_type: SecretType
    environment: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    status: SecretStatus = SecretStatus.ACTIVE
    metadata: SecretMetadata
    expires_at: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    @validator('name')
    def validate_name(cls, v):
        """Validate secret name format."""
        if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
            raise ValueError('Secret name must contain only alphanumeric characters, underscores, hyphens, and dots')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment name."""
        allowed_envs = {'development', 'staging', 'production', 'test'}
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {allowed_envs}')
        return v
    
    @validator('expires_at')
    def validate_expiration(cls, v):
        """Validate expiration date is in the future."""
        if v and v <= datetime.utcnow():
            raise ValueError('Expiration date must be in the future')
        return v
    
    def is_expired(self) -> bool:
        """Check if the secret has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if the secret is active and not expired."""
        return self.status == SecretStatus.ACTIVE and not self.is_expired()
    
    def needs_rotation(self, rotation_policy: Optional['RotationPolicy'] = None) -> bool:
        """
        Check if the secret needs rotation based on policy.
        
        Args:
            rotation_policy: Optional rotation policy to check against
            
        Returns:
            True if rotation is needed, False otherwise
        """
        if self.status in [SecretStatus.REVOKED, SecretStatus.ROTATING]:
            return False
            
        if not rotation_policy:
            return self.status == SecretStatus.PENDING_ROTATION
            
        if not self.metadata.last_rotated:
            # Never rotated, check if it's older than max age
            age = datetime.utcnow() - self.metadata.created_at
            return age > rotation_policy.max_age
            
        # Check if it's time for rotation
        time_since_rotation = datetime.utcnow() - self.metadata.last_rotated
        return time_since_rotation > rotation_policy.rotation_interval
    
    def mark_for_rotation(self) -> None:
        """Mark the secret for rotation."""
        if self.status == SecretStatus.ACTIVE:
            self.status = SecretStatus.PENDING_ROTATION
    
    def start_rotation(self) -> None:
        """Mark the secret as currently rotating."""
        self.status = SecretStatus.ROTATING
    
    def complete_rotation(self, new_value: str) -> None:
        """Complete rotation with new value."""
        self.value = new_value
        self.status = SecretStatus.ACTIVE
        self.metadata.update_rotation_info()
    
    def revoke(self) -> None:
        """Revoke the secret."""
        self.status = SecretStatus.REVOKED
    
    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        """
        Convert secret to dictionary representation.
        
        Args:
            include_value: Whether to include the secret value
            
        Returns:
            Dictionary representation of the secret
        """
        data = self.dict()
        if not include_value:
            data.pop('value', None)
        return data
    
    def __str__(self) -> str:
        """String representation without exposing the secret value."""
        return f"Secret(id={self.id}, name={self.name}, type={self.secret_type}, env={self.environment})"
    
    def __repr__(self) -> str:
        """Representation without exposing the secret value."""
        return self.__str__()