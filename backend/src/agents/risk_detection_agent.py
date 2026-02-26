"""
Risk Detection Agent

AI Agent that assesses invoice risk using multiple detection strategies.

Components (6 weighted dimensions):
1. Duplicate detection  (25%)  – hash, invoice #, fuzzy amount/vendor/date
2. Vendor risk analysis (20%)  – payment history, fraud flags, activity
3. Price anomaly        (15%)  – statistical z-score vs. vendor history
4. Amount risk          (10%)  – absolute thresholds for unusually high amounts
5. PO matching risk     (20%)  – match score, discrepancies, no-match
6. Pattern risk         (10%)  – multi-flag escalation, round numbers
"""

import uuid
import logging
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
from ..models.matching import MatchingResult
from ..db.repositories import InvoiceRepository, VendorRepository
from ..services.duplicate_detector import DuplicateDetector
from ..services.vendor_risk_analyzer import VendorRiskAnalyzer
from ..services.price_anomaly_detector import PriceAnomalyDetector

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weight configuration (must sum to 1.0)
# ---------------------------------------------------------------------------
WEIGHT_DUPLICATE = 0.25
WEIGHT_VENDOR    = 0.20
WEIGHT_PRICE     = 0.15
WEIGHT_AMOUNT    = 0.10
WEIGHT_MATCHING  = 0.20
WEIGHT_PATTERN   = 0.10


class RiskDetectionAgent:
    """
    Agent for comprehensive invoice risk assessment.

    Combines six detection dimensions with configurable weights
    to produce an overall risk score, risk flags, and a recommended action.
    """

    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        vendor_repo: VendorRepository,
        settings: dict | None = None,
    ):
        self.invoice_repo = invoice_repo
        self.vendor_repo = vendor_repo
        self.settings = settings or {}

        # Initialize detection services with settings
        self.duplicate_detector = DuplicateDetector(invoice_repo, settings)
        self.vendor_analyzer = VendorRiskAnalyzer(vendor_repo, settings)
        self.price_detector = PriceAnomalyDetector(invoice_repo, settings)

        # Override module-level weights if provided
        self.weight_duplicate = self.settings.get("weight_duplicate", WEIGHT_DUPLICATE)
        self.weight_vendor = self.settings.get("weight_vendor", WEIGHT_VENDOR)
        self.weight_price = self.settings.get("weight_price", WEIGHT_PRICE)
        self.weight_amount = self.settings.get("weight_amount", WEIGHT_AMOUNT)
        self.weight_matching = self.settings.get("weight_matching", WEIGHT_MATCHING)
        self.weight_pattern = self.settings.get("weight_pattern", WEIGHT_PATTERN)

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------
    async def assess_risk(
        self,
        invoice: Invoice,
        vendor_id: Optional[str] = None,
        matching_result: Optional[MatchingResult] = None,
    ) -> RiskAssessment:
        """
        Perform comprehensive risk assessment on an invoice.

        Args:
            invoice: Extracted invoice data
            vendor_id: Optional vendor ID for vendor-risk lookup
            matching_result: Optional PO matching result for matching-risk

        Returns:
            RiskAssessment with risk level, flags, and recommendations
        """
        assessment_id = str(uuid.uuid4())
        risk_flags: List[RiskFlag] = []

        # -------------------------------------------------------------------
        # 1. Duplicate Detection (25%)
        # -------------------------------------------------------------------
        duplicate_score, duplicate_info = await self._assess_duplicate_risk(invoice)
        if duplicate_info and duplicate_info.is_duplicate:
            flag_type = duplicate_info.duplicate_type or RiskFlagType.DUPLICATE_NEAR
            risk_flags.append(RiskFlag(
                flag_type=flag_type,
                severity=self._score_to_severity(duplicate_info.similarity_score),
                description=f"Potential duplicate: {flag_type.value} match with {duplicate_info.duplicate_invoice_number}",
                confidence=duplicate_info.similarity_score,
                evidence=f"Matched invoice {duplicate_info.duplicate_invoice_number} (similarity {duplicate_info.similarity_score:.0%})",
                related_invoice_id=duplicate_info.duplicate_invoice_id,
                expected_value="Unique invoice",
                actual_value=f"Duplicate of {duplicate_info.duplicate_invoice_number}",
                deviation=f"{duplicate_info.similarity_score:.0%} similarity",
                suggested_action="Verify this is not a re-submission of an existing invoice",
                details={
                    "duplicate_invoice_id": duplicate_info.duplicate_invoice_id,
                    "duplicate_type": flag_type.value if flag_type else None,
                    "similarity_score": duplicate_info.similarity_score,
                },
            ))

        # -------------------------------------------------------------------
        # 2. Vendor Risk Analysis (20%)
        # -------------------------------------------------------------------
        vendor_score = 0.0
        vendor_info: Optional[VendorRiskInfo] = None

        # Auto-resolve vendor_id from vendor name if not supplied
        if not vendor_id and invoice.vendor_name:
            vendor_id = await self._resolve_vendor_id(invoice.vendor_name)

        if vendor_id:
            vendor_score, vendor_info = await self._assess_vendor_risk(vendor_id)
            if vendor_info and vendor_score >= 0.40:
                # Pick the most relevant vendor flag type
                if vendor_info.is_blocked:
                    vflag = RiskFlagType.VENDOR_BLOCKED
                    vdesc = f"Vendor '{vendor_info.vendor_name}' is blocked/suspended"
                    vaction = "Do not process — vendor is blocked"
                elif vendor_info.is_new_vendor:
                    vflag = RiskFlagType.VENDOR_NEW
                    vdesc = f"New vendor '{vendor_info.vendor_name}' with limited history"
                    vaction = "Verify vendor identity and banking details before first payment"
                elif vendor_info.active_fraud_flags > 0:
                    vflag = RiskFlagType.VENDOR_SPOOFING
                    vdesc = f"Vendor '{vendor_info.vendor_name}' has {vendor_info.active_fraud_flags} active fraud flag(s)"
                    vaction = "Investigate fraud flags before processing"
                else:
                    vflag = RiskFlagType.VENDOR_SPOOFING
                    vdesc = f"Vendor risk elevated for '{vendor_info.vendor_name}' (score: {vendor_score:.2f})"
                    vaction = "Review vendor profile and recent activity"

                risk_flags.append(RiskFlag(
                    flag_type=vflag,
                    severity=self._score_to_severity(vendor_score),
                    description=vdesc,
                    confidence=0.90,
                    evidence=f"Vendor risk score: {vendor_score:.2f}, fraud flags: {vendor_info.active_fraud_flags}, total invoices: {vendor_info.total_invoices}",
                    expected_value="Risk score < 0.40",
                    actual_value=f"{vendor_score:.2f}",
                    deviation=f"+{(vendor_score - 0.40):.2f} above threshold",
                    suggested_action=vaction,
                    details={
                        "vendor_risk_score": vendor_info.vendor_risk_score,
                        "is_blocked": vendor_info.is_blocked,
                        "active_fraud_flags": vendor_info.active_fraud_flags,
                        "is_new_vendor": vendor_info.is_new_vendor,
                        "total_invoices": vendor_info.total_invoices,
                    },
                ))

        # -------------------------------------------------------------------
        # 3. Price Anomaly Detection (15%)
        # -------------------------------------------------------------------
        price_score, price_anomaly = await self._assess_price_anomaly(invoice, invoice.vendor_name)
        if price_anomaly and price_anomaly.is_anomaly:
            pct = (price_anomaly.deviation_percentage or 0) / 100  # stored as percentage points
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.PRICE_ANOMALY,
                severity=self._score_to_severity(price_score),
                description=f"Price anomaly: {pct:+.1%} from vendor average (${float(price_anomaly.historical_average or 0):,.2f})",
                confidence=0.85,
                evidence=f"Z-score: {price_anomaly.price_z_score:.2f}, historical avg: ${float(price_anomaly.historical_average or 0):,.2f}, std dev: ${float(price_anomaly.historical_std_dev or 0):,.2f}",
                expected_value=f"${float(price_anomaly.historical_average or 0):,.2f}",
                actual_value=f"${float(price_anomaly.current_price):,.2f}",
                deviation=f"{pct:+.1%}",
                suggested_action="Compare line items against recent invoices from this vendor",
                details={
                    "z_score": price_anomaly.price_z_score,
                    "current_amount": float(price_anomaly.current_price),
                    "average_amount": float(price_anomaly.historical_average or 0),
                    "std_dev": float(price_anomaly.historical_std_dev or 0),
                    "deviation_pct": price_anomaly.deviation_percentage,
                },
            ))

        # -------------------------------------------------------------------
        # 4. Amount Risk (10%)
        # -------------------------------------------------------------------
        amount_score = self._assess_amount_risk(float(invoice.total))
        if amount_score >= 0.30:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.AMOUNT_ANOMALY,
                severity=self._score_to_severity(amount_score),
                description=f"Unusually high invoice amount: ${float(invoice.total):,.2f}",
                confidence=0.70,
                evidence=f"Invoice total ${float(invoice.total):,.2f} exceeds typical range",
                expected_value="< $200,000",
                actual_value=f"${float(invoice.total):,.2f}",
                suggested_action="Verify invoice amount against PO and contract terms",
                details={"amount": float(invoice.total)},
            ))

        # -------------------------------------------------------------------
        # 5. PO Matching Risk (20%)
        # -------------------------------------------------------------------
        matching_score = self._assess_matching_risk(matching_result, risk_flags)

        # -------------------------------------------------------------------
        # 6. Pattern Risk (10%)
        # -------------------------------------------------------------------
        pattern_score = self._assess_pattern_risk(risk_flags, invoice)

        # -------------------------------------------------------------------
        # Overall score (weighted sum)
        # -------------------------------------------------------------------
        overall_risk_score = (
            duplicate_score * self.weight_duplicate +
            vendor_score   * self.weight_vendor +
            price_score    * self.weight_price +
            amount_score   * self.weight_amount +
            matching_score * self.weight_matching +
            pattern_score  * self.weight_pattern
        )
        overall_risk_score = max(0.0, min(1.0, overall_risk_score))

        risk_level = self._determine_risk_level(overall_risk_score)

        critical_flags = sum(1 for f in risk_flags if f.severity == "critical")
        high_flags = sum(1 for f in risk_flags if f.severity == "high")

        recommended_action, action_reason = self._determine_action(
            risk_level, critical_flags, high_flags, risk_flags,
        )

        return RiskAssessment(
            invoice_id=invoice.invoice_number,
            assessment_id=assessment_id,
            risk_level=risk_level,
            risk_score=overall_risk_score,
            duplicate_risk_score=duplicate_score,
            vendor_risk_score=vendor_score,
            price_risk_score=price_score,
            amount_risk_score=amount_score,
            matching_risk_score=matching_score,
            pattern_risk_score=pattern_score,
            risk_flags=risk_flags,
            critical_flags=critical_flags,
            high_flags=high_flags,
            duplicate_info=duplicate_info,
            vendor_risk_info=vendor_info,
            price_anomaly_info=price_anomaly,
            recommended_action=recommended_action,
            action_reason=action_reason,
            requires_manual_review=recommended_action in [
                RecommendedAction.REJECT,
                RecommendedAction.MANAGER_APPROVAL,
                RecommendedAction.INVESTIGATE,
            ],
            assessed_by="risk_detection_agent",
            assessment_version="2.0",
        )

    # -----------------------------------------------------------------------
    # Component assessors
    # -----------------------------------------------------------------------
    async def _assess_duplicate_risk(
        self, invoice: Invoice,
    ) -> tuple[float, Optional[DuplicateInfo]]:
        """Assess duplicate risk."""
        is_dup, dup_info = await self.duplicate_detector.detect_duplicates(invoice)
        if is_dup and dup_info:
            return dup_info.similarity_score, dup_info
        return 0.0, None

    async def _resolve_vendor_id(self, vendor_name: str) -> Optional[str]:
        """Try to find vendor_id by matching vendor_name in the vendor table."""
        try:
            vendors = await self.vendor_repo.search_by_name(vendor_name)
            if vendors:
                # Prefer exact (case-insensitive) match, fall back to first result
                for v in vendors:
                    if v.vendor_name.strip().lower() == vendor_name.strip().lower():
                        return v.vendor_id
                return vendors[0].vendor_id
        except Exception:
            pass
        return None

    async def _assess_vendor_risk(
        self, vendor_id: str,
    ) -> tuple[float, Optional[VendorRiskInfo]]:
        """Assess vendor risk."""
        return await self.vendor_analyzer.analyze_vendor_risk(vendor_id)

    async def _assess_price_anomaly(
        self, invoice: Invoice, vendor_name: str,
    ) -> tuple[float, Optional[PriceAnomalyInfo]]:
        """Assess price anomaly risk."""
        return await self.price_detector.detect_price_anomalies(
            invoice, vendor_name, exclude_document_id=invoice.document_id,
        )

    def _assess_amount_risk(self, amount: float) -> float:
        """Assess risk based on invoice amount."""
        return self.price_detector.calculate_amount_risk(amount)

    def _assess_matching_risk(
        self,
        matching_result: Optional[MatchingResult],
        risk_flags: List[RiskFlag],
    ) -> float:
        """
        Assess risk based on PO-matching outcome.

        Scoring:
        - No matching result available → 0.35 (unknown)
        - Not matched (no PO found)    → 0.70
        - Match score < 0.60           → 0.60
        - Match score < 0.80           → 0.30
        - Critical discrepancies       → +0.10 per critical (capped at 0.90)
        - High discrepancies           → +0.05 per high
        - Good match (≥ 0.85, no critical) → 0.0
        """
        if matching_result is None:
            # Matching wasn't run or failed — moderate unknown risk
            return 0.35

        if not matching_result.matched:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.MATCHING_NO_MATCH,
                severity="high",
                description=f"No matching PO found for this invoice (score: {matching_result.match_score:.2f})",
                confidence=0.85,
                evidence=f"Best match score: {matching_result.match_score:.2f}, candidates considered: {len(matching_result.candidate_pos)}",
                suggested_action="Manually assign a PO or request a new PO from the requester",
                details={
                    "match_score": matching_result.match_score,
                    "candidates": len(matching_result.candidate_pos),
                },
            ))
            return 0.70

        # Matched — evaluate quality
        score = matching_result.match_score
        crit = matching_result.critical_discrepancies
        high_disc = sum(1 for d in matching_result.discrepancies if d.severity.value == "high") if matching_result.discrepancies else 0

        base = 0.0
        if score < 0.60:
            base = 0.60
        elif score < 0.80:
            base = 0.30
        elif score < 0.85:
            base = 0.15

        discrepancy_penalty = crit * 0.10 + high_disc * 0.05

        if crit > 0:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.MATCHING_DISCREPANCY,
                severity="high" if crit < 3 else "critical",
                description=f"PO match has {crit} critical discrepancy(ies) with PO {matching_result.po_number}",
                confidence=0.90,
                evidence="; ".join(d.description for d in matching_result.discrepancies if d.severity.value == "critical")[:300],
                expected_value=f"Match to PO {matching_result.po_number}",
                actual_value=f"Score {score:.2f} with {crit} critical discrepancies",
                deviation=f"{crit} critical, {high_disc} high",
                suggested_action="Review discrepancies and request vendor clarification if needed",
                details={
                    "match_score": score,
                    "po_number": matching_result.po_number,
                    "critical_discrepancies": crit,
                    "high_discrepancies": high_disc,
                },
            ))
        elif score < 0.80:
            risk_flags.append(RiskFlag(
                flag_type=RiskFlagType.MATCHING_LOW_SCORE,
                severity="medium",
                description=f"Low PO match confidence ({score:.0%}) with PO {matching_result.po_number}",
                confidence=0.80,
                suggested_action="Manually verify the PO assignment is correct",
                details={
                    "match_score": score,
                    "po_number": matching_result.po_number,
                },
            ))

        return min(0.90, base + discrepancy_penalty)

    def _assess_pattern_risk(
        self,
        risk_flags: List[RiskFlag],
        invoice: Invoice,
    ) -> float:
        """
        Assess pattern risk (multiple flags, suspicious combinations).
        """
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

        # Round numbers (potential fabrication) — conservative thresholds
        if self._is_suspiciously_round(float(invoice.total)):
            return 0.10

        return 0.0

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------
    @staticmethod
    def _is_suspiciously_round(amount: float) -> bool:
        """
        Flag only genuinely suspicious round amounts.

        Raised thresholds vs. prior version to avoid false positives on
        normal invoices that happen to be in round hundreds.
        """
        if amount >= 50_000 and amount % 10_000 == 0:
            return True
        if amount >= 25_000 and amount % 5_000 == 0:
            return True
        if amount >= 10_000 and amount % 1_000 == 0:
            return True
        return False

    @staticmethod
    def _determine_risk_level(risk_score: float) -> RiskLevel:
        if risk_score < 0.25:
            return RiskLevel.LOW
        elif risk_score < 0.50:
            return RiskLevel.MEDIUM
        elif risk_score < 0.75:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL

    @staticmethod
    def _score_to_severity(score: float) -> str:
        if score >= 0.90:
            return "critical"
        elif score >= 0.70:
            return "high"
        elif score >= 0.40:
            return "medium"
        return "low"

    @staticmethod
    def _determine_action(
        risk_level: RiskLevel,
        critical_flags: int,
        high_flags: int,
        risk_flags: List[RiskFlag],
    ) -> tuple[RecommendedAction, str]:
        """Determine recommended action based on risk assessment."""
        if risk_level == RiskLevel.CRITICAL or critical_flags >= 2:
            return RecommendedAction.REJECT, f"Critical risk level with {critical_flags} critical flag(s)"

        if critical_flags == 1:
            flag = next(f for f in risk_flags if f.severity == "critical")
            return RecommendedAction.MANAGER_APPROVAL, f"Critical flag: {flag.flag_type.value}"

        if risk_level == RiskLevel.HIGH or high_flags >= 2:
            return RecommendedAction.INVESTIGATE, f"High risk with {high_flags} high-severity flag(s)"

        if risk_level == RiskLevel.MEDIUM:
            return RecommendedAction.REVIEW, "Medium risk level — manual review recommended"

        return RecommendedAction.AUTO_APPROVE, "Low risk assessment — safe to proceed"
