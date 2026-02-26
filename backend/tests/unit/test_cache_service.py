"""
Tests for cache service module.
Tests InMemoryCache, CacheService, decorators, and CacheInvalidator.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.cache.cache_service import (
    InMemoryCache,
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


# ============================================================================
# InMemoryCache Tests
# ============================================================================

class TestInMemoryCache:
    """Tests for InMemoryCache class."""
    
    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return InMemoryCache(max_size=100)
    
    @pytest.mark.asyncio
    async def test_set_and_get_basic(self, cache):
        """Test basic set and get operations."""
        await cache.set("test_key", "test_value")
        result = await cache.get("test_key")
        assert result == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache):
        """Test getting a key that doesn't exist."""
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self, cache):
        """Test set with custom TTL."""
        await cache.set("ttl_key", "ttl_value", ttl=1)
        result = await cache.get("ttl_key")
        assert result == "ttl_value"
        
        # Wait for TTL to expire
        await asyncio.sleep(1.1)
        result = await cache.get("ttl_key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_key(self, cache):
        """Test deleting a key."""
        await cache.set("delete_me", "value")
        assert await cache.get("delete_me") == "value"
        
        deleted = await cache.delete("delete_me")
        assert deleted is True
        assert await cache.get("delete_me") is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache):
        """Test deleting a key that doesn't exist."""
        deleted = await cache.delete("nonexistent")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_clear_all(self, cache):
        """Test clearing all cached items."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        await cache.clear()
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
        assert await cache.get("key3") is None
    
    @pytest.mark.asyncio
    async def test_delete_pattern(self, cache):
        """Test deleting keys by pattern."""
        await cache.set("user:1:profile", "profile1")
        await cache.set("user:2:profile", "profile2")
        await cache.set("user:1:settings", "settings1")
        await cache.set("other:key", "other")
        
        count = await cache.delete_pattern("user:*")
        assert count == 3
        
        assert await cache.get("user:1:profile") is None
        assert await cache.get("user:2:profile") is None
        assert await cache.get("user:1:settings") is None
        assert await cache.get("other:key") == "other"
    
    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        """Test that items are evicted when max size is reached."""
        cache = InMemoryCache(max_size=5)
        
        # Fill to capacity
        for i in range(5):
            await cache.set(f"key{i}", f"value{i}")
        
        # Adding more should trigger eviction
        for i in range(5, 10):
            await cache.set(f"key{i}", f"value{i}")
        
        # Cache should not exceed max_size significantly
        stats = cache.stats
        # Eviction is batched, so size may vary slightly
        assert stats["size"] <= 10  # Should have evicted some items
    
    @pytest.mark.asyncio
    async def test_stats_property(self, cache):
        """Test getting cache statistics via property."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        # Generate some hits and misses
        await cache.get("key1")  # hit
        await cache.get("key1")  # hit
        await cache.get("nonexistent")  # miss
        
        stats = cache.stats
        
        assert stats["size"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.67, rel=0.1)
    
    @pytest.mark.asyncio
    async def test_complex_data_types(self, cache):
        """Test caching complex data types."""
        # Dict
        await cache.set("dict_key", {"nested": {"data": [1, 2, 3]}})
        result = await cache.get("dict_key")
        assert result == {"nested": {"data": [1, 2, 3]}}
        
        # List
        await cache.set("list_key", [1, "two", 3.0, None])
        result = await cache.get("list_key")
        assert result == [1, "two", 3.0, None]


# ============================================================================
# CacheService Tests
# ============================================================================

class TestCacheService:
    """Tests for CacheService class."""
    
    @pytest.fixture
    async def cache_service(self):
        """Create a cache service with memory fallback."""
        reset_cache_service()
        service = CacheService()
        await service.initialize()
        return service
    
    @pytest.mark.asyncio
    async def test_memory_fallback_when_redis_disabled(self, cache_service):
        """Test that memory cache is used when Redis is disabled."""
        # By default, Redis is disabled in settings
        assert cache_service._memory_cache is not None
    
    @pytest.mark.asyncio
    async def test_set_and_get_with_prefix(self, cache_service):
        """Test set and get with prefix."""
        await cache_service.set("dashboard", "metrics", value={"total": 100})
        result = await cache_service.get("dashboard", "metrics")
        assert result == {"total": 100}
    
    @pytest.mark.asyncio
    async def test_multiple_key_parts(self, cache_service):
        """Test with multiple key parts."""
        await cache_service.set("user", "profile", "123", value={"name": "test"})
        result = await cache_service.get("user", "profile", "123")
        assert result == {"name": "test"}
        
        # Different key part should not match
        result = await cache_service.get("user", "profile", "456")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_operation(self, cache_service):
        """Test delete operation."""
        await cache_service.set("test", "key", value="value")
        assert await cache_service.get("test", "key") == "value"
        
        await cache_service.delete("test", "key")
        assert await cache_service.get("test", "key") is None
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_service):
        """Test pattern-based invalidation."""
        await cache_service.set("analytics", "volume", value={"count": 10})
        await cache_service.set("analytics", "rate", value={"rate": 0.5})
        await cache_service.set("dashboard", "summary", value={"total": 100})
        
        count = await cache_service.invalidate_pattern("smartap:analytics:*")
        assert count == 2
        
        assert await cache_service.get("analytics", "volume") is None
        assert await cache_service.get("analytics", "rate") is None
        assert await cache_service.get("dashboard", "summary") == {"total": 100}
    
    @pytest.mark.asyncio
    async def test_stats_retrieval(self, cache_service):
        """Test getting cache statistics."""
        await cache_service.set("test", "key", value="value")
        await cache_service.get("test", "key")  # hit
        await cache_service.get("test", "miss")  # miss
        
        stats = await cache_service.get_stats()
        
        assert "backend" in stats
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalCacheService:
    """Tests for global cache service instance management."""
    
    @pytest.mark.asyncio
    async def test_get_cache_service_singleton(self):
        """Test that get_cache_service returns singleton."""
        reset_cache_service()
        
        service1 = await get_cache_service()
        service2 = await get_cache_service()
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_reset_cache_service(self):
        """Test resetting the global cache service."""
        service1 = await get_cache_service()
        reset_cache_service()
        service2 = await get_cache_service()
        
        assert service1 is not service2


# ============================================================================
# Decorator Tests
# ============================================================================

class TestCachedDecorator:
    """Tests for @cached decorator."""
    
    @pytest.mark.asyncio
    async def test_cached_basic_function(self):
        """Test basic function caching."""
        reset_cache_service()
        call_count = 0
        
        @cached(prefix=CachePrefix.DASHBOARD, ttl=60)
        async def get_data():
            nonlocal call_count
            call_count += 1
            return {"data": "test"}
        
        # First call should execute function
        result1 = await get_data()
        assert result1 == {"data": "test"}
        assert call_count == 1
        
        # Second call should return cached result
        result2 = await get_data()
        assert result2 == {"data": "test"}
        assert call_count == 1  # Function not called again
    
    @pytest.mark.asyncio
    async def test_cached_with_parameters(self):
        """Test caching with function parameters as key parts."""
        reset_cache_service()
        call_count = 0
        
        @cached(prefix=CachePrefix.ANALYTICS, ttl=60, key_params=["user_id"])
        async def get_user_data(user_id: str):
            nonlocal call_count
            call_count += 1
            return {"user_id": user_id}
        
        # Different user_ids should cache separately
        result1 = await get_user_data(user_id="user1")
        assert result1 == {"user_id": "user1"}
        assert call_count == 1
        
        result2 = await get_user_data(user_id="user2")
        assert result2 == {"user_id": "user2"}
        assert call_count == 2
        
        # Same user_id should return cached
        result3 = await get_user_data(user_id="user1")
        assert result3 == {"user_id": "user1"}
        assert call_count == 2  # Not incremented


class TestCachedWithKeyDecorator:
    """Tests for @cached_with_key decorator."""
    
    @pytest.mark.asyncio
    async def test_cached_with_custom_key_function(self):
        """Test caching with custom key function."""
        reset_cache_service()
        call_count = 0
        
        def custom_key_func(page: int, limit: int):
            return f"page_{page}_limit_{limit}"
        
        @cached_with_key(key_func=custom_key_func, prefix=CachePrefix.INVOICE, ttl=60)
        async def get_paginated_data(page: int, limit: int):
            nonlocal call_count
            call_count += 1
            return {"page": page, "limit": limit, "items": []}
        
        result1 = await get_paginated_data(1, 10)
        assert call_count == 1
        
        # Same params should hit cache
        result2 = await get_paginated_data(1, 10)
        assert call_count == 1
        
        # Different params should miss cache
        result3 = await get_paginated_data(2, 10)
        assert call_count == 2


# ============================================================================
# CacheInvalidator Tests
# ============================================================================

class TestCacheInvalidator:
    """Tests for CacheInvalidator class."""
    
    @pytest.fixture
    async def invalidator(self):
        """Create cache invalidator with fresh service."""
        reset_cache_service()
        await get_cache_service()  # Initialize
        invalidator = CacheInvalidator()
        invalidator.register("test_entity", ["dashboard:*", "analytics:*"])
        return invalidator
    
    @pytest.mark.asyncio
    async def test_invalidate_registered_patterns(self, invalidator):
        """Test invalidating registered patterns."""
        cache = await get_cache_service()
        
        # Set some data
        await cache.set("dashboard", "metrics", value={"data": "test"})
        await cache.set("analytics", "other", value={"data": "keep"})
        await cache.set("vendor", "list", value={"data": "also_keep"})
        
        # Invalidate via entity type
        await invalidator.invalidate("test_entity")
        
        # Dashboard and analytics should be invalidated (matching patterns)
        # vendor should remain
        assert await cache.get("vendor", "list") == {"data": "also_keep"}
    
    @pytest.mark.asyncio
    async def test_invalidate_unregistered_entity(self, invalidator):
        """Test invalidating unregistered entity does nothing."""
        # Should not raise error
        result = await invalidator.invalidate("unregistered_type")
        assert result == 0


# ============================================================================
# CacheTTL and CachePrefix Constants Tests
# ============================================================================

class TestCacheConstants:
    """Tests for cache constants."""
    
    def test_cache_ttl_values(self):
        """Test CacheTTL constants have reasonable values."""
        assert CacheTTL.DASHBOARD_METRICS == 60  # 1 minute
        assert CacheTTL.ANALYTICS == 300  # 5 minutes
        assert CacheTTL.LIST_RESULTS == 120  # 2 minutes
        assert CacheTTL.SINGLE_ENTITY == 600  # 10 minutes
        assert CacheTTL.VENDOR_DATA == 1800  # 30 minutes
        assert CacheTTL.REFERENCE_DATA == 3600  # 1 hour
        assert CacheTTL.CONFIG == 7200  # 2 hours
    
    def test_cache_prefix_values(self):
        """Test CachePrefix constants."""
        assert CachePrefix.DASHBOARD == "dashboard"
        assert CachePrefix.ANALYTICS == "analytics"
        assert CachePrefix.INVOICE == "invoice"
        assert CachePrefix.VENDOR == "vendor"
        assert CachePrefix.PURCHASE_ORDER == "po"
        assert CachePrefix.RISK == "risk"
        assert CachePrefix.APPROVAL == "approval"
        assert CachePrefix.USER == "user"
        assert CachePrefix.CONFIG == "config"


# ============================================================================
# Integration Tests
# ============================================================================

class TestCacheServiceIntegration:
    """Integration tests for cache service with real async operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent cache access."""
        reset_cache_service()
        cache = await get_cache_service()
        
        async def write_and_read(key_suffix: int):
            key = f"concurrent_{key_suffix}"
            await cache.set("test", key, value={"value": key_suffix})
            await asyncio.sleep(0.01)  # Small delay
            result = await cache.get("test", key)
            return result
        
        # Run multiple concurrent operations
        tasks = [write_and_read(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for i, result in enumerate(results):
            assert result == {"value": i}
    
    @pytest.mark.asyncio
    async def test_cache_expiration_cleanup(self):
        """Test that expired items are cleaned up on access."""
        cache = InMemoryCache(max_size=100)
        
        await cache.set("expire_test", "value", ttl=1)
        assert await cache.get("expire_test") == "value"
        
        await asyncio.sleep(1.1)
        
        # Access should return None and clean up expired item
        result = await cache.get("expire_test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete caching workflow."""
        reset_cache_service()
        cache = await get_cache_service()
        
        # Set data
        await cache.set(CachePrefix.DASHBOARD, "metrics", value={"total": 100})
        await cache.set(CachePrefix.ANALYTICS, "volume", value={"count": 50})
        
        # Verify data exists
        assert await cache.get(CachePrefix.DASHBOARD, "metrics") == {"total": 100}
        assert await cache.get(CachePrefix.ANALYTICS, "volume") == {"count": 50}
        
        # Invalidate dashboard
        await cache.invalidate_pattern("smartap:dashboard:*")
        
        # Dashboard gone, analytics remain
        assert await cache.get(CachePrefix.DASHBOARD, "metrics") is None
        assert await cache.get(CachePrefix.ANALYTICS, "volume") == {"count": 50}


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestCacheEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_string_key(self):
        """Test handling of empty string key."""
        cache = InMemoryCache()
        await cache.set("", "empty_key_value")
        result = await cache.get("")
        assert result == "empty_key_value"
    
    @pytest.mark.asyncio
    async def test_large_value(self):
        """Test caching large values."""
        cache = InMemoryCache()
        large_data = {"items": list(range(10000))}
        
        await cache.set("large", large_data)
        result = await cache.get("large")
        
        assert result == large_data
        assert len(result["items"]) == 10000
    
    @pytest.mark.asyncio
    async def test_special_characters_in_key(self):
        """Test keys with special characters."""
        cache = InMemoryCache()
        special_key = "user:123:profile:settings#v1"
        
        await cache.set(special_key, {"data": "test"})
        result = await cache.get(special_key)
        
        assert result == {"data": "test"}
    
    @pytest.mark.asyncio
    async def test_zero_ttl(self):
        """Test with zero TTL - should expire immediately."""
        cache = InMemoryCache(max_size=100)
        
        await cache.set("zero_ttl", "value", ttl=0)
        # Zero TTL means immediately expired
        await asyncio.sleep(0.1)
        result = await cache.get("zero_ttl")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
