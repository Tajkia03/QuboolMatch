"""merge all active migration heads

Revision ID: 9e7c6b5a4d3f
Revises: 0d4f5b2a9e11, 2f4a9e1b7c33, c8a4d9f2a7b1, f6a1b2c3d4e5
"""
from typing import Sequence, Union


revision: str = "9e7c6b5a4d3f"
down_revision: Union[str, tuple[str, ...], None] = (
    "0d4f5b2a9e11",
    "2f4a9e1b7c33",
    "c8a4d9f2a7b1",
    "f6a1b2c3d4e5",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge-only revision; schema changes live in its parent revisions."""


def downgrade() -> None:
    """Merge-only revision; downgrading separates the parent branches."""
