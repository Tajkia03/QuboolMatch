"""add living arrangement comment to profiles

Revision ID: c3b8f9a1d2e4
Revises: 1a8075c9f785
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3b8f9a1d2e4"
down_revision: Union[str, None] = "1a8075c9f785"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("living_arrangement_comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "living_arrangement_comment")
