"""
Enumerations for the Inter-LLM Mailbox System
"""

from enum import Enum, auto


class AddressingMode(Enum):
    """Message addressing modes"""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    TOPIC = "topic"


class ContentType(Enum):
    """Supported message content types"""
    TEXT = "text/plain"
    JSON = "application/json"
    BINARY = "application/octet-stream"
    CODE = "text/code"
    MARKDOWN = "text/markdown"


class Priority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class DeliveryMode(Enum):
    """Subscription delivery modes"""
    REALTIME = "realtime"
    BATCH = "batch"
    POLLING = "polling"


class OperationType(Enum):
    """Permission operation types"""
    READ = "read"
    WRITE = "write"
    SUBSCRIBE = "subscribe"
    ADMIN = "admin"


class DeliveryStatus(Enum):
    """Message delivery status"""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"