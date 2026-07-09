import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

from main import app
from database import Base, get_db
from config import get_settings
from unittest.mock import patch, MagicMock

# Configure test database connection
DATABASE = f"{get_settings().DATABASE_URL}{get_settings().DATABASE_NAME}"
DATABASE_NAME = get_settings().DATABASE_NAME

# Never allow pytest's create/drop lifecycle to point at an application
# database.  Set ENV=test and use a database whose name clearly ends in
# "_test" before running the suite.
if not DATABASE_NAME.lower().endswith("_test"):
    raise RuntimeError(
        f"Refusing to run destructive pytest fixtures against database "
        f"'{DATABASE_NAME}'. Set ENV=test and DATABASE_NAME to a dedicated "
        "database ending in '_test'."
    )

engine = create_engine(DATABASE)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture to create and drop tables in the test database
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create the test database schema at the start of the session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# Fixture for providing a new session for each test
@pytest.fixture(scope="function")
def db_session():
    """Provides a transactional session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

# Fixture to override the `get_db` dependency
@pytest.fixture(scope="function", autouse=True)
def override_get_db(db_session):
    """Override the `get_db` dependency to use the test database session."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.pop(get_db, None)

# Fixture to initialize the TestClient for FastAPI
@pytest.fixture(scope="session")
def client():
    """Provides a TestClient for making requests to the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def mock_requests_post():
    # Create a MagicMock object to mock requests.get
    with patch('requests.post') as mock_get:
        # Prepare a mock response object with necessary methods
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        yield mock_get
