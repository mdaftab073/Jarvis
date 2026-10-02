"""add persisted chat sessions and messages

Revision ID: c8e2f14a9d30
Revises: f7c3a1d9b620
Create Date: 2026-10-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c8e2f14a9d30"
down_revision = "f7c3a1d9b620"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New chat"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_sessions_student_id", "chat_sessions", ["student_id"])
    op.create_index("ix_chat_sessions_id", "chat_sessions", ["id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="ck_chat_messages_role"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
    op.create_index("ix_chat_messages_id", "chat_messages", ["id"])


def downgrade():
    op.drop_index("ix_chat_messages_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_student_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")