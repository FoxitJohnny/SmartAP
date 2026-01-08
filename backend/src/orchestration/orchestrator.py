"""
Invoice processing orchestrator using LangGraph.

Main orchestration class that manages the complete invoice
processing workflow from extraction to approval decision.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.repositories import (
    InvoiceRepository,
    PurchaseOrderRepository,
    VendorRepository,
    MatchingRepository,
    RiskRepository,
)
from .workflow_state import WorkflowState, create_initial_state, ProcessingDecision
from .workflow_nodes import WorkflowNodes
from .workflow_graph import create_workflow_graph


logger = logging.getLogger(__name__)


class InvoiceProcessingOrchestrator:
    """
    Orchestrates multi-agent invoice processing workflow.
    
    This class manages the complete invoice processing pipeline:
    1. Extraction validation
    2. PO matching
    3. Risk assessment
    4. Final decision
    
    Uses LangGraph for workflow orchestration and state management.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize orchestrator with database session.
        
        Args:
            db_session: Async SQLAlchemy session for database access
        """
        self.db_session = db_session
        
        # Initialize repositories
        self.invoice_repo = InvoiceRepository(db_session)
        self.po_repo = PurchaseOrderRepository(db_session)
        self.vendor_repo = VendorRepository(db_session)
        self.matching_repo = MatchingRepository(db_session)
        self.risk_repo = RiskRepository(db_session)
        
        # Initialize workflow nodes
        self.nodes = WorkflowNodes(
            invoice_repo=self.invoice_repo,
            po_repo=self.po_repo,
            vendor_repo=self.vendor_repo,
            matching_repo=self.matching_repo,
            risk_repo=self.risk_repo,
        )
        
        # Create workflow graph
        self.workflow = create_workflow_graph(self.nodes)
        
        logger.info("Invoice processing orchestrator initialized")
    
    async def process_invoice(
        self,
        document_id: str,
        vendor_id: Optional[str] = None,
    ) -> WorkflowState:
        """
        Process an invoice through the complete workflow.
        
        This method orchestrates:
        - Extraction validation
        - PO matching with AI assistance
        - Risk and fraud detection
        - Final approval decision
        
        Args:
            document_id: Document identifier for the invoice
            vendor_id: Optional vendor ID for risk assessment
            
        Returns:
            Final workflow state with decision and results
            
        Raises:
            Exception: If workflow execution fails critically
        """
        logger.info(f"Starting invoice processing for document {document_id}")
        
        try:
            # Create initial state
            initial_state = create_initial_state(
                document_id=document_id,
                vendor_id=vendor_id,
            )
            
            # Execute workflow
            logger.debug(f"Executing workflow for {document_id}")
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Log completion
            logger.info(
                f"Invoice processing completed for {document_id}: "
                f"decision={final_state.get('decision')}, "
                f"status={final_state.get('status')}, "
                f"time={final_state.get('processing_time_ms')}ms"
            )
            
            # Save final state to database (optional - could persist state for audit)
            await self._save_workflow_state(final_state)
            
            return final_state
            
        except Exception as e:
            logger.error(
                f"Invoice processing failed for {document_id}: {str(e)}",
                exc_info=True,
            )
            
            # Return error state
            error_state = create_initial_state(document_id, vendor_id)
            error_state["status"] = "failed"
            error_state["decision"] = ProcessingDecision.REQUIRES_REVIEW
            error_state["decision_reason"] = f"Workflow execution failed: {str(e)}"
            error_state["requires_manual_review"] = True
            error_state["errors"].append({
                "step": "orchestrator",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            })
            error_state["completed_at"] = datetime.utcnow()
            
            return error_state
    
    async def _save_workflow_state(self, state: WorkflowState) -> None:
        """
        Save workflow state to database for audit trail.
        
        This persists key workflow metadata that can be used for:
        - Audit logs
        - Performance monitoring
        - Decision traceability
        
        Args:
            state: Final workflow state to persist
        """
        try:
            # Update invoice with final decision
            invoice = await self.invoice_repo.get_by_document_id(state["document_id"])
            if invoice:
                invoice.processing_status = str(state.get("decision", "unknown"))
                invoice.requires_review = state.get("requires_manual_review", True)
                await self.db_session.commit()
                
                logger.debug(f"Saved workflow state for {state['document_id']}")
        
        except Exception as e:
            logger.warning(f"Failed to save workflow state: {str(e)}")
            # Don't fail the workflow if state saving fails
            pass
    
    async def get_processing_status(self, document_id: str) -> Dict[str, Any]:
        """
        Get current processing status for an invoice.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Dictionary with processing status information
        """
        try:
            # Retrieve invoice
            invoice = await self.invoice_repo.get_by_document_id(document_id)
            if not invoice:
                return {
                    "document_id": document_id,
                    "status": "not_found",
                    "message": "Invoice not found",
                }
            
            # Retrieve matching result
            matching_result = await self.matching_repo.get_by_document_id(document_id)
            
            # Retrieve risk assessment
            risk_assessment = await self.risk_repo.get_by_document_id(document_id)
            
            return {
                "document_id": document_id,
                "extraction_status": invoice.extraction_status,
                "processing_status": invoice.processing_status,
                "requires_review": invoice.requires_review,
                "matching_completed": matching_result is not None,
                "match_score": float(matching_result.match_score) if matching_result else None,
                "risk_completed": risk_assessment is not None,
                "risk_level": risk_assessment.risk_level if risk_assessment else None,
                "last_updated": invoice.updated_at.isoformat() if invoice.updated_at else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {str(e)}")
            return {
                "document_id": document_id,
                "status": "error",
                "message": str(e),
            }
    
    async def reprocess_invoice(
        self,
        document_id: str,
        vendor_id: Optional[str] = None,
    ) -> WorkflowState:
        """
        Reprocess an invoice (useful for failed or rejected invoices).
        
        Args:
            document_id: Document identifier
            vendor_id: Optional vendor ID
            
        Returns:
            Final workflow state
        """
        logger.info(f"Reprocessing invoice {document_id}")
        
        # Clear previous results (optional - could keep for audit)
        try:
            # Delete previous matching result
            matching_result = await self.matching_repo.get_by_document_id(document_id)
            if matching_result:
                await self.matching_repo.delete(matching_result.id)
            
            # Delete previous risk assessment
            risk_assessment = await self.risk_repo.get_by_document_id(document_id)
            if risk_assessment:
                await self.risk_repo.delete(risk_assessment.id)
            
            await self.db_session.commit()
            
        except Exception as e:
            logger.warning(f"Failed to clear previous results: {str(e)}")
            # Continue with reprocessing anyway
        
        # Process invoice
        return await self.process_invoice(document_id, vendor_id)
