"""
Migration script to add new profile page fields without changing existing guardian fields.

This keeps the current guardian_name / guardian_contact_number / guardian_relation
columns intact and adds only the newer fields used by the updated profile page.
"""

from sqlalchemy import create_engine, text
from config import get_settings


def migrate_add_profile_page_fields():
    """Add profile page fields if they do not already exist."""

    engine = create_engine(
        get_settings().DATABASE_URL.replace(
            f"/{get_settings().DATABASE_NAME}",
            f"/{get_settings().DATABASE_NAME}"
        )
    )

    migration_queries = [
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS date_of_birth DATE;
        """,
        """
        ALTER TABLE profiles
        ADD COLUMN IF NOT EXISTS father_name VARCHAR,
        ADD COLUMN IF NOT EXISTS mother_name VARCHAR;
        """
    ]

    try:
        with engine.connect() as connection:
            for query in migration_queries:
                connection.execute(text(query))
            connection.commit()
            print("Successfully added profile page fields")
    except Exception as e:
        print(f"Migration error: {e}")


if __name__ == "__main__":
    migrate_add_profile_page_fields()
