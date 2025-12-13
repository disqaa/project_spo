# reset_db.py
import asyncio
import asyncpg
import logging
from config import config
from datetime import datetime, timedelta
import random

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseResetter:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Подключение к базе данных"""
        try:
            self.pool = await asyncpg.create_pool(
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                host=config.DB_HOST,
                port=config.DB_PORT,
                min_size=5,
                max_size=20
            )
            logger.info("✅ Подключение к базе данных успешно")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к базе данных: {e}")
            return False

    async def drop_all_data(self):
        """Удаление всех данных из таблиц (с сохранением структуры)"""
        try:
            async with self.pool.acquire() as conn:
                # Отключаем проверку внешних ключей для безопасного удаления
                await conn.execute('SET session_replication_role = replica;')

                # Удаляем данные в правильном порядке (чтобы не нарушить целостность внешних ключей)
                tables = [
                    'map_meeting_participants',
                    'map_meeting_requests',
                    'matches',
                    'likes',
                    'profile_views',
                    'search_filters',
                    'venues',
                    'users'
                ]

                for table in tables:
                    await conn.execute(f'TRUNCATE TABLE {table} CASCADE;')
                    logger.info(f"✅ Данные из таблицы {table} удалены")

                # Включаем проверку внешних ключей обратно
                await conn.execute('SET session_replication_role = DEFAULT;')

                logger.info("✅ Все данные из базы данных удалены")
                return True

        except Exception as e:
            logger.error(f"❌ Ошибка при удалении данных: {e}")
            return False

    async def create_test_users(self):
        """Создание тестовых пользователей"""
        test_users = [
            {
                'telegram_id': 100000001,
                'username': 'alex_test',
                'password': 'password123',
                'first_name': 'Алексей',
                'age': 25,
                'interests': 'Программирование, Кино, Футбол',
                'about': 'Люблю путешествовать и изучать новые технологии',
                'activity_interest': 'Кофе',
                'activity_location': 'Москва, центр',
                'activity_time': 'Выходные',
                'activity_description': 'Выпить кофе и обсудить IT новости',
                'photo_path': 'test_photo_1.jpg',
                'photo_id': 'AgACAgIAAxkBAAMRZvwbJJi1LjeL3IHxQT_6m6V8iSUAAp_QMRuU0nlIAAGvjMhYQYADAQADAgADeQADNgQ',
                'is_active': True,
                'is_authenticated': True,
                'is_published': True,
                'likes_received_count': 5,
                'matches_count': 2,
                'telegram_real_username': 'alex_real'
            },
            {
                'telegram_id': 100000002,
                'username': 'maria_test',
                'password': 'password123',
                'first_name': 'Мария',
                'age': 23,
                'interests': 'Искусство, Фотография, Йога',
                'about': 'Фотограф, люблю искусство и здоровый образ жизни',
                'activity_interest': 'Искусство',
                'activity_location': 'Санкт-Петербург',
                'activity_time': 'Вечер',
                'activity_description': 'Сходить на выставку современного искусства',
                'photo_path': 'test_photo_2.jpg',
                'photo_id': 'AgACAgIAAxkBAAMRZvwbJJi1LjeL3IHxQT_6m6V8iSUAAp_QMRuU0nlIAAGvjMhYQYADAQADAgADeAADNgQ',
                'is_active': True,
                'is_authenticated': True,
                'is_published': True,
                'likes_received_count': 8,
                'matches_count': 3,
                'telegram_real_username': 'maria_real'
            },
            {
                'telegram_id': 100000003,
                'username': 'ivan_test',
                'password': 'password123',
                'first_name': 'Иван',
                'age': 28,
                'interests': 'Спорт, Путешествия, Музыка',
                'about': 'Спортсмен, музыкант, искатель приключений',
                'activity_interest': 'Спорт',
                'activity_location': 'Казань',
                'activity_time': 'Утро',
                'activity_description': 'Пробежка в парке',
                'photo_path': 'test_photo_3.jpg',
                'photo_id': 'AgACAgIAAxkBAAMRZvwbJJi1LjeL3IHxQT_6m6V8iSUAAp_QMRuU0nlIAAGvjMhYQYADAQADAgADdwADNgQ',
                'is_active': True,
                'is_authenticated': True,
                'is_published': True,
                'likes_received_count': 3,
                'matches_count': 1,
                'telegram_real_username': 'ivan_real'
            },
            {
                'telegram_id': 100000004,
                'username': 'anna_test',
                'password': 'password123',
                'first_name': 'Анна',
                'age': 22,
                'interests': 'Книги, Кофе, Настольные игры',
                'about': 'Студентка, книголюб, кофеман',
                'activity_interest': 'Настольные игры',
                'activity_location': 'Екатеринбург',
                'activity_time': 'Вечер',
                'activity_description': 'Сыграть в настольные игры в кафе',
                'photo_path': 'test_photo_4.jpg',
                'photo_id': 'AgACAgIAAxkBAAMRZvwbJJi1LjeL3IHxQT_6m6V8iSUAAp_QMRuU0nlIAAGvjMhYQYADAQADAgADdgADNgQ',
                'is_active': True,
                'is_authenticated': True,
                'is_published': True,
                'likes_received_count': 7,
                'matches_count': 2,
                'telegram_real_username': 'anna_real'
            },
            {
                'telegram_id': 100000005,
                'username': 'dmitry_test',
                'password': 'password123',
                'first_name': 'Дмитрий',
                'age': 30,
                'interests': 'Бизнес, Технологии, Автомобили',
                'about': 'Предприниматель, увлекаюсь новыми технологиями',
                'activity_interest': 'Бизнес',
                'activity_location': 'Новосибирск',
                'activity_time': 'Обед',
                'activity_description': 'Обсудить стартап идеи за обедом',
                'photo_path': 'test_photo_5.jpg',
                'photo_id': 'AgACAgIAAxkBAAMRZvwbJJi1LjeL3IHxQT_6m6V8iSUAAp_QMRuU0nlIAAGvjMhYQYADAQADAgADdQADNgQ',
                'is_active': True,
                'is_authenticated': True,
                'is_published': True,
                'likes_received_count': 4,
                'matches_count': 1,
                'telegram_real_username': 'dmitry_real'
            }
        ]

        try:
            async with self.pool.acquire() as conn:
                user_ids = []
                for user_data in test_users:
                    # Добавляем временные метки
                    created_at = datetime.now() - timedelta(days=random.randint(1, 30))
                    last_login = datetime.now() - timedelta(hours=random.randint(1, 24))
                    last_search = datetime.now() - timedelta(hours=random.randint(1, 12))

                    query = '''
                        INSERT INTO users (
                            telegram_id, username, password, first_name, age, interests, about,
                            activity_interest, activity_location, activity_time, activity_description,
                            photo_path, photo_id, is_active, is_authenticated, is_published,
                            likes_received_count, matches_count, created_at, last_login, last_search,
                            telegram_real_username
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 
                                 $16, $17, $18, $19, $20, $21, $22)
                        RETURNING id
                    '''

                    user_id = await conn.fetchval(
                        query,
                        user_data['telegram_id'],
                        user_data['username'],
                        user_data['password'],
                        user_data['first_name'],
                        user_data['age'],
                        user_data['interests'],
                        user_data['about'],
                        user_data['activity_interest'],
                        user_data['activity_location'],
                        user_data['activity_time'],
                        user_data['activity_description'],
                        user_data['photo_path'],
                        user_data['photo_id'],
                        user_data['is_active'],
                        user_data['is_authenticated'],
                        user_data['is_published'],
                        user_data['likes_received_count'],
                        user_data['matches_count'],
                        created_at,
                        last_login,
                        last_search,
                        user_data['telegram_real_username']
                    )
                    user_ids.append(user_id)
                    logger.info(f"✅ Создан тестовый пользователь: {user_data['username']} (ID: {user_id})")

                return user_ids

        except Exception as e:
            logger.error(f"❌ Ошибка при создании тестовых пользователей: {e}")
            return []

    async def create_test_venues(self):
        """Создание тестовых мест для встреч"""
        test_venues = [
            {
                'name': 'Кофейня "Уют"',
                'category': 'Кафе',
                'latitude': 55.7558,
                'longitude': 37.6176,
                'address': 'Москва, ул. Тверская, д. 10',
                'description': 'Уютная кофейня в центре города',
                'working_hours': '08:00-23:00'
            },
            {
                'name': 'Парк Горького',
                'category': 'Парк',
                'latitude': 55.7289,
                'longitude': 37.6017,
                'address': 'Москва, Крымский Вал, 9',
                'description': 'Центральный парк культуры и отдыха',
                'working_hours': 'Круглосуточно'
            },
            {
                'name': 'Библиотека им. Ленина',
                'category': 'Культура',
                'latitude': 55.7512,
                'longitude': 37.6095,
                'address': 'Москва, ул. Воздвиженка, 3/5',
                'description': 'Крупнейшая библиотека России',
                'working_hours': '09:00-20:00'
            },
            {
                'name': 'Спорткомплекс "Олимпийский"',
                'category': 'Спорт',
                'latitude': 55.7804,
                'longitude': 37.6208,
                'address': 'Москва, Олимпийский проспект, 16',
                'description': 'Современный спортивный комплекс',
                'working_hours': '06:00-23:00'
            }
        ]

        try:
            async with self.pool.acquire() as conn:
                venue_ids = []
                for venue_data in test_venues:
                    query = '''
                        INSERT INTO venues (
                            name, category, latitude, longitude, address, 
                            description, working_hours, is_active
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id
                    '''

                    venue_id = await conn.fetchval(
                        query,
                        venue_data['name'],
                        venue_data['category'],
                        venue_data['latitude'],
                        venue_data['longitude'],
                        venue_data['address'],
                        venue_data['description'],
                        venue_data['working_hours'],
                        True
                    )
                    venue_ids.append(venue_id)
                    logger.info(f"✅ Создано тестовое место: {venue_data['name']} (ID: {venue_id})")

                return venue_ids

        except Exception as e:
            logger.error(f"❌ Ошибка при создании тестовых мест: {e}")
            return []

    async def create_test_meetings(self, user_ids, venue_ids):
        """Создание тестовых встреч"""
        try:
            async with self.pool.acquire() as conn:
                meeting_ids = []

                # Создаем несколько встреч
                meetings_data = [
                    {
                        'user_id': user_ids[0],
                        'venue_id': venue_ids[0],
                        'title': 'Кофе и обсуждение IT',
                        'description': 'Ищу компанию для обсуждения новинок в мире технологий',
                        'category': 'Кафе',
                        'meeting_time': 'Завтра, 15:00',
                        'latitude': 55.7558,
                        'longitude': 37.6176,
                        'status': 'active',
                        'telegram_message_id': 'test_msg_1',
                        'telegram_chat_id': -1000000001
                    },
                    {
                        'user_id': user_ids[1],
                        'venue_id': venue_ids[1],
                        'title': 'Прогулка в парке',
                        'description': 'Прогулка и беседа об искусстве',
                        'category': 'Парк',
                        'meeting_time': 'Суббота, 12:00',
                        'latitude': 55.7289,
                        'longitude': 37.6017,
                        'status': 'active',
                        'telegram_message_id': 'test_msg_2',
                        'telegram_chat_id': -1000000002
                    }
                ]

                for meeting_data in meetings_data:
                    query = '''
                        INSERT INTO map_meeting_requests (
                            user_id, venue_id, title, description, category, meeting_time,
                            max_participants, latitude, longitude, status, created_at, expires_at,
                            telegram_message_id, telegram_chat_id
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                        RETURNING id
                    '''

                    meeting_id = await conn.fetchval(
                        query,
                        meeting_data['user_id'],
                        meeting_data['venue_id'],
                        meeting_data['title'],
                        meeting_data['description'],
                        meeting_data['category'],
                        meeting_data['meeting_time'],
                        2,
                        meeting_data['latitude'],
                        meeting_data['longitude'],
                        meeting_data['status'],
                        datetime.now(),
                        datetime.now() + timedelta(days=7),
                        meeting_data['telegram_message_id'],
                        meeting_data['telegram_chat_id']
                    )
                    meeting_ids.append(meeting_id)
                    logger.info(f"✅ Создана тестовая встреча: {meeting_data['title']} (ID: {meeting_id})")

                return meeting_ids

        except Exception as e:
            logger.error(f"❌ Ошибка при создании тестовых встреч: {e}")
            return []

    async def create_test_likes_and_matches(self, user_ids):
        """Создание тестовых лайков и мэтчей"""
        try:
            async with self.pool.acquire() as conn:
                # Создаем лайки
                likes_data = [
                    (user_ids[0], user_ids[1]),  # Алексей лайкнул Марию
                    (user_ids[1], user_ids[0]),  # Мария лайкнула Алексея (взаимный лайк = мэтч)
                    (user_ids[0], user_ids[2]),  # Алексей лайкнул Ивана
                    (user_ids[2], user_ids[3]),  # Иван лайкнул Анну
                    (user_ids[3], user_ids[4]),  # Анна лайкнула Дмитрия
                    (user_ids[4], user_ids[0]),  # Дмитрий лайкнул Алексея
                ]

                for from_user_id, to_user_id in likes_data:
                    try:
                        await conn.execute('''
                            INSERT INTO likes (from_user_id, to_user_id, created_at)
                            VALUES ($1, $2, $3)
                        ''', from_user_id, to_user_id, datetime.now())
                        logger.info(f"✅ Создан лайк от пользователя {from_user_id} к {to_user_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Лайк уже существует: {e}")

                # Создаем мэтч из взаимных лайков
                try:
                    await conn.execute('''
                        INSERT INTO matches (from_user_id, to_user_id, status, from_confirmed, to_confirmed)
                        VALUES ($1, $2, $3, $4, $5)
                    ''', user_ids[0], user_ids[1], 'matched', True, True)
                    logger.info(f"✅ Создан мэтч между пользователями {user_ids[0]} и {user_ids[1]}")
                except Exception as e:
                    logger.warning(f"⚠️ Мэтч уже существует: {e}")

                # Создаем просмотры профилей
                views_data = [
                    (user_ids[0], user_ids[2]),
                    (user_ids[0], user_ids[3]),
                    (user_ids[1], user_ids[0]),
                    (user_ids[2], user_ids[1]),
                    (user_ids[3], user_ids[0]),
                    (user_ids[4], user_ids[1]),
                ]

                for viewer_id, viewed_user_id in views_data:
                    try:
                        await conn.execute('''
                            INSERT INTO profile_views (viewer_id, viewed_user_id, viewed_at)
                            VALUES ($1, $2, $3)
                        ''', viewer_id, viewed_user_id, datetime.now())
                        logger.info(f"✅ Создан просмотр профиля: {viewer_id} просмотрел {viewed_user_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ Просмотр уже существует: {e}")

                # Создаем поисковые фильтры
                for i, user_id in enumerate(user_ids):
                    filters = [
                        ('Кофе', 'Москва', 'Выходные'),
                        ('Искусство', 'Санкт-Петербург', 'Вечер'),
                        ('Спорт', 'Казань', 'Утро'),
                        ('Настольные игры', 'Екатеринбург', 'Вечер'),
                        ('Бизнес', 'Новосибирск', 'Обед')
                    ]

                    if i < len(filters):
                        interest, location, time_period = filters[i]
                        try:
                            await conn.execute('''
                                INSERT INTO search_filters (user_id, interest, location, time_period, created_at)
                                VALUES ($1, $2, $3, $4, $5)
                            ''', user_id, interest, location, time_period, datetime.now())
                            logger.info(f"✅ Создан поисковый фильтр для пользователя {user_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ Фильтр уже существует: {e}")

                return True

        except Exception as e:
            logger.error(f"❌ Ошибка при создании лайков и мэтчей: {e}")
            return False

    async def reset_and_seed(self):
        """Основная функция сброса и заполнения базы данных"""
        logger.info("🚀 Начинаем процесс сброса и заполнения базы данных...")

        # Подключаемся к базе
        if not await self.connect():
            return False

        # Удаляем все данные
        if not await self.drop_all_data():
            return False

        # Создаем тестовых пользователей
        user_ids = await self.create_test_users()
        if not user_ids:
            logger.error("❌ Не удалось создать тестовых пользователей")
            return False

        # Создаем тестовые места
        venue_ids = await self.create_test_venues()
        if not venue_ids:
            logger.error("❌ Не удалось создать тестовые места")
            return False

        # Создаем тестовые встречи
        meeting_ids = await self.create_test_meetings(user_ids, venue_ids)

        # Создаем тестовые лайки, мэтчи и просмотры
        await self.create_test_likes_and_matches(user_ids)

        logger.info("✅ База данных успешно сброшена и заполнена тестовыми данными!")
        logger.info("📊 Статистика:")
        logger.info(f"   • Пользователей: {len(user_ids)}")
        logger.info(f"   • Мест для встреч: {len(venue_ids)}")
        logger.info(f"   • Встреч: {len(meeting_ids)}")

        return True


async def main():
    """Основная функция"""
    resetter = DatabaseResetter()

    # Подтверждение действия
    print("=" * 60)
    print("⚠️  ВНИМАНИЕ: Этот скрипт удалит ВСЕ данные из базы данных!")
    print(f"База данных: {config.DB_NAME}")
    print(f"Хост: {config.DB_HOST}")
    print("=" * 60)

    confirm = input("Продолжить? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("❌ Операция отменена")
        return

    # Выполняем сброс и заполнение
    success = await resetter.reset_and_seed()

    if success:
        print("✅ База данных успешно обновлена!")
        print("\nТестовые данные:")
        print("Пользователи:")
        print("  1. alex_test / password123")
        print("  2. maria_test / password123")
        print("  3. ivan_test / password123")
        print("  4. anna_test / password123")
        print("  5. dmitry_test / password123")
    else:
        print("❌ Произошла ошибка при обновлении базы данных")


if __name__ == "__main__":
    asyncio.run(main())