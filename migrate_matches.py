import asyncio
import asyncpg
from config import config


async def migrate_matches():
    """Добавляем таблицу для встреч"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        # Создаем таблицу matches для подтвержденных встреч
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id SERIAL PRIMARY KEY,
                user1_id INTEGER NOT NULL REFERENCES users(id),
                user2_id INTEGER NOT NULL REFERENCES users(id),
                status VARCHAR(50) DEFAULT 'pending', -- pending, accepted, rejected, cancelled
                user1_confirmed BOOLEAN DEFAULT FALSE,
                user2_confirmed BOOLEAN DEFAULT FALSE,
                meeting_confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user1_id, user2_id)
            )
        ''')

        print("✅ Таблица matches создана")

        # Добавляем колонку для счетчика лайков
        await conn.execute('''
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS likes_received_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS matches_count INTEGER DEFAULT 0;
        ''')

        print("✅ Колонки для статистики добавлены")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")


if __name__ == "__main__":
    asyncio.run(migrate_matches())