"""merge heads

Revision ID: 7678e5794af7
Revises: c1f2d9b8a7e6, d2f4a6b8c0d2
Create Date: 2026-05-27 16:38:11.809938

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7678e5794af7'
down_revision: Union[str, None] = ('c1f2d9b8a7e6', 'd2f4a6b8c0d2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
