"""remove deprecated SVNIT MIS persistence

Revision ID: e7b4c1d9a260
Revises: 4c8ef6d1a203
Create Date: 2026-10-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e7b4c1d9a260"
down_revision = "4c8ef6d1a203"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "DELETE FROM student_connectors "
            "WHERE lower(connector_type) = 'svnit_mis'"
        )
    )
    op.drop_table("mis_login_sessions")
    op.drop_table("mis_accounts")
    op.drop_table("mis_student_profiles")


def downgrade():
    op.create_table(
        "mis_student_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("roll_no", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("program", sa.String(length=255), nullable=True),
        sa.Column("semester", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("attendance_json", sa.JSON(), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("timetable_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("source_page", sa.String(length=500), nullable=True),
        sa.Column("attendance_raw_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("attendance_synced_at", sa.DateTime(), nullable=True),
        sa.Column("attendance_source_page", sa.String(length=500), nullable=True),
        sa.Column("results_raw_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("results_synced_at", sa.DateTime(), nullable=True),
        sa.Column("results_source_page", sa.String(length=500), nullable=True),
        sa.Column("timetable_raw_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("timetable_synced_at", sa.DateTime(), nullable=True),
        sa.Column("timetable_source_page", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("student_id", name="uq_mis_student_profiles_student"),
        sa.CheckConstraint(
            "semester IS NULL OR semester >= 1",
            name="ck_mis_student_profiles_semester",
        ),
    )
    op.create_index(
        "ix_mis_student_profiles_student_id",
        "mis_student_profiles",
        ["student_id"],
    )
    op.create_index(
        "ix_mis_student_profiles_roll_no",
        "mis_student_profiles",
        ["roll_no"],
    )
    op.create_index(
        "ix_mis_student_profiles_email",
        "mis_student_profiles",
        ["email"],
    )
    op.create_table(
        "mis_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("endpoint_url", sa.String(length=500), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="READY"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("student_id", name="uq_mis_accounts_student"),
        sa.CheckConstraint(
            "status IN ('READY', 'SYNCING', 'ERROR', 'DISABLED')",
            name="ck_mis_accounts_status",
        ),
    )
    op.create_index("ix_mis_accounts_id", "mis_accounts", ["id"])
    op.create_index("ix_mis_accounts_student_id", "mis_accounts", ["student_id"])
    op.create_table(
        "mis_login_sessions",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("encrypted_state", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_id"),
    )
    op.create_index(
        "ix_mis_login_sessions_expires_at",
        "mis_login_sessions",
        ["expires_at"],
    )
