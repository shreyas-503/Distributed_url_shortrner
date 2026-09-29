"""align short_code column length with ORM model

Revision ID: 7c3e9a1b2d4f
Revises: 0a5ae5a4a5f8
Create Date: 2026-08-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c3e9a1b2d4f"
down_revision: Union[str, Sequence[str], None] = "0a5ae5a4a5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "urls",
        "short_code",
        existing_type=sa.String(length=10),
        type_=sa.String(length=16),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "urls",
        "short_code",
        existing_type=sa.String(length=16),
        type_=sa.String(length=10),
        existing_nullable=False,
    )