"""add source metadata to SVNIT MIS snapshots

Revision ID: a8d4e2c6f901
Revises: b9d72e4c1a63
Create Date: 2026-10-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a8d4e2c6f901"
down_revision = "b9d72e4c1a63"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("mis_student_profiles") as batch:
        batch.add_column(sa.Column("synced_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("source_page", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("attendance_raw_json", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("attendance_synced_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("attendance_source_page", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("results_raw_json", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("results_synced_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("results_source_page", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("timetable_raw_json", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("timetable_synced_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("timetable_source_page", sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table("mis_student_profiles") as batch:
        batch.drop_column("timetable_source_page")
        batch.drop_column("timetable_synced_at")
        batch.drop_column("timetable_raw_json")
        batch.drop_column("results_source_page")
        batch.drop_column("results_synced_at")
        batch.drop_column("results_raw_json")
        batch.drop_column("attendance_source_page")
        batch.drop_column("attendance_synced_at")
        batch.drop_column("attendance_raw_json")
        batch.drop_column("source_page")
        batch.drop_column("synced_at")
