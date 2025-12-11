# add_test_users.py

import asyncio
import asyncpg
from config import config
import logging
from utils import hash_password, encrypt_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_test_users():
    """Добавить тестовых пользователей с полными анкетами"""
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    # Список тестовых пользователей
    test_users = [
        {
            'telegram_id': 111111111,
            'username': 'anna_25',
            'password': 'password123',
            'first_name': 'Анна',
            'age': 25,
            'interests': 'Книги, путешествия, фотография, йога',
            'about': 'Люблю активный отдых, новые знакомства и саморазвитие. Ищу интересных собеседников.',
            'activity_interest': '🏃 Спорт',
            'activity_location': 'Парк Горького, главный вход',
            'activity_time': '🌆 Вечером',
            'activity_description': 'Пробежка по парку, можно вместе со мной или просто поболтать',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'anna_sport',
            'photo_id': None
        },
        {
            'telegram_id': 222222222,
            'username': 'ivan_30',
            'password': 'password123',
            'first_name': 'Иван',
            'age': 30,
            'interests': 'Кино, музыка, программирование, настольные игры',
            'about': 'Разработчик, люблю интеллектуальные беседы и хорошее кино. Всегда открыт к новым знакомствам.',
            'activity_interest': '🎬 Кино',
            'activity_location': 'Кинотеатр Октябрь',
            'activity_time': '🌆 Вечером',
            'activity_description': 'Хочу посмотреть новый фильм Marvel в компании',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'ivan_dev',
            'photo_id': None
        },
        {
            'telegram_id': 333333333,
            'username': 'maria_28',
            'password': 'password123',
            'first_name': 'Мария',
            'age': 28,
            'interests': 'Кофе, искусство, психология, настольные игры',
            'about': 'Психолог по образованию, люблю душевные разговоры за чашкой кофе.',
            'activity_interest': '☕ Кафе/Бар',
            'activity_location': 'Кофейня "Братья Караваевы"',
            'activity_time': '🌅 Утром',
            'activity_description': 'Утренний кофе и приятная беседа',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'maria_coffee',
            'photo_id': None
        },
        {
            'telegram_id': 444444444,
            'username': 'alex_35',
            'password': 'password123',
            'first_name': 'Алексей',
            'age': 35,
            'interests': 'Бизнес, инвестиции, спорт, шахматы',
            'about': 'Предприниматель, ищу партнеров по бизнесу и просто интересных людей.',
            'activity_interest': '🎮 Настольные игры',
            'activity_location': 'Игровой клуб "Кубик Рубика"',
            'activity_time': '🌞 В выходные',
            'activity_description': 'Игра в мафию или другие настолки, компания от 4 человек',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'alex_business',
            'photo_id': None
        },
        {
            'telegram_id': 555555555,
            'username': 'ekaterina_27',
            'password': 'password123',
            'first_name': 'Екатерина',
            'age': 27,
            'interests': 'Танцы, музыка, иностранные языки, кулинария',
            'about': 'Профессиональная танцовщица, преподаю латиноамериканские танцы.',
            'activity_interest': '🏃 Спорт',
            'activity_location': 'Танцевальная студия "Ритм"',
            'activity_time': '🌆 Вечером',
            'activity_description': 'Групповое занятие по сальсе, можно присоединиться',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'kate_dance',
            'photo_id': None
        },
        {
            'telegram_id': 666666666,
            'username': 'dmitry_32',
            'password': 'password123',
            'first_name': 'Дмитрий',
            'age': 32,
            'interests': 'Рыбалка, походы, гитара, фотография',
            'about': 'Люблю природу и активный отдых. Ищу компанию для походов.',
            'activity_interest': '🏃 Спорт',
            'activity_location': 'Лесопарк "Лосиный остров"',
            'activity_time': '🌞 В выходные',
            'activity_description': 'Пеший поход по лесопарку, 10-15 км',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'dmitry_nature',
            'photo_id': None
        },
        {
            'telegram_id': 777777777,
            'username': 'olga_29',
            'password': 'password123',
            'first_name': 'Ольга',
            'age': 29,
            'interests': 'Искусство, театр, поэзия, вино',
            'about': 'Арт-критик, часто бываю на выставках и в театрах.',
            'activity_interest': '🎬 Кино',
            'activity_location': 'Кинотеатр "Пионер"',
            'activity_time': '🌆 Вечером',
            'activity_description': 'Просмотр арт-хаусного кино с обсуждением',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'olga_art',
            'photo_id': None
        },
        {
            'telegram_id': 888888888,
            'username': 'sergey_40',
            'password': 'password123',
            'first_name': 'Сергей',
            'age': 40,
            'interests': 'История, политика, дебаты, шахматы',
            'about': 'Преподаватель истории, люблю интеллектуальные дискуссии.',
            'activity_interest': '☕ Кафе/Бар',
            'activity_location': 'Бар "Философ"',
            'activity_time': '🌆 Вечером',
            'activity_description': 'Обсуждение исторических событий за бокалом вина',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'sergey_history',
            'photo_id': None
        },
        {
            'telegram_id': 999999999,
            'username': 'natalia_26',
            'password': 'password123',
            'first_name': 'Наталья',
            'age': 26,
            'interests': 'Йога, медитация, вегетарианство, экология',
            'about': 'Инструктор по йоге, пропагандирую здоровый образ жизни.',
            'activity_interest': '🏃 Спорт',
            'activity_location': 'Йога-студия "Ом"',
            'activity_time': '🌅 Утром',
            'activity_description': 'Групповая утренняя йога, все уровни',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'natalia_yoga',
            'photo_id': None
        },
        {
            'telegram_id': 101010101,
            'username': 'maxim_33',
            'password': 'password123',
            'first_name': 'Максим',
            'age': 33,
            'interests': 'Автомобили, технологии, видеоигры, пиво',
            'about': 'Автомеханик, люблю тюнинговать машины и играть в игры.',
            'activity_interest': '🎮 Настольные игры',
            'activity_location': 'Бар с настолками "Игромания"',
            'activity_time': '🌆 Вечером',
            'activity_description': 'Турнир по настольным играм, приз - бесплатное пиво',
            'is_authenticated': True,
            'is_published': True,
            'telegram_real_username': 'maxim_games',
            'photo_id': None
        }
    ]

    logger.info("👥 Добавление тестовых пользователей...")

    for user_data in test_users:
        try:
            # Хешируем пароль
            salt, hashed_password = hash_password(user_data['password'])
            password_str = f"{salt}:{hashed_password}"

            # Шифруем данные
            encrypted_first_name = encrypt_data(user_data['first_name'])
            encrypted_interests = encrypt_data(user_data['interests'])
            encrypted_about = encrypt_data(user_data['about'])
            encrypted_location = encrypt_data(user_data['activity_location'])
            encrypted_description = encrypt_data(user_data['activity_description'])

            # Проверяем, существует ли уже пользователь
            existing = await conn.fetchrow(
                "SELECT id FROM users WHERE telegram_id = $1",
                user_data['telegram_id']
            )

            if existing:
                logger.info(f"⚠️ Пользователь {user_data['username']} уже существует, обновляем...")

                await conn.execute('''
                    UPDATE users SET
                        username = $1,
                        password = $2,
                        first_name = $3,
                        age = $4,
                        interests = $5,
                        about = $6,
                        activity_interest = $7,
                        activity_location = $8,
                        activity_time = $9,
                        activity_description = $10,
                        is_authenticated = $11,
                        is_published = $12,
                        telegram_real_username = $13
                    WHERE telegram_id = $14
                ''',
                                   user_data['username'],
                                   password_str,
                                   encrypted_first_name,
                                   user_data['age'],
                                   encrypted_interests,
                                   encrypted_about,
                                   user_data['activity_interest'],
                                   encrypted_location,
                                   user_data['activity_time'],
                                   encrypted_description,
                                   user_data['is_authenticated'],
                                   user_data['is_published'],
                                   user_data['telegram_real_username'],
                                   user_data['telegram_id']
                                   )
            else:
                await conn.execute('''
                    INSERT INTO users 
                    (telegram_id, username, password, first_name, age, interests, about,
                     activity_interest, activity_location, activity_time, activity_description,
                     is_authenticated, is_published, telegram_real_username, photo_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ''',
                                   user_data['telegram_id'],
                                   user_data['username'],
                                   password_str,
                                   encrypted_first_name,
                                   user_data['age'],
                                   encrypted_interests,
                                   encrypted_about,
                                   user_data['activity_interest'],
                                   encrypted_location,
                                   user_data['activity_time'],
                                   encrypted_description,
                                   user_data['is_authenticated'],
                                   user_data['is_published'],
                                   user_data['telegram_real_username'],
                                   user_data['photo_id']
                                   )

            logger.info(f"✅ Добавлен/обновлен: {user_data['first_name']} (@{user_data['username']})")

        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении {user_data['username']}: {e}")

    await conn.close()
    logger.info("✅ Все тестовые пользователи добавлены!")


async def create_test_likes_and_matches():
    """Создать тестовые лайки и мэтчи между пользователями"""
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    logger.info("❤️ Создание тестовых лайков и мэтчей...")

    try:
        # Получаем ID пользователей
        users = await conn.fetch('SELECT id, username FROM users ORDER BY id LIMIT 10')

        if len(users) < 4:
            logger.warning("⚠️ Недостаточно пользователей для создания лайков")
            return

        # Создаем несколько лайков
        likes_to_create = [
            (users[0]['id'], users[1]['id']),  # Анна лайкнула Ивана
            (users[1]['id'], users[0]['id']),  # Иван лайкнул Анну (взаимный лайк)
            (users[2]['id'], users[3]['id']),  # Мария лайкнула Алексея
            (users[4]['id'], users[5]['id']),  # Екатерина лайкнула Дмитрия
            (users[6]['id'], users[7]['id']),  # Ольга лайкнула Сергея
        ]

        for from_id, to_id in likes_to_create:
            try:
                await conn.execute('''
                    INSERT INTO likes (from_user_id, to_user_id, created_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (from_user_id, to_user_id) DO NOTHING
                ''', from_id, to_id)

                # Если это взаимный лайк, создаем мэтч
                mutual = await conn.fetchrow(
                    "SELECT * FROM likes WHERE from_user_id = $1 AND to_user_id = $2",
                    to_id, from_id
                )

                if mutual:
                    await conn.execute('''
                        INSERT INTO matches (from_user_id, to_user_id, activity_id, status, created_at)
                        VALUES ($1, $2, $2, 'accepted', NOW())
                        ON CONFLICT (from_user_id, to_user_id) DO NOTHING
                    ''', from_id, to_id)

                    logger.info(f"✅ Создан мэтч между пользователями {from_id} и {to_id}")
                else:
                    logger.info(f"✅ Создан лайк от {from_id} к {to_id}")

            except Exception as e:
                logger.error(f"❌ Ошибка при создании лайка: {e}")

        # Создаем несколько запросов на встречи (pending matches)
        pending_matches = [
            (users[3]['id'], users[2]['id']),  # Алексей отправил запрос Марии
            (users[5]['id'], users[4]['id']),  # Дмитрий отправил запрос Екатерине
        ]

        for from_id, to_id in pending_matches:
            try:
                await conn.execute('''
                    INSERT INTO matches (from_user_id, to_user_id, activity_id, status, created_at)
                    VALUES ($1, $2, $2, 'pending', NOW())
                    ON CONFLICT (from_user_id, to_user_id) DO NOTHING
                ''', from_id, to_id)
                logger.info(f"✅ Создан запрос на встречу от {from_id} к {to_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка при создании запроса: {e}")

        await conn.close()
        logger.info("✅ Тестовые лайки и мэтчи созданы!")

    except Exception as e:
        logger.error(f"❌ Ошибка при создании лайков: {e}")


async def create_test_place_meetings():
    """Создать тестовые встречи в заведениях"""
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    logger.info("🗓️ Создание тестовых встреч в заведениях...")

    try:
        # Получаем пользователей и заведения
        users = await conn.fetch('SELECT id, username FROM users ORDER BY id LIMIT 5')
        places = await conn.fetch('SELECT id FROM places ORDER BY id LIMIT 5')

        if not users or not places:
            logger.warning("⚠️ Недостаточно данных для создания встреч")
            return

        from datetime import datetime, timedelta

        # Создаем несколько встреч
        meetings = [
            {
                'place_id': places[0]['id'],
                'user_id': users[0]['id'],
                'meeting_time': datetime.now() + timedelta(hours=2),
                'interest': '☕ Кофе/Общение',
                'description': 'Утренний кофе и обсуждение новых проектов'
            },
            {
                'place_id': places[1]['id'],
                'user_id': users[1]['id'],
                'meeting_time': datetime.now() + timedelta(days=1),
                'interest': '🎬 Кино/Обсуждение',
                'description': 'Просмотр нового фильма и обсуждение после'
            },
            {
                'place_id': places[2]['id'],
                'user_id': users[2]['id'],
                'meeting_time': datetime.now() + timedelta(days=2),
                'interest': '🎮 Настольные игры',
                'description': 'Игра в мафию для начинающих, правила объясню'
            }
        ]

        for meeting_data in meetings:
            try:
                await conn.execute('''
                    INSERT INTO place_meetings 
                    (place_id, user_id, meeting_time, description, interest, max_participants, status)
                    VALUES ($1, $2, $3, $4, $5, 4, 'active')
                ''',
                                   meeting_data['place_id'],
                                   meeting_data['user_id'],
                                   meeting_data['meeting_time'],
                                   meeting_data['description'],
                                   meeting_data['interest']
                                   )
                logger.info(f"✅ Создана встреча: {meeting_data['interest']}")
            except Exception as e:
                logger.error(f"❌ Ошибка при создании встречи: {e}")

        await conn.close()
        logger.info("✅ Тестовые встречи созданы!")

    except Exception as e:
        logger.error(f"❌ Ошибка при создании встреч: {e}")


async def main():
    """Основная функция"""
    print("\n" + "=" * 60)
    print("👥 ЗАПОЛНЕНИЕ БАЗЫ ДАННЫХ ТЕСТОВЫМИ ДАННЫМИ")
    print("=" * 60)

    await add_test_users()
    await create_test_likes_and_matches()
    await create_test_place_meetings()

    print("\n✅ Все тестовые данные успешно добавлены!")
    print("\n📊 Статистика:")
    print("   • 10 пользователей с полными анкетами")
    print("   • Лайки и взаимные лайки")
    print("   • Запросы на встречи")
    print("   • Встречи в заведениях")
    print("\n🚀 Теперь можно тестировать поиск и функционал бота!")


if __name__ == '__main__':
    asyncio.run(main())