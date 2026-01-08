"""
ERP Integration Database Models
Track ERP connections, sync history, and field mappings
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from ..database import Base


class ERPSystemType(str, enum.Enum):
    """ERP system types"""
    QUICKBOOKS = "quickbooks"
    XERO = "xero"
    SAP = "sap"
    SAGE = "sage"
    NETSUITE = "netsuite"
    ORACLE = "oracle"
    DYNAMICS = "dynamics"


class ERPConnectionStatus(str, enum.Enum):
    """Connection status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class SyncStatus(str, enum.Enum):
    """Sync operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ERPEntityType(str, enum.Enum):
    """Entity types for sync"""
    VENDOR = "vendor"
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    PAYMENT = "payment"
    ACCOUNT = "account"
    TAX_CODE = "tax_code"


class ERPConnection(Base):
    """
    ERP system connection configuration
    
    Stores credentials and settings for connecting to external ERP systems
    """
    __tablename__ = "erp_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Connection details
    name = Column(String(255), nullable=False)  # User-friendly connection name
    system_type = Column(SQLEnum(ERPSystemType), nullable=False, index=True)
    status = Column(SQLEnum(ERPConnectionStatus), default=ERPConnectionStatus.PENDING, index=True)
    
    # Authentication
    credentials = Column(JSON, nullable=False)  # Encrypted credentials (client_id, secret, tokens, etc.)
    
    # Connection metadata
    tenant_id = Column(String(255))  # For multi-tenant ERPs (Xero, QuickBooks)
    company_db = Column(String(255))  # For SAP
    api_url = Column(String(512))  # Custom API URL if needed
    
    # Status tracking
    last_connected_at = Column(DateTime)
    last_sync_at = Column(DateTime)
    connection_error = Column(Text)
    
    # Settings
    auto_sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=60)  # How often to sync
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))  # User who created connection
    
    # Relationships
    sync_logs = relationship("ERPSyncLog", back_populates="connection", cascade="all, delete-orphan")
    field_mappings = relationship("ERPFieldMapping", back_populates="connection", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_erp_connections_status', 'status'),
        Index('idx_erp_connections_system_type', 'system_type'),
        Index('idx_erp_connections_last_sync', 'last_sync_at'),
    )
    
    def __repr__(self):
        return f"<ERPConnection {self.name} ({self.system_type})>"


class ERPSyncLog(Base):
    """
    ERP synchronization operation log
    
    Tracks history of all sync operations for audit and troubleshooting
    """
    __tablename__ = "erp_sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Connection reference
    connection_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Sync details
    entity_type = Column(SQLEnum(ERPEntityType), nullable=False, index=True)
    sync_direction = Column(String(50), nullable=False)  # 'import' or 'export'
    status = Column(SQLEnum(SyncStatus), nullable=False, index=True)
    
    # Operation metadata
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # Results
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Error details
    errors = Column(JSON)  # List of error messages
    error_message = Column(Text)  # Primary error message
    
    # Sync parameters
    sync_params = Column(JSON)  # Parameters used for sync (filters, limits, etc.)
    
    # User context
    triggered_by = Column(String(255))  # 'system', 'user:john@example.com', etc.
    
    # Relationship
    connection = relationship("ERPConnection", back_populates="sync_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_erp_sync_logs_connection', 'connection_id'),
        Index('idx_erp_sync_logs_entity_type', 'entity_type'),
        Index('idx_erp_sync_logs_status', 'status'),
        Index('idx_erp_sync_logs_started_at', 'started_at'),
    )
    
    def __repr__(self):
        return f"<ERPSyncLog {self.entity_type} {self.status}>"


class ERPFieldMapping(Base):
    """
    Field mapping configuration
    
    Maps SmartAP fields to ERP system fields for data transformation
    """
    __tablename__ = "erp_field_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Connection reference
    connection_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Entity mapping
    entity_type = Column(SQLEnum(ERPEntityType), nullable=False, index=True)
    
    # Field mapping
    smartap_field = Column(String(255), nullable=False)  # SmartAP field name
    erp_field = Column(String(255), nullable=False)  # ERP field name/path
    
    # Transformation
    transformation_rule = Column(Text)  # Python expression or jq filter
    default_value = Column(String(512))  # Default value if source is empty
    
    # Validation
    is_required = Column(Boolean, default=False)
    validation_regex = Column(String(512))  # Regex pattern for validation
    
    # Metadata
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    connection = relationship("ERPConnection", back_populates="field_mappings")
    
    # Indexes
    __table_args__ = (
        Index('idx_erp_field_mappings_connection', 'connection_id'),
        Index('idx_erp_field_mappings_entity', 'entity_type'),
        Index('idx_erp_field_mappings_smartap_field', 'smartap_field'),
    )
    
    def __repr__(self):
        return f"<ERPFieldMapping {self.smartap_field} -> {self.erp_field}>"


class ERPVendorMapping(Base):
    """
    Vendor ID mapping between SmartAP and ERP systems
    
    Tracks vendor relationships across systems for accurate data sync
    """
    __tablename__ = "erp_vendor_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Connection reference
    connection_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Vendor references
    smartap_vendor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    erp_vendor_id = Column(String(255), nullable=False, index=True)  # External vendor ID
    erp_vendor_name = Column(String(255))
    
    # Sync metadata
    first_synced_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_synced_at = Column(DateTime)
    sync_count = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_erp_vendor_mappings_connection', 'connection_id'),
        Index('idx_erp_vendor_mappings_smartap_vendor', 'smartap_vendor_id'),
        Index('idx_erp_vendor_mappings_erp_vendor', 'erp_vendor_id'),
        # Unique constraint to prevent duplicates
        Index('idx_erp_vendor_mappings_unique', 'connection_id', 'smartap_vendor_id', unique=True),
    )
    
    def __repr__(self):
        return f"<ERPVendorMapping {self.smartap_vendor_id} -> {self.erp_vendor_id}>"


class ERPInvoiceMapping(Base):
    """
    Invoice mapping between SmartAP and ERP systems
    
    Tracks exported invoices for status sync and audit trail
    """
    __tablename__ = "erp_invoice_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Connection reference
    connection_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Invoice references
    smartap_invoice_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    erp_invoice_id = Column(String(255), nullable=False, index=True)  # External invoice ID
    erp_invoice_number = Column(String(255))
    
    # Export details
    exported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    exported_by = Column(String(255))  # User who triggered export
    
    # Payment sync
    payment_status = Column(String(50))  # 'unpaid', 'partial', 'paid'
    payment_synced_at = Column(DateTime)
    payment_amount = Column(Integer)  # Amount in cents
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_erp_invoice_mappings_connection', 'connection_id'),
        Index('idx_erp_invoice_mappings_smartap_invoice', 'smartap_invoice_id'),
        Index('idx_erp_invoice_mappings_erp_invoice', 'erp_invoice_id'),
        Index('idx_erp_invoice_mappings_exported_at', 'exported_at'),
        # Unique constraint
        Index('idx_erp_invoice_mappings_unique', 'connection_id', 'smartap_invoice_id', unique=True),
    )
    
    def __repr__(self):
        return f"<ERPInvoiceMapping {self.smartap_invoice_id} -> {self.erp_invoice_id}>"
