import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
from aiogram.client.default import DefaultBotProperties

from config import config
from database import db
from handlers import start, auth, profile, search, activity, matches

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await db.init_db()

    # Инициализация бота с default properties
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    # Создаем диспетчер с хранилищем состояний в памяти
    storage = MemoryStorage()
    dp = Dispatcher(
        storage=storage,
        fsm_strategy=FSMStrategy.USER_IN_CHAT
    )

    # Включаем роутеры
    dp.include_router(start.router)
    dp.include_router(auth.router)
    dp.include_router(profile.router)
    dp.include_router(activity.router)
    dp.include_router(search.router)
    dp.include_router(matches.router)  # Новый роутер для встреч

    # Удаляем вебхук (если был)
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем поллинг
    logger.info("Бот запущен!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")