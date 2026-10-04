"""add persistent worker heartbeats

Revision ID: c4e8b2a6d190
Revises: b7e9a1c3d502
Create Date: 2026-10-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c4e8b2a6d190"
down_revision = "b7e9a1c3d502"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_id", sa.String(length=160), primary_key=True),
        sa.Column("last_heartbeat", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_worker_heartbeats_last_heartbeat",
        "worker_heartbeats",
        ["last_heartbeat"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_worker_heartbeats_last_heartbeat",
        table_name="worker_heartbeats",
    )
    op.drop_table("worker_heartbeats")
