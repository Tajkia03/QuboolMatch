"""add profile comment columns

Revision ID: a8f2d1c4e5b6
Revises: c3b8f9a1d2e4
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8f2d1c4e5b6"
down_revision: Union[str, None] = "c3b8f9a1d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("fertility_comment", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("preferred_religion_comment", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("preferred_education_comment", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("career_support_comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "career_support_comment")
    op.drop_column("profiles", "preferred_education_comment")
    op.drop_column("profiles", "preferred_religion_comment")
    op.drop_column("profiles", "fertility_comment")
