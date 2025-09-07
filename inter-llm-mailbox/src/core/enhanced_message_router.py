"""
Enhanced Message Router with Real-time Delivery Integration

This module extends the message router to integrate with the real-time delivery
service for immediate message broadcasting to active subscribers.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from .message_router import MessageRouter, RoutingResult
from .realtime_delivery import RealtimeDeliveryService, BroadcastResult
from ..models.message import Message, MessageID, LLMID
from ..models.enums import AddressingMode, DeliveryStatus, DeliveryMode
from .redis_manager import RedisConnectionManager
from .redis_pubsub import RedisPubSubManager
from .subscription_manager import SubscriptionManager


logger = logging.getLogger(__name__)


class EnhancedMessageRouter(MessageRouter):
    """
    Enhanced message router with real-time delivery capabilities.
    
    Extends the base MessageRouter to provide:
    - Real-time message broadcasting to active subscribers
    - Pattern-based subscription support with wildcards
    - Immediate delivery for subscribed LLMs
    """
    
    def __init__(self,
                 redis_manager: RedisConnectionManager,
                 pubsub_manager: RedisPubSubManager,
                 subscription_manager: SubscriptionManager):
        super().__init__(redis_manager, pubsub_manager)
        
        self.subscription_manager = subscription_manager
        self.realtime_delivery = RealtimeDeliveryService(
            redis_manager, pubsub_manager, subscription_manager
        )
        
        # Enhanced routing configuration
        self.enable_realtime_delivery = True
        self.realtime_delivery_timeout = 5.0  # seconds
        
        # Statistics
        self._realtime_stats = {
            'realtime_deliveries': 0,
            'realtime_failures': 0,
            'average_broadcast_latency_ms': 0.0
        }
    
    async def start(self) -> None:
        """Start the enhanced message router"""
        await super().start()
        
        # Start real-time delivery service
        if self.enable_realtime_delivery:
            await self.realtime_delivery.start()
        
        logger.info("Enhanced message router started with real-time delivery")
    
    async def stop(self) -> None:
        """Stop the enhanced message router"""
        # Stop real-time delivery service
        if self.realtime_delivery._running:
            await self.realtime_delivery.stop()
        
        await super().stop()
        logger.info("Enhanced message router stopped")
    
    async def route_message(self, message: Message) -> RoutingResult:
        """
        Enhanced message routing with real-time delivery.
        
        Args:
            message: Message to route
            
        Returns:
            RoutingResult indicating the outcome
        """
        start_time = time.time()
        
        try:
            # First, perform standard routing (persistence, validation, etc.)
            base_result = await super().route_message(message)
            
            # If base routing failed, don't attempt real-time delivery
            if base_result in [RoutingResult.REJECTED, RoutingResult.FAILED]:
                return base_result
            
            # Attempt real-time delivery for active subscribers
            if self.enable_realtime_delivery:
                broadcast_result = await self._attempt_realtime_delivery(message)
                
                # Update statistics
                await self._update_realtime_stats(broadcast_result)
                
                # If we successfully delivered to active subscribers, consider it a success
                if broadcast_result.subscribers_reached > 0:
                    logger.info(f"Message {message.id} delivered in real-time to "
                               f"{broadcast_result.subscribers_reached} subscribers")
                    return RoutingResult.SUCCESS
            
            # Return the base routing result (SUCCESS or QUEUED)
            return base_result
            
        except Exception as e:
            logger.error(f"Error in enhanced message routing for {message.id}: {e}")
            await self._increment_metric('routing_errors')
            return RoutingResult.FAILED
    
    async def _attempt_realtime_delivery(self, message: Message) -> BroadcastResult:
        """Attempt real-time delivery of message to active subscribers"""
        try:
            # Use asyncio.wait_for to enforce timeout
            broadcast_result = await asyncio.wait_for(
                self.realtime_delivery.broadcast_message(message),
                timeout=self.realtime_delivery_timeout
            )
            
            return broadcast_result
            
        except asyncio.TimeoutError:
            logger.warning(f"Real-time delivery timeout for message {message.id}")
            return BroadcastResult(
                message_id=message.id,
                target=message.routing_info.target,
                subscribers_reached=0,
                pattern_matches=0,
                delivery_failures=1,
                latency_ms=self.realtime_delivery_timeout * 1000,
                errors=["Delivery timeout"]
            )
        except Exception as e:
            logger.error(f"Error in real-time delivery for message {message.id}: {e}")
            return BroadcastResult(
                message_id=message.id,
                target=message.routing_info.target,
                subscribers_reached=0,
                pattern_matches=0,
                delivery_failures=1,
                latency_ms=0.0,
                errors=[str(e)]
            )
    
    async def _update_realtime_stats(self, broadcast_result: BroadcastResult) -> None:
        """Update real-time delivery statistics"""
        if broadcast_result.subscribers_reached > 0:
            self._realtime_stats['realtime_deliveries'] += 1
        
        if broadcast_result.delivery_failures > 0:
            self._realtime_stats['realtime_failures'] += 1
        
        # Update average latency
        if self._realtime_stats['realtime_deliveries'] == 1:
            self._realtime_stats['average_broadcast_latency_ms'] = broadcast_result.latency_ms
        else:
            alpha = 0.1  # Smoothing factor
            current_avg = self._realtime_stats['average_broadcast_latency_ms']
            self._realtime_stats['average_broadcast_latency_ms'] = (
                alpha * broadcast_result.latency_ms + (1 - alpha) * current_avg
            )
    
    async def register_llm_handler(self, llm_id: LLMID, handler: Any) -> None:
        """
        Register a delivery handler for an LLM instance.
        
        Args:
            llm_id: ID of the LLM instance
            handler: Message delivery handler function
        """
        await self.realtime_delivery.register_delivery_handler(llm_id, handler)
        logger.info(f"Registered LLM handler for {llm_id}")
    
    async def unregister_llm_handler(self, llm_id: LLMID) -> None:
        """
        Unregister a delivery handler for an LLM instance.
        
        Args:
            llm_id: ID of the LLM instance
        """
        await self.realtime_delivery.unregister_delivery_handler(llm_id)
        logger.info(f"Unregistered LLM handler for {llm_id}")
    
    async def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Get enhanced routing statistics including real-time delivery metrics"""
        base_stats = await self.get_statistics()
        realtime_stats = await self.realtime_delivery.get_delivery_statistics()
        
        return {
            **base_stats,
            'realtime_delivery': realtime_stats,
            'enhanced_routing': self._realtime_stats
        }
    
    async def test_realtime_delivery(self, message: Message) -> BroadcastResult:
        """Test real-time delivery for a message (for debugging/testing)"""
        return await self.realtime_delivery.broadcast_message(message)
    
    async def get_active_subscribers(self, target: str) -> List[Dict[str, Any]]:
        """Get list of active subscribers for a target"""
        subscribers = []
        
        # Get all LLM handlers
        for llm_id in self.realtime_delivery._delivery_handlers.keys():
            llm_subscriptions = await self.subscription_manager.get_active_subscriptions(llm_id)
            
            for subscription in llm_subscriptions:
                if (subscription.target == target or 
                    (subscription.pattern and subscription.matches_target(target))):
                    subscribers.append({
                        'llm_id': llm_id,
                        'subscription_id': subscription.id,
                        'target': subscription.target,
                        'pattern': subscription.pattern,
                        'delivery_mode': subscription.options.delivery_mode.value,
                        'message_count': subscription.message_count,
                        'last_activity': subscription.last_activity.isoformat()
                    })
        
        return subscribers