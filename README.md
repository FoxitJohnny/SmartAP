# SmartAP - Intelligent Accounts Payable Automation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**SmartAP** is an open-source, AI-powered accounts payable automation platform that transforms manual invoice processing into an intelligent, streamlined workflow. Built with modern AI agent architecture, SmartAP extracts data from invoices, validates against purchase orders, detects fraud, and routes for approval—all while learning from your finance team's decisions.

🎯 **Mission:** Make AP automation accessible to every organization, from startups to enterprises, without vendor lock-in or prohibitive costs.

---

## ✨ Key Features

### 🤖 AI-Powered Intelligence
- **Multi-Agent Architecture:** Specialized agents for extraction, validation, fraud detection, and approval routing
- **Flexible AI Providers:** Choose from GitHub Models (gpt-4o), OpenAI, Anthropic, or Azure OpenAI
- **Adaptive Learning:** Agents improve accuracy based on your correction history
- **Agentic Workflows:** Complex approval chains, escalations, and conditional routing

### 📄 Advanced Document Processing
- **Foxit PDF SDK Integration:** Enterprise-grade PDF parsing and text extraction
- **OCR for Scanned Invoices:** Handles handwritten notes, stamps, and low-quality scans
- **Multi-Format Support:** PDF, TIFF, PNG, JPEG invoice uploads
- **Structured Data Extraction:** Line items, totals, taxes, vendor details, payment terms

### 🔄 3-Way Matching & Validation
- **Purchase Order Matching:** Automatic PO lookup and line-item comparison
- **Tolerance Management:** Configurable price/quantity variance thresholds
- **Exception Handling:** Flags mismatches for manual review
- **Audit Trail:** Complete history of matches, approvals, and modifications

### 🛡️ Fraud Detection & Compliance
- **Duplicate Invoice Detection:** Identifies resubmitted invoices across all systems
- **Vendor Validation:** Cross-references against approved vendor master
- **Anomaly Detection:** Flags unusual amounts, payment terms, or vendor changes
- **Compliance Checks:** Tax calculation validation, regulatory requirements

### 📊 Workflow & Approval Management
- **Dynamic Approval Routing:** Role-based, amount-based, and department-based rules
- **Multi-Level Approvals:** Sequential and parallel approval chains
- **Email Notifications:** Real-time alerts for pending approvals
- **Mobile-Friendly Dashboard:** Approve invoices on-the-go

### 🔌 Extensibility & Integration
- **Plugin Architecture:** Build custom agents in minutes (see [Extensibility Guide](docs/Extensibility_Guide.md))
- **REST API:** Full-featured API for ERP integration (SAP, NetSuite, QuickBooks)
- **Webhook Support:** Real-time notifications for invoice events
- **Export Formats:** JSON, CSV, XML for accounting systems

### 🚀 Production-Ready Deployment
- **Docker Compose:** One-command local setup (`docker-compose up -d`)
- **Kubernetes Helm Charts:** Production deployment with auto-scaling
- **High Availability:** StatefulSets for databases, HPA for compute services
- **Monitoring:** Health checks, Prometheus metrics, structured logging

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                      │
│  Invoice Upload │ Dashboard │ Approvals │ Vendor Management     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
┌───────────────────────────┴─────────────────────────────────────┐
│                      Backend (FastAPI)                          │
│  Authentication │ API Endpoints │ Business Logic │ Webhooks     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
│  PostgreSQL  │    │   Redis     │    │ Foxit PDF   │
│  (Invoices,  │    │  (Cache,    │    │   Service   │
│   Vendors,   │    │   Queue)    │    │             │
│   POs, Users)│    └─────────────┘    └─────────────┘
└──────────────┘
        │
┌───────▼────────────────────────────────────────────────────────┐
│                    AI Agent Orchestration                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Extractor   │→ │   Auditor    │→ │ Fraud Agent  │         │
│  │    Agent     │  │    Agent     │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                           │                                     │
│                    ┌──────▼──────┐                             │
│                    │  Approval   │                             │
│                    │   Router    │                             │
│                    └─────────────┘                             │
└────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Frontend:** Next.js 14 with TypeScript, React Query, Tailwind CSS
- **Backend:** FastAPI (Python 3.12) with async SQLAlchemy ORM
- **Database:** PostgreSQL 16 for transactional data
- **Cache/Queue:** Redis 7 for Celery task queue and session storage
- **PDF Processing:** Foxit PDF SDK for text extraction and OCR
- **AI Orchestration:** LangChain + PydanticAI for agent workflows
- **Task Workers:** Celery for background processing (invoice extraction, matching)
- **Task Scheduler:** Celery Beat for periodic tasks (daily reports, archival)

---

## 🚀 Quick Start (5-Minute Setup)

### Prerequisites
- **Docker** 24.0+ and **Docker Compose** 2.20+
- **Git** 2.40+
- **Foxit API Key** (free trial at [developers.foxit.com](https://developers.foxit.com/))
- **AI API Key** (GitHub Models, OpenAI, or Anthropic)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/smartap.git
   cd smartap
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```bash
   # Foxit API Key (required)
   FOXIT_API_KEY=your_foxit_key_here
   
   # AI Provider (choose one)
   AI_PROVIDER=github  # or "openai" or "anthropic"
   GITHUB_TOKEN=your_github_token  # if using GitHub Models
   OPENAI_API_KEY=your_openai_key  # if using OpenAI
   ANTHROPIC_API_KEY=your_anthropic_key  # if using Anthropic
   
   # Database (auto-configured for Docker)
   POSTGRES_PASSWORD=smartap_secure_pass_123
   REDIS_PASSWORD=redis_secure_pass_456
   
   # Application Secrets (generate with: openssl rand -hex 32)
   SECRET_KEY=your_secret_key_here
   JWT_SECRET=your_jwt_secret_here
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```
   
   This will start:
   - PostgreSQL database (port 5432)
   - Redis cache (port 6379)
   - Backend API (port 8000)
   - Frontend UI (port 3000)
   - Celery worker (background tasks)
   - Celery beat (scheduler)
   - Nginx (reverse proxy on port 80)

4. **Verify deployment:**
   ```bash
   docker-compose ps  # All services should show "Up"
   ```

5. **Access SmartAP:**
   - **Frontend:** http://localhost (or http://localhost:3000)
   - **API Docs:** http://localhost/api/docs
   - **Default Login:** admin@smartap.example.com / admin123 (⚠️ Change immediately!)

6. **Upload your first invoice:**
   - Navigate to the **Dashboard** → **Upload Invoice**
   - Drag and drop a PDF invoice
   - Watch as SmartAP extracts data, validates against POs, and routes for approval

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Quick Start Guide](docs/Quick_Start_Guide.md) | Step-by-step setup with troubleshooting |
| [Architecture](docs/Architecture.md) | System design, data models, and API overview |
| [Deployment Guide](docs/Deployment_Guide.md) | Docker, Kubernetes, Azure deployment instructions |
| [Extensibility Guide](docs/Extensibility_Guide.md) | Building custom agents and plugins |
| [API Reference](docs/API_Reference.md) | REST API endpoints and examples |
| [FAQ](docs/FAQ.md) | Common questions and troubleshooting |
| [Helm Chart README](helm/smartap/README.md) | Kubernetes deployment with Helm |

---

## 🛠️ Technology Stack

### Backend
- **Language:** Python 3.12
- **Framework:** FastAPI 0.110+ (async REST API)
- **ORM:** SQLAlchemy 2.0+ with Alembic migrations
- **Task Queue:** Celery 5.3+ with Redis backend
- **AI Framework:** LangChain 0.1+, PydanticAI 0.0.14+
- **PDF Processing:** Foxit PDF SDK for Python
- **Testing:** pytest, pytest-asyncio, pytest-cov

### Frontend
- **Language:** TypeScript 5.3+
- **Framework:** Next.js 14 (App Router)
- **UI Library:** React 18 with Tailwind CSS 3.4
- **State Management:** React Query (TanStack Query)
- **Forms:** React Hook Form with Zod validation
- **Charts:** Recharts for analytics
- **Testing:** Jest, React Testing Library

### Infrastructure
- **Database:** PostgreSQL 16
- **Cache/Queue:** Redis 7
- **Reverse Proxy:** Nginx 1.25
- **Container Runtime:** Docker 24.0+
- **Orchestration:** Kubernetes 1.23+ (Helm 3.8+)
- **CI/CD:** GitHub Actions
- **Monitoring:** Prometheus, Grafana (optional)

### AI/ML
- **AI Providers:** GitHub Models (gpt-4o), OpenAI, Anthropic Claude
- **Agent Framework:** LangChain for orchestration
- **Data Validation:** PydanticAI for structured outputs
- **OCR:** Foxit PDF SDK with OCR engine

---

## 🎯 Use Cases

### Small Businesses (10-100 invoices/month)
- **Problem:** Manual data entry into accounting software
- **Solution:** Upload invoices, auto-extract to CSV, import to QuickBooks
- **Benefit:** 90% reduction in data entry time

### Mid-Sized Companies (100-1,000 invoices/month)
- **Problem:** Inconsistent approval workflows, duplicate payments
- **Solution:** 3-way matching, approval routing, fraud detection
- **Benefit:** 95% automation rate, zero duplicate payments

### Enterprises (1,000+ invoices/month)
- **Problem:** Complex approval hierarchies, multi-currency, ERP integration
- **Solution:** Custom agents, SAP/NetSuite integration, multi-language support
- **Benefit:** 40% cost reduction vs. commercial AP solutions

---

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving docs, or sharing feedback, your help is appreciated.

**Getting Started:**
1. Read the [Contribution Guidelines](CONTRIBUTING.md)
2. Fork the repository
3. Create a feature branch (`git checkout -b feature/amazing-feature`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

**Code Style:**
- Python: PEP 8, Black formatter, Flake8 linter
- TypeScript: Prettier, ESLint
- Commits: Conventional Commits (feat:, fix:, docs:, etc.)

**Testing:**
- Backend: `pytest` (coverage >80%)
- Frontend: `npm test` (Jest + React Testing Library)

---

## 🏆 Community & Support

- **GitHub Discussions:** [Ask questions, share ideas](https://github.com/yourusername/smartap/discussions)
- **Discord Server:** [Join our community](https://discord.gg/smartap) (coming soon)
- **Issue Tracker:** [Report bugs, request features](https://github.com/yourusername/smartap/issues)
- **Email Support:** support@smartap.example.com

---

## 📊 Project Status

### Current Version: 1.0.0 (Open-Source Launch)

**Completed Features:**
- ✅ Invoice upload and storage
- ✅ AI-powered data extraction (Foxit + GPT-4o)
- ✅ 3-way matching with purchase orders
- ✅ Multi-level approval workflows
- ✅ Fraud detection and duplicate checking
- ✅ Vendor master management
- ✅ User roles and permissions
- ✅ REST API with JWT authentication
- ✅ Docker Compose deployment
- ✅ Kubernetes Helm charts
- ✅ Extensibility plugin system

**In Progress:**
- 🚧 Mobile app (iOS/Android)
- 🚧 SAP integration module
- 🚧 OCR for handwritten invoices (advanced)
- 🚧 Multi-tenant SaaS mode

**Roadmap:**
- 📅 **Q1 2026:** NetSuite integration, QuickBooks connector
- 📅 **Q2 2026:** Machine learning for approval prediction
- 📅 **Q3 2026:** Multi-language support (Spanish, German, French)
- 📅 **Q4 2026:** Blockchain-based audit trail

See [ROADMAP.md](ROADMAP.md) for detailed plans.

---

## 📖 Sample Data

SmartAP includes **50 synthetic invoice samples** covering:
- ✅ Clean, professional invoices (30)
- ✅ Handwritten notes and stamps (10)
- ✅ Low-quality scans and rotated pages (5)
- ✅ Multi-page invoices (3)
- ✅ International formats (EUR, GBP, JPY) (2)

**Load sample data:**
```bash
docker-compose exec backend python -m scripts.load_sample_data
```

This will:
1. Create 10 sample vendors
2. Generate 20 purchase orders
3. Upload 50 invoices with ground-truth JSON files
4. Demonstrate matching, approvals, and exceptions

**Ground truth data:** `samples/ground_truth/` contains JSON files with expected extraction results for testing.

---

## 🔒 Security

SmartAP follows security best practices:
- 🔐 JWT authentication with refresh tokens
- 🔐 Password hashing with bcrypt
- 🔐 SQL injection prevention (SQLAlchemy ORM)
- 🔐 CORS configuration for frontend
- 🔐 Rate limiting on API endpoints
- 🔐 Environment variables for secrets (no hardcoding)
- 🔐 HTTPS/TLS for production deployments

**Reporting Vulnerabilities:**
Please email security@smartap.example.com (GPG key available). Do not open public issues for security bugs.

---

## 📜 License

SmartAP is open-source software licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 SmartAP Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

SmartAP is built on the shoulders of giants:

- **Foxit Software:** Enterprise PDF SDK
- **LangChain:** AI agent orchestration framework
- **FastAPI:** Modern Python web framework
- **Next.js:** React framework for production
- **PostgreSQL:** World's most advanced open-source database
- **Redis:** In-memory data structure store

Special thanks to all [contributors](https://github.com/yourusername/smartap/graphs/contributors) who have helped build SmartAP!

---

## 📞 Contact

- **Website:** https://smartap.example.com
- **Email:** hello@smartap.example.com
- **Twitter:** [@smartap_ai](https://twitter.com/smartap_ai)
- **LinkedIn:** [SmartAP Company Page](https://linkedin.com/company/smartap)

---

<div align="center">
  <strong>Made with ❤️ by the SmartAP community</strong>
  <br>
  <sub>Built for finance teams, by developers who understand your pain.</sub>
</div>

