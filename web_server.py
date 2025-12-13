# web_server.py - ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncpg
import logging
from config import config
import os
from datetime import datetime, timedelta
import json
import asyncio
from typing import Optional
import re

# Создаем папки
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(title="MeetMap Web App")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")


# Подключение к базе данных
async def get_connection():
    return await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )


# Главная страница с картой
@app.get("/", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})


# Mini App версия
@app.get("/mini", response_class=HTMLResponse)
async def mini_app_page(request: Request):
    return templates.TemplateResponse("mini_app.html", {"request": request})


# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Получить заведения
@app.get("/api/venues")
async def get_venues():
    try:
        conn = await get_connection()
        venues = await conn.fetch('''
            SELECT * FROM venues 
            WHERE is_active = TRUE
            ORDER BY name
        ''')

        result = []
        for venue in venues:
            result.append({
                "id": venue["id"],
                "name": venue["name"],
                "category": venue["category"],
                "latitude": float(venue["latitude"]),
                "longitude": float(venue["longitude"]),
                "address": venue["address"] or "",
                "description": venue["description"] or ""
            })

        await conn.close()
        return JSONResponse(result)

    except Exception as e:
        logging.error(f"Error getting venues: {e}")
        return JSONResponse([])


# Получить встречи с фильтрами
@app.get("/api/meetings")
async def get_meetings(category: Optional[str] = None, time_filter: Optional[str] = None):
    try:
        conn = await get_connection()

        # Формируем запрос
        query = '''
            SELECT 
                mr.*,
                u.username,
                u.first_name,
                u.age,
                u.telegram_id,
                u.telegram_real_username,
                v.name as venue_name,
                v.category as venue_category,
                v.address as venue_address,
                COALESCE(participants.count, 0) as current_participants
            FROM map_meeting_requests mr
            JOIN users u ON u.id = mr.user_id
            LEFT JOIN venues v ON v.id = mr.venue_id
            LEFT JOIN (
                SELECT meeting_id, COUNT(*) as count 
                FROM map_meeting_participants 
                WHERE status = 'accepted'
                GROUP BY meeting_id
            ) participants ON participants.meeting_id = mr.id
            WHERE mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
        '''

        params = []
        param_counter = 1

        if category and category != 'all':
            query += f" AND mr.category = ${param_counter}"
            params.append(category)
            param_counter += 1

        if time_filter and time_filter != 'all':
            # Обработка временных фильтров
            time_mapping = {
                'today': '👋 Сегодня',
                'tomorrow': '📅 Завтра',
                'evening': '🌆 Вечером',
                'weekend': '🌞 В выходные'
            }

            if time_filter in time_mapping:
                query += f" AND mr.meeting_time = ${param_counter}"
                params.append(time_mapping[time_filter])
                param_counter += 1

        query += " ORDER BY mr.created_at DESC"

        meetings = await conn.fetch(query, *params)

        result = []
        for meeting in meetings:
            result.append({
                "id": meeting["id"],
                "title": meeting["title"],
                "description": meeting["description"] or "",
                "category": meeting["category"],
                "meeting_time": meeting["meeting_time"],
                "latitude": float(meeting["latitude"]) if meeting["latitude"] else 55.7558,
                "longitude": float(meeting["longitude"]) if meeting["longitude"] else 37.6173,
                "username": meeting["username"],
                "first_name": meeting["first_name"],
                "age": meeting["age"],
                "telegram_id": meeting["telegram_id"],
                "telegram_username": meeting["telegram_real_username"],
                "venue_name": meeting["venue_name"],
                "venue_category": meeting["venue_category"],
                "venue_address": meeting["venue_address"],
                "max_participants": meeting["max_participants"],
                "current_participants": meeting["current_participants"],
                "created_at": meeting["created_at"].isoformat() if meeting["created_at"] else None,
                "user_id": meeting["user_id"]
            })

        await conn.close()
        return JSONResponse(result)

    except Exception as e:
        logging.error(f"Error getting meetings: {e}")
        return JSONResponse([])

# Получить мои встречи (созданные и присоединенные)
@app.get("/api/my-meetings")
async def get_my_meetings(telegram_id: int):
    try:
        conn = await get_connection()

        # Находим пользователя
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )

        if not user:
            await conn.close()
            return JSONResponse([])

        user_id = user["id"]

        # Получаем встречи, созданные пользователем
        my_created_meetings = await conn.fetch('''
            SELECT 
                mr.*,
                v.name as venue_name,
                v.category as venue_category,
                v.address as venue_address,
                COALESCE(participants.count, 0) as current_participants
            FROM map_meeting_requests mr
            LEFT JOIN venues v ON v.id = mr.venue_id
            LEFT JOIN (
                SELECT meeting_id, COUNT(*) as count 
                FROM map_meeting_participants 
                WHERE status = 'accepted'
                GROUP BY meeting_id
            ) participants ON participants.meeting_id = mr.id
            WHERE mr.user_id = $1 AND mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
            ORDER BY mr.created_at DESC
        ''', user_id)

        # Получаем встречи, к которым присоединился пользователь
        my_participant_meetings = await conn.fetch('''
            SELECT 
                mr.*,
                v.name as venue_name,
                v.category as venue_category,
                v.address as venue_address,
                u.username as creator_username,
                u.first_name as creator_name,
                COALESCE(participants.count, 0) as current_participants
            FROM map_meeting_participants mp
            JOIN map_meeting_requests mr ON mr.id = mp.meeting_id
            LEFT JOIN venues v ON v.id = mr.venue_id
            JOIN users u ON u.id = mr.user_id
            LEFT JOIN (
                SELECT meeting_id, COUNT(*) as count 
                FROM map_meeting_participants 
                WHERE status = 'accepted'
                GROUP BY meeting_id
            ) participants ON participants.meeting_id = mr.id
            WHERE mp.user_id = $1 AND mp.status = 'accepted' AND mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
            ORDER BY mp.joined_at DESC
        ''', user_id)

        result = []

        # Добавляем созданные встречи
        for meeting in my_created_meetings:
            result.append({
                "id": meeting["id"],
                "title": meeting["title"],
                "description": meeting["description"] or "",
                "category": meeting["category"],
                "meeting_time": meeting["meeting_time"],
                "venue_name": meeting["venue_name"],
                "venue_category": meeting["venue_category"],
                "venue_address": meeting["venue_address"],
                "max_participants": meeting["max_participants"],
                "current_participants": meeting["current_participants"],
                "created_at": meeting["created_at"].isoformat() if meeting["created_at"] else None,
                "type": "created"
            })

        # Добавляем встречи, к которым присоединился
        for meeting in my_participant_meetings:
            result.append({
                "id": meeting["id"],
                "title": meeting["title"],
                "description": meeting["description"] or "",
                "category": meeting["category"],
                "meeting_time": meeting["meeting_time"],
                "venue_name": meeting["venue_name"],
                "venue_category": meeting["venue_category"],
                "venue_address": meeting["venue_address"],
                "max_participants": meeting["max_participants"],
                "current_participants": meeting["current_participants"],
                "created_at": meeting["created_at"].isoformat() if meeting["created_at"] else None,
                "creator_username": meeting["creator_username"],
                "creator_name": meeting["creator_name"],
                "type": "joined"
            })

        await conn.close()
        return JSONResponse(result)

    except Exception as e:
        logging.error(f"Error getting my meetings: {e}")
        return JSONResponse([])


# Создать встречу (ИСПРАВЛЕННЫЙ)
@app.post("/api/meetings")
async def create_meeting(request: Request):
    try:
        data = await request.json()
        logging.info(f"Получены данные для создания встречи: {data}")

        telegram_id = data.get("telegram_id")
        title = data.get("title")
        description = data.get("description", "")
        category = data.get("category")
        meeting_time = data.get("meeting_time")
        max_participants = data.get("max_participants", 2)
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        venue_id = data.get("venue_id")

        # Новые поля для адреса
        address = data.get("address", "")
        custom_location = data.get("custom_location", "")

        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        if not title or not meeting_time:
            raise HTTPException(status_code=400, detail="Title and meeting time required")

        if not latitude or not longitude:
            raise HTTPException(status_code=400, detail="Location coordinates required")

        conn = await get_connection()

        try:
            # Находим пользователя
            user = await conn.fetchrow(
                "SELECT id, username FROM users WHERE telegram_id = $1",
                telegram_id
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Устанавливаем время истечения (7 дней)
            expires_at = datetime.now() + timedelta(days=7)

            # Если есть кастомная локация, используем ее как адрес
            final_address = address
            if custom_location:
                final_address = custom_location

            # Если есть venue_id, получаем координаты из заведения
            if venue_id and venue_id != "custom":
                venue = await conn.fetchrow(
                    "SELECT latitude, longitude, address FROM venues WHERE id = $1",
                    int(venue_id)
                )
                if venue:
                    latitude = float(venue["latitude"])
                    longitude = float(venue["longitude"])
                    if not final_address:
                        final_address = venue["address"] or ""

            # Создаем встречу
            meeting_id = await conn.fetchval('''
                INSERT INTO map_meeting_requests 
                (user_id, venue_id, title, description, category, meeting_time,
                 max_participants, latitude, longitude, status, expires_at, address)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'active', $10, $11)
                RETURNING id
            ''',
                                             user["id"],
                                             int(venue_id) if venue_id and venue_id != "custom" else None,
                                             title,
                                             description,
                                             category,
                                             meeting_time,
                                             max_participants,
                                             float(latitude),
                                             float(longitude),
                                             expires_at,
                                             final_address
                                             )

            # Добавляем создателя как участника
            await conn.execute('''
                INSERT INTO map_meeting_participants (meeting_id, user_id, status)
                VALUES ($1, $2, 'accepted')
                ON CONFLICT (meeting_id, user_id) DO NOTHING
            ''', meeting_id, user["id"])

            # Создаем соответствующую активность в профиле пользователя
            activity_category_map = {
                'coffee': '☕ Кафе/Бар',
                'sports': '🏃 Спорт',
                'cinema': '🎬 Кино',
                'games': '🎮 Настольные игры'
            }

            activity_interest = activity_category_map.get(category, '🎯 Встреча')
            activity_location = final_address or f"📍 {title}"

            # Обновляем активность пользователя
            await conn.execute('''
                UPDATE users 
                SET activity_interest = $1, 
                    activity_location = $2,
                    activity_time = $3,
                    activity_description = $4
                WHERE id = $5
            ''',
                               activity_interest,
                               activity_location,
                               meeting_time,
                               description,
                               user["id"])

            await conn.close()

            logging.info(f"✅ Встреча создана успешно: ID={meeting_id}, пользователь={user['username']}")

            return JSONResponse({
                "success": True,
                "meeting_id": meeting_id,
                "message": "Meeting created successfully"
            })

        except Exception as e:
            await conn.close()
            logging.error(f"❌ Ошибка при создании встречи в БД: {e}")
            raise

    except Exception as e:
        logging.error(f"❌ Ошибка создания встречи: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# Присоединиться к встрече (ИСПРАВЛЕННЫЙ)
@app.post("/api/meetings/{meeting_id}/join")
async def join_meeting(meeting_id: int, request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")

        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        conn = await get_connection()

        try:
            # Находим пользователя
            user = await conn.fetchrow(
                "SELECT id, first_name, telegram_real_username FROM users WHERE telegram_id = $1",
                telegram_id
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Проверяем существование встречи
            meeting = await conn.fetchrow('''
                SELECT * FROM map_meeting_requests 
                WHERE id = $1 AND status = 'active'
                AND (expires_at IS NULL OR expires_at > NOW())
            ''', meeting_id)

            if not meeting:
                raise HTTPException(status_code=404, detail="Meeting not found or expired")

            # Проверяем, не присоединился ли уже
            existing = await conn.fetchrow('''
                SELECT * FROM map_meeting_participants 
                WHERE meeting_id = $1 AND user_id = $2
            ''', meeting_id, user["id"])

            if existing:
                # Если уже присоединился, возвращаем успех
                return JSONResponse({"status": "already_joined", "message": "Вы уже присоединились к этой встрече"})

            # Проверяем свободные места
            participants_count = await conn.fetchval('''
                SELECT COUNT(*) FROM map_meeting_participants 
                WHERE meeting_id = $1 AND status = 'accepted'
            ''', meeting_id)

            if participants_count >= meeting["max_participants"]:
                raise HTTPException(status_code=400, detail="Meeting is full")

            # Добавляем участника
            await conn.execute('''
                INSERT INTO map_meeting_participants (meeting_id, user_id, status)
                VALUES ($1, $2, 'accepted')
            ''', meeting_id, user["id"])

            # Получаем информацию о создателе встречи для уведомления
            creator = await conn.fetchrow(
                "SELECT telegram_id, first_name, username FROM users WHERE id = $1",
                meeting["user_id"]
            )

            if creator and creator["telegram_id"]:
                # Записываем информацию для уведомления (реальная отправка через бота)
                logging.info(f"User {user['id']} joined meeting {meeting_id}. Creator: {creator['telegram_id']}")

            await conn.close()

            return JSONResponse({
                "status": "joined",
                "message": "Вы успешно присоединились к встрече",
                "meeting_id": meeting_id,
                "participants_count": participants_count + 1
            })

        except Exception as e:
            await conn.close()
            raise

    except Exception as e:
        logging.error(f"Error joining meeting: {e}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)


# Удалить встречу
@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int, request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")

        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        conn = await get_connection()

        # Находим пользователя
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )

        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        # Проверяем, принадлежит ли встреча пользователю
        meeting = await conn.fetchrow('''
            SELECT * FROM map_meeting_requests 
            WHERE id = $1 AND user_id = $2
        ''', meeting_id, user["id"])

        if not meeting:
            await conn.close()
            raise HTTPException(status_code=403, detail="Not authorized")

        # Помечаем как удаленную
        await conn.execute('''
            UPDATE map_meeting_requests 
            SET status = 'deleted'
            WHERE id = $1
        ''', meeting_id)

        await conn.close()

        return JSONResponse({
            "success": True,
            "message": "Meeting deleted"
        })

    except Exception as e:
        logging.error(f"Error deleting meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/meetings/{meeting_id}/leave")
async def leave_meeting(meeting_id: int, request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")

        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        conn = await get_connection()

        # Находим пользователя
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )

        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        # Проверяем участие пользователя
        participant = await conn.fetchrow('''
            SELECT * FROM map_meeting_participants 
            WHERE meeting_id = $1 AND user_id = $2 AND status = 'accepted'
        ''', meeting_id, user["id"])

        if not participant:
            await conn.close()
            raise HTTPException(status_code=404, detail="You are not a participant of this meeting")

        # Проверяем, является ли пользователь организатором
        meeting = await conn.fetchrow('''
            SELECT * FROM map_meeting_requests 
            WHERE id = $1 AND user_id = $2
        ''', meeting_id, user["id"])

        if meeting:
            # Если пользователь организатор, нельзя покинуть встречу, нужно удалить
            await conn.close()
            return JSONResponse({
                "error": "You are the organizer. Use delete instead.",
                "is_organizer": True
            })

        # Удаляем участника
        await conn.execute('''
            DELETE FROM map_meeting_participants 
            WHERE meeting_id = $1 AND user_id = $2
        ''', meeting_id, user["id"])

        await conn.close()

        return JSONResponse({
            "success": True,
            "message": "You have left the meeting"
        })

    except Exception as e:
        logging.error(f"Error leaving meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Получить статус участия в встрече
@app.get("/api/meetings/{meeting_id}/status")
async def get_meeting_status(meeting_id: int, telegram_id: int):
    try:
        conn = await get_connection()

        # Находим пользователя
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )

        if not user:
            await conn.close()
            return JSONResponse({"status": "not_found"})

        # Проверяем участие
        participant = await conn.fetchrow('''
            SELECT status FROM map_meeting_participants 
            WHERE meeting_id = $1 AND user_id = $2
        ''', meeting_id, user["id"])

        await conn.close()

        if participant:
            return JSONResponse({"status": participant["status"]})
        else:
            return JSONResponse({"status": "not_joined"})

    except Exception as e:
        logging.error(f"Error getting meeting status: {e}")
        return JSONResponse({"status": "error"})


# Получить категории встреч
@app.get("/api/categories")
async def get_categories():
    return JSONResponse([
        {"id": "all", "name": "Все категории", "icon": "🗺️"},
        {"id": "coffee", "name": "☕ Кофе/Бар", "icon": "☕"},
        {"id": "sports", "name": "🏃 Спорт", "icon": "🏃"},
        {"id": "cinema", "name": "🎬 Кино", "icon": "🎬"},
        {"id": "games", "name": "🎮 Игры", "icon": "🎮"}
    ])


# Получить временные фильтры
@app.get("/api/time-filters")
async def get_time_filters():
    return JSONResponse([
        {"id": "all", "name": "Любое время", "icon": "⏰"},
        {"id": "today", "name": "👋 Сегодня", "icon": "👋"},
        {"id": "tomorrow", "name": "📅 Завтра", "icon": "📅"},
        {"id": "evening", "name": "🌆 Вечером", "icon": "🌆"},
        {"id": "weekend", "name": "🌞 Выходные", "icon": "🌞"}
    ])


# Проверить координаты
def validate_coordinates(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
        return None
    except:
        return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")