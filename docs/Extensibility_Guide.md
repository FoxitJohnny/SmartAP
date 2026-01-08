# SmartAP Extensibility Guide
## Building Custom Agents for Invoice Processing

**Version:** 1.0.0  
**Last Updated:** January 8, 2026  
**Target Audience:** Developers, System Integrators, DevOps Engineers

---

## Table of Contents

1. [Introduction](#introduction)
2. [When to Extend vs. Configure](#when-to-extend-vs-configure)
3. [Agent Architecture](#agent-architecture)
4. [Getting Started](#getting-started)
5. [Creating Custom Agents](#creating-custom-agents)
6. [Agent Types](#agent-types)
7. [Plugin System](#plugin-system)
8. [Testing Strategies](#testing-strategies)
9. [Deployment](#deployment)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## Introduction

SmartAP's extensibility system allows you to customize invoice processing without modifying core code. Through a plugin architecture, you can:

- **Add custom extraction logic** using different AI models or OCR engines
- **Implement company-specific risk rules** (vendor blacklists, amount thresholds, compliance checks)
- **Integrate with proprietary ERPs** (SAP, Oracle, NetSuite, custom systems)
- **Add custom validation rules** (tax calculations, address verification, duplicate checking)
- **Extend workflow logic** (custom approval routing, notifications, archival)

**Key Benefits:**
- ✅ **No core code changes** - Plugins are isolated and upgradeable
- ✅ **Hot-reloadable** - Add/remove agents without restarting
- ✅ **Dependency management** - Agents can depend on other agents
- ✅ **Type-safe** - Strong typing with Python dataclasses
- ✅ **Testable** - Built-in testing utilities

---

## When to Extend vs. Configure

### Use Configuration When:
- Changing approval thresholds ($10k → $15k)
- Enabling/disabling existing features (fraud detection, PO matching)
- Switching AI models (GPT-4 → Claude)
- Updating environment variables (API keys, URLs)
- Modifying logging levels or retention periods

**Example:**
```bash
# .env configuration
APPROVAL_THRESHOLD=15000
ENABLE_FRAUD_DETECTION=true
AI_MODEL=claude-3-opus
```

### Use Extensions (Plugins) When:
- Adding a new extraction algorithm (custom OCR, regex-based extraction)
- Implementing company-specific risk rules (vendor blacklists, geographic restrictions)
- Integrating with a new ERP system (SAP, Oracle, custom API)
- Adding custom validation logic (tax calculations, address verification)
- Creating custom workflows (multi-stage approvals, conditional routing)

**Example:**
```python
# plugins/custom_risk.py
class CompanyRiskAgent(BaseRiskAgent):
    async def assess_risk(self, invoice_data):
        # Your custom logic here
        return risk_assessment
```

---

## Agent Architecture

### Agent Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                     Invoice Upload                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              1. Extraction Agents                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ OCR Extractor│→ │AI Extractor  │→ │Custom        │     │
│  │              │  │              │  │Extractor     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │ Extracted Data
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              2. Validation Agents                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Data Validator│→ │PO Matcher    │→ │Custom        │     │
│  │              │  │              │  │Validator     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │ Validated Data
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              3. Risk Assessment Agents                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Fraud Detector│→ │Vendor Checker│→ │Custom Risk   │     │
│  │              │  │              │  │Agent         │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │ Risk Assessment
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              4. Approval Workflow                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Auto-Approve  │→ │Manual Review │→ │Escalation    │     │
│  │              │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────┬──────────────────────────────────────┘
                       │ Approved Invoice
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              5. Integration Agents                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ERP Sync      │→ │Payment System│→ │Archival      │     │
│  │              │  │              │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Agent Context Flow

```python
# 1. Context is created with invoice data
context = AgentContext(
    invoice_id="INV-123",
    pdf_bytes=raw_pdf_data,
    metadata={"user_id": "user@company.com"}
)

# 2. Each agent processes the context
result1 = await extractor_agent.process(context)
context.extracted_data = result1.data

result2 = await validator_agent.process(context)
context.previous_results["validator"] = result2.data

result3 = await risk_agent.process(context)
# ... and so on
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- SmartAP backend installed
- Basic understanding of async/await in Python
- Familiarity with invoice processing workflows

### Quick Start: Your First Custom Agent

Let's create a simple agent that checks if an invoice amount is within budget.

#### Step 1: Create Plugin File

Create `backend/plugins/budget_checker.py`:

```python
from src.plugins import BaseAgent, AgentContext, AgentResult, AgentStatus

class BudgetCheckerAgent(BaseAgent):
    """Check if invoice amount is within department budget"""
    
    def __init__(self, budget_limit: float = 50000):
        super().__init__(
            name="budget_checker",
            version="1.0.0",
            description="Verify invoice amount against department budget"
        )
        self.budget_limit = budget_limit
    
    async def process(self, context: AgentContext) -> AgentResult:
        """Check if amount is within budget"""
        try:
            # Get invoice amount from extracted data
            extracted = context.extracted_data or {}
            amount = extracted.get("total_amount", 0)
            
            # Check against budget
            within_budget = amount <= self.budget_limit
            
            return AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data={
                    "within_budget": within_budget,
                    "amount": amount,
                    "budget_limit": self.budget_limit,
                    "message": "Approved" if within_budget else "Over budget"
                },
                confidence=1.0
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
```

#### Step 2: Register the Agent

Add to `backend/src/main.py` or create `backend/src/config/agents.py`:

```python
from src.plugins import registry
from plugins.budget_checker import BudgetCheckerAgent

# Register the agent
budget_agent = BudgetCheckerAgent(budget_limit=50000)
registry.register_agent(budget_agent)

print(f"Registered agents: {registry.list_agents()}")
```

#### Step 3: Use in Pipeline

```python
from src.plugins import get_agent, AgentContext

# Get the agent
budget_agent = get_agent("budget_checker")

# Create context
context = AgentContext(
    invoice_id="INV-123",
    pdf_bytes=b"...",
    extracted_data={"total_amount": 45000}
)

# Process
result = await budget_agent.process(context)

if result.success:
    print(f"Budget check: {result.data['message']}")
    print(f"Amount: ${result.data['amount']:,.2f}")
else:
    print(f"Error: {result.errors}")
```

#### Step 4: Test

Create `backend/tests/plugins/test_budget_checker.py`:

```python
import pytest
from plugins.budget_checker import BudgetCheckerAgent
from src.plugins import AgentContext

@pytest.mark.asyncio
async def test_within_budget():
    agent = BudgetCheckerAgent(budget_limit=50000)
    context = AgentContext(
        invoice_id="TEST-1",
        pdf_bytes=b"test",
        extracted_data={"total_amount": 30000}
    )
    
    result = await agent.process(context)
    
    assert result.success
    assert result.data["within_budget"] is True

@pytest.mark.asyncio
async def test_over_budget():
    agent = BudgetCheckerAgent(budget_limit=50000)
    context = AgentContext(
        invoice_id="TEST-2",
        pdf_bytes=b"test",
        extracted_data={"total_amount": 75000}
    )
    
    result = await agent.process(context)
    
    assert result.success
    assert result.data["within_budget"] is False
```

Run tests:
```bash
cd backend
pytest tests/plugins/test_budget_checker.py -v
```

---

## Creating Custom Agents

### Agent Base Classes

SmartAP provides several base classes for different agent types:

| Base Class | Purpose | Use When |
|------------|---------|----------|
| `BaseAgent` | General-purpose agent | Any custom logic |
| `BaseExtractorAgent` | Data extraction | Parsing PDFs, OCR, AI extraction |
| `BaseValidatorAgent` | Data validation | Checking data completeness, formats |
| `BaseRiskAgent` | Risk assessment | Fraud detection, compliance checks |

### BaseAgent Methods

All agents inherit from `BaseAgent` and must implement:

```python
class MyCustomAgent(BaseAgent):
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method (REQUIRED).
        
        Args:
            context: AgentContext with invoice data
        
        Returns:
            AgentResult with processed data and metadata
        """
        pass
```

Optional methods you can override:

```python
    async def validate_context(self, context: AgentContext) -> bool:
        """
        Validate context before processing (OPTIONAL).
        
        Returns:
            True if context is valid, False otherwise
        """
        return True
    
    async def pre_process(self, context: AgentContext) -> None:
        """
        Setup before processing (OPTIONAL).
        
        Use for:
        - Loading ML models
        - Establishing API connections
        - Initializing caches
        """
        pass
    
    async def post_process(self, result: AgentResult) -> AgentResult:
        """
        Cleanup after processing (OPTIONAL).
        
        Use for:
        - Logging results
        - Sending notifications
        - Updating caches
        """
        return result
```

### AgentContext Structure

```python
@dataclass
class AgentContext:
    # Required
    invoice_id: str
    pdf_bytes: bytes
    
    # Optional
    pdf_path: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    vendor_id: Optional[str] = None
    vendor_data: Optional[Dict[str, Any]] = None
    po_number: Optional[str] = None
    po_data: Optional[Dict[str, Any]] = None
    previous_results: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
```

**Access previous agent results:**
```python
async def process(self, context: AgentContext) -> AgentResult:
    # Get extractor results
    extracted_data = context.extracted_data
    
    # Get results from specific agent
    validator_results = context.previous_results.get("validator", {})
    
    # Your processing logic
    ...
```

### AgentResult Structure

```python
@dataclass
class AgentResult:
    success: bool              # Did processing succeed?
    status: AgentStatus        # SUCCESS, FAILED, PARTIAL, SKIPPED
    data: Dict[str, Any]       # Processed data
    confidence: float          # Confidence score (0.0-1.0)
    errors: List[str] = []     # Any errors encountered
    warnings: List[str] = []   # Any warnings
    execution_time_ms: Optional[float] = None
    agent_version: Optional[str] = None
```

**Creating results:**
```python
# Success
return AgentResult(
    success=True,
    status=AgentStatus.SUCCESS,
    data={"key": "value"},
    confidence=0.95
)

# Failure
return AgentResult(
    success=False,
    status=AgentStatus.FAILED,
    data={},
    confidence=0.0,
    errors=["Something went wrong"]
)

# Partial success
return AgentResult(
    success=True,
    status=AgentStatus.PARTIAL,
    data={"some": "data"},
    confidence=0.7,
    warnings=["Some fields missing"]
)
```

---

## Agent Types

### 1. Extraction Agents

**Purpose:** Extract structured data from invoice PDFs

**Base Class:** `BaseExtractorAgent`

**Example:** Custom OCR using Tesseract

```python
from src.plugins import BaseExtractorAgent, AgentContext, AgentResult, AgentStatus
import pytesseract
from PIL import Image
import io

class TesseractExtractor(BaseExtractorAgent):
    """Extract invoice data using Tesseract OCR"""
    
    def __init__(self):
        super().__init__(
            name="tesseract_extractor",
            version="1.0.0",
            description="OCR-based extraction using Tesseract",
            supported_formats=["pdf", "png", "jpg"]
        )
    
    async def process(self, context: AgentContext) -> AgentResult:
        try:
            extracted_data = await self.extract_invoice_data(context.pdf_bytes)
            
            return AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data=extracted_data,
                confidence=0.85
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
    
    async def extract_invoice_data(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract text using Tesseract"""
        # Convert PDF to image
        image = Image.open(io.BytesIO(pdf_bytes))
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        # Parse text (simplified)
        invoice_data = {
            "raw_text": text,
            "invoice_number": self._extract_invoice_number(text),
            "total_amount": self._extract_total(text),
            # ... more extraction logic
        }
        
        return invoice_data
    
    def _extract_invoice_number(self, text: str) -> str:
        import re
        match = re.search(r"Invoice #?:?\s*([A-Z0-9-]+)", text)
        return match.group(1) if match else ""
    
    def _extract_total(self, text: str) -> float:
        import re
        match = re.search(r"Total:?\s*\$?([0-9,]+\.\d{2})", text)
        if match:
            return float(match.group(1).replace(",", ""))
        return 0.0
```

### 2. Validation Agents

**Purpose:** Validate extracted data for correctness

**Base Class:** `BaseValidatorAgent`

**Example:** Tax calculation validator

```python
from src.plugins import BaseValidatorAgent, AgentContext, AgentResult, AgentStatus

class TaxValidator(BaseValidatorAgent):
    """Validate tax calculations"""
    
    def __init__(self, tax_rates: Dict[str, float]):
        super().__init__(
            name="tax_validator",
            version="1.0.0",
            description="Verify tax calculations by state/country",
            validation_rules=["tax_amount_matches", "tax_rate_valid"]
        )
        self.tax_rates = tax_rates  # {"CA": 0.0725, "NY": 0.08, ...}
    
    async def process(self, context: AgentContext) -> AgentResult:
        try:
            validation_results = await self.validate_data(context.extracted_data or {})
            
            return AgentResult(
                success=validation_results["is_valid"],
                status=AgentStatus.SUCCESS if validation_results["is_valid"] else AgentStatus.PARTIAL,
                data=validation_results,
                confidence=1.0
            )
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
    
    async def validate_data(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tax calculation"""
        subtotal = invoice_data.get("subtotal", 0)
        tax_amount = invoice_data.get("tax_amount", 0)
        total = invoice_data.get("total_amount", 0)
        state = invoice_data.get("customer", {}).get("state", "")
        
        errors = []
        warnings = []
        
        # Check if state has valid tax rate
        if state not in self.tax_rates:
            warnings.append(f"Unknown state: {state}")
            expected_tax_rate = 0.0
        else:
            expected_tax_rate = self.tax_rates[state]
        
        # Calculate expected tax
        expected_tax = subtotal * expected_tax_rate
        tax_difference = abs(tax_amount - expected_tax)
        
        # Allow 1% margin for rounding
        if tax_difference > (expected_tax * 0.01):
            errors.append(
                f"Tax mismatch: Expected ${expected_tax:.2f}, got ${tax_amount:.2f}"
            )
        
        # Verify total = subtotal + tax
        expected_total = subtotal + tax_amount
        if abs(total - expected_total) > 0.01:
            errors.append(
                f"Total mismatch: Expected ${expected_total:.2f}, got ${total:.2f}"
            )
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "expected_tax_rate": expected_tax_rate,
            "expected_tax_amount": expected_tax,
            "actual_tax_amount": tax_amount
        }
```

### 3. Risk Assessment Agents

**Purpose:** Assess invoice risk and fraud potential

**Base Class:** `BaseRiskAgent`

**Example:** See `plugins/custom_risk.py` for a complete implementation

Key methods:
```python
class MyRiskAgent(BaseRiskAgent):
    async def assess_risk(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess risk and return:
        {
            "risk_score": 0.0-1.0,
            "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
            "risk_factors": [...],
            "recommended_action": "AUTO_APPROVE" | "MANUAL_REVIEW" | "REJECT"
        }
        """
        pass
```

### 4. Integration Agents

**Purpose:** Integrate with external systems (ERPs, payment gateways)

**Base Class:** `BaseAgent`

**Example:** See `plugins/custom_erp.py` for ERP connectors

---

## Plugin System

### Plugin Discovery

SmartAP auto-discovers plugins from the `backend/plugins/` directory:

```python
from src.plugins import registry
from pathlib import Path

# Auto-discover all plugins
plugins_dir = Path("backend/plugins")
count = registry.discover_plugins(plugins_dir)
print(f"Discovered {count} agents")

# List all registered agents
print(registry.list_agents())
```

### Manual Registration

```python
from src.plugins import register_agent
from plugins.my_agent import MyCustomAgent

# Instantiate and register
agent = MyCustomAgent()
register_agent(agent)
```

### Dependency Management

Agents can depend on other agents:

```python
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="my_agent",
            version="1.0.0",
            description="My custom agent",
            dependencies=["extractor", "validator"]  # Runs after these agents
        )
```

Resolve execution order:

```python
from src.plugins import registry

# Get execution order (dependencies first)
execution_order = registry.resolve_dependencies("my_agent")
print(execution_order)  # ["extractor", "validator", "my_agent"]
```

### Configuration Management

Load configuration from environment variables or config files:

```python
import os
from dataclasses import dataclass

@dataclass
class MyAgentConfig:
    api_url: str
    api_key: str
    timeout: int
    
    @classmethod
    def from_env(cls):
        return cls(
            api_url=os.getenv("MY_AGENT_API_URL", "https://api.example.com"),
            api_key=os.getenv("MY_AGENT_API_KEY", ""),
            timeout=int(os.getenv("MY_AGENT_TIMEOUT", "30"))
        )

class MyAgent(BaseAgent):
    def __init__(self, config: MyAgentConfig = None):
        super().__init__(name="my_agent", version="1.0.0")
        self.config = config or MyAgentConfig.from_env()
```

---

## Testing Strategies

### Unit Testing

Test individual agents in isolation:

```python
import pytest
from plugins.my_agent import MyAgent
from src.plugins import AgentContext, AgentResult

@pytest.fixture
def agent():
    return MyAgent()

@pytest.fixture
def context():
    return AgentContext(
        invoice_id="TEST-1",
        pdf_bytes=b"test pdf content",
        extracted_data={"total_amount": 1000}
    )

@pytest.mark.asyncio
async def test_agent_success(agent, context):
    result = await agent.process(context)
    
    assert result.success is True
    assert result.status == AgentStatus.SUCCESS
    assert result.confidence > 0.8
    assert "key" in result.data

@pytest.mark.asyncio
async def test_agent_handles_missing_data(agent):
    context = AgentContext(
        invoice_id="TEST-2",
        pdf_bytes=b"test",
        extracted_data=None  # Missing data
    )
    
    result = await agent.process(context)
    
    assert result.success is False
    assert len(result.errors) > 0
```

### Integration Testing

Test agent in full pipeline:

```python
@pytest.mark.asyncio
async def test_full_pipeline():
    from src.plugins import registry, AgentContext
    
    # Register agents
    registry.register_agent(ExtractorAgent())
    registry.register_agent(ValidatorAgent())
    registry.register_agent(RiskAgent())
    
    # Create context
    context = AgentContext(
        invoice_id="INT-TEST-1",
        pdf_bytes=load_test_pdf()
    )
    
    # Run pipeline
    execution_order = registry.resolve_dependencies("risk_agent")
    
    for agent_name in execution_order:
        agent = registry.get_agent(agent_name)
        result = await agent.process(context)
        
        assert result.success, f"{agent_name} failed: {result.errors}"
        
        # Update context with results
        if agent_name == "extractor":
            context.extracted_data = result.data
        context.previous_results[agent_name] = result.data
    
    # Verify final result
    final_result = context.previous_results["risk_agent"]
    assert "risk_score" in final_result
```

### Mocking External APIs

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_erp_connector_with_mock():
    from plugins.custom_erp import CustomERPConnector
    
    # Mock the HTTP client
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "ERP-123",
            "status": "created"
        }
        mock_response.raise_for_status = AsyncMock()
        
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        # Test connector
        connector = CustomERPConnector(api_key="test_key")
        context = AgentContext(
            invoice_id="TEST-1",
            pdf_bytes=b"test",
            extracted_data={"invoice_number": "INV-123", "total_amount": 1000}
        )
        
        result = await connector.process(context)
        
        assert result.success
        assert result.data["erp_invoice_id"] == "ERP-123"
```

---

## Deployment

### As Python Package

Package your plugins as a Python package:

```
my-company-smartap-plugins/
├── setup.py
├── README.md
├── requirements.txt
└── smartap_plugins/
    ├── __init__.py
    ├── risk_agents/
    │   ├── __init__.py
    │   └── company_risk.py
    └── erp_connectors/
        ├── __init__.py
        └── sap_connector.py
```

**setup.py:**
```python
from setuptools import setup, find_packages

setup(
    name="smartap-mycompany-plugins",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "smartap>=1.0.0",
        "httpx>=0.25.0",
        # ... other dependencies
    ],
    entry_points={
        "smartap.plugins": [
            "company_risk = smartap_plugins.risk_agents.company_risk:CompanyRiskAgent",
            "sap_connector = smartap_plugins.erp_connectors.sap_connector:SAPConnector",
        ]
    }
)
```

Install:
```bash
pip install smartap-mycompany-plugins
```

### As Docker Layer

Add plugins to Docker image:

```dockerfile
# Dockerfile.plugins
FROM smartap-backend:latest

# Copy plugins
COPY plugins/ /app/plugins/

# Install additional dependencies
COPY plugins/requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Register plugins on startup
ENV SMARTAP_PLUGINS_DIR=/app/plugins
```

Build and run:
```bash
docker build -f Dockerfile.plugins -t smartap-backend-custom .
docker-compose up -d
```

### Environment-Specific Plugins

Load different plugins per environment:

```python
# src/config/agents.py
import os
from src.plugins import registry
from pathlib import Path

def load_plugins():
    env = os.getenv("APP_ENV", "development")
    
    # Load core plugins (always)
    core_plugins_dir = Path("backend/plugins/core")
    registry.discover_plugins(core_plugins_dir)
    
    # Load environment-specific plugins
    if env == "production":
        prod_plugins_dir = Path("backend/plugins/production")
        registry.discover_plugins(prod_plugins_dir)
    elif env == "staging":
        staging_plugins_dir = Path("backend/plugins/staging")
        registry.discover_plugins(staging_plugins_dir)
    else:
        dev_plugins_dir = Path("backend/plugins/development")
        registry.discover_plugins(dev_plugins_dir)
    
    print(f"Loaded {len(registry.list_agents())} agents for {env}")
```

---

## Best Practices

### 1. Error Handling

Always catch exceptions and return AgentResult with errors:

```python
async def process(self, context: AgentContext) -> AgentResult:
    try:
        # Your logic
        result_data = await self.do_something(context)
        
        return AgentResult(
            success=True,
            status=AgentStatus.SUCCESS,
            data=result_data,
            confidence=0.95
        )
    except ValueError as e:
        # Validation error (user-facing)
        return AgentResult(
            success=False,
            status=AgentStatus.FAILED,
            data={},
            confidence=0.0,
            errors=[f"Invalid data: {str(e)}"]
        )
    except httpx.HTTPError as e:
        # API error (retry-able)
        return AgentResult(
            success=False,
            status=AgentStatus.FAILED,
            data={},
            confidence=0.0,
            errors=[f"API error: {str(e)}"],
            warnings=["Retry recommended"]
        )
    except Exception as e:
        # Unexpected error (log and alert)
        logger.exception("Unexpected error in agent")
        return AgentResult(
            success=False,
            status=AgentStatus.FAILED,
            data={},
            confidence=0.0,
            errors=[f"Internal error: {str(e)}"]
        )
```

### 2. Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

async def process(self, context: AgentContext) -> AgentResult:
    logger.info(
        "Processing invoice",
        extra={
            "agent": self.name,
            "invoice_id": context.invoice_id,
            "version": self.version
        }
    )
    
    # ... processing
    
    logger.info(
        "Processing complete",
        extra={
            "agent": self.name,
            "invoice_id": context.invoice_id,
            "confidence": result.confidence,
            "execution_time_ms": result.execution_time_ms
        }
    )
    
    return result
```

### 3. Performance

Cache expensive operations:

```python
from functools import lru_cache
from cachetools import TTLCache

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="my_agent", version="1.0.0")
        
        # Cache with TTL
        self._vendor_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
    
    @lru_cache(maxsize=128)
    def _get_tax_rate(self, state: str) -> float:
        """Cache tax rates (rarely change)"""
        return tax_rates.get(state, 0.0)
    
    async def _get_vendor_data(self, vendor_id: str) -> Dict:
        """Cache vendor data with TTL"""
        if vendor_id in self._vendor_cache:
            return self._vendor_cache[vendor_id]
        
        # Fetch from database
        vendor_data = await self.fetch_vendor(vendor_id)
        self._vendor_cache[vendor_id] = vendor_data
        
        return vendor_data
```

### 4. Security

Never log sensitive data:

```python
async def process(self, context: AgentContext) -> AgentResult:
    # ❌ DON'T: Log sensitive data
    logger.info(f"Processing invoice: {context.extracted_data}")
    
    # ✅ DO: Log only safe fields
    logger.info(
        "Processing invoice",
        extra={
            "invoice_id": context.invoice_id,
            "vendor_id": context.vendor_id,
            # Don't log amounts, tax IDs, etc.
        }
    )
```

Sanitize API keys:

```python
def __repr__(self):
    return f"<{self.__class__.__name__} api_key={'*' * 8}>"
```

### 5. Testing

Write tests for every agent:

```bash
backend/
├── plugins/
│   └── my_agent.py
└── tests/
    └── plugins/
        └── test_my_agent.py
```

Aim for >80% code coverage:

```bash
pytest tests/plugins/ --cov=plugins --cov-report=html
```

---

## Troubleshooting

### Agent Not Discovered

**Problem:** Agent not showing in `registry.list_agents()`

**Solutions:**
1. Check filename: Must be `.py` file in `plugins/` directory
2. Check class: Must inherit from `BaseAgent`
3. Check `__init__`: Must be callable without required arguments
4. Check for import errors: Run `python -c "from plugins.my_agent import MyAgent"`

```bash
# Debug plugin discovery
python -c "
from src.plugins import registry
from pathlib import Path
count = registry.discover_plugins(Path('backend/plugins'))
print(f'Discovered: {count}')
print(f'Agents: {registry.list_agents()}')
"
```

### Circular Dependencies

**Problem:** `ValueError: Circular dependency detected: A → B → A`

**Solution:** Remove circular dependency or merge agents:

```python
# ❌ DON'T: Circular dependency
class AgentA(BaseAgent):
    def __init__(self):
        super().__init__(dependencies=["agent_b"])

class AgentB(BaseAgent):
    def __init__(self):
        super().__init__(dependencies=["agent_a"])

# ✅ DO: Linear dependency
class AgentA(BaseAgent):
    def __init__(self):
        super().__init__(dependencies=[])

class AgentB(BaseAgent):
    def __init__(self):
        super().__init__(dependencies=["agent_a"])
```

### Low Confidence Scores

**Problem:** Agent returns `confidence < 0.5`

**Solutions:**
1. Improve data quality (better OCR, higher resolution PDFs)
2. Add validation checks (reject incomplete data early)
3. Fine-tune AI models (more training data)
4. Add fallback logic (try alternative extraction methods)

```python
async def process(self, context: AgentContext) -> AgentResult:
    # Try primary extraction
    result1 = await self.extract_primary(context)
    
    if result1.confidence < 0.7:
        # Try fallback method
        logger.warning("Low confidence, trying fallback method")
        result2 = await self.extract_fallback(context)
        
        # Use better result
        return result1 if result1.confidence > result2.confidence else result2
    
    return result1
```

### Performance Issues

**Problem:** Agent takes >5 seconds to process

**Solutions:**
1. Add caching (see Best Practices > Performance)
2. Use async I/O for API calls
3. Batch process multiple invoices
4. Profile with `cProfile` or `py-spy`

```python
# Profile agent
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

result = await agent.process(context)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(10)  # Top 10 slowest functions
```

---

## API Reference

### Base Classes

#### `BaseAgent`

```python
class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        dependencies: Optional[List[str]] = None
    )
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResult:
        """Main processing method (REQUIRED)"""
        pass
    
    async def validate_context(self, context: AgentContext) -> bool:
        """Validate context (OPTIONAL)"""
        return True
    
    async def pre_process(self, context: AgentContext) -> None:
        """Setup hook (OPTIONAL)"""
        pass
    
    async def post_process(self, result: AgentResult) -> AgentResult:
        """Cleanup hook (OPTIONAL)"""
        return result
```

#### `BaseExtractorAgent`

```python
class BaseExtractorAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        supported_formats: Optional[List[str]] = None
    )
    
    @abstractmethod
    async def extract_invoice_data(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract data from PDF (REQUIRED)"""
        pass
```

#### `BaseValidatorAgent`

```python
class BaseValidatorAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        validation_rules: Optional[List[str]] = None
    )
    
    @abstractmethod
    async def validate_data(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate invoice data (REQUIRED)"""
        pass
```

#### `BaseRiskAgent`

```python
class BaseRiskAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        risk_threshold: float = 0.5
    )
    
    @abstractmethod
    async def assess_risk(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess invoice risk (REQUIRED)"""
        pass
```

### Data Classes

#### `AgentContext`

```python
@dataclass
class AgentContext:
    invoice_id: str
    pdf_bytes: bytes
    pdf_path: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    vendor_id: Optional[str] = None
    vendor_data: Optional[Dict[str, Any]] = None
    po_number: Optional[str] = None
    po_data: Optional[Dict[str, Any]] = None
    previous_results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### `AgentResult`

```python
@dataclass
class AgentResult:
    success: bool
    status: AgentStatus
    data: Dict[str, Any]
    confidence: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: Optional[float] = None
    agent_version: Optional[str] = None
```

#### `AgentStatus`

```python
class AgentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
```

### Registry Functions

```python
def register_agent(agent: BaseAgent) -> None:
    """Register agent with global registry"""

def get_agent(name: str) -> Optional[BaseAgent]:
    """Get agent by name"""

def list_agents() -> List[str]:
    """List all registered agent names"""

class PluginRegistry:
    def register_agent(self, agent: BaseAgent) -> None
    def register_agent_class(self, name: str, agent_class: Type[BaseAgent]) -> None
    def get_agent(self, name: str) -> Optional[BaseAgent]
    def list_agents(self) -> List[str]
    def get_agent_info(self, name: str) -> Optional[Dict]
    def discover_plugins(self, plugins_dir: Path) -> int
    def resolve_dependencies(self, agent_name: str) -> List[str]
```

---

## Examples

### Complete Example: Carbon Footprint Agent

Track carbon footprint for shipped items:

```python
# plugins/carbon_footprint.py
from src.plugins import BaseAgent, AgentContext, AgentResult, AgentStatus
import httpx
import os

class CarbonFootprintAgent(BaseAgent):
    """Calculate carbon footprint for invoice line items"""
    
    def __init__(self):
        super().__init__(
            name="carbon_footprint",
            version="1.0.0",
            description="Calculate CO2 emissions for shipped products"
        )
        self.carbon_api_url = "https://api.carbon.example.com/calculate"
        self.carbon_api_key = os.getenv("CARBON_API_KEY")
    
    async def process(self, context: AgentContext) -> AgentResult:
        try:
            extracted_data = context.extracted_data or {}
            line_items = extracted_data.get("line_items", [])
            
            if not line_items:
                return AgentResult(
                    success=True,
                    status=AgentStatus.SKIPPED,
                    data={"message": "No line items to analyze"},
                    confidence=1.0
                )
            
            # Calculate footprint for each item
            total_co2_kg = 0.0
            item_footprints = []
            
            for item in line_items:
                co2 = await self._calculate_item_footprint(item)
                total_co2_kg += co2
                item_footprints.append({
                    "description": item.get("description"),
                    "co2_kg": co2
                })
            
            return AgentResult(
                success=True,
                status=AgentStatus.SUCCESS,
                data={
                    "total_co2_kg": round(total_co2_kg, 2),
                    "total_co2_tons": round(total_co2_kg / 1000, 3),
                    "item_footprints": item_footprints,
                    "carbon_offset_cost_usd": round(total_co2_kg * 0.02, 2)  # $20/ton
                },
                confidence=0.85
            )
        
        except Exception as e:
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                data={},
                confidence=0.0,
                errors=[str(e)]
            )
    
    async def _calculate_item_footprint(self, item: Dict) -> float:
        """Calculate CO2 footprint for single item"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.carbon_api_url,
                json={
                    "product": item.get("description"),
                    "quantity": item.get("quantity", 1),
                    "category": item.get("category", "general")
                },
                headers={"Authorization": f"Bearer {self.carbon_api_key}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("co2_kg", 0.0)
```

---

## Conclusion

SmartAP's plugin system provides a powerful, flexible way to extend invoice processing without modifying core code. By following this guide, you can:

- ✅ Create custom extraction agents for any PDF format
- ✅ Implement company-specific risk rules and compliance checks
- ✅ Integrate with any ERP system or payment gateway
- ✅ Add custom validation logic for tax, address, or business rules
- ✅ Build and deploy plugins as Python packages or Docker layers

**Next Steps:**
1. Review the three example plugins (`custom_extractor.py`, `custom_risk.py`, `custom_erp.py`)
2. Create your first custom agent following the Quick Start guide
3. Write tests for your agent
4. Deploy to staging environment
5. Monitor performance and iterate

**Resources:**
- [API Documentation](http://localhost:8000/docs)
- [Sample Plugins](backend/plugins/)
- [Test Utilities](backend/tests/plugins/)
- [GitHub Discussions](https://github.com/yourusername/smartap/discussions)

---

*Last updated: January 8, 2026*
