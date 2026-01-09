"""
Approval Workflow Database Models
Phase 4.4: Multi-Level Approval Workflows with eSign Integration

SQLAlchemy models for approval chains, thresholds, escalation, and archival.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum as SQLEnum, Integer, Boolean, Text
from sqlalchemy.orm import relationship
from ..db.models import Base
import enum
import uuid


class ApprovalStatus(str, enum.Enum):
    """Approval workflow status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApproverAction(str, enum.Enum):
    """Approver action types"""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_INFO = "request_info"
    FORWARD = "forward"
    ESCALATE = "escalate"


class EscalationReason(str, enum.Enum):
    """Escalation reasons"""
    TIMEOUT = "timeout"
    AMOUNT_THRESHOLD = "amount_threshold"
    MANUAL = "manual"
    RISK_SCORE = "risk_score"
    MISSING_INFO = "missing_info"


class ArchivalStatus(str, enum.Enum):
    """Document archival status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ARCHIVED = "archived"
    FAILED = "failed"
    SEALED = "sealed"


class ApprovalChain(Base):
    """
    Approval chain configuration for organization.
    
    Defines multi-level approval rules based on amount thresholds.
    """
    __tablename__ = "approval_chains"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Configuration
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Threshold rules
    min_amount = Column(Integer, nullable=False, default=0)  # In cents
    max_amount = Column(Integer, nullable=True)  # In cents, NULL = no max
    
    # Approval requirements
    required_approvers = Column(Integer, nullable=False, default=1)
    sequential_approval = Column(Boolean, default=True, nullable=False)
    
    # eSign integration
    require_esign = Column(Boolean, default=False, nullable=False)
    esign_threshold = Column(Integer, nullable=True)  # Amount requiring eSign (cents)
    
    # Timing
    approval_timeout_hours = Column(Integer, nullable=False, default=72)  # 3 days
    reminder_frequency_hours = Column(Integer, nullable=False, default=24)
    
    # Escalation rules
    auto_escalate_on_timeout = Column(Boolean, default=True, nullable=False)
    escalation_email = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=False)
    
    # Relationships
    levels = relationship("ApprovalLevel", back_populates="chain", cascade="all, delete-orphan", order_by="ApprovalLevel.level_number")
    workflows = relationship("ApprovalWorkflow", back_populates="chain")
    
    def __repr__(self):
        return f"<ApprovalChain {self.name}: ${self.min_amount/100}-${self.max_amount/100 if self.max_amount else '∞'}>"


class ApprovalLevel(Base):
    """
    Individual approval level within a chain.
    
    Defines approvers for each level (e.g., Manager, Director, CFO).
    """
    __tablename__ = "approval_levels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Chain reference
    chain_id = Column(String, ForeignKey("approval_chains.id"), nullable=False, index=True)
    
    # Level configuration
    level_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    level_name = Column(String, nullable=False)  # "Manager", "Director", "CFO"
    
    # Approvers (JSON array of user IDs or emails)
    approver_ids = Column(JSON, nullable=False, default=list)
    approver_emails = Column(JSON, nullable=False, default=list)
    
    # Requirements
    required_approvals = Column(Integer, nullable=False, default=1)  # How many from this level
    
    # Timing
    timeout_hours = Column(Integer, nullable=True)  # Override chain timeout
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    chain = relationship("ApprovalChain", back_populates="levels")
    
    def __repr__(self):
        return f"<ApprovalLevel {self.level_number}: {self.level_name}>"


class ApprovalWorkflow(Base):
    """
    Active approval workflow for an invoice.
    
    Tracks the progression through approval chain.
    """
    __tablename__ = "approval_workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Invoice reference (uses document_id which is the string UUID)
    invoice_id = Column(String, ForeignKey("invoices.document_id"), nullable=False, index=True, unique=True)
    invoice_number = Column(String, nullable=False, index=True)
    invoice_amount = Column(Integer, nullable=False)  # In cents
    vendor_name = Column(String, nullable=False)
    
    # Chain reference
    chain_id = Column(String, ForeignKey("approval_chains.id"), nullable=False, index=True)
    
    # Current state
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False, index=True)
    current_level = Column(Integer, nullable=False, default=1)
    
    # eSign integration
    esign_required = Column(Boolean, default=False, nullable=False)
    esign_request_id = Column(String, ForeignKey("esign_requests.id"), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Final outcome
    final_action = Column(SQLEnum(ApproverAction), nullable=True)
    final_approver_id = Column(String, nullable=True)
    final_comment = Column(Text, nullable=True)
    
    # Escalation tracking
    escalated = Column(Boolean, default=False, nullable=False)
    escalation_reason = Column(SQLEnum(EscalationReason), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    escalated_to = Column(String, nullable=True)
    
    # Metadata
    initiated_by = Column(String, nullable=False)
    
    # Relationships
    chain = relationship("ApprovalChain", back_populates="workflows")
    approvals = relationship("ApprovalAction", back_populates="workflow", cascade="all, delete-orphan", order_by="ApprovalAction.action_at")
    esign_request = relationship("ESignRequest", foreign_keys=[esign_request_id])
    
    def __repr__(self):
        return f"<ApprovalWorkflow {self.invoice_number}: {self.status}>"
    
    @property
    def is_expired(self) -> bool:
        """Check if workflow has expired"""
        return datetime.utcnow() > self.expires_at and self.status in [ApprovalStatus.PENDING, ApprovalStatus.IN_PROGRESS]
    
    @property
    def time_remaining_hours(self) -> float:
        """Calculate hours remaining before expiration"""
        if self.expires_at:
            delta = self.expires_at - datetime.utcnow()
            return max(0, delta.total_seconds() / 3600)
        return 0


class ApprovalAction(Base):
    """
    Individual approval or rejection action.
    
    Tracks each approver's decision and comments.
    """
    __tablename__ = "approval_actions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Workflow reference
    workflow_id = Column(String, ForeignKey("approval_workflows.id"), nullable=False, index=True)
    
    # Approver information
    approver_id = Column(String, nullable=False, index=True)
    approver_email = Column(String, nullable=False)
    approver_name = Column(String, nullable=False)
    
    # Level information
    level_number = Column(Integer, nullable=False)
    level_name = Column(String, nullable=False)
    
    # Action details
    action = Column(SQLEnum(ApproverAction), nullable=False, index=True)
    comment = Column(Text, nullable=True)
    
    # Additional context
    forwarded_to = Column(String, nullable=True)  # If action is FORWARD
    escalated_to = Column(String, nullable=True)  # If action is ESCALATE
    
    # Audit information
    action_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # eSign integration
    signature_id = Column(String, nullable=True)  # Link to eSign signature
    
    # Relationships
    workflow = relationship("ApprovalWorkflow", back_populates="approvals")
    
    def __repr__(self):
        return f"<ApprovalAction {self.approver_name}: {self.action}>"


class ApprovalNotification(Base):
    """
    Approval notification tracking.
    
    Tracks emails and reminders sent to approvers.
    """
    __tablename__ = "approval_notifications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Workflow reference
    workflow_id = Column(String, ForeignKey("approval_workflows.id"), nullable=False, index=True)
    
    # Recipient
    recipient_email = Column(String, nullable=False, index=True)
    recipient_name = Column(String, nullable=False)
    
    # Notification details
    notification_type = Column(String, nullable=False, index=True)  # request, reminder, escalation, completion
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Delivery tracking
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    opened = Column(Boolean, default=False, nullable=False)
    opened_at = Column(DateTime, nullable=True)
    clicked = Column(Boolean, default=False, nullable=False)
    clicked_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<ApprovalNotification {self.notification_type} to {self.recipient_email}>"


class ArchivedDocument(Base):
    """
    Archived invoice document with tamper-proof seal.
    
    Permanent, immutable storage of approved invoices.
    """
    __tablename__ = "archived_documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Invoice reference (uses document_id which is the string UUID)
    invoice_id = Column(String, ForeignKey("invoices.document_id"), nullable=False, index=True, unique=True)
    invoice_number = Column(String, nullable=False, index=True)
    invoice_amount = Column(Integer, nullable=False)
    vendor_name = Column(String, nullable=False)
    
    # Document information
    original_document_path = Column(String, nullable=False)
    archived_document_path = Column(String, nullable=False, unique=True)
    document_hash = Column(String, nullable=False, unique=True)  # SHA256 hash
    
    # Archival process
    status = Column(SQLEnum(ArchivalStatus), default=ArchivalStatus.PENDING, nullable=False, index=True)
    
    # PDF operations performed
    flattened = Column(Boolean, default=False, nullable=False)
    audit_page_added = Column(Boolean, default=False, nullable=False)
    pdfa_converted = Column(Boolean, default=False, nullable=False)
    tamper_sealed = Column(Boolean, default=False, nullable=False)
    seal_verification = Column(JSON, nullable=True)
    
    # Metadata
    file_size = Column(Integer, nullable=False)
    page_count = Column(Integer, nullable=False)
    pdf_version = Column(String, nullable=True)
    pdfa_version = Column(String, nullable=True)
    
    # Timestamps
    archived_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sealed_at = Column(DateTime, nullable=True)
    
    # Retention policy
    retention_years = Column(Integer, nullable=False, default=7)
    retention_expires_at = Column(DateTime, nullable=False)
    can_delete_after = Column(DateTime, nullable=False)
    
    # Approval workflow reference
    workflow_id = Column(String, ForeignKey("approval_workflows.id"), nullable=True, index=True)
    
    # Audit data embedded in document
    audit_data = Column(JSON, nullable=False)
    
    # Access tracking
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    last_accessed_by = Column(String, nullable=True)
    
    # Archival metadata
    archived_by = Column(String, nullable=False)
    archival_notes = Column(Text, nullable=True)
    
    # Relationships
    access_logs = relationship("DocumentAccessLog", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ArchivedDocument {self.invoice_number}: {self.status}>"
    
    @property
    def is_retention_expired(self) -> bool:
        """Check if retention period has expired"""
        return datetime.utcnow() > self.retention_expires_at
    
    @property
    def can_be_deleted(self) -> bool:
        """Check if document can be deleted (past can_delete_after date)"""
        return datetime.utcnow() > self.can_delete_after


class DocumentAccessLog(Base):
    """
    Access log for archived documents.
    
    Tracks who accessed archived documents and when.
    """
    __tablename__ = "document_access_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Document reference
    document_id = Column(String, ForeignKey("archived_documents.id"), nullable=False, index=True)
    
    # Access details
    accessed_by = Column(String, nullable=False, index=True)
    access_type = Column(String, nullable=False)  # view, download, print
    accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Audit information
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    
    # Relationships
    document = relationship("ArchivedDocument", back_populates="access_logs")
    
    def __repr__(self):
        return f"<DocumentAccessLog {self.access_type} by {self.accessed_by}>"
