import os
from sqlalchemy import create_engine, text
from config import get_settings

# Create the engine to connect to PostgreSQL (without specifying the database)
engine = create_engine(get_settings().DATABASE_URL,
                       isolation_level="AUTOCOMMIT", pool_pre_ping=True)

# Function to create the database if it does not exist


def create_database():
    try:
        with engine.connect() as connection:
            if os.getenv("ENV") == "test":
                print("Skipping database bootstrap in test environment.")
                return

            db_name = get_settings().DATABASE_NAME
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": db_name},
            ).scalar()

            if exists:
                print(f"Database '{db_name}' already exists. Skipping creation.")
                return

            connection.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"Database '{db_name}' created successfully.")
    except Exception as e:
        print(f"Error: {e}")


# Main execution to create the database and tables
if __name__ == "__main__":
    # Create the database if it does not exist
    create_database()
