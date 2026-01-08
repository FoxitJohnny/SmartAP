"""
PO Matching Agent

AI Agent that matches invoices to purchase orders using the Microsoft Agent Framework.
"""

import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Try to import Azure AI agent clients - may not be available in all environments
try:
    from azure.ai.projects.aio import AIProjectClient
    from azure.ai.agents.aio import AgentsClient
    HAS_AZURE_AGENTS = True
except ImportError:
    AIProjectClient = None
    AgentsClient = None
    HAS_AZURE_AGENTS = False

from ..config import get_settings
from ..models import (
    Invoice,
    PurchaseOrder,
    MatchingResult,
    MatchType,
    Discrepancy,
    DiscrepancySeverity,
    LineItemMatch,
)
from ..db.repositories import PurchaseOrderRepository, VendorRepository
from ..services.matching_service import MatchingService
from ..services.discrepancy_detector import DiscrepancyDetector

logger = logging.getLogger(__name__)


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
        
        # AI client for complex cases
        self.ai_client: Optional[Any] = None
        self.agents_client: Optional[Any] = None
        self.agent: Optional[Any] = None
    
    async def initialize(self):
        """Initialize AI agent client."""
        if not HAS_AZURE_AGENTS:
            logger.warning("Azure AI Agents SDK not available - using algorithmic matching only")
            return
        
        settings = get_settings()
        if settings.github_token:
            # Initialize AI client
            self.ai_client = AIProjectClient()
            self.agents_client = AgentsClient()
            
            # Create agent for complex matching decisions
            self.agent = await self.agents_client.create_agent(
                model_id=settings.model_id,
                name="PO Matching Agent",
                instructions="""You are an expert at matching invoices to purchase orders.
                
Your role:
1. Analyze invoice and PO data provided by the system
2. Determine if they match based on vendor, amounts, line items, dates
3. Identify discrepancies and their severity
4. Recommend whether to approve, flag for review, or reject

Consider:
- Vendor name variations (abbreviations, Inc vs LLC, etc.)
- Line item descriptions (different wording for same product)
- Amount differences (tax, shipping, discounts)
- Date reasonableness (invoice should be after PO)
- Quantity and pricing alignment

Provide clear reasoning for your decisions.""",
            )
    
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
            if self.agent:
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
    ) -> List[tuple[PurchaseOrder, Any]]:
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
        vendor: Any
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
        vendor: Any,
        score_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Use AI agent for complex matching decisions."""
        if not self.agent or not self.agents_client:
            return None
        
        # Prepare context for AI
        context = f"""
Analyze this invoice-PO match:

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

Should this match be approved? Consider vendor name variations, reasonable amount differences, and date alignment.
Respond with: APPROVE or REVIEW_REQUIRED and your reasoning.
"""
        
        try:
            # Query AI agent
            thread = await self.agents_client.create_thread()
            await self.agents_client.create_message(
                thread_id=thread.id,
                role="user",
                content=context
            )
            
            run = await self.agents_client.create_run(
                thread_id=thread.id,
                agent_id=self.agent.id
            )
            
            # Wait for completion (simplified)
            # In production, use proper async waiting
            response = await self.agents_client.get_message(
                thread_id=thread.id,
                message_id=run.id
            )
            
            # Parse AI response
            if "APPROVE" in response.content:
                return {"match_type": MatchType.FUZZY, "approved": True}
            else:
                return {"match_type": MatchType.PARTIAL, "approved": False}
        
        except Exception as e:
            print(f"AI agent error: {e}")
            return None
    
    async def close(self):
        """Cleanup resources."""
        if self.agents_client:
            await self.agents_client.close()
        if self.ai_client:
            await self.ai_client.close()
