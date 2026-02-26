# Data Flow Architecture

This document describes the data flow through the SmartAP invoice processing system.

## Overview

SmartAP processes invoices through a multi-stage pipeline, from document ingestion to ERP synchronization. Each stage transforms and enriches the data while maintaining audit trails.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SmartAP Data Flow                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │  Ingest │──▶│ Extract │──▶│  Match  │──▶│ Approve │──▶│  Sync   │       │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘       │
│       │             │             │             │             │              │
│       ▼             ▼             ▼             ▼             ▼              │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│  │ Storage │   │Database │   │Database │   │Database │   │   ERP   │       │
│  │  (S3)   │   │(Postgres)│  │(Postgres)│  │(Postgres)│  │ System  │       │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘       │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Document Ingestion

### Input Sources

| Source | Format | Method |
|--------|--------|--------|
| Email | PDF, Image | IMAP polling |
| API Upload | PDF, Image | REST endpoint |
| S3 Bucket | PDF, Image | S3 events |
| Manual | PDF, Image | Web upload |

### Processing Flow

```python
async def ingest_document(source: DocumentSource) -> Document:
    """
    1. Receive document from source
    2. Validate file type and size
    3. Extract metadata
    4. Store in blob storage
    5. Create database record
    6. Queue for processing
    """
    # Validate
    validate_document(source.file)
    
    # Store original
    blob_url = await storage.upload(
        file=source.file,
        path=f"invoices/{organization_id}/{document_id}"
    )
    
    # Create record
    document = await db.documents.create(
        id=document_id,
        organization_id=organization_id,
        blob_url=blob_url,
        filename=source.filename,
        mime_type=source.mime_type,
        size_bytes=source.size,
        status=DocumentStatus.PENDING
    )
    
    # Queue for processing
    await queue.publish("document.ingested", document_id)
    
    return document
```

### Data Model

```python
class Document(BaseModel):
    id: UUID
    organization_id: UUID
    blob_url: str
    filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

---

## Stage 2: Data Extraction

### Processing Flow

```python
async def extract_invoice_data(document_id: UUID) -> ExtractedData:
    """
    1. Load document from storage
    2. Convert to processable format
    3. Run OCR if needed
    4. Extract structured data via AI
    5. Validate extracted data
    6. Store results
    """
    # Load document
    document = await db.documents.get(document_id)
    pdf_bytes = await storage.download(document.blob_url)
    
    # Convert/OCR
    text = await pdf_processor.extract_text(pdf_bytes)
    if not text or is_scanned(pdf_bytes):
        text = await ocr_service.process(pdf_bytes)
    
    # AI extraction
    extraction_result = await extraction_agent.process(
        text=text,
        document_type="invoice"
    )
    
    # Validate
    validated_data = validate_extraction(extraction_result)
    
    # Store
    invoice = await db.invoices.create(
        document_id=document_id,
        vendor_name=validated_data.vendor_name,
        invoice_number=validated_data.invoice_number,
        invoice_date=validated_data.invoice_date,
        total_amount=validated_data.total_amount,
        # ... other fields
        extraction_confidence=extraction_result.confidence,
        status=InvoiceStatus.EXTRACTED
    )
    
    return invoice
```

### Extracted Data Fields

| Field | Type | Required | Source |
|-------|------|----------|--------|
| vendor_name | string | Yes | AI extraction |
| vendor_address | string | No | AI extraction |
| invoice_number | string | Yes | AI extraction |
| invoice_date | date | Yes | AI extraction |
| due_date | date | No | AI extraction |
| po_number | string | No | AI extraction |
| line_items | array | Yes | AI extraction |
| subtotal | decimal | No | AI extraction |
| tax_amount | decimal | No | AI extraction |
| total_amount | decimal | Yes | AI extraction |
| currency | string | Yes | AI extraction |
| payment_terms | string | No | AI extraction |

### Confidence Scoring

Each extracted field has an associated confidence score:

```python
class ExtractionConfidence(BaseModel):
    overall: float  # 0.0 - 1.0
    fields: Dict[str, float]  # Field-level confidence
    
    def needs_review(self) -> bool:
        return self.overall < 0.85 or any(
            score < 0.7 for score in self.fields.values()
        )
```

---

## Stage 3: PO Matching

### Matching Algorithm

```python
async def match_invoice_to_po(invoice_id: UUID) -> MatchResult:
    """
    1. Load invoice data
    2. Query potential POs
    3. Calculate match scores
    4. Select best match
    5. Identify discrepancies
    6. Store match result
    """
    invoice = await db.invoices.get(invoice_id)
    
    # Find candidate POs
    candidates = await db.purchase_orders.find(
        organization_id=invoice.organization_id,
        vendor_id=invoice.vendor_id,
        status=POStatus.OPEN,
        amount_range=(invoice.total_amount * 0.9, invoice.total_amount * 1.1)
    )
    
    # Score each candidate
    scored_matches = []
    for po in candidates:
        score = calculate_match_score(invoice, po)
        scored_matches.append((po, score))
    
    # Select best match
    best_match = max(scored_matches, key=lambda x: x[1], default=None)
    
    if best_match and best_match[1] > 0.8:
        # Create match record
        match = await db.matches.create(
            invoice_id=invoice_id,
            purchase_order_id=best_match[0].id,
            confidence=best_match[1],
            discrepancies=find_discrepancies(invoice, best_match[0])
        )
        
        # Update invoice status
        await db.invoices.update(
            invoice_id,
            status=InvoiceStatus.MATCHED,
            purchase_order_id=best_match[0].id
        )
        
        return match
    
    # No match found
    await db.invoices.update(
        invoice_id,
        status=InvoiceStatus.UNMATCHED
    )
    
    return None
```

### Match Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| PO number match | 0.30 | Exact or fuzzy match |
| Total amount | 0.25 | Within tolerance % |
| Vendor match | 0.20 | Vendor ID or name |
| Line items | 0.15 | Item descriptions |
| Date proximity | 0.10 | PO date vs invoice date |

### Discrepancy Types

```python
class DiscrepancyType(Enum):
    PRICE_MISMATCH = "price_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"
    MISSING_LINE_ITEM = "missing_line_item"
    EXTRA_LINE_ITEM = "extra_line_item"
    TAX_MISMATCH = "tax_mismatch"
    SHIPPING_MISMATCH = "shipping_mismatch"
```

---

## Stage 4: Risk Assessment

### Risk Scoring Flow

```python
async def assess_risk(invoice_id: UUID) -> RiskAssessment:
    """
    1. Load invoice and match data
    2. Check for duplicates
    3. Analyze vendor history
    4. Apply risk rules
    5. Calculate composite score
    6. Store assessment
    """
    invoice = await db.invoices.get(invoice_id)
    
    # Run risk checks
    risk_factors = []
    
    # Duplicate check
    duplicates = await check_duplicates(invoice)
    if duplicates:
        risk_factors.append(RiskFactor(
            type="duplicate",
            severity=0.9,
            details={"duplicates": [d.id for d in duplicates]}
        ))
    
    # Vendor analysis
    vendor_risk = await analyze_vendor(invoice.vendor_id)
    if vendor_risk.is_new:
        risk_factors.append(RiskFactor(
            type="new_vendor",
            severity=0.3,
            details=vendor_risk.details
        ))
    
    # Amount anomaly
    amount_risk = await check_amount_anomaly(invoice)
    if amount_risk:
        risk_factors.append(amount_risk)
    
    # Calculate composite score
    risk_score = calculate_composite_risk(risk_factors)
    
    # Store assessment
    assessment = await db.risk_assessments.create(
        invoice_id=invoice_id,
        risk_score=risk_score,
        risk_level=categorize_risk(risk_score),
        factors=risk_factors
    )
    
    return assessment
```

### Risk Levels

| Level | Score Range | Auto-Approve | Review Required |
|-------|-------------|--------------|-----------------|
| LOW | 0.0 - 0.3 | Yes* | No |
| MEDIUM | 0.3 - 0.6 | No | Optional |
| HIGH | 0.6 - 0.8 | No | Yes |
| CRITICAL | 0.8 - 1.0 | No | Yes + Audit |

*Subject to amount thresholds

---

## Stage 5: Approval Workflow

### Approval Flow

```python
async def route_for_approval(invoice_id: UUID) -> ApprovalWorkflow:
    """
    1. Load invoice and risk assessment
    2. Determine approval requirements
    3. Identify approvers
    4. Create workflow
    5. Send notifications
    """
    invoice = await db.invoices.get(invoice_id)
    risk = await db.risk_assessments.get_by_invoice(invoice_id)
    
    # Determine approval path
    approval_rules = await get_approval_rules(invoice.organization_id)
    required_approvals = determine_approvals(
        invoice=invoice,
        risk=risk,
        rules=approval_rules
    )
    
    # Create workflow
    workflow = await db.approval_workflows.create(
        invoice_id=invoice_id,
        required_approvals=required_approvals,
        status=WorkflowStatus.PENDING
    )
    
    # Notify approvers
    for approval in required_approvals:
        await notifications.send(
            user_id=approval.approver_id,
            type="approval_request",
            data={"invoice_id": invoice_id}
        )
    
    return workflow
```

### Approval Rules Engine

```yaml
# Example approval rules
rules:
  - name: "High Value Invoice"
    condition:
      amount_gte: 10000
    approvers:
      - role: finance_manager
      - role: department_head
    
  - name: "High Risk Invoice"
    condition:
      risk_level: ["HIGH", "CRITICAL"]
    approvers:
      - role: finance_director
      - role: compliance_officer

  - name: "New Vendor"
    condition:
      vendor_is_new: true
    approvers:
      - role: procurement_manager
```

---

## Stage 6: ERP Synchronization

### Sync Flow

```python
async def sync_to_erp(invoice_id: UUID) -> SyncResult:
    """
    1. Verify invoice is approved
    2. Transform to ERP format
    3. Send to ERP system
    4. Handle response
    5. Update records
    """
    invoice = await db.invoices.get(invoice_id)
    
    # Verify approval
    if invoice.status != InvoiceStatus.APPROVED:
        raise ValueError("Invoice not approved")
    
    # Transform data
    erp_payload = transform_to_erp_format(
        invoice=invoice,
        erp_type=organization.erp_type  # SAP, Oracle, NetSuite, etc.
    )
    
    # Send to ERP
    try:
        erp_response = await erp_connector.create_invoice(erp_payload)
        
        # Update with ERP reference
        await db.invoices.update(
            invoice_id,
            erp_id=erp_response.invoice_id,
            erp_status="synced",
            synced_at=datetime.utcnow()
        )
        
        return SyncResult(success=True, erp_id=erp_response.invoice_id)
        
    except ERPError as e:
        # Log error and mark for retry
        await db.sync_errors.create(
            invoice_id=invoice_id,
            error_type=e.type,
            error_message=str(e),
            retry_count=0
        )
        
        return SyncResult(success=False, error=str(e))
```

### Supported ERP Systems

| ERP | Protocol | Features |
|-----|----------|----------|
| SAP S/4HANA | RFC/BAPI | Full sync, attachments |
| Oracle ERP Cloud | REST API | Full sync |
| NetSuite | REST API | Full sync |
| Microsoft Dynamics | REST API | Full sync |
| QuickBooks | REST API | Basic sync |

---

## Event-Driven Architecture

### Event Types

```python
class EventType(Enum):
    # Document events
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    
    # Invoice events
    INVOICE_EXTRACTED = "invoice.extracted"
    INVOICE_MATCHED = "invoice.matched"
    INVOICE_UNMATCHED = "invoice.unmatched"
    
    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    
    # Sync events
    ERP_SYNC_STARTED = "erp.sync.started"
    ERP_SYNC_COMPLETED = "erp.sync.completed"
    ERP_SYNC_FAILED = "erp.sync.failed"
```

### Event Flow

```
Document Upload → document.uploaded
       │
       ▼
   Extraction → invoice.extracted
       │
       ▼
    Matching → invoice.matched / invoice.unmatched
       │
       ▼
 Risk Assessment → (internal, no event)
       │
       ▼
Approval Routing → approval.requested
       │
       ▼
  User Approval → approval.approved / approval.rejected
       │
       ▼
   ERP Sync → erp.sync.started → erp.sync.completed / erp.sync.failed
```

### Event Handlers

```python
@event_handler("invoice.extracted")
async def on_invoice_extracted(event: Event):
    """Trigger matching after extraction."""
    await match_invoice_to_po(event.invoice_id)

@event_handler("invoice.matched")
async def on_invoice_matched(event: Event):
    """Trigger risk assessment after matching."""
    await assess_risk(event.invoice_id)

@event_handler("approval.approved")
async def on_approval_approved(event: Event):
    """Check if all approvals complete, then sync."""
    workflow = await db.approval_workflows.get(event.workflow_id)
    if workflow.all_approved:
        await sync_to_erp(event.invoice_id)
```

---

## Data Retention

### Retention Policies

| Data Type | Retention Period | Archive Strategy |
|-----------|------------------|------------------|
| Documents | 7 years | Cold storage after 1 year |
| Invoices | 7 years | Keep in DB |
| Audit logs | 10 years | Archive after 2 years |
| Workflow history | 3 years | Archive after 1 year |
| Risk assessments | 7 years | Keep in DB |

### Archival Process

```python
async def archive_old_data():
    """Monthly archival job."""
    # Archive documents older than 1 year
    old_docs = await db.documents.find(
        created_at_lt=datetime.utcnow() - timedelta(days=365),
        archived=False
    )
    
    for doc in old_docs:
        # Move to cold storage
        await storage.move_to_cold_storage(doc.blob_url)
        await db.documents.update(doc.id, archived=True)
```

---

## API Data Flow

### REST API Response Flow

```
Client Request
     │
     ▼
┌─────────────────┐
│   API Gateway   │ ─── Rate Limiting, Auth Check
└─────────────────┘
     │
     ▼
┌─────────────────┐
│   Controller    │ ─── Request Validation
└─────────────────┘
     │
     ▼
┌─────────────────┐
│    Service      │ ─── Business Logic
└─────────────────┘
     │
     ▼
┌─────────────────┐
│   Repository    │ ─── Data Access
└─────────────────┘
     │
     ▼
┌─────────────────┐
│   Database      │ ─── PostgreSQL
└─────────────────┘
     │
     ▼
Response (JSON)
```

### WebSocket Real-time Updates

```python
# Server-side
@websocket("/ws/invoices/{organization_id}")
async def invoice_updates(websocket: WebSocket, organization_id: UUID):
    await websocket.accept()
    
    async for event in event_stream.subscribe(f"org.{organization_id}.*"):
        await websocket.send_json({
            "type": event.type,
            "data": event.data
        })

# Client receives real-time updates:
# {"type": "invoice.extracted", "data": {"id": "...", "status": "extracted"}}
# {"type": "invoice.matched", "data": {"id": "...", "status": "matched", "po_id": "..."}}
```

---

## Performance Considerations

### Caching Strategy

```python
# Multi-layer caching
class CacheStrategy:
    # L1: In-memory (process-local)
    local_cache = TTLCache(maxsize=1000, ttl=60)
    
    # L2: Redis (distributed)
    redis_cache = RedisCache(ttl=300)
    
    async def get(self, key: str) -> Optional[Any]:
        # Check L1
        if value := self.local_cache.get(key):
            return value
        
        # Check L2
        if value := await self.redis_cache.get(key):
            self.local_cache[key] = value
            return value
        
        return None
```

### Database Optimization

```sql
-- Key indexes for invoice queries
CREATE INDEX idx_invoices_org_status ON invoices(organization_id, status);
CREATE INDEX idx_invoices_vendor_date ON invoices(vendor_id, invoice_date);
CREATE INDEX idx_invoices_po ON invoices(purchase_order_id) WHERE purchase_order_id IS NOT NULL;

-- Partitioning by date for historical data
CREATE TABLE invoices_partitioned (
    LIKE invoices INCLUDING ALL
) PARTITION BY RANGE (created_at);
```
