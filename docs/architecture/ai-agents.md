# AI Agents Architecture

This document describes the AI agent architecture in SmartAP.

## Overview

SmartAP uses a multi-agent architecture where specialized AI agents collaborate to process invoices. Each agent has a specific responsibility and can be extended or replaced via the plugin system.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Invoice Processing Pipeline                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  Extraction │    │  Matching   │    │    Risk     │             │
│  │    Agent    │───▶│    Agent    │───▶│   Agent     │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│         │                  │                  │                      │
│         ▼                  ▼                  ▼                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  Extracted  │    │   Match     │    │    Risk     │             │
│  │    Data     │    │   Results   │    │   Score     │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Agent Types

### 1. Extraction Agent

**Purpose:** Extract structured data from invoice documents.

**Input:**
- PDF document bytes
- OCR text (if scanned document)
- Document metadata

**Output:**
```python
class ExtractionResult:
    vendor_name: str
    vendor_address: str
    invoice_number: str
    invoice_date: date
    due_date: date
    line_items: List[LineItem]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    payment_terms: str
    confidence_scores: Dict[str, float]
```

**AI Model:** GPT-4o with structured output

**Configuration:**
```yaml
extraction_agent:
  model: gpt-4o
  temperature: 0.0
  max_tokens: 4096
  retry_attempts: 3
  confidence_threshold: 0.85
```

### 2. PO Matching Agent

**Purpose:** Match invoices to purchase orders and validate line items.

**Input:**
- Extracted invoice data
- Purchase order database
- Vendor information

**Output:**
```python
class MatchingResult:
    matched_po: Optional[str]
    match_confidence: float
    line_item_matches: List[LineItemMatch]
    discrepancies: List[Discrepancy]
    recommendation: MatchRecommendation
```

**Logic:**
1. Query POs by vendor ID
2. Compare amounts within tolerance
3. Match line items by description/SKU
4. Flag discrepancies for review

**Configuration:**
```yaml
matching_agent:
  price_tolerance_percent: 5.0
  quantity_tolerance_percent: 2.0
  fuzzy_match_threshold: 0.8
  require_exact_po_number: false
```

### 3. Risk Detection Agent

**Purpose:** Identify potential fraud and compliance issues.

**Input:**
- Invoice data
- Vendor history
- Matching results
- Historical patterns

**Output:**
```python
class RiskAssessment:
    risk_score: float  # 0.0 - 1.0
    risk_level: RiskLevel  # LOW, MEDIUM, HIGH, CRITICAL
    flags: List[RiskFlag]
    recommendations: List[str]
```

**Risk Factors:**
- Duplicate invoice detection
- Unusual amounts for vendor
- Payment term anomalies
- Vendor status (new, inactive)
- Round number amounts
- Rush payment requests

**Configuration:**
```yaml
risk_agent:
  duplicate_window_days: 365
  unusual_amount_std_dev: 2.0
  new_vendor_risk_weight: 0.3
  rush_payment_risk_weight: 0.2
```

### 4. Approval Routing Agent

**Purpose:** Determine approval workflow based on business rules.

**Input:**
- Invoice data
- Risk assessment
- Organization hierarchy
- Approval policies

**Output:**
```python
class ApprovalRoute:
    workflow_id: str
    approvers: List[Approver]
    escalation_path: List[Approver]
    auto_approve: bool
    reason: str
```

**Routing Rules:**
- Amount thresholds
- Department budgets
- Vendor categories
- Risk levels
- Time sensitivity

---

## Agent Orchestration

### Workflow Graph

The agent pipeline is defined as a directed acyclic graph (DAG):

```python
from src.orchestration import WorkflowGraph, WorkflowState

graph = WorkflowGraph()

# Define nodes
graph.add_node("ingest", ingest_document)
graph.add_node("extract", extraction_agent.process)
graph.add_node("match", matching_agent.process)
graph.add_node("risk", risk_agent.process)
graph.add_node("route", routing_agent.process)

# Define edges
graph.add_edge("ingest", "extract")
graph.add_edge("extract", "match")
graph.add_edge("match", "risk")
graph.add_edge("risk", "route")

# Conditional routing
graph.add_conditional_edge(
    "extract",
    lambda state: "manual_review" if state.confidence < 0.7 else "match"
)
```

### State Management

Workflow state tracks invoice progress:

```python
class WorkflowState:
    document_id: str
    status: WorkflowStatus
    current_node: str
    extraction_result: Optional[ExtractionResult]
    matching_result: Optional[MatchingResult]
    risk_assessment: Optional[RiskAssessment]
    approval_route: Optional[ApprovalRoute]
    errors: List[str]
    timestamps: Dict[str, datetime]
```

### Error Handling

Agents implement retry logic with exponential backoff:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(AIModelError)
)
async def process(self, input_data: AgentInput) -> AgentOutput:
    # Agent processing logic
    pass
```

---

## Plugin System

### Creating Custom Agents

Extend `BaseAgent` to create custom agents:

```python
from src.plugins.base import BaseAgent, AgentInput, AgentOutput

class CarbonFootprintAgent(BaseAgent):
    """Calculate carbon footprint from shipping details."""
    
    name = "carbon_footprint"
    version = "1.0.0"
    
    async def process(self, input_data: AgentInput) -> AgentOutput:
        # Extract shipping details
        shipping = input_data.extraction_result.get("shipping_info")
        
        # Calculate carbon footprint
        footprint = await self._calculate_footprint(shipping)
        
        return AgentOutput(
            success=True,
            data={"carbon_kg": footprint},
            confidence=0.95
        )
    
    async def _calculate_footprint(self, shipping: dict) -> float:
        # Implementation
        pass
```

### Registering Agents

Register custom agents in the plugin registry:

```python
from src.plugins.registry import PluginRegistry

registry = PluginRegistry()
registry.register(CarbonFootprintAgent())

# Or via configuration
# plugins/carbon_footprint/config.yaml
```

### Agent Configuration

Configure agents via YAML:

```yaml
# plugins/carbon_footprint/config.yaml
name: carbon_footprint
version: 1.0.0
enabled: true
priority: 100

settings:
  emission_factors:
    air: 0.5
    sea: 0.01
    road: 0.1

dependencies:
  - extraction_agent
```

---

## AI Model Integration

### Supported Providers

| Provider | Models | Configuration |
|----------|--------|---------------|
| GitHub Models | gpt-4o, gpt-4o-mini | `GITHUB_TOKEN` |
| OpenAI | gpt-4o, gpt-4-turbo | `OPENAI_API_KEY` |
| Anthropic | claude-3-opus, claude-3-sonnet | `ANTHROPIC_API_KEY` |
| Azure OpenAI | gpt-4o (custom deployment) | `AZURE_OPENAI_*` |

### Model Selection

Configure the model provider:

```python
from src.config import get_settings

settings = get_settings()
model_config = {
    "provider": settings.ai_model_provider,  # "github", "openai", etc.
    "model": settings.ai_model_name,         # "gpt-4o"
    "temperature": settings.ai_model_temperature,
    "max_tokens": 4096
}
```

### Structured Output

Use Pydantic models for type-safe AI responses:

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class InvoiceData(BaseModel):
    vendor_name: str
    total_amount: float
    line_items: List[LineItem]

agent = Agent(
    model="gpt-4o",
    result_type=InvoiceData,
    system_prompt="Extract invoice data..."
)

result = await agent.run(document_text)
# result.data is typed as InvoiceData
```

---

## Performance Optimization

### Batch Processing

Process multiple invoices efficiently:

```python
async def batch_extract(documents: List[Document]) -> List[ExtractionResult]:
    """Process documents in parallel batches."""
    batch_size = 10
    results = []
    
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[extraction_agent.process(doc) for doc in batch]
        )
        results.extend(batch_results)
    
    return results
```

### Caching

Cache AI responses for identical inputs:

```python
from src.cache import get_cache

@cached(ttl=3600, key_prefix="extraction")
async def cached_extract(document_hash: str, text: str) -> ExtractionResult:
    return await extraction_agent.process(text)
```

### Model Fallback

Implement fallback for model failures:

```python
async def extract_with_fallback(text: str) -> ExtractionResult:
    try:
        return await gpt4o_agent.process(text)
    except RateLimitError:
        return await gpt4o_mini_agent.process(text)
    except AIModelError:
        return await rule_based_extractor.process(text)
```

---

## Monitoring & Observability

### Metrics

Track agent performance:

```python
from src.utils.monitoring import metrics

# Processing time
with metrics.timer("agent.extraction.duration"):
    result = await extraction_agent.process(input_data)

# Success rate
metrics.increment("agent.extraction.success" if result.success else "agent.extraction.failure")

# Confidence scores
metrics.histogram("agent.extraction.confidence", result.confidence)
```

### Logging

Structured logging for agent operations:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "agent.extraction.complete",
    document_id=doc.id,
    confidence=result.confidence,
    duration_ms=duration,
    extracted_fields=list(result.data.keys())
)
```

### Tracing

Distributed tracing for pipeline debugging:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("invoice.extraction") as span:
    span.set_attribute("document.id", document_id)
    result = await extraction_agent.process(input_data)
    span.set_attribute("extraction.confidence", result.confidence)
```

---

## Testing Agents

### Unit Tests

Test agent logic in isolation:

```python
@pytest.mark.asyncio
async def test_extraction_agent_basic():
    agent = ExtractionAgent()
    input_data = AgentInput(text="Invoice #12345\nTotal: $1,000.00")
    
    result = await agent.process(input_data)
    
    assert result.success
    assert result.data["invoice_number"] == "12345"
    assert result.data["total_amount"] == 1000.00
```

### Integration Tests

Test agent pipeline with mocked AI:

```python
@pytest.mark.asyncio
async def test_full_pipeline(mock_ai_model):
    mock_ai_model.return_value = mock_extraction_response
    
    result = await process_invoice(test_document)
    
    assert result.status == "matched"
    assert result.risk_level == "low"
```

### Performance Tests

Benchmark agent throughput:

```python
@pytest.mark.performance
async def test_extraction_throughput():
    documents = generate_test_documents(100)
    
    start = time.perf_counter()
    results = await batch_extract(documents)
    duration = time.perf_counter() - start
    
    assert duration < 60  # 100 docs in < 60 seconds
    assert all(r.success for r in results)
```
