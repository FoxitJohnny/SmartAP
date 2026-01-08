"""Add approval workflow tables

Revision ID: 002_add_approval_tables
Revises: 001_add_erp_tables
Create Date: 2026-01-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_approval_tables'
down_revision: Union[str, None] = '001_add_erp_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create approval workflow tables"""
    
    # Create ApprovalChain table
    op.create_table(
        'approval_chains',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('min_amount', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_amount', sa.Integer, nullable=True),
        sa.Column('required_approvers', sa.Integer, nullable=False, server_default='1'),
        sa.Column('sequential_approval', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('require_esign', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('esign_threshold', sa.Integer, nullable=True),
        sa.Column('approval_timeout_hours', sa.Integer, nullable=False, server_default='72'),
        sa.Column('auto_escalate_on_timeout', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for approval_chains
    op.create_index('ix_approval_chains_min_amount', 'approval_chains', ['min_amount'])
    op.create_index('ix_approval_chains_max_amount', 'approval_chains', ['max_amount'])
    
    # Create ApprovalLevel table
    op.create_table(
        'approval_levels',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('chain_id', sa.String(36), sa.ForeignKey('approval_chains.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level_number', sa.Integer, nullable=False),
        sa.Column('level_name', sa.String(100), nullable=False),
        sa.Column('approver_ids', sa.JSON, nullable=True),
        sa.Column('approver_emails', sa.JSON, nullable=False),
        sa.Column('required_approvals', sa.Integer, nullable=False, server_default='1'),
        sa.Column('timeout_hours', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for approval_levels
    op.create_index('ix_approval_levels_chain_id', 'approval_levels', ['chain_id'])
    op.create_index('ix_approval_levels_level_number', 'approval_levels', ['level_number'])
    
    # Create ApprovalWorkflow table
    op.create_table(
        'approval_workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('invoice_id', sa.String(255), nullable=False, unique=True),
        sa.Column('chain_id', sa.String(36), sa.ForeignKey('approval_chains.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('current_level', sa.Integer, nullable=False, server_default='1'),
        sa.Column('esign_required', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('esign_request_id', sa.String(36), sa.ForeignKey('esign_requests.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('escalated', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('escalation_reason', sa.String(100), nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for approval_workflows
    op.create_index('ix_approval_workflows_invoice_id', 'approval_workflows', ['invoice_id'])
    op.create_index('ix_approval_workflows_chain_id', 'approval_workflows', ['chain_id'])
    op.create_index('ix_approval_workflows_status', 'approval_workflows', ['status'])
    op.create_index('ix_approval_workflows_created_at', 'approval_workflows', ['created_at'])
    op.create_index('ix_approval_workflows_esign_request_id', 'approval_workflows', ['esign_request_id'])
    
    # Create ApprovalAction table
    op.create_table(
        'approval_actions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('approval_workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('approver_id', sa.String(255), nullable=True),
        sa.Column('approver_email', sa.String(255), nullable=False),
        sa.Column('level_number', sa.Integer, nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('forwarded_to', sa.String(255), nullable=True),
        sa.Column('escalated_to', sa.String(255), nullable=True),
        sa.Column('signature_id', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for approval_actions
    op.create_index('ix_approval_actions_workflow_id', 'approval_actions', ['workflow_id'])
    op.create_index('ix_approval_actions_approver_email', 'approval_actions', ['approver_email'])
    op.create_index('ix_approval_actions_level_number', 'approval_actions', ['level_number'])
    op.create_index('ix_approval_actions_action', 'approval_actions', ['action'])
    op.create_index('ix_approval_actions_created_at', 'approval_actions', ['created_at'])
    
    # Create ApprovalNotification table
    op.create_table(
        'approval_notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('approval_workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('delivered', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('opened', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('clicked', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('delivered_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes for approval_notifications
    op.create_index('ix_approval_notifications_workflow_id', 'approval_notifications', ['workflow_id'])
    op.create_index('ix_approval_notifications_recipient_email', 'approval_notifications', ['recipient_email'])
    op.create_index('ix_approval_notifications_notification_type', 'approval_notifications', ['notification_type'])
    op.create_index('ix_approval_notifications_delivered', 'approval_notifications', ['delivered'])
    op.create_index('ix_approval_notifications_created_at', 'approval_notifications', ['created_at'])
    
    # Create ArchivedDocument table
    op.create_table(
        'archived_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('invoice_id', sa.String(255), nullable=False, unique=True),
        sa.Column('archived_document_path', sa.String(1000), nullable=False, unique=True),
        sa.Column('document_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('flattened', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('audit_page_added', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('pdfa_converted', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('tamper_sealed', sa.Boolean, nullable=False, server_default='0'),
        sa.Column('seal_verification', sa.JSON, nullable=True),
        sa.Column('retention_years', sa.Integer, nullable=False, server_default='7'),
        sa.Column('retention_expires_at', sa.DateTime, nullable=True),
        sa.Column('workflow_id', sa.String(36), sa.ForeignKey('approval_workflows.id'), nullable=True),
        sa.Column('audit_data', sa.JSON, nullable=True),
        sa.Column('access_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('archived_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for archived_documents
    op.create_index('ix_archived_documents_invoice_id', 'archived_documents', ['invoice_id'])
    op.create_index('ix_archived_documents_document_hash', 'archived_documents', ['document_hash'])
    op.create_index('ix_archived_documents_status', 'archived_documents', ['status'])
    op.create_index('ix_archived_documents_archived_at', 'archived_documents', ['archived_at'])
    op.create_index('ix_archived_documents_retention_expires_at', 'archived_documents', ['retention_expires_at'])
    op.create_index('ix_archived_documents_workflow_id', 'archived_documents', ['workflow_id'])
    
    # Create DocumentAccessLog table
    op.create_table(
        'document_access_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('document_id', sa.String(36), sa.ForeignKey('archived_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('accessed_by', sa.String(255), nullable=False),
        sa.Column('access_type', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('accessed_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes for document_access_logs
    op.create_index('ix_document_access_logs_document_id', 'document_access_logs', ['document_id'])
    op.create_index('ix_document_access_logs_accessed_by', 'document_access_logs', ['accessed_by'])
    op.create_index('ix_document_access_logs_access_type', 'document_access_logs', ['access_type'])
    op.create_index('ix_document_access_logs_accessed_at', 'document_access_logs', ['accessed_at'])


def downgrade() -> None:
    """Drop approval workflow tables"""
    
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('document_access_logs')
    op.drop_table('archived_documents')
    op.drop_table('approval_notifications')
    op.drop_table('approval_actions')
    op.drop_table('approval_workflows')
    op.drop_table('approval_levels')
    op.drop_table('approval_chains')
