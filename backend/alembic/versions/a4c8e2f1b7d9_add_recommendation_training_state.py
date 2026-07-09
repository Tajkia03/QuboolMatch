"""add recommendation training state

Revision ID: a4c8e2f1b7d9
Revises: 9e7c6b5a4d3f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a4c8e2f1b7d9"
down_revision: Union[str, None] = "9e7c6b5a4d3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("recommendation_training_state"):
        op.create_table(
            "recommendation_training_state",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("requested_generation", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("completed_generation", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("status", sa.Text(), nullable=False, server_default="idle"),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.PrimaryKeyConstraint("id"),
        )
    op.execute(
        "INSERT INTO recommendation_training_state "
        "(id, requested_generation, completed_generation, status) "
        "VALUES (1, 0, 0, 'idle') ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("recommendation_training_state")
