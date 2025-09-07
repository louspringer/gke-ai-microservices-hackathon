"""
Subscription data models for the Inter-LLM Mailbox System
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

from .enums import DeliveryMode


# Type aliases
SubscriptionID = str
LLMID = str


@dataclass
class MessageFilter:
    """Filter criteria for subscription messages"""
    content_types: Optional[List[str]] = None
    sender_ids: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    priority_min: Optional[int] = None
    
    def matches(self, message_data: Dict[str, Any]) -> bool:
        """Check if message matches filter criteria"""
        if self.content_types and message_data.get('content_type') not in self.content_types:
            return False
        
        if self.sender_ids and message_data.get('sender_id') not in self.sender_ids:
            return False
        
        if self.priority_min and message_data.get('priority', 0) < self.priority_min:
            return False
        
        if self.keywords:
            payload = str(message_data.get('payload', ''))
            if not any(keyword.lower() in payload.lower() for keyword in self.keywords):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'content_types': self.content_types,
            'sender_ids': self.sender_ids,
            'keywords': self.keywords,
            'priority_min': self.priority_min
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageFilter':
        """Create from dictionary"""
        return cls(
            content_types=data.get('content_types'),
            sender_ids=data.get('sender_ids'),
            keywords=data.get('keywords'),
            priority_min=data.get('priority_min')
        )


@dataclass
class SubscriptionOptions:
    """Configuration options for subscriptions"""
    delivery_mode: DeliveryMode = DeliveryMode.REALTIME
    message_filter: Optional[MessageFilter] = None
    max_queue_size: int = 1000
    auto_ack: bool = True
    batch_size: int = 10  # For batch delivery mode
    batch_timeout: int = 30  # Seconds to wait before sending partial batch
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'delivery_mode': self.delivery_mode.value,
            'message_filter': self.message_filter.to_dict() if self.message_filter else None,
            'max_queue_size': self.max_queue_size,
            'auto_ack': self.auto_ack,
            'batch_size': self.batch_size,
            'batch_timeout': self.batch_timeout
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionOptions':
        """Create from dictionary"""
        message_filter = None
        if data.get('message_filter'):
            message_filter = MessageFilter.from_dict(data['message_filter'])
        
        return cls(
            delivery_mode=DeliveryMode(data.get('delivery_mode', 'realtime')),
            message_filter=message_filter,
            max_queue_size=data.get('max_queue_size', 1000),
            auto_ack=data.get('auto_ack', True),
            batch_size=data.get('batch_size', 10),
            batch_timeout=data.get('batch_timeout', 30)
        )


@dataclass
class Subscription:
    """Subscription to a mailbox or topic"""
    id: SubscriptionID
    llm_id: LLMID
    target: str  # mailbox name or topic pattern
    pattern: Optional[str] = None  # for pattern-based subscriptions
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    options: SubscriptionOptions = field(default_factory=SubscriptionOptions)
    active: bool = True
    message_count: int = 0  # Number of messages received
    
    @classmethod
    def create(cls,
               llm_id: LLMID,
               target: str,
               pattern: Optional[str] = None,
               options: Optional[SubscriptionOptions] = None) -> 'Subscription':
        """Create a new subscription with generated ID"""
        return cls(
            id=str(uuid.uuid4()),
            llm_id=llm_id,
            target=target,
            pattern=pattern,
            options=options or SubscriptionOptions()
        )
    
    def matches_target(self, target: str) -> bool:
        """Check if subscription matches a target mailbox/topic"""
        if self.pattern:
            # Simple wildcard pattern matching
            import fnmatch
            return fnmatch.fnmatch(target, self.pattern)
        return self.target == target
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def increment_message_count(self):
        """Increment received message counter"""
        self.message_count += 1
        self.update_activity()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'llm_id': self.llm_id,
            'target': self.target,
            'pattern': self.pattern,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'options': self.options.to_dict(),
            'active': self.active,
            'message_count': self.message_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subscription':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            llm_id=data['llm_id'],
            target=data['target'],
            pattern=data.get('pattern'),
            created_at=datetime.fromisoformat(data['created_at']),
            last_activity=datetime.fromisoformat(data['last_activity']),
            options=SubscriptionOptions.from_dict(data['options']),
            active=data.get('active', True),
            message_count=data.get('message_count', 0)
        )
    
    def validate(self) -> bool:
        """Validate subscription data"""
        if not self.id or not self.llm_id or not self.target:
            return False
        
        if self.options.max_queue_size <= 0:
            return False
        
        if self.options.batch_size <= 0 or self.options.batch_timeout <= 0:
            return False
        
        return True