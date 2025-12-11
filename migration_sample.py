import asyncio
import asyncpg
import logging
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration():
    """Выполнить миграцию базы данных"""
    conn = None
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        logger.info("🔄 Начало миграции базы данных...")

        # 1. Удаляем существующие таблицы (в правильном порядке)
        logger.info("🗑️  Удаление старых таблиц...")

        tables_to_drop = [
            'meeting_participants',
            'place_meetings',
            'places',
            'matches',
            'profile_views',
            'search_filters',
            'likes',
            'users'
        ]

        for table in tables_to_drop:
            try:
                await conn.execute(f'DROP TABLE IF EXISTS {table} CASCADE;')
                logger.info(f"✅ Удалена таблица: {table}")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось удалить {table}: {e}")

        # 2. Создаем таблицы заново
        logger.info("🏗️  Создание новых таблиц...")

        # Создание таблицы users
        await conn.execute('''
            CREATE TABLE users (
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
        logger.info("✅ Создана таблица: users")

        # Создание таблицы likes
        await conn.execute('''
            CREATE TABLE likes (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                to_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        logger.info("✅ Создана таблица: likes")

        # Создание таблицы profile_views
        await conn.execute('''
            CREATE TABLE profile_views (
                id SERIAL PRIMARY KEY,
                viewer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                viewed_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(viewer_id, viewed_user_id)
            )
        ''')
        logger.info("✅ Создана таблица: profile_views")

        # Создание таблицы search_filters
        await conn.execute('''
            CREATE TABLE search_filters (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                interest VARCHAR(50),
                location VARCHAR(255),
                time_period VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')
        logger.info("✅ Создана таблица: search_filters")

        # Создание таблицы matches
        await conn.execute('''
            CREATE TABLE matches (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                to_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                activity_id BIGINT REFERENCES users(id),
                status VARCHAR(50) DEFAULT 'pending',
                from_confirmed BOOLEAN DEFAULT FALSE,
                to_confirmed BOOLEAN DEFAULT FALSE,
                meeting_confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        logger.info("✅ Создана таблица: matches")

        # Создание таблицы places
        await conn.execute('''
            CREATE TABLE places (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                address VARCHAR(500) NOT NULL,
                latitude DECIMAL(10, 8) NOT NULL,
                longitude DECIMAL(11, 8) NOT NULL,
                category VARCHAR(100) NOT NULL,
                description TEXT,
                opening_hours VARCHAR(200),
                phone VARCHAR(50),
                website VARCHAR(255),
                rating DECIMAL(3, 2) DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Создана таблица: places")

        # Создание таблицы place_meetings
        await conn.execute('''
            CREATE TABLE place_meetings (
                id SERIAL PRIMARY KEY,
                place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                meeting_time TIMESTAMP NOT NULL,
                description TEXT NOT NULL,
                interest VARCHAR(100) NOT NULL,
                max_participants INTEGER DEFAULT 2,
                current_participants INTEGER DEFAULT 1,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_message_id BIGINT,
                CONSTRAINT unique_user_place_time UNIQUE(user_id, place_id, meeting_time)
            )
        ''')
        logger.info("✅ Создана таблица: place_meetings")

        # Создание таблицы meeting_participants
        await conn.execute('''
            CREATE TABLE meeting_participants (
                id SERIAL PRIMARY KEY,
                meeting_id INTEGER NOT NULL REFERENCES place_meetings(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                status VARCHAR(50) DEFAULT 'pending',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(meeting_id, user_id)
            )
        ''')
        logger.info("✅ Создана таблица: meeting_participants")

        # Создание индексов
        logger.info("📊 Создание индексов...")

        await conn.execute('''
            CREATE INDEX idx_users_telegram_id ON users(telegram_id);
            CREATE INDEX idx_users_is_published ON users(is_published);
            CREATE INDEX idx_likes_from_user ON likes(from_user_id);
            CREATE INDEX idx_likes_to_user ON likes(to_user_id);
            CREATE INDEX idx_places_location ON places(latitude, longitude);
            CREATE INDEX idx_place_meetings_time ON place_meetings(meeting_time);
        ''')

        logger.info("✅ Индексы созданы")

        await conn.close()
        logger.info("🎉 Миграция успешно завершена!")

    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        if conn:
            await conn.close()
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())