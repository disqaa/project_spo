import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Database configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "telegram_bot_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Create database URL for asyncpg
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")
    NGROK_REGION = os.getenv("NGROK_REGION", "eu")

    MINI_APP_URL = os.getenv("MINI_APP_URL", "")

    WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", "8000"))

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

    # Admin ID (optional)
    ADMIN_ID = os.getenv("ADMIN_ID", "750540476")

    # File paths
    UPLOAD_DIR = "uploads"
    PROFILE_PHOTOS_DIR = "uploads/profile_photos"

    @property
    def is_development(self):
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self):
        return self.ENVIRONMENT == "production"


config = Config()