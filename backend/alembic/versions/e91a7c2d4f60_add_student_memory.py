"""add student profiles, memories, and readiness history

Revision ID: e91a7c2d4f60
Revises: d43f9b1c6e20
Create Date: 2026-09-28 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e91a7c2d4f60"
down_revision: Union[str, Sequence[str], None] = "d43f9b1c6e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("preferred_study_hours", sa.Float(), nullable=True),
        sa.Column("preferred_subjects", sa.JSON(), nullable=False),
        sa.Column("current_goal", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "preferred_study_hours IS NULL OR preferred_study_hours > 0",
            name="ck_student_profiles_preferred_study_hours",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_student_profiles_student"),
    )
    for column in ("id", "student_id"):
        op.create_index(f"ix_student_profiles_{column}", "student_profiles", [column])

    op.create_table(
        "student_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("memory_type", sa.String(), nullable=False),
        sa.Column("memory_key", sa.String(), nullable=False),
        sa.Column("memory_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "memory_type IN ('STRENGTH', 'WEAKNESS', 'GOAL', 'HABIT', 'RECOMMENDATION', 'READINESS')",
            name="ck_student_memories_memory_type",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "memory_type",
            "memory_key",
            name="uq_student_memories_student_type_key",
        ),
    )
    for column in ("id", "student_id"):
        op.create_index(f"ix_student_memories_{column}", "student_memories", [column])

    op.create_table(
        "readiness_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "student_id", "subject_id", "captured_at"):
        op.create_index(
            f"ix_readiness_snapshots_{column}",
            "readiness_snapshots",
            [column],
        )


def downgrade() -> None:
    for column in ("id", "student_id", "subject_id", "captured_at"):
        op.drop_index(
            f"ix_readiness_snapshots_{column}",
            table_name="readiness_snapshots",
        )
    op.drop_table("readiness_snapshots")
    for column in ("id", "student_id"):
        op.drop_index(f"ix_student_memories_{column}", table_name="student_memories")
    op.drop_table("student_memories")
    for column in ("id", "student_id"):
        op.drop_index(f"ix_student_profiles_{column}", table_name="student_profiles")
    op.drop_table("student_profiles")