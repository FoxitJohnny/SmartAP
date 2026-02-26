"""SmartAP Risk Settings Models

Pydantic models for user-configurable risk detection settings.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RiskSettings(BaseModel):
    """Active risk detection settings returned by the API."""

    id: int
    name: str = Field(..., description="Settings profile name")

    # Component weights (should sum to 1.0)
    weight_duplicate: float = Field(0.25, ge=0.0, le=1.0)
    weight_vendor: float = Field(0.20, ge=0.0, le=1.0)
    weight_price: float = Field(0.15, ge=0.0, le=1.0)
    weight_amount: float = Field(0.10, ge=0.0, le=1.0)
    weight_matching: float = Field(0.20, ge=0.0, le=1.0)
    weight_pattern: float = Field(0.10, ge=0.0, le=1.0)

    # Price anomaly detection
    price_std_dev_threshold: float = Field(2.0, ge=0.0, description="Std devs from mean to flag")
    price_min_historical_invoices: int = Field(2, ge=1, description="Min historical invoices needed")
    price_significant_amount: float = Field(1000.0, ge=0.0, description="Only flag above this $")
    price_minor_increase: float = Field(0.15, ge=0.0, le=1.0, description="Minor increase %")
    price_major_increase: float = Field(0.30, ge=0.0, le=1.0, description="Major increase %")
    price_critical_increase: float = Field(0.50, ge=0.0, le=1.0, description="Critical increase %")

    # Duplicate detection
    duplicate_exact_days: int = Field(90, ge=1, description="Look-back days for exact dupes")
    duplicate_fuzzy_days: int = Field(30, ge=1, description="Look-back days for fuzzy dupes")
    duplicate_amount_tolerance: float = Field(0.02, ge=0.0, le=1.0, description="Amount tolerance %")

    # Vendor risk
    vendor_low_risk_threshold: float = Field(0.25, ge=0.0, le=1.0)
    vendor_medium_risk_threshold: float = Field(0.50, ge=0.0, le=1.0)
    vendor_high_risk_threshold: float = Field(0.75, ge=0.0, le=1.0)
    vendor_good_payment_reliability: float = Field(0.90, ge=0.0, le=1.0)
    vendor_acceptable_payment_reliability: float = Field(0.75, ge=0.0, le=1.0)
    vendor_inactive_days: int = Field(180, ge=1)
    vendor_new_vendor_days: int = Field(90, ge=1)

    # Metadata
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class RiskSettingsUpdate(BaseModel):
    """Partial update for risk detection settings."""

    # Component weights
    weight_duplicate: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_vendor: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_price: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_amount: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_matching: Optional[float] = Field(None, ge=0.0, le=1.0)
    weight_pattern: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Price anomaly detection
    price_std_dev_threshold: Optional[float] = Field(None, ge=0.0)
    price_min_historical_invoices: Optional[int] = Field(None, ge=1)
    price_significant_amount: Optional[float] = Field(None, ge=0.0)
    price_minor_increase: Optional[float] = Field(None, ge=0.0, le=1.0)
    price_major_increase: Optional[float] = Field(None, ge=0.0, le=1.0)
    price_critical_increase: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Duplicate detection
    duplicate_exact_days: Optional[int] = Field(None, ge=1)
    duplicate_fuzzy_days: Optional[int] = Field(None, ge=1)
    duplicate_amount_tolerance: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Vendor risk
    vendor_low_risk_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    vendor_medium_risk_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    vendor_high_risk_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    vendor_good_payment_reliability: Optional[float] = Field(None, ge=0.0, le=1.0)
    vendor_acceptable_payment_reliability: Optional[float] = Field(None, ge=0.0, le=1.0)
    vendor_inactive_days: Optional[int] = Field(None, ge=1)
    vendor_new_vendor_days: Optional[int] = Field(None, ge=1)

    updated_by: Optional[str] = None
