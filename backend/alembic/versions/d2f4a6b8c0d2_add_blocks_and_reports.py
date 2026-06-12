"""add blocks and reports tables

Revision ID: d2f4a6b8c0d2
Revises: c9f2a1d6b3e4
Create Date: 2026-05-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d2f4a6b8c0d2"
down_revision = "c9f2a1d6b3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blocks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("blocker_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("blocked_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint("uq_blocks_blocker_blocked", "blocks", ["blocker_id", "blocked_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("reporter_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reported_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("blocks")