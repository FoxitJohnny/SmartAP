"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by stopping calls to failing services.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Optional, Any, TypeVar, ParamSpec
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests pass through
    OPEN = "open"          # Failing - requests are blocked
    HALF_OPEN = "half_open"  # Testing - limited requests allowed


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening circuit
    success_threshold: int = 3          # Successes in half-open to close
    timeout: float = 30.0               # Seconds before trying half-open
    half_open_max_calls: int = 1        # Max concurrent calls in half-open


class CircuitBreaker:
    """
    Circuit Breaker implementation for protecting external service calls.
    
    Usage:
        # Create a circuit breaker for a service
        foxit_breaker = CircuitBreaker("foxit_ocr")
        
        # Use as context manager
        async with foxit_breaker:
            result = await call_foxit_api()
        
        # Or use decorator
        @foxit_breaker
        async def call_foxit():
            ...
        
        # Or use call() method
        result = await foxit_breaker.call(lambda: call_foxit_api())
    """
    
    # Global registry of circuit breakers
    _registry: dict[str, "CircuitBreaker"] = {}
    _registry_lock = Lock()
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None,
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            config: Configuration options
            on_state_change: Callback when state changes (name, old_state, new_state)
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        # Register in global registry
        with CircuitBreaker._registry_lock:
            CircuitBreaker._registry[name] = self
    
    @classmethod
    def get(cls, name: str) -> Optional["CircuitBreaker"]:
        """Get a circuit breaker by name from the global registry."""
        with cls._registry_lock:
            return cls._registry.get(name)
    
    @classmethod
    def get_all_states(cls) -> dict[str, CircuitState]:
        """Get the state of all registered circuit breakers."""
        with cls._registry_lock:
            return {name: cb._state for name, cb in cls._registry.items()}
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitState.OPEN
    
    def _should_allow_request(self) -> bool:
        """Determine if a request should be allowed."""
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout:
                    return True  # Will transition to half-open
            return False
        
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            
            logger.info(
                f"Circuit breaker '{self.name}' transitioned: {old_state.value} -> {new_state.value}"
            )
            
            if self.on_state_change:
                self.on_state_change(self.name, old_state, new_state)
            
            # Reset counters on state change
            if new_state == CircuitState.CLOSED:
                self._failure_count = 0
                self._success_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
                self._success_count = 0
    
    async def _record_success(self):
        """Record a successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                self._half_open_calls -= 1
                
                if self._success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            else:
                # Reset failure count on success in closed state
                self._failure_count = 0
    
    async def _record_failure(self, error: Exception):
        """Record a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls -= 1
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
    
    async def __aenter__(self):
        """Async context manager entry."""
        async with self._lock:
            if not self._should_allow_request():
                from .errors import CircuitBreakerOpenError
                raise CircuitBreakerOpenError(
                    self.name,
                    retry_after=int(self.config.timeout)
                )
            
            if self._state == CircuitState.OPEN:
                self._transition_to(CircuitState.HALF_OPEN)
            
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is None:
            await self._record_success()
        else:
            await self._record_failure(exc_val)
        
        return False  # Don't suppress exceptions
    
    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        """Decorator for protecting async functions."""
        import functools
        
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with self:
                return await func(*args, **kwargs)
        
        return wrapper
    
    async def call(self, func: Callable[[], T]) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to call (wrap with lambda for parameters)
        
        Returns:
            Result of the function
        
        Raises:
            CircuitBreakerOpenError: When circuit is open
        """
        async with self:
            return await func()
    
    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
            }
        }


# Pre-configured circuit breakers for common services
def get_ocr_circuit_breaker() -> CircuitBreaker:
    """Get or create circuit breaker for OCR service."""
    breaker = CircuitBreaker.get("ocr_service")
    if not breaker:
        breaker = CircuitBreaker(
            "ocr_service",
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=60.0,
            )
        )
    return breaker


def get_erp_circuit_breaker(erp_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for an ERP service."""
    name = f"erp_{erp_name}"
    breaker = CircuitBreaker.get(name)
    if not breaker:
        breaker = CircuitBreaker(
            name,
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout=30.0,
            )
        )
    return breaker


def get_ai_circuit_breaker() -> CircuitBreaker:
    """Get or create circuit breaker for AI service."""
    breaker = CircuitBreaker.get("ai_service")
    if not breaker:
        breaker = CircuitBreaker(
            "ai_service",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=120.0,  # AI services may have longer recovery times
            )
        )
    return breaker
