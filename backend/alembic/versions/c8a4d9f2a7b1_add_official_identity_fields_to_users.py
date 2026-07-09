"""add official identity fields to users

Revision ID: c8a4d9f2a7b1
Revises: b4c1d2e3f4a5
Create Date: 2026-06-27

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c8a4d9f2a7b1"
down_revision: Union[str, None] = "b4c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS father_name VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mother_name VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS identity_verified BOOLEAN NOT NULL DEFAULT FALSE")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS identity_verified")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS mother_name")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS father_name")
