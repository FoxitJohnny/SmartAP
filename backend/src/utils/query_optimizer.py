"""Query optimization utilities for preventing N+1 queries and improving performance.

This module provides utilities for:
- Batch loading to prevent N+1 queries
- Eager loading configuration for relationships
- Query result caching
- Query performance analysis and logging
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from sqlalchemy import Select, event, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    RelationshipProperty,
    joinedload,
    selectinload,
    subqueryload,
    Load,
)
from sqlalchemy.orm.strategy_options import _AbstractLoad

logger = logging.getLogger(__name__)

T = TypeVar("T")
ModelT = TypeVar("ModelT")


class LoadStrategy(str, Enum):
    """SQLAlchemy relationship loading strategies."""

    JOINED = "joined"  # Single query with JOIN
    SELECTIN = "selectin"  # Separate SELECT IN query
    SUBQUERY = "subquery"  # Subquery-based loading
    LAZY = "lazy"  # Default lazy loading (N+1 risk)


@dataclass
class QueryMetrics:
    """Metrics for query performance analysis."""

    query_text: str
    execution_time_ms: float
    rows_returned: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parameters: Optional[Dict[str, Any]] = None
    source: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "query_text": self.query_text[:500],  # Truncate for logging
            "execution_time_ms": round(self.execution_time_ms, 2),
            "rows_returned": self.rows_returned,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with expiration support."""

    value: T
    created_at: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300  # 5 minutes default

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)


class QueryCache:
    """In-memory query result cache with TTL support.

    Provides caching for expensive database queries with automatic expiration.
    Thread-safe using asyncio locks.

    Example:
        cache = QueryCache(default_ttl=300)

        async def get_invoices(session: AsyncSession, status: str):
            cache_key = f"invoices:status:{status}"

            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            result = await session.execute(query)
            invoices = result.scalars().all()

            await cache.set(cache_key, invoices, ttl=60)
            return invoices
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        """Initialize query cache.

        Args:
            default_ttl: Default time-to-live in seconds.
            max_size: Maximum number of cache entries.
        """
        self._cache: Dict[str, CacheEntry[Any]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found/expired.
        """
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

    async def set(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        """Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (uses default if not specified).
        """
        async with self._lock:
            # Evict expired entries if cache is full
            if len(self._cache) >= self._max_size:
                await self._evict_expired()

            # If still full, evict oldest entries
            if len(self._cache) >= self._max_size:
                await self._evict_oldest(len(self._cache) - self._max_size + 1)

            self._cache[key] = CacheEntry(
                value=value,
                ttl_seconds=ttl or self._default_ttl,
            )

    async def delete(self, key: str) -> bool:
        """Delete a cache entry.

        Args:
            key: Cache key.

        Returns:
            True if entry was deleted, False if not found.
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all entries matching a pattern.

        Args:
            pattern: Key pattern (prefix match).

        Returns:
            Number of entries invalidated.
        """
        async with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    async def _evict_expired(self) -> int:
        """Evict all expired entries. Must be called with lock held."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    async def _evict_oldest(self, count: int) -> None:
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
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }


class BatchLoader(Generic[T]):
    """Batch loader for efficient data fetching.

    Groups individual load requests into batches to prevent N+1 queries.
    Uses a DataLoader-like pattern.

    Example:
        async def load_vendors(vendor_ids: List[str]) -> List[Vendor]:
            result = await session.execute(
                select(Vendor).where(Vendor.vendor_id.in_(vendor_ids))
            )
            vendors = {v.vendor_id: v for v in result.scalars().all()}
            return [vendors.get(vid) for vid in vendor_ids]

        vendor_loader = BatchLoader(load_vendors, max_batch_size=100)

        # These will be batched into a single query
        vendor1 = await vendor_loader.load("V001")
        vendor2 = await vendor_loader.load("V002")
    """

    def __init__(
        self,
        batch_load_fn: Callable[[List[Any]], Awaitable[List[T]]],
        max_batch_size: int = 100,
        cache_enabled: bool = True,
    ):
        """Initialize batch loader.

        Args:
            batch_load_fn: Function that loads items by keys.
            max_batch_size: Maximum batch size.
            cache_enabled: Whether to cache loaded items.
        """
        self._batch_load_fn = batch_load_fn
        self._max_batch_size = max_batch_size
        self._cache_enabled = cache_enabled
        self._cache: Dict[Any, T] = {}
        self._pending: Dict[Any, asyncio.Future[T]] = {}
        self._batch: List[Any] = []
        self._batch_lock = asyncio.Lock()
        self._scheduled = False

    async def load(self, key: Any) -> Optional[T]:
        """Load a single item by key.

        Args:
            key: Item key.

        Returns:
            Loaded item or None.
        """
        # Check cache first
        if self._cache_enabled and key in self._cache:
            return self._cache[key]

        # Check if already pending
        if key in self._pending:
            return await self._pending[key]

        # Add to batch
        async with self._batch_lock:
            future: asyncio.Future[T] = asyncio.get_event_loop().create_future()
            self._pending[key] = future
            self._batch.append(key)

            # Schedule batch execution
            if not self._scheduled:
                self._scheduled = True
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.create_task(self._execute_batch())
                )

        return await future

    async def load_many(self, keys: List[Any]) -> List[Optional[T]]:
        """Load multiple items by keys.

        Args:
            keys: List of item keys.

        Returns:
            List of loaded items (None for missing keys).
        """
        return await asyncio.gather(*[self.load(key) for key in keys])

    async def _execute_batch(self) -> None:
        """Execute the pending batch load."""
        async with self._batch_lock:
            if not self._batch:
                self._scheduled = False
                return

            # Get batch to process
            keys = self._batch[: self._max_batch_size]
            self._batch = self._batch[self._max_batch_size:]

            # Schedule next batch if needed
            if self._batch:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.create_task(self._execute_batch())
                )
            else:
                self._scheduled = False

        try:
            # Execute batch load
            results = await self._batch_load_fn(keys)

            # Resolve futures and update cache
            for key, result in zip(keys, results):
                if self._cache_enabled and result is not None:
                    self._cache[key] = result

                future = self._pending.pop(key, None)
                if future and not future.done():
                    future.set_result(result)

        except Exception as e:
            # Reject all pending futures
            for key in keys:
                future = self._pending.pop(key, None)
                if future and not future.done():
                    future.set_exception(e)

    def clear_cache(self) -> None:
        """Clear the batch loader cache."""
        self._cache.clear()

    def prime(self, key: Any, value: T) -> None:
        """Prime the cache with a value.

        Args:
            key: Item key.
            value: Item value.
        """
        if self._cache_enabled:
            self._cache[key] = value


class EagerLoadBuilder:
    """Builder for constructing eager loading options.

    Provides a fluent interface for building SQLAlchemy loading options.

    Example:
        options = (
            EagerLoadBuilder(Invoice)
            .load("vendor", strategy=LoadStrategy.JOINED)
            .load("line_items", strategy=LoadStrategy.SELECTIN)
            .load("matching_results.purchase_order", strategy=LoadStrategy.JOINED)
            .build()
        )

        query = select(Invoice).options(*options)
    """

    def __init__(self, model: Type[ModelT]):
        """Initialize builder for a model.

        Args:
            model: SQLAlchemy model class.
        """
        self._model = model
        self._loads: List[Tuple[str, LoadStrategy]] = []

    def load(
        self,
        relationship_path: str,
        strategy: LoadStrategy = LoadStrategy.SELECTIN,
    ) -> "EagerLoadBuilder":
        """Add a relationship to load.

        Args:
            relationship_path: Dot-separated path to relationship.
            strategy: Loading strategy to use.

        Returns:
            Self for chaining.
        """
        self._loads.append((relationship_path, strategy))
        return self

    def build(self) -> List[_AbstractLoad]:
        """Build SQLAlchemy loading options.

        Returns:
            List of SQLAlchemy load options.
        """
        options: List[_AbstractLoad] = []

        for path, strategy in self._loads:
            parts = path.split(".")
            load_option = self._get_loader(strategy, parts[0])

            for part in parts[1:]:
                load_option = load_option.options(
                    self._get_loader(strategy, part)
                )

            options.append(load_option)

        return options

    def _get_loader(self, strategy: LoadStrategy, attr: str) -> _AbstractLoad:
        """Get the appropriate loader for a strategy."""
        if strategy == LoadStrategy.JOINED:
            return joinedload(getattr(self._model, attr, attr))
        elif strategy == LoadStrategy.SELECTIN:
            return selectinload(getattr(self._model, attr, attr))
        elif strategy == LoadStrategy.SUBQUERY:
            return subqueryload(getattr(self._model, attr, attr))
        else:
            raise ValueError(f"Unsupported strategy: {strategy}")


class QueryAnalyzer:
    """Analyze and log query performance.

    Tracks query execution times and identifies slow queries.

    Example:
        analyzer = QueryAnalyzer(slow_query_threshold_ms=100)

        async with analyzer.track("load_invoices"):
            result = await session.execute(query)

        # Check for slow queries
        slow = analyzer.get_slow_queries()
    """

    def __init__(
        self,
        slow_query_threshold_ms: float = 100.0,
        max_history: int = 1000,
    ):
        """Initialize query analyzer.

        Args:
            slow_query_threshold_ms: Threshold for slow query warnings.
            max_history: Maximum number of queries to keep in history.
        """
        self._slow_threshold = slow_query_threshold_ms
        self._max_history = max_history
        self._history: List[QueryMetrics] = []
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def track(self, source: str = "unknown"):
        """Context manager for tracking query execution.

        Args:
            source: Source identifier for the query.

        Yields:
            QueryMetrics instance (updated after execution).
        """
        metrics = QueryMetrics(
            query_text="",
            execution_time_ms=0,
            rows_returned=0,
            source=source,
        )

        start_time = time.perf_counter()
        try:
            yield metrics
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            metrics.execution_time_ms = elapsed_ms

            if elapsed_ms > self._slow_threshold:
                logger.warning(
                    f"Slow query detected ({source}): {elapsed_ms:.2f}ms"
                )

            async with self._lock:
                self._history.append(metrics)
                if len(self._history) > self._max_history:
                    self._history = self._history[-self._max_history:]

    async def record(
        self,
        query_text: str,
        execution_time_ms: float,
        rows_returned: int,
        source: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a query execution.

        Args:
            query_text: SQL query text.
            execution_time_ms: Execution time in milliseconds.
            rows_returned: Number of rows returned.
            source: Source identifier.
            parameters: Query parameters.
        """
        metrics = QueryMetrics(
            query_text=query_text,
            execution_time_ms=execution_time_ms,
            rows_returned=rows_returned,
            source=source,
            parameters=parameters,
        )

        if execution_time_ms > self._slow_threshold:
            logger.warning(
                f"Slow query recorded ({source}): {execution_time_ms:.2f}ms"
            )

        async with self._lock:
            self._history.append(metrics)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def get_slow_queries(
        self, threshold_ms: Optional[float] = None
    ) -> List[QueryMetrics]:
        """Get queries exceeding the threshold.

        Args:
            threshold_ms: Custom threshold (uses default if not specified).

        Returns:
            List of slow query metrics.
        """
        threshold = threshold_ms or self._slow_threshold
        return [m for m in self._history if m.execution_time_ms > threshold]

    def get_statistics(self) -> Dict[str, Any]:
        """Get query statistics.

        Returns:
            Statistics dictionary.
        """
        if not self._history:
            return {
                "total_queries": 0,
                "avg_time_ms": 0,
                "max_time_ms": 0,
                "min_time_ms": 0,
                "slow_query_count": 0,
            }

        times = [m.execution_time_ms for m in self._history]
        slow_count = len([t for t in times if t > self._slow_threshold])

        return {
            "total_queries": len(self._history),
            "avg_time_ms": round(sum(times) / len(times), 2),
            "max_time_ms": round(max(times), 2),
            "min_time_ms": round(min(times), 2),
            "slow_query_count": slow_count,
            "slow_query_threshold_ms": self._slow_threshold,
        }

    def clear_history(self) -> None:
        """Clear query history."""
        self._history.clear()


def generate_cache_key(
    prefix: str,
    *args: Any,
    **kwargs: Any,
) -> str:
    """Generate a cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix.
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Returns:
        Cache key string.
    """
    key_parts = [prefix]

    # Add positional args
    for arg in args:
        if isinstance(arg, (list, dict)):
            key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest()[:8])
        else:
            key_parts.append(str(arg))

    # Add sorted keyword args
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (list, dict)):
            value_str = hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()[:8]
        else:
            value_str = str(value)
        key_parts.append(f"{key}={value_str}")

    return ":".join(key_parts)


def cached_query(
    cache: QueryCache,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
):
    """Decorator for caching query results.

    Args:
        cache: QueryCache instance.
        ttl: Time-to-live in seconds.
        key_prefix: Cache key prefix.

    Example:
        @cached_query(cache, ttl=60, key_prefix="invoices")
        async def get_invoices_by_status(session, status):
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        prefix = key_prefix or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Skip session argument in cache key
            cache_args = args[1:] if args else ()
            cache_key = generate_cache_key(prefix, *cache_args, **kwargs)

            # Try cache
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute query
            result = await func(*args, **kwargs)

            # Cache result
            await cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# Global instances for convenience
_default_cache = QueryCache()
_default_analyzer = QueryAnalyzer()


def get_default_cache() -> QueryCache:
    """Get the default query cache instance."""
    return _default_cache


def get_default_analyzer() -> QueryAnalyzer:
    """Get the default query analyzer instance."""
    return _default_analyzer


# Common eager loading configurations
INVOICE_EAGER_LOADS = [
    ("vendor", LoadStrategy.JOINED),
    ("line_items", LoadStrategy.SELECTIN),
    ("matching_results", LoadStrategy.SELECTIN),
    ("risk_assessments", LoadStrategy.SELECTIN),
]

PO_EAGER_LOADS = [
    ("vendor", LoadStrategy.JOINED),
    ("line_items", LoadStrategy.SELECTIN),
]

MATCHING_RESULT_EAGER_LOADS = [
    ("invoice", LoadStrategy.JOINED),
    ("purchase_order", LoadStrategy.JOINED),
]


def get_invoice_load_options() -> List[_AbstractLoad]:
    """Get optimized load options for invoices."""
    return [
        joinedload("vendor"),
        selectinload("line_items"),
        selectinload("matching_results"),
        selectinload("risk_assessments"),
    ]


def get_po_load_options() -> List[_AbstractLoad]:
    """Get optimized load options for purchase orders."""
    return [
        joinedload("vendor"),
        selectinload("line_items"),
    ]


def get_matching_result_load_options() -> List[_AbstractLoad]:
    """Get optimized load options for matching results."""
    return [
        joinedload("invoice"),
        joinedload("purchase_order"),
    ]
