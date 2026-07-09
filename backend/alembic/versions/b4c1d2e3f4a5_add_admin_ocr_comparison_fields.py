"""add admin ocr comparison fields

Revision ID: b4c1d2e3f4a5
Revises: e3b7c0a9d4f2
Create Date: 2026-06-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4c1d2e3f4a5"
down_revision: Union[str, None] = "e3b7c0a9d4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_name_match_score FLOAT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_name_match_status VARCHAR(30)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_nid_match BOOLEAN")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_dob_match BOOLEAN")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_review_status VARCHAR(30)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS admin_review_notes TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS admin_review_notes")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_review_status")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_dob_match")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_nid_match")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_name_match_status")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_name_match_score")
