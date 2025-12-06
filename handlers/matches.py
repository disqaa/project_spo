from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncio

from database import db
from keyboards import (
    get_main_menu_keyboard, get_profile_keyboard,
    get_meetings_keyboard, get_meeting_confirmation_keyboard,
    get_meeting_details_keyboard
)
from utils import decrypt_data

router = Router()


# Мои встречи
@router.message(F.text == "🤝 Мои встречи")
async def my_meetings(message: Message):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1 AND is_authenticated = TRUE",
            message.from_user.id
        )

        if not user:
            await message.answer(
                "❌ Вы не авторизованы!",
                reply_markup=get_main_menu_keyboard(is_authenticated=False)
            )
            return

        # Получаем статистику встреч
        pending_matches = await conn.fetchval('''
            SELECT COUNT(*) FROM matches 
            WHERE (user1_id = $1 OR user2_id = $1) 
            AND status = 'pending'
        ''', user['id'])

        confirmed_matches = await conn.fetchval('''
            SELECT COUNT(*) FROM matches 
            WHERE (user1_id = $1 OR user2_id = $1) 
            AND status = 'accepted'
        ''', user['id'])

        total_matches = await conn.fetchval('''
            SELECT COUNT(*) FROM matches 
            WHERE user1_id = $1 OR user2_id = $1
        ''', user['id'])

    meetings_text = (
        "🤝 **Мои встречи:**\n\n"
        f"📊 Всего встреч: {total_matches}\n"
        f"⏳ Ожидают подтверждения: {pending_matches}\n"
        f"✅ Подтвержденные встречи: {confirmed_matches}\n\n"
        "Выберите раздел:"
    )

    await message.answer(
        meetings_text,
        parse_mode="Markdown",
        reply_markup=get_meetings_keyboard()
    )


# Запросы на встречу
@router.message(F.text == "📝 Запросы на встречу")
async def meeting_requests(message: Message):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if not user:
            return

        # Получаем запросы на встречу (где пользователь - user2 и статус pending)
        requests = await conn.fetch('''
            SELECT m.*, u.username, u.first_name, u.age, u.activity_interest, 
                   u.activity_location, u.activity_time, u.activity_description
            FROM matches m
            JOIN users u ON u.id = m.user1_id
            WHERE m.user2_id = $1 AND m.status = 'pending'
            ORDER BY m.created_at DESC
        ''', user['id'])

    if not requests:
        await message.answer(
            "📭 У вас нет запросов на встречу",
            reply_markup=get_meetings_keyboard()
        )
        return

    for req in requests:
        # Дешифруем данные
        decrypted_first_name = decrypt_data(req['first_name'])
        decrypted_location = decrypt_data(req['activity_location']) if req['activity_location'] else "Не указано"
        decrypted_description = decrypt_data(req['activity_description']) if req['activity_description'] else ""

        request_text = (
            f"📩 **Новый запрос на встречу!**\n\n"
            f"👤 От: {decrypted_first_name} (@{req['username']})\n"
            f"🎂 Возраст: {req['age']} лет\n\n"
            f"🎯 Предлагает: {req['activity_interest']}\n"
            f"📍 Место: {decrypted_location}\n"
            f"⏰ Время: {req['activity_time']}\n"
        )

        if decrypted_description:
            request_text += f"📝 Описание: {decrypted_description}\n"

        request_text += f"\n📅 Запрос отправлен: {req['created_at'].strftime('%d.%m.%Y %H:%M')}"

        await message.answer(
            request_text,
            parse_mode="Markdown",
            reply_markup=get_meeting_confirmation_keyboard(req['id'])
        )


# Подтвержденные встречи
@router.message(F.text == "✅ Подтвержденные встречи")
async def confirmed_meetings(message: Message):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if not user:
            return

        # Получаем подтвержденные встречи
        matches = await conn.fetch('''
            SELECT m.*, 
                   u1.username as user1_username, u1.first_name as user1_first_name,
                   u2.username as user2_username, u2.first_name as user2_first_name,
                   CASE 
                       WHEN $1 = m.user1_id THEN u2.id
                       ELSE u1.id
                   END as other_user_id,
                   CASE 
                       WHEN $1 = m.user1_id THEN u2.username
                       ELSE u1.username
                   END as other_username,
                   CASE 
                       WHEN $1 = m.user1_id THEN u2.first_name
                       ELSE u1.first_name
                   END as other_first_name
            FROM matches m
            JOIN users u1 ON u1.id = m.user1_id
            JOIN users u2 ON u2.id = m.user2_id
            WHERE (m.user1_id = $1 OR m.user2_id = $1) 
            AND m.status = 'accepted'
            ORDER BY m.meeting_confirmed_at DESC
        ''', user['id'])

    if not matches:
        await message.answer(
            "📭 У вас нет подтвержденных встреч",
            reply_markup=get_meetings_keyboard()
        )
        return

    for match in matches:
        # Определяем, кто другой пользователь
        other_user_id = match['other_user_id']

        # Получаем информацию о другом пользователе
        async with db.pool.acquire() as conn:
            other_user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                other_user_id
            )

        if other_user:
            decrypted_first_name = decrypt_data(other_user['first_name'])
            decrypted_location = decrypt_data(other_user['activity_location']) if other_user[
                'activity_location'] else "Не указано"

            meeting_text = (
                f"🤝 **Подтвержденная встреча**\n\n"
                f"👤 С: {decrypted_first_name} (@{other_user['username']})\n"
                f"🎂 Возраст: {other_user['age']} лет\n\n"
                f"🎯 Активность: {other_user['activity_interest']}\n"
                f"📍 Место: {decrypted_location}\n"
                f"⏰ Время: {other_user['activity_time']}\n\n"
                f"✅ Подтверждена: {match['meeting_confirmed_at'].strftime('%d.%m.%Y %H:%M') if match['meeting_confirmed_at'] else 'Не указано'}"
            )

            await message.answer(
                meeting_text,
                parse_mode="Markdown",
                reply_markup=get_meeting_details_keyboard(match['id'])
            )


# Обработка принятия встречи
@router.callback_query(F.data.startswith("accept_meeting_"))
async def accept_meeting(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[2])

    async with db.pool.acquire() as conn:
        # Получаем информацию о встрече
        match = await conn.fetchrow(
            "SELECT * FROM matches WHERE id = $1",
            match_id
        )

        if not match:
            await callback.answer("❌ Встреча не найдена")
            return

        # Получаем информацию о текущем пользователе
        current_user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        if not current_user:
            await callback.answer("❌ Пользователь не найден")
            return

        # Определяем, кто user1, кто user2
        is_user1 = current_user['id'] == match['user1_id']

        if is_user1:
            # Текущий пользователь - инициатор встречи
            await conn.execute(
                "UPDATE matches SET user1_confirmed = TRUE WHERE id = $1",
                match_id
            )
        else:
            # Текущий пользователь - получатель
            await conn.execute(
                "UPDATE matches SET user2_confirmed = TRUE WHERE id = $1",
                match_id
            )

        # Проверяем, подтвердили ли оба
        updated_match = await conn.fetchrow(
            "SELECT * FROM matches WHERE id = $1",
            match_id
        )

        if updated_match['user1_confirmed'] and updated_match['user2_confirmed']:
            # Оба подтвердили - встреча подтверждена
            await conn.execute('''
                UPDATE matches 
                SET status = 'accepted', meeting_confirmed_at = CURRENT_TIMESTAMP 
                WHERE id = $1
            ''', match_id)

            # Обновляем счетчики встреч у пользователей
            await conn.execute(
                "UPDATE users SET matches_count = matches_count + 1 WHERE id = $1",
                match['user1_id']
            )
            await conn.execute(
                "UPDATE users SET matches_count = matches_count + 1 WHERE id = $1",
                match['user2_id']
            )

            # Получаем информацию о другом пользователе для уведомления
            other_user_id = match['user2_id'] if is_user1 else match['user1_id']
            other_user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                other_user_id
            )

            if other_user:
                # Отправляем уведомление другому пользователю
                decrypted_current_name = decrypt_data(current_user['first_name'])
                try:
                    await callback.bot.send_message(
                        chat_id=other_user['telegram_id'],
                        text=f"🎉 {decrypted_current_name} подтвердил(а) встречу!\n\n"
                             f"🤝 **Встреча подтверждена!**\n"
                             f"📞 Контакт: @{current_user['username']}\n\n"
                             f"Не забудьте договориться о деталях встречи!"
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление: {e}")

            # Отправляем уведомление текущему пользователю
            if other_user:
                decrypted_other_name = decrypt_data(other_user['first_name'])
                await callback.message.edit_text(
                    f"🎉 **Встреча подтверждена!**\n\n"
                    f"🤝 Вы договорились о встрече с {decrypted_other_name}\n"
                    f"📞 Контакт: @{other_user['username']}\n\n"
                    f"Не забудьте договориться о деталях встречи!",
                    parse_mode="Markdown"
                )

            await callback.answer("✅ Встреча подтверждена!")
        else:
            # Ждем подтверждения от второго пользователя
            await callback.message.edit_text(
                "✅ Вы подтвердили встречу! Ждем подтверждения от второго участника.",
                parse_mode="Markdown"
            )
            await callback.answer("✅ Подтверждение отправлено")


# Обработка отклонения встречи
@router.callback_query(F.data.startswith("reject_meeting_"))
async def reject_meeting(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[2])

    async with db.pool.acquire() as conn:
        # Обновляем статус встречи
        await conn.execute(
            "UPDATE matches SET status = 'rejected' WHERE id = $1",
            match_id
        )

        # Получаем информацию о встрече для уведомления другого пользователя
        match = await conn.fetchrow(
            "SELECT * FROM matches WHERE id = $1",
            match_id
        )

        current_user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        if match and current_user:
            # Определяем, кто другой пользователь
            other_user_id = match['user2_id'] if current_user['id'] == match['user1_id'] else match['user1_id']
            other_user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                other_user_id
            )

            if other_user:
                decrypted_current_name = decrypt_data(current_user['first_name'])
                try:
                    await callback.bot.send_message(
                        chat_id=other_user['telegram_id'],
                        text=f"😔 {decrypted_current_name} отклонил(а) ваш запрос на встречу."
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление: {e}")

    await callback.message.edit_text(
        "❌ Вы отклонили запрос на встречу.",
        parse_mode="Markdown"
    )
    await callback.answer("❌ Встреча отклонена")


# Обработка отмены встречи
@router.callback_query(F.data.startswith("cancel_meeting_"))
async def cancel_meeting(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[2])

    async with db.pool.acquire() as conn:
        # Обновляем статус встречи
        await conn.execute(
            "UPDATE matches SET status = 'cancelled' WHERE id = $1",
            match_id
        )

        # Получаем информацию о встрече для уведомления другого пользователя
        match = await conn.fetchrow(
            "SELECT * FROM matches WHERE id = $1",
            match_id
        )

        current_user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        if match and current_user:
            # Определяем, кто другой пользователь
            other_user_id = match['user2_id'] if current_user['id'] == match['user1_id'] else match['user1_id']
            other_user = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                other_user_id
            )

            if other_user:
                decrypted_current_name = decrypt_data(current_user['first_name'])
                try:
                    await callback.bot.send_message(
                        chat_id=other_user['telegram_id'],
                        text=f"😔 {decrypted_current_name} отменил(а) вашу встречу."
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление: {e}")

    await callback.message.edit_text(
        "❌ Вы отменили встречу.",
        parse_mode="Markdown"
    )
    await callback.answer("❌ Встреча отменена")


# Обработка кнопки "Написать"
@router.callback_query(F.data.startswith("message_"))
async def send_message_to_match(callback: CallbackQuery):
    match_id = int(callback.data.split("_")[1])

    async with db.pool.acquire() as conn:
        match = await conn.fetchrow(
            "SELECT * FROM matches WHERE id = $1",
            match_id
        )

        current_user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        if match and current_user:
            # Определяем, кто другой пользователь
            other_user_id = match['user2_id'] if current_user['id'] == match['user1_id'] else match['user1_id']
            other_user = await conn.fetchrow(
                "SELECT username, first_name FROM users WHERE id = $1",
                other_user_id
            )

            if other_user:
                decrypted_name = decrypt_data(other_user['first_name'])
                await callback.message.answer(
                    f"📞 **Контакт для связи:**\n\n"
                    f"👤 Имя: {decrypted_name}\n"
                    f"📱 Telegram: @{other_user['username']}\n\n"
                    f"Напишите пользователю в Telegram для обсуждения деталей встречи!",
                    parse_mode="Markdown"
                )

    await callback.answer()