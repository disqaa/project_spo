import asyncio
import asyncpg
import logging
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def drop_all_tables():
    """Удалить все таблицы из базы данных"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        logger.info("🗑️  Удаление всех таблиц...")

        # Получаем список всех таблиц
        tables = await conn.fetch('''
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'pg_%'
            AND tablename NOT LIKE 'sql_%'
        ''')

        # Отключаем внешние ключи для безопасного удаления
        await conn.execute('SET session_replication_role = replica;')

        # Удаляем таблицы в правильном порядке (сначала зависимые)
        drop_order = [
            'meeting_participants',
            'place_meetings',
            'places',
            'matches',
            'profile_views',
            'search_filters',
            'likes',
            'users'
        ]

        for table_name in drop_order:
            try:
                await conn.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE;')
                logger.info(f"✅ Таблица {table_name} удалена")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось удалить таблицу {table_name}: {e}")

        # Включаем внешние ключи обратно
        await conn.execute('SET session_replication_role = origin;')

        await conn.close()
        logger.info("✅ Все таблицы удалены")

    except Exception as e:
        logger.error(f"❌ Ошибка при удалении таблиц: {e}")
        raise


async def create_tables():
    """Создать все таблицы с новой структурой"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        logger.info("🗃️  Создание новых таблиц...")

        # Таблица users
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
        logger.info("✅ Таблица users создана")

        # Таблица likes
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS likes (
                id SERIAL PRIMARY KEY,
                from_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                to_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            )
        ''')
        logger.info("✅ Таблица likes создана")

        # Таблица profile_views
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS profile_views (
                id SERIAL PRIMARY KEY,
                viewer_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                viewed_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(viewer_id, viewed_user_id)
            )
        ''')
        logger.info("✅ Таблица profile_views создана")

        # Таблица search_filters
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS search_filters (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                interest VARCHAR(50),
                location VARCHAR(255),
                time_period VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')
        logger.info("✅ Таблица search_filters создана")

        # Таблица matches
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS matches (
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
        logger.info("✅ Таблица matches создана")

        # Таблица places
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS places (
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
        logger.info("✅ Таблица places создана")

        # Таблица place_meetings
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS place_meetings (
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
        logger.info("✅ Таблица place_meetings создана")

        # Таблица meeting_participants
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS meeting_participants (
                id SERIAL PRIMARY KEY,
                meeting_id INTEGER NOT NULL REFERENCES place_meetings(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                status VARCHAR(50) DEFAULT 'pending',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(meeting_id, user_id)
            )
        ''')
        logger.info("✅ Таблица meeting_participants создана")

        # Создаем индексы для производительности
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_users_is_published ON users(is_published) WHERE is_published = TRUE;
            CREATE INDEX IF NOT EXISTS idx_users_is_authenticated ON users(is_authenticated) WHERE is_authenticated = TRUE;
            CREATE INDEX IF NOT EXISTS idx_likes_from_user ON likes(from_user_id);
            CREATE INDEX IF NOT EXISTS idx_likes_to_user ON likes(to_user_id);
            CREATE INDEX IF NOT EXISTS idx_profile_views_viewer ON profile_views(viewer_id);
            CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
            CREATE INDEX IF NOT EXISTS idx_matches_from_user ON matches(from_user_id);
            CREATE INDEX IF NOT EXISTS idx_matches_to_user ON matches(to_user_id);
            CREATE INDEX IF NOT EXISTS idx_places_location ON places(latitude, longitude);
            CREATE INDEX IF NOT EXISTS idx_places_category ON places(category);
            CREATE INDEX IF NOT EXISTS idx_place_meetings_time ON place_meetings(meeting_time);
            CREATE INDEX IF NOT EXISTS idx_place_meetings_status ON place_meetings(status) WHERE status = 'active';
            CREATE INDEX IF NOT EXISTS idx_meeting_participants_meeting ON meeting_participants(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_meeting_participants_user ON meeting_participants(user_id);
        ''')
        logger.info("✅ Индексы созданы")

        await conn.close()
        logger.info("✅ Все таблицы успешно созданы")

    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise


async def add_sample_data():
    """Добавить тестовые данные"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        logger.info("📝 Добавление тестовых данных...")

        # Добавляем тестовые заведения (Москва)
        sample_places = [
            {
                'name': 'Starbucks Coffee',
                'address': 'ул. Тверская, 12, Москва',
                'latitude': 55.7602,
                'longitude': 37.6085,
                'category': 'cafe',
                'description': 'Кофейня с уютной атмосферой и бесплатным Wi-Fi',
                'opening_hours': '08:00-23:00',
                'rating': 4.5
            },
            {
                'name': 'Кинотеатр Октябрь',
                'address': 'Новый Арбат, 24, Москва',
                'latitude': 55.7517,
                'longitude': 37.5866,
                'category': 'cinema',
                'description': 'Современный кинотеатр с 7 залами и 4K проекцией',
                'opening_hours': '10:00-02:00',
                'rating': 4.7
            },
            {
                'name': 'Фитнес клуб World Class',
                'address': 'ул. Маросейка, 6/8, Москва',
                'latitude': 55.7588,
                'longitude': 37.6353,
                'category': 'sport',
                'description': 'Премиальный фитнес клуб с бассейном и спа',
                'opening_hours': '06:00-24:00',
                'rating': 4.8
            },
            {
                'name': 'Бар Правила Игры',
                'address': 'Кузнецкий Мост, 7, Москва',
                'latitude': 55.7616,
                'longitude': 37.6213,
                'category': 'bar',
                'description': 'Бар с настольными играми и коктейлями',
                'opening_hours': '14:00-05:00',
                'rating': 4.6
            },
            {
                'name': 'Книжный магазин Библио-Глобус',
                'address': 'Мясницкая ул., 6/3, Москва',
                'latitude': 55.7620,
                'longitude': 37.6302,
                'category': 'books',
                'description': 'Крупнейший книжный магазин с читальным залом',
                'opening_hours': '09:00-22:00',
                'rating': 4.9
            },
            {
                'name': 'Парк Горького',
                'address': 'Крымский Вал, 9, Москва',
                'latitude': 55.7285,
                'longitude': 37.6021,
                'category': 'park',
                'description': 'Центральный парк для прогулок и активного отдыха',
                'opening_hours': 'круглосуточно',
                'rating': 4.8
            },
            {
                'name': 'Ресторан White Rabbit',
                'address': 'Смоленская площадь, 3, Москва',
                'latitude': 55.7486,
                'longitude': 37.5843,
                'category': 'restaurant',
                'description': 'Ресторан с панорамным видом на город',
                'opening_hours': '12:00-01:00',
                'rating': 4.9
            },
            {
                'name': 'Библиотека им. Ленина',
                'address': 'ул. Воздвиженка, 3/5, Москва',
                'latitude': 55.7504,
                'longitude': 37.6095,
                'category': 'library',
                'description': 'Крупнейшая публичная библиотека',
                'opening_hours': '09:00-21:00',
                'rating': 4.7
            },
            {
                'name': 'Музей современного искусства',
                'address': 'ул. Петровка, 25, Москва',
                'latitude': 55.7645,
                'longitude': 37.6180,
                'category': 'museum',
                'description': 'Выставки современного искусства и фотографии',
                'opening_hours': '12:00-21:00',
                'rating': 4.5
            },
            {
                'name': 'Кофейня Double B',
                'address': 'ул. Большая Дмитровка, 32, Москва',
                'latitude': 55.7610,
                'longitude': 37.6155,
                'category': 'cafe',
                'description': 'Спешелти кофейня с обжаркой на месте',
                'opening_hours': '07:00-23:00',
                'rating': 4.8
            }
        ]

        for place in sample_places:
            try:
                await conn.execute('''
                    INSERT INTO places (name, address, latitude, longitude, category, description, opening_hours, rating)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ''',
                                   place['name'], place['address'], place['latitude'], place['longitude'],
                                   place['category'], place['description'], place['opening_hours'], place['rating']
                                   )
                logger.info(f"✅ Добавлено заведение: {place['name']}")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось добавить {place['name']}: {e}")

        # Добавляем тестового пользователя
        try:
            await conn.execute('''
                INSERT INTO users (telegram_id, username, password, first_name, age, is_authenticated, is_published, telegram_real_username)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ''',
                               123456789, 'testuser', 'salt:hashed_password', 'Тестовый Пользователь', 25, True, True,
                               'testuser_telegram'
                               )
            logger.info("✅ Добавлен тестовый пользователь")
        except Exception as e:
            logger.warning(f"⚠️  Не удалось добавить тестового пользователя: {e}")

        await conn.close()
        logger.info("✅ Тестовые данные добавлены")

    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении тестовых данных: {e}")


async def verify_tables():
    """Проверить, что все таблицы созданы"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        logger.info("🔍 Проверка структуры базы данных...")

        tables = await conn.fetch('''
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        ''')

        expected_tables = [
            'users', 'likes', 'profile_views', 'search_filters',
            'matches', 'places', 'place_meetings', 'meeting_participants'
        ]

        created_tables = [table['tablename'] for table in tables]

        logger.info("📋 Созданные таблицы:")
        for table in created_tables:
            logger.info(f"  • {table}")

        missing_tables = set(expected_tables) - set(created_tables)
        if missing_tables:
            logger.error(f"❌ Отсутствуют таблицы: {missing_tables}")
            return False

        # Проверяем структуру таблицы users
        users_columns = await conn.fetch('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        ''')

        logger.info("\n📊 Структура таблицы users:")
        for col in users_columns:
            logger.info(f"  • {col['column_name']} ({col['data_type']})")

        await conn.close()
        logger.info("✅ Проверка завершена успешно")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка при проверке: {e}")
        return False


async def backup_database():
    """Создать резервную копию базы данных (опционально)"""
    import subprocess
    import os
    from datetime import datetime

    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")

    logger.info(f"💾 Создание резервной копии в {backup_file}...")

    try:
        # Используем pg_dump для создания резервной копии
        env = os.environ.copy()
        env['PGPASSWORD'] = config.DB_PASSWORD

        cmd = [
            'pg_dump',
            '-h', config.DB_HOST,
            '-p', config.DB_PORT,
            '-U', config.DB_USER,
            '-d', config.DB_NAME,
            '-f', backup_file,
            '--clean',  # Добавляет команды DROP перед CREATE
            '--if-exists'
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info(f"✅ Резервная копия создана: {backup_file}")
            return backup_file
        else:
            logger.error(f"❌ Ошибка создания резервной копии: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"❌ Ошибка при создании резервной копии: {e}")
        return None


async def main():
    """Основная функция миграции"""
    import sys

    print("\n" + "=" * 60)
    print("🚀 МИГРАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 60)
    print("\n⚠️  ВНИМАНИЕ: Все существующие данные будут удалены!")

    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        confirm = "yes"
    else:
        confirm = input("\nПродолжить? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("❌ Миграция отменена")
        return

    try:
        # Создаем резервную копию
        print("\n1. Создание резервной копии...")
        backup_file = await backup_database()
        if backup_file:
            print(f"   ✅ Резервная копия: {backup_file}")

        # Удаляем старые таблицы
        print("\n2. Удаление старых таблиц...")
        await drop_all_tables()

        # Создаем новые таблицы
        print("\n3. Создание новых таблиц...")
        await create_tables()

        # Добавляем тестовые данные
        print("\n4. Добавление тестовых данных...")
        add_test_data = input("Добавить тестовые данные? (yes/no): ").strip().lower()
        if add_test_data == "yes":
            await add_sample_data()

        # Проверяем создание таблиц
        print("\n5. Проверка структуры базы...")
        if await verify_tables():
            print("\n✅ МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
            print("\n📋 Следующие таблицы созданы:")
            print("   • users - Пользователи")
            print("   • likes - Лайки")
            print("   • profile_views - Просмотры профилей")
            print("   • search_filters - Фильтры поиска")
            print("   • matches - Встречи")
            print("   • places - Заведения")
            print("   • place_meetings - Встречи в заведениях")
            print("   • meeting_participants - Участники встреч")
        else:
            print("\n❌ МИГРАЦИЯ ЗАВЕРШИЛАСЬ С ОШИБКАМИ")

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        if backup_file:
            print(f"\n💾 Для восстановления используйте команду:")
            print(
                f"   psql -h {config.DB_HOST} -p {config.DB_PORT} -U {config.DB_USER} -d {config.DB_NAME} -f {backup_file}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())