"""
Retry Utility with Exponential Backoff

Provides retry logic for external service calls with configurable backoff strategies.
"""

import asyncio
import logging
import functools
from typing import Callable, Type, Tuple, Optional, Any, TypeVar, ParamSpec
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )
    # Specific HTTP status codes to retry on
    retryable_status_codes: Tuple[int, ...] = field(
        default_factory=lambda: (429, 500, 502, 503, 504)
    )


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_exception}")


def calculate_backoff(
    attempt: int,
    initial_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool = True,
) -> float:
    """Calculate backoff delay with optional jitter."""
    import random
    
    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
    
    if jitter:
        # Add up to 25% random jitter
        delay = delay * (0.75 + random.random() * 0.5)
    
    return delay


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    Decorator for async functions with retry and exponential backoff.
    
    Usage:
        @retry_with_backoff(RetryConfig(max_retries=5))
        async def call_external_api():
            ...
    
    Args:
        config: RetryConfig with retry parameters
        on_retry: Optional callback called before each retry with (exception, attempt, delay)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry based on HTTP status code
                    if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                        if e.response.status_code not in config.retryable_status_codes:
                            raise  # Don't retry client errors (4xx except 429)
                    
                    if attempt < config.max_retries:
                        delay = calculate_backoff(
                            attempt,
                            config.initial_delay,
                            config.max_delay,
                            config.exponential_base,
                            config.jitter,
                        )
                        
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                            f"after {delay:.2f}s. Error: {e}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1, delay)
                        
                        await asyncio.sleep(delay)
                    else:
                        raise RetryExhaustedError(e, config.max_retries + 1)
            
            # This should never be reached
            raise RetryExhaustedError(last_exception, config.max_retries + 1)
        
        return wrapper
    
    return decorator


async def retry_async(
    func: Callable[[], T],
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Usage:
        result = await retry_async(
            lambda: external_api_call(param1, param2),
            config=RetryConfig(max_retries=5)
        )
    
    Args:
        func: Async function to retry (wrap with lambda if it has parameters)
        config: RetryConfig with retry parameters
        on_retry: Optional callback called before each retry
    
    Returns:
        The result of the function call
    
    Raises:
        RetryExhaustedError: When all retries are exhausted
    """
    if config is None:
        config = RetryConfig()
    
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func()
            
        except config.retryable_exceptions as e:
            last_exception = e
            
            # Check if we should retry based on HTTP status code
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                if e.response.status_code not in config.retryable_status_codes:
                    raise
            
            if attempt < config.max_retries:
                delay = calculate_backoff(
                    attempt,
                    config.initial_delay,
                    config.max_delay,
                    config.exponential_base,
                    config.jitter,
                )
                
                logger.warning(
                    f"Retry {attempt + 1}/{config.max_retries} "
                    f"after {delay:.2f}s. Error: {e}"
                )
                
                if on_retry:
                    on_retry(e, attempt + 1, delay)
                
                await asyncio.sleep(delay)
            else:
                raise RetryExhaustedError(e, config.max_retries + 1)
    
    raise RetryExhaustedError(last_exception, config.max_retries + 1)


# Pre-configured retry configs for common scenarios
RETRY_CONFIG_EXTERNAL_API = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)

RETRY_CONFIG_DATABASE = RetryConfig(
    max_retries=2,
    initial_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=False,
)

RETRY_CONFIG_AI_SERVICE = RetryConfig(
    max_retries=3,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retryable_status_codes=(429, 500, 502, 503, 504, 520, 521, 522, 523, 524),
)
