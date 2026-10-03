"""persist encrypted SVNIT MIS session state

Revision ID: c8d1f7a4b209
Revises: a8d4e2c6f901
Create Date: 2026-10-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c8d1f7a4b209"
down_revision = "a8d4e2c6f901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mis_login_sessions",
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("encrypted_state", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_mis_login_sessions_expires_at", "mis_login_sessions", ["expires_at"])


def downgrade():
    op.drop_index("ix_mis_login_sessions_expires_at", table_name="mis_login_sessions")
    op.drop_table("mis_login_sessions")
