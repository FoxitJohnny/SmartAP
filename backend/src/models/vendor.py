"""
SmartAP Vendor Data Models

Pydantic models for vendor profiles and risk history.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import date, datetime
from enum import Enum
from decimal import Decimal


class VendorStatus(str, Enum):
    """Vendor status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


class FraudFlagType(str, Enum):
    """Types of fraud flags."""
    DUPLICATE_INVOICE = "duplicate_invoice"
    BANK_ACCOUNT_CHANGE = "bank_account_change"
    SUSPICIOUS_AMOUNT = "suspicious_amount"
    PRICE_ANOMALY = "price_anomaly"
    VENDOR_SPOOFING = "vendor_spoofing"
    UNUSUAL_PATTERN = "unusual_pattern"


class PaymentRecord(BaseModel):
    """Historical payment record for a vendor."""
    payment_id: str = Field(..., description="Payment identifier")
    invoice_number: str = Field(..., description="Related invoice number")
    amount: Decimal = Field(..., description="Payment amount", gt=0)
    payment_date: date = Field(..., description="Date payment was made")
    days_to_pay: int = Field(..., description="Days from invoice to payment", ge=0)
    currency: str = Field(default="USD", description="Currency code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_id": "PAY-2024-001",
                "invoice_number": "INV-2024-001",
                "amount": "5000.00",
                "payment_date": "2024-01-15",
                "days_to_pay": 28,
                "currency": "USD"
            }
        }


class FraudFlag(BaseModel):
    """Fraud or risk flag associated with a vendor."""
    flag_id: str = Field(..., description="Flag identifier")
    flag_type: FraudFlagType = Field(..., description="Type of fraud flag")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    description: str = Field(..., description="Description of the flag")
    flagged_date: datetime = Field(default_factory=datetime.utcnow)
    invoice_id: Optional[str] = Field(default=None, description="Related invoice ID")
    resolved: bool = Field(default=False, description="Whether flag has been resolved")
    resolved_date: Optional[datetime] = Field(default=None, description="Date flag was resolved")
    resolved_by: Optional[str] = Field(default=None, description="User who resolved the flag")
    notes: Optional[str] = Field(default=None, description="Resolution notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "flag_id": "FLAG-2024-001",
                "flag_type": "price_anomaly",
                "severity": "medium",
                "description": "Unit price 50% higher than historical average",
                "invoice_id": "INV-2024-045",
                "resolved": False
            }
        }


class VendorRiskProfile(BaseModel):
    """Risk assessment profile for a vendor."""
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall risk score (0-1)")
    payment_reliability_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Payment history score")
    fraud_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Fraud risk score")
    price_stability_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Price stability score")
    
    total_invoices_processed: int = Field(default=0, ge=0, description="Total invoices processed")
    total_amount_paid: float = Field(default=0.0, ge=0, description="Total amount paid to vendor")
    average_invoice_amount: float = Field(default=0.0, ge=0, description="Average invoice amount")
    average_days_to_pay: float = Field(default=0.0, ge=0, description="Average payment time in days")
    
    last_payment_date: Optional[date] = Field(default=None, description="Date of last payment")
    last_risk_assessment_date: datetime = Field(default_factory=datetime.utcnow)
    
    active_fraud_flags: int = Field(default=0, ge=0, description="Number of unresolved fraud flags")
    total_fraud_flags: int = Field(default=0, ge=0, description="Total fraud flags (all time)")


class Vendor(BaseModel):
    """Vendor profile and information."""
    # Identifiers
    vendor_id: str = Field(..., description="Unique vendor identifier")
    vendor_name: str = Field(..., description="Vendor legal name")
    
    # Contact info
    contact_name: Optional[str] = Field(default=None, description="Primary contact name")
    email: Optional[EmailStr] = Field(default=None, description="Contact email")
    phone: Optional[str] = Field(default=None, description="Contact phone")
    website: Optional[str] = Field(default=None, description="Vendor website")
    
    # Address
    address_line1: Optional[str] = Field(default=None, description="Address line 1")
    address_line2: Optional[str] = Field(default=None, description="Address line 2")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State/Province")
    postal_code: Optional[str] = Field(default=None, description="Postal code")
    country: str = Field(default="US", description="Country code")
    
    # Tax & Banking
    tax_id: Optional[str] = Field(default=None, description="Tax identification number")
    bank_account_number: Optional[str] = Field(default=None, description="Bank account number (last 4 digits)")
    bank_name: Optional[str] = Field(default=None, description="Bank name")
    bank_routing_number: Optional[str] = Field(default=None, description="Bank routing number")
    
    # Status & Terms
    status: VendorStatus = Field(default=VendorStatus.ACTIVE, description="Vendor status")
    payment_terms: str = Field(default="Net 30", description="Default payment terms")
    currency: str = Field(default="USD", description="Default currency")
    
    # Risk profile
    risk_profile: VendorRiskProfile = Field(default_factory=VendorRiskProfile)
    
    # History
    payment_history: List[PaymentRecord] = Field(default_factory=list, description="Payment history")
    fraud_flags: List[FraudFlag] = Field(default_factory=list, description="Fraud flags")
    
    # Metadata
    onboarded_date: date = Field(..., description="Date vendor was added to system")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None, description="User who created vendor record")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    
    @property
    def is_active(self) -> bool:
        """Check if vendor is active."""
        return self.status == VendorStatus.ACTIVE
    
    @property
    def has_active_fraud_flags(self) -> bool:
        """Check if vendor has unresolved fraud flags."""
        return any(not flag.resolved for flag in self.fraud_flags)
    
    @property
    def is_high_risk(self) -> bool:
        """Check if vendor is considered high risk."""
        return self.risk_profile.risk_score > 0.7
    
    class Config:
        json_schema_extra = {
            "example": {
                "vendor_id": "VND-001",
                "vendor_name": "Tech Supplies Inc",
                "contact_name": "John Smith",
                "email": "john@techsupplies.com",
                "phone": "+1-555-0100",
                "address_line1": "123 Tech Street",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94102",
                "country": "US",
                "tax_id": "12-3456789",
                "bank_account_number": "****1234",
                "status": "active",
                "payment_terms": "Net 30",
                "onboarded_date": "2023-01-15"
            }
        }
