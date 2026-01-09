"""
PO Matching Agent

AI Agent that matches invoices to purchase orders using the Microsoft Agent Framework.
"""

import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI

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
    ):
        self.po_repo = po_repository
        self.vendor_repo = vendor_repository
        self.matching_service = MatchingService()
        self.discrepancy_detector = DiscrepancyDetector()
        self.settings = get_settings()
        
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
            
            chat_client = OpenAIChatClient(
                async_client=client,
                model_id=self.settings.model_id,
            )
            
            self._agent = ChatAgent(
                chat_client=chat_client,
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
        
        # Use AI for ambiguous cases
        if use_ai_for_ambiguous and match_type in [MatchType.PARTIAL, MatchType.FUZZY]:
            agent = await self._get_agent()
            if agent:
                ai_decision = await self._get_ai_decision(invoice, best_po, best_vendor, best_score)
                # AI can override match type and approval decision
                if ai_decision:
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
        
        # Create matching result
        return MatchingResult(
            invoice_id=invoice.invoice_number,
            po_number=best_po.po_number,
            matching_id=matching_id,
            match_type=match_type,
            match_score=best_score["overall_score"],
            matched=best_score["overall_score"] >= MatchingService.ACCEPTABLE_MATCH_THRESHOLD,
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
        
        for vendor_db in vendors[:3]:  # Top 3 vendor matches
            # Find POs with amount within 20% range
            amount_min = invoice.total_amount * 0.80
            amount_max = invoice.total_amount * 1.20
            
            pos = await self.po_repo.find_candidates(
                vendor_id=vendor_db.vendor_id,
                amount_min=amount_min,
                amount_max=amount_max,
            )
            
            # Convert to Pydantic models
            for po_db in pos:
                po = PurchaseOrder.model_validate(po_db)
                vendor = Vendor.model_validate(vendor_db)
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
        amount_score = MatchingService.calculate_amount_match_score(
            invoice.total_amount,
            po.total_amount
        )
        
        # Date score
        date_score = MatchingService.calculate_date_match_score(
            invoice.invoice_date,
            po.created_date
        )
        
        # Line items score
        line_matches, line_items_score = MatchingService.match_line_items(
            invoice.line_items,
            po.line_items
        )
        
        # Overall score
        overall_score = MatchingService.calculate_overall_match_score(
            vendor_score,
            amount_score,
            date_score,
            line_items_score
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
        if score >= MatchingService.EXACT_MATCH_THRESHOLD:
            return MatchType.EXACT
        elif score >= MatchingService.GOOD_MATCH_THRESHOLD:
            return MatchType.FUZZY
        elif score >= MatchingService.ACCEPTABLE_MATCH_THRESHOLD:
            return MatchType.PARTIAL
        else:
            return MatchType.NONE
    
    def _determine_approval_requirement(
        self,
        match_score: float,
        discrepancies: List[Discrepancy]
    ) -> tuple[bool, Optional[str]]:
        """Determine if manual approval is required."""
        # Critical discrepancies always require approval
        critical_count = sum(1 for d in discrepancies if d.severity == DiscrepancySeverity.CRITICAL)
        if critical_count > 0:
            return True, f"{critical_count} critical discrepancy(ies) detected"
        
        # Low match score requires approval
        if match_score < MatchingService.GOOD_MATCH_THRESHOLD:
            return True, f"Match score below threshold ({match_score:.1%})"
        
        # Major discrepancies require approval
        major_count = sum(1 for d in discrepancies if d.severity == DiscrepancySeverity.MAJOR)
        if major_count >= 2:
            return True, f"{major_count} major discrepancies detected"
        
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
- Total: ${invoice.total_amount:.2f}
- Line Items: {len(invoice.line_items)}

PURCHASE ORDER:
- Number: {po.po_number}
- Vendor: {vendor.vendor_name}
- Date: {po.created_date}
- Total: ${po.total_amount:.2f}
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
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    
                    if decision.get("decision") == "APPROVE":
                        logger.info(f"AI approved match: {decision.get('reasoning', 'No reason provided')}")
                        return {"match_type": MatchType.FUZZY, "approved": True}
                    else:
                        logger.info(f"AI flagged for review: {decision.get('reasoning', 'No reason provided')}")
                        return {"match_type": MatchType.PARTIAL, "approved": False}
                
                # Fallback: check for APPROVE/REVIEW in text
                if "APPROVE" in response_text.upper():
                    return {"match_type": MatchType.FUZZY, "approved": True}
                else:
                    return {"match_type": MatchType.PARTIAL, "approved": False}
                    
            except json.JSONDecodeError:
                # Fallback: check for APPROVE/REVIEW in text
                if "APPROVE" in response_text.upper():
                    return {"match_type": MatchType.FUZZY, "approved": True}
                else:
                    return {"match_type": MatchType.PARTIAL, "approved": False}
        
        except Exception as e:
            logger.error(f"AI agent error: {e}")
            return None
    
    async def close(self):
        """Cleanup resources."""
        self._agent = None
