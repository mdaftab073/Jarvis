"""add semester copilot entities

Revision ID: f2c8a4d1b709
Revises: e91a7c2d4f60
Create Date: 2026-09-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2c8a4d1b709"
down_revision: Union[str, Sequence[str], None] = "e91a7c2d4f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "semesters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("semester_number", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("target_cgpa", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("semester_number > 0", name="ck_semesters_number_positive"),
        sa.CheckConstraint("end_date >= start_date", name="ck_semesters_date_range"),
        sa.CheckConstraint(
            "target_cgpa IS NULL OR target_cgpa > 0",
            name="ck_semesters_target_cgpa_positive",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED')",
            name="ck_semesters_status",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "semester_number",
            name="uq_semesters_student_number",
        ),
    )
    for column in ("id", "student_id"):
        op.create_index(f"ix_semesters_{column}", "semesters", [column])

    op.create_table(
        "semester_subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("target_score", sa.Float(), nullable=True),
        sa.Column("current_readiness", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "target_score IS NULL OR (target_score >= 0 AND target_score <= 100)",
            name="ck_semester_subjects_target_score",
        ),
        sa.CheckConstraint(
            "current_readiness >= 0 AND current_readiness <= 100",
            name="ck_semester_subjects_current_readiness",
        ),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "semester_id",
            "subject_id",
            name="uq_semester_subjects_semester_subject",
        ),
    )
    for column in ("id", "semester_id", "subject_id"):
        op.create_index(
            f"ix_semester_subjects_{column}",
            "semester_subjects",
            [column],
        )

    op.create_table(
        "semester_milestones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "completed IN (true, false)",
            name="ck_semester_milestones_completed",
        ),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "semester_id", "due_date"):
        op.create_index(
            f"ix_semester_milestones_{column}",
            "semester_milestones",
            [column],
        )


def downgrade() -> None:
    for column in ("id", "semester_id", "due_date"):
        op.drop_index(
            f"ix_semester_milestones_{column}",
            table_name="semester_milestones",
        )
    op.drop_table("semester_milestones")
    for column in ("id", "semester_id", "subject_id"):
        op.drop_index(f"ix_semester_subjects_{column}", table_name="semester_subjects")
    op.drop_table("semester_subjects")
    for column in ("id", "student_id"):
        op.drop_index(f"ix_semesters_{column}", table_name="semesters")
    op.drop_table("semesters")