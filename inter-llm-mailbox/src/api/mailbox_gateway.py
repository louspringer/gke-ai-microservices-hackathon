"""
Inter-LLM Mailbox Gateway

High-performance API gateway for inter-LLM communication with comprehensive
routing, authentication, and real-time messaging capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import redis.asyncio as redis
from contextlib import asynccontextmanager

from ..core.message_router import MessageRouter, MessagePriority
from ..core.permission_manager import PermissionManager, Permission
from ..core.subscription_manager import SubscriptionManager
from ..core.real_time_delivery import RealTimeDelivery
from ..core.offline_message_handler import OfflineMessageHandler
from ..core.redis_manager import RedisManager
from ..core.circuit_breaker import CircuitBreaker
from ..core.resilience_manager import ResilienceManager


logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Message types for API"""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    TOPIC = "topic"
    SYSTEM = "system"


class DeliveryMode(str, Enum):
    """Message delivery modes"""
    IMMEDIATE = "immediate"
    PERSISTENT = "persistent"
    BEST_EFFORT = "best_effort"


# Pydantic models for API
class SendMessageRequest(BaseModel):
    """Request model for sending messages"""
    recipient_id: Optional[str] = None
    topic: Optional[str] = None
    message_type: MessageType
    content: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.IMMEDIATE
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    """Response model for message operations"""
    message_id: str
    status: str
    timestamp: datetime
    delivery_info: Dict[str, Any] = Field(default_factory=dict)


class SubscriptionRequest(BaseModel):
    """Request model for subscriptions"""
    topic: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    delivery_options: Dict[str, Any] = Field(default_factory=dict)


class HealthStatus(BaseModel):
    """Health status response"""
    status: str
    timestamp: datetime
    components: Dict[str, str]
    metrics: Dict[str, Any]


@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    connection_id: str
    agent_id: str
    connected_at: datetime
    last_activity: datetime
    subscriptions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'connection_id': self.connection_id,
            'agent_id': self.agent_id,
            'connected_at': self.connected_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'subscriptions': self.subscriptions
        }


class MailboxGateway:
    """
    High-performance API gateway for inter-LLM communication.
    
    Features:
    - RESTful API for message operations
    - WebSocket support for real-time messaging
    - Topic-based pub/sub messaging
    - Authentication and authorization
    - Circuit breaker and resilience patterns
    - Comprehensive monitoring and metrics
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        # Core components
        self.redis_manager = RedisManager(redis_url)
        self.message_router = MessageRouter(self.redis_manager)
        self.permission_manager = PermissionManager(self.redis_manager)
        self.subscription_manager = SubscriptionManager(self.redis_manager)
        self.real_time_delivery = RealTimeDelivery(self.redis_manager)
        self.offline_handler = OfflineMessageHandler(self.redis_manager)
        
        # Resilience components
        self.circuit_breaker = CircuitBreaker()
        self.resilience_manager = ResilienceManager()
        
        # Connection management
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        
        # Security
        self.security = HTTPBearer()
        
        # Metrics
        self.metrics = {
            'messages_sent': 0,
            'messages_received': 0,
            'active_connections': 0,
            'total_connections': 0,
            'errors': 0
        }
        
        logger.info("Mailbox Gateway initialized")
    
    async def initialize(self):
        """Initialize the gateway and all components"""
        try:
            await self.redis_manager.initialize()
            await self.message_router.initialize()
            await self.permission_manager.initialize()
            await self.subscription_manager.initialize()
            await self.real_time_delivery.initialize()
            await self.offline_handler.initialize()
            
            logger.info("Mailbox Gateway initialization completed")
        except Exception as e:
            logger.error(f"Gateway initialization failed: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Close all WebSocket connections
            for connection_id, websocket in self.active_connections.items():
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Failed to close connection {connection_id}: {e}")
            
            # Cleanup components
            await self.redis_manager.cleanup()
            
            logger.info("Mailbox Gateway cleanup completed")
        except Exception as e:
            logger.error(f"Gateway cleanup failed: {e}")


# FastAPI application with lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    gateway = app.state.gateway
    await gateway.initialize()
    yield
    # Shutdown
    await gateway.cleanup()


# Create FastAPI application
def create_app(redis_url: str = "redis://localhost:6379") -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="Inter-LLM Mailbox Gateway",
        description="High-performance API gateway for inter-LLM communication",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize gateway
    gateway = MailboxGateway(redis_url)
    app.state.gateway = gateway
    
    # Authentication dependency
    async def get_current_agent(credentials: HTTPAuthorizationCredentials = Depends(gateway.security)) -> str:
        """Extract agent ID from authorization header"""
        # In production, this would validate the token and extract agent ID
        # For now, we'll use a simple approach
        token = credentials.credentials
        if not token:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # Extract agent ID from token (simplified)
        # In production, decode JWT or validate with auth service
        agent_id = token.split(":")[-1] if ":" in token else token
        return agent_id
    
    # API Routes
    
    @app.get("/health", response_model=HealthStatus)
    async def health_check():
        """Health check endpoint"""
        try:
            # Check component health
            components = {
                'redis': 'healthy' if await gateway.redis_manager.health_check() else 'unhealthy',
                'message_router': 'healthy',
                'permission_manager': 'healthy',
                'subscription_manager': 'healthy'
            }
            
            return HealthStatus(
                status='healthy' if all(status == 'healthy' for status in components.values()) else 'degraded',
                timestamp=datetime.utcnow(),
                components=components,
                metrics=gateway.metrics
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail="Health check failed")
    
    @app.post("/messages/send", response_model=MessageResponse)
    async def send_message(
        request: SendMessageRequest,
        agent_id: str = Depends(get_current_agent)
    ):
        """Send a message"""
        try:
            # Validate request
            if request.message_type == MessageType.DIRECT and not request.recipient_id:
                raise HTTPException(status_code=400, detail="recipient_id required for direct messages")
            
            if request.message_type == MessageType.TOPIC and not request.topic:
                raise HTTPException(status_code=400, detail="topic required for topic messages")
            
            # Check permissions
            if request.message_type == MessageType.DIRECT:
                has_permission = await gateway.permission_manager.check_permission(
                    agent_id, Permission.SEND_MESSAGE, request.recipient_id
                )
            else:
                has_permission = await gateway.permission_manager.check_permission(
                    agent_id, Permission.PUBLISH_TOPIC, request.topic
                )
            
            if not has_permission:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            # Create message
            message_data = {
                'sender_id': agent_id,
                'recipient_id': request.recipient_id,
                'topic': request.topic,
                'message_type': request.message_type.value,
                'content': request.content,
                'priority': request.priority.value,
                'delivery_mode': request.delivery_mode.value,
                'ttl_seconds': request.ttl_seconds,
                'metadata': request.metadata,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Route message
            message_id = await gateway.message_router.route_message(message_data)
            
            # Handle real-time delivery for WebSocket connections
            if request.message_type == MessageType.DIRECT and request.recipient_id in gateway.connection_info:
                await gateway._deliver_to_websocket(request.recipient_id, message_data)
            elif request.message_type == MessageType.TOPIC:
                await gateway._broadcast_to_topic_subscribers(request.topic, message_data)
            
            # Update metrics
            gateway.metrics['messages_sent'] += 1
            
            return MessageResponse(
                message_id=message_id,
                status='sent',
                timestamp=datetime.utcnow(),
                delivery_info={'delivery_mode': request.delivery_mode.value}
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            gateway.metrics['errors'] += 1
            raise HTTPException(status_code=500, detail="Failed to send message")
    
    @app.get("/messages/inbox/{agent_id}")
    async def get_inbox(
        agent_id: str,
        limit: int = 50,
        offset: int = 0,
        current_agent: str = Depends(get_current_agent)
    ):
        """Get messages from inbox"""
        try:
            # Check if agent can access this inbox
            if agent_id != current_agent:
                has_permission = await gateway.permission_manager.check_permission(
                    current_agent, Permission.READ_MESSAGES, agent_id
                )
                if not has_permission:
                    raise HTTPException(status_code=403, detail="Cannot access this inbox")
            
            # Get messages from offline handler
            messages = await gateway.offline_handler.get_messages(agent_id, limit, offset)
            
            return {
                'agent_id': agent_id,
                'messages': messages,
                'count': len(messages),
                'limit': limit,
                'offset': offset
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get inbox: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve messages")
    
    @app.post("/subscriptions/subscribe")
    async def subscribe_to_topic(
        request: SubscriptionRequest,
        agent_id: str = Depends(get_current_agent)
    ):
        """Subscribe to a topic"""
        try:
            # Check permissions
            has_permission = await gateway.permission_manager.check_permission(
                agent_id, Permission.SUBSCRIBE_TOPIC, request.topic
            )
            if not has_permission:
                raise HTTPException(status_code=403, detail="Cannot subscribe to this topic")
            
            # Create subscription
            subscription_id = await gateway.subscription_manager.subscribe(
                agent_id, request.topic, request.filters, request.delivery_options
            )
            
            return {
                'subscription_id': subscription_id,
                'agent_id': agent_id,
                'topic': request.topic,
                'status': 'subscribed'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
            raise HTTPException(status_code=500, detail="Failed to create subscription")
    
    @app.delete("/subscriptions/{subscription_id}")
    async def unsubscribe(
        subscription_id: str,
        agent_id: str = Depends(get_current_agent)
    ):
        """Unsubscribe from a topic"""
        try:
            # Unsubscribe
            success = await gateway.subscription_manager.unsubscribe(agent_id, subscription_id)
            
            if not success:
                raise HTTPException(status_code=404, detail="Subscription not found")
            
            return {
                'subscription_id': subscription_id,
                'status': 'unsubscribed'
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            raise HTTPException(status_code=500, detail="Failed to unsubscribe")
    
    @app.get("/subscriptions")
    async def list_subscriptions(agent_id: str = Depends(get_current_agent)):
        """List agent's subscriptions"""
        try:
            subscriptions = await gateway.subscription_manager.get_subscriptions(agent_id)
            
            return {
                'agent_id': agent_id,
                'subscriptions': subscriptions,
                'count': len(subscriptions)
            }
            
        except Exception as e:
            logger.error(f"Failed to list subscriptions: {e}")
            raise HTTPException(status_code=500, detail="Failed to list subscriptions")
    
    # WebSocket endpoint
    @app.websocket("/ws/{agent_id}")
    async def websocket_endpoint(websocket: WebSocket, agent_id: str):
        """WebSocket endpoint for real-time messaging"""
        connection_id = str(uuid.uuid4())
        
        try:
            await websocket.accept()
            
            # Register connection
            gateway.active_connections[connection_id] = websocket
            gateway.connection_info[connection_id] = ConnectionInfo(
                connection_id=connection_id,
                agent_id=agent_id,
                connected_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            gateway.metrics['active_connections'] += 1
            gateway.metrics['total_connections'] += 1
            
            logger.info(f"WebSocket connection established: {agent_id} ({connection_id})")
            
            # Send welcome message
            await websocket.send_json({
                'type': 'connection_established',
                'connection_id': connection_id,
                'agent_id': agent_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Handle incoming messages
            while True:
                try:
                    data = await websocket.receive_json()
                    
                    # Update last activity
                    gateway.connection_info[connection_id].last_activity = datetime.utcnow()
                    
                    # Handle different message types
                    message_type = data.get('type')
                    
                    if message_type == 'ping':
                        await websocket.send_json({
                            'type': 'pong',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    
                    elif message_type == 'subscribe':
                        topic = data.get('topic')
                        if topic:
                            # Add to connection subscriptions
                            if topic not in gateway.connection_info[connection_id].subscriptions:
                                gateway.connection_info[connection_id].subscriptions.append(topic)
                            
                            await websocket.send_json({
                                'type': 'subscription_confirmed',
                                'topic': topic,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                    
                    elif message_type == 'unsubscribe':
                        topic = data.get('topic')
                        if topic and topic in gateway.connection_info[connection_id].subscriptions:
                            gateway.connection_info[connection_id].subscriptions.remove(topic)
                            
                            await websocket.send_json({
                                'type': 'unsubscription_confirmed',
                                'topic': topic,
                                'timestamp': datetime.utcnow().isoformat()
                            })
                    
                    else:
                        await websocket.send_json({
                            'type': 'error',
                            'message': f'Unknown message type: {message_type}',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"WebSocket message handling error: {e}")
                    await websocket.send_json({
                        'type': 'error',
                        'message': 'Message processing failed',
                        'timestamp': datetime.utcnow().isoformat()
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {agent_id} ({connection_id})")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Cleanup connection
            if connection_id in gateway.active_connections:
                del gateway.active_connections[connection_id]
            if connection_id in gateway.connection_info:
                del gateway.connection_info[connection_id]
            
            gateway.metrics['active_connections'] -= 1
    
    # Helper methods for gateway
    async def _deliver_to_websocket(gateway_self, recipient_id: str, message_data: Dict[str, Any]):
        """Deliver message to WebSocket connection"""
        for conn_id, conn_info in gateway_self.connection_info.items():
            if conn_info.agent_id == recipient_id:
                websocket = gateway_self.active_connections.get(conn_id)
                if websocket:
                    try:
                        await websocket.send_json({
                            'type': 'message',
                            'data': message_data,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Failed to deliver WebSocket message: {e}")
    
    async def _broadcast_to_topic_subscribers(gateway_self, topic: str, message_data: Dict[str, Any]):
        """Broadcast message to topic subscribers"""
        for conn_id, conn_info in gateway_self.connection_info.items():
            if topic in conn_info.subscriptions:
                websocket = gateway_self.active_connections.get(conn_id)
                if websocket:
                    try:
                        await websocket.send_json({
                            'type': 'topic_message',
                            'topic': topic,
                            'data': message_data,
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Failed to broadcast to WebSocket: {e}")
    
    # Bind helper methods to gateway
    gateway._deliver_to_websocket = lambda recipient_id, message_data: _deliver_to_websocket(gateway, recipient_id, message_data)
    gateway._broadcast_to_topic_subscribers = lambda topic, message_data: _broadcast_to_topic_subscribers(gateway, topic, message_data)
    
    return app


# Application factory
def create_mailbox_app(redis_url: str = "redis://localhost:6379") -> FastAPI:
    """Create mailbox application"""
    return create_app(redis_url)


if __name__ == "__main__":
    import uvicorn
    
    app = create_mailbox_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)