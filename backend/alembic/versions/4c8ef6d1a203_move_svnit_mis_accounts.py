"""move SVNIT MIS connection state out of generic connectors

Revision ID: 4c8ef6d1a203
Revises: c8d1f7a4b209
Create Date: 2026-10-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "4c8ef6d1a203"
down_revision = "c8d1f7a4b209"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mis_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("endpoint_url", sa.String(length=500), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="READY", nullable=False),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('READY', 'SYNCING', 'ERROR', 'DISABLED')",
            name="ck_mis_accounts_status",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_mis_accounts_student"),
    )
    op.create_index("ix_mis_accounts_id", "mis_accounts", ["id"])
    op.create_index("ix_mis_accounts_student_id", "mis_accounts", ["student_id"])

    connection = op.get_bind()
    connectors = sa.table(
        "student_connectors",
        sa.column("student_id", sa.Integer()),
        sa.column("connector_type", sa.String()),
        sa.column("endpoint_url", sa.String()),
        sa.column("encrypted_credentials", sa.Text()),
        sa.column("configuration", sa.JSON()),
        sa.column("enabled", sa.Boolean()),
        sa.column("sync_interval_minutes", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("last_sync_at", sa.DateTime()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    accounts = sa.table(
        "mis_accounts",
        sa.column("student_id", sa.Integer()),
        sa.column("endpoint_url", sa.String()),
        sa.column("encrypted_credentials", sa.Text()),
        sa.column("configuration", sa.JSON()),
        sa.column("enabled", sa.Boolean()),
        sa.column("sync_interval_minutes", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("last_sync_at", sa.DateTime()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    connector_rows = connection.execute(
        sa.select(
            connectors.c.student_id,
            connectors.c.endpoint_url,
            connectors.c.encrypted_credentials,
            connectors.c.configuration,
            connectors.c.enabled,
            connectors.c.sync_interval_minutes,
            connectors.c.status,
            connectors.c.last_sync_at,
            connectors.c.created_at,
            connectors.c.updated_at,
        ).where(connectors.c.connector_type == "svnit_mis")
    ).mappings()
    for row in connector_rows:
        connection.execute(accounts.insert().values(**dict(row)))


def downgrade():
    connection = op.get_bind()
    accounts = sa.table(
        "mis_accounts",
        sa.column("student_id", sa.Integer()),
        sa.column("endpoint_url", sa.String()),
        sa.column("encrypted_credentials", sa.Text()),
        sa.column("configuration", sa.JSON()),
        sa.column("enabled", sa.Boolean()),
        sa.column("sync_interval_minutes", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("last_sync_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    connectors = sa.table(
        "student_connectors",
        sa.column("student_id", sa.Integer()),
        sa.column("connector_type", sa.String()),
        sa.column("endpoint_url", sa.String()),
        sa.column("encrypted_credentials", sa.Text()),
        sa.column("configuration", sa.JSON()),
        sa.column("enabled", sa.Boolean()),
        sa.column("sync_interval_minutes", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("last_sync_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    account_rows = connection.execute(
        sa.select(
            accounts.c.student_id,
            accounts.c.endpoint_url,
            accounts.c.encrypted_credentials,
            accounts.c.configuration,
            accounts.c.enabled,
            accounts.c.sync_interval_minutes,
            accounts.c.status,
            accounts.c.last_sync_at,
            accounts.c.updated_at,
        )
    ).mappings()
    for row in account_rows:
        connection.execute(
            connectors.update()
            .where(
                connectors.c.student_id == row["student_id"],
                connectors.c.connector_type == "svnit_mis",
            )
            .values(
                endpoint_url=row["endpoint_url"],
                encrypted_credentials=row["encrypted_credentials"],
                configuration=row["configuration"],
                enabled=row["enabled"],
                sync_interval_minutes=row["sync_interval_minutes"],
                status=row["status"],
                last_sync_at=row["last_sync_at"],
                updated_at=row["updated_at"],
            )
        )
    op.drop_index("ix_mis_accounts_student_id", table_name="mis_accounts")
    op.drop_index("ix_mis_accounts_id", table_name="mis_accounts")
    op.drop_table("mis_accounts")
