import asyncio
import asyncpg
from config import config


async def migrate_database():
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        print("✅ Подключение к базе данных успешно")

        # Добавляем новые колонки
        await conn.execute('''
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS interests TEXT,
            ADD COLUMN IF NOT EXISTS about TEXT,
            ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS last_search TIMESTAMP;
        ''')
        print("✅ Колонки добавлены в таблицу users")

        # Создаем таблицу likes
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                liked_user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, liked_user_id)
            )
        ''')
        print("✅ Таблица likes создана")

        # Создаем таблицу profile_views
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS profile_views (
                id SERIAL PRIMARY KEY,
                viewer_id INTEGER NOT NULL REFERENCES users(id),
                viewed_user_id INTEGER NOT NULL REFERENCES users(id),
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(viewer_id, viewed_user_id)
            )
        ''')
        print("✅ Таблица profile_views создана")

        # Проверяем структуру таблицы users
        columns = await conn.fetch('''
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        ''')

        print("\n📊 Текущая структура таблицы users:")
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']}")

        await conn.close()
        print("\n✅ Миграция базы данных завершена успешно!")

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")


if __name__ == "__main__":
    asyncio.run(migrate_database())