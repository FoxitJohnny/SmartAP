"""
Vendor Risk Analyzer

Analyzes vendor risk based on history, patterns, and fraud flags.
"""

from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from ..models import Vendor, VendorRiskProfile, VendorStatus
from ..models.risk import VendorRiskInfo, RiskLevel
from ..db.repositories import VendorRepository


class VendorRiskAnalyzer:
    """Service for analyzing vendor risk."""
    
    # Risk thresholds
    LOW_RISK_THRESHOLD = 0.25
    MEDIUM_RISK_THRESHOLD = 0.50
    HIGH_RISK_THRESHOLD = 0.75
    
    # Payment reliability thresholds
    GOOD_PAYMENT_RELIABILITY = 0.90
    ACCEPTABLE_PAYMENT_RELIABILITY = 0.75
    
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
                vendor_risk_score=0.80,
                is_new_vendor=True,
                is_blocked=False,
                active_fraud_flags=0,
                average_invoice_amount=Decimal("0.0"),
                invoice_amount_std_dev=Decimal("0.0"),
                total_invoices=0,
            )
        
        # Get risk profile from vendor
        risk_profile = vendor_db.risk_profile or {}
        
        # Calculate risk components
        risk_score = 0.0
        
        # 1. Base risk from profile (40%)
        base_risk = risk_profile.get('risk_score', 0.5)
        risk_score += base_risk * 0.40
        
        # 2. Payment reliability risk (30%)
        payment_reliability = risk_profile.get('payment_reliability_score', 0.5)
        payment_risk = self._calculate_payment_risk(payment_reliability)
        risk_score += payment_risk * 0.30
        
        # 3. Activity risk (20%)
        last_payment_date = risk_profile.get('last_payment_date')
        total_invoices = risk_profile.get('total_invoices_processed', 0)
        onboarded_date = vendor_db.onboarded_date
        
        days_since_payment = self._days_since_payment(last_payment_date)
        activity_risk = self._calculate_activity_risk(
            days_since_payment,
            total_invoices,
            onboarded_date
        )
        risk_score += activity_risk * 0.20
        
        # 4. Fraud flag risk (10%)
        active_fraud_flags = risk_profile.get('active_fraud_flags', 0)
        fraud_risk = min(1.0, active_fraud_flags * 0.25) if active_fraud_flags > 0 else 0.0
        risk_score += fraud_risk * 0.10
        
        # Ensure score is between 0 and 1
        risk_score = max(0.0, min(1.0, risk_score))
        
        # Check if vendor is blocked
        is_blocked = vendor_db.status == VendorStatus.BLOCKED or vendor_db.status == VendorStatus.SUSPENDED
        
        # Create risk info
        is_new = self._is_new_vendor(onboarded_date)
        
        risk_info = VendorRiskInfo(
            vendor_id=vendor_db.vendor_id,
            vendor_name=vendor_db.vendor_name,
            vendor_risk_score=risk_score,
            is_new_vendor=is_new,
            is_blocked=is_blocked,
            active_fraud_flags=active_fraud_flags,
            average_invoice_amount=Decimal(str(risk_profile.get('average_invoice_amount', 0.0))),
            invoice_amount_std_dev=Decimal("0.0"),  # Would need historical calculation
            total_invoices=total_invoices,
        )
        
        return risk_score, risk_info
    
    def _days_since_payment(self, last_payment_date) -> int:
        """Calculate days since last payment."""
        if not last_payment_date:
            return 9999  # No payment history = high risk indicator
        
        # Handle string date format from JSON
        if isinstance(last_payment_date, str):
            try:
                last_payment_date = datetime.fromisoformat(last_payment_date).date()
            except ValueError:
                return 9999
        elif isinstance(last_payment_date, datetime):
            last_payment_date = last_payment_date.date()
        
        return (date.today() - last_payment_date).days
    
    def _calculate_payment_risk(self, payment_reliability: float) -> float:
        """Calculate risk based on payment reliability score."""
        if payment_reliability >= self.GOOD_PAYMENT_RELIABILITY:
            return 0.0
        elif payment_reliability >= self.ACCEPTABLE_PAYMENT_RELIABILITY:
            # Linear scale from 0.0 to 0.5
            return (self.GOOD_PAYMENT_RELIABILITY - payment_reliability) / \
                   (self.GOOD_PAYMENT_RELIABILITY - self.ACCEPTABLE_PAYMENT_RELIABILITY) * 0.5
        else:
            # Linear scale from 0.5 to 1.0
            return 0.5 + ((self.ACCEPTABLE_PAYMENT_RELIABILITY - payment_reliability) / 
                          self.ACCEPTABLE_PAYMENT_RELIABILITY) * 0.5
    
    def _calculate_activity_risk(
        self,
        days_since_last_payment: int,
        invoice_count: int,
        onboarded_date
    ) -> float:
        """Calculate risk based on vendor activity."""
        # New vendor (limited history)
        if self._is_new_vendor(onboarded_date):
            return 0.50
        
        # Very few invoices = higher risk
        if invoice_count < 5:
            return 0.60
        
        # Inactive vendor
        if days_since_last_payment > self.INACTIVE_DAYS:
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
    
    def _is_new_vendor(self, onboarded_date) -> bool:
        """Check if vendor is new (less than 90 days)."""
        if not onboarded_date:
            return True
        
        if isinstance(onboarded_date, datetime):
            onboarded_date = onboarded_date.date()
        
        days_since_onboarding = (date.today() - onboarded_date).days
        return days_since_onboarding < self.NEW_VENDOR_DAYS
    
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
