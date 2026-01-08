"""
SmartAP Invoice Data Models

Pydantic models for invoice data extraction and processing.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from enum import Enum
from decimal import Decimal


class InvoiceStatus(str, Enum):
    """Invoice processing status."""
    INGESTED = "ingested"
    EXTRACTED = "extracted"
    MATCHED = "matched"
    RISK_REVIEW = "risk_review"
    APPROVED = "approved"
    READY_FOR_PAYMENT = "ready_for_payment"
    ARCHIVED = "archived"
    FAILED = "failed"


class ExtractionConfidence(BaseModel):
    """Confidence scores for extracted fields."""
    invoice_number: float = Field(default=0.0, ge=0.0, le=1.0)
    vendor_name: float = Field(default=0.0, ge=0.0, le=1.0)
    invoice_date: float = Field(default=0.0, ge=0.0, le=1.0)
    due_date: float = Field(default=0.0, ge=0.0, le=1.0)
    subtotal: float = Field(default=0.0, ge=0.0, le=1.0)
    tax: float = Field(default=0.0, ge=0.0, le=1.0)
    total: float = Field(default=0.0, ge=0.0, le=1.0)
    line_items: float = Field(default=0.0, ge=0.0, le=1.0)
    
    @property
    def overall(self) -> float:
        """Calculate overall confidence as average of all fields."""
        scores = [
            self.invoice_number,
            self.vendor_name,
            self.invoice_date,
            self.total,
            self.line_items,
        ]
        return sum(scores) / len(scores)


class InvoiceLineItem(BaseModel):
    """A single line item on an invoice."""
    description: str = Field(..., description="Item description")
    quantity: Optional[float] = Field(default=None, description="Quantity ordered")
    unit_price: Optional[Decimal] = Field(default=None, description="Price per unit")
    amount: Optional[Decimal] = Field(default=None, description="Total amount for line item")
    sku: Optional[str] = Field(default=None, description="SKU or product code")
    unit: Optional[str] = Field(default=None, description="Unit of measure")


class Invoice(BaseModel):
    """Extracted invoice data."""
    # Header fields
    invoice_number: str = Field(..., description="Invoice number/ID")
    vendor_name: str = Field(..., description="Vendor/supplier name")
    vendor_address: Optional[str] = Field(default=None, description="Vendor address")
    vendor_tax_id: Optional[str] = Field(default=None, description="Vendor tax ID")
    
    # Dates
    invoice_date: Optional[date] = Field(default=None, description="Invoice date")
    due_date: Optional[date] = Field(default=None, description="Payment due date")
    
    # Amounts
    currency: str = Field(default="USD", description="Currency code")
    subtotal: Optional[Decimal] = Field(default=None, description="Subtotal before tax")
    tax: Optional[Decimal] = Field(default=None, description="Tax amount")
    total: Decimal = Field(..., description="Total invoice amount")
    
    # Line items
    line_items: list[InvoiceLineItem] = Field(default_factory=list, description="Invoice line items")
    
    # Payment info
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    bank_account: Optional[str] = Field(default=None, description="Bank account for payment")
    
    # Reference
    po_number: Optional[str] = Field(default=None, description="Purchase order reference")


class InvoiceExtractionResult(BaseModel):
    """Result of invoice extraction process."""
    # Identifiers
    document_id: str = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original file name")
    file_hash: str = Field(..., description="Document hash for deduplication")
    
    # Status
    status: InvoiceStatus = Field(default=InvoiceStatus.EXTRACTED)
    
    # Extracted data
    invoice: Optional[Invoice] = Field(default=None, description="Extracted invoice data")
    
    # Confidence
    confidence: ExtractionConfidence = Field(default_factory=ExtractionConfidence)
    requires_review: bool = Field(default=False, description="Whether manual review is needed")
    
    # Metadata
    ocr_applied: bool = Field(default=False, description="Whether OCR was applied")
    page_count: int = Field(default=1, description="Number of pages")
    extraction_time_ms: int = Field(default=0, description="Extraction time in milliseconds")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Errors
    errors: list[str] = Field(default_factory=list, description="Extraction errors")
    warnings: list[str] = Field(default_factory=list, description="Extraction warnings")
