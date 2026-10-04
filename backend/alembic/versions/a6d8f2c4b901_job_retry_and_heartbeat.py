"""add job recovery and retry lifecycle fields

Revision ID: a6d8f2c4b901
Revises: f0b1c3d5e709
Create Date: 2026-10-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a6d8f2c4b901"
down_revision = "f0b1c3d5e709"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_executions", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.add_column("job_executions", sa.Column("last_heartbeat", sa.DateTime(), nullable=True))
    op.add_column(
        "job_executions",
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
    )
    op.execute(
        "UPDATE job_executions SET finished_at = completed_at "
        "WHERE completed_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("job_executions", "max_retries")
    op.drop_column("job_executions", "last_heartbeat")
    op.drop_column("job_executions", "finished_at")
