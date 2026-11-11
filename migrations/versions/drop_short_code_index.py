"""drop short_code index

Revision ID: drop_idx_01
Revises: 8a9b0c1d2e3f
Create Date: 2026-11-10
"""
from typing import Sequence, Union
from alembic import op

revision: str = "drop_idx_01"
down_revision: Union[str, Sequence[str], None] = "8a9b0c1d2e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Dropping the index automatically removes the Unique constraint that was tied to it
    op.drop_index(op.f('ix_urls_short_code'), table_name='urls')

def downgrade() -> None:
    op.create_index(op.f('ix_urls_short_code'), 'urls', ['short_code'], unique=True)