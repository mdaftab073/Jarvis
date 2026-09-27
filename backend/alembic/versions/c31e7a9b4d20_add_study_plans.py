"""add study plans and tasks

Revision ID: c31e7a9b4d20
Revises: 8d2f4a6c1b90
Create Date: 2026-09-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c31e7a9b4d20"
down_revision: Union[str, Sequence[str], None] = "8d2f4a6c1b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("hours_per_day", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "hours_per_day > 0",
            name="ck_study_plans_hours_per_day",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_plans_id", "study_plans", ["id"])
    op.create_index("ix_study_plans_student_id", "study_plans", ["student_id"])
    op.create_index("ix_study_plans_subject_id", "study_plans", ["subject_id"])

    op.create_table(
        "study_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("estimated_hours", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), server_default="PENDING", nullable=False),
        sa.CheckConstraint("day_number >= 1", name="ck_study_tasks_day_number"),
        sa.CheckConstraint("priority >= 1", name="ck_study_tasks_priority"),
        sa.CheckConstraint(
            "estimated_hours > 0",
            name="ck_study_tasks_estimated_hours",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED')",
            name="ck_study_tasks_status",
        ),
        sa.ForeignKeyConstraint(
            ["study_plan_id"],
            ["study_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_tasks_id", "study_tasks", ["id"])
    op.create_index("ix_study_tasks_study_plan_id", "study_tasks", ["study_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_study_tasks_study_plan_id", table_name="study_tasks")
    op.drop_index("ix_study_tasks_id", table_name="study_tasks")
    op.drop_table("study_tasks")
    op.drop_index("ix_study_plans_subject_id", table_name="study_plans")
    op.drop_index("ix_study_plans_student_id", table_name="study_plans")
    op.drop_index("ix_study_plans_id", table_name="study_plans")
    op.drop_table("study_plans")