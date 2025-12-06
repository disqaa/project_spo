import asyncio
import asyncpg
from config import config


async def migrate_activity():
    """Добавляем поля для активности"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        # Добавляем новые поля в таблицу users
        await conn.execute('''
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS activity_interest VARCHAR(50),
            ADD COLUMN IF NOT EXISTS activity_location VARCHAR(255),
            ADD COLUMN IF NOT EXISTS activity_time VARCHAR(100),
            ADD COLUMN IF NOT EXISTS activity_description TEXT;
        ''')

        print("✅ Поля активности добавлены в таблицу users")

        # Создаем таблицу для сохраненных поисковых фильтров
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS search_filters (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                interest VARCHAR(50),
                location VARCHAR(255),
                time_period VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')

        print("✅ Таблица search_filters создана")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")


if __name__ == "__main__":
    asyncio.run(migrate_activity())