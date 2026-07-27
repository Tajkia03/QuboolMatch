"""add nid back side ocr fields

Revision ID: e7b9c2d4a6f8
Revises: a4c8e2f1b7d9
Create Date: 2026-07-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e7b9c2d4a6f8"
down_revision = "a4c8e2f1b7d9"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nid_back_image_data BYTEA")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nid_back_image_filename VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS nid_back_image_content_type VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_address TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ocr_blood_group VARCHAR")
    op.execute("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS address TEXT")


def downgrade():
    op.execute("ALTER TABLE profiles DROP COLUMN IF EXISTS address")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_blood_group")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ocr_address")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nid_back_image_content_type")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nid_back_image_filename")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS nid_back_image_data")
