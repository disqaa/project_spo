# handlers/map.py - исправляем импорты

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import logging

from database import db
from keyboards import (
    get_main_menu_keyboard, get_cancel_keyboard,
    get_confirmation_keyboard, get_map_menu_keyboard,
    get_places_list_keyboard, get_place_details_keyboard
    # Убрали get_meeting_types_keyboard, так как она не используется или заменим на другую
)
from utils import decrypt_data, encrypt_data

router = Router()


class PlaceMeetingStates(StatesGroup):
    choosing_place = State()
    choosing_time = State()
    entering_description = State()
    choosing_interest = State()
    confirmation = State()


# Основное меню карты
# handlers/map.py - исправленная функция map_menu

@router.message(F.text == "🗺️ Карта встреч")
async def map_menu(message: Message):
    try:
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

        # Используем HTML разметку вместо Markdown
        await message.answer(
            "🗺️ <b>Карта встреч</b>\n\n"
            "Здесь вы можете:\n"
            "📍 Просмотреть заведения на карте\n"
            "📋 Посмотреть список всех заведений\n"
            "📅 Создать заявку на встречу в заведении\n"
            "👥 Присоединиться к существующей встрече\n\n"
            "Для открытия карты с заведениями перейдите по ссылке:\n"
            f"<a href='http://localhost:5000/map?user_id={message.from_user.id}'>Открыть карту</a>",
            parse_mode="HTML",  # Изменено с Markdown на HTML
            reply_markup=get_map_menu_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка в map_menu: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )

# Список всех заведений
@router.message(F.text == "📋 Список заведений")
async def list_places(message: Message, state: FSMContext):
    async with db.pool.acquire() as conn:
        places = await conn.fetch('''
            SELECT id, name, category, address, description, rating
            FROM places 
            WHERE is_active = TRUE
            ORDER BY rating DESC, name
            LIMIT 50
        ''')

    if not places:
        await message.answer(
            "📭 Пока нет добавленных заведений.",
            reply_markup=get_map_menu_keyboard()
        )
        return

    text = "📋 **Список заведений:**\n\n"
    for i, place in enumerate(places, 1):
        text += f"{i}. **{place['name']}**\n"
        text += f"   🏷️ Категория: {place['category']}\n"
        text += f"   ⭐ Рейтинг: {place['rating'] or 'Нет'}\n"
        text += f"   📍 Адрес: {place['address'][:50]}...\n"
        if place['description']:
            text += f"   📝 {place['description'][:60]}...\n"
        text += "\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_places_list_keyboard()
    )


# Создать заявку на встречу
@router.message(F.text == "📅 Создать встречу")
async def create_meeting_start(message: Message, state: FSMContext):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1 AND is_authenticated = TRUE",
            message.from_user.id
        )

        if not user:
            await message.answer("❌ Вы не авторизованы!")
            return

        # Получаем ближайшие заведения
        places = await conn.fetch('''
            SELECT id, name, category, address
            FROM places 
            WHERE is_active = TRUE
            ORDER BY name
            LIMIT 20
        ''')

    if not places:
        await message.answer(
            "❌ Пока нет доступных заведений.",
            reply_markup=get_map_menu_keyboard()
        )
        return

    # Создаем клавиатуру с заведениями
    keyboard = []
    for place in places:
        keyboard.append([
            InlineKeyboardButton(
                text=f"{place['name']} ({place['category']})",
                callback_data=f"choose_place_{place['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")])

    await message.answer(
        "📍 **Выберите заведение для встречи:**\n\n"
        "Нажмите на заведение из списка ниже:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(PlaceMeetingStates.choosing_place)


# Обработка выбора заведения
@router.callback_query(PlaceMeetingStates.choosing_place, F.data.startswith("choose_place_"))
async def process_place_choice(callback: CallbackQuery, state: FSMContext):
    place_id = int(callback.data.split("_")[2])

    async with db.pool.acquire() as conn:
        place = await conn.fetchrow(
            "SELECT * FROM places WHERE id = $1",
            place_id
        )

    if not place:
        await callback.answer("❌ Заведение не найдено")
        return

    await state.update_data(place_id=place_id, place_name=place['name'])

    # Предлагаем выбрать время
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⌛ Через 1 час", callback_data="time_1h"),
            InlineKeyboardButton(text="⏰ Сегодня вечером", callback_data="time_evening")
        ],
        [
            InlineKeyboardButton(text="📅 Завтра", callback_data="time_tomorrow"),
            InlineKeyboardButton(text="🌞 В выходные", callback_data="time_weekend")
        ],
        [
            InlineKeyboardButton(text="📝 Указать своё время", callback_data="time_custom"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")
        ]
    ])

    await callback.message.edit_text(
        f"📍 **Выбрано:** {place['name']}\n"
        f"🏷️ Категория: {place['category']}\n"
        f"📌 Адрес: {place['address']}\n\n"
        "⏰ **Выберите время встречи:**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(PlaceMeetingStates.choosing_time)


# Обработка выбора времени
@router.callback_query(PlaceMeetingStates.choosing_time, F.data.startswith("time_"))
async def process_time_choice(callback: CallbackQuery, state: FSMContext):
    time_choice = callback.data

    now = datetime.now()
    meeting_time = None

    if time_choice == "time_1h":
        meeting_time = now + timedelta(hours=1)
    elif time_choice == "time_evening":
        # Сегодня в 19:00
        meeting_time = datetime(now.year, now.month, now.day, 19, 0)
        if meeting_time < now:
            meeting_time += timedelta(days=1)
    elif time_choice == "time_tomorrow":
        # Завтра в 18:00
        tomorrow = now + timedelta(days=1)
        meeting_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 18, 0)
    elif time_choice == "time_weekend":
        # Ближайшая суббота в 15:00
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7  # Если сегодня суббота, то следующую
        meeting_time = now + timedelta(days=days_until_saturday)
        meeting_time = datetime(meeting_time.year, meeting_time.month, meeting_time.day, 15, 0)
    elif time_choice == "time_custom":
        await callback.message.edit_text(
            "📝 **Введите дату и время встречи:**\n\n"
            "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2024 19:30",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")]
            ])
        )
        # Остаемся в том же состоянии для обработки пользовательского ввода
        return

    if meeting_time:
        await state.update_data(meeting_time=meeting_time)
        await ask_interest(callback, state)


# Обработка пользовательского ввода времени
@router.message(PlaceMeetingStates.choosing_time)
async def process_custom_time(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание встречи отменено")
        return

    try:
        # Парсим дату и время
        datetime_str = message.text.strip()
        meeting_time = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")

        if meeting_time <= datetime.now():
            await message.answer("❌ Время должно быть в будущем. Попробуйте еще раз:")
            return

        await state.update_data(meeting_time=meeting_time)
        await ask_interest(message, state)

    except ValueError:
        await message.answer(
            "❌ Неверный формат даты.\n"
            "Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2024 19:30\n"
            "Попробуйте еще раз:"
        )


async def ask_interest(callback_or_message, state: FSMContext):
    """Спросить интерес/тему встречи"""
    data = await state.get_data()
    meeting_time = data['meeting_time']

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="☕ Кофе/Общение", callback_data="interest_coffee"),
            InlineKeyboardButton(text="🎮 Настольные игры", callback_data="interest_games")
        ],
        [
            InlineKeyboardButton(text="🎬 Кино/Обсуждение", callback_data="interest_movies"),
            InlineKeyboardButton(text="🏃 Спорт/Активность", callback_data="interest_sport")
        ],
        [
            InlineKeyboardButton(text="💼 Бизнес/Нетворкинг", callback_data="interest_business"),
            InlineKeyboardButton(text="🎨 Творчество/Хобби", callback_data="interest_hobby")
        ],
        [
            InlineKeyboardButton(text="📝 Своя тема", callback_data="interest_custom"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")
        ]
    ])

    text = (
        f"⏰ **Время:** {meeting_time.strftime('%d.%m.%Y %H:%M')}\n\n"
        "🎯 **Выберите тему встречи:**"
    )

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await callback_or_message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    await state.set_state(PlaceMeetingStates.choosing_interest)


@router.callback_query(PlaceMeetingStates.choosing_interest, F.data.startswith("interest_"))
async def process_interest_choice(callback: CallbackQuery, state: FSMContext):
    interest_map = {
        "interest_coffee": "☕ Кофе/Общение",
        "interest_games": "🎮 Настольные игры",
        "interest_movies": "🎬 Кино/Обсуждение",
        "interest_sport": "🏃 Спорт/Активность",
        "interest_business": "💼 Бизнес/Нетворкинг",
        "interest_hobby": "🎨 Творчество/Хобби"
    }

    if callback.data in interest_map:
        interest = interest_map[callback.data]
        await state.update_data(interest=interest)
        await ask_description(callback, state)
    elif callback.data == "interest_custom":
        await callback.message.edit_text(
            "✏️ **Введите свою тему встречи:**\n\n"
            "Например: 'Обсуждение стартапов', 'Игра в покер', 'Просмотр футбола'",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")]
            ])
        )
        # Остаемся в том же состоянии для обработки пользовательского ввода


# Обработка ввода пользовательской темы
@router.message(PlaceMeetingStates.choosing_interest)
async def process_custom_interest(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание встречи отменено")
        return

    if len(message.text) < 3:
        await message.answer("❌ Тема слишком короткая. Минимум 3 символа. Попробуйте еще раз:")
        return

    await state.update_data(interest=message.text)
    await ask_description(message, state)


async def ask_description(callback_or_message, state: FSMContext):
    """Спросить описание встречи"""
    text = (
        "📝 **Напишите описание встречи:**\n\n"
        "Что вы хотите обсудить/сделать?\n"
        "Что ищете в собеседнике?\n"
        "Любая дополнительная информация.\n\n"
        "Например: 'Ищу компанию для игры в мафию, правила объясню на месте'"
    )

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")]
            ])
        )
    else:
        await callback_or_message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_meeting")]
            ])
        )

    await state.set_state(PlaceMeetingStates.entering_description)


@router.message(PlaceMeetingStates.entering_description)
async def process_description(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Создание встречи отменено")
        return

    if len(message.text) < 10:
        await message.answer("❌ Описание слишком короткое. Минимум 10 символов. Попробуйте еще раз:")
        return

    await state.update_data(description=message.text)
    await show_confirmation(message, state)


async def show_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение встречи"""
    data = await state.get_data()

    async with db.pool.acquire() as conn:
        place = await conn.fetchrow(
            "SELECT * FROM places WHERE id = $1",
            data['place_id']
        )

    text = (
        "✅ **Подтвердите детали встречи:**\n\n"
        f"📍 **Заведение:** {place['name']}\n"
        f"📌 Адрес: {place['address']}\n"
        f"⏰ **Время:** {data['meeting_time'].strftime('%d.%m.%Y %H:%M')}\n"
        f"🎯 **Тема:** {data['interest']}\n"
        f"📝 **Описание:** {data['description']}\n\n"
        "Всё верно?"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_confirmation_keyboard()
    )
    await state.set_state(PlaceMeetingStates.confirmation)


@router.callback_query(PlaceMeetingStates.confirmation)
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Создание встречи отменено")
        return

    if callback.data != "confirm":
        return

    data = await state.get_data()

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        # Создаем встречу
        meeting = await conn.fetchrow('''
            INSERT INTO place_meetings 
            (place_id, user_id, meeting_time, description, interest, max_participants, current_participants, status)
            VALUES ($1, $2, $3, $4, $5, $6, 1, 'active')
            RETURNING id
        ''', data['place_id'], user['id'], data['meeting_time'],
                                      data['description'], data['interest'], 2)

        # Добавляем создателя как участника
        await conn.execute('''
            INSERT INTO meeting_participants (meeting_id, user_id, status)
            VALUES ($1, $2, 'accepted')
        ''', meeting['id'], user['id'])

        place = await conn.fetchrow(
            "SELECT name, address FROM places WHERE id = $1",
            data['place_id']
        )

    # Отправляем сообщение в чат
    meeting_message = (
        "🗺️ **Новая встреча создана!**\n\n"
        f"📍 **Место:** {place['name']}\n"
        f"📌 Адрес: {place['address']}\n"
        f"⏰ **Время:** {data['meeting_time'].strftime('%d.%m.%Y %H:%M')}\n"
        f"🎯 **Тема:** {data['interest']}\n"
        f"📝 **Описание:** {data['description']}\n"
        f"👤 **Организатор:** @{callback.from_user.username or 'пользователь'}\n\n"
        "Хотите присоединиться?"
    )

    # Сохраняем ID сообщения в базе
    sent_message = await callback.message.answer(
        meeting_message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Присоединиться", callback_data=f"join_meeting_{meeting['id']}")],
            [InlineKeyboardButton(text="📍 Посмотреть на карте", callback_data=f"view_on_map_{meeting['id']}")]
        ])
    )

    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE place_meetings SET telegram_message_id = $1 WHERE id = $2",
            sent_message.message_id, meeting['id']
        )

    await callback.message.edit_text("✅ Встреча создана и опубликована!")
    await state.clear()


# Присоединиться к встрече
@router.callback_query(F.data.startswith("join_meeting_"))
async def join_meeting(callback: CallbackQuery):
    meeting_id = int(callback.data.split("_")[2])

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback.from_user.id
        )

        # Проверяем, можно ли присоединиться
        meeting = await conn.fetchrow('''
            SELECT pm.*, p.name as place_name, p.address,
                   u.username as organizer_username,
                   (SELECT COUNT(*) FROM meeting_participants WHERE meeting_id = pm.id AND status = 'accepted') as participants_count
            FROM place_meetings pm
            JOIN places p ON p.id = pm.place_id
            JOIN users u ON u.id = pm.user_id
            WHERE pm.id = $1 AND pm.status = 'active'
        ''', meeting_id)

        if not meeting:
            await callback.answer("❌ Встреча не найдена или завершена")
            return

        if meeting['current_participants'] >= meeting['max_participants']:
            await callback.answer("❌ Мест больше нет")
            return

        # Проверяем, не участник ли уже
        existing = await conn.fetchrow(
            "SELECT * FROM meeting_participants WHERE meeting_id = $1 AND user_id = $2",
            meeting_id, user['id']
        )

        if existing:
            await callback.answer("✅ Вы уже участник")
            return

        # Добавляем как участника
        await conn.execute('''
            INSERT INTO meeting_participants (meeting_id, user_id, status)
            VALUES ($1, $2, 'pending')
        ''', meeting_id, user['id'])

        # Отправляем запрос организатору
        organizer = await conn.fetchrow(
            "SELECT telegram_id FROM users WHERE id = $1",
            meeting['user_id']
        )

        if organizer:
            try:
                await callback.bot.send_message(
                    chat_id=organizer['telegram_id'],
                    text=f"👤 @{callback.from_user.username or 'пользователь'} хочет присоединиться к вашей встрече!\n\n"
                         f"📍 {meeting['place_name']}\n"
                         f"⏰ {meeting['meeting_time'].strftime('%d.%m.%Y %H:%M')}\n\n"
                         "Подтвердите запрос в '🗺️ Мои встречи на карте'"
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление: {e}")

    await callback.answer("✅ Запрос на участие отправлен организатору")


# Мои встречи на карте
@router.message(F.text == "🗺️ Мои встречи на карте")
async def my_map_meetings(message: Message):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        # Встречи, которые пользователь создал
        organized = await conn.fetch('''
            SELECT pm.*, p.name as place_name, p.address,
                   (SELECT COUNT(*) FROM meeting_participants WHERE meeting_id = pm.id AND status = 'accepted') as participants_count
            FROM place_meetings pm
            JOIN places p ON p.id = pm.place_id
            WHERE pm.user_id = $1 AND pm.status = 'active'
            ORDER BY pm.meeting_time
        ''', user['id'])

        # Встречи, в которых пользователь участвует
        participating = await conn.fetch('''
            SELECT pm.*, p.name as place_name, p.address,
                   mp.status as participation_status
            FROM meeting_participants mp
            JOIN place_meetings pm ON pm.id = mp.meeting_id
            JOIN places p ON p.id = pm.place_id
            WHERE mp.user_id = $1 AND pm.status = 'active'
            ORDER BY pm.meeting_time
        ''', user['id'])

    text = "🗺️ **Мои встречи на карте:**\n\n"

    if organized:
        text += "🎯 **Созданные мной:**\n"
        for meeting in organized:
            text += f"📍 {meeting['place_name']}\n"
            text += f"   ⏰ {meeting['meeting_time'].strftime('%d.%m.%Y %H:%M')}\n"
            text += f"   👥 Участников: {meeting['participants_count']}/{meeting['max_participants']}\n"
            text += f"   🎯 Тема: {meeting['interest']}\n"
            if meeting['description']:
                text += f"   📝 {meeting['description'][:50]}...\n"
            text += "\n"

    if participating:
        text += "👥 **Я участвую:**\n"
        for meeting in participating:
            status_emoji = "✅" if meeting['participation_status'] == 'accepted' else "⏳"
            text += f"{status_emoji} {meeting['place_name']}\n"
            text += f"   ⏰ {meeting['meeting_time'].strftime('%d.%m.%Y %H:%M')}\n"
            text += f"   🎯 Тема: {meeting['interest']}\n\n"

    if not organized and not participating:
        text += "📭 У вас пока нет встреч на карте.\nСоздайте первую встречу!"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_map_menu_keyboard())


# Просмотр деталей заведения
@router.callback_query(F.data.startswith("view_place_"))
async def view_place_details(callback: CallbackQuery):
    place_id = int(callback.data.split("_")[2])

    async with db.pool.acquire() as conn:
        place = await conn.fetchrow(
            "SELECT * FROM places WHERE id = $1",
            place_id
        )

        # Получаем предстоящие встречи в этом заведении
        meetings = await conn.fetch('''
            SELECT pm.*, u.username as organizer_username
            FROM place_meetings pm
            JOIN users u ON u.id = pm.user_id
            WHERE pm.place_id = $1 
            AND pm.status = 'active'
            AND pm.meeting_time > NOW()
            ORDER BY pm.meeting_time
            LIMIT 5
        ''', place_id)

    text = (
        f"🏢 **{place['name']}**\n\n"
        f"🏷️ Категория: {place['category']}\n"
        f"📍 Адрес: {place['address']}\n"
        f"⭐ Рейтинг: {place['rating'] or 'Нет'}\n"
    )

    if place['opening_hours']:
        text += f"🕒 Часы работы: {place['opening_hours']}\n"

    if place['description']:
        text += f"\n📝 Описание: {place['description']}\n"

    if meetings:
        text += "\n📅 **Предстоящие встречи:**\n"
        for meeting in meetings:
            text += f"• {meeting['meeting_time'].strftime('%H:%M')} - {meeting['interest']}"
            text += f" (от @{meeting['organizer_username']})\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Создать встречу здесь", callback_data=f"create_here_{place_id}"),
            InlineKeyboardButton(text="👥 Присоединиться", callback_data=f"join_place_{place_id}")
        ],
        [InlineKeyboardButton(text="📍 Посмотреть на карте", callback_data=f"show_on_map_{place_id}")]
    ])

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


# Отмена встречи
@router.callback_query(F.data == "cancel_meeting")
async def cancel_meeting_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Создание встречи отменено")


# Обработка кнопки "Посмотреть на карте"
@router.callback_query(F.data.startswith("view_on_map_"))
async def view_meeting_on_map(callback: CallbackQuery):
    """Показать ссылку на карту с конкретной встречей"""
    try:
        # Исправляем получение meeting_id
        meeting_id_str = callback.data.replace("view_on_map_", "")
        if not meeting_id_str.isdigit():
            await callback.answer("❌ Ошибка: неверный ID встречи")
            return

        meeting_id = int(meeting_id_str)

        await callback.answer("📍 Открываем карту...")

        await callback.message.answer(
            "📍 Чтобы увидеть встречу на карте, перейдите по ссылке:\n"
            f"http://localhost:5000/map?user_id={callback.from_user.id}&meeting_id={meeting_id}\n\n"
            "Если карта не открывается, убедитесь что Flask сервер запущен: python run_web.py"
        )
    except Exception as e:
        logging.error(f"Ошибка в view_meeting_on_map: {e}")
        await callback.answer("❌ Ошибка при открытии карты")


# Обработка кнопки "Присоединиться к заведению"
@router.callback_query(F.data.startswith("join_place_"))
async def join_place_meeting(callback: CallbackQuery):
    place_id = int(callback.data.split("_")[2])

    await callback.answer("📍 Выберите встречу для присоединения")

    # Показываем встречи в этом заведении
    async with db.pool.acquire() as conn:
        meetings = await conn.fetch('''
            SELECT pm.id, pm.meeting_time, pm.interest, pm.description,
                   u.username as organizer_username,
                   pm.current_participants, pm.max_participants
            FROM place_meetings pm
            JOIN users u ON u.id = pm.user_id
            WHERE pm.place_id = $1 
            AND pm.status = 'active'
            AND pm.meeting_time > NOW()
            ORDER BY pm.meeting_time
            LIMIT 5
        ''', place_id)

    if not meetings:
        await callback.message.answer("📭 В этом заведении пока нет активных встреч.")
        return

    text = "👥 **Активные встречи в заведении:**\n\n"
    keyboard = []

    for meeting in meetings:
        text += f"⏰ {meeting['meeting_time'].strftime('%d.%m %H:%M')}\n"
        text += f"🎯 {meeting['interest']}\n"
        text += f"👤 Организатор: @{meeting['organizer_username']}\n"
        text += f"👥 {meeting['current_participants']}/{meeting['max_participants']} мест\n\n"

        keyboard.append([
            InlineKeyboardButton(
                text=f"Присоединиться к встрече {meeting['meeting_time'].strftime('%H:%M')}",
                callback_data=f"join_meeting_{meeting['id']}"
            )
        ])

    await callback.message.answer(text, parse_mode="Markdown",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


# В handlers/map.py добавляем вспомогательную функцию

def extract_id_from_callback(callback_data: str, prefix: str) -> int:
    """Извлечь ID из callback_data"""
    try:
        return int(callback_data.replace(prefix, ""))
    except (ValueError, AttributeError):
        raise ValueError(f"Неверный формат callback_data: {callback_data}")


# В handlers/map.py добавляем обработчики для кнопок навигации

@router.message(F.text == "🗺️ Назад в меню карты")
async def back_to_map_menu(message: Message):
    """Вернуться в меню карты"""
    await map_menu(message)


@router.message(F.text == "📍 Открыть карту")
async def open_map_link(message: Message):
    """Показать ссылку на карту"""
    await message.answer(
        "🌐 Карта встреч доступна по ссылке:\n"
        f"http://localhost:5000/map?user_id={message.from_user.id}\n\n"
        "Если карта не открывается, убедитесь что Flask сервер запущен командой:\n"
        "python run_web_sync.py"
    )


@router.message(F.text == "📍 Посмотреть на карте")
async def view_on_map_button(message: Message):
    """Обработка кнопки '📍 Посмотреть на карте' из reply-клавиатуры"""
    await message.answer(
        "🌐 Чтобы открыть карту, перейдите по ссылке:\n"
        f"http://localhost:5000/map?user_id={message.from_user.id}\n\n"
        "Или используйте команду '🗺️ Карта встреч' в главном меню"
    )

# В handlers/map.py добавляем кнопку WebApp

from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

@router.message(F.text == "🗺️ Карта встреч")
async def map_menu(message: Message):
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

    # Создаем кнопку WebApp
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🌐 Открыть интерактивную карту",
                web_app=WebAppInfo(url="https://benito-unrouted-preachingly.ngrok-free.dev/webapp")
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Список заведений",
                callback_data="list_places_web"
            ),
            InlineKeyboardButton(
                text="📅 Мои встречи",
                callback_data="my_map_meetings"
            )
        ]
    ])

    await message.answer(
        "🗺️ **Интерактивная карта встреч**\n\n"
        "Нажмите кнопку ниже, чтобы открыть интерактивную карту прямо в Telegram!\n\n"
        "В карте вы сможете:\n"
        "📍 Просматривать встречи на карте\n"
        "👤 Смотреть анкеты пользователей\n"
        "❤️ Лайкать/пропускать прямо в приложении\n"
        "📅 Присоединяться к встречам\n\n"
        "Для начала нажмите '🌐 Открыть интерактивную карту':",
        parse_mode="Markdown",
        reply_markup=keyboard
    )