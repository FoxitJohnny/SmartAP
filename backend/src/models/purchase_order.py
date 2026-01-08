"""
SmartAP Purchase Order Data Models

Pydantic models for purchase orders and line items.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum
from decimal import Decimal


class POStatus(str, Enum):
    """Purchase order status."""
    OPEN = "open"
    PARTIALLY_RECEIVED = "partially_received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class POLineItem(BaseModel):
    """A single line item on a purchase order."""
    line_number: int = Field(..., description="Line item number")
    description: str = Field(..., description="Item description")
    quantity: float = Field(..., description="Quantity ordered", gt=0)
    unit_price: Decimal = Field(..., description="Price per unit", ge=0)
    amount: Decimal = Field(..., description="Total amount for line item", ge=0)
    sku: Optional[str] = Field(default=None, description="SKU or product code")
    unit: Optional[str] = Field(default=None, description="Unit of measure (ea, box, etc)")
    received_quantity: float = Field(default=0.0, description="Quantity received so far", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "line_number": 1,
                "description": "Dell XPS 15 Laptop",
                "quantity": 5,
                "unit_price": "1299.99",
                "amount": "6499.95",
                "sku": "DELL-XPS15-2024",
                "unit": "ea",
                "received_quantity": 0
            }
        }


class PurchaseOrder(BaseModel):
    """Purchase order details."""
    # Identifiers
    po_number: str = Field(..., description="Purchase order number")
    po_id: Optional[str] = Field(default=None, description="Internal PO ID")
    
    # Vendor
    vendor_id: str = Field(..., description="Vendor identifier")
    vendor_name: str = Field(..., description="Vendor name")
    
    # Dates
    created_date: date = Field(..., description="PO creation date")
    expected_delivery: Optional[date] = Field(default=None, description="Expected delivery date")
    
    # Status
    status: POStatus = Field(default=POStatus.OPEN, description="PO status")
    
    # Line items
    line_items: List[POLineItem] = Field(..., description="PO line items", min_length=1)
    
    # Amounts
    currency: str = Field(default="USD", description="Currency code")
    subtotal: Decimal = Field(..., description="Subtotal before tax", ge=0)
    tax: Optional[Decimal] = Field(default=None, description="Tax amount", ge=0)
    total_amount: Decimal = Field(..., description="Total PO amount", ge=0)
    
    # Additional info
    ship_to_address: Optional[str] = Field(default=None, description="Shipping address")
    bill_to_address: Optional[str] = Field(default=None, description="Billing address")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    
    # Metadata
    created_by: Optional[str] = Field(default=None, description="User who created the PO")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def is_fully_received(self) -> bool:
        """Check if all line items have been fully received."""
        return all(
            item.received_quantity >= item.quantity 
            for item in self.line_items
        )
    
    @property
    def is_partially_received(self) -> bool:
        """Check if any line items have been partially received."""
        return any(
            0 < item.received_quantity < item.quantity 
            for item in self.line_items
        )
    
    @property
    def received_percentage(self) -> float:
        """Calculate percentage of order received."""
        total_ordered = sum(item.quantity for item in self.line_items)
        total_received = sum(item.received_quantity for item in self.line_items)
        return (total_received / total_ordered * 100) if total_ordered > 0 else 0.0
    
    class Config:
        json_schema_extra = {
            "example": {
                "po_number": "PO-2024-001",
                "vendor_id": "VND-001",
                "vendor_name": "Tech Supplies Inc",
                "created_date": "2024-12-01",
                "expected_delivery": "2024-12-15",
                "status": "open",
                "line_items": [
                    {
                        "line_number": 1,
                        "description": "Dell XPS 15 Laptop",
                        "quantity": 5,
                        "unit_price": "1299.99",
                        "amount": "6499.95",
                        "sku": "DELL-XPS15-2024"
                    }
                ],
                "currency": "USD",
                "subtotal": "6499.95",
                "tax": "520.00",
                "total_amount": "7019.95",
                "payment_terms": "Net 30"
            }
        }
