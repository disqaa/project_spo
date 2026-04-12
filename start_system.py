import asyncio
import logging
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None


async def run_web_server():
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🌐 Запуск веб-сервера на порту {port}...")
    config = uvicorn.Config(
        "web_server:app",
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    from main import main as bot_main
    await bot_main()


def get_mini_app_url():
    """Возвращает корректный HTTPS URL для мини-апп."""
    url = os.getenv("MINI_APP_URL", "")
    # Убеждаемся что URL начинается с https://
    if url and not url.startswith("http"):
        url = f"https://{url}"
    return url.rstrip("/")


async def main():
    if IS_RAILWAY:
        logger.info("🚀 Запуск на Railway...")
    else:
        logger.info("🚀 Запуск локально...")

    # Устанавливаем правильный MINI_APP_URL
    from config import config as app_config
    mini_app_url = get_mini_app_url()
    if mini_app_url:
        app_config.MINI_APP_URL = mini_app_url
        logger.info(f"🌐 Mini App URL: {mini_app_url}/mini")
    else:
        logger.warning("⚠️ MINI_APP_URL не задан!")

    if IS_RAILWAY:
        # На Railway запускаем веб-сервер и бота параллельно
        logger.info("── Запуск веб-сервера и бота параллельно ──")
        await asyncio.gather(
            run_web_server(),
            run_bot(),
        )
    else:
        # Локально — запускаем туннель + веб-сервер + бот
        import multiprocessing
        import time

        logger.info("── 1. Запуск веб-сервера (локально) ──")
        import multiprocessing
        web_process = multiprocessing.Process(target=_run_web_server_sync, daemon=True)
        web_process.start()
        time.sleep(2)

        logger.info("── 2. Запуск Cloudflare-туннеля ──")
        from tunnel_handler import tunnel_manager
        webapp_url = tunnel_manager.start_tunnel(port=8000)
        if webapp_url:
            public_url = tunnel_manager.get_public_url()
            app_config.MINI_APP_URL = public_url
            logger.info(f"🌐 Публичный URL: {public_url}")
            try:
                from dotenv import set_key
                set_key(".env", "MINI_APP_URL", public_url)
            except Exception:
                pass

        logger.info("── 3. Запуск бота ──")
        try:
            await run_bot()
        finally:
            tunnel_manager.stop_tunnel()
            if web_process.is_alive():
                web_process.terminate()


def _run_web_server_sync():
    """Синхронная обёртка для запуска в отдельном процессе (локально)."""
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)