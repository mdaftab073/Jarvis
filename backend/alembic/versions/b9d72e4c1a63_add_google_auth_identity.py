"""add Google identity fields and refresh-token revocation storage

Revision ID: b9d72e4c1a63
Revises: f4a9c2d7e610
Create Date: 2026-10-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b9d72e4c1a63"
down_revision = "f4a9c2d7e610"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("google_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("full_name", sa.String(), nullable=True))
        batch.add_column(sa.Column("profile_picture", sa.String(), nullable=True))
        batch.add_column(sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_students_google_id", ["google_id"], unique=True)

    op.execute("UPDATE students SET full_name = name WHERE full_name IS NULL")
    op.create_table(
        "auth_refresh_tokens",
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti"),
    )
    op.create_index("ix_auth_refresh_tokens_student_id", "auth_refresh_tokens", ["student_id"])


def downgrade():
    op.drop_index("ix_auth_refresh_tokens_student_id", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")
    with op.batch_alter_table("students") as batch:
        batch.drop_index("ix_students_google_id")
        batch.drop_column("last_login_at")
        batch.drop_column("is_active")
        batch.drop_column("is_verified")
        batch.drop_column("profile_picture")
        batch.drop_column("full_name")
        batch.drop_column("google_id")