"""Add ERP integration tables

Revision ID: 001_add_erp_tables
Revises: 
Create Date: 2026-01-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_erp_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ERP integration tables"""
    
    # Create ERPConnection table
    op.create_table(
        'erp_connections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('system_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('credentials', sa.JSON, nullable=True),
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('company_db', sa.String(255), nullable=True),
        sa.Column('api_url', sa.String(500), nullable=True),
        sa.Column('last_connected_at', sa.DateTime, nullable=True),
        sa.Column('last_sync_at', sa.DateTime, nullable=True),
        sa.Column('connection_error', sa.Text, nullable=True),
        sa.Column('auto_sync_enabled', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('sync_interval_minutes', sa.Integer, nullable=False, server_default='60'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', sa.String(255), nullable=False),
    )
    
    # Create indexes for erp_connections
    op.create_index('ix_erp_connections_status', 'erp_connections', ['status'])
    op.create_index('ix_erp_connections_system_type', 'erp_connections', ['system_type'])
    op.create_index('ix_erp_connections_last_sync_at', 'erp_connections', ['last_sync_at'])
    
    # Create ERPSyncLog table
    op.create_table(
        'erp_sync_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('connection_id', sa.String(36), sa.ForeignKey('erp_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('sync_direction', sa.String(20), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('total_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('errors', sa.JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('sync_params', sa.JSON, nullable=True),
        sa.Column('triggered_by', sa.String(255), nullable=False),
    )
    
    # Create indexes for erp_sync_logs
    op.create_index('ix_erp_sync_logs_connection_id', 'erp_sync_logs', ['connection_id'])
    op.create_index('ix_erp_sync_logs_entity_type', 'erp_sync_logs', ['entity_type'])
    op.create_index('ix_erp_sync_logs_status', 'erp_sync_logs', ['status'])
    op.create_index('ix_erp_sync_logs_started_at', 'erp_sync_logs', ['started_at'])
    
    # Create ERPFieldMapping table
    op.create_table(
        'erp_field_mappings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('connection_id', sa.String(36), sa.ForeignKey('erp_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('smartap_field', sa.String(255), nullable=False),
        sa.Column('erp_field', sa.String(255), nullable=False),
        sa.Column('transformation_rule', sa.Text, nullable=True),
        sa.Column('default_value', sa.String(500), nullable=True),
        sa.Column('is_required', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('validation_regex', sa.String(500), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for erp_field_mappings
    op.create_index('ix_erp_field_mappings_connection_id', 'erp_field_mappings', ['connection_id'])
    op.create_index('ix_erp_field_mappings_entity_type', 'erp_field_mappings', ['entity_type'])
    op.create_index('ix_erp_field_mappings_smartap_field', 'erp_field_mappings', ['smartap_field'])
    
    # Create ERPVendorMapping table
    op.create_table(
        'erp_vendor_mappings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('connection_id', sa.String(36), sa.ForeignKey('erp_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('smartap_vendor_id', sa.String(36), nullable=False),  # Would be FK to vendors table
        sa.Column('erp_vendor_id', sa.String(255), nullable=False),
        sa.Column('erp_vendor_name', sa.String(500), nullable=True),
        sa.Column('first_synced_at', sa.DateTime, nullable=False),
        sa.Column('last_synced_at', sa.DateTime, nullable=False),
        sa.Column('sync_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create unique constraint and indexes for erp_vendor_mappings
    op.create_unique_constraint(
        'uq_erp_vendor_mappings_connection_vendor',
        'erp_vendor_mappings',
        ['connection_id', 'smartap_vendor_id']
    )
    op.create_index('ix_erp_vendor_mappings_connection_id', 'erp_vendor_mappings', ['connection_id'])
    op.create_index('ix_erp_vendor_mappings_smartap_vendor_id', 'erp_vendor_mappings', ['smartap_vendor_id'])
    op.create_index('ix_erp_vendor_mappings_erp_vendor_id', 'erp_vendor_mappings', ['erp_vendor_id'])
    
    # Create ERPInvoiceMapping table
    op.create_table(
        'erp_invoice_mappings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('connection_id', sa.String(36), sa.ForeignKey('erp_connections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('smartap_invoice_id', sa.String(36), nullable=False),  # Would be FK to invoices table
        sa.Column('erp_invoice_id', sa.String(255), nullable=False),
        sa.Column('erp_invoice_number', sa.String(255), nullable=True),
        sa.Column('exported_at', sa.DateTime, nullable=False),
        sa.Column('exported_by', sa.String(255), nullable=False),
        sa.Column('payment_status', sa.String(50), nullable=True),
        sa.Column('payment_synced_at', sa.DateTime, nullable=True),
        sa.Column('payment_amount', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create unique constraint and indexes for erp_invoice_mappings
    op.create_unique_constraint(
        'uq_erp_invoice_mappings_connection_invoice',
        'erp_invoice_mappings',
        ['connection_id', 'smartap_invoice_id']
    )
    op.create_index('ix_erp_invoice_mappings_connection_id', 'erp_invoice_mappings', ['connection_id'])
    op.create_index('ix_erp_invoice_mappings_smartap_invoice_id', 'erp_invoice_mappings', ['smartap_invoice_id'])
    op.create_index('ix_erp_invoice_mappings_erp_invoice_id', 'erp_invoice_mappings', ['erp_invoice_id'])
    op.create_index('ix_erp_invoice_mappings_payment_status', 'erp_invoice_mappings', ['payment_status'])


def downgrade() -> None:
    """Drop ERP integration tables"""
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('erp_invoice_mappings')
    op.drop_table('erp_vendor_mappings')
    op.drop_table('erp_field_mappings')
    op.drop_table('erp_sync_logs')
    op.drop_table('erp_connections')
