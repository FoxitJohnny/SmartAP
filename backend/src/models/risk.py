"""
SmartAP Risk Assessment Data Models

Pydantic models for fraud detection and risk assessment results.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal


class RiskLevel(str, Enum):
    """Overall risk level classification."""
    LOW = "low"              # 0.0 - 0.3
    MEDIUM = "medium"        # 0.3 - 0.6
    HIGH = "high"            # 0.6 - 0.8
    CRITICAL = "critical"    # 0.8 - 1.0


class RiskFlagType(str, Enum):
    """Types of risk flags."""
    DUPLICATE_EXACT = "duplicate_exact"              # Exact duplicate (file hash)
    DUPLICATE_NEAR = "duplicate_near"                # Near duplicate (invoice # + vendor)
    DUPLICATE_SIMILAR = "duplicate_similar"          # Similar content (embedding)
    VENDOR_NEW = "vendor_new"                        # First invoice from vendor
    VENDOR_BLOCKED = "vendor_blocked"                # Vendor is blocked
    VENDOR_BANK_CHANGE = "vendor_bank_change"        # Bank account changed
    VENDOR_SPOOFING = "vendor_spoofing"              # Possible vendor impersonation
    PRICE_SPIKE = "price_spike"                      # Price significantly higher than normal
    PRICE_ANOMALY = "price_anomaly"                  # Unusual pricing pattern
    AMOUNT_ANOMALY = "amount_anomaly"                # Amount unusually high
    AMOUNT_ROUND = "amount_round"                    # Suspiciously round amount
    PATTERN_ANOMALY = "pattern_anomaly"              # Unusual pattern detected
    MULTIPLE_INVOICES_SAME_DAY = "multiple_invoices_same_day"  # Multiple invoices same day


class RecommendedAction(str, Enum):
    """Recommended actions for risk mitigation."""
    AUTO_APPROVE = "auto_approve"              # Safe to auto-approve
    REVIEW = "review"                          # Requires manual review
    MANAGER_APPROVAL = "manager_approval"      # Requires manager approval
    INVESTIGATE = "investigate"                # Requires investigation
    REJECT = "reject"                          # Should be rejected
    CONTACT_VENDOR = "contact_vendor"          # Contact vendor for verification


class RiskFlag(BaseModel):
    """A single risk flag identified during assessment."""
    flag_type: RiskFlagType = Field(..., description="Type of risk flag")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    description: str = Field(..., description="Human-readable description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this flag (0-1)")
    
    # Evidence
    evidence: Optional[str] = Field(default=None, description="Evidence supporting this flag")
    related_invoice_id: Optional[str] = Field(default=None, description="Related invoice (for duplicates)")
    
    # Values
    expected_value: Optional[str] = Field(default=None, description="Expected value")
    actual_value: Optional[str] = Field(default=None, description="Actual value found")
    deviation: Optional[str] = Field(default=None, description="Deviation from expected")
    
    # Resolution
    requires_action: bool = Field(default=True, description="Whether action is required")
    suggested_action: Optional[str] = Field(default=None, description="Suggested mitigation action")
    
    class Config:
        json_schema_extra = {
            "example": {
                "flag_type": "price_spike",
                "severity": "medium",
                "description": "Unit price 45% higher than 6-month average",
                "confidence": 0.88,
                "evidence": "Historical avg: $850, Current: $1232",
                "expected_value": "850.00",
                "actual_value": "1232.00",
                "deviation": "+45%",
                "requires_action": True,
                "suggested_action": "Contact vendor to verify pricing"
            }
        }


class DuplicateInfo(BaseModel):
    """Information about potential duplicate invoices."""
    is_duplicate: bool = Field(..., description="Whether duplicate detected")
    duplicate_type: Optional[RiskFlagType] = Field(default=None, description="Type of duplicate")
    duplicate_invoice_id: Optional[str] = Field(default=None, description="ID of duplicate invoice")
    duplicate_invoice_number: Optional[str] = Field(default=None, description="Invoice number of duplicate")
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Similarity score")
    duplicate_processed_date: Optional[datetime] = Field(default=None, description="When duplicate was processed")


class VendorRiskInfo(BaseModel):
    """Vendor-specific risk information."""
    vendor_id: str = Field(..., description="Vendor identifier")
    vendor_name: str = Field(..., description="Vendor name")
    vendor_risk_score: float = Field(..., ge=0.0, le=1.0, description="Vendor's overall risk score")
    is_new_vendor: bool = Field(..., description="Whether this is first invoice from vendor")
    is_blocked: bool = Field(default=False, description="Whether vendor is blocked")
    active_fraud_flags: int = Field(default=0, description="Number of active fraud flags")
    
    # Historical patterns
    average_invoice_amount: Decimal = Field(default=Decimal("0.0"), description="Average invoice amount")
    invoice_amount_std_dev: Decimal = Field(default=Decimal("0.0"), description="Standard deviation of amounts")
    total_invoices: int = Field(default=0, description="Total invoices from this vendor")
    
    # Anomalies
    amount_z_score: Optional[float] = Field(default=None, description="Z-score for this invoice amount")
    is_amount_anomaly: bool = Field(default=False, description="Whether amount is anomalous")


class PriceAnomalyInfo(BaseModel):
    """Information about price anomalies for specific items."""
    item_description: str = Field(..., description="Item description")
    current_price: Decimal = Field(..., description="Current unit price")
    historical_average: Optional[Decimal] = Field(default=None, description="Historical average price")
    historical_std_dev: Optional[Decimal] = Field(default=None, description="Price standard deviation")
    price_z_score: Optional[float] = Field(default=None, description="Z-score for current price")
    is_anomaly: bool = Field(..., description="Whether price is anomalous")
    deviation_percentage: Optional[float] = Field(default=None, description="Deviation from average (%)")


class RiskAssessment(BaseModel):
    """Complete risk assessment for an invoice."""
    # Identifiers
    assessment_id: str = Field(..., description="Unique assessment ID")
    invoice_id: str = Field(..., description="Invoice document ID")
    
    # Overall risk
    risk_level: RiskLevel = Field(..., description="Overall risk classification")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score (0-1)")
    
    # Risk component scores
    duplicate_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Duplicate risk")
    vendor_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Vendor risk")
    price_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Price anomaly risk")
    amount_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Amount anomaly risk")
    pattern_risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Pattern anomaly risk")
    
    # Flags
    risk_flags: List[RiskFlag] = Field(default_factory=list, description="All risk flags identified")
    critical_flags: int = Field(default=0, description="Number of critical flags")
    high_flags: int = Field(default=0, description="Number of high severity flags")
    
    # Detailed info
    duplicate_info: Optional[DuplicateInfo] = Field(default=None, description="Duplicate detection details")
    vendor_risk_info: Optional[VendorRiskInfo] = Field(default=None, description="Vendor risk details")
    price_anomalies: List[PriceAnomalyInfo] = Field(default_factory=list, description="Price anomalies")
    
    # Recommendation
    recommended_action: RecommendedAction = Field(..., description="Recommended action")
    action_reason: str = Field(..., description="Reason for recommended action")
    requires_manual_review: bool = Field(..., description="Whether manual review required")
    
    # Additional context
    assessment_notes: Optional[str] = Field(default=None, description="Additional assessment notes")
    
    # Metadata
    assessed_at: datetime = Field(default_factory=datetime.utcnow)
    assessed_by: str = Field(default="system", description="Who/what performed assessment")
    assessment_version: str = Field(default="1.0", description="Risk engine version")
    
    @property
    def is_safe_to_auto_approve(self) -> bool:
        """Check if invoice is safe to auto-approve."""
        return (
            self.risk_level == RiskLevel.LOW and
            self.critical_flags == 0 and
            self.high_flags == 0 and
            self.recommended_action == RecommendedAction.AUTO_APPROVE
        )
    
    @property
    def requires_investigation(self) -> bool:
        """Check if invoice requires investigation."""
        return (
            self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            self.critical_flags > 0 or
            self.recommended_action in [RecommendedAction.INVESTIGATE, RecommendedAction.REJECT]
        )
    
    @property
    def flag_summary(self) -> dict:
        """Get summary of flags by severity."""
        summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for flag in self.risk_flags:
            summary[flag.severity] += 1
        return summary
    
    class Config:
        json_schema_extra = {
            "example": {
                "assessment_id": "RISK-2024-001",
                "invoice_id": "INV-2024-001",
                "risk_level": "low",
                "risk_score": 0.15,
                "duplicate_risk_score": 0.0,
                "vendor_risk_score": 0.1,
                "price_risk_score": 0.2,
                "amount_risk_score": 0.05,
                "critical_flags": 0,
                "high_flags": 0,
                "recommended_action": "auto_approve",
                "action_reason": "All checks passed, no significant risk factors",
                "requires_manual_review": False
            }
        }
