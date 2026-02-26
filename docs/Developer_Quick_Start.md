# SmartAP Developer Quick Start Guide

**Technical guide for developers setting up the SmartAP development environment.**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Summary](#architecture-summary)
3. [Development Environment Setup](#development-environment-setup)
4. [Running Locally](#running-locally)
5. [Project Structure](#project-structure)
6. [Backend Development](#backend-development)
7. [Frontend Development](#frontend-development)
8. [Database Management](#database-management)
9. [Testing](#testing)
10. [Common Development Tasks](#common-development-tasks)
11. [Debugging](#debugging)
12. [Contributing](#contributing)

---

## Overview

SmartAP is an AI-powered accounts payable automation platform built with:

| Component | Technology | Version |
|-----------|------------|---------|
| **Backend** | FastAPI (Python) | 3.12+ |
| **Frontend** | Next.js (React) | 16.x |
| **Database** | PostgreSQL | 15+ |
| **Cache** | Redis | 7+ |
| **AI/ML** | Azure AI Agent Framework, LangGraph | Latest |
| **PDF Processing** | Foxit PDF SDK | 10.x |

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 16)                    │
│    React 19 │ TanStack Query │ Tailwind CSS │ Zustand      │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (port 3000 → 8000)
┌──────────────────────────┴──────────────────────────────────┐
│                    Backend (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Routes    │  │  Services   │  │   AI Agents         │ │
│  │  /api/*     │  │  Business   │  │  - Extraction       │ │
│  │  /auth/*    │  │   Logic     │  │  - PO Matching      │ │
│  │  /esign/*   │  │             │  │  - Risk Detection   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼───┐ ┌─────▼─────┐
       │ PostgreSQL  │ │ Redis │ │ Foxit PDF │
       │   (5432)    │ │(6379) │ │  Service  │
       └─────────────┘ └───────┘ └───────────┘
```

---

## Development Environment Setup

### Prerequisites

```bash
# Required
- Docker Desktop 20.10+
- Git 2.30+
- Node.js 20+ (for frontend development)
- Python 3.12+ (for backend development)

# Recommended
- VS Code with extensions:
  - Python
  - Pylance
  - ESLint
  - Tailwind CSS IntelliSense
  - Docker
```

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/SmartAP.git
cd SmartAP
```

### Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env
```

**Key environment variables for development:**

```bash
# .env file
# Database
POSTGRES_PASSWORD=smartap_dev_password

# AI Provider (choose one)
AI_PROVIDER=github
GITHUB_TOKEN=your_github_pat_token
MODEL_ID=openai/gpt-4.1

# Debug mode
DEBUG=true

# Optional: Foxit SDK (for PDF features)
FOXIT_API_KEY=your_foxit_key
```

### Step 3: Start Services with Docker

```bash
# Start all services (recommended for development)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Services started:**
| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js web application |
| Backend | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache & Queue |

---

## Running Locally

### Option A: Full Docker Stack (Recommended)

```bash
# Build and start all services
docker-compose up -d --build

# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Option B: Hybrid Development (Backend Local)

```bash
# Start infrastructure only
docker-compose up -d db redis

# Set up Python environment
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt --pre

# Run backend locally
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Option C: Hybrid Development (Frontend Local)

```bash
# Start backend services
docker-compose up -d db redis backend

# Run frontend locally
cd frontend
npm install
npm run dev
```

### Option D: Full Local Development (No Docker)

Run everything locally without Docker. Requires local PostgreSQL and Redis installations.

#### Prerequisites for Local Development

**Windows:**
```powershell
# Install PostgreSQL (using winget or download from postgresql.org)
winget install PostgreSQL.PostgreSQL

# Install Redis (Windows build or use WSL)
# Option 1: Use Memurai (Redis-compatible for Windows)
winget install Memurai.MemuraiDeveloper

# Option 2: Use WSL
wsl --install
# Then in WSL: sudo apt install redis-server

# Verify installations
psql --version
redis-cli --version  # or memurai-cli --version
```

**macOS:**
```bash
# Install with Homebrew
brew install postgresql@15
brew install redis

# Start services
brew services start postgresql@15
brew services start redis

# Verify
psql --version
redis-cli --version
```

**Linux (Ubuntu/Debian):**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install Redis
sudo apt install redis-server

# Start services
sudo systemctl start postgresql
sudo systemctl start redis-server

# Verify
psql --version
redis-cli --version
```

#### Step 1: Set Up PostgreSQL Database

```bash
# Connect to PostgreSQL as superuser
# Windows: use pgAdmin or psql from Start Menu
# macOS/Linux:
sudo -u postgres psql

# Create database and user
CREATE USER smartap WITH PASSWORD 'smartap_dev_password';
CREATE DATABASE smartap OWNER smartap;
GRANT ALL PRIVILEGES ON DATABASE smartap TO smartap;
\q
```

#### Step 2: Verify Redis is Running

```bash
# Test Redis connection
redis-cli ping
# Should return: PONG
```

#### Step 3: Set Up Backend (Python venv)

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
.\venv\Scripts\activate.bat

# macOS/Linux:
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies (--pre flag for preview packages)
pip install -r requirements.txt --pre

# Verify installation
pip list | Select-String "fastapi|sqlalchemy|redis"
```

#### Step 4: Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# backend/.env

# Database - Local PostgreSQL
DATABASE_URL=postgresql+asyncpg://smartap:smartap_dev_password@localhost:5432/smartap
DATABASE_POOL_SIZE=5
DATABASE_POOL_MAX_OVERFLOW=10

# Redis - Local Redis
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# AI Provider Configuration
AI_PROVIDER=github
GITHUB_TOKEN=your_github_personal_access_token
MODEL_ID=openai/gpt-4.1
MODEL_BASE_URL=https://models.github.ai/inference

# Alternative: OpenAI direct
# AI_PROVIDER=openai
# OPENAI_API_KEY=your_openai_api_key

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# File paths (relative to backend directory)
UPLOAD_DIR=./uploads
PROCESSED_DIR=./processed
SIGNED_DIR=./signed

# Approval thresholds
APPROVAL_LEVEL1_MAX=100000
APPROVAL_LEVEL2_MAX=500000
APPROVAL_ESIGN_THRESHOLD=500000

# Optional: Foxit PDF SDK
# FOXIT_API_KEY=your_foxit_key
# FOXIT_API_ENDPOINT=https://api.foxitcloud.com

# Optional: ERP Integration (disable for local dev)
ERP_SYNC_ENABLED=false
```

#### Step 5: Initialize Database

```bash
# Make sure venv is activated and you're in backend directory
cd backend

# Run database migrations
alembic upgrade head

# The application will auto-seed demo data on first run in DEBUG mode
```

#### Step 6: Run Backend Server

```bash
# From backend directory with venv activated
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# You should see:
# [START] SmartAP v1.0.0 starting...
# [DIR] Upload directory: ./uploads
# [AI] AI Provider: github
# Uvicorn running on http://0.0.0.0:8000
```

**Verify backend is running:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

#### Step 7: Set Up Frontend (Node.js)

Open a **new terminal** (keep backend running):

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create/verify environment file
# frontend/.env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

#### Step 8: Run Frontend Development Server

```bash
# From frontend directory
npm run dev

# You should see:
# ▲ Next.js 16.x.x
# - Local: http://localhost:3000
# ✓ Ready
```

**Verify frontend is running:**
- Application: http://localhost:3000
- Should connect to backend at :8000

#### Complete Local Setup Checklist

| Component | Command to Verify | Expected Result |
|-----------|------------------|-----------------|
| PostgreSQL | `psql -U smartap -d smartap -c "SELECT 1"` | Returns "1" |
| Redis | `redis-cli ping` | Returns "PONG" |
| Backend | `curl http://localhost:8000/health` | Returns health JSON |
| Frontend | Open http://localhost:3000 | Dashboard loads |

#### Stopping Local Services

```bash
# Stop backend (Ctrl+C in terminal)

# Stop frontend (Ctrl+C in terminal)

# Deactivate Python venv
deactivate

# Stop PostgreSQL (if needed)
# Windows: Stop from Services or pg_ctl stop
# macOS: brew services stop postgresql@15
# Linux: sudo systemctl stop postgresql

# Stop Redis (if needed)
# Windows: Stop Memurai service
# macOS: brew services stop redis
# Linux: sudo systemctl stop redis-server
```

#### Troubleshooting Local Setup

| Issue | Solution |
|-------|----------|
| `psql: connection refused` | Start PostgreSQL service |
| `redis.exceptions.ConnectionError` | Start Redis service |
| `ModuleNotFoundError` | Activate venv: `.\venv\Scripts\Activate.ps1` |
| `alembic: Target database is not up to date` | Run `alembic upgrade head` |
| `CORS error in browser` | Backend must be running on :8000 |
| `Cannot connect to API` | Check `NEXT_PUBLIC_API_URL` in frontend/.env.local |
| Port already in use | Kill process: `npx kill-port 8000` or `npx kill-port 3000` |

---

## Project Structure

```
SmartAP/
├── backend/
│   ├── src/
│   │   ├── agents/              # AI agents
│   │   │   ├── extraction_agent.py
│   │   │   ├── po_matching_agent.py
│   │   │   └── risk_detection_agent.py
│   │   ├── api/                 # API routes
│   │   │   ├── routes.py        # Invoice endpoints
│   │   │   ├── approval_routes.py
│   │   │   ├── dashboard_routes.py
│   │   │   ├── erp_routes.py
│   │   │   └── esign_routes.py
│   │   ├── db/                  # Database layer
│   │   │   ├── database.py      # Connection setup
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   ├── repositories.py  # Data access
│   │   │   └── seed_data.py     # Demo data
│   │   ├── services/            # Business logic
│   │   ├── integrations/        # ERP connectors
│   │   ├── middleware/          # Logging, auth
│   │   ├── config.py            # Settings
│   │   └── main.py              # FastAPI app
│   ├── tests/                   # Test suites
│   ├── alembic/                 # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   │   ├── dashboard/
│   │   │   ├── invoices/
│   │   │   ├── approvals/
│   │   │   ├── vendors/
│   │   │   └── layout.tsx
│   │   ├── components/          # React components
│   │   │   ├── ui/              # Shadcn/ui components
│   │   │   ├── layout/
│   │   │   └── invoices/
│   │   ├── lib/                 # Utilities
│   │   │   └── api/             # API client & hooks
│   │   ├── stores/              # Zustand state
│   │   └── types/               # TypeScript types
│   ├── package.json
│   └── Dockerfile
│
├── docs/                        # Documentation
├── e2e/                         # Playwright E2E tests
├── k8s/                         # Kubernetes manifests
├── helm/                        # Helm charts
└── docker-compose.yml
```

---

## Backend Development

### API Structure

```python
# backend/src/api/routes.py - Example endpoint structure

@router.post("/invoices/upload")
async def upload_invoice(
    file: UploadFile,
    session: AsyncSession = Depends(get_db_session),
):
    """Upload and process a new invoice."""
    # 1. Save file
    # 2. Extract data with AI agent
    # 3. Store in database
    # 4. Return processed invoice
```

### Adding a New API Endpoint

1. **Create route in `backend/src/api/`:**

```python
# backend/src/api/my_routes.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.get("/items")
async def get_items():
    return {"items": []}
```

2. **Register in `__init__.py`:**

```python
# backend/src/api/__init__.py
from .my_routes import router as my_router
```

3. **Add to main app:**

```python
# backend/src/main.py
app.include_router(my_router)
```

### Working with AI Agents

```python
# Example: Using the extraction agent
from src.agents.extraction_agent import ExtractionAgent

agent = ExtractionAgent()
result = await agent.extract(pdf_content)

# Result contains:
# - invoice_number, vendor_name, total_amount
# - line_items, tax_amount, due_date
# - confidence_scores for each field
```

### Database Operations

```python
# Using repositories (recommended)
from src.db.repositories import InvoiceRepository

repo = InvoiceRepository(session)
invoices = await repo.get_all(skip=0, limit=20)
invoice = await repo.get_by_id(invoice_id)
await repo.update(invoice_id, {"status": "approved"})
```

---

## Frontend Development

### Tech Stack

- **Next.js 16** with App Router
- **React 19** with Server Components
- **TanStack Query** for data fetching
- **Zustand** for client state
- **Tailwind CSS 4** + **shadcn/ui** components
- **TypeScript 5** strict mode

### Component Structure

```tsx
// frontend/src/app/invoices/page.tsx
'use client';

import { useInvoices } from '@/lib/api/invoices';
import { InvoiceList } from '@/components/invoices/invoice-list';

export default function InvoicesPage() {
  const { data, isLoading } = useInvoices();
  
  if (isLoading) return <Loading />;
  
  return <InvoiceList invoices={data} />;
}
```

### API Integration

```typescript
// frontend/src/lib/api/invoices.ts
import { useQuery, useMutation } from '@tanstack/react-query';
import apiClient from './client';

export const useInvoices = () => {
  return useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const { data } = await apiClient.get('/invoices');
      return data;
    },
  });
};

export const useUploadInvoice = () => {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return apiClient.post('/invoices/upload', formData);
    },
  });
};
```

### Adding New UI Components

```bash
# Using shadcn/ui CLI
cd frontend
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add dialog
```

---

## Database Management

### Running Migrations

```bash
# Generate new migration
cd backend
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Database Schema

```sql
-- Key tables
invoices          -- Invoice records
vendors           -- Vendor master
purchase_orders   -- PO records
line_items        -- Invoice line items
approval_history  -- Approval audit trail
users             -- User accounts
```

### Direct Database Access

```bash
# Connect to PostgreSQL in Docker
docker exec -it smartap-db psql -U smartap -d smartap

# Common queries
\dt                          -- List tables
SELECT * FROM invoices LIMIT 5;
SELECT * FROM vendors;
```

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api_e2e.py

# Run specific test
pytest tests/test_api_e2e.py::test_upload_invoice -v

# Run by marker
pytest -m "unit"
pytest -m "integration"
```

### Frontend Tests

```bash
cd frontend

# Run linting
npm run lint

# Type checking
npx tsc --noEmit
```

### E2E Tests (Playwright)

```bash
cd e2e

# Install browsers
npx playwright install

# Run E2E tests
npx playwright test

# Run with UI
npx playwright test --ui

# Run specific test
npx playwright test tests/invoice-upload.spec.ts
```

---

## Common Development Tasks

### Rebuild After Code Changes

```bash
# Backend changes
docker-compose build backend
docker-compose up -d backend

# Frontend changes
docker-compose build frontend
docker-compose up -d frontend

# Both
docker-compose up -d --build
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Reset Database

```bash
# Stop services and remove volumes
docker-compose down -v

# Restart (will recreate and seed database)
docker-compose up -d
```

### Clear Redis Cache

```bash
docker exec -it smartap-redis redis-cli FLUSHALL
```

### Run Backend Shell

```bash
# Interactive Python shell with app context
docker exec -it smartap-backend python -c "
from src.db.database import async_session_maker
from src.db.models import InvoiceDB
# Your code here
"
```

---

## Debugging

### Backend Debugging

1. **VS Code Launch Configuration:**

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Debug",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://smartap:smartap_dev_password@localhost:5432/smartap"
      }
    }
  ]
}
```

2. **Add breakpoints and use debugger**

### Frontend Debugging

1. **React DevTools** - Install browser extension
2. **TanStack Query DevTools** - Enabled in development (bottom-right corner)
3. **Next.js Debug Mode:**

```bash
NODE_OPTIONS='--inspect' npm run dev
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Database connection failed | Check if `smartap-db` container is running |
| Redis connection refused | Ensure `smartap-redis` is healthy |
| CORS errors | Backend must allow frontend origin |
| AI extraction fails | Verify `GITHUB_TOKEN` or API keys are set |
| Frontend hydration errors | Check for SSR/client component mismatch |

---

## Contributing

### Branch Naming

```
feature/add-vendor-portal
bugfix/fix-invoice-upload
hotfix/security-patch
docs/update-readme
```

### Commit Messages

```
feat: add vendor management API
fix: resolve PDF parsing error for scanned invoices
docs: update API reference
test: add integration tests for approval workflow
refactor: optimize database queries
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Ensure all tests pass: `pytest` and `npm run lint`
4. Update documentation if needed
5. Submit PR with description
6. Address review feedback
7. Merge after approval

### Code Style

**Python (Backend):**
- Follow PEP 8
- Use type hints
- Async/await for I/O operations
- Docstrings for public functions

**TypeScript (Frontend):**
- Strict TypeScript
- Functional components with hooks
- Named exports preferred
- Use `@/` path aliases

---

## Quick Reference

### URLs (Development)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

### Common Commands

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f [service]

# Rebuild service
docker-compose build [service]

# Run tests
cd backend && pytest
cd frontend && npm run lint

# Database shell
docker exec -it smartap-db psql -U smartap -d smartap
```

### Default Credentials (Development)

| Service | Username | Password | Role |
|---------|----------|----------|------|
| Database | smartap | smartap_dev_password | — |
| Admin | admin@smartap.dev | Admin1234! | admin |
| Finance Manager | finance@smartap.dev | Finance1234! | finance_manager |
| Accountant | accountant@smartap.dev | Account1234! | accountant |
| Viewer | viewer@smartap.dev | Viewer1234! | viewer |

> Demo users are auto-created on first login attempt.

---

## Next Steps

- [API Reference](API_Reference.md) - Complete API documentation
- [Configuration Reference](Configuration_Reference.md) - All environment variables
- [Extensibility Guide](Extensibility_Guide.md) - Building custom agents
- [Deployment Guide](DEPLOYMENT.md) - Production deployment

---

*Last updated: January 2026*
