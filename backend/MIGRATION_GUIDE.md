# Database Migration Guide

This project uses Alembic for database schema migrations, providing a systematic way to manage database changes over time.

## Setup

### Prerequisites
- Python virtual environment activated
- PostgreSQL database running
- All dependencies installed from `requirements.txt`

### Initial Setup
1. Alembic is already initialized in this project
2. The configuration is set up in `alembic.ini` and `alembic/env.py`
3. Database URL is configured for development: `postgresql://postgres:mim123@localhost:5432/qubool`

## Using Migrations

### Quick Commands
Use the migration utility script for easier management:

```bash
# Check current migration status
python migrate.py current

# Create a new migration
python migrate.py create "Add new feature to User model"

# Apply all pending migrations
python migrate.py upgrade

# Rollback one migration
python migrate.py downgrade

# Show migration history
python migrate.py history
```

### Manual Alembic Commands
If you prefer using Alembic directly:

```bash
# Create a new migration
python -m alembic revision --autogenerate -m "Migration message"

# Apply migrations
python -m alembic upgrade head

# Check current version
python -m alembic current

# Show history
python -m alembic history
```

## Migration Workflow

### 1. Making Model Changes
1. Edit your SQLAlchemy models in `models/`
2. Import new models in `alembic/env.py` if needed
3. Create a migration to capture the changes

### 2. Creating Migrations
```bash
# Create migration with descriptive message
python migrate.py create "Add email verification fields"
```

### 3. Reviewing Migrations
- Check the generated migration file in `alembic/versions/`
- Review the `upgrade()` and `downgrade()` functions
- Modify if needed for custom logic

### Profile Page Fields
If you need to update an existing database for the profile page, run the manual migration script:

```bash
python migrations/add_profile_page_fields.py
```

This adds the new profile fields without changing the existing guardian phone number or guardian relation columns.

### Verification Cleanup
To clean up legacy verification columns from `users`, run:

```bash
alembic upgrade heads
```

This applies the migration that removes the legacy verification fields from the table.

### 4. Applying Migrations
```bash
# Apply to development database
python migrate.py upgrade

# For production, use the same command in production environment
```

## Current Database Schema

### User Table
The current `users` table includes:

**Basic Fields:**
- `id`: Primary key (VARCHAR)
- `email`: User email (VARCHAR)
- `hashed_password`: Encrypted password (VARCHAR)
- `is_deleted`: Soft delete flag (BOOLEAN)
- `is_archived`: Archive flag (BOOLEAN)
- `created_at`: Creation timestamp (TIMESTAMP)

**NID Verification Fields:**
- `nid_image_data`: Binary image data (BYTEA)
- `nid_image_filename`: Original filename (VARCHAR)
- `nid_image_content_type`: MIME type (VARCHAR)
- `verification_status`: Status (pending/in_progress/verified) (VARCHAR)
- `verification_notes`: Additional notes (TEXT)
- `verified_at`: Verification completion timestamp (TIMESTAMP)

## Environment Management

### Virtual Environment
The project uses a separate virtual environment (`venv_new`) with all required packages:
- SQLAlchemy 2.0.36
- Alembic 1.13.2
- FastAPI and dependencies
- PostgreSQL adapter

### Switching Environments
```bash
# Deactivate current environment
deactivate

# Activate project environment
venv_new\Scripts\Activate.ps1

# Install/update dependencies
pip install -r requirements.txt
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Database Connection**: Check PostgreSQL is running and credentials are correct
3. **Empty Migrations**: Usually means no schema changes detected
4. **Migration Conflicts**: Use `alembic history` to understand the migration chain

### Database Reset (Development Only)
If you need to reset the database schema:

```sql
-- Connect to PostgreSQL and drop/recreate database
DROP DATABASE IF EXISTS qubool;
CREATE DATABASE qubool;
```

Then run:
```bash
python migrate.py upgrade
```

## Production Deployment

### Best Practices
1. Always backup database before migrations
2. Test migrations on staging environment first
3. Run migrations during maintenance windows
4. Monitor for any issues after deployment

### Deployment Commands
```bash
# In production environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\Activate.ps1  # Windows

python migrate.py upgrade
```

## Files Structure

```
backend/
├── alembic/                 # Alembic configuration
│   ├── versions/           # Migration files
│   ├── env.py             # Environment configuration
│   └── script.py.mako     # Migration template
├── alembic.ini            # Alembic configuration file
├── migrate.py             # Migration utility script
├── models/                # SQLAlchemy models
│   └── user/
│       └── user.py        # User model
└── database.py            # Database configuration
```

## Advanced Usage

### Custom Migrations
For complex schema changes, you may need to edit migration files manually:

1. Generate base migration: `python migrate.py create "Custom change"`
2. Edit the generated file in `alembic/versions/`
3. Add custom SQL or Python logic to `upgrade()` and `downgrade()`
4. Test thoroughly before applying

### Data Migrations
For migrations that involve data transformation:

```python
def upgrade():
    # Schema changes
    op.add_column('users', sa.Column('new_field', sa.String(255)))
    
    # Data migration
    connection = op.get_bind()
    connection.execute(text("UPDATE users SET new_field = 'default_value'"))
```

This migration system ensures reliable, trackable database schema management throughout the project lifecycle.
