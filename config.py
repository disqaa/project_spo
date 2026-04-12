import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "telegram_bot_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'telegram_bot_db')}"

    # Proxy (для обхода блокировок Telegram в России)
    # Форматы: socks5://user:pass@host:port  или  http://user:pass@host:port
    PROXY_URL = os.getenv("PROXY_URL", "")  # пустая строка = без прокси

    # Mini App
    MINI_APP_URL = os.getenv("MINI_APP_URL", "")

    # Web server
    WEB_SERVER_HOST = os.getenv("WEB_SERVER_HOST", "0.0.0.0")
    WEB_SERVER_PORT = int(os.getenv("WEB_SERVER_PORT", "8000"))

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    ADMIN_ID = os.getenv("ADMIN_ID", "")

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