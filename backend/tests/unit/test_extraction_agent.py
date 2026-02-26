"""
Unit Tests for Invoice Extraction Agent

Tests the AI-powered invoice extraction with mocked AI responses.
"""

import pytest
import json
from pathlib import Path
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.extraction_agent import InvoiceExtractionAgent, EXTRACTION_SYSTEM_PROMPT
from src.models import Invoice, InvoiceLineItem, ExtractionConfidence, InvoiceStatus
from src.config import Settings


class TestInvoiceExtractionAgent:
    """Tests for InvoiceExtractionAgent."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        settings = MagicMock(spec=Settings)
        settings.ai_provider = "openai"
        settings.openai_api_key = "test-key"
        settings.model_id = "gpt-4"
        settings.extraction_confidence_threshold = 0.8
        settings.foxit_api_key = "test-foxit-key"
        settings.foxit_api_endpoint = "https://api.foxit.test"
        return settings
    
    @pytest.fixture
    def agent(self, settings):
        """Create agent instance with mocked dependencies."""
        with patch('src.services.extraction_agent.OCRService'):
            return InvoiceExtractionAgent(settings)
    
    @pytest.fixture
    def valid_ai_response(self):
        """Valid AI extraction response."""
        return json.dumps({
            "invoice_number": "INV-2026-001",
            "vendor_name": "Acme Corporation",
            "vendor_address": "123 Main St, City, ST 12345",
            "vendor_tax_id": "12-3456789",
            "invoice_date": "2026-01-15",
            "due_date": "2026-02-14",
            "currency": "USD",
            "subtotal": 1000.00,
            "tax": 80.00,
            "total": 1080.00,
            "line_items": [
                {
                    "description": "Widget A - Premium",
                    "quantity": 10,
                    "unit_price": 50.00,
                    "amount": 500.00,
                    "sku": "WGT-A-001"
                },
                {
                    "description": "Widget B - Standard",
                    "quantity": 20,
                    "unit_price": 25.00,
                    "amount": 500.00,
                    "sku": "WGT-B-001"
                }
            ],
            "po_number": "PO-2026-0050",
            "payment_terms": "Net 30",
            "confidence": {
                "invoice_number": 0.98,
                "vendor_name": 0.95,
                "invoice_date": 0.92,
                "total": 0.99,
                "line_items": 0.88
            }
        })
    
    @pytest.fixture
    def ocr_result_mock(self):
        """Mock OCR result."""
        mock = MagicMock()
        mock.text = """
        INVOICE
        Invoice Number: INV-2026-001
        Date: January 15, 2026
        Due Date: February 14, 2026
        
        From: Acme Corporation
        123 Main St, City, ST 12345
        Tax ID: 12-3456789
        
        To: Customer Inc
        456 Oak Ave, Town, ST 67890
        
        Items:
        Widget A - Premium    10 @ $50.00    $500.00
        Widget B - Standard   20 @ $25.00    $500.00
        
        Subtotal: $1,000.00
        Tax (8%): $80.00
        Total: $1,080.00
        
        PO Number: PO-2026-0050
        Payment Terms: Net 30
        """
        mock.is_scanned = False
        mock.ocr_applied = False
        mock.page_count = 1
        mock.file_hash = "abc123def456"
        return mock
    
    def test_parse_extraction_response_valid(self, agent, valid_ai_response):
        """Test parsing valid AI extraction response."""
        errors = []
        warnings = []
        
        invoice, confidence = agent._parse_extraction_response(
            valid_ai_response, errors, warnings
        )
        
        assert invoice is not None
        assert invoice.invoice_number == "INV-2026-001"
        assert invoice.vendor_name == "Acme Corporation"
        assert invoice.total == Decimal("1080")
        assert len(invoice.line_items) == 2
        assert invoice.line_items[0].description == "Widget A - Premium"
        assert invoice.line_items[0].quantity == 10
        
        assert confidence.invoice_number == 0.98
        assert confidence.vendor_name == 0.95
        assert confidence.total == 0.99
        assert len(errors) == 0
    
    def test_parse_extraction_response_with_code_blocks(self, agent):
        """Test parsing response wrapped in markdown code blocks."""
        response = """```json
{
    "invoice_number": "INV-001",
    "vendor_name": "Test Corp",
    "total": 500.00,
    "line_items": [],
    "currency": "USD",
    "confidence": {
        "invoice_number": 0.90,
        "vendor_name": 0.85,
        "invoice_date": 0.80,
        "total": 0.95,
        "line_items": 0.70
    }
}
```"""
        errors = []
        warnings = []
        
        invoice, confidence = agent._parse_extraction_response(
            response, errors, warnings
        )
        
        assert invoice is not None
        assert invoice.invoice_number == "INV-001"
        assert len(errors) == 0
    
    def test_parse_extraction_response_invalid_json(self, agent):
        """Test handling of invalid JSON response."""
        response = "This is not valid JSON {broken"
        errors = []
        warnings = []
        
        invoice, confidence = agent._parse_extraction_response(
            response, errors, warnings
        )
        
        assert invoice is None
        assert len(errors) == 1
        assert "JSON" in errors[0]
    
    def test_parse_extraction_response_missing_fields(self, agent):
        """Test parsing response with missing optional fields."""
        response = json.dumps({
            "invoice_number": "INV-002",
            "vendor_name": "Minimal Corp",
            "total": 250.00,
            "currency": "USD",
            "line_items": [],
            "confidence": {
                "invoice_number": 0.80,
                "vendor_name": 0.75,
                "invoice_date": 0.0,
                "total": 0.90,
                "line_items": 0.50
            }
        })
        errors = []
        warnings = []
        
        invoice, confidence = agent._parse_extraction_response(
            response, errors, warnings
        )
        
        assert invoice is not None
        assert invoice.invoice_number == "INV-002"
        assert invoice.subtotal is None
        assert invoice.tax is None
        assert invoice.po_number is None
        assert len(errors) == 0
    
    def test_validate_extraction_line_item_mismatch(self, agent):
        """Test validation detects line item sum mismatch."""
        invoice = Invoice(
            invoice_number="INV-003",
            vendor_name="Test Vendor",
            currency="USD",
            subtotal=Decimal("1000.00"),
            total=Decimal("1080.00"),
            line_items=[
                InvoiceLineItem(
                    line_number=1,
                    description="Item 1",
                    quantity=5,
                    unit_price=Decimal("100.00"),
                    amount=Decimal("500.00"),  # Should be 500, subtotal says 1000
                )
            ],
        )
        confidence = ExtractionConfidence(
            invoice_number=0.9,
            vendor_name=0.9,
            invoice_date=0.9,
            total=0.9,
            line_items=0.9,
        )
        warnings = []
        
        agent._validate_extraction(invoice, confidence, warnings)
        
        assert len(warnings) == 1
        assert "does not match subtotal" in warnings[0].lower()
    
    def test_validate_extraction_tax_calculation_error(self, agent):
        """Test validation detects tax calculation error."""
        invoice = Invoice(
            invoice_number="INV-004",
            vendor_name="Test Vendor",
            currency="USD",
            subtotal=Decimal("1000.00"),
            tax=Decimal("80.00"),
            total=Decimal("1200.00"),  # Should be 1080
            line_items=[],
        )
        confidence = ExtractionConfidence(
            invoice_number=0.9,
            vendor_name=0.9,
            invoice_date=0.9,
            total=0.9,
            line_items=0.9,
        )
        warnings = []
        
        agent._validate_extraction(invoice, confidence, warnings)
        
        assert len(warnings) == 1
        assert "does not match total" in warnings[0].lower()
    
    @pytest.mark.asyncio
    async def test_extract_success(self, agent, ocr_result_mock, valid_ai_response):
        """Test successful extraction flow."""
        # Mock OCR service
        agent.ocr_service.process_pdf = AsyncMock(return_value=ocr_result_mock)
        
        # Mock AI agent
        mock_agent = AsyncMock()
        async def mock_run_stream(prompt):
            class Chunk:
                def __init__(self, text):
                    self.text = text
            yield Chunk(valid_ai_response)
        
        mock_agent.run_stream = mock_run_stream
        agent._agent = mock_agent
        
        with patch.object(agent, '_get_agent', return_value=mock_agent):
            result = await agent.extract(Path("/test/invoice.pdf"), "invoice.pdf")
        
        assert result.status == InvoiceStatus.EXTRACTED
        assert result.invoice is not None
        assert result.invoice.invoice_number == "INV-2026-001"
        assert result.confidence.overall > 0.8
        # extraction_time_ms may be 0 in fast test environment with mocks
        assert result.extraction_time_ms >= 0
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_extract_empty_text(self, agent):
        """Test extraction with empty OCR text."""
        empty_ocr_mock = MagicMock()
        empty_ocr_mock.text = ""
        empty_ocr_mock.is_scanned = True
        empty_ocr_mock.ocr_applied = False
        empty_ocr_mock.page_count = 1
        empty_ocr_mock.file_hash = "empty123"
        
        agent.ocr_service.process_pdf = AsyncMock(return_value=empty_ocr_mock)
        
        result = await agent.extract(Path("/test/empty.pdf"), "empty.pdf")
        
        assert result.status == InvoiceStatus.FAILED
        assert result.invoice is None
        assert len(result.errors) == 1
        assert "no text" in result.errors[0].lower()
    
    @pytest.mark.asyncio
    async def test_extract_handles_exception(self, agent):
        """Test extraction handles exceptions gracefully."""
        agent.ocr_service.process_pdf = AsyncMock(
            side_effect=Exception("OCR service unavailable")
        )
        
        result = await agent.extract(Path("/test/error.pdf"), "error.pdf")
        
        assert result.status == InvoiceStatus.FAILED
        assert len(result.errors) == 1
        assert "ocr service unavailable" in result.errors[0].lower()
    
    def test_system_prompt_contains_key_fields(self):
        """Test that system prompt includes all required fields."""
        assert "invoice_number" in EXTRACTION_SYSTEM_PROMPT
        assert "vendor_name" in EXTRACTION_SYSTEM_PROMPT
        assert "total" in EXTRACTION_SYSTEM_PROMPT
        assert "line_items" in EXTRACTION_SYSTEM_PROMPT
        assert "confidence" in EXTRACTION_SYSTEM_PROMPT
        assert "po_number" in EXTRACTION_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_extract_requires_review_low_confidence(
        self, agent, ocr_result_mock
    ):
        """Test that low confidence triggers manual review."""
        low_confidence_response = json.dumps({
            "invoice_number": "INV-LOW",
            "vendor_name": "Unknown Vendor",
            "total": 100.00,
            "currency": "USD",
            "line_items": [],
            "confidence": {
                "invoice_number": 0.50,
                "vendor_name": 0.40,
                "invoice_date": 0.30,
                "total": 0.60,
                "line_items": 0.20
            }
        })
        
        agent.ocr_service.process_pdf = AsyncMock(return_value=ocr_result_mock)
        
        mock_agent = AsyncMock()
        async def mock_run_stream(prompt):
            class Chunk:
                def __init__(self, text):
                    self.text = text
            yield Chunk(low_confidence_response)
        
        mock_agent.run_stream = mock_run_stream
        agent._agent = mock_agent
        
        with patch.object(agent, '_get_agent', return_value=mock_agent):
            result = await agent.extract(Path("/test/unclear.pdf"), "unclear.pdf")
        
        assert result.requires_review is True
        assert result.confidence.overall < 0.8
