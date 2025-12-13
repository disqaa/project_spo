from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from database import db
from keyboards import get_main_menu_keyboard, get_back_to_menu_keyboard
from utils import decrypt_data
import json
from config import config

router = Router()


class MapMeetingStates(StatesGroup):
    choosing_action = State()
    creating_title = State()
    creating_description = State()
    choosing_time = State()
    choosing_venue = State()
    setting_location = State()


# Кнопка для доступа к карте через миниаппу
@router.message(F.text == "🗺️ Карта встреч")
async def show_map_menu(message: Message, state: FSMContext):
    # Проверяем авторизацию
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

    # Проверяем, есть ли URL для миниаппы
    mini_app_url = None

    # Сначала пробуем получить из конфига
    if hasattr(config, 'MINI_APP_URL') and config.MINI_APP_URL:
        mini_app_url = f"{config.MINI_APP_URL}/mini"
        logging.info(f"Используем URL из конфига: {mini_app_url}")

    # Если нет в конфиге, пробуем получить из файла или использовать локальный
    if not mini_app_url:
        try:
            # Пробуем прочитать из файла
            with open('ngrok_url.txt', 'r') as f:
                for line in f:
                    if 'Mini App URL:' in line:
                        mini_app_url = line.split('Mini App URL:')[1].strip()
                        break
        except:
            # Используем локальный адрес
            mini_app_url = f"http://localhost:{config.WEB_SERVER_PORT}/mini"

    logging.info(f"Финальный URL мини-аппы: {mini_app_url}")

    # Создаем клавиатуру с кнопкой для мини-аппы
    keyboard_buttons = []

    if mini_app_url.startswith('https://'):
        # HTTPS URL - можно использовать WebApp кнопку
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="📍 Открыть карту в мини-аппе",
                web_app=WebAppInfo(url=mini_app_url)
            )
        ])
    else:
        # HTTP URL - используем обычную ссылку
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="📍 Открыть карту встреч (в браузере)",
                url=mini_app_url
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="📝 Создать заявку", callback_data="create_map_meeting"),
        InlineKeyboardButton(text="📋 Мои заявки", callback_data="my_map_meetings")
    ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="🔄 Обновить URL мини-аппы", callback_data="refresh_mini_app_url"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_menu")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    # Текст сообщения
    if mini_app_url.startswith('https://'):
        message_text = (
            "🗺️ **Карта встреч**\n\n"
            "Теперь доступна мини-аппа прямо в Telegram!\n\n"
            "Вы можете:\n"
            "• 📍 Открыть интерактивную карту с встречами\n"
            "• 📝 Создать свою заявку на встречу\n"
            "• 📋 Просмотреть свои заявки\n"
            "• 👥 Присоединиться к другим встречам\n\n"
            "Используйте кнопку ниже для открытия мини-аппы:"
        )
    else:
        message_text = (
            "🗺️ **Карта встреч**\n\n"
            "⚠️ *Внимание: для мини-аппы в Telegram требуется HTTPS*\n\n"
            "Вы можете:\n"
            "• 📍 Открыть карту в браузере\n"
            "• 📝 Создать свою заявку на встречу\n"
            "• 📋 Просмотреть свои заявки\n\n"
            "Для работы мини-аппы в Telegram:\n"
            "1. Запустите ngrok: `ngrok http 8000 --region=eu`\n"
            "2. Скопируйте HTTPS URL\n"
            "3. Нажмите '🔄 Обновить URL мини-аппы' и вставьте URL\n"
            "4. Обновите настройки в @BotFather"
        )

    await message.answer(
        message_text,
        reply_markup=keyboard
    )


# Обработка обновления URL мини-аппы
@router.callback_query(F.data == "refresh_mini_app_url")
async def refresh_mini_app_url(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔄 **Обновление URL мини-аппы:**\n\n"
        "Пожалуйста, введите новый URL для мини-аппы.\n"
        "URL должен начинаться с https:// и заканчиваться на /mini\n\n"
        "Пример: https://your-domain.ngrok-free.dev/mini\n\n"
        "Чтобы получить URL:\n"
        "1. Запустите ngrok: `ngrok http 8000 --region=eu`\n"
        "2. Скопируйте HTTPS URL (например: https://abc123.ngrok-free.dev)\n"
        "3. Добавьте /mini в конце\n\n"
        "Введите URL или отправьте 'отмена' для отмены:"
    )

    await state.set_state("waiting_for_mini_app_url")
    await state.update_data(message_id=callback.message.message_id)


# Обработка ввода нового URL
@router.message(F.text, lambda message: message.text.lower() != "отмена")
async def process_mini_app_url(message: Message, state: FSMContext):
    if await state.get_state() != "waiting_for_mini_app_url":
        return

    url = message.text.strip()

    # Проверяем URL
    if not url.startswith('http'):
        await message.answer("❌ URL должен начинаться с http:// или https://")
        return

    # Сохраняем URL в файл
    try:
        if url.endswith('/mini'):
            base_url = url[:-5]
        else:
            base_url = url

        # Обновляем конфиг
        import os
        from dotenv import set_key, load_dotenv

        # Загружаем текущий .env
        load_dotenv()

        # Обновляем переменную
        set_key('.env', 'MINI_APP_URL', base_url)

        # Обновляем объект config
        config.MINI_APP_URL = base_url

        # Сохраняем в файл для информации
        with open('ngrok_url.txt', 'w') as f:
            f.write(f"Public URL: {base_url}\n")
            f.write(f"Mini App URL: {base_url}/mini\n")

        await message.answer(
            f"✅ URL мини-аппы обновлен!\n\n"
            f"Новый URL: {base_url}/mini\n\n"
            "Теперь обновите настройки в @BotFather:\n"
            "1. Откройте @BotFather\n"
            "2. Выберите вашего бота\n"
            "3. Нажмите 'Edit Bot'\n"
            "4. Нажмите 'Edit Web App'\n"
            "5. Вставьте URL: {base_url}/mini\n"
            "6. Сохраните изменения"
        )

    except Exception as e:
        logging.error(f"Ошибка при сохранении URL: {e}")
        await message.answer("❌ Ошибка при сохранении URL. Попробуйте снова.")

    await state.clear()


@router.message(F.text.lower() == "отмена")
async def cancel_mini_app_url(message: Message, state: FSMContext):
    if await state.get_state() == "waiting_for_mini_app_url":
        await state.clear()
        await message.answer("❌ Обновление URL отменено.")


# Обработка кнопки "Назад в меню"
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "🏠 Вы вернулись в главное меню",
        reply_markup=get_main_menu_keyboard(is_authenticated=True)
    )


# Обработка кнопки "Создать заявку"
@router.callback_query(F.data == "create_map_meeting")
async def create_map_meeting(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)

    # Проверяем, есть ли HTTPS URL для мини-аппы
    mini_app_url = None
    if hasattr(config, 'MINI_APP_URL') and config.MINI_APP_URL:
        mini_app_url = f"{config.MINI_APP_URL}/mini"

    if mini_app_url and mini_app_url.startswith('https://'):
        # Есть HTTPS URL - открываем мини-аппу для создания встречи
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Создать встречу в мини-аппе",
                    web_app=WebAppInfo(url=f"{mini_app_url}?mode=create")
                )
            ],
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_menu")
            ]
        ])

        await callback.message.answer(
            "📝 **Создание встречи:**\n\n"
            "Для создания встречи используйте мини-аппу.\n"
            "Нажмите кнопку ниже, чтобы открыть карту и выбрать место.",
            reply_markup=keyboard
        )
    else:
        # Нет HTTPS URL - предлагаем открыть в браузере
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Открыть карту в браузере",
                    url=f"http://localhost:{config.WEB_SERVER_PORT}/"
                )
            ],
            [
                InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_menu")
            ]
        ])

        await callback.message.answer(
            "📝 **Создание встречи:**\n\n"
            "Для создания встречи откройте карту в браузере.\n"
            "Выберите место на карте и создайте заявку.",
            reply_markup=keyboard
        )


# Обработка кнопки "Мои заявки"
@router.callback_query(F.data == "my_map_meetings")
async def my_map_meetings(callback: CallbackQuery):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        if not user:
            await callback.answer("❌ Пользователь не найден")
            return

        # Получаем заявки пользователя
        meetings = await conn.fetch('''
            SELECT mr.*, v.name as venue_name
            FROM map_meeting_requests mr
            LEFT JOIN venues v ON v.id = mr.venue_id
            WHERE mr.user_id = $1 AND mr.status = 'active'
            ORDER BY mr.created_at DESC
        ''', user['id'])

    if not meetings:
        await callback.message.answer(
            "📭 У вас нет активных заявок на встречи.",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        return

    response = "📋 **Ваши активные заявки:**\n\n"

    for i, meeting in enumerate(meetings, 1):
        participants_count = await db.pool.fetchval(
            "SELECT COUNT(*) FROM map_meeting_participants WHERE meeting_id = $1 AND status = 'accepted'",
            meeting['id']
        )

        response += f"{i}. **{meeting['title']}**\n"
        response += f"   📍 {meeting['venue_name'] or 'Место уточняется'}\n"
        response += f"   ⏰ {meeting['meeting_time']}\n"
        response += f"   👥 Участников: {participants_count}/{meeting['max_participants']}\n"
        response += f"   🆔 ID: {meeting['id']}\n\n"

    await callback.message.answer(
        response,
        reply_markup=get_main_menu_keyboard(is_authenticated=True)
    )