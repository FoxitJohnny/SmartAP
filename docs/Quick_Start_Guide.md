# SmartAP Quick Start Guide

**Get SmartAP running with Docker in under 5 minutes!** 🚀

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Running SmartAP](#running-smartap)
4. [Accessing the Application](#accessing-the-application)
5. [Testing with Sample Data](#testing-with-sample-data)
6. [Basic Workflow](#basic-workflow)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (20.10 or higher)
  - Download: https://www.docker.com/get-started
  - Verify: `docker --version`

- **Docker Compose** (2.0 or higher)
  - Usually included with Docker Desktop
  - Verify: `docker-compose --version`

- **Git** (optional, for cloning repository)
  - Download: https://git-scm.com/downloads

### System Requirements

- **RAM:** 4GB minimum (8GB recommended)
- **Disk:** 10GB free space
- **OS:** Windows 10+, macOS 10.14+, or Linux (Ubuntu 20.04+)

---

## Installation

### Step 1: Get the Code

**Option A: Clone from GitHub**

```bash
git clone https://github.com/your-org/SmartAP.git
cd SmartAP
```

**Option B: Download ZIP**

1. Visit: https://github.com/your-org/SmartAP
2. Click "Code" → "Download ZIP"
3. Extract and open folder

### Step 2: Configure Environment

Create your `.env` file from the template:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the file with your settings (optional for quick start)
# nano .env  # Linux/Mac
# notepad .env  # Windows
```

**Minimal Configuration for Quick Start:**

The default `.env.example` values work out-of-the-box. For production, update these critical settings:

```bash
# Database (default values work for development)
DB_HOST=db
DB_PORT=5432
DB_NAME=smartap
DB_USER=smartap
DB_PASSWORD=your_secure_password  # Change this!

# Backend
SECRET_KEY=your_secret_key_here  # Generate: openssl rand -hex 32

# AI Provider (choose one)
AI_PROVIDER=github  # Options: github, azure, openai

# GitHub Models (if using github provider)
GITHUB_TOKEN=your_github_token
GITHUB_MODEL=gpt-4o

# Azure AI (if using azure provider)
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your_api_key
# AZURE_OPENAI_DEPLOYMENT=gpt-4

# OpenAI (if using openai provider)
# OPENAI_API_KEY=your_api_key
# OPENAI_MODEL=gpt-4-turbo
```

**🎯 Quick Start Tip:** For testing, use GitHub Models with a free GitHub token.

### Step 3: Get API Keys (Optional)

For full functionality, sign up for these services:

1. **GitHub Models** (Free for testing)
   - Visit: https://github.com/marketplace/models
   - Generate token: Settings → Developer settings → Personal access tokens
   - Add to `.env`: `GITHUB_TOKEN=your_token`

2. **Foxit eSign** (Optional, for digital signatures)
   - Visit: https://www.foxit.com/esign
   - Get API key and add to `.env`

3. **ERP Integration** (Optional)
   - QuickBooks, Xero, SAP, or NetSuite credentials

---

## Running SmartAP

### Development Mode (Basic Services)

Start the core services (database, backend, frontend):

```bash
docker-compose up
```

**Expected Output:**

```
[+] Running 4/4
 ⠿ Container smartap-db-1        Started
 ⠿ Container smartap-redis-1     Started
 ⠿ Container smartap-backend-1   Started
 ⠿ Container smartap-frontend-1  Started
```

**Wait for services to be ready** (30-60 seconds):
- ✅ Database migrations complete
- ✅ Backend API listening on port 8000
- ✅ Frontend ready on port 3000

### Production Mode (All Services)

Start with background workers and production proxy:

```bash
docker-compose --profile production up
```

**This adds:**
- ✅ Celery worker (background tasks)
- ✅ Celery beat (scheduled jobs)
- ✅ Nginx proxy (load balancing)

### Background Mode

Run services in the background:

```bash
docker-compose up -d
```

**View logs:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

**Stop services:**

```bash
docker-compose down
```

**Reset everything (⚠️ deletes data):**

```bash
docker-compose down -v
```

---

## Accessing the Application

Once services are running:

### Web Interface

**Frontend (React UI)**
- URL: http://localhost:3000
- Default login: `admin@smartap.com` / `admin123`

### API

**Backend API (FastAPI)**
- URL: http://localhost:8000
- Docs: http://localhost:8000/docs (Swagger UI)
- Redoc: http://localhost:8000/redoc

### Database

**PostgreSQL**
- Host: localhost
- Port: 5432
- User: smartap
- Password: (from `.env`)
- Database: smartap

**Connect with psql:**

```bash
docker-compose exec db psql -U smartap -d smartap
```

### Redis Cache

**Redis**
- URL: redis://localhost:6379

**Connect with redis-cli:**

```bash
docker-compose exec redis redis-cli
```

---

## Testing with Sample Data

SmartAP includes 50 synthetic invoices for testing.

### Generate Sample Invoices

```bash
# Run the sample data generator
docker-compose exec backend python /app/scripts/generate_sample_data.py
```

**This creates:**
- 📄 20 clean invoices (perfect formatting)
- 📄 20 messy invoices (poor scans)
- 📄 10 handwritten invoices (cursive text)

**Output location:** `sample-data/invoices/`

### Upload Test Invoice

**Via Web UI:**

1. Navigate to http://localhost:3000
2. Click "Upload Invoice"
3. Select a file from `sample-data/invoices/`
4. Watch the AI extraction in real-time!

**Via API:**

```bash
# Upload invoice via curl
curl -X POST http://localhost:8000/api/invoices/upload \
  -F "file=@sample-data/invoices/clean/invoice_001.pdf"
```

**Via Python:**

```python
import httpx

with open("sample-data/invoices/clean/invoice_001.pdf", "rb") as f:
    files = {"file": f}
    response = httpx.post("http://localhost:8000/api/invoices/upload", files=files)
    print(response.json())
```

---

## Basic Workflow

### 1. Upload Invoice

- Drag & drop PDF or click "Upload"
- Supports: PDF, PNG, JPG, TIFF

### 2. AI Extraction

SmartAP automatically:
- ✅ Extracts text with OCR (Foxit SDK)
- ✅ Identifies vendor, date, amounts
- ✅ Extracts line items
- ✅ Validates data with 3-way matching
- ✅ Checks for duplicates/fraud

### 3. Review & Approve

- View extracted data
- Edit if needed (low-confidence fields highlighted)
- Approve or reject invoice

### 4. ERP Integration

- Approved invoices sync to your ERP
- Status updates in real-time
- Audit trail maintained

### 5. Digital Signature

- Optional: Sign with Foxit eSign
- Archival to secure storage

---

## Configuration

### Essential Settings

**AI Provider Selection:**

```bash
# GitHub Models (Free, rate-limited)
AI_PROVIDER=github
GITHUB_TOKEN=your_token
GITHUB_MODEL=gpt-4o

# Azure OpenAI (Recommended for production)
AI_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt-4

# OpenAI (Direct API)
AI_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4-turbo
```

**Approval Thresholds:**

```bash
# Auto-approve invoices below threshold
AUTO_APPROVE_THRESHOLD=1000.00

# Flag for review above threshold
REVIEW_REQUIRED_THRESHOLD=10000.00
```

**Email Notifications:**

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
NOTIFICATION_EMAIL=approvers@company.com
```

### ERP Connectors

**QuickBooks:**

```bash
QUICKBOOKS_CLIENT_ID=your_client_id
QUICKBOOKS_CLIENT_SECRET=your_secret
QUICKBOOKS_REDIRECT_URI=http://localhost:8000/api/erp/quickbooks/callback
```

**Xero:**

```bash
XERO_CLIENT_ID=your_client_id
XERO_CLIENT_SECRET=your_secret
XERO_REDIRECT_URI=http://localhost:8000/api/erp/xero/callback
```

**SAP:**

```bash
SAP_API_URL=https://your-sap-instance.com/api
SAP_USERNAME=your_username
SAP_PASSWORD=your_password
```

---

## Troubleshooting

### Common Issues

#### 1. "Port already in use"

**Error:** `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Solution:** Stop conflicting service or change port

```bash
# Find process using port
lsof -i :3000  # Mac/Linux
netstat -ano | findstr :3000  # Windows

# Kill process (Mac/Linux)
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "3001:3000"  # Use port 3001 instead
```

#### 2. "Database connection failed"

**Error:** `FATAL: password authentication failed for user "smartap"`

**Solution:** Reset database

```bash
docker-compose down -v
docker-compose up
```

#### 3. "Backend not starting"

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:** Rebuild containers

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

#### 4. "Frontend shows blank page"

**Error:** Browser shows empty page or "Cannot connect to API"

**Solution:** Check API URL

```bash
# Ensure REACT_APP_API_URL is set correctly
echo $REACT_APP_API_URL  # Should be http://localhost:8000

# Rebuild frontend
docker-compose build frontend
docker-compose up frontend
```

#### 5. "AI extraction failing"

**Error:** `401 Unauthorized` or `Rate limit exceeded`

**Solution:** Verify AI provider credentials

```bash
# Check environment variables
docker-compose exec backend env | grep GITHUB_TOKEN

# Test API key
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://models.github.com/v1/models
```

### Health Checks

**Check service status:**

```bash
docker-compose ps
```

**Expected output:**

```
NAME                   STATUS              PORTS
smartap-db-1          Up 2 minutes        5432/tcp
smartap-redis-1       Up 2 minutes        6379/tcp
smartap-backend-1     Up 1 minute         0.0.0.0:8000->8000/tcp
smartap-frontend-1    Up 1 minute         0.0.0.0:3000->3000/tcp
```

**Test API health:**

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

**Check logs:**

```bash
# Backend logs
docker-compose logs backend --tail=50

# Frontend logs
docker-compose logs frontend --tail=50

# Database logs
docker-compose logs db --tail=50
```

### Getting Help

- **Documentation:** https://docs.smartap.dev
- **GitHub Issues:** https://github.com/your-org/SmartAP/issues
- **Discord:** https://discord.gg/smartap
- **Email:** support@smartap.dev

---

## Next Steps

### Explore Features

- **Dashboard:** View processing metrics and analytics
- **Approval Workflow:** Configure multi-level approvals
- **Audit Trail:** Track all invoice changes
- **Reports:** Generate spend analysis reports

### Customize

- **Create Custom Agents:** See [Extensibility Guide](./Extensibility_Guide.md)
- **Add ERP Connector:** Integrate with your accounting system
- **Configure Workflows:** Set up approval rules
- **Brand UI:** Customize colors and logo

### Deploy to Production

- **Use Production Profile:** `docker-compose --profile production up -d`
- **Enable HTTPS:** Configure SSL certificates
- **Set Up Backups:** Schedule database backups
- **Monitor:** Add logging and monitoring tools

### Learn More

- 📖 [User Guide](./User_Guide.md)
- 🔌 [Extensibility Guide](./Extensibility_Guide.md)
- 🏗️ [Architecture Overview](./Architecture.md)
- 🔐 [Security Best Practices](./Security.md)
- 🚀 [Deployment Guide](./Deployment.md)

---

## Quick Reference

### Common Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild containers
docker-compose build

# Reset everything
docker-compose down -v

# Run backend command
docker-compose exec backend python manage.py <command>

# Access database
docker-compose exec db psql -U smartap -d smartap

# Generate sample data
docker-compose exec backend python /app/scripts/generate_sample_data.py

# Run tests
docker-compose exec backend pytest
```

### Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | React web interface |
| Backend API | http://localhost:8000 | FastAPI REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Web UI | admin@smartap.com | admin123 |
| Database | smartap | (from .env) |

⚠️ **Change default passwords in production!**

---

## Congratulations! 🎉

You now have SmartAP running locally. Upload your first invoice and watch the AI magic happen!

**Need help?** Join our [Discord community](https://discord.gg/smartap) or check the [documentation](https://docs.smartap.dev).

Happy automating! 🚀
