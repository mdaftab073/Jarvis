# Alembic migration for Learning Intelligence Layer

"""add learning intelligence tables

Revision ID: 20230928_14_add_learning_intelligence_tables
Revises: d43f9b1c6e20  # previous head (adjust if needed)
Create Date: 2026-09-28 21:47:45.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a14b8c9d2e10"
down_revision = "f2c8a4d1b709"
branch_labels = None
depends_on = None

def upgrade():
    # topics
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # flashcard decks
    op.create_table(
        "flashcard_decks",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # flashcards
    op.create_table(
        "flashcards",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("deck_id", sa.Integer, sa.ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("topic_id", sa.Integer, sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # quiz sessions
    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("total_questions", sa.Integer, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # quiz questions
    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("quiz_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("topic_id", sa.Integer, sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(length=20), nullable=False),
        sa.Column("correct_answer", sa.Text, nullable=False),
    )
    # quiz answers
    op.create_table(
        "quiz_answers",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("student_answer", sa.Text, nullable=False),
        sa.Column("is_correct", sa.Boolean, nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # topic mastery
    op.create_table(
        "topic_mastery",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("topic_id", sa.Integer, sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mastery_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    # learning sessions
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("duration_minutes", sa.Float, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table("learning_sessions")
    op.drop_table("topic_mastery")
    op.drop_table("quiz_answers")
    op.drop_table("quiz_questions")
    op.drop_table("quiz_sessions")
    op.drop_table("flashcards")
    op.drop_table("flashcard_decks")
    op.drop_table("topics")
