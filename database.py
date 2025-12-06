import asyncpg
from config import config
import os

os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/profile_photos", exist_ok=True)


class Database:
    def __init__(self):
        self.pool = None

    async def init_db(self):
        """Initialize database with all required tables and columns"""
        try:
            # Connect to PostgreSQL
            self.pool = await asyncpg.create_pool(
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                host=config.DB_HOST,
                port=config.DB_PORT,
                min_size=5,
                max_size=20
            )

            print("✅ Подключение к базе данных успешно")

            async with self.pool.acquire() as conn:
                # Создаем таблицу users с полной структурой
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id INTEGER UNIQUE,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        first_name VARCHAR(255) NOT NULL,
                        age INTEGER NOT NULL,
                        interests TEXT,
                        about TEXT,
                        activity_interest VARCHAR(50),
                        activity_location VARCHAR(255),
                        activity_time VARCHAR(100),
                        activity_description TEXT,
                        photo_path VARCHAR(255),
                        photo_id VARCHAR(255),
                        is_active BOOLEAN DEFAULT TRUE,
                        is_authenticated BOOLEAN DEFAULT FALSE,
                        is_published BOOLEAN DEFAULT FALSE,
                        likes_received_count INTEGER DEFAULT 0,
                        matches_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        last_search TIMESTAMP
                    )
                ''')
                print("✅ Таблица users создана/проверена")

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
                print("✅ Таблица likes создана/проверена")

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
                print("✅ Таблица profile_views создана/проверена")

                # Создаем таблицу search_filters
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
                print("✅ Таблица search_filters создана/проверена")

                # Создаем таблицу matches для встреч
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS matches (
                        id SERIAL PRIMARY KEY,
                        user1_id INTEGER NOT NULL REFERENCES users(id),
                        user2_id INTEGER NOT NULL REFERENCES users(id),
                        status VARCHAR(50) DEFAULT 'pending',
                        user1_confirmed BOOLEAN DEFAULT FALSE,
                        user2_confirmed BOOLEAN DEFAULT FALSE,
                        meeting_confirmed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user1_id, user2_id)
                    )
                ''')
                print("✅ Таблица matches создана/проверена")

            print("✅ База данных инициализирована успешно")

        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {e}")
            raise


db = Database()