# SmartAP Implementation Plan

## Intelligent Invoice & Accounts Payable (AP) Automation Hub

**Document Version:** 1.0  
**Created:** January 7, 2026  
**Status:** Draft  
**Priority:** High

---

## Executive Summary

This implementation plan consolidates the two initial requirement recommendations into a unified, actionable roadmap for building the **Intelligent Invoice & Accounts Payable Automation Hub**. The system will leverage Foxit PDF Services combined with Agentic AI to automate invoice processing, reduce manual data entry, and provide enterprise-grade auditability.

### Core Value Proposition
- Eliminate manual invoice processing while maintaining auditability and control
- Target Users: Finance & Operations (SME → Mid-Market)
- Deployment: Cloud or On-Premises

---

## 1. Business & Technical Objectives

### Business Objectives
| Objective | Target |
|-----------|--------|
| Invoice processing time reduction | 60–80% |
| Straight-through processing (STP) rate | >90% for clean invoices |
| Fraud/duplicate detection | Before payment approval |
| Audit compliance | Full audit trail |

### Technical Objectives
| Objective | Description |
|-----------|-------------|
| Foxit Integration | Demonstrate Foxit PDF Services + AI as production workflow |
| Architecture | Agentic AI (not monolithic prompt) |
| LLM Flexibility | Provider-agnostic (GPT-4o, Claude, etc.) |
| Deployment | On-prem or cloud deployable |

### MVP Success Metrics
| Metric | Target Goal |
|--------|-------------|
| Extraction Accuracy | >95% for header fields |
| Processing Speed | <10 seconds per page (OCR + AI) |
| Touchless Ratio | 80% of invoices processed without human intervention |

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                       │
├────────────────────────────────────────────────────────────────┤
│  Web Portal (React/Next.js)  │  Foxit PDF Web Viewer (embedded) │
└──────────────────────────────┴─────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────┐
│                         BACKEND API LAYER                       │
├────────────────────────────────────────────────────────────────┤
│  FastAPI                                             │
│  • Authentication & RBAC                                        │
│  • Workflow Orchestration                                       │
│  • Audit Logging                                                │
│  • API Gateway                                                  │
└────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────┐
│                    AI ORCHESTRATION LAYER                       │
├────────────────────────────────────────────────────────────────┤
│  Agent Router / State Machine (LangGraph / PydanticAI)          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Extraction  │  │  Matching   │  │    Risk     │             │
│  │   Agent     │  │   Agent     │  │   Agent     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└────────────────────────────────────────────────────────────────┘
                     │                           │
        ┌────────────▼────────────┐  ┌──────────▼──────────┐
        │      FOXIT SERVICES     │  │   BUSINESS DATA     │
        ├─────────────────────────┤  ├─────────────────────┤
        │ • Maestro OCR Server    │  │ • PO Database       │
        │ • PDF Extraction SDK    │  │ • Vendor Database   │
        │ • PDF Flattening        │  │ • Payment System    │
        │ • eSign API             │  │ • ERP Connectors    │
        │ • Web Viewer SDK        │  │                     │
        └─────────────────────────┘  └─────────────────────┘
```

---

## 3. Core Functional Modules

### 3.1 Invoice Ingestion & Preprocessing

| Feature | Description |
|---------|-------------|
| PDF Upload | Digital or scanned invoice upload |
| Email Ingestion | invoice@company.com inbox monitoring |
| Batch Upload | ZIP file support for bulk processing |

**Foxit API Integration:**
- OCR for scanned invoices (Maestro OCR Server/SDK)
- PDF normalization and page/layout analysis
- Document structure identification (headers vs. line items)

**Outputs:**
- Machine-readable PDF
- OCR confidence score
- Immutable document hash (duplication detection)

---

### 3.2 AI Agent 1 — Invoice Extraction Agent

**Role:** Extract structured invoice data from PDFs without templates

**Inputs:**
- OCR'd PDF with text coordinates
- Vendor master data (optional)

**Output Schema:**
```json
{
  "invoice_number": "INV-2025-0312",
  "vendor": "ABC Supplies Ltd",
  "invoice_date": "2026-01-12",
  "currency": "EUR",
  "line_items": [
    { "description": "Laptop", "qty": 5, "unit_price": 850 }
  ],
  "subtotal": 4250,
  "tax": 850,
  "total": 5100
}
```

**AI Techniques:**
- Zero-shot structured extraction with schema-based prompts
- Self-consistency checks (sum of line items vs. total)
- Confidence scoring per field

**Human-in-the-Loop:**
- Foxit Web Viewer shows extracted fields side-by-side with PDF
- Editable fields before confirmation
- Visual highlighting for low-confidence areas (<85%)

---

### 3.3 AI Agent 2 — PO Matching & Reconciliation Agent (Auditor Agent)

**Role:** Match invoice data against Purchase Orders and receipts (3-Way Matching)

**Matching Logic:**
- Exact match: PO number
- Fuzzy match: vendor + amount + date
- Line-item similarity scoring

**Output Schema:**
```json
{
  "po_id": "PO-88421",
  "match_score": 0.93,
  "discrepancies": [
    {
      "type": "PRICE",
      "item": "Laptop",
      "invoice_price": 850,
      "po_price": 820
    }
  ]
}
```

**Business Rules:**
- Tolerance thresholds (e.g., ±2%)
- Partial delivery handling
- Multi-PO invoice support

---

### 3.4 AI Agent 3 — Risk, Fraud & Duplication Agent

**Role:** Flag anomalies before payment approval

**Detection Signals:**
- Duplicate invoice number + vendor
- Similar totals across different invoices
- Unusual price deviations
- Vendor risk profile changes
- Bank account spoofing detection

**AI Techniques:**
- Embedding-based similarity search
- Rule + AI hybrid scoring
- Historical vendor behavior analysis

**Output Schema:**
```json
{
  "risk_level": "MEDIUM",
  "flags": ["DUPLICATE_LIKE", "PRICE_SPIKE"],
  "recommended_action": "MANUAL_REVIEW"
}
```

---

### 3.5 Approval Workflow & Payment Preparation

**Workflow States:**
```
INGESTED → EXTRACTED → MATCHED → RISK_REVIEW → APPROVED → READY_FOR_PAYMENT → ARCHIVED
```

**Features:**
- Role-based approvals (AP Clerk, Manager, Auditor)
- Escalation rules and SLA timers
- eSign integration for high-value invoices (>$5,000 threshold)

**Foxit API Usage:**
- PDF flattening after approval (tamper-proof archival)
- Audit page appended to PDF (who approved, when)
- Optional eSign for formal authorization

---

## 4. Data Model

| Entity | Description |
|--------|-------------|
| Invoice | Canonical invoice record with extracted data |
| InvoiceLineItem | Normalized line items from invoices |
| PurchaseOrder | PO master records for matching |
| Vendor | Vendor profile and risk history |
| RiskAssessment | AI-generated risk reports |
| AuditLog | Immutable action trail |

---

## 5. Security & Compliance Requirements

- **RBAC:** AP Clerk, Manager, Auditor roles
- **Audit Trail:** Full logging of who approved what, when
- **Document Integrity:** Immutable PDFs after approval
- **Data Privacy:** GDPR-ready data handling
- **Deployment:** Optional on-premises deployment support

---

## 6. Implementation Phases

### Phase 1: Core Intake Engine (Weeks 1-4)
**Goal:** Convert unstructured PDF pixels into structured, clean data

| Task | Deliverable |
|------|-------------|
| Foxit OCR Integration | Maestro OCR Server setup |
| Data Extraction Pipeline | SDK integration for document structure |
| AI Enhancement | Zero-shot extraction with LLM |
| Basic UI | CLI or Web Dropzone |

**Deliverable:** JSON representation of any uploaded invoice

---

### Phase 2: Multi-Agent Reasoning Layer (Weeks 5-8)
**Goal:** Move from "Reading" to "Thinking"

| Task | Deliverable |
|------|-------------|
| Extractor Agent | Line item mapping with coordinates |
| Auditor Agent | 3-Way PO matching implementation |
| Fraud Agent | Duplicate/spoofing detection |
| Agent Orchestration | LangGraph/PydanticAI integration |

**Deliverable:** 80% of invoices auto-processed

---

### Phase 3: Human-in-the-Loop UI (Weeks 9-12)
**Goal:** Professional interface for finance teams

| Task | Deliverable |
|------|-------------|
| Foxit Web SDK Integration | Embedded PDF viewer in React/Next.js |
| Visual Validation | Highlight uncertain areas on PDF |
| Correction Interface | Click-to-correct AI extractions |
| Audit Trail UI | Approval history and audit pages |

**Deliverable:** Production-ready exception handling interface

---

### Phase 4: Workflow & eSign Integration (Weeks 13-16)
**Goal:** Connect the hub to the rest of the business

| Task | Deliverable |
|------|-------------|
| eSign Integration | Foxit eSign for threshold approvals |
| ERP Connectors | QuickBooks, Xero, SAP adapters |
| PDF Flattening | Tamper-proof archival workflow |
| Payment System Integration | Ready-for-payment data export |

**Deliverable:** Drop-in AP automation system

---

### Phase 5: Open-Source Launch & Community Kit (Weeks 17-20)
**Goal:** Make it easy for others to adopt and contribute

| Task | Deliverable |
|------|-------------|
| GitHub Template | docker-compose.yml for one-command setup |
| Sample Data | 50 synthetic invoices (clean, messy, handwritten) |
| Documentation | Extensibility guide for custom agents |
| Helm Charts | Kubernetes deployment support |

**Deliverable:** Production-ready open-source release

---

## 7. Technology Stack (2026 Edition)

| Layer | Technology | Notes |
|-------|------------|-------|
| **Frontend** | Next.js 16+ (App Router) | Modern React framework with server components |
| **PDF Viewer** | Foxit Web SDK | Embedded viewer for visual validation |
| **Backend API** | Python (FastAPI) | Best for AI library integration |
| **AI Framework** | LangChain / PydanticAI | Agent development and prompt management |
| **LLM Provider** | OpenAI or Anthropic | Reasoning and extraction capabilities |
| **Vector Storage** | Pinecone | Document vector storage for RAG |
| **Orchestration** | Temporal or LangGraph | Long-running agentic workflows (e.g., eSign waits) |
| **PDF Services** | Foxit Maestro OCR, PDF SDK, eSign API | Core document processing |
| **Database** | PostgreSQL | Transactional data storage |
| **Containerization** | Docker, Kubernetes | Deployment and scaling |

---

## 8. Recommended Next Steps

1. **Agent Interaction Diagram & State Machine** — Define agent communication flows
2. **AI Extraction Prompt & Validation Strategy** — Create prompt templates and validation rules
3. **Foxit API Integration Code Skeleton** — Build foundational integration layer
4. **Demo Dataset & Success Metrics Dashboard** — Prepare test data and measurement framework

---

## 9. Repository Information

**Recommended Name:** `foxit-ap-automation-hub`

**Tagline:** *"An open-source, AI-powered Accounts Payable system built on Foxit PDF Services."*

---

## Appendix: Workflow State Diagram

```
                    ┌─────────────┐
                    │   INGESTED  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  EXTRACTED  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
              ┌─────│   MATCHED   │─────┐
              │     └─────────────┘     │
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │ RISK_REVIEW │          │   APPROVED  │
       └──────┬──────┘          └──────┬──────┘
              │                        │
              └────────────┬───────────┘
                           │
                    ┌──────▼──────┐
                    │ READY_FOR   │
                    │  PAYMENT    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  ARCHIVED   │
                    └─────────────┘
```

---

*This implementation plan is based on the consolidated requirements from req1.txt and req2.txt.*
