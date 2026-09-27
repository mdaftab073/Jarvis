"""add learning analytics and practice tracking

Revision ID: d43f9b1c6e20
Revises: c31e7a9b4d20
Create Date: 2026-09-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d43f9b1c6e20"
down_revision: Union[str, Sequence[str], None] = "c31e7a9b4d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_topic_performance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_answers", sa.Integer(), server_default="0", nullable=False),
        sa.Column("incorrect_answers", sa.Integer(), server_default="0", nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="50", nullable=False),
        sa.Column("mastery_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("attempts >= 0", name="ck_topic_performance_attempts"),
        sa.CheckConstraint("correct_answers >= 0", name="ck_topic_performance_correct_answers"),
        sa.CheckConstraint("incorrect_answers >= 0", name="ck_topic_performance_incorrect_answers"),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="ck_topic_performance_confidence"),
        sa.CheckConstraint("mastery_score >= 0 AND mastery_score <= 100", name="ck_topic_performance_mastery"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "subject_id", "topic", name="uq_student_topic_performance_topic"),
    )
    for column in ("id", "student_id", "subject_id"):
        op.create_index(
            f"ix_student_topic_performance_{column}",
            "student_topic_performance",
            [column],
        )

    op.create_table(
        "practice_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("total_questions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_answers", sa.Integer(), server_default="0", nullable=False),
        sa.CheckConstraint("total_questions >= 0", name="ck_practice_sessions_total_questions"),
        sa.CheckConstraint("correct_answers >= 0", name="ck_practice_sessions_correct_answers"),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_practice_sessions_score"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "student_id", "subject_id"):
        op.create_index(
            f"ix_practice_sessions_{column}",
            "practice_sessions",
            [column],
        )

    op.create_table(
        "practice_question_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("practice_session_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("expected_answer", sa.String(), nullable=True),
        sa.Column("student_answer", sa.String(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), server_default="50", nullable=False),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name="ck_practice_attempt_score"),
        sa.CheckConstraint("confidence_score >= 0 AND confidence_score <= 100", name="ck_practice_attempt_confidence"),
        sa.ForeignKeyConstraint(["practice_session_id"], ["practice_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "practice_session_id", "topic"):
        op.create_index(
            f"ix_practice_question_attempts_{column}",
            "practice_question_attempts",
            [column],
        )


def downgrade() -> None:
    for column in ("id", "practice_session_id", "topic"):
        op.drop_index(
            f"ix_practice_question_attempts_{column}",
            table_name="practice_question_attempts",
        )
    op.drop_table("practice_question_attempts")
    for column in ("id", "student_id", "subject_id"):
        op.drop_index(
            f"ix_practice_sessions_{column}",
            table_name="practice_sessions",
        )
    op.drop_table("practice_sessions")
    for column in ("id", "student_id", "subject_id"):
        op.drop_index(
            f"ix_student_topic_performance_{column}",
            table_name="student_topic_performance",
        )
    op.drop_table("student_topic_performance")
