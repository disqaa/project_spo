import asyncio
import asyncpg
from config import config
from utils import hash_password, encrypt_data
import random


async def create_test_users():
    """Создание тестовых пользователей с активностями"""
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

        # Список возможных активностей
        activities = [
            {
                "interest": "🏃 Спорт",
                "locations": ["Спортзал 'Сила'", "Стадион Центральный", "Парк Победы", "Бассейн 'Волна'"],
                "times": ["🌆 Вечером", "🌅 Утром", "🌞 В выходные", "👋 Сегодня"],
                "descriptions": [
                    "Ищу партнера для совместных тренировок",
                    "Хочу поиграть в футбол/баскетбол",
                    "Предлагаю пробежку в парке",
                    "Ищу напарника для занятий в зале"
                ]
            },
            {
                "interest": "🎬 Кино",
                "locations": ["Кинотеатр 'Октябрь'", "Кинотеатр 'Макси'", "Кинозал в ТЦ 'Галерея'"],
                "times": ["🌆 Вечером", "👋 Сегодня", "📅 Завтра", "🌞 В выходные"],
                "descriptions": [
                    "Хочу посмотреть новый фильм в компании",
                    "Ищу компанию для похода в кино",
                    "Предлагаю сходить на премьеру",
                    "Хочу обсудить фильмы за просмотром"
                ]
            },
            {
                "interest": "☕ Кафе/Бар",
                "locations": ["Кофейня 'Уют'", "Бар 'Старый город'", "Кафе 'Вкусняшка'", "Кофейня на Пушкина"],
                "times": ["🌆 Вечером", "🌞 В выходные", "👋 Сегодня", "⏰ Любое время"],
                "descriptions": [
                    "Хочу выпить кофе и пообщаться",
                    "Ищу компанию для вечерних посиделок",
                    "Предлагаю встретиться за чашечкой кофе",
                    "Хочу познакомиться в неформальной обстановке"
                ]
            },
            {
                "interest": "🎮 Настольные игры",
                "locations": ["Игровой клуб 'Дженга'", "Кафе с настолками", "Домашняя атмосфера",
                              "Антикафе 'Игротека'"],
                "times": ["🌆 Вечером", "🌞 В выходные", "🗓️ В ближайшие дни", "👋 Сегодня"],
                "descriptions": [
                    "Ищу компанию для игры в настолки",
                    "Хочу поиграть в Мафию/Монополию",
                    "Предлагаю игровой вечер",
                    "Ищу партнеров для командных игр"
                ]
            }
        ]

        # Список тестовых пользователей
        test_users = [
            {
                "telegram_id": 11111111,
                "username": "anna10",
                "password": "anna12345",
                "first_name": "Анна",
                "age": 25,
                "interests": "Книги, путешествия, фотография, йога, кофе",
                "about": "Люблю активный отдых и знакомства с новыми людьми. Ищу друзей для походов в горы и совместных путешествий.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 22222222,
                "username": "ivan11",
                "password": "ivan12345",
                "first_name": "Иван",
                "age": 30,
                "interests": "Спорт, музыка, кино, программирование, настольные игры",
                "about": "Работаю IT-специалистом. Люблю активный образ жизни, хожу в тренажерный зал. Ищу компанию для походов в кино и на концерты.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 33333333,
                "username": "maria13",
                "password": "maria12345",
                "first_name": "Мария",
                "age": 22,
                "interests": "Танцы, рисование, мода, психология, иностранные языки",
                "about": "Студентка, изучаю психологию. Увлекаюсь танцами и рисованием. Хочу найти друзей для практики английского языка.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 44444444,
                "username": "alex14",
                "password": "alex12345",
                "first_name": "Алексей",
                "age": 35,
                "interests": "Рыбалка, охота, машины, ремонт, строительство",
                "about": "Люблю природу и активный отдых. Часто езжу на рыбалку. Ищу единомышленников для совместных выездов на природу.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 55555555,
                "username": "elena15",
                "password": "elena12345",
                "first_name": "Елена",
                "age": 28,
                "interests": "Кулинария, садоводство, рукоделие, домашние животные",
                "about": "Люблю готовить и принимать гостей. У меня есть собака и кот. Ищу друзей для обмена рецептами и совместных прогулок с собаками.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 66666666,
                "username": "dmitry16",
                "password": "dmitry12345",
                "first_name": "Дмитрий",
                "age": 32,
                "interests": "Бизнес, инвестиции, экономика, путешествия, вино",
                "about": "Предприниматель. Люблю путешествовать и пробовать новое. Ищу интересных собеседников для обсуждения бизнес-идей.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 77777777,
                "username": "olga17",
                "password": "olga12345",
                "first_name": "Ольга",
                "age": 27,
                "interests": "Фитнес, здоровое питание, медитация, саморазвитие",
                "about": "Ведю здоровый образ жизни. Работаю тренером по фитнесу. Ищу людей, которые тоже ценят здоровье и саморазвитие.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 88888888,
                "username": "sergey18",
                "password": "sergey12345",
                "first_name": "Сергей",
                "age": 40,
                "interests": "История, философия, шахматы, классическая музыка",
                "about": "Преподаватель истории. Люблю интеллектуальные беседы и настольные игры. Ищу компанию для игры в шахматы.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 99999999,
                "username": "tanya19",
                "password": "tanya12345",
                "first_name": "Татьяна",
                "age": 33,
                "interests": "Мода, дизайн, архитектура, искусство, выставки",
                "about": "Дизайнер интерьеров. Люблю посещать выставки и музеи. Ищу друзей для совместных походов на культурные мероприятия.",
                "photo_id": None,
                "is_published": True
            },
            {
                "telegram_id": 10101010,
                "username": "andrey20",
                "password": "andrey12345",
                "first_name": "Андрей",
                "age": 29,
                "interests": "Экстрим, мотоциклы, парашютный спорт, дайвинг",
                "about": "Адреналин - моя жизнь! Люблю экстремальные виды спорта. Ищу таких же смельчаков для совместных приключений.",
                "photo_id": None,
                "is_published": True
            }
        ]

        created_count = 0
        skipped_count = 0

        for i, user_data in enumerate(test_users):
            # Проверяем, существует ли уже пользователь
            existing = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1 OR username = $2",
                user_data["telegram_id"], user_data["username"]
            )

            if existing:
                print(f"⚠️ Пользователь {user_data['username']} уже существует, пропускаем")
                skipped_count += 1
                continue

            try:
                # Хешируем пароль
                salt, hashed_password = hash_password(user_data["password"])

                # Шифруем данные
                encrypted_first_name = encrypt_data(user_data["first_name"])
                encrypted_interests = encrypt_data(user_data["interests"])
                encrypted_about = encrypt_data(user_data["about"])

                # Выбираем случайную активность для пользователя
                activity = random.choice(activities)
                activity_interest = activity["interest"]
                activity_location = random.choice(activity["locations"])
                activity_time = random.choice(activity["times"])
                activity_description = random.choice(activity["descriptions"])

                # Шифруем данные активности
                encrypted_location = encrypt_data(activity_location)
                encrypted_description = encrypt_data(activity_description)

                # Вставляем пользователя
                await conn.execute('''
                    INSERT INTO users 
                    (telegram_id, username, password, first_name, age, interests, about, 
                     activity_interest, activity_location, activity_time, activity_description,
                     photo_id, is_authenticated, is_published)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ''',
                                   user_data["telegram_id"],
                                   user_data["username"],
                                   f"{salt}:{hashed_password}",
                                   encrypted_first_name,
                                   user_data["age"],
                                   encrypted_interests,
                                   encrypted_about,
                                   activity_interest,
                                   encrypted_location,
                                   activity_time,
                                   encrypted_description,
                                   user_data["photo_id"],
                                   True,  # is_authenticated
                                   user_data["is_published"]
                                   )

                print(
                    f"✅ Создан пользователь: {user_data['username']} ({user_data['first_name']}, {user_data['age']} лет)")
                print(f"   Активность: {activity_interest} - {activity_location} - {activity_time}")
                created_count += 1

            except Exception as e:
                print(f"❌ Ошибка при создании пользователя {user_data['username']}: {e}")

        print(f"\n📊 Итог: создано {created_count} пользователей, пропущено {skipped_count}")

        # Проверяем распределение по активностям
        print("\n📈 Распределение по активностям:")
        for activity_info in activities:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE activity_interest = $1",
                activity_info["interest"]
            )
            print(f"   {activity_info['interest']}: {count} пользователей")

        # Проверяем общее количество пользователей
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        published_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_published = TRUE")

        print(f"\n📊 Всего пользователей в базе: {total_users}")
        print(f"📢 Опубликованных анкет: {published_users}")

        await conn.close()

    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        print("Проверьте настройки подключения в config.py")


if __name__ == "__main__":
    print("🚀 Создание тестовых пользователей с активностями...")
    asyncio.run(create_test_users())