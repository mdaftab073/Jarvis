"""add material types and exam questions

Revision ID: 8d2f4a6c1b90
Revises: 7c8d9e0f1a2b
Create Date: 2026-09-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8d2f4a6c1b90"
down_revision: Union[str, Sequence[str], None] = "7c8d9e0f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "study_materials",
        sa.Column(
            "material_type",
            sa.String(),
            nullable=False,
            server_default="NOTES",
        ),
    )
    op.create_check_constraint(
        "ck_study_materials_material_type",
        "study_materials",
        "material_type IN ('NOTES', 'PYQ', 'SYLLABUS', 'REFERENCE')",
    )
    op.create_table(
        "exam_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("study_material_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.String(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("marks", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["study_material_id"],
            ["study_materials.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_questions_id",
        "exam_questions",
        ["id"],
    )
    op.create_index(
        "ix_exam_questions_subject_id",
        "exam_questions",
        ["subject_id"],
    )
    op.create_index(
        "ix_exam_questions_study_material_id",
        "exam_questions",
        ["study_material_id"],
    )
    op.create_index(
        "ix_exam_questions_year",
        "exam_questions",
        ["year"],
    )
    op.create_index(
        "ix_exam_questions_topic",
        "exam_questions",
        ["topic"],
    )


def downgrade() -> None:
    op.drop_index("ix_exam_questions_topic", table_name="exam_questions")
    op.drop_index("ix_exam_questions_year", table_name="exam_questions")
    op.drop_index(
        "ix_exam_questions_study_material_id",
        table_name="exam_questions",
    )
    op.drop_index("ix_exam_questions_subject_id", table_name="exam_questions")
    op.drop_index("ix_exam_questions_id", table_name="exam_questions")
    op.drop_table("exam_questions")
    op.drop_constraint(
        "ck_study_materials_material_type",
        "study_materials",
        type_="check",
    )
    op.drop_column("study_materials", "material_type")