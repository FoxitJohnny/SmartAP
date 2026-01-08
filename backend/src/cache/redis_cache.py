"""
Redis Cache Implementation

Provides caching functionality with TTL, invalidation, and fallback.
"""

import json
import hashlib
from typing import Any, Optional, Callable, TypeVar
from datetime import timedelta
from functools import wraps

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ..config import get_settings


T = TypeVar("T")


class RedisCache:
    """Redis cache manager with fallback and invalidation."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """Initialize cache with Redis client."""
        self.redis: Optional[Redis] = redis_client
        self.enabled = False
        self.default_ttl = 3600  # 1 hour default
        
    async def connect(self) -> bool:
        """
        Connect to Redis server.
        
        Returns:
            bool: True if connected, False otherwise
        """
        settings = get_settings()
        
        if not settings.redis_enabled:
            return False
        
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            await self.redis.ping()
            self.enabled = True
            self.default_ttl = settings.cache_ttl_seconds
            
            return True
            
        except (RedisError, Exception) as e:
            print(f"Redis connection failed: {e}")
            self.enabled = False
            self.redis = None
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            self.enabled = False
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """
        Generate cache key.
        
        Args:
            prefix: Key prefix (e.g., 'vendor', 'po')
            identifier: Unique identifier
            
        Returns:
            Cache key string
        """
        return f"smartap:{prefix}:{identifier}"
    
    def _generate_hash_key(self, prefix: str, **kwargs) -> str:
        """
        Generate cache key from parameters hash.
        
        Args:
            prefix: Key prefix
            **kwargs: Parameters to hash
            
        Returns:
            Cache key with hashed parameters
        """
        # Sort kwargs for consistent hashing
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"smartap:{prefix}:{params_hash}"
    
    async def get(self, prefix: str, identifier: str) -> Optional[dict]:
        """
        Get value from cache.
        
        Args:
            prefix: Cache key prefix
            identifier: Unique identifier
            
        Returns:
            Cached value or None
        """
        if not self.enabled or not self.redis:
            return None
        
        try:
            key = self._generate_key(prefix, identifier)
            value = await self.redis.get(key)
            
            if value:
                return json.loads(value)
            
            return None
            
        except (RedisError, Exception) as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        prefix: str,
        identifier: str,
        value: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            prefix: Cache key prefix
            identifier: Unique identifier
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (default: self.default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis:
            return False
        
        try:
            key = self._generate_key(prefix, identifier)
            value_str = json.dumps(value)
            ttl_seconds = ttl or self.default_ttl
            
            await self.redis.setex(key, ttl_seconds, value_str)
            return True
            
        except (RedisError, Exception) as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, prefix: str, identifier: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            prefix: Cache key prefix
            identifier: Unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis:
            return False
        
        try:
            key = self._generate_key(prefix, identifier)
            await self.redis.delete(key)
            return True
            
        except (RedisError, Exception) as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., 'smartap:vendor:*')
            
        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis:
            return 0
        
        try:
            # Scan for matching keys
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis.delete(*keys)
                return deleted
            
            return 0
            
        except (RedisError, Exception) as e:
            print(f"Cache delete pattern error: {e}")
            return 0
    
    async def invalidate_vendor(self, vendor_id: str) -> bool:
        """Invalidate vendor cache."""
        return await self.delete("vendor", vendor_id)
    
    async def invalidate_po(self, po_number: str) -> bool:
        """Invalidate PO cache."""
        return await self.delete("po", po_number)
    
    async def invalidate_all_vendors(self) -> int:
        """Invalidate all vendor caches."""
        return await self.delete_pattern("smartap:vendor:*")
    
    async def invalidate_all_pos(self) -> int:
        """Invalidate all PO caches."""
        return await self.delete_pattern("smartap:po:*")
    
    async def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        if not self.enabled or not self.redis:
            return {
                "enabled": False,
                "connected": False,
            }
        
        try:
            info = await self.redis.info("stats")
            
            return {
                "enabled": True,
                "connected": True,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0),
                ),
            }
            
        except (RedisError, Exception):
            return {
                "enabled": True,
                "connected": False,
            }
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round(hits / total, 3)


# Global cache instance
_cache: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """
    Get or create global cache instance.
    
    Returns:
        RedisCache instance
    """
    global _cache
    
    if _cache is None:
        _cache = RedisCache()
        await _cache.connect()
    
    return _cache


def cached(
    prefix: str,
    key_param: str = "id",
    ttl: Optional[int] = None,
):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        key_param: Parameter name to use as cache key
        ttl: Time-to-live in seconds
        
    Example:
        @cached(prefix="vendor", key_param="vendor_id", ttl=3600)
        async def get_vendor(vendor_id: str) -> dict:
            # Fetch from database
            return vendor_data
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = await get_cache()
            
            # Extract key parameter
            identifier = kwargs.get(key_param)
            if not identifier and args:
                # Try to get from positional args
                # Assume first arg is the identifier
                identifier = str(args[0])
            
            if not identifier:
                # No identifier, skip caching
                return await func(*args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache.get(prefix, str(identifier))
            if cached_value is not None:
                return cached_value
            
            # Cache miss, call function
            result = await func(*args, **kwargs)
            
            # Cache result if it's a dict
            if isinstance(result, dict):
                await cache.set(prefix, str(identifier), result, ttl)
            
            return result
        
        return wrapper
    
    return decorator
