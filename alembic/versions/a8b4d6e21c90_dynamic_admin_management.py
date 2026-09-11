"""dynamic admin management

Revision ID: a8b4d6e21c90
Revises: f4a2c8d17b63
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a8b4d6e21c90"
down_revision: Union[str, Sequence[str], None] = "f4a2c8d17b63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_admins",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('SUPERADMIN', 'ADMIN')", name="ck_bot_admins_role"),
        sa.UniqueConstraint("telegram_id", name="uq_bot_admins_telegram_id"),
    )
    op.create_index("ix_bot_admins_telegram_id", "bot_admins", ["telegram_id"], unique=False)
    op.create_index("ix_bot_admins_role", "bot_admins", ["role"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bot_admins_role", table_name="bot_admins")
    op.drop_index("ix_bot_admins_telegram_id", table_name="bot_admins")
    op.drop_table("bot_admins")
