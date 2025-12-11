# add_sample_places.py

import asyncio
import asyncpg
from config import config


async def add_sample_places():
    """Добавление тестовых заведений"""
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )

    # Тестовые заведения (Москва)
    sample_places = [
        {
            'name': 'Starbucks Coffee',
            'address': 'ул. Тверская, 12',
            'latitude': 55.7602,
            'longitude': 37.6085,
            'category': 'cafe',
            'description': 'Кофейня с уютной атмосферой',
            'rating': 4.5
        },
        {
            'name': 'Кинотеатр Октябрь',
            'address': 'Новый Арбат, 24',
            'latitude': 55.7517,
            'longitude': 37.5866,
            'category': 'cinema',
            'description': 'Современный кинотеатр с 7 залами',
            'rating': 4.7
        },
        {
            'name': 'Фитнес клуб World Class',
            'address': 'ул. Маросейка, 6/8',
            'latitude': 55.7588,
            'longitude': 37.6353,
            'category': 'sport',
            'description': 'Премиальный фитнес клуб',
            'rating': 4.8
        },
        {
            'name': 'Бар Правила Игры',
            'address': 'Кузнецкий Мост, 7',
            'latitude': 55.7616,
            'longitude': 37.6213,
            'category': 'bar',
            'description': 'Бар с настольными играми',
            'rating': 4.6
        },
        {
            'name': 'Книжный магазин Библио-Глобус',
            'address': 'Мясницкая ул., 6/3',
            'latitude': 55.7620,
            'longitude': 37.6302,
            'category': 'books',
            'description': 'Крупнейший книжный магазин',
            'rating': 4.9
        }
    ]

    for place in sample_places:
        try:
            await conn.execute('''
                INSERT INTO places (name, address, latitude, longitude, category, description, rating)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
            ''', place['name'], place['address'], place['latitude'], place['longitude'],
               place['category'], place['description'], place['rating'])
            print(f"✅ Добавлено: {place['name']}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    await conn.close()
    print("✅ Все тестовые заведения добавлены!")


if __name__ == '__main__':
    asyncio.run(add_sample_places())