"""language, verified phone and delivery lifecycle hardening

Revision ID: d7c2f4189a6e
Revises: b9a1e47cb84b
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d7c2f4189a6e"
down_revision: Union[str, Sequence[str], None] = "b9a1e47cb84b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("phone_verification_source", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("phone_verified_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("language_code", sa.String(length=16), nullable=False, server_default="uz_cyrl"))
        batch_op.add_column(sa.Column("telegram_status", sa.String(length=20), nullable=False, server_default="ACTIVE"))
        batch_op.add_column(sa.Column("last_seen_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("unreachable_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("appeals") as batch_op:
        batch_op.add_column(sa.Column("delivery_status", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("delivery_attempted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("delivery_error_code", sa.String(length=64), nullable=True))

    with op.batch_alter_table("admin_contacts") as batch_op:
        batch_op.add_column(sa.Column("delivery_status", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("delivery_attempted_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("delivery_error_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("admin_contacts") as batch_op:
        batch_op.drop_column("delivery_error_code")
        batch_op.drop_column("delivery_attempted_at")
        batch_op.drop_column("delivery_status")

    with op.batch_alter_table("appeals") as batch_op:
        batch_op.drop_column("delivery_error_code")
        batch_op.drop_column("delivery_attempted_at")
        batch_op.drop_column("delivery_status")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("unreachable_at")
        batch_op.drop_column("last_seen_at")
        batch_op.drop_column("telegram_status")
        batch_op.drop_column("language_code")
        batch_op.drop_column("phone_verified_at")
        batch_op.drop_column("phone_verification_source")
        batch_op.drop_column("phone_verified")
