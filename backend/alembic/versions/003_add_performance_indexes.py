"""Add performance indexes for query optimization.

Revision ID: 003_add_performance_indexes
Revises: 002_add_approval_tables
Create Date: 2024-01-15 10:00:00.000000

This migration adds composite indexes to optimize common query patterns:
- Invoice listing with status filtering and date sorting
- Vendor-based invoice lookups
- Matching result queries by status
- Risk assessment queries by risk level
- Audit log queries by entity and timestamp
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_add_performance_indexes"
down_revision: Union[str, None] = "002_add_approval_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for common query patterns."""
    
    # ===========================================
    # Invoice Table Composite Indexes
    # ===========================================
    
    # Index for listing invoices by status with date ordering
    # Used by: GET /api/invoices?status=pending&sort=created_at
    op.create_index(
        "ix_invoices_status_created_at",
        "invoices",
        ["status", sa.text("created_at DESC")],
        postgresql_using="btree",
    )
    
    # Index for vendor-specific invoice queries with status
    # Used by: GET /api/vendors/{id}/invoices?status=approved
    op.create_index(
        "ix_invoices_vendor_id_status",
        "invoices",
        ["vendor_id", "status"],
        postgresql_using="btree",
    )
    
    # Index for date range queries on invoices
    # Used by: GET /api/invoices?start_date=X&end_date=Y
    op.create_index(
        "ix_invoices_invoice_date",
        "invoices",
        ["invoice_date"],
        postgresql_using="btree",
    )
    
    # Index for amount-based queries and analytics
    # Used by: Dashboard analytics, reports
    op.create_index(
        "ix_invoices_total_amount",
        "invoices",
        ["total_amount"],
        postgresql_using="btree",
    )
    
    # Partial index for pending invoices only (commonly queried)
    op.create_index(
        "ix_invoices_pending",
        "invoices",
        ["created_at"],
        postgresql_where=sa.text("status = 'pending'"),
        postgresql_using="btree",
    )
    
    # ===========================================
    # Purchase Order Table Composite Indexes
    # ===========================================
    
    # Index for PO lookups by vendor with status filtering
    # Used by: GET /api/vendors/{id}/purchase-orders?status=open
    op.create_index(
        "ix_purchase_orders_vendor_id_status",
        "purchase_orders",
        ["vendor_id", "status"],
        postgresql_using="btree",
    )
    
    # Index for date-based PO queries
    op.create_index(
        "ix_purchase_orders_po_date",
        "purchase_orders",
        ["po_date"],
        postgresql_using="btree",
    )
    
    # ===========================================
    # Matching Results Table Composite Indexes
    # ===========================================
    
    # Index for matching results by match status
    # Used by: GET /api/matching?matched=true
    op.create_index(
        "ix_matching_results_matched",
        "matching_results",
        ["matched"],
        postgresql_using="btree",
    )
    
    # Index for confidence score range queries
    # Used by: Dashboard analytics for match quality
    op.create_index(
        "ix_matching_results_confidence_score",
        "matching_results",
        ["confidence_score"],
        postgresql_using="btree",
    )
    
    # Composite index for invoice-PO lookup with match status
    op.create_index(
        "ix_matching_results_invoice_po_matched",
        "matching_results",
        ["invoice_id", "po_id", "matched"],
        postgresql_using="btree",
    )
    
    # ===========================================
    # Risk Assessments Table Composite Indexes
    # ===========================================
    
    # Index for risk level queries
    # Used by: GET /api/risk-assessments?level=high
    op.create_index(
        "ix_risk_assessments_risk_level",
        "risk_assessments",
        ["risk_level"],
        postgresql_using="btree",
    )
    
    # Index for risk score range queries
    # Used by: Dashboard risk analytics
    op.create_index(
        "ix_risk_assessments_risk_score",
        "risk_assessments",
        ["risk_score"],
        postgresql_using="btree",
    )
    
    # Composite index for invoice risk lookups
    op.create_index(
        "ix_risk_assessments_invoice_level",
        "risk_assessments",
        ["invoice_id", "risk_level"],
        postgresql_using="btree",
    )
    
    # ===========================================
    # Vendor Table Composite Indexes
    # ===========================================
    
    # Index for vendor status queries
    op.create_index(
        "ix_vendors_status",
        "vendors",
        ["status"],
        postgresql_using="btree",
    )
    
    # Index for vendor name search (case-insensitive)
    op.create_index(
        "ix_vendors_name_lower",
        "vendors",
        [sa.text("LOWER(vendor_name)")],
        postgresql_using="btree",
    )
    
    # ===========================================
    # User Table Composite Indexes
    # ===========================================
    
    # Index for active users
    op.create_index(
        "ix_users_is_active",
        "users",
        ["is_active"],
        postgresql_using="btree",
    )
    
    # Index for user role queries
    op.create_index(
        "ix_users_role",
        "users",
        ["role"],
        postgresql_using="btree",
    )
    
    # ===========================================
    # Refresh Token Table Indexes
    # ===========================================
    
    # Index for expired token cleanup
    op.create_index(
        "ix_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
        postgresql_using="btree",
    )
    
    # Partial index for non-revoked tokens
    op.create_index(
        "ix_refresh_tokens_active",
        "refresh_tokens",
        ["user_id", "expires_at"],
        postgresql_where=sa.text("revoked = false"),
        postgresql_using="btree",
    )
    
    # ===========================================
    # Payment Records Table Indexes
    # ===========================================
    
    # Index for payment date queries
    op.create_index(
        "ix_payment_records_payment_date",
        "payment_records",
        ["payment_date"],
        postgresql_using="btree",
    )
    
    # Index for payment status
    op.create_index(
        "ix_payment_records_status",
        "payment_records",
        ["status"],
        postgresql_using="btree",
    )
    
    # ===========================================
    # Fraud Flags Table Indexes
    # ===========================================
    
    # Index for flag type queries
    op.create_index(
        "ix_fraud_flags_flag_type",
        "fraud_flags",
        ["flag_type"],
        postgresql_using="btree",
    )
    
    # Index for severity level
    op.create_index(
        "ix_fraud_flags_severity",
        "fraud_flags",
        ["severity"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    """Remove performance indexes."""
    
    # Fraud Flags
    op.drop_index("ix_fraud_flags_severity", table_name="fraud_flags")
    op.drop_index("ix_fraud_flags_flag_type", table_name="fraud_flags")
    
    # Payment Records
    op.drop_index("ix_payment_records_status", table_name="payment_records")
    op.drop_index("ix_payment_records_payment_date", table_name="payment_records")
    
    # Refresh Tokens
    op.drop_index("ix_refresh_tokens_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    
    # Users
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    
    # Vendors
    op.drop_index("ix_vendors_name_lower", table_name="vendors")
    op.drop_index("ix_vendors_status", table_name="vendors")
    
    # Risk Assessments
    op.drop_index("ix_risk_assessments_invoice_level", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_risk_score", table_name="risk_assessments")
    op.drop_index("ix_risk_assessments_risk_level", table_name="risk_assessments")
    
    # Matching Results
    op.drop_index("ix_matching_results_invoice_po_matched", table_name="matching_results")
    op.drop_index("ix_matching_results_confidence_score", table_name="matching_results")
    op.drop_index("ix_matching_results_matched", table_name="matching_results")
    
    # Purchase Orders
    op.drop_index("ix_purchase_orders_po_date", table_name="purchase_orders")
    op.drop_index("ix_purchase_orders_vendor_id_status", table_name="purchase_orders")
    
    # Invoices
    op.drop_index("ix_invoices_pending", table_name="invoices")
    op.drop_index("ix_invoices_total_amount", table_name="invoices")
    op.drop_index("ix_invoices_invoice_date", table_name="invoices")
    op.drop_index("ix_invoices_vendor_id_status", table_name="invoices")
    op.drop_index("ix_invoices_status_created_at", table_name="invoices")
