"""
PO Matching Agent

AI Agent that matches invoices to purchase orders using the Microsoft Agent Framework.
"""

import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from openai import AsyncOpenAI

from ..compat.chat_agent import ChatAgent

from ..config import get_settings
from ..models import (
    Invoice,
    PurchaseOrder,
    MatchingResult,
    MatchType,
    Discrepancy,
    DiscrepancySeverity,
    LineItemMatch,
    Vendor,
    MatchingSettings,
)
from ..db.repositories import PurchaseOrderRepository, VendorRepository
from ..services.matching_service import MatchingService
from ..services.discrepancy_detector import DiscrepancyDetector

logger = logging.getLogger(__name__)


# System prompt for AI matching decisions
MATCHING_SYSTEM_PROMPT = """You are an expert at matching invoices to purchase orders.

Your role:
1. Analyze invoice and PO data provided by the system
2. Determine if they match based on vendor, amounts, line items, dates
3. Identify any discrepancies and their severity
4. Recommend whether to approve or flag for review

Consider:
- Vendor name variations (abbreviations, Inc vs LLC, etc.)
- Line item descriptions (different wording for same product)
- Amount differences (tax, shipping, discounts)
- Date reasonableness (invoice should be after PO)
- Quantity and pricing alignment

OUTPUT FORMAT:
You must respond with valid JSON only:
{
  "decision": "APPROVE" or "REVIEW_REQUIRED",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "concerns": ["list of any concerns"]
}"""


class POMatchingAgent:
    """
    Agent for matching invoices to purchase orders.
    
    Uses:
    1. Repository queries to find candidate POs
    2. Algorithmic scoring for fast matching
    3. AI agent for complex/ambiguous cases
    """
    
    def __init__(
        self,
        po_repository: PurchaseOrderRepository,
        vendor_repository: VendorRepository,
        matching_settings: Optional[MatchingSettings] = None,
    ):
        self.po_repo = po_repository
        self.vendor_repo = vendor_repository
        self.matching_service = MatchingService()
        self.discrepancy_detector = DiscrepancyDetector()
        self.settings = get_settings()
        self.matching_settings = matching_settings
        
        # AI agent for complex cases
        self._agent: Optional[ChatAgent] = None
    
    async def _get_agent(self) -> Optional[ChatAgent]:
        """Get or create the ChatAgent instance for AI matching."""
        if self._agent is not None:
            return self._agent
        
        # Check if we have AI credentials
        if self.settings.ai_provider == "github" and not self.settings.github_token:
            logger.warning("GitHub token not configured - AI matching disabled")
            return None
        elif self.settings.ai_provider == "openai" and not self.settings.openai_api_key:
            logger.warning("OpenAI API key not configured - AI matching disabled")
            return None
        
        try:
            # Configure OpenAI client based on provider
            if self.settings.ai_provider == "github":
                client = AsyncOpenAI(
                    base_url=self.settings.model_base_url,
                    api_key=self.settings.github_token,
                )
            else:
                client = AsyncOpenAI(
                    api_key=self.settings.openai_api_key,
                )
            
            self._agent = ChatAgent(
                async_client=client,
                model_id=self.settings.model_id,
                name="POMatchingAgent",
                instructions=MATCHING_SYSTEM_PROMPT,
            )
            
            logger.info(f"AI matching agent initialized with provider: {self.settings.ai_provider}")
            return self._agent
            
        except Exception as e:
            logger.error(f"Failed to initialize AI matching agent: {e}")
            return None
    
    async def initialize(self):
        """Initialize AI agent client (lazy initialization)."""
        await self._get_agent()
    
    async def match_invoice_to_po(
        self,
        invoice: Invoice,
        use_ai_for_ambiguous: bool = True
    ) -> MatchingResult:
        """
        Match an invoice to a purchase order.
        
        Process:
        1. Find candidate POs based on vendor and amount
        2. Score each candidate algorithmically
        3. If ambiguous, use AI agent for decision
        4. Return matching result with discrepancies
        """
        matching_id = str(uuid.uuid4())
        
        # Step 1: Find candidate POs
        candidates = await self._find_candidate_pos(invoice)
        
        if not candidates:
            return self._create_no_match_result(invoice, matching_id, "No candidate POs found")
        
        # Step 2: Score all candidates
        scored_candidates = []
        for po, vendor in candidates:
            score_result = await self._score_match(invoice, po, vendor)
            scored_candidates.append((po, vendor, score_result))
        
        # Sort by match score
        scored_candidates.sort(key=lambda x: x[2]["overall_score"], reverse=True)
        
        # Best match
        best_po, best_vendor, best_score = scored_candidates[0]
        
        # Step 3: Determine match type and approval
        match_type = self._determine_match_type(best_score["overall_score"])

        ai_evaluation: Optional[Dict[str, Any]] = None
        
        # Use AI for ambiguous cases
        effective_use_ai = use_ai_for_ambiguous
        if self.matching_settings is not None:
            effective_use_ai = effective_use_ai and bool(self.matching_settings.use_ai_for_ambiguous)

        if effective_use_ai and match_type in [MatchType.PARTIAL, MatchType.FUZZY]:
            agent = await self._get_agent()
            if agent:
                ai_decision = await self._get_ai_decision(invoice, best_po, best_vendor, best_score)
                # AI can override match type and approval decision
                if ai_decision:
                    ai_evaluation = ai_decision
                    match_type = ai_decision.get("match_type", match_type)
        
        # Step 4: Detect discrepancies
        discrepancies = DiscrepancyDetector.detect_all_discrepancies(
            invoice=invoice,
            po=best_po,
            vendor_name_from_db=best_vendor.vendor_name,
            vendor_match_score=best_score["vendor_score"],
            amount_match_score=best_score["amount_score"],
            date_match_score=best_score["date_score"],
            line_matches=best_score["line_matches"],
            line_items_score=best_score["line_items_score"],
        )
        
        # Step 5: Determine approval requirement
        requires_approval, approval_reason = self._determine_approval_requirement(
            best_score["overall_score"],
            discrepancies
        )

        acceptable_threshold = (
            float(self.matching_settings.acceptable_match_threshold)
            if self.matching_settings is not None
            else MatchingService.ACCEPTABLE_MATCH_THRESHOLD
        )
        
        # Create matching result
        return MatchingResult(
            invoice_id=invoice.invoice_number,
            po_number=best_po.po_number,
            matching_id=matching_id,
            match_type=match_type,
            match_score=best_score["overall_score"],
            matched=best_score["overall_score"] >= acceptable_threshold,
            vendor_match_score=best_score["vendor_score"],
            amount_match_score=best_score["amount_score"],
            date_match_score=best_score["date_score"],
            line_items_match_score=best_score["line_items_score"],
            line_item_matches=best_score["line_matches"],
            discrepancies=discrepancies,
            has_discrepancies=len(discrepancies) > 0,
            critical_discrepancies=sum(1 for d in discrepancies if d.severity == DiscrepancySeverity.CRITICAL),
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            matched_by="po_matching_agent",
            ai_evaluation=ai_evaluation,
        )
    
    async def _find_candidate_pos(
        self,
        invoice: Invoice
    ) -> List[tuple[PurchaseOrder, Vendor]]:
        """Find candidate POs for matching."""
        # Find vendor by name (fuzzy search)
        vendors = await self.vendor_repo.search_by_name(invoice.vendor_name)
        
        if not vendors:
            return []
        
        candidates = []

        # Optionally rank/filter vendor candidates using fuzzy score
        vendor_threshold = self.matching_settings.vendor_fuzzy_threshold if self.matching_settings else 0.0
        scored_vendors = []
        for vendor_db in vendors:
            score = MatchingService.calculate_vendor_match_score(
                invoice.vendor_name,
                vendor_db.vendor_id,
                vendor_db.vendor_name,
            )
            if score >= float(vendor_threshold):
                scored_vendors.append((vendor_db, score))

        if scored_vendors:
            scored_vendors.sort(key=lambda x: x[1], reverse=True)
            vendor_candidates = [v for v, _ in scored_vendors[:3]]
        else:
            vendor_candidates = vendors[:3]

        amount_tol = self.matching_settings.amount_tolerance_percent if self.matching_settings else 0.20
        for vendor_db in vendor_candidates:  # Top 3 vendor matches
            # Find POs with amount within configured tolerance range
            amount_min = float(invoice.total) * (1.0 - float(amount_tol))
            amount_max = float(invoice.total) * (1.0 + float(amount_tol))
            
            pos = await self.po_repo.find_candidates(
                vendor_id=vendor_db.vendor_id,
                amount_min=amount_min,
                amount_max=amount_max,
            )
            
            # Convert SQLAlchemy models to Pydantic models via dict
            for po_db in pos:
                # Convert PO DB model to dict for Pydantic validation
                po_dict = {
                    "po_number": po_db.po_number,
                    "po_id": str(po_db.id) if po_db.id else None,
                    "vendor_id": po_db.vendor_id,
                    "vendor_name": vendor_db.vendor_name,  # Get from vendor
                    "created_date": po_db.created_date,
                    "expected_delivery": po_db.expected_delivery,
                    "status": po_db.status.value if hasattr(po_db.status, 'value') else po_db.status,
                    "currency": po_db.currency,
                    "subtotal": po_db.subtotal,
                    "tax": po_db.tax,
                    "total_amount": po_db.total_amount,
                    "payment_terms": po_db.payment_terms,
                    "notes": po_db.notes,
                    "created_by": po_db.created_by,
                    "line_items": [
                        {
                            "line_number": li.line_number,
                            "description": li.description,
                            "quantity": li.quantity,
                            "unit_price": li.unit_price,
                            "amount": li.amount,
                            "sku": li.sku,
                            "unit": li.unit,
                            "received_quantity": getattr(li, 'received_quantity', 0.0),
                        }
                        for li in (po_db.line_items or [])
                    ],
                }
                # Build vendor dict - VendorDB has different fields from Vendor pydantic
                vendor_dict = {
                    "vendor_id": vendor_db.vendor_id,
                    "vendor_name": vendor_db.vendor_name,
                    "status": vendor_db.status.value if hasattr(vendor_db.status, 'value') else vendor_db.status,
                    "tax_id": vendor_db.tax_id,
                    "email": vendor_db.email,
                    "phone": vendor_db.phone,
                    "address_line1": vendor_db.address_line1,
                    "city": vendor_db.city,
                    "state": vendor_db.state,
                    "postal_code": vendor_db.postal_code,
                    "country": vendor_db.country,
                    "payment_terms": vendor_db.payment_terms,
                    "currency": vendor_db.currency,
                    "onboarded_date": vendor_db.onboarded_date,
                    # risk_profile is stored as JSON dict in DB
                    "risk_profile": vendor_db.risk_profile if vendor_db.risk_profile else {},
                }
                po = PurchaseOrder.model_validate(po_dict)
                vendor = Vendor.model_validate(vendor_dict)
                candidates.append((po, vendor))
        
        return candidates
    
    async def _score_match(
        self,
        invoice: Invoice,
        po: PurchaseOrder,
        vendor: Vendor
    ) -> Dict[str, Any]:
        """Calculate match scores."""
        # Vendor score
        vendor_score = MatchingService.calculate_vendor_match_score(
            invoice.vendor_name,
            po.vendor_id,
            vendor.vendor_name
        )
        
        # Amount score
        amount_tolerance = (
            float(self.matching_settings.amount_match_tolerance)
            if self.matching_settings is not None
            else MatchingService.AMOUNT_TOLERANCE
        )
        amount_score = MatchingService.calculate_amount_match_score(
            float(invoice.total),
            float(po.total_amount),
            tolerance=amount_tolerance,
        )
        
        # Date score
        date_tolerance_days = (
            int(self.matching_settings.date_tolerance_days)
            if self.matching_settings is not None
            else MatchingService.DATE_TOLERANCE_DAYS
        )
        date_score = MatchingService.calculate_date_match_score(
            invoice.invoice_date,
            po.created_date,
            tolerance_days=date_tolerance_days,
        )
        
        # Line items score
        line_amount_tol = (
            float(self.matching_settings.line_item_amount_tolerance)
            if self.matching_settings is not None
            else 0.10
        )
        line_threshold = (
            float(self.matching_settings.line_item_description_threshold)
            if self.matching_settings is not None
            else 0.70
        )
        min_item_score = max(0.0, line_threshold - 0.10)
        line_matches, line_items_score = MatchingService.match_line_items(
            invoice.line_items,
            po.line_items,
            amount_tolerance=line_amount_tol,
            min_match_score=min_item_score,
            matched_score_threshold=line_threshold,
        )
        
        # Overall score
        vw = float(self.matching_settings.vendor_match_weight) if self.matching_settings is not None else 0.30
        aw = float(self.matching_settings.amount_match_weight) if self.matching_settings is not None else 0.30
        dw = float(self.matching_settings.date_match_weight) if self.matching_settings is not None else 0.10
        lw = float(self.matching_settings.line_items_match_weight) if self.matching_settings is not None else 0.30
        overall_score = MatchingService.calculate_overall_match_score(
            vendor_score,
            amount_score,
            date_score,
            line_items_score,
            vendor_weight=vw,
            amount_weight=aw,
            date_weight=dw,
            line_items_weight=lw,
        )
        
        return {
            "vendor_score": vendor_score,
            "amount_score": amount_score,
            "date_score": date_score,
            "line_items_score": line_items_score,
            "line_matches": line_matches,
            "overall_score": overall_score,
        }
    
    def _determine_match_type(self, score: float) -> MatchType:
        """Determine match type from score."""
        exact = (
            float(self.matching_settings.exact_match_threshold)
            if self.matching_settings is not None
            else MatchingService.EXACT_MATCH_THRESHOLD
        )
        good = (
            float(self.matching_settings.good_match_threshold)
            if self.matching_settings is not None
            else MatchingService.GOOD_MATCH_THRESHOLD
        )
        acceptable = (
            float(self.matching_settings.acceptable_match_threshold)
            if self.matching_settings is not None
            else MatchingService.ACCEPTABLE_MATCH_THRESHOLD
        )

        if score >= exact:
            return MatchType.EXACT
        elif score >= good:
            return MatchType.FUZZY
        elif score >= acceptable:
            return MatchType.PARTIAL
        else:
            return MatchType.NONE
    
    def _determine_approval_requirement(
        self,
        match_score: float,
        discrepancies: List[Discrepancy]
    ) -> tuple[bool, Optional[str]]:
        """Determine if manual approval is required."""
        critical_blocks = (
            bool(self.matching_settings.critical_discrepancy_blocks_approval)
            if self.matching_settings is not None
            else True
        )

        # Critical discrepancies always require approval (when enabled)
        critical_count = sum(1 for d in discrepancies if d.severity == DiscrepancySeverity.CRITICAL)
        if critical_blocks and critical_count > 0:
            return True, f"{critical_count} critical discrepancy(ies) detected"
        
        # Low match score requires approval
        good_threshold = (
            float(self.matching_settings.good_match_threshold)
            if self.matching_settings is not None
            else MatchingService.GOOD_MATCH_THRESHOLD
        )

        if match_score < good_threshold:
            return True, f"Match score below threshold ({match_score:.1%})"
        
        # High-severity discrepancies require approval
        high_count = sum(1 for d in discrepancies if d.severity == DiscrepancySeverity.HIGH)
        if high_count >= 2:
            return True, f"{high_count} high-severity discrepancies detected"
        
        # Otherwise, auto-approve
        return False, None
    
    def _create_no_match_result(
        self,
        invoice: Invoice,
        matching_id: str,
        reason: str
    ) -> MatchingResult:
        """Create a no-match result."""
        return MatchingResult(
            invoice_id=invoice.invoice_number,
            po_number=None,
            matching_id=matching_id,
            match_type=MatchType.NONE,
            match_score=0.0,
            matched=False,
            vendor_match_score=0.0,
            amount_match_score=0.0,
            date_match_score=0.0,
            line_items_match_score=0.0,
            line_item_matches=[],
            discrepancies=[],
            has_discrepancies=False,
            critical_discrepancies=0,
            requires_approval=True,
            approval_reason=reason,
            matched_by="po_matching_agent",
        )
    
    async def _get_ai_decision(
        self,
        invoice: Invoice,
        po: PurchaseOrder,
        vendor: Vendor,
        score_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use AI agent for complex matching decisions."""
        agent = await self._get_agent()
        if not agent:
            return None
        
        # Prepare context for AI
        prompt = f"""Analyze this invoice-PO match:

INVOICE:
- Number: {invoice.invoice_number}
- Vendor: {invoice.vendor_name}
- Date: {invoice.invoice_date}
- Total: ${float(invoice.total):.2f}
- Line Items: {len(invoice.line_items)}

PURCHASE ORDER:
- Number: {po.po_number}
- Vendor: {vendor.vendor_name}
- Date: {po.created_date}
- Total: ${float(po.total_amount):.2f}
- Line Items: {len(po.line_items)}

ALGORITHMIC SCORES:
- Vendor: {score_result['vendor_score']:.1%}
- Amount: {score_result['amount_score']:.1%}
- Date: {score_result['date_score']:.1%}
- Line Items: {score_result['line_items_score']:.1%}
- Overall: {score_result['overall_score']:.1%}

Should this match be approved? Respond with JSON only."""
        
        try:
            # Query AI agent using ChatAgent
            response = await agent.chat(prompt)
            
            # Try to parse JSON response
            try:
                # Find JSON in response
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract JSON from the response
                import re

                json_obj = None
                try:
                    json_obj = json.loads(response_text)
                except Exception:
                    pass

                if json_obj is None:
                    # Best-effort extraction: first { ... } block
                    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    if json_match:
                        json_obj = json.loads(json_match.group())

                if isinstance(json_obj, dict):
                    decision_str = str(json_obj.get("decision", "")).upper()
                    confidence = float(json_obj.get("confidence", 0.0) or 0.0)
                    reasoning = json_obj.get("reasoning")
                    concerns = json_obj.get("concerns")

                    confidence_threshold = (
                        float(self.matching_settings.ai_confidence_threshold)
                        if self.matching_settings is not None
                        else 0.75
                    )

                    approved = decision_str == "APPROVE" and confidence >= confidence_threshold

                    if approved:
                        logger.info(f"AI approved match: {reasoning or 'No reason provided'}")
                        match_type = MatchType.FUZZY
                    else:
                        logger.info(f"AI flagged for review: {reasoning or 'No reason provided'}")
                        match_type = MatchType.PARTIAL

                    return {
                        "decision": decision_str or None,
                        "confidence": confidence,
                        "confidence_threshold": confidence_threshold,
                        "reasoning": reasoning,
                        "concerns": concerns,
                        "approved": approved,
                        "match_type": match_type,
                    }
                
                # Fallback: check for APPROVE/REVIEW in text
                if "APPROVE" in response_text.upper():
                    return {
                        "decision": "APPROVE",
                        "confidence": None,
                        "reasoning": None,
                        "concerns": None,
                        "approved": True,
                        "match_type": MatchType.FUZZY,
                    }
                else:
                    return {
                        "decision": "REVIEW_REQUIRED",
                        "confidence": None,
                        "reasoning": None,
                        "concerns": None,
                        "approved": False,
                        "match_type": MatchType.PARTIAL,
                    }
                    
            except json.JSONDecodeError:
                # Fallback: check for APPROVE/REVIEW in text
                if "APPROVE" in response_text.upper():
                    return {
                        "decision": "APPROVE",
                        "confidence": None,
                        "reasoning": None,
                        "concerns": None,
                        "approved": True,
                        "match_type": MatchType.FUZZY,
                    }
                else:
                    return {
                        "decision": "REVIEW_REQUIRED",
                        "confidence": None,
                        "reasoning": None,
                        "concerns": None,
                        "approved": False,
                        "match_type": MatchType.PARTIAL,
                    }
        
        except Exception as e:
            logger.error(f"AI agent error: {e}")
            return None
    
    async def close(self):
        """Cleanup resources."""
        self._agent = None
