"""add ocr verification columns

Revision ID: e3b7c0a9d4f2
Revises: da618169e553
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3b7c0a9d4f2"
down_revision: Union[str, None] = "da618169e553"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ocr_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("ocr_father_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("ocr_mother_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("ocr_date_of_birth", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("ocr_nid_number", sa.String(), nullable=True))
    op.add_column("users", sa.Column("ocr_image_quality", sa.String(), nullable=True))
    op.add_column("users", sa.Column("ocr_warnings", sa.JSON(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "ocr_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("users", sa.Column("ocr_processed_at", sa.DateTime(), nullable=True))

    op.add_column("profiles", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.add_column(
        "profiles",
        sa.Column(
            "identity_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("profiles", "identity_verified")
    op.drop_column("profiles", "date_of_birth")

    op.drop_column("users", "ocr_processed_at")
    op.drop_column("users", "ocr_confirmed")
    op.drop_column("users", "ocr_warnings")
    op.drop_column("users", "ocr_image_quality")
    op.drop_column("users", "ocr_nid_number")
    op.drop_column("users", "ocr_date_of_birth")
    op.drop_column("users", "ocr_mother_name")
    op.drop_column("users", "ocr_father_name")
    op.drop_column("users", "ocr_name")
