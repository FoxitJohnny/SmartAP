"""
SmartAP Matching Data Models

Pydantic models for invoice-PO matching results and discrepancies.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from decimal import Decimal


class MatchType(str, Enum):
    """Type of match between invoice and PO."""
    EXACT = "exact"              # Exact PO number match
    FUZZY = "fuzzy"              # Fuzzy match on vendor + amount
    LINE_ITEM = "line_item"      # Matched by line items
    MANUAL = "manual"            # Manually matched
    NO_MATCH = "no_match"        # No match found


class DiscrepancyType(str, Enum):
    """Types of discrepancies between invoice and PO."""
    PRICE_MISMATCH = "price_mismatch"
    QUANTITY_MISMATCH = "quantity_mismatch"
    MISSING_LINE_ITEM = "missing_line_item"
    EXTRA_LINE_ITEM = "extra_line_item"
    AMOUNT_TOLERANCE_EXCEEDED = "amount_tolerance_exceeded"
    DATE_MISMATCH = "date_mismatch"
    VENDOR_MISMATCH = "vendor_mismatch"
    DESCRIPTION_MISMATCH = "description_mismatch"


class DiscrepancySeverity(str, Enum):
    """Severity of discrepancy."""
    LOW = "low"          # Within tolerance, informational only
    MEDIUM = "medium"    # Requires review but likely acceptable
    HIGH = "high"        # Significant issue, requires approval
    CRITICAL = "critical" # Must be resolved before payment


class Discrepancy(BaseModel):
    """A single discrepancy found during matching."""
    discrepancy_type: DiscrepancyType = Field(..., description="Type of discrepancy")
    severity: DiscrepancySeverity = Field(..., description="Severity level")
    description: str = Field(..., description="Human-readable description")
    
    # Line item info (if applicable)
    line_number: Optional[int] = Field(default=None, description="Line item number")
    item_description: Optional[str] = Field(default=None, description="Item description")
    
    # Values
    invoice_value: Optional[str] = Field(default=None, description="Value from invoice")
    po_value: Optional[str] = Field(default=None, description="Value from PO")
    difference: Optional[str] = Field(default=None, description="Calculated difference")
    difference_percentage: Optional[float] = Field(default=None, description="Difference as percentage")
    
    # Resolution
    requires_approval: bool = Field(default=False, description="Whether approval is required")
    resolution_notes: Optional[str] = Field(default=None, description="Notes about resolution")
    
    class Config:
        json_schema_extra = {
            "example": {
                "discrepancy_type": "price_mismatch",
                "severity": "medium",
                "description": "Unit price on invoice differs from PO",
                "line_number": 1,
                "item_description": "Dell XPS 15 Laptop",
                "invoice_value": "1350.00",
                "po_value": "1299.99",
                "difference": "50.01",
                "difference_percentage": 3.85,
                "requires_approval": True
            }
        }


class LineItemMatch(BaseModel):
    """Match information for a single line item."""
    invoice_line_number: int = Field(..., description="Line number on invoice")
    po_line_number: Optional[int] = Field(default=None, description="Matched line number on PO")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Match confidence (0-1)")
    description_similarity: float = Field(..., ge=0.0, le=1.0, description="Description similarity")
    matched: bool = Field(..., description="Whether line was successfully matched")
    discrepancies: List[Discrepancy] = Field(default_factory=list, description="Line-level discrepancies")


class MatchingResult(BaseModel):
    """Result of invoice-to-PO matching process."""
    # Identifiers
    matching_id: str = Field(..., description="Unique matching ID")
    invoice_id: str = Field(..., description="Invoice document ID")
    po_id: Optional[str] = Field(default=None, description="Matched PO ID")
    po_number: Optional[str] = Field(default=None, description="Matched PO number")
    
    # Match details
    match_type: MatchType = Field(..., description="Type of match")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Overall match confidence (0-1)")
    matched: bool = Field(..., description="Whether a match was found")
    
    # Matching scores breakdown
    vendor_match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Vendor name similarity")
    amount_match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Amount comparison score")
    date_match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Date proximity score")
    line_items_match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Line items match score")
    
    # Line item matching
    line_item_matches: List[LineItemMatch] = Field(default_factory=list, description="Line-by-line matching")
    
    # Discrepancies
    discrepancies: List[Discrepancy] = Field(default_factory=list, description="All discrepancies found")
    has_discrepancies: bool = Field(default=False, description="Whether any discrepancies exist")
    critical_discrepancies: int = Field(default=0, description="Number of critical discrepancies")
    
    # Approval requirements
    requires_approval: bool = Field(default=False, description="Whether manual approval needed")
    approval_reason: Optional[str] = Field(default=None, description="Reason approval is required")
    
    # Additional info
    candidate_pos: List[str] = Field(default_factory=list, description="Other PO candidates considered")
    matching_algorithm: str = Field(default="fuzzy_matching_v1", description="Algorithm used")
    
    # Metadata
    matched_at: datetime = Field(default_factory=datetime.utcnow)
    matched_by: Optional[str] = Field(default=None, description="User or system that performed match")
    
    @property
    def is_high_confidence_match(self) -> bool:
        """Check if match is high confidence (>0.9)."""
        return self.matched and self.match_score > 0.9
    
    @property
    def is_acceptable_match(self) -> bool:
        """Check if match is acceptable (>0.85 and no critical discrepancies)."""
        return (
            self.matched and 
            self.match_score > 0.85 and 
            self.critical_discrepancies == 0
        )
    
    @property
    def discrepancy_summary(self) -> dict:
        """Get summary of discrepancies by severity."""
        summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for disc in self.discrepancies:
            summary[disc.severity.value] += 1
        return summary
    
    class Config:
        json_schema_extra = {
            "example": {
                "matching_id": "MATCH-2024-001",
                "invoice_id": "INV-2024-001",
                "po_id": "PO-2024-001",
                "po_number": "PO-2024-001",
                "match_type": "exact",
                "match_score": 0.95,
                "matched": True,
                "vendor_match_score": 1.0,
                "amount_match_score": 0.98,
                "date_match_score": 0.90,
                "line_items_match_score": 0.92,
                "has_discrepancies": True,
                "critical_discrepancies": 0,
                "requires_approval": False,
                "discrepancies": [
                    {
                        "discrepancy_type": "price_mismatch",
                        "severity": "low",
                        "description": "Minor price difference within tolerance",
                        "line_number": 1,
                        "difference_percentage": 1.5
                    }
                ]
            }
        }
