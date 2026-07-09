"""add canonical demo marker to users

Revision ID: f6a1b2c3d4e5
Revises: 7678e5794af7
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f6a1b2c3d4e5"
down_revision: Union[str, None] = "7678e5794af7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older seed scripts created this column directly, so tolerate that state.
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "is_demo BOOLEAN NOT NULL DEFAULT FALSE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_demo")
