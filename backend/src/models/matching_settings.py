"""SmartAP Matching Settings Models

Pydantic models for user-configurable PO matching settings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MatchingSettings(BaseModel):
    """Active matching settings returned by the API."""

    id: int
    name: str = Field(..., description="Settings profile name")

    vendor_fuzzy_threshold: float = Field(0.80, ge=0.0, le=1.0)
    vendor_match_weight: float = Field(0.30, ge=0.0)

    amount_tolerance_percent: float = Field(0.20, ge=0.0, le=1.0)
    amount_match_tolerance: float = Field(0.05, ge=0.0, le=1.0)
    amount_match_weight: float = Field(0.30, ge=0.0)

    date_tolerance_days: int = Field(30, ge=0)
    date_match_weight: float = Field(0.10, ge=0.0)

    line_items_match_weight: float = Field(0.30, ge=0.0)
    line_item_description_threshold: float = Field(0.70, ge=0.0, le=1.0)
    line_item_amount_tolerance: float = Field(0.10, ge=0.0, le=1.0)

    exact_match_threshold: float = Field(0.95, ge=0.0, le=1.0)
    good_match_threshold: float = Field(0.85, ge=0.0, le=1.0)
    acceptable_match_threshold: float = Field(0.70, ge=0.0, le=1.0)
    review_threshold: float = Field(0.60, ge=0.0, le=1.0)

    use_ai_for_ambiguous: bool = True
    ai_confidence_threshold: float = Field(0.75, ge=0.0, le=1.0)

    max_amount_discrepancy_for_auto_approve: float = Field(100.0, ge=0.0)
    critical_discrepancy_blocks_approval: bool = True

    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class MatchingSettingsUpdate(BaseModel):
    """Partial update for matching settings."""

    vendor_fuzzy_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    vendor_match_weight: Optional[float] = Field(None, ge=0.0)

    amount_tolerance_percent: Optional[float] = Field(None, ge=0.0, le=1.0)
    amount_match_tolerance: Optional[float] = Field(None, ge=0.0, le=1.0)
    amount_match_weight: Optional[float] = Field(None, ge=0.0)

    date_tolerance_days: Optional[int] = Field(None, ge=0)
    date_match_weight: Optional[float] = Field(None, ge=0.0)

    line_items_match_weight: Optional[float] = Field(None, ge=0.0)
    line_item_description_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    line_item_amount_tolerance: Optional[float] = Field(None, ge=0.0, le=1.0)

    exact_match_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    good_match_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    acceptable_match_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    review_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    use_ai_for_ambiguous: Optional[bool] = None
    ai_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    max_amount_discrepancy_for_auto_approve: Optional[float] = Field(None, ge=0.0)
    critical_discrepancy_blocks_approval: Optional[bool] = None

    updated_by: Optional[str] = None
