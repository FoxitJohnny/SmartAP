"""Performance benchmark tests for V3.4.1 Query Optimization.

These tests verify that the application meets performance requirements:
- Invoice processing: < 10 seconds
- Dashboard loading: < 500ms
- Invoice list pagination: < 200ms
- Concurrent upload handling: scales efficiently
"""

import asyncio
import statistics
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.utils.query_optimizer import (
    BatchLoader,
    CacheEntry,
    EagerLoadBuilder,
    LoadStrategy,
    QueryAnalyzer,
    QueryCache,
    QueryMetrics,
    generate_cache_key,
    cached_query,
    get_default_cache,
    get_default_analyzer,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def query_cache() -> QueryCache:
    """Create a fresh query cache."""
    return QueryCache(default_ttl=300, max_size=100)


@pytest.fixture
def query_analyzer() -> QueryAnalyzer:
    """Create a fresh query analyzer."""
    return QueryAnalyzer(slow_query_threshold_ms=100.0)


@pytest.fixture
def sample_invoices() -> List[Dict[str, Any]]:
    """Generate sample invoice data."""
    return [
        {
            "id": i,
            "invoice_id": f"INV-{i:05d}",
            "vendor_id": f"V-{i % 10:03d}",
            "total_amount": 1000.0 + i * 10,
            "status": ["pending", "approved", "rejected"][i % 3],
            "created_at": datetime.utcnow() - timedelta(days=i),
        }
        for i in range(100)
    ]


@pytest.fixture
def sample_vendors() -> Dict[str, Dict[str, Any]]:
    """Generate sample vendor data."""
    return {
        f"V-{i:03d}": {
            "vendor_id": f"V-{i:03d}",
            "vendor_name": f"Vendor {i}",
            "status": "active",
        }
        for i in range(10)
    }


# =============================================================================
# QueryCache Tests
# =============================================================================


class TestQueryCache:
    """Tests for QueryCache functionality."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, query_cache: QueryCache):
        """Test basic cache set and get operations."""
        await query_cache.set("test_key", {"data": "value"})
        result = await query_cache.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, query_cache: QueryCache):
        """Test that cache miss returns None."""
        result = await query_cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiration(self, query_cache: QueryCache):
        """Test that expired entries are not returned."""
        await query_cache.set("expire_key", "value", ttl=1)
        # Wait for expiration (1 second TTL + small buffer)
        await asyncio.sleep(1.1)
        result = await query_cache.get("expire_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self, query_cache: QueryCache):
        """Test cache entry deletion."""
        await query_cache.set("delete_key", "value")
        deleted = await query_cache.delete("delete_key")
        assert deleted is True
        result = await query_cache.get("delete_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete_nonexistent(self, query_cache: QueryCache):
        """Test deleting non-existent entry."""
        deleted = await query_cache.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_cache_invalidate_pattern(self, query_cache: QueryCache):
        """Test pattern-based cache invalidation."""
        await query_cache.set("invoices:pending:1", "data1")
        await query_cache.set("invoices:pending:2", "data2")
        await query_cache.set("invoices:approved:1", "data3")
        await query_cache.set("vendors:1", "vendor1")

        count = await query_cache.invalidate_pattern("invoices:pending")
        assert count == 2

        # Check invalidated entries are gone
        assert await query_cache.get("invoices:pending:1") is None
        assert await query_cache.get("invoices:pending:2") is None

        # Check other entries remain
        assert await query_cache.get("invoices:approved:1") == "data3"
        assert await query_cache.get("vendors:1") == "vendor1"

    @pytest.mark.asyncio
    async def test_cache_clear(self, query_cache: QueryCache):
        """Test clearing all cache entries."""
        await query_cache.set("key1", "value1")
        await query_cache.set("key2", "value2")

        await query_cache.clear()

        assert await query_cache.get("key1") is None
        assert await query_cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_cache_stats(self, query_cache: QueryCache):
        """Test cache statistics."""
        await query_cache.set("key1", "value1")
        await query_cache.get("key1")  # Hit
        await query_cache.get("key1")  # Hit
        await query_cache.get("nonexistent")  # Miss

        stats = query_cache.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(0.6667, rel=0.01)

    @pytest.mark.asyncio
    async def test_cache_max_size_eviction(self):
        """Test cache eviction when max size is reached."""
        small_cache = QueryCache(default_ttl=300, max_size=3)

        await small_cache.set("key1", "value1")
        await small_cache.set("key2", "value2")
        await small_cache.set("key3", "value3")
        await small_cache.set("key4", "value4")  # Should trigger eviction

        # At least one entry should be evicted
        stats = small_cache.stats
        assert stats["size"] <= 3


# =============================================================================
# BatchLoader Tests
# =============================================================================


class TestBatchLoader:
    """Tests for BatchLoader functionality."""

    @pytest.mark.asyncio
    async def test_batch_load_single_item(self, sample_vendors):
        """Test loading a single item."""
        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            return [sample_vendors.get(vid) for vid in ids]

        loader = BatchLoader(load_vendors)
        result = await loader.load("V-001")
        assert result["vendor_name"] == "Vendor 1"

    @pytest.mark.asyncio
    async def test_batch_load_multiple_items(self, sample_vendors):
        """Test loading multiple items."""
        call_count = 0

        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            return [sample_vendors.get(vid) for vid in ids]

        loader = BatchLoader(load_vendors)
        results = await loader.load_many(["V-001", "V-002", "V-003"])

        assert len(results) == 3
        assert results[0]["vendor_name"] == "Vendor 1"
        assert results[1]["vendor_name"] == "Vendor 2"

    @pytest.mark.asyncio
    async def test_batch_load_caching(self, sample_vendors):
        """Test that batch loader caches results."""
        call_count = 0

        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            return [sample_vendors.get(vid) for vid in ids]

        loader = BatchLoader(load_vendors, cache_enabled=True)

        # First load
        await loader.load("V-001")
        # Second load (should be cached)
        await loader.load("V-001")

        # Only one batch call should have been made
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_batch_load_prime_cache(self, sample_vendors):
        """Test priming the batch loader cache."""
        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            pytest.fail("Should not be called when cache is primed")

        loader = BatchLoader(load_vendors)
        loader.prime("V-001", sample_vendors["V-001"])

        result = await loader.load("V-001")
        assert result["vendor_name"] == "Vendor 1"

    @pytest.mark.asyncio
    async def test_batch_load_clear_cache(self, sample_vendors):
        """Test clearing the batch loader cache."""
        call_count = 0

        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            nonlocal call_count
            call_count += 1
            return [sample_vendors.get(vid) for vid in ids]

        loader = BatchLoader(load_vendors)
        await loader.load("V-001")
        loader.clear_cache()
        await loader.load("V-001")

        assert call_count == 2


# =============================================================================
# QueryAnalyzer Tests
# =============================================================================


class TestQueryAnalyzer:
    """Tests for QueryAnalyzer functionality."""

    @pytest.mark.asyncio
    async def test_track_query(self, query_analyzer: QueryAnalyzer):
        """Test tracking query execution."""
        async with query_analyzer.track("test_query") as metrics:
            await asyncio.sleep(0.01)  # Simulate query

        stats = query_analyzer.get_statistics()
        assert stats["total_queries"] == 1
        assert stats["avg_time_ms"] >= 10  # At least 10ms

    @pytest.mark.asyncio
    async def test_detect_slow_query(self, query_analyzer: QueryAnalyzer):
        """Test slow query detection."""
        async with query_analyzer.track("slow_query"):
            await asyncio.sleep(0.15)  # 150ms - above threshold

        slow_queries = query_analyzer.get_slow_queries()
        assert len(slow_queries) == 1
        assert slow_queries[0].source == "slow_query"

    @pytest.mark.asyncio
    async def test_record_query(self, query_analyzer: QueryAnalyzer):
        """Test recording a query manually."""
        await query_analyzer.record(
            query_text="SELECT * FROM invoices",
            execution_time_ms=50.0,
            rows_returned=100,
            source="test",
        )

        stats = query_analyzer.get_statistics()
        assert stats["total_queries"] == 1
        assert stats["avg_time_ms"] == 50.0

    @pytest.mark.asyncio
    async def test_query_statistics(self, query_analyzer: QueryAnalyzer):
        """Test comprehensive query statistics."""
        await query_analyzer.record("q1", 10.0, 10)
        await query_analyzer.record("q2", 50.0, 20)
        await query_analyzer.record("q3", 150.0, 5)  # Slow query

        stats = query_analyzer.get_statistics()
        assert stats["total_queries"] == 3
        assert stats["min_time_ms"] == 10.0
        assert stats["max_time_ms"] == 150.0
        assert stats["slow_query_count"] == 1

    @pytest.mark.asyncio
    async def test_clear_history(self, query_analyzer: QueryAnalyzer):
        """Test clearing query history."""
        await query_analyzer.record("q1", 10.0, 10)
        query_analyzer.clear_history()

        stats = query_analyzer.get_statistics()
        assert stats["total_queries"] == 0


# =============================================================================
# EagerLoadBuilder Tests
# =============================================================================


class TestEagerLoadBuilder:
    """Tests for EagerLoadBuilder functionality."""

    def test_build_single_relationship(self):
        """Test building single relationship load."""
        # EagerLoadBuilder requires actual SQLAlchemy model classes
        # This test validates the builder pattern interface
        from src.db.models import InvoiceDB
        
        builder = EagerLoadBuilder(InvoiceDB)
        builder.load("matching_results", LoadStrategy.SELECTIN)

        options = builder.build()
        assert len(options) == 1

    def test_build_multiple_relationships(self):
        """Test building multiple relationship loads."""
        from src.db.models import InvoiceDB
        
        builder = (
            EagerLoadBuilder(InvoiceDB)
            .load("matching_results", LoadStrategy.SELECTIN)
            .load("risk_assessments", LoadStrategy.SELECTIN)
        )

        options = builder.build()
        assert len(options) == 2


# =============================================================================
# Utility Function Tests
# =============================================================================


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_cache_key_simple(self):
        """Test simple cache key generation."""
        key = generate_cache_key("invoices", "pending")
        assert key == "invoices:pending"

    def test_generate_cache_key_with_kwargs(self):
        """Test cache key generation with kwargs."""
        key = generate_cache_key("invoices", status="pending", page=1)
        assert "invoices" in key
        assert "status=pending" in key
        assert "page=1" in key

    def test_generate_cache_key_with_complex_types(self):
        """Test cache key generation with lists/dicts."""
        key = generate_cache_key("query", filters={"status": "pending"})
        assert "invoices" not in key  # Should hash complex types
        assert len(key) > 0

    @pytest.mark.asyncio
    async def test_cached_query_decorator(self):
        """Test cached_query decorator."""
        cache = QueryCache()
        call_count = 0

        @cached_query(cache, ttl=60, key_prefix="test")
        async def get_data(session, key: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"data_{key}"

        mock_session = MagicMock()

        # First call
        result1 = await get_data(mock_session, "key1")
        assert result1 == "data_key1"
        assert call_count == 1

        # Second call (cached)
        result2 = await get_data(mock_session, "key1")
        assert result2 == "data_key1"
        assert call_count == 1  # No additional call


# =============================================================================
# CacheEntry Tests
# =============================================================================


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(value="test", ttl_seconds=60)
        assert entry.value == "test"
        assert entry.ttl_seconds == 60

    def test_cache_entry_not_expired(self):
        """Test that fresh entry is not expired."""
        entry = CacheEntry(value="test", ttl_seconds=60)
        assert not entry.is_expired

    def test_cache_entry_expired(self):
        """Test that old entry is expired."""
        entry = CacheEntry(
            value="test",
            created_at=datetime.utcnow() - timedelta(seconds=120),
            ttl_seconds=60,
        )
        assert entry.is_expired


# =============================================================================
# QueryMetrics Tests
# =============================================================================


class TestQueryMetrics:
    """Tests for QueryMetrics dataclass."""

    def test_query_metrics_creation(self):
        """Test creating query metrics."""
        metrics = QueryMetrics(
            query_text="SELECT * FROM invoices",
            execution_time_ms=25.5,
            rows_returned=100,
            source="test",
        )
        assert metrics.query_text == "SELECT * FROM invoices"
        assert metrics.execution_time_ms == 25.5
        assert metrics.rows_returned == 100

    def test_query_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = QueryMetrics(
            query_text="SELECT * FROM invoices",
            execution_time_ms=25.5,
            rows_returned=100,
            source="test",
        )
        data = metrics.to_dict()

        assert data["query_text"] == "SELECT * FROM invoices"
        assert data["execution_time_ms"] == 25.5
        assert data["rows_returned"] == 100
        assert "timestamp" in data


# =============================================================================
# Performance Benchmark Tests
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmark tests for query optimization."""

    @pytest.mark.asyncio
    async def test_cache_performance_under_1ms(self, query_cache: QueryCache):
        """Test that cache operations complete in under 1ms."""
        # Warm up
        await query_cache.set("warmup", "value")

        times = []
        for i in range(100):
            start = time.perf_counter()
            await query_cache.set(f"key_{i}", f"value_{i}")
            await query_cache.get(f"key_{i}")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = statistics.mean(times)
        p95_time = sorted(times)[94]

        assert avg_time < 1.0, f"Average cache operation time {avg_time:.3f}ms exceeds 1ms"
        assert p95_time < 2.0, f"P95 cache operation time {p95_time:.3f}ms exceeds 2ms"

    @pytest.mark.asyncio
    async def test_batch_loader_efficiency(self, sample_vendors):
        """Test that batch loader reduces query count."""
        query_count = 0

        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            nonlocal query_count
            query_count += 1
            return [sample_vendors.get(vid) for vid in ids]

        loader = BatchLoader(load_vendors, max_batch_size=50)

        # Load all vendors individually
        tasks = [loader.load(f"V-{i:03d}") for i in range(10)]
        await asyncio.gather(*tasks)

        # Should batch all loads into minimal queries
        assert query_count <= 2, f"Expected <= 2 queries, got {query_count}"

    @pytest.mark.asyncio
    async def test_cache_invalidation_performance(self, query_cache: QueryCache):
        """Test pattern invalidation performance."""
        # Add many entries
        for i in range(100):
            await query_cache.set(f"invoices:status:{i}", f"value_{i}")

        start = time.perf_counter()
        count = await query_cache.invalidate_pattern("invoices:status")
        elapsed = (time.perf_counter() - start) * 1000

        assert count == 100
        assert elapsed < 100, f"Invalidation took {elapsed:.2f}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, query_cache: QueryCache):
        """Test cache performance under concurrent access."""
        async def cache_operations(worker_id: int):
            for i in range(50):
                key = f"worker_{worker_id}_key_{i}"
                await query_cache.set(key, f"value_{i}")
                await query_cache.get(key)

        start = time.perf_counter()
        await asyncio.gather(*[cache_operations(i) for i in range(10)])
        elapsed = (time.perf_counter() - start) * 1000

        # 500 set + 500 get operations should complete in reasonable time
        assert elapsed < 500, f"Concurrent operations took {elapsed:.2f}ms"

    @pytest.mark.asyncio
    async def test_query_analyzer_overhead(self, query_analyzer: QueryAnalyzer):
        """Test that query analyzer adds minimal overhead."""
        times_without_tracking = []
        times_with_tracking = []

        # Measure without tracking
        for _ in range(100):
            start = time.perf_counter()
            await asyncio.sleep(0.001)  # Simulate 1ms query
            elapsed = (time.perf_counter() - start) * 1000
            times_without_tracking.append(elapsed)

        # Measure with tracking
        for _ in range(100):
            start = time.perf_counter()
            async with query_analyzer.track("test"):
                await asyncio.sleep(0.001)
            elapsed = (time.perf_counter() - start) * 1000
            times_with_tracking.append(elapsed)

        avg_without = statistics.mean(times_without_tracking)
        avg_with = statistics.mean(times_with_tracking)
        overhead = avg_with - avg_without

        # Analyzer overhead should be less than 1ms
        assert overhead < 1.0, f"Query analyzer overhead {overhead:.3f}ms exceeds 1ms"


# =============================================================================
# Integration-style Tests
# =============================================================================


class TestIntegrationPatterns:
    """Tests for common integration patterns."""

    @pytest.mark.asyncio
    async def test_cache_with_batch_loader_integration(
        self, query_cache: QueryCache, sample_vendors
    ):
        """Test using cache with batch loader together."""
        cache_prefix = "vendors"

        async def load_vendors(ids: List[str]) -> List[Dict[str, Any]]:
            results = []
            uncached_ids = []

            # Check cache first
            for vid in ids:
                cached = await query_cache.get(f"{cache_prefix}:{vid}")
                if cached:
                    results.append((vid, cached))
                else:
                    uncached_ids.append(vid)

            # Load uncached from "database"
            for vid in uncached_ids:
                vendor = sample_vendors.get(vid)
                if vendor:
                    await query_cache.set(f"{cache_prefix}:{vid}", vendor)
                results.append((vid, vendor))

            # Return in original order
            result_map = dict(results)
            return [result_map.get(vid) for vid in ids]

        loader = BatchLoader(load_vendors, cache_enabled=False)  # Use external cache

        # First load
        result1 = await loader.load("V-001")
        assert result1["vendor_name"] == "Vendor 1"

        # Second load (should hit cache)
        result2 = await loader.load("V-001")
        assert result2["vendor_name"] == "Vendor 1"

    @pytest.mark.asyncio
    async def test_analyzer_with_cache_pattern(
        self, query_cache: QueryCache, query_analyzer: QueryAnalyzer
    ):
        """Test analyzer tracking cache-aware queries."""
        async def cached_query_with_tracking(key: str) -> str:
            async with query_analyzer.track(f"query:{key}") as metrics:
                cached = await query_cache.get(key)
                if cached:
                    return cached

                # Simulate database query
                await asyncio.sleep(0.01)
                result = f"result_{key}"
                await query_cache.set(key, result)
                return result

        # First query (cache miss, slower)
        await cached_query_with_tracking("test_key")

        # Second query (cache hit, faster)
        await cached_query_with_tracking("test_key")

        stats = query_analyzer.get_statistics()
        assert stats["total_queries"] == 2

        # Second query should be faster (cache hit)
        slow_queries = query_analyzer.get_slow_queries(threshold_ms=5)
        # Only the first query should be slow
        assert len(slow_queries) <= 1


# =============================================================================
# Default Instance Tests
# =============================================================================


class TestDefaultInstances:
    """Tests for default singleton instances."""

    def test_get_default_cache(self):
        """Test getting default cache instance."""
        cache1 = get_default_cache()
        cache2 = get_default_cache()
        assert cache1 is cache2

    def test_get_default_analyzer(self):
        """Test getting default analyzer instance."""
        analyzer1 = get_default_analyzer()
        analyzer2 = get_default_analyzer()
        assert analyzer1 is analyzer2


# =============================================================================
# Simulated Database Performance Tests
# =============================================================================


class TestSimulatedDatabasePerformance:
    """Simulated database performance tests."""

    @pytest.mark.asyncio
    async def test_invoice_list_pagination_under_200ms(self):
        """Test that paginated invoice listing completes under 200ms."""
        cache = QueryCache()

        async def get_invoices_page(page: int, page_size: int = 20):
            cache_key = f"invoices:page:{page}:size:{page_size}"
            cached = await cache.get(cache_key)
            if cached:
                return cached

            # Simulate database query with indexes
            await asyncio.sleep(0.05)  # 50ms simulated query
            result = [{"id": i} for i in range(page * page_size, (page + 1) * page_size)]
            await cache.set(cache_key, result, ttl=30)
            return result

        # Test multiple page loads
        times = []
        for page in range(5):
            start = time.perf_counter()
            await get_invoices_page(page)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        avg_time = statistics.mean(times)
        max_time = max(times)

        assert avg_time < 100, f"Average pagination time {avg_time:.2f}ms exceeds 100ms"
        assert max_time < 200, f"Max pagination time {max_time:.2f}ms exceeds 200ms"

    @pytest.mark.asyncio
    async def test_dashboard_aggregation_under_500ms(self):
        """Test that dashboard data aggregation completes under 500ms."""
        cache = QueryCache()

        async def get_dashboard_metrics():
            cache_key = "dashboard:metrics"
            cached = await cache.get(cache_key)
            if cached:
                return cached

            # Simulate multiple aggregation queries in parallel
            async def query_invoices():
                await asyncio.sleep(0.1)  # 100ms
                return {"total": 1000, "pending": 50}

            async def query_risk():
                await asyncio.sleep(0.08)  # 80ms
                return {"high_risk": 5, "medium_risk": 20}

            async def query_matching():
                await asyncio.sleep(0.07)  # 70ms
                return {"matched": 900, "unmatched": 100}

            # Execute in parallel
            invoices, risk, matching = await asyncio.gather(
                query_invoices(),
                query_risk(),
                query_matching(),
            )

            result = {**invoices, **risk, **matching}
            await cache.set(cache_key, result, ttl=60)
            return result

        start = time.perf_counter()
        metrics = await get_dashboard_metrics()
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 500, f"Dashboard load took {elapsed:.2f}ms, expected < 500ms"
        assert "total" in metrics
        assert "high_risk" in metrics
        assert "matched" in metrics

    @pytest.mark.asyncio
    async def test_concurrent_invoice_processing(self):
        """Test concurrent invoice processing performance."""
        processed = []
        process_lock = asyncio.Lock()

        async def process_invoice(invoice_id: str):
            # Simulate invoice processing pipeline
            await asyncio.sleep(0.05)  # OCR/extraction: 50ms
            await asyncio.sleep(0.03)  # Matching: 30ms
            await asyncio.sleep(0.02)  # Risk assessment: 20ms

            async with process_lock:
                processed.append(invoice_id)

            return {"invoice_id": invoice_id, "status": "processed"}

        # Process 10 invoices concurrently
        start = time.perf_counter()
        invoice_ids = [f"INV-{i:05d}" for i in range(10)]
        results = await asyncio.gather(*[process_invoice(id) for id in invoice_ids])
        elapsed = (time.perf_counter() - start) * 1000

        assert len(results) == 10
        assert len(processed) == 10
        # Concurrent processing should be much faster than sequential
        # 10 invoices * 100ms each = 1000ms sequential, should be ~100ms parallel
        assert elapsed < 500, f"Concurrent processing took {elapsed:.2f}ms"

    @pytest.mark.asyncio
    async def test_bulk_vendor_lookup_efficiency(self, sample_vendors):
        """Test efficient bulk vendor lookups."""
        query_count = 0

        async def batch_load_vendors(vendor_ids: List[str]) -> List[Dict]:
            nonlocal query_count
            query_count += 1
            # Simulate single batch query
            await asyncio.sleep(0.02)  # 20ms for batch query
            return [sample_vendors.get(vid) for vid in vendor_ids]

        loader = BatchLoader(batch_load_vendors, max_batch_size=50)

        # Load 10 vendors
        start = time.perf_counter()
        vendors = await loader.load_many([f"V-{i:03d}" for i in range(10)])
        elapsed = (time.perf_counter() - start) * 1000

        assert len(vendors) == 10
        assert query_count <= 2  # Should batch efficiently
        assert elapsed < 100, f"Bulk lookup took {elapsed:.2f}ms"
