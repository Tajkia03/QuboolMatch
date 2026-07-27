"""add email verification

Revision ID: f2a7c8d9e1b0
Revises: e7b9c2d4a6f8
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a7c8d9e1b0"
down_revision = "e7b9c2d4a6f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}

    if "email_verified" not in user_columns:
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True, server_default=sa.false()))
    if "email_verified_at" not in user_columns:
        op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL OR email_verified = FALSE")
    op.alter_column("users", "email_verified", nullable=False, server_default=sa.false())

    if not inspector.has_table("email_verification_codes"):
        op.create_table(
            "email_verification_codes",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("code_hash", sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("email_verification_codes")}
    if "ix_email_verification_codes_user_id" not in indexes:
        op.create_index("ix_email_verification_codes_user_id", "email_verification_codes", ["user_id"])
    if "ix_email_verification_codes_email" not in indexes:
        op.create_index("ix_email_verification_codes_email", "email_verification_codes", ["email"])


def downgrade() -> None:
    op.drop_index("ix_email_verification_codes_email", table_name="email_verification_codes")
    op.drop_index("ix_email_verification_codes_user_id", table_name="email_verification_codes")
    op.drop_table("email_verification_codes")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email_verified")
