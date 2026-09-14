"""append-only admin audit log

Revision ID: c3e9f7a42d11
Revises: a8b4d6e21c90
Create Date: 2026-09-14
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3e9f7a42d11"
down_revision: Union[str, Sequence[str], None] = "a8b4d6e21c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_role", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "channel IN ('TELEGRAM', 'WEB')",
            name="ck_audit_logs_channel",
        ),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_audit_logs_actor_created_at",
        "audit_logs",
        ["actor_telegram_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_action_created_at",
        "audit_logs",
        ["action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
