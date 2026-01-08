"""
eSign Database Models
Phase 4.2: Electronic Signature Tracking

SQLAlchemy models for tracking eSign requests, signers, and audit trail.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.orm import relationship
from ..db.base import Base
import enum


class ESignStatus(str, enum.Enum):
    """eSign request status"""
    PENDING = "pending_signature"
    PARTIALLY_SIGNED = "partially_signed"
    FULLY_SIGNED = "fully_signed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignerStatus(str, enum.Enum):
    """Individual signer status"""
    PENDING = "pending"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"


class ESignRequest(Base):
    """
    Electronic signature request for invoice approval.
    
    Tracks the overall eSign request lifecycle and links to invoice.
    """
    __tablename__ = "esign_requests"
    
    id = Column(String, primary_key=True)
    
    # Foxit eSign integration
    foxit_request_id = Column(String, unique=True, index=True, nullable=False)
    
    # Invoice reference
    invoice_id = Column(String, ForeignKey("invoice_documents.id"), nullable=False, index=True)
    invoice_number = Column(String, nullable=False)
    invoice_amount = Column(Float, nullable=False)
    vendor_name = Column(String, nullable=False)
    
    # Status tracking
    status = Column(SQLEnum(ESignStatus), default=ESignStatus.PENDING, nullable=False, index=True)
    
    # Document paths
    original_document_path = Column(String, nullable=False)
    signed_document_path = Column(String, nullable=True)
    signed_document_url = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Metadata
    title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    
    # Settings
    sequential_signing = Column(Integer, default=1, nullable=False)  # Boolean as int
    reminder_enabled = Column(Integer, default=1, nullable=False)
    
    # Webhook data
    webhook_events = Column(JSON, default=list, nullable=False)
    
    # Relationships
    signers = relationship("ESignSigner", back_populates="request", cascade="all, delete-orphan")
    audit_logs = relationship("ESignAuditLog", back_populates="request", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ESignRequest {self.foxit_request_id} for Invoice {self.invoice_number}>"


class ESignSigner(Base):
    """
    Individual signer for an eSign request.
    
    Tracks each approver's signing status and actions.
    """
    __tablename__ = "esign_signers"
    
    id = Column(String, primary_key=True)
    
    # Request reference
    request_id = Column(String, ForeignKey("esign_requests.id"), nullable=False, index=True)
    
    # Signer information
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)  # manager, senior_manager, cfo, controller
    order = Column(Integer, nullable=False)  # Signing order (1, 2, 3...)
    
    # Status
    status = Column(SQLEnum(SignerStatus), default=SignerStatus.PENDING, nullable=False, index=True)
    
    # Action tracking
    signed_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    decline_reason = Column(String, nullable=True)
    
    # Foxit data
    signer_url = Column(String, nullable=True)  # Unique signing URL
    reminder_count = Column(Integer, default=0, nullable=False)
    last_reminder_at = Column(DateTime, nullable=True)
    
    # IP and device tracking
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Relationships
    request = relationship("ESignRequest", back_populates="signers")
    
    def __repr__(self):
        return f"<ESignSigner {self.email} ({self.role})>"


class ESignAuditLog(Base):
    """
    Audit trail for eSign activities.
    
    Logs all actions, state changes, and events for compliance.
    """
    __tablename__ = "esign_audit_logs"
    
    id = Column(String, primary_key=True)
    
    # Request reference
    request_id = Column(String, ForeignKey("esign_requests.id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String, nullable=False, index=True)  # created, signed, declined, completed, expired, reminder_sent, etc.
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Actor (who performed the action)
    actor_email = Column(String, nullable=True)
    actor_name = Column(String, nullable=True)
    actor_role = Column(String, nullable=True)
    
    # Event data
    event_data = Column(JSON, default=dict, nullable=False)
    
    # System tracking
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Relationships
    request = relationship("ESignRequest", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<ESignAuditLog {self.event_type} at {self.event_timestamp}>"


class ESignWebhook(Base):
    """
    Webhook events received from Foxit eSign.
    
    Stores raw webhook payloads for debugging and replay.
    """
    __tablename__ = "esign_webhooks"
    
    id = Column(String, primary_key=True)
    
    # Foxit request reference
    foxit_request_id = Column(String, index=True, nullable=False)
    
    # Webhook details
    event_type = Column(String, nullable=False, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Payload
    payload = Column(JSON, nullable=False)
    
    # Processing status
    processed = Column(Integer, default=0, nullable=False)  # Boolean as int
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(String, nullable=True)
    
    # Security
    signature_valid = Column(Integer, default=0, nullable=False)
    
    def __repr__(self):
        return f"<ESignWebhook {self.event_type} for {self.foxit_request_id}>"
