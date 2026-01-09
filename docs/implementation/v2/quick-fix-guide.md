# SmartAP V2 Quick Fix Guide

## Immediate Priority Fixes

This document provides step-by-step instructions to resolve the critical blockers identified in the V2 implementation plan.

**STATUS UPDATE (2026-01-08):**
- ✅ Fix 1.1.1: ExtractionAgent wrapper - COMPLETE
- ✅ Fix 1.1.2: Routes enabled - COMPLETE  
- ✅ Fix 1.1.3: Mock data replaced with real DB queries - COMPLETE

---

## Fix 1: Create ExtractionAgent Wrapper ✅ COMPLETE

**Problem:** `workflow_nodes.py` imports from non-existent `agents/extraction_agent.py`

**Solution:** Created wrapper file at `backend/src/agents/extraction_agent.py`

### Create File: `backend/src/agents/extraction_agent.py`

```python
"""
Extraction Agent Wrapper

This module provides backward compatibility for the orchestration layer
by re-exporting the InvoiceExtractionAgent from services.
"""

from ..services.extraction_agent import InvoiceExtractionAgent

# Alias for orchestration compatibility
class ExtractionAgent(InvoiceExtractionAgent):
    """
    Wrapper class for orchestration workflow compatibility.
    
    The actual implementation is in services/extraction_agent.py.
    This wrapper ensures the orchestration layer can import correctly.
    """
    pass

__all__ = ["ExtractionAgent", "InvoiceExtractionAgent"]
```

---

## Fix 2: Fix ERP Routes Database Import

**Problem:** `erp_routes.py` imports from wrong path

**Solution:** Update import statement

### Modify: `backend/src/api/erp_routes.py`

Change line 26:
```python
# FROM:
from ..database import get_db

# TO:
from ..db.database import get_session as get_db
```

---

## Fix 3: Enable Full API Routes

**Problem:** Full routes, eSign routes, and ERP routes are commented out

**Solution:** Update API router initialization

### Modify: `backend/src/api/__init__.py`

```python
"""
SmartAP API Module
"""

import logging

logger = logging.getLogger(__name__)

# Core routers (always enabled)
from .routes_simple import router as routes_simple
from .dashboard_routes import router as dashboard_router

# Auth router
try:
    from ..auth import router as auth_router
    HAS_AUTH = True
except ImportError as e:
    logger.warning(f"Auth router not available: {e}")
    HAS_AUTH = False
    auth_router = None

# Full routes with agent integration
try:
    from .routes import router as full_router
    HAS_FULL_ROUTES = True
except ImportError as e:
    logger.warning(f"Full routes not available: {e}")
    HAS_FULL_ROUTES = False
    full_router = None

# eSign routes
try:
    from .esign_routes import router as esign_router
    HAS_ESIGN = True
except ImportError as e:
    logger.warning(f"eSign routes not available: {e}")
    HAS_ESIGN = False
    esign_router = None

# ERP routes
try:
    from .erp_routes import router as erp_router
    HAS_ERP = True
except ImportError as e:
    logger.warning(f"ERP routes not available: {e}")
    HAS_ERP = False
    erp_router = None

__all__ = [
    "routes_simple",
    "dashboard_router",
    "auth_router",
    "full_router",
    "esign_router",
    "erp_router",
    "HAS_AUTH",
    "HAS_FULL_ROUTES",
    "HAS_ESIGN",
    "HAS_ERP",
]
```

Then update `backend/src/main.py` to conditionally include routers:

```python
from .api import (
    routes_simple, 
    dashboard_router, 
    auth_router,
    full_router,
    esign_router,
    erp_router,
    HAS_AUTH,
    HAS_FULL_ROUTES,
    HAS_ESIGN,
    HAS_ERP,
)

# Always include simple routes as fallback
app.include_router(routes_simple)
app.include_router(dashboard_router)

# Conditionally include advanced routers
if HAS_AUTH and auth_router:
    app.include_router(auth_router, prefix="/auth")

if HAS_FULL_ROUTES and full_router:
    app.include_router(full_router)

if HAS_ESIGN and esign_router:
    app.include_router(esign_router)

if HAS_ERP and erp_router:
    app.include_router(erp_router)
```

---

## Fix 4: Database-Backed Authentication

**Problem:** Users stored in-memory, lost on restart

**Solution:** Connect auth to database

### Modify: `backend/src/auth.py`

Add database integration:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .db.database import get_session
from .db.models import UserDB  # Need to create this model

# Replace in-memory storage with database operations
class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_by_email(self, email: str) -> Optional[UserDB]:
        result = await self.session.execute(
            select(UserDB).where(UserDB.email == email)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, email: str, full_name: str, hashed_password: str) -> UserDB:
        user = UserDB(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
        )
        self.session.add(user)
        await self.session.commit()
        return user
```

### Create User Model in `backend/src/db/models.py`:

```python
class UserDB(Base):
    """User database model."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(50), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now())
```

---

## Fix 5: Replace Mock Data Endpoints

**Problem:** Dashboard returns random mock data

**Solution:** Use real repository queries

### Example: Replace `/api/v1/invoices` endpoint

```python
# In dashboard_routes.py, replace:
@router.get("/invoices", summary="List invoices with pagination")
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),  # Add this dependency
):
    """List invoices from database."""
    from ..db.repositories import InvoiceRepository
    
    repo = InvoiceRepository(session)
    
    # Calculate offset
    offset = (page - 1) * limit
    
    # Get invoices from database
    invoices = await repo.get_all(limit=limit, offset=offset)
    total = await repo.count()
    
    return {
        "items": [inv.to_dict() for inv in invoices],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }
```

---

## Verification Steps

After applying fixes, verify with these commands:

### 1. Test Imports
```bash
cd backend
python -c "from src.api import full_router, esign_router, erp_router; print('All imports OK')"
```

### 2. Start Server
```bash
docker-compose up -d
docker logs smartap-backend --follow
```

### 3. Check Endpoints
```bash
# Test full routes loaded
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# Should include:
# /api/v1/invoices/upload
# /esign/*
# /erp/*
```

### 4. Test Database Connection
```bash
docker exec -it smartap-backend python -c "
from src.db.database import engine
import asyncio

async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Database connected:', result.scalar())

asyncio.run(test())
"
```

---

## Rollback Plan

If fixes cause issues, revert to working state:

```bash
# Restore simple routes only
git checkout backend/src/api/__init__.py

# Or restore entire api folder
git checkout backend/src/api/
```

---

## Next Steps After Fixes

1. Run database migrations
2. Seed demo data
3. Test invoice upload with real extraction
4. Enable eSign with Foxit credentials
5. Test ERP connector with sandbox account
