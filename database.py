import asyncpg
from config import config
import os
import logging

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

            logging.info("✅ Подключение к базе данных успешно")

            async with self.pool.acquire() as conn:
                # Создаем таблицу users с полной структурой
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE,
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
                        last_search TIMESTAMP,
                        telegram_real_username VARCHAR(255)
                    )
                ''')
                logging.info("✅ Таблица users создана/проверена")

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS likes (
                        id SERIAL PRIMARY KEY,
                        from_user_id BIGINT NOT NULL REFERENCES users(id),
                        to_user_id BIGINT NOT NULL REFERENCES users(id),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(from_user_id, to_user_id)
                    )
                ''')
                print("✅ Таблица likes создана/проверена")

                # Создаем таблицу profile_views
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS profile_views (
                        id SERIAL PRIMARY KEY,
                        viewer_id BIGINT NOT NULL REFERENCES users(id),
                        viewed_user_id BIGINT NOT NULL REFERENCES users(id),
                        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(viewer_id, viewed_user_id)
                    )
                ''')
                logging.info("✅ Таблица profile_views создана/проверена")

                # Создаем таблицу search_filters
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_filters (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id),
                        interest VARCHAR(50),
                        location VARCHAR(255),
                        time_period VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id)
                    )
                ''')
                logging.info("✅ Таблица search_filters создана/проверена")

                # Обновим таблицу matches
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
                print("✅ Таблица matches создана/проверена")

                # Создаем таблицу для заведений на карте
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS venues (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        category VARCHAR(100) NOT NULL,
                        latitude DECIMAL(10, 8) NOT NULL,
                        longitude DECIMAL(11, 8) NOT NULL,
                        address TEXT,
                        description TEXT,
                        working_hours TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                logging.info("✅ Таблица venues создана/проверена")

                # Создаем таблицу для заявок на встречи на карте
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS map_meeting_requests (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id),
                        venue_id BIGINT REFERENCES venues(id),
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        meeting_time VARCHAR(100) NOT NULL,
                        max_participants INTEGER DEFAULT 2,
                        current_participants INTEGER DEFAULT 1,
                        latitude DECIMAL(10, 8),
                        longitude DECIMAL(11, 8),
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        telegram_message_id VARCHAR(100),
                        telegram_chat_id BIGINT
                    )
                ''')
                logging.info("✅ Таблица map_meeting_requests создана/проверена")

                # Создаем таблицу для участников встреч
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS map_meeting_participants (
                        id SERIAL PRIMARY KEY,
                        meeting_id BIGINT NOT NULL REFERENCES map_meeting_requests(id),
                        user_id BIGINT NOT NULL REFERENCES users(id),
                        status VARCHAR(50) DEFAULT 'pending',
                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(meeting_id, user_id)
                    )
                ''')
                logging.info("✅ Таблица map_meeting_participants создана/проверена")

            logging.info("✅ База данных инициализирована успешно")

        except Exception as e:
            logging.error(f"❌ Ошибка инициализации базы данных: {e}")
            raise


db = Database()