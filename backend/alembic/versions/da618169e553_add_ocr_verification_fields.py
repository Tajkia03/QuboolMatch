"""add ocr verification fields

Revision ID: da618169e553
Revises: 7678e5794af7
Create Date: 2026-06-24 04:55:14.849365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da618169e553'
down_revision: Union[str, None] = '7678e5794af7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
