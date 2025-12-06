import asyncio
import asyncpg
from config import config


async def list_all_users():
    """Вывести список всех пользователей"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        users = await conn.fetch(
            "SELECT id, telegram_id, username, first_name, age, is_authenticated, created_at FROM users ORDER BY id")

        print("📋 Список пользователей:")
        print("-" * 80)
        for user in users:
            print(f"ID: {user['id']}")
            print(f"Telegram ID: {user['telegram_id']}")
            print(f"Логин: {user['username']}")
            print(f"Имя: {user['first_name']}")
            print(f"Возраст: {user['age']}")
            print(f"Авторизован: {'✅' if user['is_authenticated'] else '❌'}")
            print(f"Создан: {user['created_at']}")
            print("-" * 80)

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(list_all_users())