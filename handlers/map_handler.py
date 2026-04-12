from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
import logging

from database import db
from keyboards import get_main_menu_keyboard, get_profile_keyboard   # ← исправленный импорт
from utils import decrypt_data
from config import config

router = Router()


def _build_map_url(telegram_id: int) -> str:
    """Возвращает URL мини-апп с user_id. Предпочитает HTTPS (туннель)."""
    base = config.MINI_APP_URL if config.MINI_APP_URL else f"http://localhost:{config.WEB_SERVER_PORT}"
    return f"{base}/mini?user_id={telegram_id}"


# ── Карта встреч ──────────────────────────────────────────────────────────────

@router.message(F.text == "🗺️ Карта встреч")
async def show_map_menu(message: Message, state: FSMContext):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1 AND is_authenticated = TRUE",
            message.from_user.id,
        )

    if not user:
        await message.answer(
            "❌ Вы не авторизованы!",
            reply_markup=get_main_menu_keyboard(is_authenticated=False),
        )
        return

    map_url = _build_map_url(message.from_user.id)
    is_https = map_url.startswith("https://")

    keyboard_buttons = []

    if is_https:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="📍 Открыть карту встреч",
                web_app=WebAppInfo(url=map_url),
            )
        ])
    else:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="📍 Открыть карту встреч (браузер)",
                url=map_url,
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="📋 Мои встречи на карте", callback_data="my_map_meetings"),
        InlineKeyboardButton(text="📊 Статистика карты", callback_data="map_stats"),
    ])
    keyboard_buttons.append([
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_menu"),
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    status_note = "" if is_https else "\n\n⚠️ Карта открывается в браузере, т.к. туннель не запущен."

    await message.answer(
        "🗺️ <b>Карта встреч</b>\n\n"
        "На карте вы можете:\n"
        "• 📍 Найти встречи рядом с вами\n"
        "• 📝 Создать свою встречу\n"
        "• 👥 Присоединиться к другим встречам\n"
        "• 📋 Управлять своими встречами"
        + status_note,
        reply_markup=keyboard,
    )


# ── Мои встречи на карте ──────────────────────────────────────────────────────

@router.callback_query(F.data == "my_map_meetings")
async def my_map_meetings(callback: CallbackQuery):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback.from_user.id,
        )

        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        created_meetings = await conn.fetch('''
            SELECT mr.*,
                   COALESCE(participants.count, 0) as current_participants
            FROM map_meeting_requests mr
            LEFT JOIN (
                SELECT meeting_id, COUNT(*) as count
                FROM map_meeting_participants
                WHERE status = 'accepted'
                GROUP BY meeting_id
            ) participants ON participants.meeting_id = mr.id
            WHERE mr.user_id = $1 AND mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
            ORDER BY mr.created_at DESC
        ''', user['id'])

        joined_meetings = await conn.fetch('''
            SELECT mr.*,
                   u.username as creator_username,
                   u.first_name as creator_name,
                   COALESCE(participants.count, 0) as current_participants
            FROM map_meeting_participants mp
            JOIN map_meeting_requests mr ON mr.id = mp.meeting_id
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
        ''', user['id'])

    response = "📋 <b>Мои встречи на карте:</b>\n\n"

    if created_meetings:
        response += "👑 <b>Созданные мной:</b>\n"
        for i, m in enumerate(created_meetings, 1):
            response += (
                f"{i}. <b>{m['title']}</b>\n"
                f"   📅 {m['meeting_time']}\n"
                f"   👥 Участников: {m['current_participants']}/{m['max_participants']}\n"
                f"   🆔 ID: {m['id']}\n\n"
            )

    if joined_meetings:
        response += "✅ <b>Я присоединился:</b>\n"
        for i, m in enumerate(joined_meetings, 1):
            response += (
                f"{i}. <b>{m['title']}</b>\n"
                f"   👤 Организатор: {m['creator_name']}\n"
                f"   📅 {m['meeting_time']}\n"
                f"   👥 Участников: {m['current_participants']}/{m['max_participants']}\n"
                f"   🆔 ID: {m['id']}\n\n"
            )

    if not created_meetings and not joined_meetings:
        response += "📭 У вас пока нет встреч на карте.\nСоздайте первую встречу или присоединитесь к существующей!"

    await callback.message.answer(response, reply_markup=get_main_menu_keyboard(is_authenticated=True))
    await callback.answer()


# ── Статистика карты ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "map_stats")
async def map_stats(callback: CallbackQuery):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback.from_user.id,
        )

        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        total_meetings = await conn.fetchval(
            "SELECT COUNT(*) FROM map_meeting_requests WHERE status = 'active'"
        )
        my_created = await conn.fetchval(
            "SELECT COUNT(*) FROM map_meeting_requests WHERE user_id = $1 AND status = 'active'",
            user['id'],
        )
        my_joined = await conn.fetchval('''
            SELECT COUNT(*) FROM map_meeting_participants mp
            JOIN map_meeting_requests mr ON mr.id = mp.meeting_id
            WHERE mp.user_id = $1 AND mp.status = 'accepted' AND mr.status = 'active'
        ''', user['id'])
        active_participants = await conn.fetchval(
            "SELECT COUNT(DISTINCT user_id) FROM map_meeting_participants WHERE status = 'accepted'"
        )

    await callback.message.answer(
        "📊 <b>Статистика карты встреч:</b>\n\n"
        f"🗺️ Всего активных встреч: {total_meetings}\n"
        f"👑 Моих созданных встреч: {my_created}\n"
        f"✅ Моих присоединений: {my_joined}\n"
        f"👥 Активных участников: {active_participants}\n\n"
        "Присоединяйтесь к встречам и создавайте свои!",
        reply_markup=get_main_menu_keyboard(is_authenticated=True),
    )
    await callback.answer()


# ── Назад в меню ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "🏠 Вы вернулись в главное меню",
        reply_markup=get_main_menu_keyboard(is_authenticated=True),
    )
    await callback.answer()


# ── Заглушка при недоступном туннеле ─────────────────────────────────────────

@router.callback_query(F.data == "tunnel_not_ready")
async def tunnel_not_ready(callback: CallbackQuery):
    await callback.answer(
        "⏳ Туннель ещё не запущен. Попробуйте через несколько секунд.",
        show_alert=True,
    )


# ── Синхронизация встречи с профилем ─────────────────────────────────────────

@router.message(F.text == "🔄 Синхронизировать")
async def sync_profile_with_meetings(message: Message):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1 AND is_authenticated = TRUE",
            message.from_user.id,
        )

        if not user:
            await message.answer(
                "❌ Вы не авторизованы!",
                reply_markup=get_main_menu_keyboard(is_authenticated=False),
            )
            return

        latest_meeting = await conn.fetchrow('''
            SELECT mr.* FROM map_meeting_requests mr
            WHERE mr.user_id = $1 AND mr.status = 'active'
            AND (mr.expires_at IS NULL OR mr.expires_at > NOW())
            ORDER BY mr.created_at DESC
            LIMIT 1
        ''', user['id'])

        if latest_meeting:
            await conn.execute('''
                UPDATE users
                SET activity_interest = $1,
                    activity_location = $2,
                    activity_time     = $3,
                    activity_description = $4,
                    is_published      = TRUE
                WHERE id = $5
            ''',
                f"📍 {latest_meeting['title']}",
                latest_meeting['address'] or latest_meeting['title'],
                latest_meeting['meeting_time'],
                latest_meeting['description'] or "Встреча создана на карте",
                user['id'],
            )

            await message.answer(
                f"✅ Профиль синхронизирован с последней встречей!\n\n"
                f"🎯 Активность: {latest_meeting['title']}\n"
                f"📍 Место: {latest_meeting['address'] or latest_meeting['title']}\n"
                f"⏰ Время: {latest_meeting['meeting_time']}\n\n"
                f"Теперь другие пользователи могут найти вас по этой активности!",
                reply_markup=get_profile_keyboard(True),
            )
        else:
            await message.answer(
                "📭 У вас нет активных встреч на карте для синхронизации.\n"
                "Создайте встречу на карте или присоединитесь к существующей.",
                reply_markup=get_main_menu_keyboard(is_authenticated=True),
            )