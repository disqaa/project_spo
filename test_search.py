import asyncio
import asyncpg
from config import config


async def test_search_functionality():
    """Тестирование функционала поиска"""
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        print("🔍 Тестирование функционала поиска\n")

        # 1. Проверяем общее количество пользователей
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        print(f"1. Всего пользователей в базе: {total_users}")

        # 2. Проверяем опубликованных пользователей
        published_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_published = TRUE")
        print(f"2. Опубликованных анкет: {published_users}")

        # 3. Проверяем авторизованных пользователей
        auth_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_authenticated = TRUE")
        print(f"3. Авторизованных пользователей: {auth_users}")

        # 4. Показываем примеры пользователей
        print(f"\n4. Примеры опубликованных пользователей:")
        sample_users = await conn.fetch(
            "SELECT username, first_name, age, interests FROM users WHERE is_published = TRUE LIMIT 5"
        )

        for i, user in enumerate(sample_users, 1):
            print(f"   {i}. {user['username']} - {user['first_name']}, {user['age']} лет")
            print(f"      Интересы: {user['interests'][:50]}...")

        # 5. Проверяем таблицу лайков
        likes_count = await conn.fetchval("SELECT COUNT(*) FROM likes")
        print(f"\n5. Всего лайков в системе: {likes_count}")

        # 6. Проверяем просмотры профилей
        views_count = await conn.fetchval("SELECT COUNT(*) FROM profile_views")
        print(f"6. Всего просмотров профилей: {views_count}")

        # 7. Показываем распределение по возрастам
        print(f"\n7. Распределение пользователей по возрастам:")
        age_stats = await conn.fetch(
            "SELECT age, COUNT(*) as count FROM users WHERE is_published = TRUE GROUP BY age ORDER BY age"
        )

        for stat in age_stats:
            print(f"   {stat['age']} лет: {stat['count']} пользователь(ей)")

        # 8. Проверяем, сколько пользователей заполнили интересы
        with_interests = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_published = TRUE AND interests IS NOT NULL AND interests != ''"
        )
        print(f"\n8. Пользователей с заполненными интересами: {with_interests}/{published_users}")

        # 9. Проверяем, сколько пользователей заполнили "о себе"
        with_about = await conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE is_published = TRUE AND about IS NOT NULL AND about != ''"
        )
        print(f"9. Пользователей с заполненным 'о себе': {with_about}/{published_users}")

        # 10. Тестовый поиск - находим пользователей для конкретного пользователя
        print(f"\n10. Тестовый поиск для пользователя с ID=1:")

        # Находим пользователей, которых еще не просматривал пользователь с ID=1
        test_user_id = 1
        potential_matches = await conn.fetch('''
            SELECT u.id, u.username, u.first_name, u.age 
            FROM users u
            WHERE u.is_published = TRUE 
                AND u.id != $1
                AND u.id NOT IN (
                    SELECT viewed_user_id FROM profile_views WHERE viewer_id = $1
                )
            ORDER BY RANDOM()
            LIMIT 3
        ''', test_user_id)

        if potential_matches:
            print("   Найдены потенциальные совпадения:")
            for match in potential_matches:
                print(f"   👤 {match['first_name']}, {match['age']} лет (@{match['username']})")
        else:
            print("   ❌ Нет потенциальных совпадений")

        await conn.close()

        print(f"\n✅ Тестирование завершено!")
        print(f"\n📋 Рекомендации для тестирования:")
        print(f"   1. Зарегистрируйтесь и опубликуйте анкету")
        print(f"   2. Используйте '🔍 Начать поиск' в главном меню")
        print(f"   3. Просматривайте анкеты и ставьте лайки")
        print(f"   4. Проверьте статистику в '📊 Статистика'")

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")


if __name__ == "__main__":
    print("🧪 Тестирование функционала поиска...")
    asyncio.run(test_search_functionality())