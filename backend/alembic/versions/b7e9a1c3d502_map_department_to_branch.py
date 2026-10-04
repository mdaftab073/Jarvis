"""map legacy academic department values to branch

Revision ID: b7e9a1c3d502
Revises: a6d8f2c4b901
Create Date: 2026-10-04 00:00:00.000000
"""

from alembic import op


revision = "b7e9a1c3d502"
down_revision = "a6d8f2c4b901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE student_academic_profiles "
        "SET branch = department "
        "WHERE branch IS NULL AND department IS NOT NULL"
    )


def downgrade() -> None:
    pass
