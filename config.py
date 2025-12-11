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

    # WebApp configuration
    WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.ngrok.io/webapp")
    NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN", "")

    # Admin ID (optional)
    ADMIN_ID = os.getenv("ADMIN_ID", "")

    # File paths
    UPLOAD_DIR = "uploads"
    PROFILE_PHOTOS_DIR = "uploads/profile_photos"

config = Config()


# config.py - дополняем





