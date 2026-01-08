# SmartAP Agent Orchestration Flow

**Section 4 of Architecture Documentation**

---

## Table of Contents

1. [Agent Pipeline Overview](#agent-pipeline-overview)
2. [Agent Descriptions](#agent-descriptions)
3. [Pipeline Execution Flow](#pipeline-execution-flow)
4. [Sequence Diagrams](#sequence-diagrams)
5. [Error Handling & Recovery](#error-handling--recovery)
6. [Agent Communication](#agent-communication)
7. [Configuration](#configuration)

---

## Agent Pipeline Overview

SmartAP uses a multi-agent architecture where specialized AI agents collaborate to process invoices through a configurable pipeline. Each agent has a single responsibility and passes its output to the next agent in the chain.

### Default Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Extractor  │───>│   Auditor   │───>│   Matcher   │───>│    Fraud    │───>│  Approval   │
│    Agent    │    │    Agent    │    │    Agent    │    │    Agent    │    │   Router    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
      │                  │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼                  ▼
 Extract data      Validate data      Match with PO     Detect fraud      Route approval
 from PDF          consistency        (if applicable)   & duplicates      to approver(s)
```

### Agent Characteristics

| Agent | Input | Output | Blocking | Retry |
|-------|-------|--------|----------|-------|
| Extractor | PDF text | Structured invoice data | Yes | 3x |
| Auditor | Invoice data | Validation results | Yes | 1x |
| Matcher | Invoice + PO list | Match results | No | 1x |
| Fraud | Invoice + History | Risk assessment | No | 1x |
| Approval Router | Invoice + Rules | Approval assignments | Yes | 1x |

---

## Agent Descriptions

### 1. Extractor Agent

**Purpose:** Extract structured invoice data from PDF text using AI.

**Input:**
```json
{
  "invoice_id": 12345,
  "pdf_text": "INVOICE\nInvoice #: INV-001\nDate: 2026-01-08\n...",
  "file_path": "/uploads/invoice_12345.pdf"
}
```

**Output:**
```json
{
  "invoice_number": "INV-001",
  "invoice_date": "2026-01-08",
  "due_date": "2026-02-07",
  "vendor": {
    "name": "Acme Corporation",
    "address": "123 Main St, New York, NY 10001",
    "tax_id": "12-3456789"
  },
  "line_items": [
    {
      "description": "Widget A",
      "quantity": 10,
      "unit_price": 25.00,
      "amount": 250.00
    }
  ],
  "subtotal": 250.00,
  "tax": 22.50,
  "total": 272.50,
  "payment_terms": "Net 30",
  "confidence_scores": {
    "invoice_number": 0.98,
    "total": 0.95,
    "vendor_name": 0.92
  }
}
```

**Implementation:**
```python
class ExtractorAgent(BaseAgent):
    """Extract structured data from invoice PDF text."""
    
    def __init__(self):
        self.ai_provider = get_ai_provider()
        self.prompt_template = load_prompt("extraction_prompt.txt")
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        prompt = self.prompt_template.format(pdf_text=input_data.pdf_text)
        
        response = await self.ai_provider.complete(
            prompt=prompt,
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for consistency
        )
        
        extracted_data = json.loads(response)
        validated_data = InvoiceExtraction.model_validate(extracted_data)
        
        return AgentOutput(
            success=True,
            data=validated_data.model_dump(),
            confidence=self._calculate_overall_confidence(validated_data),
        )
```

---

### 2. Auditor Agent

**Purpose:** Validate extracted data for consistency and completeness.

**Validation Checks:**
- ✅ Line items sum to subtotal
- ✅ Subtotal + tax = total
- ✅ Invoice date is not in future
- ✅ Due date is after invoice date
- ✅ Required fields are present
- ✅ Tax calculation is correct (within tolerance)

**Input:**
```json
{
  "invoice_id": 12345,
  "extracted_data": { /* Extractor output */ }
}
```

**Output:**
```json
{
  "is_valid": true,
  "validation_results": [
    {"check": "line_items_sum", "passed": true, "message": "Line items sum correctly"},
    {"check": "tax_calculation", "passed": true, "message": "Tax within 1% tolerance"},
    {"check": "date_validity", "passed": true, "message": "Dates are valid"},
    {"check": "required_fields", "passed": true, "message": "All required fields present"}
  ],
  "corrections": [],
  "warnings": [
    {"field": "vendor_address", "message": "Address may be incomplete"}
  ]
}
```

**Implementation:**
```python
class AuditorAgent(BaseAgent):
    """Validate extracted invoice data."""
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        data = input_data.extracted_data
        results = []
        corrections = []
        
        # Check 1: Line items sum
        line_total = sum(item["amount"] for item in data["line_items"])
        subtotal_match = abs(line_total - data["subtotal"]) < 0.01
        results.append({
            "check": "line_items_sum",
            "passed": subtotal_match,
            "expected": line_total,
            "actual": data["subtotal"],
        })
        
        if not subtotal_match:
            corrections.append({
                "field": "subtotal",
                "old_value": data["subtotal"],
                "new_value": line_total,
            })
        
        # Check 2: Tax calculation
        expected_total = data["subtotal"] + data["tax"]
        total_match = abs(expected_total - data["total"]) < 0.01
        results.append({
            "check": "total_calculation",
            "passed": total_match,
        })
        
        # ... more validation checks
        
        return AgentOutput(
            success=all(r["passed"] for r in results),
            data={
                "is_valid": all(r["passed"] for r in results),
                "validation_results": results,
                "corrections": corrections,
            },
        )
```

---

### 3. Matcher Agent

**Purpose:** Match invoice with existing purchase orders using algorithmic and AI-based matching.

**Matching Strategy:**
1. **Exact Match:** PO number in invoice matches database
2. **Fuzzy Match:** Vendor name + amount range + date proximity
3. **AI Match:** Use AI to find semantic matches

**Input:**
```json
{
  "invoice_id": 12345,
  "invoice_data": { /* Validated invoice */ },
  "candidate_pos": [ /* List of potential POs */ ]
}
```

**Output:**
```json
{
  "match_found": true,
  "matched_po_id": 6789,
  "match_confidence": 0.95,
  "match_type": "exact",
  "line_item_matches": [
    {
      "invoice_line": 1,
      "po_line": 1,
      "description_match": 0.92,
      "quantity_match": true,
      "price_variance": 0.00
    }
  ],
  "discrepancies": [],
  "requires_review": false
}
```

**Implementation:**
```python
class MatcherAgent(BaseAgent):
    """Match invoices with purchase orders."""
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        invoice = input_data.invoice_data
        candidates = input_data.candidate_pos
        
        # Strategy 1: Exact PO number match
        if invoice.get("po_number"):
            exact_match = self._find_exact_match(invoice["po_number"], candidates)
            if exact_match:
                return self._build_match_result(exact_match, "exact", 1.0)
        
        # Strategy 2: Fuzzy matching
        fuzzy_matches = self._fuzzy_match(invoice, candidates)
        if fuzzy_matches:
            best_match = max(fuzzy_matches, key=lambda m: m["score"])
            if best_match["score"] > 0.85:
                return self._build_match_result(best_match, "fuzzy", best_match["score"])
        
        # Strategy 3: AI-based matching
        ai_match = await self._ai_match(invoice, candidates)
        if ai_match and ai_match["confidence"] > 0.80:
            return self._build_match_result(ai_match, "ai", ai_match["confidence"])
        
        return AgentOutput(
            success=True,
            data={"match_found": False, "requires_review": True},
        )
```

---

### 4. Fraud Agent

**Purpose:** Detect potential fraud, duplicates, and anomalies.

**Detection Strategies:**
- 🔍 **Duplicate Detection:** Same invoice number, amount, or hash
- 🔍 **Vendor Validation:** Unknown or flagged vendors
- 🔍 **Amount Anomaly:** Unusual amounts for vendor/category
- 🔍 **Pattern Analysis:** Frequency, timing, round numbers
- 🔍 **Bank Account Changes:** Vendor payment info changes

**Input:**
```json
{
  "invoice_id": 12345,
  "invoice_data": { /* Invoice details */ },
  "vendor_history": { /* Historical invoices from vendor */ },
  "global_context": { /* Organization-wide patterns */ }
}
```

**Output:**
```json
{
  "risk_score": 0.15,
  "risk_level": "low",
  "flags": [],
  "duplicate_check": {
    "is_duplicate": false,
    "similar_invoices": []
  },
  "vendor_check": {
    "is_approved_vendor": true,
    "vendor_risk_score": 0.1
  },
  "amount_check": {
    "is_anomaly": false,
    "typical_range": [100, 5000],
    "current_amount": 272.50
  },
  "recommendations": []
}
```

**Implementation:**
```python
class FraudAgent(BaseAgent):
    """Detect fraud and anomalies in invoices."""
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        invoice = input_data.invoice_data
        flags = []
        risk_score = 0.0
        
        # Check 1: Duplicate detection
        duplicates = await self._check_duplicates(invoice)
        if duplicates:
            flags.append({"type": "duplicate", "severity": "high", "details": duplicates})
            risk_score += 0.5
        
        # Check 2: Vendor validation
        vendor_check = await self._validate_vendor(invoice["vendor"])
        if not vendor_check["is_approved"]:
            flags.append({"type": "unknown_vendor", "severity": "medium"})
            risk_score += 0.2
        
        # Check 3: Amount anomaly
        if self._is_amount_anomaly(invoice, input_data.vendor_history):
            flags.append({"type": "amount_anomaly", "severity": "medium"})
            risk_score += 0.15
        
        # Check 4: Round number detection
        if self._is_suspicious_round_number(invoice["total"]):
            flags.append({"type": "round_number", "severity": "low"})
            risk_score += 0.05
        
        risk_level = self._calculate_risk_level(risk_score)
        
        return AgentOutput(
            success=True,
            data={
                "risk_score": min(risk_score, 1.0),
                "risk_level": risk_level,
                "flags": flags,
                "requires_review": risk_level in ["medium", "high"],
            },
        )
```

---

### 5. Approval Router Agent

**Purpose:** Route invoices to appropriate approvers based on rules.

**Routing Rules:**
- 📋 **Amount Thresholds:** Different approvers for different amounts
- 📋 **Department:** Route to department manager
- 📋 **Vendor Category:** Special approval for new vendors
- 📋 **Exception Handling:** Escalation for flagged invoices

**Input:**
```json
{
  "invoice_id": 12345,
  "invoice_data": { /* Invoice details */ },
  "match_result": { /* PO match result */ },
  "fraud_result": { /* Fraud check result */ },
  "approval_rules": [ /* Configured rules */ ]
}
```

**Output:**
```json
{
  "approval_chain": [
    {
      "level": 1,
      "approver_id": 101,
      "approver_name": "John Manager",
      "reason": "Amount under $1,000 - Department Manager",
      "required": true
    }
  ],
  "auto_approved": false,
  "escalation_required": false,
  "estimated_completion": "2026-01-10T17:00:00Z"
}
```

**Implementation:**
```python
class ApprovalRouterAgent(BaseAgent):
    """Route invoices to appropriate approvers."""
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        invoice = input_data.invoice_data
        rules = input_data.approval_rules
        fraud_result = input_data.fraud_result
        
        approval_chain = []
        
        # Check for auto-approval eligibility
        if self._can_auto_approve(invoice, fraud_result):
            return AgentOutput(
                success=True,
                data={"auto_approved": True, "approval_chain": []},
            )
        
        # Build approval chain based on rules
        for rule in sorted(rules, key=lambda r: r["priority"]):
            if self._rule_matches(rule, invoice, fraud_result):
                approver = await self._get_approver(rule)
                approval_chain.append({
                    "level": len(approval_chain) + 1,
                    "approver_id": approver["id"],
                    "approver_name": approver["name"],
                    "reason": rule["description"],
                    "required": rule.get("required", True),
                })
                
                if not rule.get("continue_chain", False):
                    break
        
        # Check for escalation
        escalation_required = fraud_result["risk_level"] == "high"
        if escalation_required:
            approval_chain.append(self._get_escalation_approver())
        
        return AgentOutput(
            success=True,
            data={
                "approval_chain": approval_chain,
                "auto_approved": False,
                "escalation_required": escalation_required,
            },
        )
```

---

## Pipeline Execution Flow

### State Machine

```
                                    ┌─────────────────┐
                                    │    UPLOADED     │
                                    │   (Initial)     │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │   EXTRACTING    │
                              ┌────>│  (Extractor)    │<────┐
                              │     └────────┬────────┘     │
                              │              │              │
                           Retry          Success        Retry
                              │              ▼              │
                              │     ┌─────────────────┐     │
                              └─────│   VALIDATING    │─────┘
                                    │   (Auditor)     │
                                    └────────┬────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              │                             │
                           Valid                        Invalid
                              │                             │
                              ▼                             ▼
                     ┌─────────────────┐          ┌─────────────────┐
                     │    MATCHING     │          │ NEEDS_CORRECTION│
                     │   (Matcher)     │          │   (Manual)      │
                     └────────┬────────┘          └─────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ FRAUD_CHECKING  │
                     │  (Fraud Agent)  │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │    ROUTING      │
                     │(Approval Router)│
                     └────────┬────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
          Auto-Approve                  Needs Approval
               │                             │
               ▼                             ▼
      ┌─────────────────┐          ┌─────────────────┐
      │    APPROVED     │          │PENDING_APPROVAL │
      │    (Final)      │          │   (Waiting)     │
      └─────────────────┘          └────────┬────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                          Approved                    Rejected
                              │                           │
                              ▼                           ▼
                     ┌─────────────────┐        ┌─────────────────┐
                     │    APPROVED     │        │    REJECTED     │
                     │    (Final)      │        │    (Final)      │
                     └─────────────────┘        └─────────────────┘
```

---

## Sequence Diagrams

### Complete Invoice Processing

```
┌──────┐ ┌────────┐ ┌───────┐ ┌────────┐ ┌───────────┐ ┌───────┐ ┌────────┐ ┌──────┐
│Client│ │Frontend│ │Backend│ │ Worker │ │ Extractor │ │Auditor│ │Matcher │ │ DB   │
└──┬───┘ └───┬────┘ └───┬───┘ └───┬────┘ └─────┬─────┘ └───┬───┘ └───┬────┘ └──┬───┘
   │         │          │         │            │           │         │         │
   │ Upload  │          │         │            │           │         │         │
   │────────>│          │         │            │           │         │         │
   │         │ POST     │         │            │           │         │         │
   │         │ /upload  │         │            │           │         │         │
   │         │─────────>│         │            │           │         │         │
   │         │          │ Save    │            │           │         │         │
   │         │          │────────────────────────────────────────────────────>│
   │         │          │         │            │           │         │         │
   │         │          │ Queue   │            │           │         │         │
   │         │          │─────────>            │           │         │         │
   │         │          │         │            │           │         │         │
   │         │ 202      │         │            │           │         │         │
   │         │<─────────│         │            │           │         │         │
   │ Pending │          │         │            │           │         │         │
   │<────────│          │         │            │           │         │         │
   │         │          │         │ Extract    │           │         │         │
   │         │          │         │───────────>│           │         │         │
   │         │          │         │            │ Foxit     │         │         │
   │         │          │         │            │──────────>│         │         │
   │         │          │         │            │<──────────│         │         │
   │         │          │         │            │ AI Call   │         │         │
   │         │          │         │            │──────────>│         │         │
   │         │          │         │            │<──────────│         │         │
   │         │          │         │<───────────│           │         │         │
   │         │          │         │            │           │         │         │
   │         │          │         │ Validate   │           │         │         │
   │         │          │         │────────────────────────>         │         │
   │         │          │         │<────────────────────────         │         │
   │         │          │         │            │           │         │         │
   │         │          │         │ Match PO   │           │         │         │
   │         │          │         │────────────────────────────────>│         │
   │         │          │         │<────────────────────────────────│         │
   │         │          │         │            │           │         │         │
   │         │          │         │ Update     │           │         │         │
   │         │          │         │──────────────────────────────────────────>│
   │         │          │         │            │           │         │         │
   │ Poll    │          │         │            │           │         │         │
   │────────>│          │         │            │           │         │         │
   │         │ GET      │         │            │           │         │         │
   │         │─────────>│         │            │           │         │         │
   │         │          │ Fetch   │            │           │         │         │
   │         │          │────────────────────────────────────────────────────>│
   │         │          │<────────────────────────────────────────────────────│
   │         │<─────────│         │            │           │         │         │
   │ Results │          │         │            │           │         │         │
   │<────────│          │         │            │           │         │         │
```

---

## Error Handling & Recovery

### Retry Policy

```python
RETRY_CONFIG = {
    "extractor": {
        "max_retries": 3,
        "backoff": "exponential",  # 60s, 120s, 240s
        "on_failure": "mark_failed",
    },
    "auditor": {
        "max_retries": 1,
        "backoff": "fixed",
        "on_failure": "mark_needs_review",
    },
    "matcher": {
        "max_retries": 1,
        "backoff": "fixed",
        "on_failure": "skip",  # Non-blocking
    },
    "fraud": {
        "max_retries": 1,
        "backoff": "fixed",
        "on_failure": "mark_high_risk",  # Conservative default
    },
    "approval_router": {
        "max_retries": 1,
        "backoff": "fixed",
        "on_failure": "escalate",
    },
}
```

### Error Recovery Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Error Handling Flow                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Agent Error ──> Retry? ──Yes──> Wait ──> Retry Agent             │
│        │              │                                             │
│        │              No                                            │
│        │              │                                             │
│        │              ▼                                             │
│        │      Max Retries? ──Yes──> Execute Fallback               │
│        │              │                    │                        │
│        │              No                   ├─> Mark Failed          │
│        │              │                    ├─> Mark Needs Review    │
│        │              ▼                    ├─> Skip to Next Agent   │
│        │      Log Error                    └─> Escalate             │
│        │              │                                             │
│        │              ▼                                             │
│        └──────> Notify Admin                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Communication

### Message Format

```python
@dataclass
class AgentMessage:
    """Standard message format for inter-agent communication."""
    
    id: str                      # Unique message ID
    timestamp: datetime          # When message was created
    source_agent: str            # Sending agent name
    target_agent: str            # Receiving agent name
    invoice_id: int              # Associated invoice
    payload: dict                # Message data
    metadata: dict               # Additional context
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> "AgentMessage":
        return cls(**json.loads(json_str))
```

### Pipeline Context

```python
class PipelineContext:
    """Shared context passed through pipeline."""
    
    def __init__(self, invoice_id: int):
        self.invoice_id = invoice_id
        self.start_time = datetime.utcnow()
        self.results: dict[str, AgentOutput] = {}
        self.errors: list[dict] = []
        self.metadata: dict = {}
    
    def add_result(self, agent_name: str, output: AgentOutput):
        self.results[agent_name] = output
    
    def get_result(self, agent_name: str) -> Optional[AgentOutput]:
        return self.results.get(agent_name)
    
    def add_error(self, agent_name: str, error: Exception):
        self.errors.append({
            "agent": agent_name,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        })
```

---

## Configuration

### Pipeline Configuration (YAML)

```yaml
# config/pipeline.yaml
pipeline:
  name: default_invoice_pipeline
  version: 1.0
  
  agents:
    - name: extractor
      class: src.agents.ExtractorAgent
      enabled: true
      timeout: 60
      config:
        ai_provider: ${AI_PROVIDER}
        temperature: 0.1
    
    - name: auditor
      class: src.agents.AuditorAgent
      enabled: true
      timeout: 10
      config:
        tolerance: 0.01
        required_fields:
          - invoice_number
          - vendor_name
          - total
    
    - name: matcher
      class: src.agents.MatcherAgent
      enabled: true
      timeout: 30
      config:
        match_threshold: 0.85
        strategies:
          - exact
          - fuzzy
          - ai
    
    - name: fraud
      class: src.agents.FraudAgent
      enabled: true
      timeout: 20
      config:
        duplicate_window_days: 365
        amount_anomaly_threshold: 3.0  # Standard deviations
    
    - name: approval_router
      class: src.agents.ApprovalRouterAgent
      enabled: true
      timeout: 10

  error_handling:
    default_retry_count: 3
    default_retry_delay: 60
    notification_on_failure: true
```

### Loading Configuration

```python
# src/core/pipeline_config.py
import yaml
from pathlib import Path

def load_pipeline_config(config_path: str = "config/pipeline.yaml") -> dict:
    """Load pipeline configuration from YAML file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Substitute environment variables
    config = _substitute_env_vars(config)
    
    return config

def _substitute_env_vars(obj):
    """Recursively substitute ${VAR} with environment variables."""
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        var_name = obj[2:-1]
        return os.environ.get(var_name, obj)
    elif isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj
```

---

## Related Documentation

- **[Section 3: Component Deep Dive](./03_Component_Details.md)** - Detailed component specifications
- **[Section 5: Data Model](./05_Data_Model.md)** - Database schema and ERD
- **[Extensibility Guide](../Extensibility_Guide.md)** - Building custom agents
- **[API Reference](../API_Reference.md)** - REST API documentation

---

*Continue to [Section 5: Data Model](./05_Data_Model.md)*
