# migrate_database.py
import asyncio
import asyncpg
from config import config


async def migrate_database():
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    try:
        # Переименовываем таблицу likes если нужно
        await conn.execute("DROP TABLE IF EXISTS likes CASCADE")

        # Создаем новую таблицу likes
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT NOT NULL REFERENCES users(id),
                to_user_id BIGINT NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        print("✅ Таблица likes создана")

        # Переименовываем таблицу matches если нужно
        await conn.execute("DROP TABLE IF EXISTS matches CASCADE")

        # Создаем новую таблицу matches
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT NOT NULL REFERENCES users(id),
                to_user_id BIGINT NOT NULL REFERENCES users(id),
                activity_id BIGINT REFERENCES users(id),
                status VARCHAR(50) DEFAULT 'pending',
                from_confirmed BOOLEAN DEFAULT FALSE,
                to_confirmed BOOLEAN DEFAULT FALSE,
                meeting_confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        print("✅ Таблица matches создана")

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate_database())