"""add date_of_birth to users table

Revision ID: 7c3d2a91b4ef
Revises: c9f2a1d6b3e4
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c3d2a91b4ef"
down_revision: Union[str, None] = "c9f2a1d6b3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "date_of_birth")
