import asyncio
import logging
import signal
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import config
from database import db
from handlers import start, auth, profile, search, activity, matches, map_handler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    logger.info(f"📞 Получен сигнал {signum}, завершаем работу...")
    sys.exit(0)

async def main():
    logger.info("🚀 Запуск системы...")

    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Инициализация базы данных
    logger.info("🗄️  Инициализация базы данных...")
    try:
        await db.init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        return

    # Инициализация бота
    logger.info("🤖 Инициализация бота...")
    try:
        bot = Bot(
            token=config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML")
        )

        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Включаем все роутеры
        dp.include_router(start.router)
        dp.include_router(auth.router)
        dp.include_router(profile.router)
        dp.include_router(activity.router)
        dp.include_router(search.router)
        dp.include_router(matches.router)
        dp.include_router(map_handler.router)

        # Удаляем вебхук
        await bot.delete_webhook(drop_pending_updates=True)

        # Выводим информацию о запуске
        logger.info("=" * 50)
        logger.info("✅ Система успешно запущена!")
        logger.info(f"🤖 Бот: @{(await bot.get_me()).username}")
        logger.info("=" * 50)
        logger.info("📝 Используйте команду /start в Telegram для начала работы")

        # Запускаем поллинг
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        logger.info("🧹 Очистка ресурсов...")
        logger.info("👋 Система остановлена")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановлено пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")