"""
Invoice Test Fixtures

Provides sample invoice data, PDF content, and helpers for invoice testing.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from io import BytesIO

from src.models import (
    Invoice,
    InvoiceLineItem,
    InvoiceExtractionResult,
    ExtractionConfidence,
    InvoiceStatus,
)


# Minimal valid PDF content for upload testing
INVOICE_PDF_CONTENT = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 200 >>
stream
BT
/F1 24 Tf
50 750 Td
(INVOICE) Tj
/F1 12 Tf
0 -30 Td
(Invoice Number: INV-2026-001) Tj
0 -20 Td
(Date: January 9, 2026) Tj
0 -20 Td
(Vendor: Test Vendor Inc.) Tj
0 -20 Td
(Total: $1,500.00) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
566
%%EOF
"""


# Sample invoice data for various test scenarios
SAMPLE_INVOICES: Dict[str, Dict[str, Any]] = {
    "standard": {
        "invoice_number": "INV-2026-001",
        "vendor_name": "Tech Supplies Inc.",
        "invoice_date": date(2026, 1, 5),
        "due_date": date(2026, 2, 5),
        "currency": "USD",
        "subtotal": Decimal("1388.89"),
        "tax": Decimal("111.11"),
        "total": Decimal("1500.00"),
        "po_number": "PO-2026-001",
        "line_items": [
            {
                "description": "Laptop Computer",
                "quantity": 1,
                "unit_price": Decimal("1200.00"),
                "amount": Decimal("1200.00"),
            },
            {
                "description": "Wireless Mouse",
                "quantity": 5,
                "unit_price": Decimal("37.78"),
                "amount": Decimal("188.89"),
            },
        ],
    },
    "high_value": {
        "invoice_number": "INV-2026-HV-001",
        "vendor_name": "Enterprise Solutions Corp.",
        "invoice_date": date(2026, 1, 8),
        "due_date": date(2026, 2, 8),
        "currency": "USD",
        "subtotal": Decimal("92592.59"),
        "tax": Decimal("7407.41"),
        "total": Decimal("100000.00"),
        "po_number": "PO-2026-HV-001",
        "line_items": [
            {
                "description": "Enterprise Software License",
                "quantity": 1,
                "unit_price": Decimal("75000.00"),
                "amount": Decimal("75000.00"),
            },
            {
                "description": "Implementation Services",
                "quantity": 40,
                "unit_price": Decimal("439.81"),
                "amount": Decimal("17592.59"),
            },
        ],
    },
    "duplicate_candidate": {
        "invoice_number": "INV-2026-001",  # Same as standard
        "vendor_name": "Tech Supplies Inc.",
        "invoice_date": date(2026, 1, 5),
        "due_date": date(2026, 2, 5),
        "currency": "USD",
        "subtotal": Decimal("1388.89"),
        "tax": Decimal("111.11"),
        "total": Decimal("1500.00"),
        "po_number": "PO-2026-001",
    },
    "no_po": {
        "invoice_number": "INV-2026-NP-001",
        "vendor_name": "Freelance Services",
        "invoice_date": date(2026, 1, 7),
        "due_date": date(2026, 1, 21),  # Net 14
        "currency": "USD",
        "subtotal": Decimal("925.93"),
        "tax": Decimal("74.07"),
        "total": Decimal("1000.00"),
        "po_number": None,
        "line_items": [
            {
                "description": "Consulting Services",
                "quantity": 8,
                "unit_price": Decimal("115.74"),
                "amount": Decimal("925.93"),
            },
        ],
    },
    "foreign_currency": {
        "invoice_number": "INV-2026-EUR-001",
        "vendor_name": "European Supplies GmbH",
        "invoice_date": date(2026, 1, 6),
        "due_date": date(2026, 2, 6),
        "currency": "EUR",
        "subtotal": Decimal("840.34"),
        "tax": Decimal("159.66"),  # 19% VAT
        "total": Decimal("1000.00"),
        "po_number": "PO-2026-EUR-001",
    },
    "past_due": {
        "invoice_number": "INV-2025-PD-001",
        "vendor_name": "Late Payment Vendor",
        "invoice_date": date(2025, 11, 1),
        "due_date": date(2025, 12, 1),  # Past due
        "currency": "USD",
        "subtotal": Decimal("462.96"),
        "tax": Decimal("37.04"),
        "total": Decimal("500.00"),
        "po_number": "PO-2025-001",
    },
    "multi_page": {
        "invoice_number": "INV-2026-MP-001",
        "vendor_name": "Bulk Supplies Co.",
        "invoice_date": date(2026, 1, 9),
        "due_date": date(2026, 2, 9),
        "currency": "USD",
        "subtotal": Decimal("4629.63"),
        "tax": Decimal("370.37"),
        "total": Decimal("5000.00"),
        "po_number": "PO-2026-BULK-001",
        "line_items": [
            {"description": f"Item {i}", "quantity": i, "unit_price": Decimal("100.00"), "amount": Decimal(str(i * 100))}
            for i in range(1, 51)  # 50 line items
        ],
    },
    "low_confidence": {
        "invoice_number": "INV-2026-LC-001",
        "vendor_name": "Unclear Vendor",
        "invoice_date": date(2026, 1, 4),
        "due_date": date(2026, 2, 4),
        "currency": "USD",
        "subtotal": Decimal("277.78"),
        "tax": Decimal("22.22"),
        "total": Decimal("300.00"),
        "confidence_override": 0.45,  # Below threshold
    },
}


def create_sample_invoice(
    scenario: str = "standard",
    **overrides,
) -> Invoice:
    """
    Create an Invoice instance from a sample scenario.
    
    Args:
        scenario: Name of the scenario from SAMPLE_INVOICES
        **overrides: Fields to override from the scenario
    
    Returns:
        Invoice instance
    """
    if scenario not in SAMPLE_INVOICES:
        raise ValueError(f"Unknown scenario: {scenario}. Available: {list(SAMPLE_INVOICES.keys())}")
    
    data = {**SAMPLE_INVOICES[scenario], **overrides}
    
    # Handle line items
    line_item_data = data.pop("line_items", [])
    data.pop("confidence_override", None)
    
    line_items = [
        InvoiceLineItem(**item) for item in line_item_data
    ] if line_item_data else []
    
    return Invoice(
        **data,
        line_items=line_items,
    )


def create_invoice_batch(
    scenarios: Optional[List[str]] = None,
    count: int = 5,
) -> List[Invoice]:
    """
    Create multiple invoices from scenarios.
    
    Args:
        scenarios: List of scenario names to use (cycles if count > len)
        count: Number of invoices to create
    
    Returns:
        List of Invoice instances
    """
    if scenarios is None:
        scenarios = ["standard", "high_value", "no_po", "foreign_currency", "past_due"]
    
    invoices = []
    for i in range(count):
        scenario = scenarios[i % len(scenarios)]
        invoice = create_sample_invoice(
            scenario,
            invoice_number=f"{SAMPLE_INVOICES[scenario]['invoice_number']}-{i+1}",
        )
        invoices.append(invoice)
    
    return invoices


def create_invoice_with_line_items(
    line_count: int = 3,
    base_price: Decimal = Decimal("100.00"),
    **invoice_overrides,
) -> Invoice:
    """
    Create an invoice with specified number of line items.
    
    Args:
        line_count: Number of line items to create
        base_price: Base unit price for items
        **invoice_overrides: Additional invoice fields
    
    Returns:
        Invoice instance with line items
    """
    line_items = []
    subtotal = Decimal("0")
    
    for i in range(1, line_count + 1):
        quantity = float(i)
        unit_price = base_price * i
        amount = unit_price * Decimal(str(quantity))
        subtotal += amount
        
        line_items.append(InvoiceLineItem(
            description=f"Test Item {i}",
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
        ))
    
    tax = subtotal * Decimal("0.08")
    total = subtotal + tax
    
    return Invoice(
        invoice_number=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        vendor_name="Test Vendor",
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        currency="USD",
        subtotal=subtotal,
        tax=tax,
        total=total,
        line_items=line_items,
        **invoice_overrides,
    )


def create_extraction_result(
    invoice: Optional[Invoice] = None,
    status: InvoiceStatus = InvoiceStatus.EXTRACTED,
    confidence: float = 0.95,
    requires_review: bool = False,
    document_id: Optional[str] = None,
) -> InvoiceExtractionResult:
    """
    Create an InvoiceExtractionResult for testing.
    
    Args:
        invoice: Invoice data (created if not provided)
        status: Extraction status
        confidence: Overall confidence score
        requires_review: Whether review is needed
        document_id: Document ID (auto-generated if not provided)
    
    Returns:
        InvoiceExtractionResult instance
    """
    if invoice is None:
        invoice = create_sample_invoice()
    
    doc_id = document_id or f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return InvoiceExtractionResult(
        document_id=doc_id,
        file_name=f"{doc_id}.pdf",
        file_hash=f"sha256:{hash(doc_id):x}",
        status=status,
        invoice=invoice,
        confidence=ExtractionConfidence(
            overall=confidence,
            invoice_number=confidence,
            vendor_name=confidence,
            amounts=confidence,
            dates=confidence,
            line_items=confidence,
        ),
        requires_review=requires_review,
        ocr_applied=confidence < 0.8,
        page_count=1,
        extraction_time_ms=350,
    )


def get_test_pdf_file(content: bytes = INVOICE_PDF_CONTENT) -> BytesIO:
    """
    Get a BytesIO object containing test PDF content.
    
    Args:
        content: PDF bytes (uses default if not provided)
    
    Returns:
        BytesIO object for file upload testing
    """
    return BytesIO(content)


def create_upload_file_tuple(
    filename: str = "test_invoice.pdf",
    content: bytes = INVOICE_PDF_CONTENT,
    content_type: str = "application/pdf",
) -> tuple:
    """
    Create a tuple suitable for httpx file uploads.
    
    Returns:
        Tuple of (filename, content, content_type)
    """
    return (filename, BytesIO(content), content_type)


# Scenario-specific extraction results
EXTRACTION_SCENARIOS = {
    "success": lambda: create_extraction_result(
        confidence=0.95,
        requires_review=False,
    ),
    "low_confidence": lambda: create_extraction_result(
        confidence=0.45,
        requires_review=True,
        status=InvoiceStatus.NEEDS_REVIEW,
    ),
    "ocr_required": lambda: create_extraction_result(
        confidence=0.75,
        requires_review=True,
    ),
    "failed": lambda: InvoiceExtractionResult(
        document_id="DOC-FAILED",
        file_name="failed.pdf",
        file_hash="sha256:failed",
        status=InvoiceStatus.FAILED,
        invoice=None,
        confidence=ExtractionConfidence(overall=0.0),
        requires_review=True,
        ocr_applied=True,
        page_count=1,
        extraction_time_ms=1000,
        error_message="Failed to extract invoice data",
    ),
}


def get_extraction_scenario(scenario: str) -> InvoiceExtractionResult:
    """Get a pre-configured extraction result scenario."""
    if scenario not in EXTRACTION_SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    return EXTRACTION_SCENARIOS[scenario]()
