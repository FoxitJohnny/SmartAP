"""
Vendor Risk Analyzer

Analyzes vendor risk based on history, patterns, and fraud flags.
"""

from typing import Optional
from datetime import datetime, timedelta

from ..models import Vendor, VendorRiskInfo, RiskLevel
from ..db.repositories import VendorRepository


class VendorRiskAnalyzer:
    """Service for analyzing vendor risk."""
    
    # Risk thresholds
    LOW_RISK_THRESHOLD = 0.25
    MEDIUM_RISK_THRESHOLD = 0.50
    HIGH_RISK_THRESHOLD = 0.75
    
    # Payment history thresholds
    GOOD_PAYMENT_RATE = 0.90
    ACCEPTABLE_PAYMENT_RATE = 0.75
    
    # Activity thresholds
    INACTIVE_DAYS = 180
    NEW_VENDOR_DAYS = 90
    
    def __init__(self, vendor_repo: VendorRepository):
        self.vendor_repo = vendor_repo
    
    async def analyze_vendor_risk(
        self,
        vendor_id: str
    ) -> tuple[float, Optional[VendorRiskInfo]]:
        """
        Analyze vendor risk.
        
        Returns:
            Tuple of (risk_score, risk_info)
        """
        # Get vendor from database
        vendor_db = await self.vendor_repo.get_by_id(vendor_id)
        
        if not vendor_db:
            # Unknown vendor = high risk
            return 0.80, VendorRiskInfo(
                vendor_id=vendor_id,
                vendor_name="Unknown",
                vendor_status="unknown",
                risk_score=0.80,
                on_time_payment_rate=0.0,
                invoice_count=0,
                days_since_last_payment=9999,
                has_fraud_flags=False,
                is_new_vendor=True,
                is_inactive=False,
            )
        
        # Parse vendor data
        vendor = Vendor.model_validate(vendor_db)
        risk_profile = vendor.risk_profile
        
        # Calculate risk components
        risk_score = 0.0
        
        # 1. Base risk from profile (40%)
        base_risk = risk_profile.risk_score
        risk_score += base_risk * 0.40
        
        # 2. Payment history risk (30%)
        payment_risk = self._calculate_payment_risk(risk_profile.on_time_payment_rate)
        risk_score += payment_risk * 0.30
        
        # 3. Activity risk (20%)
        activity_risk = self._calculate_activity_risk(
            risk_profile.days_since_last_payment,
            risk_profile.invoice_count,
            vendor.onboarded_date
        )
        risk_score += activity_risk * 0.20
        
        # 4. Fraud flag risk (10%)
        fraud_risk = 1.0 if risk_profile.has_fraud_history else 0.0
        risk_score += fraud_risk * 0.10
        
        # Create risk info
        is_new = self._is_new_vendor(vendor.onboarded_date)
        is_inactive = self._is_inactive_vendor(risk_profile.days_since_last_payment)
        
        risk_info = VendorRiskInfo(
            vendor_id=vendor.vendor_id,
            vendor_name=vendor.vendor_name,
            vendor_status=vendor.status.value,
            risk_score=risk_score,
            on_time_payment_rate=risk_profile.on_time_payment_rate,
            invoice_count=risk_profile.invoice_count,
            days_since_last_payment=risk_profile.days_since_last_payment,
            has_fraud_flags=risk_profile.has_fraud_history,
            fraud_flag_count=risk_profile.fraud_flag_count,
            is_new_vendor=is_new,
            is_inactive=is_inactive,
        )
        
        return risk_score, risk_info
    
    def _calculate_payment_risk(self, on_time_rate: float) -> float:
        """Calculate risk based on payment history."""
        if on_time_rate >= self.GOOD_PAYMENT_RATE:
            return 0.0
        elif on_time_rate >= self.ACCEPTABLE_PAYMENT_RATE:
            # Linear scale from 0.0 to 0.5
            return (self.GOOD_PAYMENT_RATE - on_time_rate) / (self.GOOD_PAYMENT_RATE - self.ACCEPTABLE_PAYMENT_RATE) * 0.5
        else:
            # Linear scale from 0.5 to 1.0
            return 0.5 + ((self.ACCEPTABLE_PAYMENT_RATE - on_time_rate) / self.ACCEPTABLE_PAYMENT_RATE) * 0.5
    
    def _calculate_activity_risk(
        self,
        days_since_last_payment: int,
        invoice_count: int,
        onboarded_date: datetime
    ) -> float:
        """Calculate risk based on vendor activity."""
        # New vendor (limited history)
        if self._is_new_vendor(onboarded_date):
            return 0.50
        
        # Very few invoices = higher risk
        if invoice_count < 5:
            return 0.60
        
        # Inactive vendor
        if self._is_inactive_vendor(days_since_last_payment):
            return 0.70
        
        # Recent activity (last 30 days)
        if days_since_last_payment <= 30:
            return 0.0
        
        # Moderate activity (31-90 days)
        elif days_since_last_payment <= 90:
            return 0.20
        
        # Declining activity (91-180 days)
        elif days_since_last_payment <= 180:
            return 0.40
        
        # Inactive
        else:
            return 0.70
    
    def _is_new_vendor(self, onboarded_date: datetime) -> bool:
        """Check if vendor is new (less than 90 days)."""
        days_since_onboarding = (datetime.now() - onboarded_date).days
        return days_since_onboarding < self.NEW_VENDOR_DAYS
    
    def _is_inactive_vendor(self, days_since_last_payment: int) -> bool:
        """Check if vendor is inactive (more than 180 days)."""
        return days_since_last_payment > self.INACTIVE_DAYS
    
    def get_risk_level(self, risk_score: float) -> RiskLevel:
        """Convert risk score to risk level."""
        if risk_score < self.LOW_RISK_THRESHOLD:
            return RiskLevel.LOW
        elif risk_score < self.MEDIUM_RISK_THRESHOLD:
            return RiskLevel.MEDIUM
        elif risk_score < self.HIGH_RISK_THRESHOLD:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
