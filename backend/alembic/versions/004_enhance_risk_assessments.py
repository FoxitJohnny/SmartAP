"""Enhance risk_assessments table with matching_risk_score and detail columns.

Revision ID: 004_enhance_risk_assessments
Revises: 003_add_performance_indexes
Create Date: 2026-02-24 00:00:00.000000

Adds:
- matching_risk_score (Float) — PO-matching risk component
- vendor_risk_info (JSON) — persisted vendor risk detail
- price_anomaly_info (JSON) — persisted price anomaly detail
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_enhance_risk_assessments"
down_revision: Union[str, None] = "003_add_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new columns to risk_assessments."""
    with op.batch_alter_table("risk_assessments") as batch_op:
        batch_op.add_column(
            sa.Column("matching_risk_score", sa.Float(), nullable=True, server_default="0.0")
        )
        batch_op.add_column(
            sa.Column("vendor_risk_info", sa.JSON(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("price_anomaly_info", sa.JSON(), nullable=True)
        )


def downgrade() -> None:
    """Remove added columns."""
    with op.batch_alter_table("risk_assessments") as batch_op:
        batch_op.drop_column("price_anomaly_info")
        batch_op.drop_column("vendor_risk_info")
        batch_op.drop_column("matching_risk_score")
