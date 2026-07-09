"""remove verification date/time and recent image columns from users table

Revision ID: 0d4f5b2a9e11
Revises: 7c3d2a91b4ef
Create Date: 2026-06-23

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0d4f5b2a9e11"
down_revision: Union[str, None] = "7c3d2a91b4ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_date")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS verification_time")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS recent_image_content_type")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS recent_image_filename")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS recent_image_data")


def downgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_date DATE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_time TIME")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS recent_image_data BYTEA")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS recent_image_filename VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS recent_image_content_type VARCHAR")
