"""add persisted background job executions

Revision ID: d2f6a4b8c910
Revises: c8e2f14a9d30
Create Date: 2026-10-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d2f6a4b8c910"
down_revision = "c8e2f14a9d30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')", name="ck_job_executions_status"),
    )
    op.create_index("ix_job_executions_id", "job_executions", ["id"])
    op.create_index("ix_job_executions_job_name", "job_executions", ["job_name"])
    op.create_index("ix_job_executions_status", "job_executions", ["status"])
    op.create_index("ix_job_executions_student_id", "job_executions", ["student_id"])
    op.create_index("ix_job_executions_created_at", "job_executions", ["created_at"])
    op.create_index("ix_job_executions_name_status", "job_executions", ["job_name", "status"])


def downgrade():
    op.drop_index("ix_job_executions_name_status", table_name="job_executions")
    op.drop_index("ix_job_executions_created_at", table_name="job_executions")
    op.drop_index("ix_job_executions_student_id", table_name="job_executions")
    op.drop_index("ix_job_executions_status", table_name="job_executions")
    op.drop_index("ix_job_executions_job_name", table_name="job_executions")
    op.drop_index("ix_job_executions_id", table_name="job_executions")
    op.drop_table("job_executions")