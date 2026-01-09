"""
Approval Workflow API Routes

Provides REST API endpoints for managing invoice approval workflows,
including approval chain configuration, approval submission, eSign integration,
escalation handling, and audit trail retrieval.

Key Features:
- Create and manage approval chains with threshold rules
- Submit invoices for approval based on amount thresholds
- Approve/reject/escalate approval requests
- Trigger eSign workflows for high-value invoices
- Track approval status and history
- Retrieve pending approvals for current user
- Generate audit trails for compliance

Author: SmartAP Development Team
Date: 2025
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..db.database import get_session as get_db
from ..models.approval import (
    ApprovalChain,
    ApprovalLevel,
    ApprovalWorkflow,
    ApprovalAction,
    ApprovalNotification,
    ArchivedDocument,
    ApprovalStatus,
    ApproverAction,
    EscalationReason,
)
from ..models.invoice import Invoice
from ..integrations.foxit.esign import FoxitESignConnector, SignerRole
from ..services.archival_service import ArchivalService
from ..auth import get_current_user, User
from ..config import get_settings

router = APIRouter(prefix="/api/v1/approvals", tags=["Approval Workflows"])

# Pydantic schemas for request/response validation
from pydantic import BaseModel, Field, EmailStr


class ApprovalLevelCreate(BaseModel):
    """Schema for creating approval level"""
    level_number: int = Field(..., ge=1, le=10)
    level_name: str = Field(..., min_length=1, max_length=100)
    approver_ids: List[str] = Field(default_factory=list)
    approver_emails: List[EmailStr] = Field(..., min_items=1)
    required_approvals: int = Field(1, ge=1)
    timeout_hours: Optional[int] = Field(72, ge=1, le=720)


class ApprovalChainCreate(BaseModel):
    """Schema for creating approval chain"""
    name: str = Field(..., min_length=1, max_length=255)
    min_amount: int = Field(0, ge=0)  # Amount in cents
    max_amount: Optional[int] = Field(None, ge=0)
    levels: List[ApprovalLevelCreate] = Field(..., min_items=1)
    sequential_approval: bool = True
    require_esign: bool = False
    esign_threshold: Optional[int] = None  # Amount threshold for eSign
    approval_timeout_hours: int = Field(72, ge=1, le=720)
    auto_escalate_on_timeout: bool = True


class ApprovalChainUpdate(BaseModel):
    """Schema for updating approval chain"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    min_amount: Optional[int] = Field(None, ge=0)
    max_amount: Optional[int] = Field(None, ge=0)
    sequential_approval: Optional[bool] = None
    require_esign: Optional[bool] = None
    esign_threshold: Optional[int] = None
    approval_timeout_hours: Optional[int] = Field(None, ge=1, le=720)
    auto_escalate_on_timeout: Optional[bool] = None


class ApprovalWorkflowCreate(BaseModel):
    """Schema for creating approval workflow"""
    invoice_id: str
    chain_id: Optional[str] = None  # If None, auto-select based on amount


class ApprovalActionCreate(BaseModel):
    """Schema for creating approval action"""
    action: ApproverAction
    comment: Optional[str] = Field(None, max_length=1000)
    forwarded_to: Optional[EmailStr] = None
    escalated_to: Optional[EmailStr] = None


class ApprovalChainResponse(BaseModel):
    """Schema for approval chain response"""
    id: str
    name: str
    min_amount: int
    max_amount: Optional[int]
    required_approvers: int
    sequential_approval: bool
    require_esign: bool
    esign_threshold: Optional[int]
    approval_timeout_hours: int
    auto_escalate_on_timeout: bool
    created_at: datetime
    updated_at: datetime
    levels: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ApprovalWorkflowResponse(BaseModel):
    """Schema for approval workflow response"""
    id: str
    invoice_id: str
    chain_id: str
    chain_name: str
    status: ApprovalStatus
    current_level: int
    esign_required: bool
    esign_request_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_expired: bool
    time_remaining_hours: Optional[float]
    escalated: bool
    escalation_reason: Optional[EscalationReason]
    approval_actions: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class ApprovalActionResponse(BaseModel):
    """Schema for approval action response"""
    id: str
    workflow_id: str
    approver_email: str
    level_number: int
    action: ApproverAction
    comment: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Approval Chain Management
# ============================================================================

@router.post("/chains", response_model=ApprovalChainResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_chain(
    chain_data: ApprovalChainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new approval chain with multiple levels.
    
    Approval chains define the approval process based on invoice amount thresholds.
    Example: $0-$1000 = Manager approval, $1000-$5000 = Director approval, $5000+ = CFO + eSign
    """
    # Validate amount range
    if chain_data.max_amount and chain_data.max_amount <= chain_data.min_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_amount must be greater than min_amount"
        )
    
    # Calculate total required approvers
    total_approvers = sum(len(level.approver_emails) for level in chain_data.levels)
    
    # Create approval chain
    chain = ApprovalChain(
        name=chain_data.name,
        min_amount=chain_data.min_amount,
        max_amount=chain_data.max_amount,
        required_approvers=total_approvers,
        sequential_approval=chain_data.sequential_approval,
        require_esign=chain_data.require_esign,
        esign_threshold=chain_data.esign_threshold,
        approval_timeout_hours=chain_data.approval_timeout_hours,
        auto_escalate_on_timeout=chain_data.auto_escalate_on_timeout
    )
    
    db.add(chain)
    db.flush()  # Get chain ID
    
    # Create approval levels
    for level_data in chain_data.levels:
        level = ApprovalLevel(
            chain_id=chain.id,
            level_number=level_data.level_number,
            level_name=level_data.level_name,
            approver_ids=level_data.approver_ids,
            approver_emails=level_data.approver_emails,
            required_approvals=level_data.required_approvals,
            timeout_hours=level_data.timeout_hours
        )
        db.add(level)
    
    db.commit()
    db.refresh(chain)
    
    # Format response
    levels_response = [
        {
            "level_number": level.level_number,
            "level_name": level.level_name,
            "approver_emails": level.approver_emails,
            "required_approvals": level.required_approvals,
            "timeout_hours": level.timeout_hours
        }
        for level in chain.levels
    ]
    
    return ApprovalChainResponse(
        id=str(chain.id),
        name=chain.name,
        min_amount=chain.min_amount,
        max_amount=chain.max_amount,
        required_approvers=chain.required_approvers,
        sequential_approval=chain.sequential_approval,
        require_esign=chain.require_esign,
        esign_threshold=chain.esign_threshold,
        approval_timeout_hours=chain.approval_timeout_hours,
        auto_escalate_on_timeout=chain.auto_escalate_on_timeout,
        created_at=chain.created_at,
        updated_at=chain.updated_at,
        levels=levels_response
    )


@router.get("/chains", response_model=List[ApprovalChainResponse])
async def list_approval_chains(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all approval chains.
    """
    chains = db.query(ApprovalChain).offset(skip).limit(limit).all()
    
    return [
        ApprovalChainResponse(
            id=str(chain.id),
            name=chain.name,
            min_amount=chain.min_amount,
            max_amount=chain.max_amount,
            required_approvers=chain.required_approvers,
            sequential_approval=chain.sequential_approval,
            require_esign=chain.require_esign,
            esign_threshold=chain.esign_threshold,
            approval_timeout_hours=chain.approval_timeout_hours,
            auto_escalate_on_timeout=chain.auto_escalate_on_timeout,
            created_at=chain.created_at,
            updated_at=chain.updated_at,
            levels=[
                {
                    "level_number": level.level_number,
                    "level_name": level.level_name,
                    "approver_emails": level.approver_emails,
                    "required_approvals": level.required_approvals,
                    "timeout_hours": level.timeout_hours
                }
                for level in chain.levels
            ]
        )
        for chain in chains
    ]


@router.get("/chains/{chain_id}", response_model=ApprovalChainResponse)
async def get_approval_chain(
    chain_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get approval chain details.
    """
    chain = db.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
    
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval chain not found: {chain_id}"
        )
    
    return ApprovalChainResponse(
        id=str(chain.id),
        name=chain.name,
        min_amount=chain.min_amount,
        max_amount=chain.max_amount,
        required_approvers=chain.required_approvers,
        sequential_approval=chain.sequential_approval,
        require_esign=chain.require_esign,
        esign_threshold=chain.esign_threshold,
        approval_timeout_hours=chain.approval_timeout_hours,
        auto_escalate_on_timeout=chain.auto_escalate_on_timeout,
        created_at=chain.created_at,
        updated_at=chain.updated_at,
        levels=[
            {
                "level_number": level.level_number,
                "level_name": level.level_name,
                "approver_emails": level.approver_emails,
                "required_approvals": level.required_approvals,
                "timeout_hours": level.timeout_hours
            }
            for level in chain.levels
        ]
    )


# ============================================================================
# Approval Workflow Management
# ============================================================================

@router.post("/workflows", response_model=ApprovalWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_workflow(
    workflow_data: ApprovalWorkflowCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit an invoice for approval.
    
    If chain_id is not provided, the system will auto-select the appropriate
    approval chain based on the invoice amount.
    """
    # Check if invoice exists
    invoice = db.query(InvoiceDocument).filter(
        InvoiceDocument.invoice_id == workflow_data.invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {workflow_data.invoice_id}"
        )
    
    # Check if workflow already exists
    existing_workflow = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.invoice_id == workflow_data.invoice_id
    ).first()
    
    if existing_workflow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval workflow already exists for invoice: {workflow_data.invoice_id}"
        )
    
    # Auto-select approval chain if not provided
    if not workflow_data.chain_id:
        invoice_amount = invoice.total_amount or 0
        
        # Query chains that match the invoice amount
        chain = db.query(ApprovalChain).filter(
            and_(
                ApprovalChain.min_amount <= invoice_amount,
                or_(
                    ApprovalChain.max_amount.is_(None),
                    ApprovalChain.max_amount >= invoice_amount
                )
            )
        ).first()
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No approval chain found for invoice amount: ${invoice_amount/100:.2f}"
            )
        
        chain_id = chain.id
    else:
        chain_id = workflow_data.chain_id
        chain = db.query(ApprovalChain).filter(ApprovalChain.id == chain_id).first()
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval chain not found: {chain_id}"
            )
    
    # Determine if eSign is required
    invoice_amount = invoice.total_amount or 0
    esign_required = chain.require_esign and (
        chain.esign_threshold is None or invoice_amount >= chain.esign_threshold
    )
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(hours=chain.approval_timeout_hours)
    
    # Create approval workflow
    workflow = ApprovalWorkflow(
        invoice_id=workflow_data.invoice_id,
        chain_id=chain_id,
        status=ApprovalStatus.PENDING,
        current_level=1,
        esign_required=esign_required,
        expires_at=expires_at
    )
    
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # Send notifications to level 1 approvers
    level_1 = db.query(ApprovalLevel).filter(
        and_(
            ApprovalLevel.chain_id == chain_id,
            ApprovalLevel.level_number == 1
        )
    ).first()
    
    if level_1:
        for email in level_1.approver_emails:
            notification = ApprovalNotification(
                workflow_id=workflow.id,
                recipient_email=email,
                notification_type="approval_request",
                delivered=False
            )
            db.add(notification)
        
        db.commit()
    
    return _format_workflow_response(workflow, db)


@router.get("/workflows/{workflow_id}", response_model=ApprovalWorkflowResponse)
async def get_approval_workflow(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get approval workflow status and history.
    """
    workflow = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval workflow not found: {workflow_id}"
        )
    
    return _format_workflow_response(workflow, db)


@router.get("/workflows", response_model=List[ApprovalWorkflowResponse])
async def list_approval_workflows(
    status_filter: Optional[ApprovalStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List approval workflows with optional status filter.
    """
    query = db.query(ApprovalWorkflow)
    
    if status_filter:
        query = query.filter(ApprovalWorkflow.status == status_filter)
    
    workflows = query.order_by(desc(ApprovalWorkflow.created_at)).offset(skip).limit(limit).all()
    
    return [_format_workflow_response(wf, db) for wf in workflows]


@router.get("/workflows/pending/me", response_model=List[ApprovalWorkflowResponse])
async def get_my_pending_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get pending approvals for current user.
    """
    # Query workflows where current user is an approver at the current level
    workflows = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.status.in_([ApprovalStatus.PENDING, ApprovalStatus.IN_PROGRESS])
    ).all()
    
    pending_workflows = []
    
    for workflow in workflows:
        # Get current level approvers
        current_level = db.query(ApprovalLevel).filter(
            and_(
                ApprovalLevel.chain_id == workflow.chain_id,
                ApprovalLevel.level_number == workflow.current_level
            )
        ).first()
        
        if current_level and current_user.email in current_level.approver_emails:
            # Check if user hasn't already approved
            existing_action = db.query(ApprovalAction).filter(
                and_(
                    ApprovalAction.workflow_id == workflow.id,
                    ApprovalAction.approver_email == current_user.email,
                    ApprovalAction.level_number == workflow.current_level
                )
            ).first()
            
            if not existing_action:
                pending_workflows.append(workflow)
    
    return [_format_workflow_response(wf, db) for wf in pending_workflows]


@router.post("/workflows/{workflow_id}/approve", response_model=ApprovalActionResponse)
async def approve_workflow(
    workflow_id: str,
    action_data: ApprovalActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve an invoice at current approval level.
    """
    return await _process_approval_action(
        workflow_id=workflow_id,
        action_data=action_data,
        request=request,
        db=db,
        current_user=current_user
    )


@router.post("/workflows/{workflow_id}/reject", response_model=ApprovalActionResponse)
async def reject_workflow(
    workflow_id: str,
    action_data: ApprovalActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reject an invoice approval.
    """
    action_data.action = ApproverAction.REJECT
    return await _process_approval_action(
        workflow_id=workflow_id,
        action_data=action_data,
        request=request,
        db=db,
        current_user=current_user
    )


@router.post("/workflows/{workflow_id}/escalate", response_model=ApprovalActionResponse)
async def escalate_workflow(
    workflow_id: str,
    action_data: ApprovalActionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Escalate an invoice approval to higher authority.
    """
    action_data.action = ApproverAction.ESCALATE
    return await _process_approval_action(
        workflow_id=workflow_id,
        action_data=action_data,
        request=request,
        db=db,
        current_user=current_user
    )


@router.post("/workflows/{workflow_id}/esign")
async def trigger_esign(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger eSign workflow for high-value invoice.
    """
    workflow = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval workflow not found: {workflow_id}"
        )
    
    if not workflow.esign_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="eSign not required for this invoice"
        )
    
    if workflow.esign_request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="eSign already initiated for this workflow"
        )
    
    # Get invoice document
    invoice = db.query(InvoiceDocument).filter(
        InvoiceDocument.invoice_id == workflow.invoice_id
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {workflow.invoice_id}"
        )
    
    # Get all approvers who have approved
    approved_actions = db.query(ApprovalAction).filter(
        and_(
            ApprovalAction.workflow_id == workflow_id,
            ApprovalAction.action == ApproverAction.APPROVE
        )
    ).all()
    
    signers = [
        {
            "email": action.approver_email,
            "name": action.approver_email.split("@")[0].title(),
            "role": SignerRole.SIGNER
        }
        for action in approved_actions
    ]
    
    if not signers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approvers to sign - workflow not yet approved"
        )
    
    # Initialize Foxit eSign connector
    settings = get_settings()
    esign_connector = FoxitESignConnector(
        api_key=settings.foxit_esign_api_key,
        api_secret=settings.foxit_esign_api_secret,
        base_url=settings.foxit_esign_base_url
    )
    
    try:
        # Upload document
        document_id = await esign_connector.upload_document(
            file_path=invoice.document_path,
            document_name=f"Invoice_{workflow.invoice_id}_For_Signature.pdf"
        )
        
        # Create signature request
        signature_request = await esign_connector.create_signature_request(
            document_id=document_id,
            signers=signers,
            subject=f"Signature Required: Invoice {workflow.invoice_id}",
            message=f"Please sign this approved invoice (Amount: ${invoice.total_amount/100:.2f})",
            expires_in_days=7
        )
        
        # Update workflow with eSign request ID
        workflow.esign_request_id = signature_request["signature_request_id"]
        db.commit()
        
        return {
            "message": "eSign workflow initiated",
            "signature_request_id": signature_request["signature_request_id"],
            "signing_url": signature_request.get("signing_url")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate eSign: {str(e)}"
        )


@router.get("/workflows/{workflow_id}/audit-trail")
async def get_audit_trail(
    workflow_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete audit trail for approval workflow.
    """
    workflow = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval workflow not found: {workflow_id}"
        )
    
    # Get all actions
    actions = db.query(ApprovalAction).filter(
        ApprovalAction.workflow_id == workflow_id
    ).order_by(ApprovalAction.created_at).all()
    
    # Get all notifications
    notifications = db.query(ApprovalNotification).filter(
        ApprovalNotification.workflow_id == workflow_id
    ).order_by(ApprovalNotification.created_at).all()
    
    return {
        "workflow_id": workflow_id,
        "invoice_id": workflow.invoice_id,
        "chain_name": workflow.chain.name,
        "status": workflow.status.value,
        "created_at": workflow.created_at.isoformat(),
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
        "actions": [
            {
                "id": str(action.id),
                "level_number": action.level_number,
                "approver_email": action.approver_email,
                "action": action.action.value,
                "comment": action.comment,
                "created_at": action.created_at.isoformat(),
                "ip_address": action.ip_address
            }
            for action in actions
        ],
        "notifications": [
            {
                "id": str(notif.id),
                "recipient_email": notif.recipient_email,
                "notification_type": notif.notification_type,
                "delivered": notif.delivered,
                "created_at": notif.created_at.isoformat()
            }
            for notif in notifications
        ]
    }


# ============================================================================
# Helper Functions
# ============================================================================

async def _process_approval_action(
    workflow_id: str,
    action_data: ApprovalActionCreate,
    request: Request,
    db: Session,
    current_user: User
) -> ApprovalActionResponse:
    """
    Process approval action (approve, reject, escalate).
    """
    workflow = db.query(ApprovalWorkflow).filter(
        ApprovalWorkflow.id == workflow_id
    ).first()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval workflow not found: {workflow_id}"
        )
    
    # Check if workflow is still pending
    if workflow.status not in [ApprovalStatus.PENDING, ApprovalStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow is not pending approval (current status: {workflow.status.value})"
        )
    
    # Get current level
    current_level = db.query(ApprovalLevel).filter(
        and_(
            ApprovalLevel.chain_id == workflow.chain_id,
            ApprovalLevel.level_number == workflow.current_level
        )
    ).first()
    
    if not current_level:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval level {workflow.current_level} not found"
        )
    
    # Verify user is an approver at this level
    if current_user.email not in current_level.approver_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not an approver at this level"
        )
    
    # Check if user has already acted
    existing_action = db.query(ApprovalAction).filter(
        and_(
            ApprovalAction.workflow_id == workflow_id,
            ApprovalAction.approver_email == current_user.email,
            ApprovalAction.level_number == workflow.current_level
        )
    ).first()
    
    if existing_action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has already acted on this approval level"
        )
    
    # Create approval action
    approval_action = ApprovalAction(
        workflow_id=workflow_id,
        approver_id=str(current_user.id),
        approver_email=current_user.email,
        level_number=workflow.current_level,
        action=action_data.action,
        comment=action_data.comment,
        forwarded_to=action_data.forwarded_to,
        escalated_to=action_data.escalated_to,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(approval_action)
    
    # Update workflow status based on action
    if action_data.action == ApproverAction.REJECT:
        workflow.status = ApprovalStatus.REJECTED
        workflow.completed_at = datetime.utcnow()
        
    elif action_data.action == ApproverAction.ESCALATE:
        workflow.status = ApprovalStatus.ESCALATED
        workflow.escalated = True
        workflow.escalation_reason = EscalationReason.MANUAL_ESCALATION
        
    elif action_data.action == ApproverAction.APPROVE:
        workflow.status = ApprovalStatus.IN_PROGRESS
        
        # Check if level is complete
        level_approvals = db.query(ApprovalAction).filter(
            and_(
                ApprovalAction.workflow_id == workflow_id,
                ApprovalAction.level_number == workflow.current_level,
                ApprovalAction.action == ApproverAction.APPROVE
            )
        ).count()
        
        if level_approvals >= current_level.required_approvals:
            # Move to next level or complete
            next_level = db.query(ApprovalLevel).filter(
                and_(
                    ApprovalLevel.chain_id == workflow.chain_id,
                    ApprovalLevel.level_number == workflow.current_level + 1
                )
            ).first()
            
            if next_level:
                # Move to next level
                workflow.current_level += 1
                
                # Send notifications to next level approvers
                for email in next_level.approver_emails:
                    notification = ApprovalNotification(
                        workflow_id=workflow.id,
                        recipient_email=email,
                        notification_type="approval_request",
                        delivered=False
                    )
                    db.add(notification)
            else:
                # Workflow complete
                workflow.status = ApprovalStatus.APPROVED
                workflow.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(approval_action)
    
    return ApprovalActionResponse(
        id=str(approval_action.id),
        workflow_id=workflow_id,
        approver_email=approval_action.approver_email,
        level_number=approval_action.level_number,
        action=approval_action.action,
        comment=approval_action.comment,
        created_at=approval_action.created_at
    )


def _format_workflow_response(workflow: ApprovalWorkflow, db: Session) -> ApprovalWorkflowResponse:
    """
    Format approval workflow for API response.
    """
    actions = db.query(ApprovalAction).filter(
        ApprovalAction.workflow_id == workflow.id
    ).order_by(ApprovalAction.created_at).all()
    
    return ApprovalWorkflowResponse(
        id=str(workflow.id),
        invoice_id=workflow.invoice_id,
        chain_id=str(workflow.chain_id),
        chain_name=workflow.chain.name,
        status=workflow.status,
        current_level=workflow.current_level,
        esign_required=workflow.esign_required,
        esign_request_id=workflow.esign_request_id,
        created_at=workflow.created_at,
        completed_at=workflow.completed_at,
        expires_at=workflow.expires_at,
        is_expired=workflow.is_expired,
        time_remaining_hours=workflow.time_remaining_hours,
        escalated=workflow.escalated,
        escalation_reason=workflow.escalation_reason,
        approval_actions=[
            {
                "id": str(action.id),
                "level_number": action.level_number,
                "approver_email": action.approver_email,
                "action": action.action.value,
                "comment": action.comment,
                "created_at": action.created_at.isoformat()
            }
            for action in actions
        ]
    )
