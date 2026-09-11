"""admin workflow v2

Revision ID: f4a2c8d17b63
Revises: e13f7a2c9b41
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a2c8d17b63"
down_revision: Union[str, Sequence[str], None] = "e13f7a2c9b41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("appeals") as batch_op:
        batch_op.add_column(sa.Column("claim_expires_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_appeals_claim_expires_at", ["claim_expires_at"], unique=False)

    with op.batch_alter_table("suggestions") as batch_op:
        batch_op.add_column(sa.Column("reviewed_by", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_suggestions_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("suggestions") as batch_op:
        batch_op.drop_index("ix_suggestions_status")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")

    with op.batch_alter_table("appeals") as batch_op:
        batch_op.drop_index("ix_appeals_claim_expires_at")
        batch_op.drop_column("claim_expires_at")
