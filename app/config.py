import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration with security defaults."""
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-in-prod-xyz")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-jwt-secret-key-change-in-prod-xyz")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    )
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///financial_chatbot.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Rate Limiting
    RATELIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "120 per minute")
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # Security Features
    ENABLE_STRICT_PROMPT_GUARD = os.getenv("ENABLE_STRICT_PROMPT_GUARD", "True").lower() == "true"
    MAX_CHAT_INPUT_LENGTH = int(os.getenv("MAX_CHAT_INPUT_LENGTH", "500"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in Production with HTTPS


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration with dedicated test database."""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test_financial_chatbot.db"
    RATELIMIT_ENABLED = False  # Disable rate limit in automated tests
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)


class ProductionConfig(Config):
    """Production configuration with strict security."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    # Ensure strong secrets in production
    if Config.SECRET_KEY.startswith("fallback") or "change-in-prod" in Config.SECRET_KEY:
        import warnings
        warnings.warn("PRODUCTION WARNING: Insecure SECRET_KEY detected! Set SECRET_KEY in environment variables.", RuntimeWarning)


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
