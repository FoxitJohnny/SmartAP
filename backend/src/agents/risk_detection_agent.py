"""
Risk Detection Agent

AI Agent that assesses invoice risk using multiple detection strategies.
"""

import uuid
from typing import Optional, List
from datetime import datetime

from ..models import (
    Invoice,
    RiskAssessment,
    RiskLevel,
    RiskFlag,
    RiskFlagType,
    RecommendedAction,
    DuplicateInfo,
    VendorRiskInfo,
    PriceAnomalyInfo,
)
from ..db.repositories import InvoiceRepository, VendorRepository
from ..services.duplicate_detector import DuplicateDetector
from ..services.vendor_risk_analyzer import VendorRiskAnalyzer
from ..services.price_anomaly_detector import PriceAnomalyDetector


class RiskDetectionAgent:
    """
    Agent for comprehensive invoice risk assessment.
    
    Combines:
    1. Duplicate detection (hash, invoice number, amount patterns)
    2. Vendor risk analysis (payment history, fraud flags, activity)
    3. Price anomaly detection (statistical analysis, historical comparison)
    4. Amount risk (unusually high/low amounts)
    5. Pattern risk (behavioral analysis)
    """
    
    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        vendor_repo: VendorRepository,
    ):
        self.invoice_repo = invoice_repo
        self.vendor_repo = vendor_repo
        
        # Initialize detection services
        self.duplicate_detector = DuplicateDetector(invoice_repo)
        self.vendor_analyzer = VendorRiskAnalyzer(vendor_repo)
        self.price_detector = PriceAnomalyDetector(invoice_repo)
    
    async def assess_risk(
        self,
        invoice: Invoice,
        vendor_id: Optional[str] = None
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment on an invoice.
        
        Returns:
            RiskAssessment with risk level, flags, and recommendations
        """
        assessment_id = str(uuid.uuid4())
        risk_flags: List[RiskFlag] = []
        
        # 1. Duplicate Detection
        duplicate_score, duplicate_info = await self._assess_duplicate_risk(invoice)
        if duplicate_info and duplicate_info.is_duplicate:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.DUPLICATE_INVOICE,
                severity=self._score_to_severity(duplicate_info.confidence_score),
                description=f"Potential duplicate: {duplicate_info.match_type} match with {duplicate_info.duplicate_invoice_number}",
                confidence=duplicate_info.confidence_score,
                details={
                    "duplicate_invoice_id": duplicate_info.duplicate_invoice_id,
                    "match_type": duplicate_info.match_type,
                    "days_apart": duplicate_info.days_apart,
                }
            ))
        
        # 2. Vendor Risk Analysis
        vendor_score = 0.0
        vendor_info = None
        if vendor_id:
            vendor_score, vendor_info = await self._assess_vendor_risk(vendor_id)
            if vendor_info and vendor_score >= 0.50:
                risk_flags.append(RiskFlag(
                    flag_type=RiskFlagType.VENDOR_RISK,
                    severity=self._score_to_severity(vendor_score),
                    description=f"Vendor risk: {vendor_info.vendor_name} (score: {vendor_score:.2f})",
                    confidence=0.90,
                    details={
                        "vendor_status": vendor_info.vendor_status,
                        "on_time_rate": vendor_info.on_time_payment_rate,
                        "has_fraud_flags": vendor_info.has_fraud_flags,
                        "is_new_vendor": vendor_info.is_new_vendor,
                    }
                ))
        
        # 3. Price Anomaly Detection
        price_score, price_anomaly = await self._assess_price_anomaly(invoice, invoice.vendor_name)
        if price_anomaly and price_anomaly.is_anomaly:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.PRICE_ANOMALY,
                severity=self._score_to_severity(price_score),
                description=f"Price anomaly: {price_anomaly.percentage_difference:+.1%} from average (${price_anomaly.average_amount:.2f})",
                confidence=0.85,
                details={
                    "z_score": price_anomaly.z_score,
                    "current_amount": price_anomaly.current_amount,
                    "average_amount": price_anomaly.average_amount,
                }
            ))
        
        # 4. Amount Risk (very high or very low amounts)
        amount_score = self._assess_amount_risk(invoice.total_amount)
        if amount_score >= 0.30:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.AMOUNT_ANOMALY,
                severity=self._score_to_severity(amount_score),
                description=f"Unusually high invoice amount: ${invoice.total_amount:,.2f}",
                confidence=0.70,
                details={"amount": invoice.total_amount}
            ))
        
        # 5. Pattern Risk (multiple flags, suspicious patterns)
        pattern_score = self._assess_pattern_risk(risk_flags, invoice)
        
        # Calculate component scores
        component_scores = {
            "duplicate": duplicate_score,
            "vendor": vendor_score,
            "price": price_score,
            "amount": amount_score,
            "pattern": pattern_score,
        }
        
        # Calculate overall risk score (weighted)
        overall_risk_score = (
            duplicate_score * 0.30 +
            vendor_score * 0.25 +
            price_score * 0.20 +
            amount_score * 0.15 +
            pattern_score * 0.10
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_risk_score)
        
        # Count flags by severity
        critical_flags = sum(1 for f in risk_flags if f.severity == "critical")
        high_flags = sum(1 for f in risk_flags if f.severity == "high")
        
        # Determine recommended action
        recommended_action, action_reason = self._determine_action(
            risk_level,
            critical_flags,
            high_flags,
            risk_flags
        )
        
        # Create risk assessment
        return RiskAssessment(
            invoice_id=invoice.invoice_number,
            assessment_id=assessment_id,
            risk_level=risk_level,
            risk_score=overall_risk_score,
            duplicate_risk_score=duplicate_score,
            vendor_risk_score=vendor_score,
            price_risk_score=price_score,
            amount_risk_score=amount_score,
            pattern_risk_score=pattern_score,
            risk_flags=risk_flags,
            critical_flags=critical_flags,
            high_flags=high_flags,
            duplicate_info=duplicate_info,
            vendor_info=vendor_info,
            price_anomaly_info=price_anomaly,
            recommended_action=recommended_action,
            action_reason=action_reason,
            requires_manual_review=recommended_action in [
                RecommendedAction.REJECT,
                RecommendedAction.ESCALATE,
                RecommendedAction.INVESTIGATE
            ],
            assessed_by="risk_detection_agent",
            assessment_version="1.0",
        )
    
    async def _assess_duplicate_risk(
        self,
        invoice: Invoice
    ) -> tuple[float, Optional[DuplicateInfo]]:
        """Assess duplicate risk."""
        is_duplicate, duplicate_info = await self.duplicate_detector.detect_duplicates(invoice)
        
        if is_duplicate and duplicate_info:
            return duplicate_info.confidence_score, duplicate_info
        
        return 0.0, None
    
    async def _assess_vendor_risk(
        self,
        vendor_id: str
    ) -> tuple[float, Optional[VendorRiskInfo]]:
        """Assess vendor risk."""
        return await self.vendor_analyzer.analyze_vendor_risk(vendor_id)
    
    async def _assess_price_anomaly(
        self,
        invoice: Invoice,
        vendor_name: str
    ) -> tuple[float, Optional[PriceAnomalyInfo]]:
        """Assess price anomaly risk."""
        return await self.price_detector.detect_price_anomalies(invoice, vendor_name)
    
    def _assess_amount_risk(self, amount: float) -> float:
        """Assess risk based on invoice amount."""
        return self.price_detector.calculate_amount_risk(amount)
    
    def _assess_pattern_risk(
        self,
        risk_flags: List[RiskFlag],
        invoice: Invoice
    ) -> float:
        """
        Assess pattern risk (multiple flags, suspicious combinations).
        """
        # Multiple high-severity flags
        critical_count = sum(1 for f in risk_flags if f.severity == "critical")
        high_count = sum(1 for f in risk_flags if f.severity == "high")
        
        if critical_count >= 2:
            return 1.0
        elif critical_count == 1 and high_count >= 1:
            return 0.80
        elif high_count >= 2:
            return 0.60
        elif len(risk_flags) >= 3:
            return 0.40
        
        # Round numbers (potential fabrication)
        if self._is_round_number(invoice.total_amount):
            return 0.20
        
        return 0.0
    
    def _is_round_number(self, amount: float) -> bool:
        """Check if amount is suspiciously round (e.g., $5000.00)."""
        # Check if divisible by 1000, 500, or 100 with no cents
        if amount % 1000 == 0 and amount >= 5000:
            return True
        elif amount % 500 == 0 and amount >= 2500:
            return True
        elif amount % 100 == 0 and amount >= 1000:
            return True
        return False
    
    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score."""
        if risk_score < 0.25:
            return RiskLevel.LOW
        elif risk_score < 0.50:
            return RiskLevel.MEDIUM
        elif risk_score < 0.75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL
    
    def _score_to_severity(self, score: float) -> str:
        """Convert score to severity level."""
        if score >= 0.90:
            return "critical"
        elif score >= 0.70:
            return "high"
        elif score >= 0.40:
            return "medium"
        else:
            return "low"
    
    def _determine_action(
        self,
        risk_level: RiskLevel,
        critical_flags: int,
        high_flags: int,
        risk_flags: List[RiskFlag]
    ) -> tuple[RecommendedAction, str]:
        """Determine recommended action based on risk assessment."""
        # Critical risk or multiple critical flags = Reject
        if risk_level == RiskLevel.CRITICAL or critical_flags >= 2:
            return RecommendedAction.REJECT, f"Critical risk level with {critical_flags} critical flags"
        
        # Single critical flag = Escalate
        if critical_flags == 1:
            flag = next(f for f in risk_flags if f.severity == "critical")
            return RecommendedAction.ESCALATE, f"Critical flag: {flag.flag_type}"
        
        # High risk or multiple high flags = Investigate
        if risk_level == RiskLevel.HIGH or high_flags >= 2:
            return RecommendedAction.INVESTIGATE, f"High risk with {high_flags} high-severity flags"
        
        # Medium risk = Review
        if risk_level == RiskLevel.MEDIUM:
            return RecommendedAction.REVIEW, "Medium risk level - manual review recommended"
        
        # Low risk = Approve
        return RecommendedAction.APPROVE, "Low risk assessment - safe to proceed"
