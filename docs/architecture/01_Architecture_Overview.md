# SmartAP Architecture

**Version:** 1.0  
**Last Updated:** January 2026  
**Status:** Production

---

## Table of Contents

1. [Overview & Design Principles](#overview--design-principles) *(This document)*
2. [High-Level System Diagram](./02_System_Diagram.md)
3. [Component Deep Dive](./03_Component_Details.md)
4. [Agent Orchestration Flow](./04_Agent_Orchestration.md)
5. [Data Model](./05_Data_Model.md)
6. [API Overview](./06_API_Overview.md)
7. [Security Architecture](./07_Security_Architecture.md)
8. [Scalability & Performance](./08_Scalability.md)

---

## Overview & Design Principles

### Executive Summary

SmartAP is a modern, AI-powered accounts payable automation platform designed to transform manual invoice processing into an intelligent, streamlined workflow. The system leverages a multi-agent architecture where specialized AI agents collaborate to extract data, validate accuracy, match with purchase orders, detect fraud, and route invoices for approval.

The architecture is built on three foundational pillars:
- **Modularity:** Each component operates independently and communicates via well-defined APIs
- **Extensibility:** Plugin system allows custom agents and integrations without core modifications
- **Scalability:** Horizontal scaling of stateless services with persistent data in managed databases

### Design Principles

#### 1. **Separation of Concerns**
Each layer of the application has a single responsibility:
- **Presentation Layer:** User interface and API endpoints
- **Business Logic Layer:** Agent orchestration and workflow rules
- **Data Access Layer:** Database operations and caching
- **Integration Layer:** External service connections (Foxit, AI, ERP)

#### 2. **Event-Driven Processing**
Invoice processing is inherently asynchronous. The system uses:
- **Task Queue (Celery + Redis):** Background processing for CPU-intensive operations
- **Webhooks:** Real-time notifications for invoice status changes
- **Polling Fallback:** For systems that cannot receive webhooks

#### 3. **Plugin Architecture**
The agent system is designed for extensibility:
- **Base Agent Interface:** All agents implement `BaseAgent` with `process()` method
- **Agent Registry:** Dynamic registration and discovery of available agents
- **Pipeline Configuration:** YAML-based workflow definitions

#### 4. **API-First Design**
All functionality is exposed via REST APIs:
- **OpenAPI Specification:** Auto-generated documentation at `/docs`
- **Consistent Response Format:** Standardized error handling and pagination
- **Versioned Endpoints:** API versioning for backward compatibility

#### 5. **Security by Default**
Security is built into every layer:
- **Authentication:** JWT tokens with refresh mechanism
- **Authorization:** Role-based access control (RBAC)
- **Encryption:** TLS for transit, AES-256 for sensitive data at rest
- **Audit Trail:** Complete logging of all user actions

### Technology Stack Overview

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS | User interface |
| **Backend API** | FastAPI (Python 3.12) | REST API endpoints |
| **Agent Framework** | LangChain, PydanticAI | AI agent orchestration |
| **Task Queue** | Celery 5.3, Redis | Background processing |
| **Database** | PostgreSQL 16 | Persistent storage |
| **Cache** | Redis 7 | Session storage, caching |
| **PDF Processing** | Foxit PDF SDK | Text extraction, OCR |
| **AI Models** | GPT-4o (GitHub/OpenAI/Anthropic) | Data extraction, reasoning |
| **Container Runtime** | Docker, Kubernetes | Deployment & orchestration |

### Key Components

The system consists of seven primary components:

1. **Frontend (Next.js):** React-based SPA for invoice upload, review, and approval
2. **Backend API (FastAPI):** RESTful API handling authentication, business logic, and data access
3. **Agent Orchestrator:** Coordinates AI agents through the invoice processing pipeline
4. **Task Workers (Celery):** Execute background tasks (extraction, matching, notifications)
5. **Task Scheduler (Celery Beat):** Periodic tasks (daily reports, archival, cleanup)
6. **Database (PostgreSQL):** Stores invoices, vendors, POs, approvals, and audit logs
7. **Cache/Queue (Redis):** Task queue backend, session storage, and result caching

---

*Continue to [Section 2: High-Level System Diagram](./02_System_Diagram.md)*
