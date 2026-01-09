"""
Monitoring and Metrics Utilities

Provides performance metrics collection, request tracking, and monitoring helpers.
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from threading import Lock
from contextlib import asynccontextmanager
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class EndpointStats:
    """Aggregated statistics for an endpoint."""
    total_requests: int = 0
    total_errors: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    status_codes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def avg_duration_ms(self) -> float:
        """Average response time in milliseconds."""
        return self.total_duration_ms / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def error_rate(self) -> float:
        """Error rate as a percentage."""
        return (self.total_errors / self.total_requests * 100) if self.total_requests > 0 else 0.0


class MetricsCollector:
    """
    Collects and aggregates application metrics.
    
    Usage:
        collector = MetricsCollector()
        
        # Record a request
        collector.record_request(
            method="GET",
            path="/api/invoices",
            status_code=200,
            duration_ms=45.2
        )
        
        # Get summary
        summary = collector.get_summary()
    """
    
    _instance: Optional["MetricsCollector"] = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern for global metrics collection."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._requests: List[RequestMetrics] = []
        self._endpoint_stats: Dict[str, EndpointStats] = defaultdict(EndpointStats)
        self._service_calls: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "total_duration_ms": 0.0,
        })
        self._start_time = datetime.utcnow()
        self._max_history = 10000  # Keep last N requests
        self._data_lock = Lock()
        self._initialized = True
    
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        error: Optional[str] = None,
    ):
        """Record metrics for a request."""
        metric = RequestMetrics(
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            error=error,
        )
        
        with self._data_lock:
            # Add to history (with size limit)
            self._requests.append(metric)
            if len(self._requests) > self._max_history:
                self._requests = self._requests[-self._max_history:]
            
            # Update endpoint stats
            endpoint_key = f"{method} {self._normalize_path(path)}"
            stats = self._endpoint_stats[endpoint_key]
            stats.total_requests += 1
            stats.total_duration_ms += duration_ms
            stats.min_duration_ms = min(stats.min_duration_ms, duration_ms)
            stats.max_duration_ms = max(stats.max_duration_ms, duration_ms)
            stats.status_codes[status_code] += 1
            
            if status_code >= 500:
                stats.total_errors += 1
    
    def record_service_call(
        self,
        service_name: str,
        success: bool,
        duration_ms: float,
    ):
        """Record metrics for an external service call."""
        with self._data_lock:
            stats = self._service_calls[service_name]
            stats["total"] += 1
            stats["total_duration_ms"] += duration_ms
            if success:
                stats["success"] += 1
            else:
                stats["failure"] += 1
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing IDs with placeholders."""
        import re
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        # Replace numeric IDs
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        return path
    
    def get_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get a summary of metrics for the specified time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        with self._data_lock:
            recent = [r for r in self._requests if r.timestamp > cutoff]
            
            # Calculate summary stats
            total_requests = len(recent)
            total_errors = sum(1 for r in recent if r.status_code >= 500)
            avg_duration = sum(r.duration_ms for r in recent) / total_requests if total_requests > 0 else 0
            
            # Get top endpoints by request count
            endpoint_counts = defaultdict(int)
            for r in recent:
                key = f"{r.method} {self._normalize_path(r.path)}"
                endpoint_counts[key] += 1
            
            top_endpoints = sorted(
                endpoint_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Get slowest endpoints
            endpoint_durations = defaultdict(list)
            for r in recent:
                key = f"{r.method} {self._normalize_path(r.path)}"
                endpoint_durations[key].append(r.duration_ms)
            
            slowest_endpoints = sorted(
                [
                    (k, sum(v) / len(v))
                    for k, v in endpoint_durations.items()
                ],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "window_minutes": minutes,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2),
                "top_endpoints": [{"endpoint": k, "count": v} for k, v in top_endpoints],
                "slowest_endpoints": [{"endpoint": k, "avg_ms": round(v, 2)} for k, v in slowest_endpoints],
                "service_calls": dict(self._service_calls),
                "uptime_seconds": (datetime.utcnow() - self._start_time).total_seconds(),
            }
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed stats for all endpoints."""
        with self._data_lock:
            return {
                endpoint: {
                    "total_requests": stats.total_requests,
                    "total_errors": stats.total_errors,
                    "error_rate": round(stats.error_rate, 2),
                    "avg_duration_ms": round(stats.avg_duration_ms, 2),
                    "min_duration_ms": round(stats.min_duration_ms, 2) if stats.min_duration_ms != float('inf') else 0,
                    "max_duration_ms": round(stats.max_duration_ms, 2),
                    "status_codes": dict(stats.status_codes),
                }
                for endpoint, stats in self._endpoint_stats.items()
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._data_lock:
            self._requests.clear()
            self._endpoint_stats.clear()
            self._service_calls.clear()
            self._start_time = datetime.utcnow()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return MetricsCollector()


@asynccontextmanager
async def track_service_call(service_name: str):
    """
    Context manager to track external service call duration and success.
    
    Usage:
        async with track_service_call("foxit_ocr"):
            result = await call_foxit_api()
    """
    collector = get_metrics_collector()
    start = time.perf_counter()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        collector.record_service_call(service_name, success, duration_ms)


def timed_operation(operation_name: str):
    """
    Decorator to track operation timing.
    
    Usage:
        @timed_operation("database_query")
        async def fetch_invoices():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with track_service_call(operation_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


class HealthChecker:
    """
    Comprehensive health checker for all system components.
    
    Provides methods to check health of:
    - Database
    - Redis cache
    - AI service
    - OCR service
    - ERP integrations
    - eSign service
    - Circuit breakers
    - File storage
    """
    
    def __init__(self, settings):
        self.settings = settings
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        try:
            from ..db.database import async_session_maker
            from sqlalchemy import text
            
            start = time.perf_counter()
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            duration_ms = (time.perf_counter() - start) * 1000
            
            return {
                "status": "healthy",
                "type": "postgresql",
                "latency_ms": round(duration_ms, 2),
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "type": "postgresql",
                "error": str(e),
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            import redis.asyncio as redis
            
            start = time.perf_counter()
            r = redis.from_url(self.settings.redis_url, decode_responses=True)
            await r.ping()
            info = await r.info("memory")
            await r.close()
            duration_ms = (time.perf_counter() - start) * 1000
            
            return {
                "status": "healthy",
                "type": "redis",
                "latency_ms": round(duration_ms, 2),
                "memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "type": "redis",
                "error": str(e),
            }
    
    def check_ai_service(self) -> Dict[str, Any]:
        """Check AI service configuration."""
        if self.settings.ai_provider == "github" and self.settings.github_token:
            return {
                "status": "configured",
                "provider": "github_models",
                "model": self.settings.model_id,
            }
        elif self.settings.ai_provider == "openai" and self.settings.openai_api_key:
            return {
                "status": "configured",
                "provider": "openai",
                "model": self.settings.model_id,
            }
        elif self.settings.ai_provider == "azure" and self.settings.azure_openai_api_key:
            return {
                "status": "configured",
                "provider": "azure_openai",
                "model": self.settings.model_id,
            }
        return {
            "status": "not_configured",
            "message": "No AI credentials configured",
        }
    
    def check_ocr_service(self) -> Dict[str, Any]:
        """Check OCR service configuration."""
        if self.settings.foxit_api_key:
            return {
                "status": "configured",
                "provider": "foxit",
            }
        return {
            "status": "fallback",
            "provider": "pytesseract",
            "message": "Using local OCR fallback",
        }
    
    def check_erp_integrations(self) -> Dict[str, Any]:
        """Check ERP integration configurations."""
        erp_status = {}
        
        # Check each ERP provider
        if hasattr(self.settings, 'xero_client_id') and self.settings.xero_client_id:
            erp_status["xero"] = {"status": "configured"}
        
        if hasattr(self.settings, 'quickbooks_client_id') and self.settings.quickbooks_client_id:
            erp_status["quickbooks"] = {"status": "configured"}
        
        if hasattr(self.settings, 'netsuite_account_id') and self.settings.netsuite_account_id:
            erp_status["netsuite"] = {"status": "configured"}
        
        if hasattr(self.settings, 'sap_api_url') and self.settings.sap_api_url:
            erp_status["sap"] = {"status": "configured"}
        
        if not erp_status:
            return {
                "status": "not_configured",
                "message": "No ERP integrations configured",
            }
        
        return {
            "status": "configured",
            "providers": erp_status,
            "sync_enabled": getattr(self.settings, 'erp_sync_enabled', False),
        }
    
    def check_esign_service(self) -> Dict[str, Any]:
        """Check eSign service configuration."""
        if hasattr(self.settings, 'foxit_esign_api_key') and self.settings.foxit_esign_api_key:
            return {
                "status": "configured",
                "provider": "foxit_esign",
            }
        return {
            "status": "not_configured",
            "message": "eSign service not configured",
        }
    
    def check_circuit_breakers(self) -> Dict[str, Any]:
        """Check status of all circuit breakers."""
        try:
            from .circuit_breaker import CircuitBreaker
            
            states = CircuitBreaker.get_all_states()
            
            if not states:
                return {
                    "status": "no_breakers",
                    "message": "No circuit breakers registered",
                }
            
            # Check if any are open
            open_breakers = [name for name, state in states.items() if state.value == "open"]
            
            return {
                "status": "degraded" if open_breakers else "healthy",
                "breakers": {name: state.value for name, state in states.items()},
                "open_count": len(open_breakers),
            }
        except ImportError:
            return {
                "status": "unavailable",
                "message": "Circuit breaker module not available",
            }
    
    def check_storage(self) -> Dict[str, Any]:
        """Check storage directories."""
        from pathlib import Path
        import os
        import shutil
        
        upload_path = Path(self.settings.upload_dir)
        processed_path = Path(self.settings.processed_dir)
        
        issues = []
        
        if not upload_path.exists():
            issues.append("upload_dir missing")
        elif not os.access(upload_path, os.W_OK):
            issues.append("upload_dir not writable")
        
        if not processed_path.exists():
            issues.append("processed_dir missing")
        elif not os.access(processed_path, os.W_OK):
            issues.append("processed_dir not writable")
        
        # Get disk usage
        try:
            usage = shutil.disk_usage(upload_path if upload_path.exists() else "/")
            disk_free_gb = usage.free / (1024**3)
            disk_used_percent = (usage.used / usage.total) * 100
        except Exception:
            disk_free_gb = 0
            disk_used_percent = 100
        
        return {
            "status": "unhealthy" if issues else "healthy",
            "upload_dir": str(upload_path),
            "processed_dir": str(processed_path),
            "issues": issues if issues else None,
            "disk_free_gb": round(disk_free_gb, 2),
            "disk_used_percent": round(disk_used_percent, 1),
        }
    
    async def get_full_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report for all components."""
        from datetime import datetime
        
        # Run async checks
        db_health = await self.check_database()
        redis_health = await self.check_redis()
        
        # Run sync checks
        ai_health = self.check_ai_service()
        ocr_health = self.check_ocr_service()
        erp_health = self.check_erp_integrations()
        esign_health = self.check_esign_service()
        circuit_health = self.check_circuit_breakers()
        storage_health = self.check_storage()
        
        # Determine overall status
        components = {
            "database": db_health,
            "cache": redis_health,
            "ai": ai_health,
            "ocr": ocr_health,
            "erp": erp_health,
            "esign": esign_health,
            "circuit_breakers": circuit_health,
            "storage": storage_health,
        }
        
        # Check for critical failures
        critical_components = ["database", "storage"]
        critical_issues = [
            name for name in critical_components
            if components.get(name, {}).get("status") == "unhealthy"
        ]
        
        # Check for degraded services
        degraded_components = [
            name for name, status in components.items()
            if status.get("status") in ("unhealthy", "degraded")
        ]
        
        if critical_issues:
            overall_status = "unhealthy"
        elif degraded_components:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "service": "smartap-api",
            "version": self.settings.app_version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": components,
            "issues": degraded_components if degraded_components else None,
        }


def get_health_checker(settings) -> HealthChecker:
    """Get a health checker instance."""
    return HealthChecker(settings)
