"""add student operating system entities

Revision ID: c82d4e6f1a30
Revises: b25c9e1f3a40
Create Date: 2026-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "c82d4e6f1a30"
down_revision = "b25c9e1f3a40"
branch_labels = None
depends_on = None


def upgrade():
    for table_name in ("attendance_records", "grade_records", "deadline_items"):
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(sa.Column("student_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table_name}_student_id_students", "students", ["student_id"], ["id"], ondelete="CASCADE"
            )
            batch.create_index(f"ix_{table_name}_student_id", ["student_id"])

    op.execute("UPDATE attendance_records SET student_id = (SELECT student_id FROM student_academic_profiles WHERE id = attendance_records.academic_profile_id)")
    op.execute("UPDATE grade_records SET student_id = (SELECT student_id FROM student_academic_profiles WHERE id = grade_records.academic_profile_id)")
    op.execute("UPDATE deadline_items SET student_id = (SELECT student_id FROM student_academic_profiles WHERE id = deadline_items.academic_profile_id)")

    with op.batch_alter_table("grade_records") as batch:
        batch.add_column(sa.Column("semester", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("credits", sa.Float(), nullable=True))
        batch.add_column(sa.Column("grade", sa.String(length=5), nullable=True))
        batch.add_column(sa.Column("grade_points", sa.Float(), nullable=True))
        batch.alter_column("component_type", existing_type=sa.String(length=20), nullable=False, server_default="OTHER")

    op.create_table(
        "student_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("notification_type IN ('INFO', 'SUCCESS', 'WARNING', 'CRITICAL', 'REMINDER')", name="ck_student_notifications_type"),
    )
    op.create_index("ix_student_notifications_student_id", "student_notifications", ["student_id"])
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False, server_default="OTHER"),
        sa.CheckConstraint("end_time > start_time", name="ck_calendar_events_time_order"),
    )
    op.create_index("ix_calendar_events_student_id", "calendar_events", ["student_id"])
    op.create_index("ix_calendar_events_start_time", "calendar_events", ["start_time"])
    op.create_table(
        "study_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("planned_duration", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("end_time > start_time", name="ck_study_blocks_time_order"),
        sa.CheckConstraint("planned_duration >= 0", name="ck_study_blocks_duration_nonneg"),
    )
    op.create_index("ix_study_blocks_student_id", "study_blocks", ["student_id"])
    op.create_index("ix_study_blocks_subject_id", "study_blocks", ["subject_id"])
    op.create_index("ix_study_blocks_start_time", "study_blocks", ["start_time"])
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("trigger_time", sa.DateTime(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_reminders_student_id", "reminders", ["student_id"])
    op.create_index("ix_reminders_trigger_time", "reminders", ["trigger_time"])
    op.create_table(
        "student_goals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_student_goals_student_id", "student_goals", ["student_id"])
    op.create_table(
        "student_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("preferred_study_time", sa.String(30), nullable=True),
        sa.Column("preferred_session_length", sa.Integer(), nullable=True),
        sa.Column("study_style", sa.String(100), nullable=True),
        sa.UniqueConstraint("student_id", name="uq_student_preferences_student"),
    )
    op.create_index("ix_student_preferences_student_id", "student_preferences", ["student_id"])
    op.create_table(
        "student_habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("habit_name", sa.String(120), nullable=False),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.CheckConstraint("streak >= 0", name="ck_student_habits_streak_nonneg"),
        sa.CheckConstraint("completion_rate >= 0 AND completion_rate <= 100", name="ck_student_habits_completion_rate"),
    )
    op.create_index("ix_student_habits_student_id", "student_habits", ["student_id"])


def downgrade():
    for table_name in (
        "student_habits", "student_preferences", "student_goals", "reminders",
        "study_blocks", "calendar_events", "student_notifications",
    ):
        op.drop_table(table_name)

    with op.batch_alter_table("grade_records") as batch:
        batch.drop_column("grade_points")
        batch.drop_column("grade")
        batch.drop_column("credits")
        batch.drop_column("semester")
        batch.alter_column("component_type", existing_type=sa.String(length=20), nullable=False, server_default=None)

    for table_name in ("deadline_items", "grade_records", "attendance_records"):
        with op.batch_alter_table(table_name) as batch:
            batch.drop_index(f"ix_{table_name}_student_id")
            batch.drop_constraint(f"fk_{table_name}_student_id_students", type_="foreignkey")
            batch.drop_column("student_id")
