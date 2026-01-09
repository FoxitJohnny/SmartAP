# SmartAP Configuration Reference

This document provides a comprehensive reference for all SmartAP configuration options.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Configuration Categories](#configuration-categories)
  - [Application](#application)
  - [Security & CORS](#security--cors)
  - [AI & Model](#ai--model)
  - [OCR Services](#ocr-services)
  - [eSign Integration](#esign-integration)
  - [Approval Workflow](#approval-workflow)
  - [Archival](#archival)
  - [Database](#database)
  - [Redis Cache](#redis-cache)
  - [Storage](#storage)
  - [ERP Integrations](#erp-integrations)
  - [Logging](#logging)
- [Example Configurations](#example-configurations)

---

## Environment Variables

All configuration is managed through environment variables, which can be set in a `.env` file or directly in your deployment environment.

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

---

## Configuration Categories

### Application

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | string | `SmartAP` | Application name |
| `APP_VERSION` | string | `0.1.0` | Application version |
| `DEBUG` | bool | `false` | Enable debug mode (development only) |
| `API_HOST` | string | `0.0.0.0` | API server host |
| `API_PORT` | int | `8000` | API server port |

### Security & CORS

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CORS_ORIGINS` | string | `http://localhost:3000,http://localhost:8000` | Comma-separated allowed origins. Use `*` for dev only. |
| `CORS_ALLOW_CREDENTIALS` | bool | `true` | Allow credentials in CORS requests |
| `CORS_ALLOW_METHODS` | string | `GET,POST,PUT,DELETE,PATCH,OPTIONS` | Comma-separated allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | string | `*` | Comma-separated allowed headers |

**Security Best Practices:**
- Never use `CORS_ORIGINS=*` in production
- Specify exact frontend domains: `https://app.yourcompany.com`
- Use HTTPS for all origins in production

### AI & Model

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_PROVIDER` | string | `github` | AI provider: `github`, `openai`, or `azure` |
| `GITHUB_TOKEN` | string | - | GitHub Personal Access Token for GitHub Models |
| `OPENAI_API_KEY` | string | - | OpenAI API key (if using OpenAI provider) |
| `MODEL_ID` | string | `openai/gpt-4.1` | Model ID for AI extraction |
| `MODEL_BASE_URL` | string | `https://models.github.ai/inference` | Model API base URL |
| `EXTRACTION_CONFIDENCE_THRESHOLD` | float | `0.85` | Minimum confidence for auto-approval (0.0-1.0) |
| `MAX_FILE_SIZE_MB` | int | `50` | Maximum upload file size in MB |

**Provider Configuration:**

```bash
# GitHub Models (recommended for development)
AI_PROVIDER=github
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
MODEL_ID=openai/gpt-4.1

# OpenAI Direct
AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxx
MODEL_ID=gpt-4-turbo

# Azure OpenAI
AI_PROVIDER=azure
AZURE_OPENAI_API_KEY=xxxxxxxxxxxx
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
MODEL_ID=gpt-4
```

### OCR Services

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FOXIT_API_KEY` | string | - | Foxit API key for OCR services |
| `FOXIT_API_ENDPOINT` | string | - | Foxit API endpoint URL |

**Note:** If Foxit credentials are not provided, the system falls back to local pytesseract OCR.

### eSign Integration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FOXIT_ESIGN_API_KEY` | string | - | Foxit eSign API key |
| `FOXIT_ESIGN_API_SECRET` | string | - | Foxit eSign API secret |
| `FOXIT_ESIGN_BASE_URL` | string | `https://api.foxitsign.com/v2.0` | Foxit eSign API base URL |
| `FOXIT_ESIGN_WEBHOOK_SECRET` | string | - | Webhook signature verification secret |
| `FOXIT_ESIGN_CALLBACK_URL` | string | - | Webhook callback URL for signature events |
| `SIGNED_DIR` | string | `./signed` | Directory for signed documents |

### Approval Workflow

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APPROVAL_LEVEL1_MAX` | int | `100000` | Level 1 max amount in cents ($1,000) |
| `APPROVAL_LEVEL2_MAX` | int | `500000` | Level 2 max amount in cents ($5,000) |
| `APPROVAL_ESIGN_THRESHOLD` | int | `500000` | eSign threshold in cents ($5,000) |
| `APPROVAL_TIMEOUT_HOURS` | int | `72` | Default approval timeout in hours |
| `APPROVAL_AUTO_ESCALATE` | bool | `true` | Auto-escalate on timeout |
| `ESIGN_THRESHOLD_MANAGER` | float | `5000.0` | Manager approval threshold |
| `ESIGN_THRESHOLD_SENIOR` | float | `25000.0` | Senior manager approval threshold |
| `ESIGN_THRESHOLD_CFO` | float | `100000.0` | CFO approval threshold |

**Approval Flow:**
- Amounts < $1,000: Auto-approved (high confidence) or Level 1
- Amounts $1,000 - $5,000: Level 2 approval required
- Amounts > $5,000: eSign required from appropriate authority

### Archival

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ARCHIVAL_STORAGE_PATH` | string | `./archival` | Directory for archived documents |
| `ARCHIVAL_RETENTION_YEARS` | int | `7` | Default retention period in years |
| `ARCHIVAL_PDFA_VERSION` | string | `PDF/A-2b` | PDF/A version for archival |
| `ARCHIVAL_ENABLE_CLOUD_BACKUP` | bool | `false` | Enable cloud backup for archives |
| `ARCHIVAL_CLOUD_PROVIDER` | string | `aws` | Cloud provider: `aws`, `azure`, `gcp` |
| `ARCHIVAL_CLOUD_BUCKET` | string | - | Cloud storage bucket/container name |
| `PDF_SEAL_CERTIFICATE_PATH` | string | `config/archival_cert.p12` | Certificate for PDF tamper seal |
| `PDF_SEAL_CERTIFICATE_PASSWORD` | string | - | Certificate password |
| `PDF_SEAL_REASON` | string | `Document archived for compliance` | Reason for sealing |
| `PDF_SEAL_LOCATION` | string | `SmartAP Archival System` | Seal location |

### Database

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | `sqlite+aiosqlite:///./smartap.db` | Database connection URL |
| `DATABASE_POOL_SIZE` | int | `5` | Connection pool size |
| `DATABASE_POOL_MAX_OVERFLOW` | int | `10` | Max overflow connections |
| `DATABASE_POOL_TIMEOUT` | int | `30` | Connection pool timeout (seconds) |
| `DATABASE_ECHO` | bool | `false` | Echo SQL queries (debugging) |

**Database URL Examples:**

```bash
# SQLite (development)
DATABASE_URL=sqlite+aiosqlite:///./smartap.db

# PostgreSQL (production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/smartap

# With SSL
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/smartap?ssl=require
```

**Production Recommendations:**
- `DATABASE_POOL_SIZE`: 20-50 based on expected load
- `DATABASE_POOL_MAX_OVERFLOW`: 10-20
- `DATABASE_ECHO`: `false` (never in production)

### Redis Cache

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_ENABLED` | bool | `false` | Enable Redis caching |
| `REDIS_URL` | string | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_TTL_SECONDS` | int | `3600` | Default cache TTL in seconds |

**Redis URL Examples:**

```bash
# Local development
REDIS_URL=redis://localhost:6379/0

# With password
REDIS_URL=redis://:password@host:6379/0

# Redis Cluster
REDIS_URL=redis://host1:6379,host2:6379,host3:6379/0
```

### Storage

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `UPLOAD_DIR` | string | `./uploads` | Directory for uploaded files |
| `PROCESSED_DIR` | string | `./processed` | Directory for processed files |
| `SIGNED_DIR` | string | `./signed` | Directory for signed documents |

**Note:** Ensure these directories have write permissions for the application user.

### ERP Integrations

#### General ERP Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ERP_SYNC_ENABLED` | bool | `true` | Enable ERP sync scheduler |
| `ERP_SYNC_INTERVAL_MINUTES` | int | `60` | Default sync interval for vendors |
| `ERP_PO_SYNC_INTERVAL_MINUTES` | int | `30` | Sync interval for purchase orders |
| `ERP_PAYMENT_SYNC_INTERVAL_MINUTES` | int | `15` | Sync interval for payment status |
| `ERP_MAX_SYNC_RETRIES` | int | `3` | Maximum sync retry attempts |
| `ERP_SYNC_BATCH_SIZE` | int | `100` | Default batch size for sync operations |

#### QuickBooks

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `QUICKBOOKS_CLIENT_ID` | string | - | QuickBooks OAuth client ID |
| `QUICKBOOKS_CLIENT_SECRET` | string | - | QuickBooks OAuth client secret |
| `QUICKBOOKS_REDIRECT_URI` | string | - | QuickBooks OAuth redirect URI |

#### Xero

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `XERO_CLIENT_ID` | string | - | Xero OAuth client ID |
| `XERO_CLIENT_SECRET` | string | - | Xero OAuth client secret |
| `XERO_REDIRECT_URI` | string | - | Xero OAuth redirect URI |

#### SAP Business One

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SAP_SERVICE_LAYER_URL` | string | - | SAP Service Layer URL |
| `SAP_VERIFY_SSL` | bool | `true` | Verify SSL for SAP connections |

#### NetSuite

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `NETSUITE_ACCOUNT_ID` | string | - | NetSuite account ID |
| `NETSUITE_CONSUMER_KEY` | string | - | NetSuite OAuth consumer key |
| `NETSUITE_CONSUMER_SECRET` | string | - | NetSuite OAuth consumer secret |
| `NETSUITE_RESTLET_URL` | string | - | NetSuite RESTlet base URL |

### Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | string | `json` | Log format: `json` or `text` |

**Log Level Recommendations:**
- **Development:** `DEBUG` or `INFO`
- **Staging:** `INFO`
- **Production:** `INFO` or `WARNING`

**Log Format:**
- `json`: Structured logs for log aggregation (ELK, CloudWatch, etc.)
- `text`: Human-readable logs for development

---

## Example Configurations

### Development Configuration

```bash
# .env.development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Database
DATABASE_URL=sqlite+aiosqlite:///./smartap.db
DATABASE_ECHO=true

# AI (GitHub Models - free tier)
AI_PROVIDER=github
GITHUB_TOKEN=ghp_your_token_here
MODEL_ID=openai/gpt-4.1

# No external services needed
REDIS_ENABLED=false
ERP_SYNC_ENABLED=false

# Relaxed CORS for development
CORS_ORIGINS=*
```

### Production Configuration

```bash
# .env.production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://smartap:${DB_PASSWORD}@postgres:5432/smartap
DATABASE_POOL_SIZE=20
DATABASE_POOL_MAX_OVERFLOW=10

# Redis
REDIS_ENABLED=true
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CACHE_TTL_SECONDS=3600

# AI
AI_PROVIDER=openai
OPENAI_API_KEY=${OPENAI_API_KEY}
MODEL_ID=gpt-4-turbo
EXTRACTION_CONFIDENCE_THRESHOLD=0.90

# Security
CORS_ORIGINS=https://app.yourcompany.com
CORS_ALLOW_CREDENTIALS=true

# OCR
FOXIT_API_KEY=${FOXIT_API_KEY}
FOXIT_API_ENDPOINT=https://api.foxit.com/ocr/v1

# eSign
FOXIT_ESIGN_API_KEY=${ESIGN_API_KEY}
FOXIT_ESIGN_API_SECRET=${ESIGN_API_SECRET}
FOXIT_ESIGN_CALLBACK_URL=https://api.yourcompany.com/api/v1/esign/webhook

# ERP Integration
ERP_SYNC_ENABLED=true
QUICKBOOKS_CLIENT_ID=${QB_CLIENT_ID}
QUICKBOOKS_CLIENT_SECRET=${QB_CLIENT_SECRET}

# Archival
ARCHIVAL_ENABLE_CLOUD_BACKUP=true
ARCHIVAL_CLOUD_PROVIDER=aws
ARCHIVAL_CLOUD_BUCKET=smartap-archives
```

### Docker Compose Environment

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - DEBUG=false
      - DATABASE_URL=postgresql+asyncpg://smartap:${DB_PASSWORD}@postgres:5432/smartap
      - REDIS_URL=redis://redis:6379/0
      - REDIS_ENABLED=true
      - LOG_FORMAT=json
      - CORS_ORIGINS=${CORS_ORIGINS}
```

### Kubernetes ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: smartap-config
  namespace: smartap
data:
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  AI_PROVIDER: "openai"
  MODEL_ID: "gpt-4-turbo"
  REDIS_ENABLED: "true"
  ERP_SYNC_ENABLED: "true"
  DATABASE_POOL_SIZE: "20"
```

---

## See Also

- [Deployment Guide](DEPLOYMENT.md)
- [API Reference](API_Reference.md)
- [Quick Start Guide](Quick_Start_Guide.md)
