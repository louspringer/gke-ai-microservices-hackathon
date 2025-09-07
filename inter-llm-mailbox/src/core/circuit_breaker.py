"""
Circuit Breaker Pattern Implementation for Inter-LLM Mailbox System

This module provides circuit breaker functionality to handle Redis connection
failures and other service failures with graceful degradation.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Number of failures to open circuit
    recovery_timeout: float = 60.0      # Seconds to wait before trying recovery
    success_threshold: int = 3          # Successes needed to close circuit in half-open
    timeout: float = 30.0               # Request timeout in seconds
    expected_exceptions: tuple = (Exception,)  # Exceptions that count as failures
    
    def __post_init__(self):
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be positive")


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_changes: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_state_change(self, old_state: CircuitState, new_state: CircuitState, reason: str):
        """Record a state change"""
        self.state_changes.append({
            'timestamp': time.time(),
            'from_state': old_state.value,
            'to_state': new_state.value,
            'reason': reason
        })
        
        # Keep only last 100 state changes
        if len(self.state_changes) > 100:
            self.state_changes = self.state_changes[-100:]


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for handling service failures.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"Created circuit breaker '{name}' with config: {config}")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            self.stats.total_requests += 1
            
            # Check if circuit should be opened
            if self.stats.state == CircuitState.CLOSED:
                if (self.stats.failure_count >= self.config.failure_threshold and 
                    self.stats.last_failure_time and 
                    time.time() - self.stats.last_failure_time < self.config.recovery_timeout):
                    await self._transition_to_open("Failure threshold exceeded")
            
            # Handle open circuit
            if self.stats.state == CircuitState.OPEN:
                if (self.stats.last_failure_time and 
                    time.time() - self.stats.last_failure_time >= self.config.recovery_timeout):
                    await self._transition_to_half_open("Recovery timeout elapsed")
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is open. "
                        f"Last failure: {self.stats.last_failure_time}"
                    )
            
            # Execute function
            try:
                # Apply timeout if it's an async function
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), 
                        timeout=self.config.timeout
                    )
                else:
                    result = func(*args, **kwargs)
                
                await self._on_success()
                return result
                
            except self.config.expected_exceptions as e:
                await self._on_failure(e)
                raise
            except asyncio.TimeoutError as e:
                await self._on_failure(e)
                raise
    
    async def _on_success(self):
        """Handle successful function execution"""
        self.stats.success_count += 1
        self.stats.total_successes += 1
        self.stats.last_success_time = time.time()
        
        # Reset failure count on success
        if self.stats.state == CircuitState.CLOSED:
            self.stats.failure_count = 0
        
        # Check if we should close the circuit from half-open
        elif self.stats.state == CircuitState.HALF_OPEN:
            if self.stats.success_count >= self.config.success_threshold:
                await self._transition_to_closed("Success threshold reached in half-open state")
        
        logger.debug(f"Circuit breaker '{self.name}' recorded success")
    
    async def _on_failure(self, exception: Exception):
        """Handle failed function execution"""
        self.stats.failure_count += 1
        self.stats.total_failures += 1
        self.stats.last_failure_time = time.time()
        
        # Reset success count on failure
        self.stats.success_count = 0
        
        logger.warning(f"Circuit breaker '{self.name}' recorded failure: {exception}")
        
        # Transition to open if threshold exceeded
        if (self.stats.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN) and 
            self.stats.failure_count >= self.config.failure_threshold):
            await self._transition_to_open(f"Failure threshold exceeded: {exception}")
    
    async def _transition_to_open(self, reason: str):
        """Transition circuit to open state"""
        old_state = self.stats.state
        self.stats.state = CircuitState.OPEN
        self.stats.add_state_change(old_state, CircuitState.OPEN, reason)
        logger.warning(f"Circuit breaker '{self.name}' opened: {reason}")
    
    async def _transition_to_half_open(self, reason: str):
        """Transition circuit to half-open state"""
        old_state = self.stats.state
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.success_count = 0  # Reset success counter
        self.stats.add_state_change(old_state, CircuitState.HALF_OPEN, reason)
        logger.info(f"Circuit breaker '{self.name}' half-opened: {reason}")
    
    async def _transition_to_closed(self, reason: str):
        """Transition circuit to closed state"""
        old_state = self.stats.state
        self.stats.state = CircuitState.CLOSED
        self.stats.failure_count = 0  # Reset failure counter
        self.stats.success_count = 0  # Reset success counter
        self.stats.add_state_change(old_state, CircuitState.CLOSED, reason)
        logger.info(f"Circuit breaker '{self.name}' closed: {reason}")
    
    async def force_open(self, reason: str = "Manually forced open"):
        """Manually force circuit to open state"""
        async with self._lock:
            await self._transition_to_open(reason)
    
    async def force_close(self, reason: str = "Manually forced closed"):
        """Manually force circuit to closed state"""
        async with self._lock:
            await self._transition_to_closed(reason)
    
    async def reset(self):
        """Reset circuit breaker statistics"""
        async with self._lock:
            old_state = self.stats.state
            self.stats = CircuitBreakerStats()
            logger.info(f"Circuit breaker '{self.name}' reset from state {old_state.value}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            'name': self.name,
            'state': self.stats.state.value,
            'failure_count': self.stats.failure_count,
            'success_count': self.stats.success_count,
            'total_requests': self.stats.total_requests,
            'total_failures': self.stats.total_failures,
            'total_successes': self.stats.total_successes,
            'last_failure_time': self.stats.last_failure_time,
            'last_success_time': self.stats.last_success_time,
            'failure_rate': (
                self.stats.total_failures / self.stats.total_requests 
                if self.stats.total_requests > 0 else 0
            ),
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'recovery_timeout': self.config.recovery_timeout,
                'success_threshold': self.config.success_threshold,
                'timeout': self.config.timeout
            },
            'recent_state_changes': self.stats.state_changes[-10:]  # Last 10 changes
        }
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self.stats.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)"""
        return self.stats.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self.stats.state == CircuitState.HALF_OPEN


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers for different services.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
    
    async def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get or create a circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Configuration (uses default if not provided)
            
        Returns:
            Circuit breaker instance
        """
        async with self._lock:
            if name not in self._breakers:
                if config is None:
                    config = CircuitBreakerConfig()
                self._breakers[name] = CircuitBreaker(name, config)
            
            return self._breakers[name]
    
    async def remove_breaker(self, name: str) -> bool:
        """
        Remove a circuit breaker.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            True if removed, False if not found
        """
        async with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                logger.info(f"Removed circuit breaker '{name}'")
                return True
            return False
    
    def list_breakers(self) -> List[str]:
        """Get list of circuit breaker names"""
        return list(self._breakers.keys())
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers"""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()
            logger.info("Reset all circuit breakers")


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()