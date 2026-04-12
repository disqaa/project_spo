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
from typing import Optional

os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(title="MeetMap Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def get_connection():
    return await asyncpg.connect(
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT
    )


# ── Страницы ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def map_page(request: Request):
    # Фикс для Python 3.13 / новых версий Starlette
    return templates.TemplateResponse(request=request, name="map.html")


@app.get("/mini", response_class=HTMLResponse)
async def mini_app_page(request: Request):
    # Фикс для Python 3.13 / новых версий Starlette
    return templates.TemplateResponse(request=request, name="mini_app.html")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── API: Заведения ────────────────────────────────────────────────────────────

@app.get("/api/venues")
async def get_venues():
    try:
        conn = await get_connection()
        venues = await conn.fetch("SELECT * FROM venues WHERE is_active = TRUE ORDER BY name")
        result = [
            {
                "id": v["id"], "name": v["name"], "category": v["category"],
                "latitude": float(v["latitude"]), "longitude": float(v["longitude"]),
                "address": v["address"] or "", "description": v["description"] or ""
            }
            for v in venues
        ]
        await conn.close()
        return JSONResponse(result)
    except Exception as e:
        logging.error(f"Error getting venues: {e}")
        return JSONResponse([])


# ── API: Встречи ──────────────────────────────────────────────────────────────

@app.get("/api/meetings")
async def get_meetings(category: Optional[str] = None, time_filter: Optional[str] = None):
    try:
        conn = await get_connection()

        query = '''
            SELECT mr.*, u.username, u.first_name, u.age, u.telegram_id,
                   u.telegram_real_username,
                   v.name as venue_name, v.category as venue_category, v.address as venue_address,
                   COALESCE(participants.count, 0) as current_participants
            FROM map_meeting_requests mr
            JOIN users u ON u.id = mr.user_id
            LEFT JOIN venues v ON v.id = mr.venue_id
            LEFT JOIN (
                SELECT meeting_id, COUNT(*) as count
                FROM map_meeting_participants WHERE status = 'accepted'
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
            time_mapping = {
                'today': '👋 Сегодня', 'tomorrow': '📅 Завтра',
                'evening': '🌆 Вечером', 'weekend': '🌞 В выходные'
            }
            if time_filter in time_mapping:
                query += f" AND mr.meeting_time = ${param_counter}"
                params.append(time_mapping[time_filter])

        query += " ORDER BY mr.created_at DESC"
        meetings = await conn.fetch(query, *params)

        result = [
            {
                "id": m["id"], "title": m["title"],
                "description": m["description"] or "",
                "category": m["category"], "meeting_time": m["meeting_time"],
                "latitude": float(m["latitude"]) if m["latitude"] else 55.7558,
                "longitude": float(m["longitude"]) if m["longitude"] else 37.6173,
                "username": m["username"], "first_name": m["first_name"],
                "age": m["age"], "telegram_id": m["telegram_id"],
                "telegram_username": m["telegram_real_username"],
                "venue_name": m["venue_name"], "venue_category": m["venue_category"],
                "venue_address": m["venue_address"],
                "max_participants": m["max_participants"],
                "current_participants": m["current_participants"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None,
                "user_id": m["user_id"]
            }
            for m in meetings
        ]
        await conn.close()
        return JSONResponse(result)
    except Exception as e:
        logging.error(f"Error getting meetings: {e}")
        return JSONResponse([])


@app.get("/api/my-meetings")
async def get_my_meetings(telegram_id: int):
    try:
        conn = await get_connection()
        user = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
        if not user:
            await conn.close()
            return JSONResponse([])

        user_id = user["id"]

        created = await conn.fetch('''
            SELECT mr.*, v.name as venue_name, v.category as venue_category,
                   v.address as venue_address,
                   COALESCE(p.count, 0) as current_participants
            FROM map_meeting_requests mr
            LEFT JOIN venues v ON v.id = mr.venue_id
            LEFT JOIN (SELECT meeting_id, COUNT(*) as count FROM map_meeting_participants
                       WHERE status='accepted' GROUP BY meeting_id) p ON p.meeting_id = mr.id
            WHERE mr.user_id = $1 AND mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
            ORDER BY mr.created_at DESC
        ''', user_id)

        joined = await conn.fetch('''
            SELECT mr.*, v.name as venue_name, v.category as venue_category,
                   v.address as venue_address, u.username as creator_username,
                   u.first_name as creator_name,
                   COALESCE(p.count, 0) as current_participants
            FROM map_meeting_participants mp
            JOIN map_meeting_requests mr ON mr.id = mp.meeting_id
            LEFT JOIN venues v ON v.id = mr.venue_id
            JOIN users u ON u.id = mr.user_id
            LEFT JOIN (SELECT meeting_id, COUNT(*) as count FROM map_meeting_participants
                       WHERE status='accepted' GROUP BY meeting_id) p ON p.meeting_id = mr.id
            WHERE mp.user_id = $1 AND mp.status = 'accepted' AND mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
            ORDER BY mp.joined_at DESC
        ''', user_id)

        result = [
            {
                "id": m["id"], "title": m["title"], "description": m["description"] or "",
                "category": m["category"], "meeting_time": m["meeting_time"],
                "venue_name": m["venue_name"], "venue_address": m["venue_address"],
                "max_participants": m["max_participants"],
                "current_participants": m["current_participants"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None,
                "type": "created"
            }
            for m in created
        ] + [
            {
                "id": m["id"], "title": m["title"], "description": m["description"] or "",
                "category": m["category"], "meeting_time": m["meeting_time"],
                "venue_name": m["venue_name"], "venue_address": m["venue_address"],
                "max_participants": m["max_participants"],
                "current_participants": m["current_participants"],
                "created_at": m["created_at"].isoformat() if m["created_at"] else None,
                "creator_username": m["creator_username"], "creator_name": m["creator_name"],
                "type": "joined"
            }
            for m in joined
        ]

        await conn.close()
        return JSONResponse(result)
    except Exception as e:
        logging.error(f"Error getting my meetings: {e}")
        return JSONResponse([])


@app.post("/api/meetings")
async def create_meeting(request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")
        title = data.get("title")
        description = data.get("description", "")
        category = data.get("category")
        meeting_time = data.get("meeting_time")
        max_participants = data.get("max_participants", 2)
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        venue_id = data.get("venue_id")
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
            user = await conn.fetchrow(
                "SELECT id, username FROM users WHERE telegram_id = $1", telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            expires_at = datetime.now() + timedelta(days=7)
            final_address = custom_location or address

            if venue_id and venue_id != "custom":
                venue = await conn.fetchrow(
                    "SELECT latitude, longitude, address FROM venues WHERE id = $1", int(venue_id))
                if venue:
                    latitude = float(venue["latitude"])
                    longitude = float(venue["longitude"])
                    if not final_address:
                        final_address = venue["address"] or ""

            meeting_id = await conn.fetchval('''
                INSERT INTO map_meeting_requests
                (user_id, venue_id, title, description, category, meeting_time,
                 max_participants, latitude, longitude, status, expires_at, address)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'active',$10,$11)
                RETURNING id
            ''', user["id"],
                int(venue_id) if venue_id and venue_id != "custom" else None,
                title, description, category, meeting_time, max_participants,
                float(latitude), float(longitude), expires_at, final_address)

            await conn.execute('''
                INSERT INTO map_meeting_participants (meeting_id, user_id, status)
                VALUES ($1, $2, 'accepted') ON CONFLICT (meeting_id, user_id) DO NOTHING
            ''', meeting_id, user["id"])

            activity_map = {
                'coffee': '☕ Кафе/Бар', 'sports': '🏃 Спорт',
                'cinema': '🎬 Кино', 'games': '🎮 Настольные игры'
            }
            await conn.execute('''
                UPDATE users SET activity_interest=$1, activity_location=$2,
                activity_time=$3, activity_description=$4 WHERE id=$5
            ''', activity_map.get(category, '🎯 Встреча'),
                final_address or f"📍 {title}", meeting_time, description, user["id"])

            await conn.close()
            return JSONResponse({"success": True, "meeting_id": meeting_id})
        except Exception as e:
            await conn.close()
            raise
    except Exception as e:
        logging.error(f"Error creating meeting: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/meetings/{meeting_id}/join")
async def join_meeting(meeting_id: int, request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        conn = await get_connection()
        try:
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE telegram_id = $1", telegram_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            meeting = await conn.fetchrow('''
                SELECT * FROM map_meeting_requests
                WHERE id=$1 AND status='active'
                AND (expires_at IS NULL OR expires_at > NOW())
            ''', meeting_id)
            if not meeting:
                raise HTTPException(status_code=404, detail="Meeting not found or expired")

            existing = await conn.fetchrow(
                "SELECT * FROM map_meeting_participants WHERE meeting_id=$1 AND user_id=$2",
                meeting_id, user["id"])
            if existing:
                return JSONResponse({"status": "already_joined"})

            count = await conn.fetchval(
                "SELECT COUNT(*) FROM map_meeting_participants WHERE meeting_id=$1 AND status='accepted'",
                meeting_id)
            if count >= meeting["max_participants"]:
                raise HTTPException(status_code=400, detail="Meeting is full")

            await conn.execute(
                "INSERT INTO map_meeting_participants (meeting_id, user_id, status) VALUES ($1,$2,'accepted')",
                meeting_id, user["id"])

            await conn.close()
            return JSONResponse({"status": "joined", "meeting_id": meeting_id, "participants_count": count + 1})
        except Exception as e:
            await conn.close()
            raise
    except Exception as e:
        logging.error(f"Error joining meeting: {e}")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@app.delete("/api/meetings/{meeting_id}")
async def delete_meeting(meeting_id: int, request: Request):
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID required")

        conn = await get_connection()
        user = await conn.fetchrow("SELECT id FROM users WHERE telegram_id=$1", telegram_id)
        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        meeting = await conn.fetchrow(
            "SELECT * FROM map_meeting_requests WHERE id=$1 AND user_id=$2",
            meeting_id, user["id"])
        if not meeting:
            await conn.close()
            raise HTTPException(status_code=403, detail="Not authorized")

        await conn.execute(
            "UPDATE map_meeting_requests SET status='deleted' WHERE id=$1", meeting_id)
        await conn.close()
        return JSONResponse({"success": True})
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
        user = await conn.fetchrow("SELECT id FROM users WHERE telegram_id=$1", telegram_id)
        if not user:
            await conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        participant = await conn.fetchrow(
            "SELECT * FROM map_meeting_participants WHERE meeting_id=$1 AND user_id=$2 AND status='accepted'",
            meeting_id, user["id"])
        if not participant:
            await conn.close()
            raise HTTPException(status_code=404, detail="Not a participant")

        is_creator = await conn.fetchrow(
            "SELECT * FROM map_meeting_requests WHERE id=$1 AND user_id=$2", meeting_id, user["id"])
        if is_creator:
            await conn.close()
            return JSONResponse({"error": "You are the organizer. Use delete instead.", "is_organizer": True})

        await conn.execute(
            "DELETE FROM map_meeting_participants WHERE meeting_id=$1 AND user_id=$2",
            meeting_id, user["id"])
        await conn.close()
        return JSONResponse({"success": True})
    except Exception as e:
        logging.error(f"Error leaving meeting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/meetings/{meeting_id}/status")
async def get_meeting_status(meeting_id: int, telegram_id: int):
    try:
        conn = await get_connection()
        user = await conn.fetchrow("SELECT id FROM users WHERE telegram_id=$1", telegram_id)
        if not user:
            await conn.close()
            return JSONResponse({"status": "not_found"})

        participant = await conn.fetchrow(
            "SELECT status FROM map_meeting_participants WHERE meeting_id=$1 AND user_id=$2",
            meeting_id, user["id"])
        await conn.close()
        return JSONResponse({"status": participant["status"] if participant else "not_joined"})
    except Exception as e:
        logging.error(f"Error getting meeting status: {e}")
        return JSONResponse({"status": "error"})


@app.get("/api/categories")
async def get_categories():
    return JSONResponse([
        {"id": "all", "name": "Все категории", "icon": "🗺️"},
        {"id": "coffee", "name": "☕ Кофе/Бар", "icon": "☕"},
        {"id": "sports", "name": "🏃 Спорт", "icon": "🏃"},
        {"id": "cinema", "name": "🎬 Кино", "icon": "🎬"},
        {"id": "games", "name": "🎮 Игры", "icon": "🎮"},
    ])


@app.get("/api/time-filters")
async def get_time_filters():
    return JSONResponse([
        {"id": "all", "name": "Любое время", "icon": "⏰"},
        {"id": "today", "name": "👋 Сегодня", "icon": "👋"},
        {"id": "tomorrow", "name": "📅 Завтра", "icon": "📅"},
        {"id": "evening", "name": "🌆 Вечером", "icon": "🌆"},
        {"id": "weekend", "name": "🌞 Выходные", "icon": "🌞"},
    ])