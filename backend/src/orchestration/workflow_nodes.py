"""
Node functions for invoice processing workflow.

Each node represents a step in the invoice processing pipeline
and updates the workflow state accordingly.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from ..agents.extraction_agent import ExtractionAgent
from ..agents.po_matching_agent import POMatchingAgent
from ..agents.risk_detection_agent import RiskDetectionAgent
from ..db.repositories import (
    InvoiceRepository,
    PurchaseOrderRepository,
    VendorRepository,
    MatchingRepository,
    RiskRepository,
)
from .workflow_state import WorkflowState, WorkflowStatus, ProcessingDecision
from ..services.processing_event_service import ProcessingEventService


event_service = ProcessingEventService()


logger = logging.getLogger(__name__)


class WorkflowNodes:
    """
    Collection of node functions for invoice processing workflow.
    
    Each node is a function that receives the workflow state,
    performs an operation, and returns updated state.
    """
    
    def __init__(
        self,
        invoice_repo: InvoiceRepository,
        po_repo: PurchaseOrderRepository,
        vendor_repo: VendorRepository,
        matching_repo: MatchingRepository,
        risk_repo: RiskRepository,
    ):
        """
        Initialize workflow nodes with repository dependencies.
        
        Args:
            invoice_repo: Invoice repository for data access
            po_repo: Purchase order repository
            vendor_repo: Vendor repository
            matching_repo: Matching results repository
            risk_repo: Risk assessment repository
        """
        self.invoice_repo = invoice_repo
        self.po_repo = po_repo
        self.vendor_repo = vendor_repo
        self.matching_repo = matching_repo
        self.risk_repo = risk_repo
    
    async def validate_extraction(self, state: WorkflowState) -> WorkflowState:
        """
        Validate that invoice extraction has been completed.
        
        Node: validate_extraction
        Purpose: Ensure invoice has been extracted before processing
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        logger.info(f"Validating extraction for document {state['document_id']}")

        await event_service.emit(
            entity_type="invoice",
            entity_id=state["document_id"],
            stage="validate_extraction",
            status="started",
            message="Validating extraction",
        )
        
        state["current_step"] = "validate_extraction"
        state["status"] = WorkflowStatus.EXTRACTING
        
        try:
            # Retrieve invoice from database
            invoice = await self.invoice_repo.get_by_document_id(state["document_id"])
            
            if not invoice:
                error_msg = f"Invoice not found: {state['document_id']}"
                logger.error(error_msg)
                await event_service.emit(
                    entity_type="invoice",
                    entity_id=state["document_id"],
                    stage="validate_extraction",
                    status="failed",
                    level="ERROR",
                    message=error_msg,
                )
                state["extraction_error"] = error_msg
                state["errors"].append({
                    "step": "validate_extraction",
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                state["status"] = WorkflowStatus.FAILED
                return state
            
            # Check extraction status - InvoiceDB uses 'status' field with InvoiceStatus enum
            # Extraction is complete if status is not INGESTED or FAILED
            from ..models.invoice import InvoiceStatus as InvStatus
            if invoice.status in (InvStatus.INGESTED, InvStatus.FAILED):
                error_msg = f"Invoice extraction not completed: {invoice.status.value}"
                logger.warning(error_msg)
                await event_service.emit(
                    entity_type="invoice",
                    entity_id=state["document_id"],
                    stage="validate_extraction",
                    status="failed",
                    level="WARNING",
                    message=error_msg,
                    details={"invoice_status": invoice.status.value},
                )
                state["extraction_error"] = error_msg
                state["errors"].append({
                    "step": "validate_extraction",
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                state["status"] = WorkflowStatus.FAILED
                return state
            
            # Store invoice data in state
            # InvoiceDB stores extracted data in invoice_data JSON field
            state["extraction_completed"] = True
            invoice_data = invoice.invoice_data or {}
            # Support both "total" and "total_amount" field names for backwards compatibility
            total_value = invoice_data.get("total") or invoice_data.get("total_amount", 0)
            state["invoice_data"] = {
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice_data.get("invoice_date"),
                "due_date": invoice_data.get("due_date"),
                "total_amount": float(total_value) if total_value else 0.0,
                "currency": invoice_data.get("currency", "USD"),
                "vendor_name": invoice_data.get("vendor_name"),
                "po_number": invoice_data.get("po_number"),
            }
            state["extraction_confidence"] = invoice.extraction_confidence
            
            # Set vendor_id if not already set
            vendor_name = invoice_data.get("vendor_name")
            if not state.get("vendor_id") and vendor_name:
                # Try to find vendor by name
                vendor = await self.vendor_repo.get_by_name(vendor_name)
                if vendor:
                    state["vendor_id"] = vendor.vendor_id
            
            logger.info(f"Extraction validation successful for {state['document_id']}")

            await event_service.emit(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="validate_extraction",
                status="succeeded",
                message="Extraction validated",
                details={"extraction_confidence": state.get("extraction_confidence")},
            )
            
        except Exception as e:
            error_msg = f"Extraction validation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await event_service.emit_error(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="validate_extraction",
                message="Extraction validation failed",
                error=e,
            )
            state["extraction_error"] = error_msg
            state["errors"].append({
                "step": "validate_extraction",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            })
            state["status"] = WorkflowStatus.FAILED
        
        return state
    
    async def match_to_po(self, state: WorkflowState) -> WorkflowState:
        """
        Match invoice to purchase order.
        
        Node: match_to_po
        Purpose: Find matching PO and calculate discrepancies
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        logger.info(f"Matching invoice {state['document_id']} to PO")

        await event_service.emit(
            entity_type="invoice",
            entity_id=state["document_id"],
            stage="match",
            status="started",
            message="PO matching started (workflow)",
        )
        
        state["current_step"] = "match_to_po"
        state["status"] = WorkflowStatus.MATCHING
        
        try:
            # Create PO matching agent (takes po_repository and vendor_repository)
            matching_agent = POMatchingAgent(
                po_repository=self.po_repo,
                vendor_repository=self.vendor_repo,
            )
            
            # Build Invoice model from state invoice_data
            from ..models.invoice import Invoice
            from decimal import Decimal
            invoice_data = state.get("invoice_data", {})
            invoice = Invoice(
                invoice_number=invoice_data.get("invoice_number", ""),
                vendor_name=invoice_data.get("vendor_name", ""),
                total=Decimal(str(invoice_data.get("total_amount", 0))),
                invoice_date=invoice_data.get("invoice_date"),
                due_date=invoice_data.get("due_date"),
                po_number=invoice_data.get("po_number"),
                currency=invoice_data.get("currency", "USD"),
                document_id=state.get("document_id"),  # Include for duplicate detection self-exclusion
            )
            
            # Perform matching with AI assistance for ambiguous cases
            matching_result = await matching_agent.match_invoice_to_po(
                invoice=invoice,
                use_ai_for_ambiguous=True,
            )
            
            # Update state with matching results
            state["matching_completed"] = True
            state["matching_result"] = matching_result.model_dump()
            state["match_score"] = matching_result.match_score
            state["match_type"] = matching_result.match_type
            state["discrepancies"] = [d.model_dump() for d in matching_result.discrepancies]
            
            # Note: ai_decision_used is not a field on MatchingResult
            # The matching algorithm may internally use AI but doesn't expose this
            
            logger.info(
                f"PO matching completed for {state['document_id']}: "
                f"score={matching_result.match_score:.2f}, "
                f"type={matching_result.match_type}"
            )

            await event_service.emit(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="match",
                status="succeeded",
                message="PO matching completed (workflow)",
                details={
                    "match_score": float(matching_result.match_score),
                    "match_type": str(matching_result.match_type),
                    "po_number": matching_result.po_number,
                    "matched": bool(matching_result.matched),
                },
            )
            
        except Exception as e:
            error_msg = f"PO matching failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await event_service.emit_error(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="match",
                message="PO matching failed (workflow)",
                error=e,
            )
            state["matching_error"] = error_msg
            state["errors"].append({
                "step": "match_to_po",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            })
            # Don't fail workflow - continue to risk assessment
            state["matching_completed"] = False
        
        return state
    
    async def assess_risk(self, state: WorkflowState) -> WorkflowState:
        """
        Assess invoice risk and detect fraud.
        
        Node: assess_risk
        Purpose: Detect duplicates, vendor risk, price anomalies
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        logger.info(f"Assessing risk for invoice {state['document_id']}")

        await event_service.emit(
            entity_type="invoice",
            entity_id=state["document_id"],
            stage="risk",
            status="started",
            message="Risk assessment started (workflow)",
            details={"vendor_id": state.get("vendor_id")},
        )
        
        state["current_step"] = "assess_risk"
        state["status"] = WorkflowStatus.ASSESSING_RISK
        
        try:
            # Create risk detection agent (takes invoice_repo and vendor_repo)
            risk_agent = RiskDetectionAgent(
                invoice_repo=self.invoice_repo,
                vendor_repo=self.vendor_repo,
            )
            
            # Build Invoice model from state invoice_data
            from ..models.invoice import Invoice
            from decimal import Decimal
            invoice_data = state.get("invoice_data", {})
            invoice = Invoice(
                invoice_number=invoice_data.get("invoice_number", ""),
                vendor_name=invoice_data.get("vendor_name", ""),
                total=Decimal(str(invoice_data.get("total_amount", 0))),
                invoice_date=invoice_data.get("invoice_date"),
                due_date=invoice_data.get("due_date"),
                po_number=invoice_data.get("po_number"),
                currency=invoice_data.get("currency", "USD"),
                document_id=state.get("document_id"),  # Include for duplicate detection self-exclusion
            )
            
            # Perform risk assessment
            # Retrieve matching result from state if available
            matching_result_data = state.get("matching_result")
            matching_result_obj = None
            if matching_result_data:
                try:
                    from ..models.matching import MatchingResult
                    if isinstance(matching_result_data, dict):
                        matching_result_obj = MatchingResult(**matching_result_data)
                    elif isinstance(matching_result_data, MatchingResult):
                        matching_result_obj = matching_result_data
                except Exception:
                    pass

            risk_assessment = await risk_agent.assess_risk(
                invoice=invoice,
                vendor_id=state.get("vendor_id"),
                matching_result=matching_result_obj,
            )
            
            # Update state with risk results
            state["risk_completed"] = True
            state["risk_assessment"] = risk_assessment.model_dump()
            state["risk_level"] = risk_assessment.risk_level
            state["risk_score"] = risk_assessment.risk_score
            state["risk_flags"] = [f.model_dump() for f in risk_assessment.risk_flags]
            state["is_duplicate"] = risk_assessment.duplicate_info.is_duplicate if risk_assessment.duplicate_info else False
            
            logger.info(
                f"Risk assessment completed for {state['document_id']}: "
                f"level={risk_assessment.risk_level}, "
                f"score={risk_assessment.risk_score:.2f}, "
                f"flags={len(risk_assessment.risk_flags)}"
            )

            await event_service.emit(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="risk",
                status="succeeded",
                message="Risk assessment completed (workflow)",
                details={
                    "risk_level": str(risk_assessment.risk_level),
                    "risk_score": float(risk_assessment.risk_score),
                    "flags": len(risk_assessment.risk_flags),
                    "is_duplicate": bool(state.get("is_duplicate", False)),
                },
            )
            
        except Exception as e:
            error_msg = f"Risk assessment failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await event_service.emit_error(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="risk",
                message="Risk assessment failed (workflow)",
                error=e,
            )
            state["risk_error"] = error_msg
            state["errors"].append({
                "step": "assess_risk",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            })
            # Don't fail workflow - continue to decision
            state["risk_completed"] = False
        
        return state
    
    async def make_decision(self, state: WorkflowState) -> WorkflowState:
        """
        Make final processing decision based on matching and risk results.
        
        Node: make_decision
        Purpose: Determine approval, review, or rejection
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with final decision
        """
        logger.info(f"Making decision for invoice {state['document_id']}")

        await event_service.emit(
            entity_type="invoice",
            entity_id=state["document_id"],
            stage="decision",
            status="started",
            message="Decisioning started",
        )
        
        state["current_step"] = "make_decision"
        state["status"] = WorkflowStatus.DECIDING
        
        try:
            decision_reason_parts = []
            recommended_actions = []
            
            # Check for critical errors
            if state.get("extraction_error"):
                state["decision"] = ProcessingDecision.REJECTED
                state["decision_reason"] = f"Extraction failed: {state['extraction_error']}"
                state["requires_manual_review"] = True
                state["recommended_actions"] = ["Review extraction error", "Re-upload document"]
                state["status"] = WorkflowStatus.COMPLETED
                return state
            
            # Evaluate duplicate status
            if state.get("is_duplicate"):
                state["decision"] = ProcessingDecision.REJECTED
                state["decision_reason"] = "Duplicate invoice detected"
                state["requires_manual_review"] = True
                state["recommended_actions"] = ["Verify duplicate status", "Check existing invoice"]
                state["status"] = WorkflowStatus.COMPLETED
                return state
            
            # Evaluate risk level
            risk_level = state.get("risk_level", "unknown")
            risk_flags = state.get("risk_flags", [])
            critical_flags = [f for f in risk_flags if f.get("severity") == "critical"]
            high_flags = [f for f in risk_flags if f.get("severity") == "high"]
            
            if risk_level == "critical" or len(critical_flags) >= 2:
                state["decision"] = ProcessingDecision.REJECTED
                decision_reason_parts.append(f"Critical risk level ({len(critical_flags)} critical flags)")
                state["requires_manual_review"] = True
                recommended_actions.append("Review all risk flags")
                recommended_actions.append("Investigate vendor")
            
            elif len(critical_flags) == 1:
                state["decision"] = ProcessingDecision.ESCALATED
                decision_reason_parts.append(f"One critical risk flag: {critical_flags[0].get('flag_type')}")
                state["requires_manual_review"] = True
                recommended_actions.append("Senior management review required")
                recommended_actions.append("Investigate specific flag")
            
            elif risk_level == "high" or len(high_flags) >= 2:
                state["decision"] = ProcessingDecision.REQUIRES_INVESTIGATION
                decision_reason_parts.append(f"High risk level ({len(high_flags)} high flags)")
                state["requires_manual_review"] = True
                recommended_actions.append("Investigate risk factors")
                recommended_actions.append("Verify vendor information")
            
            # Evaluate matching results
            elif state.get("matching_completed"):
                match_score = state.get("match_score", 0)
                match_type = state.get("match_type", "none")
                discrepancies = state.get("discrepancies", [])
                critical_discrepancies = [d for d in discrepancies if d.get("severity") == "critical"]
                
                if match_type == "none" or match_score < 0.70:
                    state["decision"] = ProcessingDecision.REQUIRES_REVIEW
                    decision_reason_parts.append(f"Low match score: {match_score:.2f}")
                    state["requires_manual_review"] = True
                    recommended_actions.append("Review PO matching")
                    recommended_actions.append("Verify invoice details")
                
                elif len(critical_discrepancies) > 0:
                    state["decision"] = ProcessingDecision.REQUIRES_REVIEW
                    decision_reason_parts.append(f"{len(critical_discrepancies)} critical discrepancies")
                    state["requires_manual_review"] = True
                    recommended_actions.append("Review discrepancies")
                    recommended_actions.append("Contact vendor")
                
                elif risk_level == "medium":
                    state["decision"] = ProcessingDecision.REQUIRES_REVIEW
                    decision_reason_parts.append("Medium risk level")
                    state["requires_manual_review"] = True
                    recommended_actions.append("Review risk assessment")
                
                elif match_score >= 0.95 and risk_level == "low":
                    state["decision"] = ProcessingDecision.AUTO_APPROVED
                    decision_reason_parts.append(f"High match score ({match_score:.2f}) and low risk")
                    state["requires_manual_review"] = False
                    recommended_actions.append("Proceed with payment")
                
                else:
                    state["decision"] = ProcessingDecision.REQUIRES_REVIEW
                    decision_reason_parts.append(f"Match score {match_score:.2f}, risk {risk_level}")
                    state["requires_manual_review"] = True
                    recommended_actions.append("Review for approval")
            
            else:
                # Matching failed - requires review
                state["decision"] = ProcessingDecision.REQUIRES_REVIEW
                decision_reason_parts.append("PO matching failed")
                state["requires_manual_review"] = True
                recommended_actions.append("Manually match to PO")
                recommended_actions.append("Review invoice details")
            
            # Set default decision if not already set
            if not state.get("decision"):
                state["decision"] = ProcessingDecision.REQUIRES_REVIEW
                decision_reason_parts.append("Default to manual review")
                state["requires_manual_review"] = True
            
            state["decision_reason"] = "; ".join(decision_reason_parts)
            state["recommended_actions"] = recommended_actions
            state["status"] = WorkflowStatus.COMPLETED
            state["completed_at"] = datetime.utcnow()
            
            # Calculate processing time
            if state.get("started_at"):
                processing_time = (state["completed_at"] - state["started_at"]).total_seconds() * 1000
                state["processing_time_ms"] = int(processing_time)
            
            logger.info(
                f"Decision made for {state['document_id']}: "
                f"{state['decision']} - {state['decision_reason']}"
            )

            await event_service.emit(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="decision",
                status="succeeded",
                message="Decisioning completed",
                details={
                    "decision": str(state.get("decision")),
                    "requires_manual_review": bool(state.get("requires_manual_review", True)),
                    "processing_time_ms": state.get("processing_time_ms"),
                },
            )
            
        except Exception as e:
            error_msg = f"Decision making failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await event_service.emit_error(
                entity_type="invoice",
                entity_id=state["document_id"],
                stage="decision",
                message="Decisioning failed",
                error=e,
            )
            state["errors"].append({
                "step": "make_decision",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat(),
            })
            state["status"] = WorkflowStatus.FAILED
            state["decision"] = ProcessingDecision.REQUIRES_REVIEW
            state["decision_reason"] = "Decision process failed - requires manual review"
            state["requires_manual_review"] = True
        
        return state
    
    async def handle_error(self, state: WorkflowState) -> WorkflowState:
        """
        Handle workflow errors and determine recovery strategy.
        
        Node: handle_error
        Purpose: Error recovery and retry logic
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        logger.warning(f"Handling error for invoice {state['document_id']}")
        
        state["current_step"] = "handle_error"
        state["status"] = WorkflowStatus.FAILED
        state["decision"] = ProcessingDecision.REQUIRES_REVIEW
        state["decision_reason"] = f"Workflow failed with {len(state.get('errors', []))} errors"
        state["requires_manual_review"] = True
        state["recommended_actions"] = [
            "Review error logs",
            "Check data quality",
            "Retry processing if transient failure",
        ]
        state["completed_at"] = datetime.utcnow()
        
        return state
