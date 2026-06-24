"""add father and mother name to profiles table

Revision ID: 2f4a9e1b7c33
Revises: a8f2d1c4e5b6
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f4a9e1b7c33"
down_revision: Union[str, None] = "a8f2d1c4e5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("father_name", sa.String(), nullable=True))
    op.add_column("profiles", sa.Column("mother_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "mother_name")
    op.drop_column("profiles", "father_name")
