"""
Topic data models for the Inter-LLM Mailbox System
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import re

# Type aliases
TopicID = str
TopicName = str

# Validation patterns
VALID_TOPIC_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]{1,256}$')


class TopicValidationError(Exception):
    """Exception raised when topic validation fails"""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Topic validation error in field '{field}': {message}")


@dataclass
class TopicMetadata:
    """Metadata for topics"""
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    priority: int = 0
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'tags': self.tags,
            'category': self.category,
            'priority': self.priority,
            'custom_fields': self.custom_fields
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicMetadata':
        """Create from dictionary"""
        return cls(
            tags=data.get('tags', []),
            category=data.get('category'),
            priority=data.get('priority', 0),
            custom_fields=data.get('custom_fields', {})
        )


@dataclass
class TopicPermissions:
    """Permission settings for topics"""
    public_read: bool = True
    public_write: bool = True
    allowed_subscribers: Optional[List[str]] = None
    allowed_publishers: Optional[List[str]] = None
    admin_users: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'public_read': self.public_read,
            'public_write': self.public_write,
            'allowed_subscribers': self.allowed_subscribers,
            'allowed_publishers': self.allowed_publishers,
            'admin_users': self.admin_users
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicPermissions':
        """Create from dictionary"""
        return cls(
            public_read=data.get('public_read', True),
            public_write=data.get('public_write', True),
            allowed_subscribers=data.get('allowed_subscribers'),
            allowed_publishers=data.get('allowed_publishers'),
            admin_users=data.get('admin_users')
        )
    
    def can_subscribe(self, llm_id: str) -> bool:
        """Check if LLM can subscribe to topic"""
        if not self.public_read:
            return (self.allowed_subscribers and llm_id in self.allowed_subscribers) or \
                   (self.admin_users and llm_id in self.admin_users)
        return True
    
    def can_publish(self, llm_id: str) -> bool:
        """Check if LLM can publish to topic"""
        if not self.public_write:
            return (self.allowed_publishers and llm_id in self.allowed_publishers) or \
                   (self.admin_users and llm_id in self.admin_users)
        return True
    
    def is_admin(self, llm_id: str) -> bool:
        """Check if LLM is admin for topic"""
        return self.admin_users and llm_id in self.admin_users


@dataclass
class TopicStatistics:
    """Statistics for a topic"""
    total_messages: int = 0
    total_subscribers: int = 0
    messages_today: int = 0
    messages_this_week: int = 0
    peak_subscribers: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'total_messages': self.total_messages,
            'total_subscribers': self.total_subscribers,
            'messages_today': self.messages_today,
            'messages_this_week': self.messages_this_week,
            'peak_subscribers': self.peak_subscribers,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicStatistics':
        """Create from dictionary"""
        last_message_at = None
        if data.get('last_message_at'):
            last_message_at = datetime.fromisoformat(data['last_message_at'])
        
        return cls(
            total_messages=data.get('total_messages', 0),
            total_subscribers=data.get('total_subscribers', 0),
            messages_today=data.get('messages_today', 0),
            messages_this_week=data.get('messages_this_week', 0),
            peak_subscribers=data.get('peak_subscribers', 0),
            last_message_at=last_message_at,
            created_at=datetime.fromisoformat(data.get('created_at', datetime.utcnow().isoformat()))
        )
    
    def record_message(self):
        """Record a new message"""
        self.total_messages += 1
        self.messages_today += 1
        self.messages_this_week += 1
        self.last_message_at = datetime.utcnow()
    
    def update_subscriber_count(self, count: int):
        """Update subscriber count and track peak"""
        self.total_subscribers = count
        if count > self.peak_subscribers:
            self.peak_subscribers = count


@dataclass
class TopicInfo:
    """Complete topic information including all metadata"""
    id: TopicID
    name: TopicName
    description: Optional[str] = None
    parent_topic: Optional[TopicName] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
    
    # Configuration
    auto_cleanup: bool = True
    cleanup_after_hours: int = 24
    max_subscribers: int = 1000
    message_retention_hours: int = 168  # 7 days
    
    # Extended information
    metadata: TopicMetadata = field(default_factory=TopicMetadata)
    permissions: TopicPermissions = field(default_factory=TopicPermissions)
    statistics: TopicStatistics = field(default_factory=TopicStatistics)
    
    @classmethod
    def create(cls, 
               name: TopicName,
               description: Optional[str] = None,
               parent_topic: Optional[TopicName] = None,
               **kwargs) -> 'TopicInfo':
        """Create a new topic with generated ID"""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            parent_topic=parent_topic,
            **kwargs
        )
    
    @property
    def is_hierarchical(self) -> bool:
        """Check if topic is part of a hierarchy"""
        return '.' in self.name or self.parent_topic is not None
    
    @property
    def hierarchy_parts(self) -> List[str]:
        """Get hierarchy parts (e.g., 'ai.ml.training' -> ['ai', 'ml', 'training'])"""
        return self.name.split('.')
    
    @property
    def parent_topics(self) -> List[str]:
        """Get all parent topic names in hierarchy"""
        parts = self.hierarchy_parts
        parents = []
        for i in range(1, len(parts)):
            parent = '.'.join(parts[:i])
            parents.append(parent)
        return parents
    
    @property
    def depth(self) -> int:
        """Get hierarchy depth (0 for root topics)"""
        return len(self.hierarchy_parts) - 1
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if topic matches a subscription pattern"""
        import fnmatch
        return fnmatch.fnmatch(self.name, pattern)
    
    def is_child_of(self, parent_name: str) -> bool:
        """Check if this topic is a child of the given parent"""
        if self.parent_topic == parent_name:
            return True
        return self.name.startswith(f"{parent_name}.")
    
    def is_ancestor_of(self, child_name: str) -> bool:
        """Check if this topic is an ancestor of the given child"""
        return child_name.startswith(f"{self.name}.")
    
    def get_immediate_children_pattern(self) -> str:
        """Get pattern to match immediate children only"""
        return f"{self.name}.*"
    
    def get_all_descendants_pattern(self) -> str:
        """Get pattern to match all descendants"""
        return f"{self.name}.**"
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.updated_at = datetime.utcnow()
    
    def validate(self) -> bool:
        """Validate topic data"""
        if not self.id or not self.name:
            return False
        
        if not VALID_TOPIC_NAME_PATTERN.match(self.name):
            return False
        
        if self.max_subscribers <= 0:
            return False
        
        if self.cleanup_after_hours <= 0:
            return False
        
        if self.message_retention_hours <= 0:
            return False
        
        # Validate hierarchy depth
        if len(self.hierarchy_parts) > 10:  # Max depth of 10
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_topic': self.parent_topic,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'active': self.active,
            'auto_cleanup': self.auto_cleanup,
            'cleanup_after_hours': self.cleanup_after_hours,
            'max_subscribers': self.max_subscribers,
            'message_retention_hours': self.message_retention_hours,
            'metadata': self.metadata.to_dict(),
            'permissions': self.permissions.to_dict(),
            'statistics': self.statistics.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TopicInfo':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            parent_topic=data.get('parent_topic'),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            active=data.get('active', True),
            auto_cleanup=data.get('auto_cleanup', True),
            cleanup_after_hours=data.get('cleanup_after_hours', 24),
            max_subscribers=data.get('max_subscribers', 1000),
            message_retention_hours=data.get('message_retention_hours', 168),
            metadata=TopicMetadata.from_dict(data.get('metadata', {})),
            permissions=TopicPermissions.from_dict(data.get('permissions', {})),
            statistics=TopicStatistics.from_dict(data.get('statistics', {}))
        )
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary view of the topic"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_topic': self.parent_topic,
            'active': self.active,
            'is_hierarchical': self.is_hierarchical,
            'depth': self.depth,
            'subscriber_count': self.statistics.total_subscribers,
            'message_count': self.statistics.total_messages,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.updated_at.isoformat()
        }


def validate_topic_name(name: str) -> bool:
    """Validate topic name format"""
    if not name or len(name) > 256:
        return False
    
    return VALID_TOPIC_NAME_PATTERN.match(name) is not None


def parse_topic_hierarchy(name: str) -> Dict[str, Any]:
    """Parse topic name into hierarchy information"""
    parts = name.split('.')
    
    return {
        'name': name,
        'parts': parts,
        'depth': len(parts) - 1,
        'root': parts[0] if parts else None,
        'leaf': parts[-1] if parts else None,
        'parents': ['.'.join(parts[:i+1]) for i in range(len(parts)-1)] if len(parts) > 1 else []
    }


def build_topic_tree(topics: List[TopicInfo]) -> Dict[str, Any]:
    """Build a hierarchical tree structure from a list of topics"""
    tree = {}
    
    # Sort topics by hierarchy depth
    sorted_topics = sorted(topics, key=lambda t: t.depth)
    
    for topic in sorted_topics:
        parts = topic.hierarchy_parts
        current = tree
        
        # Navigate/create the tree structure
        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {
                    '_topic': None,
                    '_children': {}
                }
            
            if i == len(parts) - 1:
                # This is the leaf node
                current[part]['_topic'] = topic
            else:
                # Navigate to children
                current = current[part]['_children']
    
    return tree


def find_topic_children(topics: List[TopicInfo], parent_name: str) -> List[TopicInfo]:
    """Find all direct children of a parent topic"""
    children = []
    
    for topic in topics:
        if topic.parent_topic == parent_name or \
           (topic.is_hierarchical and topic.name.startswith(f"{parent_name}.") and 
            topic.name.count('.') == parent_name.count('.') + 1):
            children.append(topic)
    
    return children


def find_topic_descendants(topics: List[TopicInfo], ancestor_name: str) -> List[TopicInfo]:
    """Find all descendants of an ancestor topic"""
    descendants = []
    
    for topic in topics:
        if topic.is_ancestor_of(ancestor_name) or topic.name.startswith(f"{ancestor_name}."):
            descendants.append(topic)
    
    return descendants