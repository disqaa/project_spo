import asyncio
import asyncpg
import logging
from config import config
from datetime import datetime, timedelta
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clear_old_test_data():
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    try:
        logger.info("🧹 Очистка старых тестовых данных...")

        # Удаляем тестовые встречи и участников
        await conn.execute("""
            DELETE FROM map_meeting_participants 
            WHERE meeting_id IN (
                SELECT mr.id FROM map_meeting_requests mr
                JOIN users u ON u.id = mr.user_id
                WHERE u.username = 'test_meeting_user'
            )
        """)

        await conn.execute("""
            DELETE FROM map_meeting_requests 
            WHERE user_id IN (
                SELECT id FROM users WHERE username = 'test_meeting_user'
            )
        """)

        # Удаляем тестового пользователя
        await conn.execute("DELETE FROM users WHERE username = 'test_meeting_user'")

        logger.info("✅ Старые тестовые данные очищены")

    except Exception as e:
        logger.error(f"❌ Ошибка при очистке тестовых данных: {e}")
    finally:
        await conn.close()


async def add_test_venues():
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    try:
        # Тестовые заведения
        sample_venues = [
            ('Кофейня "Уют"', 'coffee', 55.7558, 37.6173,
             'ул. Примерная, 10', 'Уютная кофейня с свежей выпечкой', '08:00-23:00'),

            ('Спортзал "Энергия"', 'sports', 55.7517, 37.6178,
             'пр. Спортивный, 25', 'Современный спортзал с тренажерами', '06:00-00:00'),

            ('Кинотеатр "Звезда"', 'cinema', 55.7597, 37.6192,
             'пл. Кинотеатральная, 5', 'Новейшие фильмы в комфортных залах', '10:00-02:00'),

            ('Бар "Настолки"', 'games', 55.7535, 37.6214,
             'пер. Игровой, 3', 'Бар с большой коллекцией настольных игр', '12:00-04:00'),

            ('Парк "Центральный"', 'sports', 55.7489, 37.6087,
             'Центральный парк', 'Большой парк для прогулок и спорта', 'круглосуточно'),

            ('Кафе "Вкусный уголок"', 'coffee', 55.7612, 37.6256,
             'ул. Вкусная, 15', 'Кофе и десерты высокого качества', '09:00-22:00'),

            ('Боулинг "Страйк"', 'games', 55.7456, 37.6312,
             'ул. Развлекательная, 7', 'Боулинг-клуб с 12 дорожками', '12:00-04:00'),

            ('Тренажерный зал "Сила"', 'sports', 55.7578, 37.6134,
             'ул. Спортивная, 22', 'Тренажерный зал для всех уровней', '05:00-23:00'),

            ('Кинотеатр "Иллюзион"', 'cinema', 55.7495, 37.6351,
             'пр. Кинематографический, 18', 'Артхаусное кино и авторские показы', '11:00-01:00'),

            ('Игровой клуб "Дракон"', 'games', 55.7423, 37.6229,
             'ул. Игровая, 33', 'Настольные и компьютерные игры', '14:00-06:00')
        ]

        added_count = 0
        for venue in sample_venues:
            exists = await conn.fetchval(
                "SELECT COUNT(*) FROM venues WHERE name = $1",
                venue[0]
            )

            if not exists:
                await conn.execute('''
                    INSERT INTO venues 
                    (name, category, latitude, longitude, address, description, working_hours)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', *venue)
                added_count += 1
                logger.info(f"✅ Добавлено заведение: {venue[0]}")

        logger.info(f"✅ Всего добавлено заведений: {added_count}")

        # Добавляем тестовые встречи
        await add_test_meetings(conn)

    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении заведений: {e}")
        raise
    finally:
        await conn.close()


async def add_test_meetings(conn):
    try:
        # Получаем все заведения
        venues = await conn.fetch("""
            SELECT id, name, category, latitude, longitude 
            FROM venues 
            WHERE is_active = TRUE
        """)

        if not venues:
            logger.info("❌ Нет заведений для создания встреч")
            return

        # Создаем тестового пользователя
        test_user_id = await conn.fetchval('''
            INSERT INTO users 
            (telegram_id, username, password, first_name, age, is_authenticated)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (username) DO UPDATE SET is_authenticated = TRUE
            RETURNING id
        ''', 999999, 'test_meeting_user', 'test:test', 'Тестовый Пользователь', 25, True)

        # Тестовые встречи
        test_meetings = [
            ("Играем в настольные игры", "Ищем компанию для игры в Монополию и другие настолки", "🌆 Вечером"),
            ("Пьем кофе и общаемся", "Приглашаю за чашечкой кофе поговорить на интересные темы", "👋 Сегодня"),
            ("Смотрим новый фильм", "Хочу посмотреть новый блокбастер в компании", "📅 Завтра"),
            ("Тренировка в зале", "Ищу напарника для совместной тренировки", "🌅 Утром"),
            ("Прогулка в парке", "Предлагаю прогуляться и подышать свежим воздухом", "🌞 В выходные"),
            ("Обсуждение книг", "Любители чтения, давайте обсудим последние прочитанные книги", "🗓️ В ближайшие дни"),
            ("Играем в боулинг", "Кто хочет сыграть в боулинг? Приглашаю всех желающих!", "🌆 Вечером"),
            ("Йога в парке", "Предлагаю заняться йогой на свежем воздухе", "🌅 Утром"),
            ("Кинопоказ под открытым небом", "Смотрим классику кино на открытой площадке", "🌆 Вечером"),
            ("Настольный теннис", "Ищу партнера для игры в настольный теннис", "⏰ Любое время")
        ]

        added_meetings = 0
        for i, meeting in enumerate(test_meetings):
            venue = random.choice(venues)

            # Создаем случайные координаты рядом с заведением
            lat_offset = random.uniform(-0.005, 0.005)
            lng_offset = random.uniform(-0.005, 0.005)

            # ВАЖНО: используем lowercase для полей из базы данных
            venue_latitude = float(venue['latitude'])  # lowercase!
            venue_longitude = float(venue['longitude'])  # lowercase!

            meeting_id = await conn.fetchval('''
                INSERT INTO map_meeting_requests 
                (user_id, venue_id, title, description, meeting_time,
                 max_participants, latitude, longitude, expires_at, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            ''',
                                             test_user_id,
                                             venue['id'],
                                             meeting[0],
                                             meeting[1],
                                             meeting[2],
                                             random.randint(2, 6),
                                             venue_latitude + lat_offset,
                                             venue_longitude + lng_offset,
                                             datetime.now() + timedelta(days=random.randint(1, 7)),
                                             'active'
                                             )

            # Добавляем создателя как участника
            await conn.execute('''
                INSERT INTO map_meeting_participants (meeting_id, user_id, status)
                VALUES ($1, $2, 'accepted')
                ON CONFLICT (meeting_id, user_id) DO NOTHING
            ''', meeting_id, test_user_id)

            added_meetings += 1
            logger.info(f"✅ Добавлена встреча #{meeting_id}: {meeting[0]}")

        logger.info(f"✅ Всего добавлено встреч: {added_meetings}")

    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении встреч: {e}")
        raise


async def main():
    logger.info("🚀 Начинаем добавление тестовых данных...")

    try:
        # Очищаем старые тестовые данные (опционально)
        # await clear_old_test_data()

        await add_test_venues()
        logger.info("✅ Тестовые данные успешно добавлены!")
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении тестовых данных: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())