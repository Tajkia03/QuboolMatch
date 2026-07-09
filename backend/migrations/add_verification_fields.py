"""
Migration script to add NID verification fields to the users table
Run this after updating the User model to add the new verification fields
"""

from sqlalchemy import create_engine, text
from config import get_settings

def migrate_add_verification_fields():
    """Add verification fields to users table if they don't exist"""
    
    engine = create_engine(get_settings().DATABASE_URL.replace(
        f"/{get_settings().DATABASE_NAME}", 
        f"/{get_settings().DATABASE_NAME}"
    ))
    
    migration_queries = [
        """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS nid_image_path VARCHAR,
        ADD COLUMN IF NOT EXISTS verification_status VARCHAR DEFAULT 'pending',
        ADD COLUMN IF NOT EXISTS verification_notes TEXT,
        ADD COLUMN IF NOT EXISTS verified_at TIMESTAMP;
        """,
        """
        UPDATE users 
        SET verification_status = 'pending' 
        WHERE verification_status IS NULL;
        """
    ]
    
    try:
        with engine.connect() as connection:
            for query in migration_queries:
                connection.execute(text(query))
            connection.commit()
            print("Successfully added verification fields to users table")
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate_add_verification_fields()
