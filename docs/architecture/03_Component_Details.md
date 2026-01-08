# SmartAP Component Deep Dive

**Section 3 of Architecture Documentation**

---

## Table of Contents

1. [Frontend (Next.js)](#frontend-nextjs)
2. [Backend API (FastAPI)](#backend-api-fastapi)
3. [Task Workers (Celery)](#task-workers-celery)
4. [Task Scheduler (Celery Beat)](#task-scheduler-celery-beat)
5. [Database (PostgreSQL)](#database-postgresql)
6. [Cache & Queue (Redis)](#cache--queue-redis)
7. [PDF Processing (Foxit)](#pdf-processing-foxit)
8. [AI Services](#ai-services)

---

## Frontend (Next.js)

### Overview

The frontend is a modern React application built with Next.js 14, providing a responsive, accessible user interface for invoice management.

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.x | React framework with App Router |
| React | 18.x | UI component library |
| TypeScript | 5.3+ | Type-safe JavaScript |
| Tailwind CSS | 3.4+ | Utility-first CSS framework |
| React Query | 5.x | Server state management |
| React Hook Form | 7.x | Form handling |
| Zod | 3.x | Schema validation |
| Recharts | 2.x | Data visualization |

### Directory Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── (auth)/             # Authentication routes
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/        # Protected routes
│   │   ├── invoices/
│   │   ├── vendors/
│   │   ├── purchase-orders/
│   │   ├── approvals/
│   │   └── settings/
│   ├── api/                # API route handlers
│   ├── layout.tsx          # Root layout
│   └── page.tsx            # Home page
├── components/             # Reusable UI components
│   ├── ui/                 # Base UI components
│   ├── forms/              # Form components
│   ├── tables/             # Data table components
│   └── charts/             # Visualization components
├── hooks/                  # Custom React hooks
├── lib/                    # Utility functions
├── services/               # API client services
├── types/                  # TypeScript type definitions
└── styles/                 # Global styles
```

### Key Features

#### 1. Server-Side Rendering (SSR)
- Initial page loads are server-rendered for SEO and performance
- Client-side hydration for interactive components

#### 2. API Routes
- Proxy routes to backend API (`/api/proxy/*`)
- Auth callback handlers
- File upload preprocessing

#### 3. State Management
```typescript
// React Query for server state
const { data: invoices, isLoading } = useQuery({
  queryKey: ['invoices', filters],
  queryFn: () => invoiceService.list(filters),
});

// Context for client state
const { user, logout } = useAuth();
```

#### 4. Form Handling
```typescript
// React Hook Form + Zod validation
const schema = z.object({
  invoiceNumber: z.string().min(1, 'Required'),
  vendorId: z.number().positive('Select a vendor'),
  total: z.number().positive('Must be positive'),
});

const form = useForm<InvoiceForm>({
  resolver: zodResolver(schema),
});
```

### Configuration

```typescript
// next.config.js
module.exports = {
  reactStrictMode: true,
  images: {
    domains: ['localhost', 'api.smartap.example.com'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};
```

---

## Backend API (FastAPI)

### Overview

The backend is a high-performance async Python API built with FastAPI, handling authentication, business logic, and data access.

### Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.110+ | Web framework |
| Python | 3.12+ | Runtime |
| SQLAlchemy | 2.0+ | ORM |
| Alembic | 1.13+ | Database migrations |
| Pydantic | 2.x | Data validation |
| python-jose | 3.3+ | JWT handling |
| passlib | 1.7+ | Password hashing |

### Directory Structure

```
backend/
├── src/
│   ├── api/                # API route handlers
│   │   ├── v1/
│   │   │   ├── invoices.py
│   │   │   ├── vendors.py
│   │   │   ├── purchase_orders.py
│   │   │   ├── approvals.py
│   │   │   └── auth.py
│   │   └── deps.py         # Dependency injection
│   ├── agents/             # AI agent implementations
│   ├── core/               # Core configuration
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   ├── tasks/              # Celery tasks
│   └── main.py             # Application entry point
├── tests/                  # Test suite
├── alembic/                # Database migrations
└── requirements.txt        # Dependencies
```

### API Structure

```python
# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="SmartAP API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(invoices_router, prefix="/api/v1/invoices", tags=["invoices"])
app.include_router(vendors_router, prefix="/api/v1/vendors", tags=["vendors"])
app.include_router(pos_router, prefix="/api/v1/purchase-orders", tags=["purchase-orders"])
app.include_router(approvals_router, prefix="/api/v1/approvals", tags=["approvals"])
```

### Dependency Injection

```python
# src/api/deps.py
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await user_service.get(db, user_id)
    if user is None:
        raise credentials_exception
    return user
```

### Error Handling

```python
# src/core/exceptions.py
class SmartAPException(Exception):
    """Base exception for SmartAP."""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code

class InvoiceNotFoundError(SmartAPException):
    def __init__(self, invoice_id: int):
        super().__init__(f"Invoice {invoice_id} not found", "INVOICE_NOT_FOUND")

# Exception handler
@app.exception_handler(SmartAPException)
async def smartap_exception_handler(request: Request, exc: SmartAPException):
    return JSONResponse(
        status_code=400,
        content={"error": exc.code, "message": exc.message},
    )
```

---

## Task Workers (Celery)

### Overview

Celery workers handle CPU-intensive and time-consuming operations asynchronously, such as invoice extraction, PO matching, and notifications.

### Configuration

```python
# src/celery_app.py
from celery import Celery

celery_app = Celery(
    "smartap",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # Soft limit at 4 minutes
    worker_prefetch_multiplier=1,  # One task at a time per worker
    task_acks_late=True,  # Acknowledge after completion
)
```

### Task Definitions

```python
# src/tasks/invoice_tasks.py
from src.celery_app import celery_app
from src.services.extraction_service import ExtractionService
from src.agents.extractor_agent import ExtractorAgent

@celery_app.task(bind=True, max_retries=3)
def extract_invoice(self, invoice_id: int) -> dict:
    """Extract data from uploaded invoice PDF."""
    try:
        extraction_service = ExtractionService()
        extractor_agent = ExtractorAgent()
        
        # 1. Get PDF text via Foxit
        pdf_text = extraction_service.extract_text(invoice_id)
        
        # 2. Extract structured data via AI
        extracted_data = extractor_agent.extract(pdf_text)
        
        # 3. Save to database
        extraction_service.save_extracted_data(invoice_id, extracted_data)
        
        # 4. Queue next step
        validate_invoice.delay(invoice_id)
        
        return {"status": "success", "invoice_id": invoice_id}
        
    except Exception as exc:
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

@celery_app.task
def validate_invoice(invoice_id: int) -> dict:
    """Validate extracted invoice data."""
    # Auditor agent logic
    ...

@celery_app.task
def match_purchase_order(invoice_id: int) -> dict:
    """Match invoice with purchase orders."""
    # Matcher agent logic
    ...

@celery_app.task
def detect_fraud(invoice_id: int) -> dict:
    """Run fraud detection checks."""
    # Fraud agent logic
    ...

@celery_app.task
def send_notification(user_id: int, notification_type: str, data: dict) -> dict:
    """Send email/Slack notification."""
    ...
```

### Worker Scaling

```bash
# Start worker with concurrency
celery -A src.celery_app worker --loglevel=info --concurrency=4

# Start multiple workers for different queues
celery -A src.celery_app worker -Q extraction --concurrency=2
celery -A src.celery_app worker -Q matching --concurrency=4
celery -A src.celery_app worker -Q notifications --concurrency=1
```

---

## Task Scheduler (Celery Beat)

### Overview

Celery Beat schedules periodic tasks such as daily reports, invoice archival, and cleanup operations.

### Configuration

```python
# src/celery_app.py
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # Daily report at 6 AM
    "daily-invoice-report": {
        "task": "src.tasks.reports.generate_daily_report",
        "schedule": crontab(hour=6, minute=0),
    },
    # Archive old invoices weekly (Sunday 2 AM)
    "weekly-archive": {
        "task": "src.tasks.archival.archive_old_invoices",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
    },
    # Cleanup temp files every hour
    "hourly-cleanup": {
        "task": "src.tasks.cleanup.cleanup_temp_files",
        "schedule": crontab(minute=0),
    },
    # Sync ERP every 15 minutes
    "erp-sync": {
        "task": "src.tasks.erp.sync_all_erp",
        "schedule": crontab(minute="*/15"),
    },
}
```

### Running Beat

```bash
# Start Celery Beat scheduler
celery -A src.celery_app beat --loglevel=info

# Combined worker + beat (for development)
celery -A src.celery_app worker --beat --loglevel=info
```

---

## Database (PostgreSQL)

### Overview

PostgreSQL 16 serves as the primary data store, handling all transactional data with ACID compliance.

### Configuration

```python
# src/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=settings.DEBUG,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

### Connection Pooling

| Parameter | Development | Production |
|-----------|-------------|------------|
| pool_size | 5 | 20 |
| max_overflow | 5 | 10 |
| pool_timeout | 30s | 30s |
| pool_recycle | 1800s | 1800s |

### Indexes

Key indexes for performance:

```sql
-- Invoice lookups
CREATE INDEX idx_invoices_vendor_id ON invoices(vendor_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);

-- Approval queries
CREATE INDEX idx_approvals_invoice_id ON approvals(invoice_id);
CREATE INDEX idx_approvals_approver_id ON approvals(approver_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- Audit trail
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

---

## Cache & Queue (Redis)

### Overview

Redis 7 serves dual purposes: task queue backend for Celery and caching layer for API responses.

### Configuration

```python
# src/core/redis.py
import redis.asyncio as redis

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)

# Cache settings
CACHE_TTL = {
    "invoice_list": 60,       # 1 minute
    "vendor_list": 300,       # 5 minutes
    "user_session": 1800,     # 30 minutes
    "rate_limit": 60,         # 1 minute window
}
```

### Usage Patterns

#### 1. API Response Caching
```python
async def get_invoice_cached(invoice_id: int) -> dict:
    cache_key = f"invoice:{invoice_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    invoice = await invoice_service.get(invoice_id)
    await redis_client.setex(cache_key, 300, json.dumps(invoice))
    return invoice
```

#### 2. Rate Limiting
```python
async def check_rate_limit(user_id: int, limit: int = 100) -> bool:
    key = f"rate_limit:{user_id}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, 60)
    return current <= limit
```

#### 3. Session Storage
```python
async def store_session(session_id: str, user_data: dict) -> None:
    await redis_client.setex(
        f"session:{session_id}",
        1800,  # 30 minutes
        json.dumps(user_data),
    )
```

---

## PDF Processing (Foxit)

### Overview

Foxit PDF SDK provides enterprise-grade PDF parsing, text extraction, and OCR capabilities.

### Integration

```python
# src/services/foxit_service.py
from foxit_sdk import PDFDocument, OCREngine

class FoxitService:
    def __init__(self):
        self.api_key = settings.FOXIT_API_KEY
        self.ocr_engine = OCREngine(api_key=self.api_key)
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text from PDF, using OCR if needed."""
        doc = PDFDocument(pdf_path)
        
        # Try direct text extraction first
        text = doc.get_text()
        
        # If no text found, use OCR
        if not text.strip():
            text = self.ocr_engine.recognize(pdf_path)
        
        return text
    
    def extract_with_positions(self, pdf_path: str) -> list[dict]:
        """Extract text with bounding box positions."""
        doc = PDFDocument(pdf_path)
        blocks = []
        
        for page in doc.pages:
            for block in page.text_blocks:
                blocks.append({
                    "text": block.text,
                    "page": page.number,
                    "bbox": block.bounding_box,
                })
        
        return blocks
```

### Features Used

| Feature | Purpose |
|---------|---------|
| Text Extraction | Extract text from digital PDFs |
| OCR Engine | Recognize text in scanned/image PDFs |
| Layout Analysis | Understand document structure (tables, headers) |
| Annotation Reading | Extract stamps, handwritten notes |

---

## AI Services

### Overview

AI services power the intelligent extraction and reasoning capabilities of SmartAP.

### Provider Abstraction

```python
# src/services/ai_service.py
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        pass

class GitHubModelsProvider(AIProvider):
    async def complete(self, prompt: str, **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=settings.GITHUB_MODEL,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content

class OpenAIProvider(AIProvider):
    async def complete(self, prompt: str, **kwargs) -> str:
        response = await openai.ChatCompletion.acreate(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.choices[0].message.content

class AnthropicProvider(AIProvider):
    async def complete(self, prompt: str, **kwargs) -> str:
        response = await self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return response.content[0].text

# Factory function
def get_ai_provider() -> AIProvider:
    provider = settings.AI_PROVIDER.lower()
    if provider == "github":
        return GitHubModelsProvider()
    elif provider == "openai":
        return OpenAIProvider()
    elif provider == "anthropic":
        return AnthropicProvider()
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
```

### Token Management

```python
# Estimated costs per invoice
COST_ESTIMATES = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},      # per 1K tokens
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
}

# Average tokens per invoice
AVERAGE_TOKENS = {
    "input": 2000,   # PDF text + prompt
    "output": 500,   # Extracted JSON
}

# Cost per invoice ≈ $0.01-0.02 with GPT-4o
```

---

## Related Documentation

- **[Section 1: Overview & Design Principles](./Architecture.md)** - Foundation and technology choices
- **[Section 2: High-Level System Diagram](./02_System_Diagram.md)** - System diagrams
- **[Section 4: Agent Orchestration](./04_Agent_Orchestration.md)** - AI agent pipeline details
- **[Extensibility Guide](./Extensibility_Guide.md)** - Building custom agents

---

*Continue to [Section 4: Agent Orchestration Flow](./04_Agent_Orchestration.md)*
