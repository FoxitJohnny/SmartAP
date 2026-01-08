"""
Workflow state definitions for invoice processing orchestration.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    MATCHING = "matching"
    ASSESSING_RISK = "assessing_risk"
    DECIDING = "deciding"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingDecision(str, Enum):
    """Final processing decision."""
    AUTO_APPROVED = "auto_approved"
    REQUIRES_REVIEW = "requires_review"
    REQUIRES_INVESTIGATION = "requires_investigation"
    ESCALATED = "escalated"
    REJECTED = "rejected"


class WorkflowState(TypedDict, total=False):
    """
    State object for invoice processing workflow.
    
    This TypedDict defines the complete state that flows through
    the LangGraph workflow nodes.
    """
    # Core identifiers
    document_id: str
    vendor_id: Optional[str]
    
    # Workflow metadata
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime]
    current_step: str
    
    # Invoice extraction data
    extraction_completed: bool
    invoice_data: Optional[Dict[str, Any]]
    extraction_confidence: Optional[float]
    extraction_error: Optional[str]
    
    # PO matching results
    matching_completed: bool
    matching_result: Optional[Dict[str, Any]]
    match_score: Optional[float]
    match_type: Optional[str]
    discrepancies: List[Dict[str, Any]]
    matching_error: Optional[str]
    
    # Risk assessment results
    risk_completed: bool
    risk_assessment: Optional[Dict[str, Any]]
    risk_level: Optional[str]
    risk_score: Optional[float]
    risk_flags: List[Dict[str, Any]]
    is_duplicate: bool
    risk_error: Optional[str]
    
    # Final decision
    decision: Optional[ProcessingDecision]
    decision_reason: str
    requires_manual_review: bool
    recommended_actions: List[str]
    
    # Error tracking
    errors: List[Dict[str, str]]
    retry_count: int
    
    # Processing metrics
    processing_time_ms: Optional[int]
    ai_calls_made: int


def create_initial_state(document_id: str, vendor_id: Optional[str] = None) -> WorkflowState:
    """
    Create initial workflow state for a new invoice processing job.
    
    Args:
        document_id: Document identifier
        vendor_id: Optional vendor identifier for risk assessment
        
    Returns:
        Initial workflow state with default values
    """
    return WorkflowState(
        document_id=document_id,
        vendor_id=vendor_id,
        status=WorkflowStatus.PENDING,
        started_at=datetime.utcnow(),
        completed_at=None,
        current_step="initialization",
        extraction_completed=False,
        invoice_data=None,
        extraction_confidence=None,
        extraction_error=None,
        matching_completed=False,
        matching_result=None,
        match_score=None,
        match_type=None,
        discrepancies=[],
        matching_error=None,
        risk_completed=False,
        risk_assessment=None,
        risk_level=None,
        risk_score=None,
        risk_flags=[],
        is_duplicate=False,
        risk_error=None,
        decision=None,
        decision_reason="",
        requires_manual_review=False,
        recommended_actions=[],
        errors=[],
        retry_count=0,
        processing_time_ms=None,
        ai_calls_made=0,
    )
