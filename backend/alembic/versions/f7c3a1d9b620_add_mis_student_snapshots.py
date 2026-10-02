"""add SVNIT MIS student snapshots

Revision ID: f7c3a1d9b620
Revises: e6b2d8a4c913
Create Date: 2026-10-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f7c3a1d9b620"
down_revision = "e6b2d8a4c913"
branch_labels = None
depends_on = None


def upgrade():
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
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("student_id", name="uq_mis_student_profiles_student"),
        sa.CheckConstraint("semester IS NULL OR semester >= 1", name="ck_mis_student_profiles_semester"),
    )
    op.create_index("ix_mis_student_profiles_student_id", "mis_student_profiles", ["student_id"])
    op.create_index("ix_mis_student_profiles_roll_no", "mis_student_profiles", ["roll_no"])
    op.create_index("ix_mis_student_profiles_email", "mis_student_profiles", ["email"])


def downgrade():
    op.drop_index("ix_mis_student_profiles_email", table_name="mis_student_profiles")
    op.drop_index("ix_mis_student_profiles_roll_no", table_name="mis_student_profiles")
    op.drop_index("ix_mis_student_profiles_student_id", table_name="mis_student_profiles")
    op.drop_table("mis_student_profiles")