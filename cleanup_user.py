import asyncio
import asyncpg
from config import config


async def cleanup_user(telegram_id: int):
    """Удалить пользователя по telegram_id"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        # Сначала удаляем связанные записи
        await conn.execute("DELETE FROM likes WHERE user_id IN (SELECT id FROM users WHERE telegram_id = $1)",
                           telegram_id)
        await conn.execute("DELETE FROM profile_views WHERE viewer_id IN (SELECT id FROM users WHERE telegram_id = $1)",
                           telegram_id)
        await conn.execute(
            "DELETE FROM profile_views WHERE viewed_user_id IN (SELECT id FROM users WHERE telegram_id = $1)",
            telegram_id)

        # Удаляем пользователя
        result = await conn.execute("DELETE FROM users WHERE telegram_id = $1", telegram_id)

        if "DELETE 1" in result:
            print(f"✅ Пользователь с telegram_id={telegram_id} удален")
        else:
            print(f"⚠️ Пользователь с telegram_id={telegram_id} не найден")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    telegram_id = 750540476  # Замените на ваш telegram_id
    asyncio.run(cleanup_user(telegram_id))