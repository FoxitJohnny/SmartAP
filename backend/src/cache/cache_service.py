"""
SmartAP Cache Service

Enhanced caching service with decorator support, composite keys,
and integration with both Redis (when available) and in-memory fallback.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union
from dataclasses import dataclass, field

from ..config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


# =============================================================================
# In-Memory Cache for Fallback
# =============================================================================


@dataclass
class CacheEntry:
    """Cache entry with value and expiration."""
    
    value: Any
    expires_at: datetime
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.utcnow() >= self.expires_at


class InMemoryCache:
    """Thread-safe in-memory cache with TTL support."""
    
    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                await self._evict_expired_unsafe()
                
                if len(self._cache) >= self._max_size:
                    await self._evict_oldest_unsafe(len(self._cache) - self._max_size + 100)
            
            self._cache[key] = CacheEntry(
                value=value,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl),
            )
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern prefix."""
        async with self._lock:
            # Simple prefix matching (pattern should end with *)
            prefix = pattern.rstrip("*")
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def _evict_expired_unsafe(self) -> int:
        """Evict expired entries. Must be called with lock held."""
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired:
            del self._cache[key]
        return len(expired)
    
    async def _evict_oldest_unsafe(self, count: int) -> None:
        """Evict oldest entries. Must be called with lock held."""
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at,
        )
        for key, _ in sorted_entries[:count]:
            del self._cache[key]
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
        }


# =============================================================================
# Unified Cache Service
# =============================================================================


class CacheService:
    """
    Unified cache service with Redis primary and in-memory fallback.
    
    Provides a consistent interface for caching with automatic failover
    from Redis to in-memory when Redis is unavailable.
    
    Features:
    - Automatic Redis/memory fallback
    - Composite key generation
    - Pattern-based invalidation
    - TTL support
    - Statistics tracking
    
    Example:
        cache = await get_cache_service()
        
        # Simple get/set
        await cache.set("dashboard", "metrics", data, ttl=60)
        data = await cache.get("dashboard", "metrics")
        
        # With composite key
        await cache.set("invoice", invoice_id, invoice_data, ttl=300)
        
        # Invalidate patterns
        await cache.invalidate_pattern("dashboard:*")
    """
    
    def __init__(self):
        self._redis_cache: Optional[Any] = None
        self._memory_cache = InMemoryCache()
        self._use_redis = False
        self._initialized = False
        self._default_ttl = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """
        Initialize cache service, connecting to Redis if enabled.
        
        Returns:
            True if Redis connected, False if using memory fallback.
        """
        if self._initialized:
            return self._use_redis
        
        settings = get_settings()
        self._default_ttl = settings.cache_ttl_seconds
        
        if settings.redis_enabled:
            try:
                from .redis_cache import RedisCache
                
                self._redis_cache = RedisCache()
                connected = await self._redis_cache.connect()
                
                if connected:
                    self._use_redis = True
                    logger.info("Cache service initialized with Redis")
                else:
                    logger.warning("Redis connection failed, using in-memory cache")
            except Exception as e:
                logger.warning(f"Redis initialization failed: {e}, using in-memory cache")
        else:
            logger.info("Cache service initialized with in-memory cache (Redis disabled)")
        
        self._initialized = True
        return self._use_redis
    
    async def shutdown(self) -> None:
        """Shutdown cache service and close connections."""
        if self._redis_cache:
            await self._redis_cache.disconnect()
        await self._memory_cache.clear()
        self._initialized = False
    
    def _generate_key(self, prefix: str, *parts: Any) -> str:
        """
        Generate cache key from prefix and parts.
        
        Args:
            prefix: Key namespace/prefix
            *parts: Additional key components
            
        Returns:
            Formatted cache key
        """
        key_parts = [f"smartap:{prefix}"]
        for part in parts:
            if isinstance(part, dict):
                # Hash complex objects
                sorted_items = sorted(part.items())
                part_str = hashlib.md5(json.dumps(sorted_items).encode()).hexdigest()[:12]
            elif isinstance(part, (list, tuple)):
                part_str = hashlib.md5(json.dumps(part).encode()).hexdigest()[:12]
            else:
                part_str = str(part)
            key_parts.append(part_str)
        
        return ":".join(key_parts)
    
    async def get(self, prefix: str, *key_parts: Any) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            prefix: Cache key prefix/namespace
            *key_parts: Additional key components
            
        Returns:
            Cached value or None
        """
        await self.initialize()
        key = self._generate_key(prefix, *key_parts)
        
        if self._use_redis and self._redis_cache:
            try:
                # Use existing Redis cache interface
                result = await self._redis_cache.get(prefix, ":".join(str(p) for p in key_parts) if key_parts else "default")
                return result
            except Exception as e:
                logger.warning(f"Redis get failed: {e}, falling back to memory")
                return await self._memory_cache.get(key)
        
        return await self._memory_cache.get(key)
    
    async def set(
        self,
        prefix: str,
        *key_parts: Any,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            prefix: Cache key prefix/namespace
            *key_parts: Additional key components
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        await self.initialize()
        key = self._generate_key(prefix, *key_parts)
        ttl_seconds = ttl or self._default_ttl
        
        if self._use_redis and self._redis_cache:
            try:
                identifier = ":".join(str(p) for p in key_parts) if key_parts else "default"
                await self._redis_cache.set(prefix, identifier, value, ttl_seconds)
                return True
            except Exception as e:
                logger.warning(f"Redis set failed: {e}, falling back to memory")
                return await self._memory_cache.set(key, value, ttl_seconds)
        
        return await self._memory_cache.set(key, value, ttl_seconds)
    
    async def delete(self, prefix: str, *key_parts: Any) -> bool:
        """
        Delete value from cache.
        
        Args:
            prefix: Cache key prefix/namespace
            *key_parts: Additional key components
            
        Returns:
            True if deleted
        """
        await self.initialize()
        key = self._generate_key(prefix, *key_parts)
        
        if self._use_redis and self._redis_cache:
            try:
                identifier = ":".join(str(p) for p in key_parts) if key_parts else "default"
                await self._redis_cache.delete(prefix, identifier)
                return True
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        return await self._memory_cache.delete(key)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache entries matching pattern.
        
        Args:
            pattern: Key pattern (supports prefix matching with *)
            
        Returns:
            Number of keys invalidated
        """
        await self.initialize()
        
        # Convert to full pattern
        full_pattern = f"smartap:{pattern}" if not pattern.startswith("smartap:") else pattern
        
        if self._use_redis and self._redis_cache:
            try:
                return await self._redis_cache.delete_pattern(full_pattern)
            except Exception as e:
                logger.warning(f"Redis pattern delete failed: {e}")
        
        return await self._memory_cache.delete_pattern(full_pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        await self.initialize()
        
        if self._use_redis and self._redis_cache:
            try:
                redis_stats = await self._redis_cache.get_stats()
                return {
                    "backend": "redis",
                    **redis_stats,
                }
            except Exception:
                pass
        
        return {
            "backend": "memory",
            **self._memory_cache.stats,
        }
    
    @property
    def is_redis_enabled(self) -> bool:
        """Check if Redis is being used."""
        return self._use_redis


# =============================================================================
# Global Cache Instance
# =============================================================================

_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """
    Get or create global cache service instance.
    
    Returns:
        CacheService instance
    """
    global _cache_service
    
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
    
    return _cache_service


def reset_cache_service() -> None:
    """Reset global cache service (for testing)."""
    global _cache_service
    _cache_service = None


# =============================================================================
# Caching Decorators
# =============================================================================


def cached(
    prefix: str,
    ttl: int = 300,
    key_params: Optional[List[str]] = None,
    skip_none: bool = True,
):
    """
    Decorator for caching async function results.
    
    Args:
        prefix: Cache key prefix/namespace
        ttl: Time-to-live in seconds
        key_params: List of parameter names to include in cache key
                   (if None, uses all non-session params)
        skip_none: Skip caching if result is None
        
    Example:
        @cached(prefix="dashboard", ttl=60)
        async def get_metrics(session: AsyncSession):
            return await expensive_query(session)
            
        @cached(prefix="invoice", ttl=300, key_params=["invoice_id"])
        async def get_invoice(session: AsyncSession, invoice_id: str):
            return await fetch_invoice(session, invoice_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = await get_cache_service()
            
            # Build cache key from parameters
            key_components = []
            
            if key_params:
                # Use specified parameters
                for param in key_params:
                    if param in kwargs:
                        key_components.append(kwargs[param])
            else:
                # Use all kwargs except session-like objects
                for key, value in sorted(kwargs.items()):
                    if key not in ("session", "db", "request", "response"):
                        if isinstance(value, (str, int, float, bool)):
                            key_components.append(f"{key}:{value}")
            
            # Generate cache key
            if key_components:
                cache_key = hashlib.md5(
                    json.dumps(key_components, default=str).encode()
                ).hexdigest()[:16]
            else:
                cache_key = "default"
            
            # Try cache first
            cached_value = await cache.get(prefix, func.__name__, cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {prefix}:{func.__name__}:{cache_key}")
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result is not None or not skip_none:
                await cache.set(
                    prefix, func.__name__, cache_key,
                    value=result,
                    ttl=ttl,
                )
                logger.debug(f"Cache set: {prefix}:{func.__name__}:{cache_key}")
            
            return result
        
        # Add cache invalidation helper
        async def invalidate(*key_components: Any) -> int:
            """Invalidate cache entries for this function."""
            cache = await get_cache_service()
            pattern = f"{prefix}:{func.__name__}:*"
            return await cache.invalidate_pattern(pattern)
        
        wrapper.invalidate = invalidate
        wrapper.cache_prefix = prefix
        
        return wrapper
    
    return decorator


def cached_with_key(
    key_func: Callable[..., str],
    prefix: str = "custom",
    ttl: int = 300,
):
    """
    Decorator with custom key function.
    
    Args:
        key_func: Function that takes same args as decorated function and returns cache key
        prefix: Cache key prefix
        ttl: Time-to-live in seconds
        
    Example:
        def make_key(session, vendor_id, status=None):
            return f"{vendor_id}:{status or 'all'}"
            
        @cached_with_key(make_key, prefix="vendor_invoices", ttl=120)
        async def get_vendor_invoices(session, vendor_id, status=None):
            return await query_invoices(session, vendor_id, status)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = await get_cache_service()
            
            # Generate custom key
            custom_key = key_func(*args, **kwargs)
            
            # Try cache
            cached_value = await cache.get(prefix, func.__name__, custom_key)
            if cached_value is not None:
                return cached_value
            
            # Execute and cache
            result = await func(*args, **kwargs)
            
            if result is not None:
                await cache.set(
                    prefix, func.__name__, custom_key,
                    value=result,
                    ttl=ttl,
                )
            
            return result
        
        return wrapper
    
    return decorator


class CacheInvalidator:
    """
    Helper for invalidating related cache entries.
    
    Example:
        invalidator = CacheInvalidator()
        
        # Register cache prefixes for entity types
        invalidator.register("invoice", ["dashboard:*", "analytics:*"])
        invalidator.register("vendor", ["dashboard:*", "vendor:*"])
        
        # When an invoice is updated
        await invalidator.invalidate("invoice", invoice_id)
    """
    
    def __init__(self):
        self._patterns: Dict[str, List[str]] = {}
    
    def register(self, entity_type: str, patterns: List[str]) -> None:
        """
        Register cache patterns to invalidate for an entity type.
        
        Args:
            entity_type: Type of entity (invoice, vendor, etc.)
            patterns: List of cache patterns to invalidate
        """
        self._patterns[entity_type] = patterns
    
    async def invalidate(
        self,
        entity_type: str,
        entity_id: Optional[str] = None,
    ) -> int:
        """
        Invalidate all registered patterns for an entity type.
        
        Args:
            entity_type: Type of entity
            entity_id: Optional specific entity ID
            
        Returns:
            Total number of cache entries invalidated
        """
        cache = await get_cache_service()
        total = 0
        
        patterns = self._patterns.get(entity_type, [])
        
        for pattern in patterns:
            if entity_id and "{id}" in pattern:
                pattern = pattern.replace("{id}", entity_id)
            count = await cache.invalidate_pattern(pattern)
            total += count
        
        return total

    async def invalidate_dashboard(self) -> int:
        """Invalidate all dashboard-related caches."""
        cache = await get_cache_service()
        return await cache.invalidate_pattern("dashboard:*")

    async def invalidate_analytics(self) -> int:
        """Invalidate all analytics-related caches."""
        cache = await get_cache_service()
        return await cache.invalidate_pattern("analytics:*")


# Default invalidator with common patterns
default_invalidator = CacheInvalidator()
default_invalidator.register("invoice", [
    "dashboard:get_metrics:*",
    "dashboard:get_approval_queue:*",
    "analytics:*",
    "invoice:{id}",
])
default_invalidator.register("vendor", [
    "dashboard:*",
    "vendor:{id}",
    "vendor:list:*",
])
default_invalidator.register("purchase_order", [
    "dashboard:*",
    "po:{id}",
    "po:list:*",
])


# =============================================================================
# Cache Configuration Constants
# =============================================================================


class CacheTTL:
    """Standard TTL values for different cache types."""
    
    # Dashboard metrics - short TTL for near real-time
    DASHBOARD_METRICS = 60  # 1 minute
    
    # Analytics - medium TTL
    ANALYTICS = 300  # 5 minutes
    
    # List results - short TTL
    LIST_RESULTS = 120  # 2 minutes
    
    # Single entity - longer TTL
    SINGLE_ENTITY = 600  # 10 minutes
    
    # Vendor data - longer TTL (less frequent changes)
    VENDOR_DATA = 1800  # 30 minutes
    
    # Reference data - very long TTL
    REFERENCE_DATA = 3600  # 1 hour
    
    # Configuration - very long TTL
    CONFIG = 7200  # 2 hours


class CachePrefix:
    """Standard cache prefixes for different data types."""
    
    DASHBOARD = "dashboard"
    ANALYTICS = "analytics"
    INVOICE = "invoice"
    VENDOR = "vendor"
    PURCHASE_ORDER = "po"
    RISK = "risk"
    APPROVAL = "approval"
    USER = "user"
    CONFIG = "config"
