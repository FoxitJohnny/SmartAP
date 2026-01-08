# SmartAP Data Model

**Section 5 of Architecture Documentation**

---

## Table of Contents

1. [Entity Relationship Diagram](#entity-relationship-diagram)
2. [Core Tables](#core-tables)
3. [Relationship Tables](#relationship-tables)
4. [Audit & System Tables](#audit--system-tables)
5. [Indexes & Constraints](#indexes--constraints)
6. [Migration Strategy](#migration-strategy)

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SmartAP Data Model                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│      users       │       │   departments    │       │      roles       │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │──┐    │ id (PK)          │    ┌──│ id (PK)          │
│ email            │  │    │ name             │    │  │ name             │
│ hashed_password  │  │    │ code             │    │  │ permissions      │
│ full_name        │  │    │ manager_id (FK)  │────┘  │ created_at       │
│ role_id (FK)     │──┘    │ created_at       │       └──────────────────┘
│ department_id(FK)│───────│ updated_at       │
│ is_active        │       └──────────────────┘
│ created_at       │
│ updated_at       │
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    approvals     │       │     invoices     │       │     vendors      │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │◄──────│ id (PK)          │
│ invoice_id (FK)  │──────►│ invoice_number   │       │ name             │
│ approver_id (FK) │       │ vendor_id (FK)   │───────│ tax_id           │
│ level            │       │ po_id (FK)       │──┐    │ address          │
│ status           │       │ status           │  │    │ email            │
│ decision         │       │ invoice_date     │  │    │ phone            │
│ comment          │       │ due_date         │  │    │ payment_terms    │
│ decided_at       │       │ subtotal         │  │    │ bank_account     │
│ created_at       │       │ tax_amount       │  │    │ risk_score       │
└──────────────────┘       │ total            │  │    │ is_approved      │
         ▲                 │ currency         │  │    │ created_at       │
         │                 │ pdf_path         │  │    │ updated_at       │
         │ 1:N             │ extracted_data   │  │    └──────────────────┘
         │                 │ confidence_score │  │
┌────────┴─────────┐       │ match_result     │  │    ┌──────────────────┐
│ approval_rules   │       │ fraud_result     │  │    │ purchase_orders  │
├──────────────────┤       │ created_by (FK)  │  │    ├──────────────────┤
│ id (PK)          │       │ created_at       │  │    │ id (PK)          │
│ name             │       │ updated_at       │  │    │ po_number        │
│ condition_type   │       └────────┬─────────┘  └───►│ vendor_id (FK)   │
│ condition_value  │                │                 │ status           │
│ approver_id (FK) │                │ 1:N             │ order_date       │
│ priority         │                ▼                 │ expected_date    │
│ is_active        │       ┌──────────────────┐       │ total            │
│ created_at       │       │   line_items     │       │ currency         │
└──────────────────┘       ├──────────────────┤       │ created_by (FK)  │
                           │ id (PK)          │       │ created_at       │
                           │ invoice_id (FK)  │───────│ updated_at       │
                           │ po_line_id (FK)  │──┐    └────────┬─────────┘
                           │ description      │  │             │
                           │ quantity         │  │             │ 1:N
                           │ unit_price       │  │             ▼
                           │ amount           │  │    ┌──────────────────┐
                           │ category         │  │    │  po_line_items   │
                           │ created_at       │  │    ├──────────────────┤
                           └──────────────────┘  │    │ id (PK)          │
                                                 └───►│ po_id (FK)       │
                                                      │ description      │
┌──────────────────┐       ┌──────────────────┐       │ quantity         │
│   audit_logs     │       │   attachments    │       │ unit_price       │
├──────────────────┤       ├──────────────────┤       │ amount           │
│ id (PK)          │       │ id (PK)          │       │ received_qty     │
│ entity_type      │       │ invoice_id (FK)  │       │ created_at       │
│ entity_id        │       │ file_name        │       └──────────────────┘
│ action           │       │ file_path        │
│ old_values       │       │ file_type        │       ┌──────────────────┐
│ new_values       │       │ file_size        │       │   webhooks       │
│ user_id (FK)     │       │ uploaded_by (FK) │       ├──────────────────┤
│ ip_address       │       │ created_at       │       │ id (PK)          │
│ user_agent       │       └──────────────────┘       │ url              │
│ created_at       │                                  │ events           │
└──────────────────┘       ┌──────────────────┐       │ secret           │
                           │  notifications   │       │ is_active        │
                           ├──────────────────┤       │ created_at       │
                           │ id (PK)          │       └──────────────────┘
                           │ user_id (FK)     │
                           │ type             │       ┌──────────────────┐
                           │ title            │       │ erp_connections  │
                           │ message          │       ├──────────────────┤
                           │ data             │       │ id (PK)          │
                           │ is_read          │       │ provider         │
                           │ created_at       │       │ credentials      │
                           └──────────────────┘       │ settings         │
                                                      │ last_sync        │
                                                      │ is_active        │
                                                      │ created_at       │
                                                      └──────────────────┘
```

---

## Core Tables

### Users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role_id INTEGER REFERENCES roles(id),
    department_id INTEGER REFERENCES departments(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SQLAlchemy Model
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    
    # Relationships
    role: Mapped["Role"] = relationship(back_populates="users")
    department: Mapped[Optional["Department"]] = relationship(back_populates="users")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="approver")
```

### Invoices

```sql
CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(100) NOT NULL,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    po_id INTEGER REFERENCES purchase_orders(id),
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    invoice_date DATE,
    due_date DATE,
    subtotal DECIMAL(15, 2),
    tax_amount DECIMAL(15, 2),
    total DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    pdf_path VARCHAR(500) NOT NULL,
    extracted_data JSONB,
    confidence_score DECIMAL(5, 4),
    match_result JSONB,
    fraud_result JSONB,
    payment_terms VARCHAR(100),
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_invoice_vendor UNIQUE (invoice_number, vendor_id)
);

-- Status enum values
-- 'uploaded', 'extracting', 'extracted', 'validating', 'validated',
-- 'matching', 'matched', 'fraud_checking', 'pending_approval',
-- 'approved', 'rejected', 'paid', 'archived', 'failed'

-- SQLAlchemy Model
class Invoice(Base):
    __tablename__ = "invoices"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(100), index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), index=True)
    po_id: Mapped[Optional[int]] = mapped_column(ForeignKey("purchase_orders.id"))
    status: Mapped[str] = mapped_column(String(50), default="uploaded", index=True)
    invoice_date: Mapped[Optional[date]] = mapped_column()
    due_date: Mapped[Optional[date]] = mapped_column()
    subtotal: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    tax_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    pdf_path: Mapped[str] = mapped_column(String(500))
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))
    match_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    fraud_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    
    # Relationships
    vendor: Mapped["Vendor"] = relationship(back_populates="invoices")
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship(back_populates="invoices")
    line_items: Mapped[list["LineItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    creator: Mapped[Optional["User"]] = relationship()
```

### Vendors

```sql
CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tax_id VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    email VARCHAR(255),
    phone VARCHAR(50),
    payment_terms VARCHAR(100) DEFAULT 'Net 30',
    bank_name VARCHAR(255),
    bank_account VARCHAR(100),
    bank_routing VARCHAR(50),
    risk_score DECIMAL(3, 2) DEFAULT 0.0,
    is_approved BOOLEAN DEFAULT FALSE,
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_vendor_tax_id UNIQUE (tax_id)
);

-- SQLAlchemy Model
class Vendor(Base):
    __tablename__ = "vendors"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), default="USA")
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    payment_terms: Mapped[str] = mapped_column(String(100), default="Net 30")
    bank_name: Mapped[Optional[str]] = mapped_column(String(255))
    bank_account: Mapped[Optional[str]] = mapped_column(String(100))
    bank_routing: Mapped[Optional[str]] = mapped_column(String(50))
    risk_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0.0)
    is_approved: Mapped[bool] = mapped_column(default=False)
    approved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())
    
    # Relationships
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="vendor")
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="vendor")
```

### Purchase Orders

```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(100) NOT NULL UNIQUE,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    order_date DATE NOT NULL,
    expected_date DATE,
    subtotal DECIMAL(15, 2),
    tax_amount DECIMAL(15, 2),
    total DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    shipping_address TEXT,
    billing_address TEXT,
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Status enum values
-- 'draft', 'pending_approval', 'approved', 'sent', 'partially_received',
-- 'received', 'invoiced', 'closed', 'cancelled'
```

### Line Items

```sql
CREATE TABLE line_items (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    po_line_id INTEGER REFERENCES po_line_items(id),
    line_number INTEGER NOT NULL,
    description VARCHAR(500) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    unit_price DECIMAL(15, 4) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    unit_of_measure VARCHAR(50),
    category VARCHAR(100),
    gl_code VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_invoice_line UNIQUE (invoice_id, line_number)
);
```

---

## Relationship Tables

### Approvals

```sql
CREATE TABLE approvals (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    approver_id INTEGER NOT NULL REFERENCES users(id),
    level INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    decision VARCHAR(50),
    comment TEXT,
    decided_at TIMESTAMP,
    due_date TIMESTAMP,
    reminded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_approval_level UNIQUE (invoice_id, level)
);

-- Status enum values: 'pending', 'approved', 'rejected', 'delegated', 'expired'
-- Decision enum values: 'approve', 'reject', 'request_info', 'delegate'
```

### Approval Rules

```sql
CREATE TABLE approval_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    condition_type VARCHAR(50) NOT NULL,
    condition_operator VARCHAR(20) NOT NULL,
    condition_value VARCHAR(255) NOT NULL,
    approver_id INTEGER REFERENCES users(id),
    approver_role_id INTEGER REFERENCES roles(id),
    priority INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- condition_type: 'amount', 'vendor', 'department', 'category', 'risk_score'
-- condition_operator: 'equals', 'not_equals', 'greater_than', 'less_than', 'between', 'in'

-- Example rules:
-- 1. Amount > $1000 requires Manager approval
-- 2. Amount > $5000 requires Director approval
-- 3. New vendor requires Finance approval
-- 4. High risk score requires Audit approval
```

---

## Audit & System Tables

### Audit Logs

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id INTEGER REFERENCES users(id),
    ip_address INET,
    user_agent VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Action enum values: 'create', 'update', 'delete', 'approve', 'reject',
--                     'upload', 'download', 'export', 'login', 'logout'

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
```

### Notifications

```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Type enum values: 'approval_request', 'approval_complete', 'invoice_processed',
--                   'invoice_failed', 'system_alert', 'reminder'

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
```

### Webhooks

```sql
CREATE TABLE webhooks (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    events VARCHAR(255)[] NOT NULL,
    secret VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_triggered TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events: 'invoice.created', 'invoice.extracted', 'invoice.approved',
--         'invoice.rejected', 'invoice.paid', 'approval.requested'
```

### ERP Connections

```sql
CREATE TABLE erp_connections (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    credentials BYTEA NOT NULL,  -- Encrypted
    settings JSONB,
    last_sync TIMESTAMP,
    sync_status VARCHAR(50),
    error_message TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Provider enum: 'quickbooks', 'xero', 'sap', 'netsuite', 'dynamics365'
```

---

## Indexes & Constraints

### Performance Indexes

```sql
-- Invoice lookups
CREATE INDEX idx_invoices_vendor_id ON invoices(vendor_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_created_at ON invoices(created_at DESC);
CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_due_date ON invoices(due_date) WHERE status IN ('approved', 'pending_approval');

-- Full-text search on invoice number and vendor name
CREATE INDEX idx_invoices_search ON invoices USING gin(to_tsvector('english', invoice_number));

-- Approval queries
CREATE INDEX idx_approvals_invoice_id ON approvals(invoice_id);
CREATE INDEX idx_approvals_approver_id ON approvals(approver_id);
CREATE INDEX idx_approvals_status ON approvals(status) WHERE status = 'pending';
CREATE INDEX idx_approvals_pending ON approvals(approver_id, status) WHERE status = 'pending';

-- Vendor lookups
CREATE INDEX idx_vendors_name ON vendors(name);
CREATE INDEX idx_vendors_tax_id ON vendors(tax_id);
CREATE INDEX idx_vendors_is_approved ON vendors(is_approved);

-- PO lookups
CREATE INDEX idx_pos_po_number ON purchase_orders(po_number);
CREATE INDEX idx_pos_vendor_id ON purchase_orders(vendor_id);
CREATE INDEX idx_pos_status ON purchase_orders(status);

-- Audit trail
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- User sessions
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = true;
```

### Constraints

```sql
-- Ensure invoice total matches calculated total
ALTER TABLE invoices ADD CONSTRAINT chk_invoice_total 
    CHECK (total >= 0);

-- Ensure approval levels are sequential
ALTER TABLE approvals ADD CONSTRAINT chk_approval_level 
    CHECK (level > 0 AND level <= 10);

-- Ensure vendor risk score is valid
ALTER TABLE vendors ADD CONSTRAINT chk_vendor_risk_score 
    CHECK (risk_score >= 0 AND risk_score <= 1);

-- Ensure line item amounts are positive
ALTER TABLE line_items ADD CONSTRAINT chk_line_item_amount 
    CHECK (amount >= 0);
```

---

## Migration Strategy

### Alembic Configuration

```python
# alembic/env.py
from src.models import Base
from src.core.config import settings

target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_engine(settings.DATABASE_URL)
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

### Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "Add invoice status column"

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

### Sample Migration

```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Create Date: 2026-01-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '001'
down_revision = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('invoice_number', sa.String(100), nullable=False),
        sa.Column('vendor_id', sa.Integer(), sa.ForeignKey('vendors.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, default='uploaded'),
        sa.Column('total', sa.Numeric(15, 2), nullable=False),
        sa.Column('extracted_data', JSONB),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_invoices_status', 'invoices', ['status'])

def downgrade():
    op.drop_table('invoices')
    op.drop_table('users')
```

---

## Related Documentation

- **[Section 3: Component Deep Dive](./03_Component_Details.md)** - Database configuration details
- **[Section 6: API Overview](./06_API_Overview.md)** - API endpoints using this data model
- **[API Reference](../API_Reference.md)** - Complete API documentation
- **[Deployment Guide](../Deployment_Guide.md)** - Database deployment and backup

---

*Continue to [Section 6: API Overview](./06_API_Overview.md)*
