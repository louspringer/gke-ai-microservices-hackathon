"""Rotation policy models for systematic secret rotation."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import uuid


class RotationStrategy(str, Enum):
    """Strategies for secret rotation."""
    IMMEDIATE = "immediate"  # Replace immediately
    GRACEFUL = "graceful"    # Overlap period for gradual transition
    BLUE_GREEN = "blue_green"  # Switch between two versions


class RotationTrigger(str, Enum):
    """Triggers that can initiate secret rotation."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    EMERGENCY = "emergency"
    EXPIRATION = "expiration"
    COMPROMISE = "compromise"
    POLICY_CHANGE = "policy_change"


class RotationStatus(str, Enum):
    """Status of a rotation operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RotationWindow:
    """Time window during which rotation can occur."""
    start_hour: int = 0  # 0-23
    end_hour: int = 23   # 0-23
    days_of_week: List[int] = field(default_factory=lambda: list(range(7)))  # 0=Monday, 6=Sunday
    timezone: str = "UTC"
    
    def __post_init__(self):
        """Validate rotation window parameters."""
        if not (0 <= self.start_hour <= 23):
            raise ValueError("start_hour must be between 0 and 23")
        if not (0 <= self.end_hour <= 23):
            raise ValueError("end_hour must be between 0 and 23")
        if not all(0 <= day <= 6 for day in self.days_of_week):
            raise ValueError("days_of_week must contain values between 0 and 6")
    
    def is_in_window(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if the given datetime is within the rotation window.
        
        Args:
            dt: Datetime to check (defaults to current UTC time)
            
        Returns:
            True if the datetime is within the rotation window
        """
        if dt is None:
            dt = datetime.utcnow()
        
        # Check day of week
        if dt.weekday() not in self.days_of_week:
            return False
        
        # Check hour range
        if self.start_hour <= self.end_hour:
            return self.start_hour <= dt.hour <= self.end_hour
        else:
            # Crosses midnight
            return dt.hour >= self.start_hour or dt.hour <= self.end_hour


class RotationPolicy(BaseModel):
    """
    Policy defining how and when secrets should be rotated.
    """
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    
    # Rotation timing
    rotation_interval: timedelta = Field(default=timedelta(days=90))
    max_age: timedelta = Field(default=timedelta(days=365))
    
    # Rotation strategy
    strategy: RotationStrategy = RotationStrategy.GRACEFUL
    overlap_period: Optional[timedelta] = Field(default=timedelta(hours=24))
    
    # Rotation window
    rotation_window: Optional[RotationWindow] = None
    
    # Retry configuration
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: timedelta = Field(default=timedelta(minutes=30))
    
    # Notification settings
    notify_before: Optional[timedelta] = Field(default=timedelta(days=7))
    notify_on_failure: bool = True
    notification_recipients: List[str] = Field(default_factory=list)
    
    # Emergency rotation
    allow_emergency_rotation: bool = True
    emergency_approvers: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = ""
    is_active: bool = True
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: v.total_seconds(),
        }
    
    @validator('rotation_interval')
    def validate_rotation_interval(cls, v):
        """Validate rotation interval is reasonable."""
        if v.total_seconds() < 3600:  # Less than 1 hour
            raise ValueError('Rotation interval must be at least 1 hour')
        if v.total_seconds() > 31536000:  # More than 1 year
            raise ValueError('Rotation interval must be less than 1 year')
        return v
    
    @validator('max_age')
    def validate_max_age(cls, v):
        """Validate max age is reasonable."""
        if v.total_seconds() < 86400:  # Less than 1 day
            raise ValueError('Max age must be at least 1 day')
        return v
    
    @validator('overlap_period')
    def validate_overlap_period(cls, v, values):
        """Validate overlap period is reasonable for graceful strategy."""
        if v and 'strategy' in values and values['strategy'] == RotationStrategy.GRACEFUL:
            if v.total_seconds() < 300:  # Less than 5 minutes
                raise ValueError('Overlap period must be at least 5 minutes for graceful rotation')
        return v
    
    def should_rotate(self, secret: 'Secret') -> bool:
        """
        Check if a secret should be rotated based on this policy.
        
        Args:
            secret: The secret to check
            
        Returns:
            True if the secret should be rotated
        """
        if not self.is_active:
            return False
        
        # Check if secret needs rotation based on age
        if secret.needs_rotation(self):
            # Check if we're in a valid rotation window
            if self.rotation_window:
                return self.rotation_window.is_in_window()
            return True
        
        return False
    
    def get_next_rotation_time(self, secret: 'Secret') -> datetime:
        """
        Calculate the next rotation time for a secret.
        
        Args:
            secret: The secret to calculate for
            
        Returns:
            The next rotation time
        """
        if secret.metadata.last_rotated:
            base_time = secret.metadata.last_rotated + self.rotation_interval
        else:
            base_time = secret.metadata.created_at + self.max_age
        
        # If we have a rotation window, adjust to next valid window
        if self.rotation_window:
            while not self.rotation_window.is_in_window(base_time):
                base_time += timedelta(hours=1)
        
        return base_time
    
    def get_notification_time(self, secret: 'Secret') -> Optional[datetime]:
        """
        Calculate when to send rotation notification.
        
        Args:
            secret: The secret to calculate for
            
        Returns:
            The notification time, or None if no notification needed
        """
        if not self.notify_before:
            return None
        
        next_rotation = self.get_next_rotation_time(secret)
        return next_rotation - self.notify_before
    
    def can_emergency_rotate(self, requester: str) -> bool:
        """
        Check if emergency rotation is allowed for a requester.
        
        Args:
            requester: The person requesting emergency rotation
            
        Returns:
            True if emergency rotation is allowed
        """
        if not self.allow_emergency_rotation:
            return False
        
        if not self.emergency_approvers:
            return True  # No specific approvers required
        
        return requester in self.emergency_approvers


@dataclass
class RotationExecution:
    """Tracks the execution of a rotation operation."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    secret_id: str = ""
    policy_id: str = ""
    
    # Execution details
    trigger: RotationTrigger = RotationTrigger.SCHEDULED
    strategy: RotationStrategy = RotationStrategy.GRACEFUL
    status: RotationStatus = RotationStatus.PENDING
    
    # Timing
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Retry tracking
    attempt_count: int = 0
    max_attempts: int = 3
    last_error: Optional[str] = None
    
    # Metadata
    initiated_by: str = ""
    notes: Optional[str] = None
    
    def start_execution(self) -> None:
        """Mark the rotation as started."""
        self.status = RotationStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.attempt_count += 1
    
    def complete_execution(self) -> None:
        """Mark the rotation as completed."""
        self.status = RotationStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def fail_execution(self, error: str) -> None:
        """Mark the rotation as failed."""
        self.status = RotationStatus.FAILED
        self.last_error = error
        self.completed_at = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """Check if the rotation can be retried."""
        return (self.status == RotationStatus.FAILED and 
                self.attempt_count < self.max_attempts)
    
    def cancel_execution(self) -> None:
        """Cancel the rotation."""
        self.status = RotationStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def get_duration(self) -> Optional[timedelta]:
        """Get the execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'secret_id': self.secret_id,
            'policy_id': self.policy_id,
            'trigger': self.trigger.value,
            'strategy': self.strategy.value,
            'status': self.status.value,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'attempt_count': self.attempt_count,
            'max_attempts': self.max_attempts,
            'last_error': self.last_error,
            'initiated_by': self.initiated_by,
            'notes': self.notes,
            'duration_seconds': self.get_duration().total_seconds() if self.get_duration() else None,
        }