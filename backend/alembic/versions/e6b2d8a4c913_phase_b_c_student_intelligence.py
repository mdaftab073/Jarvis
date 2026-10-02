"""add goal habit productivity and generic connector persistence

Revision ID: e6b2d8a4c913
Revises: d14e6f2a9b31
Create Date: 2026-10-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "e6b2d8a4c913"
down_revision = "d14e6f2a9b31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("study_blocks") as batch:
        batch.add_column(sa.Column("title", sa.String(255), nullable=True))
        batch.add_column(sa.Column("block_type", sa.String(30), nullable=False, server_default="STUDY"))
        batch.create_check_constraint(
            "ck_study_blocks_type",
            "block_type IN ('STUDY', 'REVISION', 'ATTENDANCE_RECOVERY', 'DEADLINE_PREP', 'GOAL')",
        )

    with op.batch_alter_table("student_goals") as batch:
        batch.add_column(sa.Column("goal_type", sa.String(20), nullable=False, server_default="STUDY_HOURS"))
        batch.add_column(sa.Column("target_value", sa.Float(), nullable=True))
        batch.add_column(sa.Column("target_unit", sa.String(30), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch.create_check_constraint(
            "ck_student_goals_type",
            "goal_type IN ('SEMESTER', 'CPI', 'ATTENDANCE', 'PLACEMENT', 'STUDY_HOURS')",
        )
        batch.create_check_constraint(
            "ck_student_goals_target_nonneg", "target_value IS NULL OR target_value >= 0"
        )
    op.execute("UPDATE student_goals SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    with op.batch_alter_table("student_goals") as batch:
        batch.alter_column("created_at", existing_type=sa.DateTime(), nullable=False)

    op.create_table(
        "goal_milestones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("student_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("target_value IS NULL OR target_value >= 0", name="ck_goal_milestones_target_nonneg"),
    )
    op.create_index("ix_goal_milestones_student_id", "goal_milestones", ["student_id"])
    op.create_index("ix_goal_milestones_goal_id", "goal_milestones", ["goal_id"])

    op.create_table(
        "goal_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", sa.Integer(), sa.ForeignKey("student_goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("progress_value", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("progress_value >= 0", name="ck_goal_progress_nonneg"),
    )
    op.create_index("ix_goal_progress_student_id", "goal_progress", ["student_id"])
    op.create_index("ix_goal_progress_goal_id", "goal_progress", ["goal_id"])
    op.create_index("ix_goal_progress_recorded_at", "goal_progress", ["recorded_at"])

    op.create_table(
        "habits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("habit_name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("target_per_week", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "habit_name", "category", name="uq_habits_student_name_category"),
        sa.CheckConstraint("category IN ('DAILY_STUDY', 'REVISION', 'PYQ_PRACTICE', 'ATTENDANCE_CHECK', 'ASSIGNMENT_COMPLETION', 'OTHER')", name="ck_habits_category"),
        sa.CheckConstraint("target_per_week > 0 AND target_per_week <= 7", name="ck_habits_target_per_week"),
    )
    op.create_index("ix_habits_student_id", "habits", ["student_id"])

    op.create_table(
        "habit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("habit_id", sa.Integer(), sa.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("habit_id", "log_date", name="uq_habit_logs_habit_day"),
        sa.CheckConstraint("duration_minutes IS NULL OR duration_minutes >= 0", name="ck_habit_logs_duration_nonneg"),
    )
    op.create_index("ix_habit_logs_student_id", "habit_logs", ["student_id"])
    op.create_index("ix_habit_logs_habit_id", "habit_logs", ["habit_id"])
    op.create_index("ix_habit_logs_log_date", "habit_logs", ["log_date"])

    op.create_table(
        "habit_streaks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("habit_id", sa.Integer(), sa.ForeignKey("habits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consistency_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_completed_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("habit_id", name="uq_habit_streaks_habit"),
        sa.CheckConstraint("current_streak >= 0 AND longest_streak >= 0", name="ck_habit_streaks_nonneg"),
        sa.CheckConstraint("completion_rate >= 0 AND completion_rate <= 100", name="ck_habit_streaks_completion_rate"),
        sa.CheckConstraint("consistency_score >= 0 AND consistency_score <= 100", name="ck_habit_streaks_consistency_score"),
    )
    op.create_index("ix_habit_streaks_student_id", "habit_streaks", ["student_id"])
    op.create_index("ix_habit_streaks_habit_id", "habit_streaks", ["habit_id"])

    op.execute(
        "INSERT INTO habits (student_id, habit_name, category, target_per_week, active) "
        "SELECT student_id, habit_name, 'OTHER', 7, TRUE FROM student_habits "
        "GROUP BY student_id, habit_name"
    )
    op.execute(
        "INSERT INTO habit_streaks (student_id, habit_id, current_streak, longest_streak, completion_rate, consistency_score) "
        "SELECT old.student_id, new.id, MAX(old.streak), MAX(old.streak), "
        "AVG(old.completion_rate), AVG(old.completion_rate) "
        "FROM student_habits AS old JOIN habits AS new "
        "ON new.student_id = old.student_id AND new.habit_name = old.habit_name AND new.category = 'OTHER' "
        "GROUP BY old.student_id, new.id"
    )

    op.create_table(
        "student_connectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connector_type", sa.String(60), nullable=False),
        sa.Column("endpoint_url", sa.String(500), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="READY"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "connector_type", name="uq_student_connectors_type"),
        sa.CheckConstraint("status IN ('READY', 'SYNCING', 'ERROR', 'DISABLED')", name="ck_student_connectors_status"),
    )
    op.create_index("ix_student_connectors_student_id", "student_connectors", ["student_id"])

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connector_id", sa.Integer(), sa.ForeignKey("student_connectors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="QUEUED"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')", name="ck_sync_jobs_status"),
    )
    op.create_index("ix_sync_jobs_student_id", "sync_jobs", ["student_id"])
    op.create_index("ix_sync_jobs_connector_id", "sync_jobs", ["connector_id"])
    op.create_index("ix_sync_jobs_scheduled_at", "sync_jobs", ["scheduled_at"])

    op.create_table(
        "sync_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connector_id", sa.Integer(), sa.ForeignKey("student_connectors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('SUCCEEDED', 'FAILED')", name="ck_sync_history_status"),
    )
    op.create_index("ix_sync_history_student_id", "sync_history", ["student_id"])
    op.create_index("ix_sync_history_connector_id", "sync_history", ["connector_id"])


def downgrade():
    for table in ("sync_history", "sync_jobs", "student_connectors", "habit_streaks", "habit_logs", "habits", "goal_progress", "goal_milestones"):
        op.drop_table(table)
    with op.batch_alter_table("study_blocks") as batch:
        batch.drop_constraint("ck_study_blocks_type", type_="check")
        batch.drop_column("block_type")
        batch.drop_column("title")
    with op.batch_alter_table("student_goals") as batch:
        batch.drop_constraint("ck_student_goals_target_nonneg", type_="check")
        batch.drop_constraint("ck_student_goals_type", type_="check")
        batch.drop_column("created_at")
        batch.drop_column("target_unit")
        batch.drop_column("target_value")
        batch.drop_column("goal_type")
