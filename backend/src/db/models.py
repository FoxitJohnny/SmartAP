"""
SmartAP SQLAlchemy ORM Models

Database models for all entities.
"""

from sqlalchemy import (
    String, Integer, Float, Boolean, Date, DateTime, Text, Numeric,
    ForeignKey, Enum as SQLEnum, JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

# Import enums from Pydantic models
from ..models.invoice import InvoiceStatus
from ..models.purchase_order import POStatus
from ..models.vendor import VendorStatus, FraudFlagType
from ..models.matching import MatchType, DiscrepancyType, DiscrepancySeverity
from ..models.risk import RiskLevel, RiskFlagType, RecommendedAction


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class InvoiceDB(Base):
    """Invoice database model."""
    __tablename__ = "invoices"
    
    # Add indexes for performance optimization
    __table_args__ = (
        {"comment": "Invoice extraction results with performance indexes"}
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiers with indexes
    document_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    
    # Status with index for filtering
    status: Mapped[InvoiceStatus] = mapped_column(SQLEnum(InvoiceStatus), index=True)
    
    # Invoice data (stored as JSON)
    invoice_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Confidence scores
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    requires_review: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    extraction_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    matching_results: Mapped[List["MatchingResultDB"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    risk_assessments: Mapped[List["RiskAssessmentDB"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")


class PurchaseOrderDB(Base):
    """Purchase Order database model."""
    __tablename__ = "purchase_orders"
    
    # Add composite indexes for common queries
    __table_args__ = (
        {"comment": "Purchase orders with composite indexes for vendor+status queries"}
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiers with indexes
    po_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    vendor_id: Mapped[str] = mapped_column(String(100), ForeignKey("vendors.vendor_id", ondelete="CASCADE"), index=True)
    
    # Dates
    created_date: Mapped[date] = mapped_column(Date)
    expected_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Status
    status: Mapped[POStatus] = mapped_column(SQLEnum(POStatus), index=True)
    
    # Amounts
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    
    # Additional info
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vendor: Mapped["VendorDB"] = relationship(back_populates="purchase_orders")
    line_items: Mapped[List["POLineItemDB"]] = relationship(back_populates="purchase_order", cascade="all, delete-orphan")
    matching_results: Mapped[List["MatchingResultDB"]] = relationship(back_populates="purchase_order")


class POLineItemDB(Base):
    """PO Line Item database model."""
    __tablename__ = "po_line_items"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    po_id: Mapped[int] = mapped_column(Integer, ForeignKey("purchase_orders.id"), index=True)
    
    # Line item data
    line_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Float)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    received_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Relationship back to purchase order
    purchase_order: Mapped["PurchaseOrderDB"] = relationship(back_populates="line_items")


class VendorDB(Base):
    """Vendor database model."""
    __tablename__ = "vendors"
    
    # Add indexes for performance
    __table_args__ = (
        {"comment": "Vendor master data with performance indexes"}
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiers with indexes
    vendor_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), index=True)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Identifiers
    vendor_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    vendor_name: Mapped[str] = mapped_column(String(255), index=True)
    
    # Contact
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="US")
    
    # Tax & Banking
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Status
    status: Mapped[VendorStatus] = mapped_column(SQLEnum(VendorStatus), default=VendorStatus.ACTIVE)
    payment_terms: Mapped[str] = mapped_column(String(100), default="Net 30")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Risk profile (stored as JSON)
    risk_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Metadata
    onboarded_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    purchase_orders: Mapped[List["PurchaseOrderDB"]] = relationship(back_populates="vendor")
    payment_history: Mapped[List["PaymentRecordDB"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
    fraud_flags: Mapped[List["FraudFlagDB"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")


class PaymentRecordDB(Base):
    """Payment Record database model."""
    __tablename__ = "payment_records"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    vendor_id: Mapped[str] = mapped_column(String(100), ForeignKey("vendors.vendor_id"), index=True)
    
    # Payment data
    payment_id: Mapped[str] = mapped_column(String(100), unique=True)
    invoice_number: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    payment_date: Mapped[date] = mapped_column(Date)
    days_to_pay: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationship
    vendor: Mapped["VendorDB"] = relationship(back_populates="payment_history")


class FraudFlagDB(Base):
    """Fraud Flag database model."""
    __tablename__ = "fraud_flags"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    vendor_id: Mapped[str] = mapped_column(String(100), ForeignKey("vendors.vendor_id"), index=True)
    
    # Flag data
    flag_id: Mapped[str] = mapped_column(String(100), unique=True)
    flag_type: Mapped[FraudFlagType] = mapped_column(SQLEnum(FraudFlagType))
    severity: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Resolution
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    flagged_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Relationship
    vendor: Mapped["VendorDB"] = relationship(back_populates="fraud_flags")


class MatchingResultDB(Base):
    """Matching Result database model."""
    __tablename__ = "matching_results"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign keys
    invoice_id: Mapped[str] = mapped_column(String(100), ForeignKey("invoices.document_id"), index=True)
    po_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("purchase_orders.id"), nullable=True, index=True)
    
    # Matching data
    matching_id: Mapped[str] = mapped_column(String(100), unique=True)
    match_type: Mapped[MatchType] = mapped_column(SQLEnum(MatchType))
    match_score: Mapped[float] = mapped_column(Float)
    matched: Mapped[bool] = mapped_column(Boolean)
    
    # Match scores
    vendor_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    amount_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    date_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    line_items_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Discrepancies (stored as JSON)
    discrepancies: Mapped[list] = mapped_column(JSON, default=list)
    has_discrepancies: Mapped[bool] = mapped_column(Boolean, default=False)
    critical_discrepancies: Mapped[int] = mapped_column(Integer, default=0)
    
    # Approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    matched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    matched_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships
    invoice: Mapped["InvoiceDB"] = relationship(back_populates="matching_results")
    purchase_order: Mapped[Optional["PurchaseOrderDB"]] = relationship(back_populates="matching_results")


class RiskAssessmentDB(Base):
    """Risk Assessment database model."""
    __tablename__ = "risk_assessments"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key
    invoice_id: Mapped[str] = mapped_column(String(100), ForeignKey("invoices.document_id"), index=True)
    
    # Assessment data
    assessment_id: Mapped[str] = mapped_column(String(100), unique=True)
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel))
    risk_score: Mapped[float] = mapped_column(Float)
    
    # Component scores
    duplicate_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    vendor_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    price_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    amount_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    pattern_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Flags (stored as JSON)
    risk_flags: Mapped[list] = mapped_column(JSON, default=list)
    critical_flags: Mapped[int] = mapped_column(Integer, default=0)
    high_flags: Mapped[int] = mapped_column(Integer, default=0)
    
    # Duplicate info (stored as JSON)
    duplicate_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Recommendation
    recommended_action: Mapped[RecommendedAction] = mapped_column(SQLEnum(RecommendedAction))
    action_reason: Mapped[str] = mapped_column(Text)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean)
    
    # Metadata
    assessed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    assessed_by: Mapped[str] = mapped_column(String(100), default="system")
    assessment_version: Mapped[str] = mapped_column(String(20), default="1.0")
    
    # Relationship
    invoice: Mapped["InvoiceDB"] = relationship(back_populates="risk_assessments")


class UserDB(Base):
    """User database model for authentication and authorization."""
    __tablename__ = "users"
    
    __table_args__ = (
        {"comment": "User accounts for authentication"}
    )
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # User identifiers
    user_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Profile
    full_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255))
    
    # Role and permissions
    role: Mapped[str] = mapped_column(String(50), default="viewer")
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RefreshTokenDB(Base):
    """Refresh token database model for JWT token management."""
    __tablename__ = "refresh_tokens"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Token data
    token: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey("users.user_id"), index=True)
    
    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    
    # Status
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
