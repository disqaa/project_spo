import asyncio
import multiprocessing
import threading
import time
import logging
import sys
import os
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_web_server():
    logger.info("🌐 Запуск веб-сервера...")
    import uvicorn
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )


def run_bot():
    logger.info("🤖 Запуск Telegram бота...")
    import asyncio
    from main import main as bot_main
    asyncio.run(bot_main())


def run_ngrok():
    try:
        logger.info("🔗 Запуск ngrok...")
        # Запускаем ngrok в отдельном процессе
        process = subprocess.Popen(
            ['ngrok', 'http', '8000', '--region=eu'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        time.sleep(5)

        try:
            import requests
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])
                if tunnels:
                    for tunnel in tunnels:
                        if tunnel['proto'] == 'https':
                            public_url = tunnel['public_url']
                            logger.info(f"✅ Ngrok запущен: {public_url}")

                            # Сохраняем URL
                            with open('ngrok_url.txt', 'w') as f:
                                f.write(f"Public URL: {public_url}\n")
                                f.write(f"Mini App URL: {public_url}/mini\n")

                            # Обновляем .env файл
                            from dotenv import set_key
                            set_key('.env', 'MINI_APP_URL', public_url)

                            return public_url
        except:
            logger.warning("⚠️ Не удалось получить URL от ngrok")

        return None

    except Exception as e:
        logger.error(f"❌ Ошибка запуска ngrok: {e}")
        return None


async def main():
    logger.info("🚀 Запуск системы MeetMap...")

    # 1. Проверяем наличие ngrok
    ngrok_url = run_ngrok()

    # 2. Запускаем веб-сервер в отдельном процессе
    logger.info("1. Запуск веб-сервера...")
    web_process = multiprocessing.Process(target=run_web_server, daemon=True)
    web_process.start()

    # Ждем запуска веб-сервера
    time.sleep(3)

    # 3. Запускаем бота в основном потоке
    logger.info("2. Запуск Telegram бота...")

    try:
        import asyncio
        from main import main as bot_main

        # Запускаем бота
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