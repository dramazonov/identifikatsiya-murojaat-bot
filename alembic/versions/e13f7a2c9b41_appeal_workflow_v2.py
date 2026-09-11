"""structured appeal workflow metadata

Revision ID: e13f7a2c9b41
Revises: d7c2f4189a6e
Create Date: 2026-09-11
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e13f7a2c9b41"
down_revision: Union[str, Sequence[str], None] = "d7c2f4189a6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("appeals") as batch_op:
        batch_op.add_column(sa.Column("category_code", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("subject", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("attachment_type", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("attachment_file_id", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("attachment_file_unique_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("attachment_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("attachment_size", sa.BigInteger(), nullable=True))
        batch_op.create_index("ix_appeals_category_code", ["category_code"], unique=False)
        batch_op.create_index("ix_appeals_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("appeals") as batch_op:
        batch_op.drop_index("ix_appeals_status")
        batch_op.drop_index("ix_appeals_category_code")
        batch_op.drop_column("attachment_size")
        batch_op.drop_column("attachment_name")
        batch_op.drop_column("attachment_file_unique_id")
        batch_op.drop_column("attachment_file_id")
        batch_op.drop_column("attachment_type")
        batch_op.drop_column("subject")
        batch_op.drop_column("category_code")
