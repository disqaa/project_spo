import asyncio
import logging
import multiprocessing
import time
import sys
import os
import requests

# Добавляем путь к текущей директории
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import main as bot_main
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_web_server():
    import uvicorn
    logger.info("🌐 Запуск веб-сервера на порту 8000...")
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        access_log=False,
        reload=False
    )


def check_web_server():
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                logger.info("✅ Веб-сервер запущен и доступен")
                return True
        except:
            if i % 3 == 0:
                logger.info(f"⏳ Ожидание запуска веб-сервера... ({i + 1}/{max_retries})")
            time.sleep(1)

    logger.error("❌ Не удалось запустить веб-сервер")
    return False


def check_ngrok():
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get('tunnels', [])
            for tunnel in tunnels:
                if tunnel['proto'] == 'https':
                    public_url = tunnel['public_url']
                    logger.info(f"✅ Ngrok туннель обнаружен: {public_url}")
                    return public_url
    except:
        return None
    return None


async def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск системы MeetMap...")

    # Проверяем, запущен ли ngrok
    ngrok_url = check_ngrok()
    if ngrok_url:
        logger.info(f"📱 Используем ngrok URL: {ngrok_url}")
        mini_app_url = f"{ngrok_url}/mini"
    else:
        if hasattr(config, 'MINI_APP_URL') and config.MINI_APP_URL:
            mini_app_url = f"{config.MINI_APP_URL}/mini"
            logger.info(f"📱 Используем URL из конфига: {mini_app_url}")
        else:
            mini_app_url = None
            logger.warning("⚠️  Ngrok не запущен. Mini App будет доступна только локально")

    # Запуск веб-сервера в отдельном процессе
    logger.info("1. Запуск веб-сервера...")
    web_process = multiprocessing.Process(target=run_web_server, daemon=True)
    web_process.start()

    # Ждем запуска веб-сервера
    if not check_web_server():
        logger.error("❌ Веб-сервер не запустился, завершаем работу")
        return

    # Устанавливаем URL в map_handler
    if mini_app_url:
        try:
            from handlers.map_handler import set_webapp_url
            set_webapp_url(mini_app_url)
            logger.info(f"✅ WebApp URL установлен: {mini_app_url}")
        except Exception as e:
            logger.warning(f"⚠️  Не удалось установить WebApp URL: {e}")

    # Запуск бота
    logger.info("2. Запуск Telegram бота...")
    try:
        await bot_main()
    except KeyboardInterrupt:
        logger.info("👋 Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        # Очистка
        logger.info("🧹 Очистка ресурсов...")

        if web_process.is_alive():
            web_process.terminate()
            web_process.join(timeout=5)

        logger.info("👋 Система остановлена")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")