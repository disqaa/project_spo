"""
clear_db.py — очищает все таблицы БД без удаления структуры.
Запускать ОДИН РАЗ, потом удалить из проекта.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv(override=False)

async def clear():
    print("🔗 Подключение к базе данных...")
    conn = await asyncpg.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432))
    )
    print("✅ Подключено!")

    await conn.execute("SET session_replication_role = replica")

    tables = [
        "map_meeting_participants",
        "map_meeting_requests",
        "matches",
        "likes",
        "profile_views",
        "search_filters",
        "users",
    ]

    for t in tables:
        await conn.execute(f"TRUNCATE TABLE {t} CASCADE")
        print(f"✅ {t} очищена")

    await conn.execute("SET session_replication_role = DEFAULT")
    await conn.close()
    print("\n✅ База данных полностью очищена!")

asyncio.run(clear())