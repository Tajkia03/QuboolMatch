import os
from functools import lru_cache

try:
    from dotenv import load_dotenv

    _ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(_ENV_PATH, override=False)
except Exception:
    pass

class Settings:
    """Production settings class"""
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "example_prod")
    SECRET_KEY = os.getenv("SECRET_KEY", "secret_key")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODERATION_API_KEY = os.getenv("GEMINI_MODERATION_API_KEY")

class DevSettings(Settings):
    """Development settings class"""
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mim123@localhost:5432/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "qubool")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODERATION_API_KEY = os.getenv("GEMINI_MODERATION_API_KEY")
class TestSettings(Settings):
    """Test settings class"""
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db/")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "example_test")
    GEMINI_MODERATION_API_KEY = os.getenv("GEMINI_MODERATION_API_KEY")

@lru_cache
def get_settings():
    """Return settings based on ENV variable"""
    env = os.getenv("ENV", "dev")
    if env == "test":
        return TestSettings()
    if env == "dev":
        return DevSettings()
    return Settings()  # Default to production settings
