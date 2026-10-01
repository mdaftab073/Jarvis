"""add digital twin academic operating system

Revision ID: b25c9e1f3a40
Revises: a14b8c9d2e10
Create Date: 2026-09-30 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "b25c9e1f3a40"
down_revision = "a14b8c9d2e10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "student_academic_profiles",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("enrollment_number", sa.String(50), nullable=True, index=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("semester", sa.Integer, nullable=True),
        sa.Column("section", sa.String(20), nullable=True),
        sa.Column("batch_year", sa.Integer, nullable=True),
        sa.Column("current_cpi", sa.Float, nullable=True),
        sa.Column("current_spi", sa.Float, nullable=True),
        sa.Column("total_credits", sa.Integer, nullable=True, server_default="0"),
        sa.Column("earned_credits", sa.Integer, nullable=True, server_default="0"),
        sa.Column("academic_status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("academic_profile_id", sa.Integer, sa.ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("attended_classes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_classes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("attendance_percentage", sa.Float, nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("academic_profile_id", "subject_id", name="uq_attendance_records_profile_subject"),
    )
    op.create_table(
        "grade_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("academic_profile_id", sa.Integer, sa.ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("component_type", sa.String(20), nullable=False),
        sa.Column("obtained_marks", sa.Float, nullable=True),
        sa.Column("max_marks", sa.Float, nullable=False, server_default="100"),
        sa.Column("grade_letter", sa.String(5), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "deadline_items",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("academic_profile_id", sa.Integer, sa.ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("item_type", sa.String(30), nullable=False, server_default="OTHER"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("priority", sa.String(10), nullable=False, server_default="MEDIUM"),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "study_activity_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("academic_profile_id", sa.Integer, sa.ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("activity_type", sa.String(30), nullable=False),
        sa.Column("duration_minutes", sa.Float, nullable=False, server_default="0"),
        sa.Column("topics_covered", sa.JSON, nullable=True),
        sa.Column("productivity_score", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )
    op.create_table(
        "digital_twin_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("academic_profile_id", sa.Integer, sa.ForeignKey("student_academic_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("overall_readiness", sa.Float, nullable=True),
        sa.Column("risk_level", sa.String(10), nullable=False, server_default="LOW"),
        sa.Column("mastery_summary", sa.JSON, nullable=True),
        sa.Column("attendance_summary", sa.JSON, nullable=True),
        sa.Column("grade_summary", sa.JSON, nullable=True),
        sa.Column("upcoming_deadlines", sa.JSON, nullable=True),
        sa.Column("ai_recommendations", sa.JSON, nullable=True),
        sa.Column("study_streak_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_study_minutes_week", sa.Float, nullable=False, server_default="0"),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade():
    op.drop_table("digital_twin_snapshots")
    op.drop_table("study_activity_logs")
    op.drop_table("deadline_items")
    op.drop_table("grade_records")
    op.drop_table("attendance_records")
    op.drop_table("student_academic_profiles")
