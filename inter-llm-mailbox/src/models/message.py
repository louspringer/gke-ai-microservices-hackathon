"""
Message data models for the Inter-LLM Mailbox System
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
import uuid
import json
import base64
import hashlib
import re

from .enums import AddressingMode, ContentType, Priority


# Type aliases
MessageID = str
LLMID = str

# Message size limits (in bytes)
MAX_MESSAGE_SIZE = 16 * 1024 * 1024  # 16MB total message size
MAX_PAYLOAD_SIZE = 15 * 1024 * 1024  # 15MB payload size
MAX_METADATA_SIZE = 1024 * 1024      # 1MB metadata size
MAX_TEXT_LENGTH = 1024 * 1024        # 1MB for text content
MAX_JSON_SIZE = 10 * 1024 * 1024     # 10MB for JSON content

# Validation patterns
VALID_MESSAGE_ID_PATTERN = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
VALID_LLM_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
VALID_TARGET_PATTERN = re.compile(r'^[a-zA-Z0-9._-]{1,256}$')


class MessageValidationError(Exception):
    """Exception raised when message validation fails"""
    
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error in field '{field}': {message}")


@dataclass
class ValidationResult:
    """Result of message validation"""
    is_valid: bool
    errors: List[MessageValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, field: str, message: str, value: Any = None):
        """Add a validation error"""
        self.is_valid = False
        self.errors.append(MessageValidationError(field, message, value))
    
    def add_warning(self, message: str):
        """Add a validation warning"""
        self.warnings.append(message)


@dataclass
class RetryPolicy:
    """Configuration for message retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class EncryptionConfig:
    """Configuration for message encryption"""
    enabled: bool = False
    algorithm: str = "AES-256-GCM"
    key_id: Optional[str] = None


@dataclass
class RoutingInfo:
    """Message routing information"""
    addressing_mode: AddressingMode
    target: str  # mailbox name or topic
    priority: Priority = Priority.NORMAL
    ttl: Optional[int] = None  # Time to live in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'addressing_mode': self.addressing_mode.value,
            'target': self.target,
            'priority': self.priority.value,
            'ttl': self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoutingInfo':
        """Create from dictionary"""
        return cls(
            addressing_mode=AddressingMode(data['addressing_mode']),
            target=data['target'],
            priority=Priority(data['priority']),
            ttl=data.get('ttl')
        )


@dataclass
class DeliveryOptions:
    """Message delivery configuration"""
    persistence: bool = True
    confirmation_required: bool = False
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    encryption: Optional[EncryptionConfig] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'persistence': self.persistence,
            'confirmation_required': self.confirmation_required,
            'retry_policy': {
                'max_attempts': self.retry_policy.max_attempts,
                'base_delay': self.retry_policy.base_delay,
                'max_delay': self.retry_policy.max_delay,
                'exponential_base': self.retry_policy.exponential_base,
                'jitter': self.retry_policy.jitter
            },
            'encryption': {
                'enabled': self.encryption.enabled if self.encryption else False,
                'algorithm': self.encryption.algorithm if self.encryption else None,
                'key_id': self.encryption.key_id if self.encryption else None
            } if self.encryption else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeliveryOptions':
        """Create from dictionary"""
        retry_data = data.get('retry_policy', {})
        retry_policy = RetryPolicy(
            max_attempts=retry_data.get('max_attempts', 3),
            base_delay=retry_data.get('base_delay', 1.0),
            max_delay=retry_data.get('max_delay', 60.0),
            exponential_base=retry_data.get('exponential_base', 2.0),
            jitter=retry_data.get('jitter', True)
        )
        
        encryption = None
        if data.get('encryption'):
            enc_data = data['encryption']
            encryption = EncryptionConfig(
                enabled=enc_data.get('enabled', False),
                algorithm=enc_data.get('algorithm', 'AES-256-GCM'),
                key_id=enc_data.get('key_id')
            )
        
        return cls(
            persistence=data.get('persistence', True),
            confirmation_required=data.get('confirmation_required', False),
            retry_policy=retry_policy,
            encryption=encryption
        )


@dataclass
class Message:
    """Core message structure for Inter-LLM communication"""
    id: MessageID
    sender_id: LLMID
    timestamp: datetime
    content_type: ContentType
    payload: Union[str, bytes, Dict[str, Any]]
    metadata: Dict[str, Any]
    routing_info: RoutingInfo
    delivery_options: DeliveryOptions = field(default_factory=DeliveryOptions)
    
    @classmethod
    def create(cls, 
               sender_id: LLMID,
               content: Union[str, bytes, Dict[str, Any]],
               content_type: ContentType,
               routing_info: RoutingInfo,
               metadata: Optional[Dict[str, Any]] = None,
               delivery_options: Optional[DeliveryOptions] = None) -> 'Message':
        """Create a new message with generated ID and timestamp"""
        return cls(
            id=str(uuid.uuid4()),
            sender_id=sender_id,
            timestamp=datetime.utcnow(),
            content_type=content_type,
            payload=content,
            metadata=metadata or {},
            routing_info=routing_info,
            delivery_options=delivery_options or DeliveryOptions()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        payload_serialized = self._serialize_payload()
        
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'timestamp': self.timestamp.isoformat(),
            'content_type': self.content_type.value,
            'payload': payload_serialized,
            'payload_hash': self._calculate_payload_hash(),
            'metadata': self.metadata,
            'routing_info': self.routing_info.to_dict(),
            'delivery_options': self.delivery_options.to_dict(),
            'version': '1.0'  # For future compatibility
        }
    
    def to_redis_hash(self) -> Dict[str, str]:
        """
        Convert message to Redis hash format (all string values)
        Optimized for Redis storage with proper type handling
        """
        data = self.to_dict()
        
        # Convert all values to strings for Redis hash storage
        redis_hash = {}
        for key, value in data.items():
            if isinstance(value, dict):
                redis_hash[key] = json.dumps(value)
            elif isinstance(value, (list, tuple)):
                redis_hash[key] = json.dumps(list(value))
            elif value is None:
                redis_hash[key] = ""
            else:
                redis_hash[key] = str(value)
        
        return redis_hash
    
    def to_redis_json(self) -> str:
        """Convert message to JSON string for Redis storage"""
        return json.dumps(self.to_dict(), separators=(',', ':'))  # Compact JSON
    
    def _serialize_payload(self) -> Union[str, Dict[str, Any]]:
        """Serialize payload based on content type"""
        if self.content_type == ContentType.JSON:
            if isinstance(self.payload, str):
                # Validate it's valid JSON
                try:
                    json.loads(self.payload)
                    return self.payload
                except json.JSONDecodeError:
                    return json.dumps(self.payload)
            else:
                return json.dumps(self.payload)
        
        elif self.content_type == ContentType.BINARY:
            if isinstance(self.payload, bytes):
                return base64.b64encode(self.payload).decode('ascii')
            else:
                raise ValueError(f"Binary payload must be bytes, got {type(self.payload)}")
        
        elif self.content_type in [ContentType.TEXT, ContentType.CODE, ContentType.MARKDOWN]:
            if isinstance(self.payload, str):
                return self.payload
            else:
                return str(self.payload)
        
        else:
            # Fallback to string representation
            return str(self.payload)
    
    def _calculate_payload_hash(self) -> str:
        """Calculate SHA-256 hash of payload for integrity verification"""
        if isinstance(self.payload, bytes):
            data = self.payload
        elif isinstance(self.payload, str):
            data = self.payload.encode('utf-8')
        else:
            data = json.dumps(self.payload, sort_keys=True).encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary with validation"""
        content_type = ContentType(data['content_type'])
        
        # Deserialize payload based on content type
        payload = cls._deserialize_payload(data['payload'], content_type)
        
        # Verify payload integrity if hash is present
        if 'payload_hash' in data:
            expected_hash = data['payload_hash']
            if isinstance(payload, bytes):
                actual_hash = hashlib.sha256(payload).hexdigest()
            elif isinstance(payload, str):
                actual_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            else:
                actual_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
            
            if actual_hash != expected_hash:
                raise ValueError(f"Payload integrity check failed. Expected: {expected_hash}, Got: {actual_hash}")
        
        return cls(
            id=data['id'],
            sender_id=data['sender_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            content_type=content_type,
            payload=payload,
            metadata=data.get('metadata', {}),
            routing_info=RoutingInfo.from_dict(data['routing_info']),
            delivery_options=DeliveryOptions.from_dict(data.get('delivery_options', {}))
        )
    
    @classmethod
    def from_redis_hash(cls, redis_data: Dict[str, str]) -> 'Message':
        """Create message from Redis hash data (all string values)"""
        # Convert Redis hash back to proper types
        data = {}
        for key, value in redis_data.items():
            if key in ['routing_info', 'delivery_options', 'metadata']:
                data[key] = json.loads(value) if value else {}
            elif key == 'timestamp':
                data[key] = value
            elif key in ['payload_hash', 'id', 'sender_id', 'content_type', 'payload', 'version']:
                data[key] = value
            else:
                data[key] = value
        
        return cls.from_dict(data)
    
    @classmethod
    def from_redis_json(cls, json_str: str) -> 'Message':
        """Create message from Redis JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def _deserialize_payload(cls, payload_data: Any, content_type: ContentType) -> Union[str, bytes, Dict[str, Any], List[Any]]:
        """Deserialize payload based on content type"""
        if content_type == ContentType.JSON:
            if isinstance(payload_data, str):
                return json.loads(payload_data)
            else:
                return payload_data
        
        elif content_type == ContentType.BINARY:
            if isinstance(payload_data, str):
                return base64.b64decode(payload_data)
            else:
                return payload_data
        
        elif content_type in [ContentType.TEXT, ContentType.CODE, ContentType.MARKDOWN]:
            return str(payload_data)
        
        else:
            return payload_data
    
    def validate(self, strict: bool = True) -> ValidationResult:
        """
        Comprehensive message validation
        
        Args:
            strict: If True, raises exceptions on validation errors
            
        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(is_valid=True)
        
        # Validate message ID
        if not self.id:
            result.add_error("id", "Message ID is required")
        elif not VALID_MESSAGE_ID_PATTERN.match(self.id):
            result.add_error("id", f"Invalid message ID format: {self.id}")
        
        # Validate sender ID
        if not self.sender_id:
            result.add_error("sender_id", "Sender ID is required")
        elif not VALID_LLM_ID_PATTERN.match(self.sender_id):
            result.add_error("sender_id", f"Invalid sender ID format: {self.sender_id}")
        
        # Validate timestamp
        if not self.timestamp:
            result.add_error("timestamp", "Timestamp is required")
        elif not isinstance(self.timestamp, datetime):
            result.add_error("timestamp", "Timestamp must be a datetime object")
        
        # Validate routing info
        if not self.routing_info:
            result.add_error("routing_info", "Routing info is required")
        else:
            if not self.routing_info.target:
                result.add_error("routing_info.target", "Target is required")
            elif not VALID_TARGET_PATTERN.match(self.routing_info.target):
                result.add_error("routing_info.target", f"Invalid target format: {self.routing_info.target}")
        
        # Validate content type and payload
        if not self.content_type:
            result.add_error("content_type", "Content type is required")
        else:
            self._validate_payload(result)
        
        # Validate metadata
        if self.metadata:
            self._validate_metadata(result)
        
        # Validate overall message size
        try:
            total_size = self.size_bytes()
            if total_size > MAX_MESSAGE_SIZE:
                result.add_error("size", f"Message size {total_size} exceeds maximum {MAX_MESSAGE_SIZE} bytes")
        except Exception as e:
            result.add_error("size", f"Error calculating message size: {str(e)}")
        
        # Add warnings for large messages
        if result.is_valid:
            try:
                size = self.size_bytes()
                if size > MAX_MESSAGE_SIZE * 0.8:  # 80% of max size
                    result.add_warning(f"Message size {size} is approaching maximum limit")
            except Exception:
                pass
        
        if strict and not result.is_valid:
            raise result.errors[0]
        
        return result
    
    def _validate_payload(self, result: ValidationResult):
        """Validate payload based on content type"""
        if self.payload is None:
            result.add_error("payload", "Payload cannot be None")
            return
        
        if self.content_type == ContentType.TEXT:
            if not isinstance(self.payload, str):
                result.add_error("payload", f"TEXT content must be string, got {type(self.payload)}")
            elif len(self.payload.encode('utf-8')) > MAX_TEXT_LENGTH:
                result.add_error("payload", f"TEXT content exceeds maximum length {MAX_TEXT_LENGTH} bytes")
        
        elif self.content_type == ContentType.JSON:
            if isinstance(self.payload, str):
                try:
                    json.loads(self.payload)
                except json.JSONDecodeError as e:
                    result.add_error("payload", f"Invalid JSON string: {str(e)}")
            elif not isinstance(self.payload, (dict, list)):
                result.add_error("payload", f"JSON content must be dict, list, or valid JSON string, got {type(self.payload)}")
            
            # Check JSON size
            try:
                json_str = json.dumps(self.payload) if not isinstance(self.payload, str) else self.payload
                if len(json_str.encode('utf-8')) > MAX_JSON_SIZE:
                    result.add_error("payload", f"JSON content exceeds maximum size {MAX_JSON_SIZE} bytes")
            except Exception as e:
                result.add_error("payload", f"Error serializing JSON: {str(e)}")
        
        elif self.content_type == ContentType.BINARY:
            if not isinstance(self.payload, bytes):
                result.add_error("payload", f"BINARY content must be bytes, got {type(self.payload)}")
            elif len(self.payload) > MAX_PAYLOAD_SIZE:
                result.add_error("payload", f"BINARY content exceeds maximum size {MAX_PAYLOAD_SIZE} bytes")
        
        elif self.content_type in [ContentType.CODE, ContentType.MARKDOWN]:
            if not isinstance(self.payload, str):
                result.add_error("payload", f"{self.content_type.value} content must be string, got {type(self.payload)}")
            elif len(self.payload.encode('utf-8')) > MAX_TEXT_LENGTH:
                result.add_error("payload", f"{self.content_type.value} content exceeds maximum length {MAX_TEXT_LENGTH} bytes")
    
    def _validate_metadata(self, result: ValidationResult):
        """Validate metadata structure and size"""
        if not isinstance(self.metadata, dict):
            result.add_error("metadata", f"Metadata must be dict, got {type(self.metadata)}")
            return
        
        try:
            metadata_json = json.dumps(self.metadata)
            if len(metadata_json.encode('utf-8')) > MAX_METADATA_SIZE:
                result.add_error("metadata", f"Metadata exceeds maximum size {MAX_METADATA_SIZE} bytes")
        except Exception as e:
            result.add_error("metadata", f"Error serializing metadata: {str(e)}")
        
        # Validate metadata keys and values
        for key, value in self.metadata.items():
            if not isinstance(key, str):
                result.add_error("metadata", f"Metadata keys must be strings, got {type(key)}")
            elif len(key) > 256:
                result.add_error("metadata", f"Metadata key '{key}' exceeds 256 characters")
            
            # Check for reserved metadata keys
            if key.startswith('_system_'):
                result.add_error("metadata", f"Metadata key '{key}' is reserved for system use")
    
    def size_bytes(self) -> int:
        """Calculate accurate message size in bytes"""
        try:
            # Use Redis JSON format for accurate size calculation
            redis_json = self.to_redis_json()
            return len(redis_json.encode('utf-8'))
        except Exception:
            # Fallback to dict serialization
            serialized = self.to_dict()
            return len(json.dumps(serialized).encode('utf-8'))
    
    def payload_size_bytes(self) -> int:
        """Calculate payload size in bytes"""
        if isinstance(self.payload, bytes):
            return len(self.payload)
        elif isinstance(self.payload, str):
            return len(self.payload.encode('utf-8'))
        else:
            return len(json.dumps(self.payload).encode('utf-8'))
    
    def is_large_message(self, threshold: float = 0.8) -> bool:
        """Check if message is approaching size limits"""
        return self.size_bytes() > (MAX_MESSAGE_SIZE * threshold)
    
    def get_content_preview(self, max_length: int = 100) -> str:
        """Get a preview of the message content for logging/debugging"""
        if isinstance(self.payload, str):
            preview = self.payload[:max_length]
            return preview + "..." if len(self.payload) > max_length else preview
        elif isinstance(self.payload, bytes):
            return f"<binary data: {len(self.payload)} bytes>"
        elif isinstance(self.payload, (dict, list)):
            json_str = json.dumps(self.payload)
            preview = json_str[:max_length]
            return preview + "..." if len(json_str) > max_length else preview
        else:
            str_repr = str(self.payload)
            preview = str_repr[:max_length]
            return preview + "..." if len(str_repr) > max_length else preview
    
    def add_system_metadata(self, key: str, value: Any):
        """Add system metadata (prefixed with _system_)"""
        system_key = f"_system_{key}"
        self.metadata[system_key] = value
    
    def get_system_metadata(self, key: str) -> Any:
        """Get system metadata value"""
        system_key = f"_system_{key}"
        return self.metadata.get(system_key)
    
    def clone(self, new_id: bool = True) -> 'Message':
        """Create a copy of the message, optionally with new ID"""
        data = self.to_dict()
        if new_id:
            data['id'] = str(uuid.uuid4())
        return Message.from_dict(data)