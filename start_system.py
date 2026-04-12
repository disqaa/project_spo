"""
start_system.py

Локально: запускает туннель + веб-сервер + бот
На Railway: запускает только веб-сервер + бот (туннель не нужен)
"""

import asyncio
import multiprocessing
import time
import logging
import sys
import os

# Фикс для Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Railway автоматически задаёт переменную RAILWAY_ENVIRONMENT
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None


def run_web_server():
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Railway задаёт PORT сам
    logger.info(f"🌐 Запуск веб-сервера на порту {port}...")
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=port,
        log_level="warning",
        reload=False,
    )


def start_tunnel_and_save_url():
    """Запускает туннель только локально."""
    from tunnel_handler import tunnel_manager

    webapp_url = tunnel_manager.start_tunnel(port=8000)

    if webapp_url:
        public_url = tunnel_manager.get_public_url()
        logger.info(f"🌐 Публичный URL: {public_url}")
        logger.info(f"📱 Mini App URL:  {webapp_url}")

        with open("tunnel_url.txt", "w") as f:
            f.write(f"Public URL: {public_url}\n")
            f.write(f"Mini App URL: {webapp_url}\n")

        try:
            from dotenv import set_key
            set_key(".env", "MINI_APP_URL", public_url)
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить .env: {e}")

        from config import config
        config.MINI_APP_URL = public_url
    else:
        logger.warning("⚠️ Туннель не запустился — мини-апп доступен только локально.")

    return webapp_url


async def main():
    if IS_RAILWAY:
        logger.info("🚀 Запуск на Railway...")
    else:
        logger.info("🚀 Запуск локально...")

    # 1. Веб-сервер
    logger.info("── 1. Запуск веб-сервера ──")
    web_process = multiprocessing.Process(target=run_web_server, daemon=True)
    web_process.start()
    time.sleep(2)

    # 2. Туннель (только локально)
    if not IS_RAILWAY:
        logger.info("── 2. Запуск Cloudflare-туннеля ──")
        start_tunnel_and_save_url()
    else:
        # На Railway URL берём из переменной окружения MINI_APP_URL
        from config import config
        if config.MINI_APP_URL:
            logger.info(f"🌐 Mini App URL (Railway): {config.MINI_APP_URL}/mini")
        else:
            logger.warning("⚠️ MINI_APP_URL не задан в переменных Railway!")

    # 3. Бот
    logger.info("── 3. Запуск Telegram-бота ──")
    try:
        from main import main as bot_main
        await bot_main()
    except KeyboardInterrupt:
        logger.info("👋 Остановлено")
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}", exc_info=True)
    finally:
        logger.info("🧹 Завершение...")
        if not IS_RAILWAY:
            from tunnel_handler import tunnel_manager
            tunnel_manager.stop_tunnel()
        if web_process.is_alive():
            web_process.terminate()
            web_process.join(timeout=5)
        logger.info("👋 Система остановлена.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)