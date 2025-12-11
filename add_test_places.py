# add_test_places.py

import asyncio
import asyncpg
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def add_test_places():
    """Добавить тестовые заведения в Москве"""
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
            'address': 'ул. Тверская, 12, Москва',
            'latitude': 55.7602,
            'longitude': 37.6085,
            'category': 'cafe',
            'description': 'Кофейня с уютной атмосферой и бесплатным Wi-Fi',
            'opening_hours': '08:00-23:00',
            'phone': '+7 (495) 123-45-67',
            'website': 'https://starbucks.ru',
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
            'phone': '+7 (495) 234-56-78',
            'website': 'https://october-cinema.ru',
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
            'phone': '+7 (495) 345-67-89',
            'website': 'https://worldclass.ru',
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
            'phone': '+7 (495) 456-78-90',
            'website': 'https://rulesofgame.ru',
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
            'phone': '+7 (495) 567-89-01',
            'website': 'https://biblio-globus.ru',
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
            'phone': '+7 (495) 678-90-12',
            'website': 'https://park-gorkogo.ru',
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
            'phone': '+7 (495) 789-01-23',
            'website': 'https://whiterabbitmoscow.ru',
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
            'phone': '+7 (495) 890-12-34',
            'website': 'https://leninka.ru',
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
            'phone': '+7 (495) 901-23-45',
            'website': 'https://moma-moscow.ru',
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
            'phone': '+7 (495) 012-34-56',
            'website': 'https://doublebcoffee.ru',
            'rating': 4.8
        }
    ]

    logger.info("📍 Добавление тестовых заведений...")

    for place in sample_places:
        try:
            # Проверяем, существует ли уже заведение
            existing = await conn.fetchrow(
                "SELECT id FROM places WHERE name = $1 AND address = $2",
                place['name'], place['address']
            )

            if existing:
                logger.info(f"⚠️ Заведение {place['name']} уже существует, обновляем...")

                await conn.execute('''
                    UPDATE places SET
                        latitude = $1,
                        longitude = $2,
                        category = $3,
                        description = $4,
                        opening_hours = $5,
                        phone = $6,
                        website = $7,
                        rating = $8,
                        is_active = TRUE
                    WHERE name = $9 AND address = $10
                ''',
                                   place['latitude'],
                                   place['longitude'],
                                   place['category'],
                                   place['description'],
                                   place['opening_hours'],
                                   place['phone'],
                                   place['website'],
                                   place['rating'],
                                   place['name'],
                                   place['address']
                                   )
            else:
                await conn.execute('''
                    INSERT INTO places 
                    (name, address, latitude, longitude, category, description, 
                     opening_hours, phone, website, rating, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, TRUE)
                ''',
                                   place['name'],
                                   place['address'],
                                   place['latitude'],
                                   place['longitude'],
                                   place['category'],
                                   place['description'],
                                   place['opening_hours'],
                                   place['phone'],
                                   place['website'],
                                   place['rating']
                                   )

            logger.info(f"✅ Добавлено/обновлено: {place['name']}")

        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении {place['name']}: {e}")

    await conn.close()
    logger.info("✅ Все тестовые заведения добавлены!")


async def main():
    """Основная функция"""
    print("\n" + "=" * 60)
    print("📍 ДОБАВЛЕНИЕ ТЕСТОВЫХ ЗАВЕДЕНИЙ")
    print("=" * 60)

    await add_test_places()

    print("\n✅ 10 тестовых заведений добавлены в Москве!")
    print("📍 Теперь карта будет показывать реальные места")


if __name__ == '__main__':
    asyncio.run(main())