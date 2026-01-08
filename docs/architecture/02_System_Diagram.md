# SmartAP System Architecture - High-Level System Diagram

**Section 2 of Architecture Documentation**

---

## System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   CLIENTS                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Browser    │    │  Mobile App  │    │  ERP System  │    │   Webhook    │  │
│  │   (React)    │    │   (Future)   │    │  (API Call)  │    │   Consumer   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
└─────────┼───────────────────┼───────────────────┼───────────────────┼──────────┘
          │                   │                   │                   │
          └───────────────────┼───────────────────┼───────────────────┘
                              │ HTTPS (TLS 1.3)   │
                              ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              LOAD BALANCER / INGRESS                             │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                         Nginx / Kubernetes Ingress                         │  │
│  │                    (SSL Termination, Rate Limiting)                        │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────────┐   ┌───────────────────────────────────┐
│         FRONTEND SERVICE          │   │         BACKEND API SERVICE        │
│  ┌─────────────────────────────┐  │   │  ┌─────────────────────────────┐  │
│  │        Next.js 14           │  │   │  │        FastAPI 0.110+       │  │
│  │  ┌───────────────────────┐  │  │   │  │  ┌───────────────────────┐  │  │
│  │  │   React Components    │  │  │   │  │  │    REST Endpoints     │  │  │
│  │  │   • Dashboard         │  │  │   │  │  │    • /api/invoices    │  │  │
│  │  │   • Invoice Upload    │  │  │   │  │  │    • /api/vendors     │  │  │
│  │  │   • Review & Approve  │  │  │   │  │  │    • /api/pos         │  │  │
│  │  │   • Vendor Management │  │  │   │  │  │    • /api/approvals   │  │  │
│  │  │   • Reports           │  │  │   │  │  │    • /api/auth        │  │  │
│  │  └───────────────────────┘  │  │   │  │  └───────────────────────┘  │  │
│  │  ┌───────────────────────┐  │  │   │  │  ┌───────────────────────┐  │  │
│  │  │   State Management    │  │  │   │  │  │     Middleware        │  │  │
│  │  │   • React Query       │  │  │   │  │  │   • Authentication    │  │  │
│  │  │   • Context API       │  │  │   │  │  │   • Rate Limiting     │  │  │
│  │  └───────────────────────┘  │  │   │  │  │   • CORS              │  │  │
│  └─────────────────────────────┘  │   │  │  │   • Logging           │  │  │
│           Port: 3000              │   │  │  └───────────────────────┘  │  │
└───────────────────────────────────┘   │  └─────────────────────────────┘  │
                                        │           Port: 8000              │
                                        └─────────────────┬─────────────────┘
                                                          │
                    ┌─────────────────┬───────────────────┼───────────────────┬─────────────────┐
                    │                 │                   │                   │                 │
                    ▼                 ▼                   ▼                   ▼                 ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│    AGENT ORCHESTRATOR   │ │      TASK QUEUE         │ │       DATABASE          │ │         CACHE           │
│  ┌───────────────────┐  │ │  ┌───────────────────┐  │ │  ┌───────────────────┐  │ │  ┌───────────────────┐  │
│  │   LangChain /     │  │ │  │   Celery 5.3      │  │ │  │  PostgreSQL 16    │  │ │  │    Redis 7        │  │
│  │   PydanticAI      │  │ │  │                   │  │ │  │                   │  │ │  │                   │  │
│  │  ┌─────────────┐  │  │ │  │  • Worker Pool    │  │ │  │  • Invoices       │  │ │  │  • Session Store  │  │
│  │  │ Extractor   │  │  │ │  │  • Beat Scheduler │  │ │  │  • Vendors        │  │ │  │  • Task Results   │  │
│  │  │ Agent       │  │  │ │  │  • Result Backend │  │ │  │  • PurchaseOrders │  │ │  │  • API Cache      │  │
│  │  └─────────────┘  │  │ │  └───────────────────┘  │ │  │  • LineItems      │  │ │  │  • Rate Limits    │  │
│  │  ┌─────────────┐  │  │ │                         │ │  │  • Approvals      │  │ │  └───────────────────┘  │
│  │  │ Auditor     │  │  │ │  Tasks:                 │ │  │  • Users          │  │ │       Port: 6379        │
│  │  │ Agent       │  │  │ │  • extract_invoice      │ │  │  • AuditLogs      │  │ └─────────────────────────┘
│  │  └─────────────┘  │  │ │  • match_po             │ │  └───────────────────┘  │
│  │  ┌─────────────┐  │  │ │  • detect_fraud         │ │       Port: 5432        │
│  │  │ Matcher     │  │  │ │  • send_notification    │ └─────────────────────────┘
│  │  │ Agent       │  │  │ │  • sync_erp             │
│  │  └─────────────┘  │  │ │  • archive_invoice      │
│  │  ┌─────────────┐  │  │ └─────────────────────────┘
│  │  │ Fraud       │  │  │
│  │  │ Agent       │  │  │
│  │  └─────────────┘  │  │
│  │  ┌─────────────┐  │  │
│  │  │ Approval    │  │  │
│  │  │ Router      │  │  │
│  │  └─────────────┘  │  │
│  └───────────────────┘  │
└─────────────────────────┘
          │
          │ API Calls
          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL SERVICES                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │   Foxit PDF SDK  │  │   AI Providers   │  │   ERP Systems    │              │
│  │                  │  │                  │  │                  │              │
│  │  • Text Extract  │  │  • GitHub Models │  │  • QuickBooks    │              │
│  │  • OCR Engine    │  │  • OpenAI        │  │  • Xero          │              │
│  │  • eSign (Opt)   │  │  • Anthropic     │  │  • SAP           │              │
│  │                  │  │  • Azure OpenAI  │  │  • NetSuite      │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
│                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │   Email Service  │  │  Cloud Storage   │  │   Monitoring     │              │
│  │                  │  │                  │  │                  │              │
│  │  • SMTP Server   │  │  • S3 / Azure    │  │  • Prometheus    │              │
│  │  • SendGrid      │  │    Blob Storage  │  │  • Grafana       │              │
│  │  • SES           │  │  • Local FS      │  │  • Sentry        │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Diagram

### Invoice Upload & Processing Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Frontend │     │ Backend  │     │  Worker  │     │ Database │
│ Browser  │     │ Next.js  │     │ FastAPI  │     │  Celery  │     │ Postgres │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │                │
     │ 1. Select PDF  │                │                │                │
     │ ─────────────> │                │                │                │
     │                │                │                │                │
     │                │ 2. POST /api/invoices/upload    │                │
     │                │ ─────────────────────────────> │                │
     │                │                │                │                │
     │                │                │ 3. Save file   │                │
     │                │                │ ─────────────────────────────> │
     │                │                │                │                │
     │                │                │ 4. Queue task  │                │
     │                │                │ ─────────────> │                │
     │                │                │                │                │
     │                │ 5. Return invoice_id (pending)  │                │
     │                │ <───────────────────────────── │                │
     │                │                │                │                │
     │ 6. Show "Processing..."         │                │                │
     │ <───────────── │                │                │                │
     │                │                │                │                │
     │                │                │                │ 7. Extract text│
     │                │                │                │ ──────────────>│
     │                │                │                │    (Foxit)     │
     │                │                │                │                │
     │                │                │                │ 8. AI Extract  │
     │                │                │                │ ──────────────>│
     │                │                │                │    (GPT-4o)    │
     │                │                │                │                │
     │                │                │                │ 9. Validate    │
     │                │                │                │ ──────────────>│
     │                │                │                │   (Auditor)    │
     │                │                │                │                │
     │                │                │                │ 10. Match PO   │
     │                │                │                │ ──────────────>│
     │                │                │                │   (Matcher)    │
     │                │                │                │                │
     │                │                │                │ 11. Fraud Check│
     │                │                │                │ ──────────────>│
     │                │                │                │  (Fraud Agent) │
     │                │                │                │                │
     │                │                │                │ 12. Update DB  │
     │                │                │                │ ─────────────> │
     │                │                │                │                │
     │                │ 13. Poll GET /api/invoices/{id} │                │
     │                │ ─────────────────────────────> │                │
     │                │                │                │                │
     │                │                │ 14. Fetch from DB               │
     │                │                │ ─────────────────────────────> │
     │                │                │                │                │
     │                │ 15. Return invoice (extracted)  │                │
     │                │ <───────────────────────────── │                │
     │                │                │                │                │
     │ 16. Show extracted data         │                │                │
     │ <───────────── │                │                │                │
     │                │                │                │                │
```

---

## Service Communication

### Internal Service Network

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Network: smartap_default               │
│                                                                  │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │   nginx     │─────>│  frontend   │      │   backend   │     │
│  │   :80/:443  │      │    :3000    │<────>│    :8000    │     │
│  └─────────────┘      └─────────────┘      └──────┬──────┘     │
│         │                                         │             │
│         │                    ┌────────────────────┼─────────┐  │
│         │                    │                    │         │  │
│         ▼                    ▼                    ▼         ▼  │
│  ┌─────────────┐      ┌─────────────┐      ┌───────────────┐  │
│  │   worker    │─────>│   redis     │<─────│   postgres    │  │
│  │   (celery)  │      │    :6379    │      │     :5432     │  │
│  └─────────────┘      └─────────────┘      └───────────────┘  │
│         │                    ▲                                 │
│         │                    │                                 │
│  ┌──────┴──────┐             │                                 │
│  │  scheduler  │─────────────┘                                 │
│  │ (celery-beat)                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Port Mapping

| Service | Internal Port | External Port | Protocol |
|---------|---------------|---------------|----------|
| nginx | 80, 443 | 80, 443 | HTTP/HTTPS |
| frontend | 3000 | 3000 (dev only) | HTTP |
| backend | 8000 | 8000 (dev only) | HTTP |
| postgres | 5432 | 5432 (dev only) | TCP |
| redis | 6379 | - (internal only) | TCP |
| worker | - | - | - |
| scheduler | - | - | - |

---

## Data Flow Summary

### 1. **Synchronous Request Flow** (User-Facing)
```
User → Nginx → Frontend/Backend → Database → Response
```
- Login, logout, list invoices, view details, manual edits
- Response time target: <200ms

### 2. **Asynchronous Task Flow** (Background)
```
Backend → Redis Queue → Celery Worker → Database
                                      → External Services
```
- Invoice extraction, PO matching, fraud detection, notifications
- Processing time: 5-30 seconds per invoice

### 3. **Scheduled Task Flow** (Periodic)
```
Celery Beat → Redis Queue → Celery Worker → Database/External
```
- Daily reports, invoice archival, cleanup tasks
- Runs on configurable schedule (cron)

### 4. **Webhook Flow** (Outbound)
```
Event → Backend → HTTP POST → External Consumer
```
- Invoice status changes, approval events
- Retry on failure with exponential backoff

---

## Deployment Topologies

### Development (docker-compose)

```
┌─────────────────────────────────────────┐
│            Single Host (Dev)            │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │
│  │nginx│ │front│ │back │ │work │       │
│  └─────┘ └─────┘ └─────┘ └─────┘       │
│  ┌─────┐ ┌─────┐ ┌─────┐               │
│  │sched│ │redis│ │postgres│            │
│  └─────┘ └─────┘ └─────┘               │
└─────────────────────────────────────────┘
```

### Production (Kubernetes)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                                │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                        Ingress Controller                       │  │
│  │                     (nginx-ingress + TLS)                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                  │                                    │
│       ┌──────────────────────────┼──────────────────────────┐        │
│       ▼                          ▼                          ▼        │
│  ┌──────────┐              ┌──────────┐              ┌──────────┐   │
│  │ frontend │              │ backend  │              │  worker  │   │
│  │ Deployment│              │Deployment│              │Deployment│   │
│  │ (2-5 pods)│              │(3-20 pods)│             │(5-30 pods)│  │
│  │   HPA     │              │   HPA    │              │   HPA    │   │
│  └──────────┘              └──────────┘              └──────────┘   │
│       │                          │                          │        │
│       └──────────────────────────┼──────────────────────────┘        │
│                                  │                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                     Internal Services                         │   │
│  │  ┌────────────────┐              ┌────────────────┐          │   │
│  │  │   PostgreSQL   │              │     Redis      │          │   │
│  │  │  StatefulSet   │              │  StatefulSet   │          │   │
│  │  │   (Primary +   │              │   (Sentinel    │          │   │
│  │  │    Replica)    │              │    Optional)   │          │   │
│  │  └────────────────┘              └────────────────┘          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- **[Section 1: Overview & Design Principles](./Architecture.md)** - Foundation and technology choices
- **[Section 3: Component Deep Dive](./03_Component_Details.md)** - Detailed component specifications
- **[Section 4: Agent Orchestration](./04_Agent_Orchestration.md)** - AI agent pipeline details
- **[Deployment Guide](./Deployment_Guide.md)** - Step-by-step deployment instructions
- **[Helm Chart README](../helm/smartap/README.md)** - Kubernetes deployment with Helm

---

*Continue to [Section 3: Component Deep Dive](./03_Component_Details.md)*
