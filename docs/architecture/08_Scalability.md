# SmartAP Scalability & Performance

**Section 8 of Architecture Documentation**

---

## Table of Contents

1. [Scalability Overview](#scalability-overview)
2. [Horizontal Scaling](#horizontal-scaling)
3. [Caching Strategy](#caching-strategy)
4. [Database Optimization](#database-optimization)
5. [Async Processing](#async-processing)
6. [Monitoring & Observability](#monitoring--observability)
7. [Performance Benchmarks](#performance-benchmarks)
8. [Capacity Planning](#capacity-planning)

---

## Scalability Overview

### Architecture for Scale

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        Scalable Architecture Overview                                │
└─────────────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────────────┐
                              │   Load Balancer   │
                              │   (Azure/NGINX)   │
                              └─────────┬─────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼─────────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
    │   API Server 1    │    │   API Server 2    │    │   API Server N    │
    │   (FastAPI)       │    │   (FastAPI)       │    │   (FastAPI)       │
    └─────────┬─────────┘    └─────────┬─────────┘    └─────────┬─────────┘
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼─────────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
    │   Redis Cluster   │    │  PostgreSQL HA    │    │  Message Queue    │
    │   (Cache/Session) │    │  (Primary/Replica)│    │   (RabbitMQ)      │
    └───────────────────┘    └───────────────────┘    └─────────┬─────────┘
                                                                │
                              ┌─────────────────────────────────┼─────────┐
                              │                                 │         │
                    ┌─────────▼─────────┐            ┌─────────▼────┐    │
                    │   Worker Node 1   │            │ Worker Node N│    │
                    │   (Celery)        │            │ (Celery)     │    │
                    └───────────────────┘            └──────────────┘    │
                                                                         │
                    ┌────────────────────────────────────────────────────┘
                    │
        ┌───────────▼───────────┐
        │   Storage (Blob/S3)   │
        │   (PDFs, Attachments) │
        └───────────────────────┘
```

### Scaling Dimensions

| Dimension | Strategy | Tools |
|-----------|----------|-------|
| **API Layer** | Horizontal Pod Autoscaler | Kubernetes HPA |
| **Database** | Read replicas, Connection pooling | PostgreSQL, PgBouncer |
| **Cache** | Redis Cluster | Redis Sentinel/Cluster |
| **Workers** | Dynamic worker scaling | Celery, KEDA |
| **Storage** | CDN, Object storage | Azure Blob, CloudFront |

---

## Horizontal Scaling

### Kubernetes Autoscaling

```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: smartap-api-hpa
  namespace: smartap
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: smartap-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    # CPU-based scaling
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    # Memory-based scaling
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    # Custom metric: requests per second
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: 100
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Pods
          value: 4
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

### Worker Autoscaling with KEDA

```yaml
# kubernetes/keda-scaler.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: smartap-worker-scaler
  namespace: smartap
spec:
  scaleTargetRef:
    name: smartap-worker
  minReplicaCount: 2
  maxReplicaCount: 50
  pollingInterval: 15
  triggers:
    # Scale based on queue length
    - type: rabbitmq
      metadata:
        host: amqp://rabbitmq.smartap.svc.cluster.local
        queueName: invoice_processing
        queueLength: "10"
    # Scale based on CPU
    - type: cpu
      metadata:
        type: Utilization
        value: "70"
```

### Stateless Design Principles

```python
# src/core/config.py
# Stateless API server configuration

class Settings(BaseSettings):
    # Use external session storage
    SESSION_STORAGE: str = "redis"
    REDIS_URL: str = "redis://redis-cluster:6379"
    
    # Externalize file storage
    STORAGE_BACKEND: str = "azure_blob"
    AZURE_STORAGE_CONNECTION: str
    
    # Distributed cache
    CACHE_BACKEND: str = "redis"
    
    # No local state - all shared via database/cache
    TEMP_DIR: str = "/tmp/smartap"  # Ephemeral container storage
```

---

## Caching Strategy

### Multi-Level Cache Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Multi-Level Cache Strategy                       │
└─────────────────────────────────────────────────────────────────────┘

    Request
       │
       ▼
┌──────────────────┐     Cache Miss      ┌──────────────────┐
│   L1: In-Memory  │ ─────────────────►  │   L2: Redis      │
│   (LRU, 100MB)   │                     │   (Distributed)  │
│   TTL: 60s       │ ◄───────────────── │   TTL: 5-60min   │
└──────────────────┘     Cache Fill      └────────┬─────────┘
                                                  │
                                         Cache Miss
                                                  │
                                                  ▼
                                         ┌──────────────────┐
                                         │   L3: Database   │
                                         │   (PostgreSQL)   │
                                         └──────────────────┘
```

### Cache Implementation

```python
# src/core/cache.py
from functools import wraps
import redis
import json
import hashlib

class CacheService:
    def __init__(self):
        self.redis = redis.Redis.from_url(settings.REDIS_URL)
        self.local_cache = {}  # L1 in-memory cache
        self.local_ttl = 60    # L1 TTL in seconds
    
    def get(self, key: str) -> Optional[dict]:
        """Get from cache with L1/L2 fallback."""
        # L1 check
        if key in self.local_cache:
            entry = self.local_cache[key]
            if entry["expires"] > time.time():
                return entry["value"]
            del self.local_cache[key]
        
        # L2 check
        value = self.redis.get(key)
        if value:
            data = json.loads(value)
            # Populate L1
            self.local_cache[key] = {
                "value": data,
                "expires": time.time() + self.local_ttl
            }
            return data
        
        return None
    
    def set(self, key: str, value: dict, ttl: int = 300):
        """Set in both L1 and L2 cache."""
        # L1
        self.local_cache[key] = {
            "value": value,
            "expires": time.time() + min(ttl, self.local_ttl)
        }
        # L2
        self.redis.setex(key, ttl, json.dumps(value))
    
    def invalidate(self, pattern: str):
        """Invalidate cache entries by pattern."""
        # Clear L1
        self.local_cache = {
            k: v for k, v in self.local_cache.items()
            if not fnmatch.fnmatch(k, pattern)
        }
        # Clear L2
        for key in self.redis.scan_iter(match=pattern):
            self.redis.delete(key)

# Cache decorator
def cached(ttl: int = 300, key_prefix: str = ""):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Check cache
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_service.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Usage
@cached(ttl=300, key_prefix="vendors")
async def get_vendor(vendor_id: int) -> dict:
    return await db.query(Vendor).filter(Vendor.id == vendor_id).first()
```

### Cache Invalidation Patterns

```python
# src/services/invoice_service.py
class InvoiceService:
    async def update_invoice(self, invoice_id: int, data: dict):
        """Update invoice and invalidate related caches."""
        # Update database
        invoice = await self._update_invoice_db(invoice_id, data)
        
        # Invalidate specific invoice cache
        cache_service.invalidate(f"invoice:{invoice_id}:*")
        
        # Invalidate list caches
        cache_service.invalidate(f"invoices:list:*")
        
        # Invalidate vendor-specific caches
        cache_service.invalidate(f"vendor:{invoice.vendor_id}:invoices:*")
        
        # Invalidate dashboard caches
        cache_service.invalidate("dashboard:*")
        
        return invoice
```

---

## Database Optimization

### Connection Pooling

```python
# src/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,           # Base connections
    max_overflow=30,        # Additional connections under load
    pool_timeout=30,        # Wait time for connection
    pool_recycle=1800,      # Recycle connections every 30 min
    pool_pre_ping=True,     # Verify connection before use
)

# Async engine with asyncpg
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=20,
    max_overflow=30,
)
```

### Read Replicas

```python
# src/core/database.py
class DatabaseRouter:
    """Route queries to appropriate database."""
    
    def __init__(self):
        self.primary = create_engine(settings.DATABASE_PRIMARY_URL)
        self.replicas = [
            create_engine(url) for url in settings.DATABASE_REPLICA_URLS
        ]
        self._replica_index = 0
    
    def get_session(self, read_only: bool = False) -> Session:
        """Get database session (primary or replica)."""
        if read_only and self.replicas:
            # Round-robin replica selection
            engine = self.replicas[self._replica_index]
            self._replica_index = (self._replica_index + 1) % len(self.replicas)
        else:
            engine = self.primary
        
        return Session(bind=engine)

# Usage
@router.get("/invoices")
async def list_invoices(db: Session = Depends(get_read_db)):
    """List uses read replica."""
    return await invoice_service.list_invoices(db)

@router.post("/invoices")
async def create_invoice(db: Session = Depends(get_write_db)):
    """Create uses primary."""
    return await invoice_service.create_invoice(db)
```

### Query Optimization

```python
# src/repositories/invoice_repository.py
class InvoiceRepository:
    async def get_invoice_with_details(self, invoice_id: int) -> Invoice:
        """Optimized query with eager loading."""
        return await self.db.query(Invoice)\
            .options(
                joinedload(Invoice.vendor),
                joinedload(Invoice.line_items),
                joinedload(Invoice.approvals).joinedload(Approval.approver),
                selectinload(Invoice.attachments)
            )\
            .filter(Invoice.id == invoice_id)\
            .first()
    
    async def get_invoices_paginated(
        self,
        filters: dict,
        page: int = 1,
        limit: int = 20
    ) -> tuple[list[Invoice], int]:
        """Optimized paginated query."""
        # Base query with filters
        query = self.db.query(Invoice)
        
        # Apply filters
        if filters.get("status"):
            query = query.filter(Invoice.status == filters["status"])
        if filters.get("vendor_id"):
            query = query.filter(Invoice.vendor_id == filters["vendor_id"])
        if filters.get("date_from"):
            query = query.filter(Invoice.created_at >= filters["date_from"])
        
        # Get total count (separate query for efficiency)
        total = await query.count()
        
        # Get paginated results with eager loading
        invoices = await query\
            .options(joinedload(Invoice.vendor))\
            .order_by(Invoice.created_at.desc())\
            .offset((page - 1) * limit)\
            .limit(limit)\
            .all()
        
        return invoices, total
```

### Partitioning Strategy

```sql
-- Partition invoices by month for efficient archival
CREATE TABLE invoices (
    id SERIAL,
    invoice_number VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    -- ... other columns
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE invoices_2026_01 PARTITION OF invoices
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
    
CREATE TABLE invoices_2026_02 PARTITION OF invoices
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

-- Automated partition management
CREATE OR REPLACE FUNCTION create_invoice_partition()
RETURNS VOID AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
BEGIN
    partition_date := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    partition_name := 'invoices_' || TO_CHAR(partition_date, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF invoices
         FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        partition_date,
        partition_date + INTERVAL '1 month'
    );
END;
$$ LANGUAGE plpgsql;
```

---

## Async Processing

### Task Queue Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Async Processing Pipeline                        │
└─────────────────────────────────────────────────────────────────────┘

    API Request                 Background Tasks              Results
         │                            │                          │
         ▼                            │                          │
┌─────────────────┐                   │                          │
│  Upload Invoice │                   │                          │
│  POST /invoices │                   │                          │
└────────┬────────┘                   │                          │
         │                            │                          │
         │ Enqueue                    │                          │
         ▼                            │                          │
┌─────────────────┐                   │                          │
│  Message Queue  │◄──────────────────┤                          │
│  (RabbitMQ)     │                   │                          │
└────────┬────────┘                   │                          │
         │                            │                          │
    ┌────┴─────────────┬──────────────┴───────────┐              │
    │                  │                          │              │
    ▼                  ▼                          ▼              │
┌────────┐       ┌────────────┐           ┌────────────┐         │
│Extract │──────►│  Validate  │──────────►│   Match    │──────►  │
│ Agent  │       │   Agent    │           │   Agent    │         │
└────────┘       └────────────┘           └────────────┘         │
                                                                  │
                                                                  ▼
                                                         ┌──────────────┐
                                                         │   Database   │
                                                         │   Update     │
                                                         └──────────────┘
                                                                  │
                                                                  ▼
                                                         ┌──────────────┐
                                                         │   Webhook    │
                                                         │   Notify     │
                                                         └──────────────┘
```

### Celery Task Configuration

```python
# src/worker/celery_config.py
from celery import Celery

celery_app = Celery(
    "smartap",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Task routing
    task_routes={
        "extract_invoice": {"queue": "extraction"},
        "validate_invoice": {"queue": "validation"},
        "match_invoice": {"queue": "matching"},
        "fraud_check": {"queue": "fraud"},
        "send_notification": {"queue": "notifications"},
    },
    
    # Concurrency settings
    worker_concurrency=4,
    worker_prefetch_multiplier=2,
    
    # Task settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 min soft limit
    
    # Result settings
    result_expires=86400,  # 24 hours
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
)
```

### Task Prioritization

```python
# src/worker/tasks/invoice_tasks.py
from celery import Task

class InvoiceTask(Task):
    """Base task with retry and error handling."""
    
    autoretry_for = (ConnectionError, TimeoutError)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

@celery_app.task(
    base=InvoiceTask,
    bind=True,
    queue="extraction",
    priority=5  # Medium priority
)
def extract_invoice(self, invoice_id: int):
    """Extract data from invoice PDF."""
    try:
        invoice = get_invoice(invoice_id)
        result = extraction_agent.process(invoice.pdf_path)
        
        update_invoice(invoice_id, {
            "extracted_data": result,
            "status": "extracted"
        })
        
        # Chain to next task
        validate_invoice.delay(invoice_id)
        
    except SoftTimeLimitExceeded:
        update_invoice(invoice_id, {"status": "extraction_timeout"})
        raise

@celery_app.task(
    base=InvoiceTask,
    bind=True,
    queue="extraction",
    priority=9  # High priority for reprocessing
)
def reprocess_invoice(self, invoice_id: int):
    """Reprocess a failed invoice with higher priority."""
    ...
```

---

## Monitoring & Observability

### Metrics Collection

```python
# src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    "smartap_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "smartap_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Business metrics
INVOICES_PROCESSED = Counter(
    "smartap_invoices_processed_total",
    "Total invoices processed",
    ["status"]
)

PROCESSING_TIME = Histogram(
    "smartap_invoice_processing_seconds",
    "Invoice processing time",
    ["stage"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

# System metrics
ACTIVE_CONNECTIONS = Gauge(
    "smartap_db_connections_active",
    "Active database connections"
)

QUEUE_SIZE = Gauge(
    "smartap_queue_size",
    "Number of tasks in queue",
    ["queue_name"]
)
```

### Distributed Tracing

```python
# src/core/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Usage in code
@tracer.start_as_current_span("process_invoice")
async def process_invoice(invoice_id: int):
    span = trace.get_current_span()
    span.set_attribute("invoice.id", invoice_id)
    
    with tracer.start_as_current_span("extract"):
        result = await extract_invoice(invoice_id)
    
    with tracer.start_as_current_span("validate"):
        await validate_invoice(invoice_id, result)
    
    span.set_attribute("invoice.status", "processed")
```

### Health Checks

```python
# src/api/health.py
from fastapi import APIRouter
from datetime import datetime

health_router = APIRouter()

@health_router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@health_router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check for all dependencies."""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "rabbitmq": await check_rabbitmq(),
        "storage": await check_storage(),
    }
    
    overall_status = "healthy" if all(
        c["status"] == "healthy" for c in checks.values()
    ) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow(),
        "checks": checks,
        "version": settings.APP_VERSION,
    }

async def check_database() -> dict:
    """Check database connectivity."""
    try:
        await db.execute("SELECT 1")
        return {"status": "healthy", "latency_ms": 5}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## Performance Benchmarks

### Target Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (p50) | < 100ms | Prometheus |
| API Response Time (p99) | < 500ms | Prometheus |
| Invoice Processing Time | < 30s | End-to-end |
| Concurrent Users | 1,000+ | Load test |
| Requests/Second | 500+ | Load test |
| Database Queries/Second | 5,000+ | pgBench |
| Cache Hit Rate | > 90% | Redis metrics |
| Worker Throughput | 100 invoices/min | Celery metrics |

### Load Testing Script

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class SmartAPUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login on start."""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "load_test@example.com",
            "password": "testpassword123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(5)
    def list_invoices(self):
        """List invoices - most common operation."""
        self.client.get(
            "/api/v1/invoices?page=1&limit=20",
            headers=self.headers
        )
    
    @task(3)
    def get_invoice(self):
        """Get single invoice."""
        self.client.get(
            "/api/v1/invoices/1",
            headers=self.headers
        )
    
    @task(1)
    def create_invoice(self):
        """Create invoice - less frequent."""
        self.client.post(
            "/api/v1/invoices",
            headers=self.headers,
            json={"vendor_id": 1, "total": 1000.00}
        )
    
    @task(2)
    def dashboard(self):
        """Dashboard - common operation."""
        self.client.get(
            "/api/v1/reports/dashboard",
            headers=self.headers
        )

# Run: locust -f locustfile.py --host=http://localhost:8000
```

---

## Capacity Planning

### Sizing Guidelines

| Scale | Users | Invoices/Day | API Pods | Workers | Database | Redis |
|-------|-------|--------------|----------|---------|----------|-------|
| Small | 1-50 | 100 | 2 | 2 | 2 vCPU, 8GB | 2GB |
| Medium | 50-200 | 1,000 | 4 | 4 | 4 vCPU, 16GB | 8GB |
| Large | 200-1000 | 10,000 | 8 | 10 | 8 vCPU, 32GB | 16GB |
| Enterprise | 1000+ | 100,000+ | 20+ | 30+ | 16+ vCPU, 64GB+ | 32GB+ |

### Resource Estimation Formula

```python
# Capacity planning calculations
def estimate_resources(daily_invoices: int, concurrent_users: int):
    """Estimate required resources."""
    
    # API pods: 1 pod per 100 concurrent users
    api_pods = max(2, (concurrent_users // 100) + 1)
    
    # Workers: 1 worker per 100 invoices/hour peak
    peak_hourly = daily_invoices * 0.2  # 20% peak hour
    workers = max(2, int(peak_hourly / 100) + 1)
    
    # Database: Based on daily volume
    if daily_invoices < 1000:
        db_tier = "2 vCPU, 8GB"
    elif daily_invoices < 10000:
        db_tier = "4 vCPU, 16GB"
    else:
        db_tier = "8+ vCPU, 32GB+"
    
    # Storage: ~5MB per invoice (PDF + metadata)
    monthly_storage_gb = (daily_invoices * 30 * 5) / 1024
    
    return {
        "api_pods": api_pods,
        "workers": workers,
        "database": db_tier,
        "storage_gb": monthly_storage_gb
    }
```

### Growth Planning

```markdown
## Quarterly Capacity Review Checklist

### Metrics to Review
- [ ] Average daily invoice volume (trend)
- [ ] Peak hour invoice volume
- [ ] API response time trends
- [ ] Database connection utilization
- [ ] Cache hit rate
- [ ] Worker queue depth
- [ ] Storage consumption rate

### Scaling Triggers
- API p99 latency > 500ms consistently → Add API pods
- Worker queue > 1000 tasks → Add workers
- DB connections > 80% → Increase pool or upgrade
- Cache hit rate < 80% → Review caching strategy
- Storage > 80% capacity → Expand storage

### Planned Actions
- [ ] Document current capacity
- [ ] Project 3-month growth
- [ ] Schedule scaling changes
- [ ] Update cost projections
```

---

## Related Documentation

- **[Section 2: System Diagram](./02_System_Diagram.md)** - Architecture overview
- **[Section 3: Component Details](./03_Component_Details.md)** - Component specifications
- **[Section 7: Security Architecture](./07_Security_Architecture.md)** - Security at scale
- **[Deployment Guide](../Deployment_Guide.md)** - Production deployment

---

*Back to [Architecture Overview](../Architecture.md)*
