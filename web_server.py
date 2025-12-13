from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncpg
import logging
from config import config
import os

# Создаем папку для шаблонов если её нет
os.makedirs("templates", exist_ok=True)

app = FastAPI(title="MeetMap Web App")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка шаблонов
templates = Jinja2Templates(directory="templates")


# Подключение к базе данных
async def get_db():
    conn = await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )
    try:
        yield conn
    finally:
        await conn.close()


# Простая проверка доступности
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "meetmap-web"}


# Главная страница с картой
@app.get("/", response_class=HTMLResponse)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})


# Mini App версия
@app.get("/mini", response_class=HTMLResponse)
async def mini_app_page(request: Request):
    return templates.TemplateResponse("mini_app.html", {"request": request})


# API: Получить все активные заявки
@app.get("/api/meetings")
async def get_meetings():
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        meetings = await conn.fetch('''
            SELECT 
                mr.*,
                u.username,
                u.first_name,
                u.age,
                v.name as venue_name,
                v.category as venue_category,
                COUNT(mp.id) as participants_count
            FROM map_meeting_requests mr
            LEFT JOIN users u ON u.id = mr.user_id
            LEFT JOIN venues v ON v.id = mr.venue_id
            LEFT JOIN map_meeting_participants mp ON mp.meeting_id = mr.id 
                AND mp.status = 'accepted'
            WHERE mr.status = 'active'
            GROUP BY mr.id, u.id, v.id
            ORDER BY mr.created_at DESC
        ''')

        await conn.close()

        result = []
        for meeting in meetings:
            result.append({
                "id": meeting["id"],
                "title": meeting["title"],
                "description": meeting["description"],
                "meeting_time": meeting["meeting_time"],
                "latitude": float(meeting["latitude"]) if meeting["latitude"] else 55.7558,
                "longitude": float(meeting["longitude"]) if meeting["longitude"] else 37.6173,
                "username": meeting["username"],
                "first_name": meeting["first_name"],
                "age": meeting["age"],
                "venue_name": meeting["venue_name"],
                "venue_category": meeting["venue_category"],
                "max_participants": meeting["max_participants"],
                "current_participants": meeting["participants_count"] or 0,
            })

        return JSONResponse(result)

    except Exception as e:
        logging.error(f"Error getting meetings: {e}")
        return JSONResponse([])


# API: Получить заведения
@app.get("/api/venues")
async def get_venues():
    try:
        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        venues = await conn.fetch('''
            SELECT * FROM venues 
            WHERE is_active = TRUE
            ORDER BY name
        ''')

        await conn.close()

        result = []
        for venue in venues:
            result.append({
                "id": venue["id"],
                "name": venue["name"],
                "category": venue["category"],
                "latitude": float(venue["latitude"]),
                "longitude": float(venue["longitude"]),
                "address": venue["address"],
                "description": venue["description"]
            })

        return JSONResponse(result)

    except Exception as e:
        logging.error(f"Error getting venues: {e}")
        return JSONResponse([])


# API: Присоединиться к встрече
@app.post("/api/meetings/{meeting_id}/join")
async def join_meeting(meeting_id: int, request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")

        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        conn = await asyncpg.connect(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT
        )

        # Получаем user_id по telegram_id
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            telegram_id
        )

        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        # Проверяем, существует ли встреча
        meeting = await conn.fetchrow(
            "SELECT * FROM map_meeting_requests WHERE id = $1",
            meeting_id
        )

        if not meeting:
            await conn.close()
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Проверяем, не присоединился ли уже пользователь
        existing = await conn.fetchrow('''
            SELECT * FROM map_meeting_participants 
            WHERE meeting_id = $1 AND user_id = $2
        ''', meeting_id, user["id"])

        if existing:
            await conn.close()
            return JSONResponse({"status": "already_joined"})

        # Добавляем пользователя как участника
        await conn.execute('''
            INSERT INTO map_meeting_participants (meeting_id, user_id, status)
            VALUES ($1, $2, 'accepted')
        ''', meeting_id, user["id"])

        await conn.close()

        return JSONResponse({
            "status": "joined",
            "meeting_id": meeting_id
        })

    except Exception as e:
        logging.error(f"Error joining meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Запуск сервера
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)