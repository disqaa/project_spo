import asyncio
import logging
import sys

# ── Фикс для Windows: ProactorEventLoop ломает SSL в aiohttp ──────────────────
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ─────────────────────────────────────────────────────────────────────────────

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import config
from database import db
from handlers import start, auth, profile, search, activity, matches, map_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Запуск системы...")

    logger.info("🗄️  Инициализация базы данных...")
    try:
        await db.init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        return

    session = None
    if config.PROXY_URL:
        logger.info(f"🔀 Используем прокси: {config.PROXY_URL}")
        session = AiohttpSession(proxy=config.PROXY_URL)

    bot = None
    try:
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML"),
            session=session,
        )

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        dp.include_router(start.router)
        dp.include_router(auth.router)
        dp.include_router(profile.router)
        dp.include_router(activity.router)
        dp.include_router(search.router)
        dp.include_router(matches.router)
        dp.include_router(map_handler.router)

        await bot.delete_webhook(drop_pending_updates=True)

        me = await bot.get_me()
        logger.info("=" * 50)
        logger.info("✅ Бот успешно запущен!")
        logger.info(f"🤖 @{me.username}")
        logger.info("=" * 50)

        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        if bot:
            await bot.session.close()
        logger.info("👋 Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")