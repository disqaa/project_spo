import asyncio
from database import db


async def test_registration():
    """Тест регистрации"""
    await db.init_db()

    async with db.pool.acquire() as conn:
        # Проверяем таблицу
        result = await conn.fetch("SELECT * FROM users")
        print(f"Пользователей в базе: {len(result)}")

        # Показываем всех пользователей
        for user in result:
            print(f"ID: {user['id']}, Логин: {user['username']}, Имя: {user['first_name']}")


if __name__ == "__main__":
    asyncio.run(test_registration())