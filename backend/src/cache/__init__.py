"""
SmartAP Cache Module

Provides caching functionality with Redis primary and in-memory fallback.
"""

from .redis_cache import RedisCache, get_cache
from .cache_service import (
    CacheService,
    CacheInvalidator,
    CacheTTL,
    CachePrefix,
    get_cache_service,
    reset_cache_service,
    cached,
    cached_with_key,
    default_invalidator,
)

__all__ = [
    # Redis cache
    "RedisCache",
    "get_cache",
    # Cache service
    "CacheService",
    "CacheInvalidator",
    "CacheTTL",
    "CachePrefix",
    "get_cache_service",
    "reset_cache_service",
    "cached",
    "cached_with_key",
    "default_invalidator",
]
