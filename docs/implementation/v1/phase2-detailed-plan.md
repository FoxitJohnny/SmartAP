# Phase 2: Multi-Agent Reasoning Layer - Detailed Implementation Plan

**Duration:** 6-8 weeks  
**Goal:** Move from "Reading" to "Thinking" - Add intelligent matching, fraud detection, and agent orchestration

---

## Overview

Phase 2 transforms SmartAP from a simple extraction tool into an intelligent reasoning system. We'll add two new AI agents that work together with the extraction agent to validate invoices, match them against purchase orders, and detect potential fraud or duplicates.

---

## Sub-Phase 2.1: Data Models & Database (Week 1)

### Objectives
- Design and implement data models for POs, Vendors, and workflow state
- Set up database layer with SQLAlchemy ORM
- Create migration strategy and seed data

### Tasks

#### 2.1.1: Extend Data Models
**Files to create/modify:**
- `backend/src/models/purchase_order.py` - PO and line item models
- `backend/src/models/vendor.py` - Vendor profiles and risk history
- `backend/src/models/matching.py` - Matching results and discrepancies
- `backend/src/models/risk.py` - Risk assessment models
- `backend/src/models/__init__.py` - Update exports

**Data Structures:**
```python
# Purchase Order
- po_number: str
- vendor_id: str
- created_date: date
- expected_delivery: date
- status: POStatus (open, partially_received, closed)
- line_items: List[POLineItem]
- total_amount: Decimal

# Vendor
- vendor_id: str
- name: str
- tax_id: str
- risk_score: float (0-1)
- payment_history: List[PaymentRecord]
- fraud_flags: List[FraudFlag]

# MatchingResult
- invoice_id: str
- po_id: str
- match_score: float (0-1)
- match_type: MatchType (exact, fuzzy, manual)
- discrepancies: List[Discrepancy]

# RiskAssessment
- invoice_id: str
- risk_level: RiskLevel (low, medium, high, critical)
- flags: List[RiskFlag]
- recommended_action: str
```

#### 2.1.2: Database Setup
**Files to create:**
- `backend/src/db/__init__.py`
- `backend/src/db/database.py` - SQLAlchemy engine and session
- `backend/src/db/models.py` - ORM models for all entities
- `backend/src/db/repositories.py` - Data access layer

**Technologies:**
- SQLAlchemy 2.0+ (async)
- SQLite for development (PostgreSQL for production)
- Alembic for migrations

#### 2.1.3: Seed Data & Test Fixtures
**Files to create:**
- `backend/src/db/seed_data.py` - Sample POs and vendors
- `backend/tests/fixtures/` - Test data for unit tests

**Sample Data:**
- 10 vendors with varying risk profiles
- 20 purchase orders (open, closed, partial)
- 5 historical invoices for duplicate testing

**Deliverables:**
- ✅ Complete data model definitions
- ✅ Working database layer with CRUD operations
- ✅ Seed data script
- ✅ Unit tests for repositories

---

## Sub-Phase 2.2: PO Matching Agent (Weeks 2-3)

### Objectives
- Implement 3-way matching logic (Invoice ↔ PO ↔ Receipt)
- Add fuzzy matching for vendor names and line items
- Calculate match scores and identify discrepancies

### Tasks

#### 2.2.1: Matching Service Foundation
**Files to create:**
- `backend/src/services/matching_agent.py` - Core matching agent
- `backend/src/services/matching_utils.py` - Helper functions for fuzzy matching

**Core Algorithms:**
- **Exact Matching:** PO number lookup
- **Fuzzy Matching:** Vendor name similarity (Levenshtein distance)
- **Line Item Matching:** Description similarity + quantity/price comparison
- **Amount Tolerance:** Configurable threshold (±2% default)

#### 2.2.2: Matching Agent Implementation
**Agent Capabilities:**
```python
class POMatchingAgent:
    async def match_invoice(self, invoice: Invoice) -> MatchingResult:
        # 1. Find candidate POs
        candidates = await self._find_po_candidates(invoice)
        
        # 2. Score each candidate
        scored_matches = [
            await self._score_match(invoice, po) 
            for po in candidates
        ]
        
        # 3. Identify best match and discrepancies
        best_match = max(scored_matches, key=lambda x: x.score)
        discrepancies = await self._find_discrepancies(
            invoice, best_match.po
        )
        
        return MatchingResult(
            po_id=best_match.po.po_number,
            match_score=best_match.score,
            discrepancies=discrepancies
        )
```

**Matching Rules:**
- PO number exact match = 1.0 score
- Vendor name fuzzy match (>0.85 similarity) + amount within tolerance = 0.9 score
- Line item similarity + date proximity = 0.7-0.8 score

#### 2.2.3: Discrepancy Detection
**Discrepancy Types:**
- `PRICE_MISMATCH`: Invoice price ≠ PO price
- `QUANTITY_MISMATCH`: Invoice qty ≠ PO qty
- `MISSING_LINE_ITEM`: Item on PO but not on invoice
- `EXTRA_LINE_ITEM`: Item on invoice but not on PO
- `AMOUNT_TOLERANCE_EXCEEDED`: Total difference > threshold

#### 2.2.4: AI-Enhanced Matching
Use LLM for ambiguous cases:
- Resolve description mismatches ("Laptop Dell XPS" vs "XPS Laptop")
- Explain discrepancies in natural language
- Suggest manual review actions

**Deliverables:**
- ✅ Working PO matching agent with fuzzy logic
- ✅ Discrepancy detection and scoring
- ✅ Unit tests with various matching scenarios
- ✅ Integration tests with Phase 1 extraction

---

## Sub-Phase 2.3: Risk & Fraud Detection Agent (Weeks 4-5)

### Objectives
- Detect duplicate invoices using document similarity
- Identify vendor anomalies and spoofing attempts
- Flag unusual pricing or amount patterns

### Tasks

#### 2.3.1: Duplicate Detection
**Files to create:**
- `backend/src/services/risk_agent.py` - Main risk assessment agent
- `backend/src/services/duplicate_detector.py` - Duplicate detection logic

**Detection Methods:**
1. **Exact Duplicate:** File hash match
2. **Near Duplicate:** Invoice number + vendor + amount match
3. **Similarity Duplicate:** Embedding-based similarity (>0.95)

**Technologies:**
- Sentence Transformers for embeddings
- Cosine similarity for document comparison
- Redis/Vector DB for fast similarity search (optional)

#### 2.3.2: Vendor Validation
**Validation Checks:**
- Vendor exists in master database
- Tax ID matches vendor record
- Bank account matches vendor record (if present)
- Historical payment patterns are normal

**Risk Signals:**
- New vendor (first invoice)
- Changed bank account
- Unusual payment terms
- Amount significantly higher than average

#### 2.3.3: Anomaly Detection
**Price Anomaly Detection:**
```python
# Compare against historical prices for same item
def detect_price_spike(invoice_item: InvoiceLineItem) -> bool:
    historical_prices = get_historical_prices(
        vendor_id=invoice.vendor_id,
        item_description=invoice_item.description
    )
    
    avg_price = mean(historical_prices)
    std_dev = stdev(historical_prices)
    
    # Flag if price > 2 standard deviations
    return invoice_item.unit_price > (avg_price + 2 * std_dev)
```

**Amount Anomaly Detection:**
- Compare against vendor's typical invoice amounts
- Flag amounts >3x the vendor's average
- Flag round numbers (potential fraud indicator)

#### 2.3.4: Risk Scoring
**Risk Score Calculation:**
```python
risk_score = weighted_sum([
    (duplicate_score, 0.4),      # 40% weight
    (vendor_risk_score, 0.3),    # 30% weight
    (price_anomaly_score, 0.2),  # 20% weight
    (amount_anomaly_score, 0.1)  # 10% weight
])

risk_level = classify_risk(risk_score)
# LOW: 0-0.3
# MEDIUM: 0.3-0.6
# HIGH: 0.6-0.8
# CRITICAL: 0.8-1.0
```

**Deliverables:**
- ✅ Duplicate detection with multiple strategies
- ✅ Vendor validation and risk profiling
- ✅ Price and amount anomaly detection
- ✅ Risk scoring and classification
- ✅ Unit tests for all detection logic

---

## Sub-Phase 2.4: Agent Orchestration (Week 6)

### Objectives
- Coordinate execution of all three agents
- Implement sequential workflow with state management
- Handle agent communication and decision-making

### Tasks

#### 2.4.1: Workflow Orchestrator
**Files to create:**
- `backend/src/orchestration/__init__.py`
- `backend/src/orchestration/workflow.py` - Main workflow coordinator
- `backend/src/orchestration/state.py` - Workflow state management

**Workflow Design:**
```
┌─────────────────┐
│  Invoice Upload │
└────────┬────────┘
         │
    ┌────▼────────────┐
    │ Extraction Agent│  (Phase 1)
    └────────┬────────┘
             │
        ┌────▼───────────┐
        │ Matching Agent │  (Phase 2)
        └────────┬───────┘
                 │
            ┌────▼──────────┐
            │  Risk Agent   │  (Phase 2)
            └────────┬──────┘
                     │
              ┌──────▼──────────┐
              │ Decision Engine │
              └──────┬──────────┘
                     │
        ┌────────────▼────────────┐
        │  Auto-approve / Review  │
        └─────────────────────────┘
```

#### 2.4.2: LangGraph Integration
**Technologies:**
- LangGraph for workflow orchestration
- State persistence across agent calls
- Conditional routing based on agent outputs

**Workflow Implementation:**
```python
from langgraph.graph import StateGraph, END

# Define workflow state
class InvoiceWorkflowState(TypedDict):
    invoice_id: str
    extraction_result: InvoiceExtractionResult
    matching_result: Optional[MatchingResult]
    risk_assessment: Optional[RiskAssessment]
    status: WorkflowStatus
    requires_review: bool

# Build graph
workflow = StateGraph(InvoiceWorkflowState)

workflow.add_node("extract", extraction_agent)
workflow.add_node("match", matching_agent)
workflow.add_node("assess_risk", risk_agent)
workflow.add_node("decide", decision_engine)

workflow.add_edge("extract", "match")
workflow.add_edge("match", "assess_risk")
workflow.add_edge("assess_risk", "decide")

# Conditional routing from decision
workflow.add_conditional_edges(
    "decide",
    lambda state: "review" if state["requires_review"] else "approved",
    {
        "approved": END,
        "review": "manual_review"
    }
)
```

#### 2.4.3: Decision Engine
**Auto-Approval Logic:**
```python
def should_auto_approve(state: InvoiceWorkflowState) -> bool:
    extraction_ok = state.extraction_result.confidence.overall > 0.85
    matching_ok = (
        state.matching_result.match_score > 0.9 and
        len(state.matching_result.discrepancies) == 0
    )
    risk_ok = state.risk_assessment.risk_level in [RiskLevel.LOW]
    
    return extraction_ok and matching_ok and risk_ok
```

**Review Routing:**
- HIGH/CRITICAL risk → Manager review
- MEDIUM risk + discrepancies → AP Clerk review
- LOW risk but low confidence → Data validation review

**Deliverables:**
- ✅ LangGraph workflow orchestrator
- ✅ State management and persistence
- ✅ Decision engine with business rules
- ✅ Integration tests for full workflow

---

## Sub-Phase 2.5: API & Testing (Weeks 7-8)

### Objectives
- Update API endpoints for full workflow
- Add endpoints for PO and vendor management
- Comprehensive testing and documentation

### Tasks

#### 2.5.1: New API Endpoints
**Files to modify:**
- `backend/src/api/routes.py` - Add new endpoints
- Create `backend/src/api/po_routes.py` - PO management
- Create `backend/src/api/vendor_routes.py` - Vendor management
- Create `backend/src/api/workflow_routes.py` - Workflow control

**Endpoints:**
```
POST   /api/v1/invoices/process-full     # Full workflow
GET    /api/v1/invoices/{id}/status      # Workflow status
POST   /api/v1/invoices/{id}/approve     # Manual approval
POST   /api/v1/invoices/{id}/reject      # Rejection

GET    /api/v1/pos                        # List POs
POST   /api/v1/pos                        # Create PO
GET    /api/v1/pos/{id}                   # Get PO details

GET    /api/v1/vendors                    # List vendors
POST   /api/v1/vendors                    # Create vendor
GET    /api/v1/vendors/{id}/risk-profile # Vendor risk history

GET    /api/v1/workflow/stats             # Processing statistics
```

#### 2.5.2: WebSocket Support
**Real-time Updates:**
- WebSocket endpoint for workflow progress
- Server-sent events for agent status
- Progress notifications during processing

**File to create:**
- `backend/src/api/websocket.py` - WebSocket handlers

#### 2.5.3: Testing Strategy
**Unit Tests:**
- All agent logic (extraction, matching, risk)
- Database repositories
- Utility functions

**Integration Tests:**
- Full workflow with various scenarios
- API endpoints with authentication
- Database transactions and rollbacks

**End-to-End Tests:**
- Upload invoice → Auto-approve flow
- Upload invoice → Manual review flow
- Duplicate detection flow
- Fraud detection flow

**Test Data:**
- 20+ test invoices (clean, messy, fraudulent)
- 30+ test POs (matched, unmatched, partial)
- 10+ vendor profiles

#### 2.5.4: Documentation
**Files to create/update:**
- `backend/docs/api.md` - API reference
- `backend/docs/architecture.md` - System architecture
- `backend/docs/workflow.md` - Workflow details
- `backend/README.md` - Update with Phase 2 features

**Deliverables:**
- ✅ Complete API endpoints for Phase 2
- ✅ WebSocket support for real-time updates
- ✅ 80%+ code coverage with tests
- ✅ API documentation and examples

---

## Sub-Phase 2.6: Performance & Deployment (Week 8)

### Objectives
- Optimize agent performance
- Add monitoring and observability
- Prepare for production deployment

### Tasks

#### 2.6.1: Performance Optimization
- Agent response caching
- Database query optimization
- Batch processing for multiple invoices
- Async/parallel agent execution where possible

#### 2.6.2: Monitoring & Observability
**Files to create:**
- `backend/src/monitoring/__init__.py`
- `backend/src/monitoring/metrics.py` - Prometheus metrics
- `backend/src/monitoring/tracing.py` - OpenTelemetry tracing

**Metrics to Track:**
- Invoice processing time (per stage)
- Agent execution time
- Match accuracy rate
- Fraud detection rate
- Auto-approval rate

#### 2.6.3: Deployment Configuration
**Files to create:**
- `backend/docker-compose.yml` - Multi-container setup
- `backend/Dockerfile` - Production container
- `backend/.env.production` - Production config template
- `backend/k8s/` - Kubernetes manifests (optional)

**Deliverables:**
- ✅ Performance optimizations applied
- ✅ Monitoring and metrics collection
- ✅ Production-ready Docker setup
- ✅ Deployment documentation

---

## Phase 2 Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Processing Time** | <30 seconds per invoice | Average workflow execution time |
| **Auto-Approval Rate** | 80% of invoices | % invoices that pass all agents without review |
| **Match Accuracy** | >95% correct PO matches | Manual validation of matching results |
| **Fraud Detection** | >99% duplicate catch rate | Test with known duplicate invoices |
| **False Positive Rate** | <5% | % of flagged invoices that are actually valid |
| **Code Coverage** | >80% | Unit + integration test coverage |

---

## Dependencies & Prerequisites

### Updated Requirements
Add to `backend/requirements.txt`:
```
# Agent Orchestration
langgraph>=0.2.0

# Database
sqlalchemy[asyncio]>=2.0.25
alembic>=1.13.0
aiosqlite>=0.19.0  # Dev
asyncpg>=0.29.0    # Production

# Fuzzy Matching & Similarity
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.25.0
sentence-transformers>=2.5.0

# Vector Storage (optional)
chromadb>=0.4.22  # or pinecone-client

# Monitoring
prometheus-client>=0.20.0
opentelemetry-instrumentation-fastapi>=0.42b0
```

### Environment Variables
Add to `.env`:
```
# Database
DATABASE_URL=sqlite+aiosqlite:///./smartap.db
# or: postgresql+asyncpg://user:pass@localhost/smartap

# Matching Configuration
MATCH_CONFIDENCE_THRESHOLD=0.85
PRICE_TOLERANCE_PERCENT=2.0
AMOUNT_ANOMALY_THRESHOLD=3.0

# Risk Configuration
DUPLICATE_SIMILARITY_THRESHOLD=0.95
VENDOR_RISK_WEIGHT=0.3
PRICE_ANOMALY_WEIGHT=0.2
```

---

## Risk Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| **Agent latency** | Slow processing | Implement caching, optimize prompts, parallel execution |
| **False positives** | Too many manual reviews | Tune thresholds, improve training data, add feedback loop |
| **Database performance** | Slow queries | Add indexes, use connection pooling, optimize queries |
| **Integration complexity** | Bugs in orchestration | Comprehensive testing, logging, state debugging tools |

---

## Timeline Summary

```
Week 1: Data Models & Database ████████████░░░░░░░░░░░░
Week 2: PO Matching Agent     ░░░░░░░░░░░░████████████░░
Week 3: PO Matching Testing   ░░░░░░░░░░░░░░░░░░░░████░░
Week 4: Risk Agent            ░░░░░░░░░░░░░░░░░░░░░░████
Week 5: Risk Agent Testing    ░░░░░░░░░░░░░░░░░░░░░░░░██
Week 6: Orchestration         ░░░░░░░░░░░░░░░░░░░░░░░░██
Week 7: API & Testing         ░░░░░░░░░░░░░░░░░░░░░░░░██
Week 8: Performance & Deploy  ░░░░░░░░░░░░░░░░░░░░░░░░██
```

**Critical Path:** Extraction Agent (Phase 1) → Data Models → Matching Agent → Risk Agent → Orchestration

---

## Next Steps After Phase 2

Phase 3 will add:
- Human-in-the-Loop UI with Foxit Web SDK
- Visual validation and correction
- Approval workflow interface
- Dashboard and analytics

This detailed plan provides a clear roadmap for implementing Phase 2's multi-agent reasoning capabilities.
