from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import asyncio
import logging
from typing import Optional

from database import db
from keyboards import get_search_keyboard, get_main_menu_keyboard, get_profile_keyboard, get_search_filters_keyboard, \
    get_save_filter_keyboard, get_cancel_keyboard
from utils import decrypt_data
from states import SearchStates

router = Router()


class FilterStates(StatesGroup):
    choosing_interest = State()
    entering_location = State()
    choosing_time = State()


async def safe_edit_message(message, **kwargs):
    """Безопасное редактирование сообщения с обработкой ошибок"""
    try:
        if 'caption' in kwargs:
            # Пытаемся редактировать caption
            if hasattr(message, 'edit_caption') and message.caption:
                return await message.edit_caption(**kwargs)
            else:
                # Если нет caption, редактируем текст
                if 'reply_markup' in kwargs:
                    return await message.edit_text(
                        text=kwargs.get('caption', ''),
                        reply_markup=kwargs.get('reply_markup')
                    )
        else:
            return await message.edit_text(**kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass  # Игнорируем, если сообщение не изменилось
        elif "there is no caption in the message to edit" in str(e):
            # Отправляем новое сообщение
            if 'caption' in kwargs:
                return await message.answer(
                    text=kwargs.get('caption', ''),
                    reply_markup=kwargs.get('reply_markup')
                )
        elif "message to edit not found" in str(e):
            pass  # Сообщение уже удалено или недоступно
        elif "there is no text in the message to edit" in str(e):
            # Сообщение не имеет текста (например, только фото с подписью)
            if 'caption' in kwargs:
                return await message.answer(
                    text=kwargs.get('caption', ''),
                    reply_markup=kwargs.get('reply_markup')
                )
            elif 'text' in kwargs:
                return await message.answer(
                    text=kwargs.get('text', ''),
                    reply_markup=kwargs.get('reply_markup')
                )
        else:
            logging.error(f"Telegram error: {e}")
    except Exception as e:
        logging.error(f"Error editing message: {e}")


def get_telegram_link(telegram_username: str, user_id: int) -> str:
    """Получить ссылку на Telegram пользователя"""
    if telegram_username and telegram_username != 'None' and telegram_username != 'null' and telegram_username != '':
        return f"https://t.me/{telegram_username}"
    else:
        return f"tg://user?id={user_id}"


def normalize_filters(filters: dict) -> dict:
    """Нормализует фильтры для поиска"""
    if not filters:
        return {}

    normalized = filters.copy()

    # Обработка интереса
    if normalized.get('interest'):
        if normalized['interest'] in ['👋 Любой интерес', 'Любой интерес']:
            normalized['interest'] = None

    # Обработка времени
    if normalized.get('time_period'):
        if normalized['time_period'] in ['⏰ Любое время', 'Любое время']:
            normalized['time_period'] = None

    return normalized


# Начать поиск
@router.message(F.text == "🔍 Начать поиск")
async def start_search(message: Message, state: FSMContext):
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

    # Проверяем, опубликована ли анкета пользователя
    if not user['is_published']:
        await message.answer(
            "❌ Чтобы искать других пользователей, вам нужно опубликовать свою анкету.\n"
            "Перейдите в профиль и нажмите '📢 Опубликовать анкету'.",
            reply_markup=get_profile_keyboard(False)
        )
        return

    # Проверяем, есть ли сохраненный фильтр
    async with db.pool.acquire() as conn:
        filter_data = await conn.fetchrow(
            "SELECT * FROM search_filters WHERE user_id = $1",
            user['id']
        )

    if filter_data:
        # Используем сохраненный фильтр
        await message.answer(
            f"🔍 Используем сохраненный фильтр:\n"
            f"• Интерес: {filter_data['interest'] or 'Любой'}\n"
            f"• Место: {filter_data['location'] or 'Любое'}\n"
            f"• Время: {filter_data['time_period'] or 'Любое'}\n\n"
            f"Начинаем поиск...",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        await state.update_data(current_filters={
            'interest': filter_data['interest'],
            'location': filter_data['location'],
            'time_period': filter_data['time_period']
        })
        await show_next_profile(message, state, user_id=message.from_user.id)
    else:
        # Показываем первую анкету без фильтров
        await message.answer(
            "🔍 Начинаем поиск анкет...",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        await show_next_profile(message, state, user_id=message.from_user.id)


# Настройка фильтров
@router.message(F.text == "⚙️ Фильтры поиска")
async def setup_filters(message: Message, state: FSMContext):
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

    # Получаем сохраненные фильтры
    async with db.pool.acquire() as conn:
        filter_data = await conn.fetchrow(
            "SELECT * FROM search_filters WHERE user_id = $1",
            user['id']
        )

    if filter_data:
        filter_text = (
            f"🎯 Текущие фильтры:\n\n"
            f"• Интерес: {filter_data['interest'] or 'Любой'}\n"
            f"• Место: {filter_data['location'] or 'Любое'}\n"
            f"• Время: {filter_data['time_period'] or 'Любое'}\n\n"
            f"Выберите действие:"
        )
    else:
        filter_text = "🎯 Настройте фильтры поиска:\n\nФильтры еще не настроены."

    await message.answer(
        filter_text,
        reply_markup=get_search_filters_keyboard()
    )


# Выбор фильтра по интересу
@router.message(F.text == "🎯 По интересу")
async def filter_by_interest(message: Message, state: FSMContext):
    interests = ["🏃 Спорт", "🎬 Кино", "☕ Кафе/Бар", "🎮 Настольные игры", "👋 Любой интерес"]

    keyboard = []
    for interest in interests:
        keyboard.append([KeyboardButton(text=interest)])
    keyboard.append([KeyboardButton(text="❌ Отмена")])

    await message.answer(
        "🎯 Выберите интерес для поиска:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )

    await state.set_state(FilterStates.choosing_interest)
    await state.update_data(filter_type="interest")


# Выбор фильтра по месту
@router.message(F.text == "📍 По месту")
async def filter_by_location(message: Message, state: FSMContext):
    await message.answer(
        "📍 Введите ключевое слово для поиска по месту:\n"
        "(Например: 'парк', 'кафе', 'центр города', 'стадион')\n"
        "Или оставьте пустым для поиска по всем местам.",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(FilterStates.entering_location)
    await state.update_data(filter_type="location")


# Выбор фильтра по времени
@router.message(F.text == "⏰ По времени")
async def filter_by_time(message: Message, state: FSMContext):
    times = [
        "👋 Сегодня", "📅 Завтра", "🗓️ В ближайшие дни",
        "🌆 Вечером", "🌅 Утром", "🌞 В выходные", "⏰ Любое время"
    ]

    keyboard = []
    for time in times:
        keyboard.append([KeyboardButton(text=time)])
    keyboard.append([KeyboardButton(text="❌ Отмена")])

    await message.answer(
        "⏰ Выберите период времени:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )

    await state.set_state(FilterStates.choosing_time)
    await state.update_data(filter_type="time")


# Сброс фильтров
@router.message(F.text == "🧹 Сбросить фильтры")
async def reset_filters(message: Message, state: FSMContext):
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if user:
            await conn.execute(
                "DELETE FROM search_filters WHERE user_id = $1",
                user['id']
            )

    # Также очищаем фильтры в состоянии
    await state.update_data(current_filters={})

    await message.answer(
        "✅ Фильтры поиска сброшены!",
        reply_markup=get_main_menu_keyboard(is_authenticated=True)
    )


# Поиск с текущими фильтрами
@router.message(F.text == "🔍 Поиск с фильтрами")
async def search_with_filters(message: Message, state: FSMContext):
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

    # Получаем сохраненные фильтры
    async with db.pool.acquire() as conn:
        filter_data = await conn.fetchrow(
            "SELECT * FROM search_filters WHERE user_id = $1",
            user['id']
        )

    if filter_data:
        filters = {
            'interest': filter_data['interest'],
            'location': filter_data['location'],
            'time_period': filter_data['time_period']
        }
    else:
        filters = {'interest': None, 'location': None, 'time_period': None}

    await state.update_data(current_filters=filters)
    await message.answer("🔍 Начинаем поиск с фильтрами...")
    await show_next_profile(message, state, user_id=message.from_user.id)


# Обработка выбора интереса для фильтра
@router.message(FilterStates.choosing_interest)
async def process_filter_interest(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Настройка фильтра отменена",
            reply_markup=get_search_filters_keyboard()
        )
        return

    valid_interests = ["🏃 Спорт", "🎬 Кино", "☕ Кафе/Бар", "🎮 Настольные игры", "👋 Любой интерес"]

    if message.text not in valid_interests:
        await message.answer(
            "❌ Пожалуйста, выберите интерес из предложенных:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=i)] for i in valid_interests] + [[KeyboardButton(text="❌ Отмена")]],
                resize_keyboard=True
            )
        )
        return

    # Сохраняем фильтр
    interest = None if message.text == "👋 Любой интерес" else message.text

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if user:
            # Проверяем, существует ли уже фильтр
            existing = await conn.fetchrow(
                "SELECT * FROM search_filters WHERE user_id = $1",
                user['id']
            )

            if existing:
                await conn.execute(
                    "UPDATE search_filters SET interest = $1 WHERE user_id = $2",
                    interest, user['id']
                )
            else:
                await conn.execute(
                    "INSERT INTO search_filters (user_id, interest) VALUES ($1, $2)",
                    user['id'], interest
                )

    # Обновляем фильтры в состоянии
    state_data = await state.get_data()
    current_filters = state_data.get('current_filters', {})
    current_filters['interest'] = interest
    await state.update_data(current_filters=current_filters)

    await state.clear()
    await message.answer(
        f"✅ Фильтр по интересу сохранен: {message.text if interest else 'Любой интерес'}",
        reply_markup=get_search_filters_keyboard()
    )


# Обработка ввода места для фильтра
@router.message(FilterStates.entering_location)
async def process_filter_location(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Настройка фильтра отменена",
            reply_markup=get_search_filters_keyboard()
        )
        return

    location = message.text if message.text.strip() else None

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if user:
            existing = await conn.fetchrow(
                "SELECT * FROM search_filters WHERE user_id = $1",
                user['id']
            )

            if existing:
                await conn.execute(
                    "UPDATE search_filters SET location = $1 WHERE user_id = $2",
                    location, user['id']
                )
            else:
                await conn.execute(
                    "INSERT INTO search_filters (user_id, location) VALUES ($1, $2)",
                    user['id'], location
                )

    # Обновляем фильтры в состоянии
    state_data = await state.get_data()
    current_filters = state_data.get('current_filters', {})
    current_filters['location'] = location
    await state.update_data(current_filters=current_filters)

    await state.clear()
    await message.answer(
        f"✅ Фильтр по месту сохранен: {location if location else 'Любое место'}",
        reply_markup=get_search_filters_keyboard()
    )


# Обработка выбора времени для фильтра
@router.message(FilterStates.choosing_time)
async def process_filter_time(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Настройка фильтра отменена",
            reply_markup=get_search_filters_keyboard()
        )
        return

    valid_times = ["👋 Сегодня", "📅 Завтра", "🗓️ В ближайшие дни", "🌆 Вечером",
                   "🌅 Утром", "🌞 В выходные", "⏰ Любое время"]

    if message.text not in valid_times:
        await message.answer(
            "❌ Пожалуйста, выберите время из предложенных:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=t)] for t in valid_times] + [[KeyboardButton(text="❌ Отмена")]],
                resize_keyboard=True
            )
        )
        return

    time_period = None if message.text == "⏰ Любое время" else message.text

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if user:
            existing = await conn.fetchrow(
                "SELECT * FROM search_filters WHERE user_id = $1",
                user['id']
            )

            if existing:
                await conn.execute(
                    "UPDATE search_filters SET time_period = $1 WHERE user_id = $2",
                    time_period, user['id']
                )
            else:
                await conn.execute(
                    "INSERT INTO search_filters (user_id, time_period) VALUES ($1, $2)",
                    user['id'], time_period
                )

    # Обновляем фильтры в состоянии
    state_data = await state.get_data()
    current_filters = state_data.get('current_filters', {})
    current_filters['time_period'] = time_period
    await state.update_data(current_filters=current_filters)

    await state.clear()
    await message.answer(
        f"✅ Фильтр по времени сохранен: {message.text if time_period else 'Любое время'}",
        reply_markup=get_search_filters_keyboard()
    )


# Показать следующую анкету с учетом фильтров
async def show_next_profile(message: Message, state: FSMContext, edit: bool = False, user_id: Optional[int] = None):
    """Показывает следующую анкету с учетом фильтров"""
    try:
        # Если user_id не передан, берем из сообщения
        if user_id is None:
            user_id = message.from_user.id

        # Получаем ID текущего пользователя
        async with db.pool.acquire() as conn:
            current_user = await conn.fetchrow(
                "SELECT id, username, first_name, is_published, is_authenticated FROM users WHERE telegram_id = $1",
                user_id
            )

            if not current_user:
                await message.answer(
                    "❌ Вы не найдены в базе данных. Пройдите регистрацию или войдите в аккаунт.",
                    reply_markup=get_main_menu_keyboard(is_authenticated=False)
                )
                await state.clear()
                return

            current_user_id = current_user['id']
            logging.info(
                f"Текущий пользователь: ID={current_user_id}, username={current_user['username']}, is_published={current_user['is_published']}")

            # Проверяем, опубликована ли анкета пользователя
            if not current_user['is_published']:
                await message.answer(
                    "❌ Ваша анкета не опубликована! Чтобы искать других, опубликуйте свою анкету в профиле.",
                    reply_markup=get_profile_keyboard(False)
                )
                await state.clear()
                return

            if not current_user['is_authenticated']:
                await message.answer(
                    "❌ Вы не авторизованы!",
                    reply_markup=get_main_menu_keyboard(is_authenticated=False)
                )
                await state.clear()
                return

        # Получаем текущие фильтры и нормализуем их
        state_data = await state.get_data()
        filters = normalize_filters(state_data.get('current_filters', {}))
        logging.info(f"Фильтры поиска после нормализации: {filters}")

        # Получаем список уже просмотренных пользователей
        async with db.pool.acquire() as conn:
            viewed_users = await conn.fetch(
                "SELECT viewed_user_id FROM profile_views WHERE viewer_id = $1",
                current_user_id
            )
            viewed_ids = [view['viewed_user_id'] for view in viewed_users]
            viewed_ids.append(current_user_id)  # Исключаем себя

            # Также исключаем пользователей, которых уже лайкнули
            liked_users = await conn.fetch(
                "SELECT to_user_id FROM likes WHERE from_user_id = $1",
                current_user_id
            )
            liked_ids = [like['to_user_id'] for like in liked_users]

            # Объединяем просмотренных и лайкнутых
            excluded_ids = list(set(viewed_ids + liked_ids))

            logging.info(f"Исключаемые ID: {excluded_ids}")
            logging.info(f"Всего исключено: {len(excluded_ids)} пользователей")

            # Сначала проверим, есть ли вообще опубликованные пользователи с активностью
            total_published = await conn.fetchval('''
                SELECT COUNT(*) FROM users 
                WHERE is_published = TRUE 
                AND is_authenticated = TRUE
                AND is_active = TRUE
                AND id != $1
                AND activity_interest IS NOT NULL
            ''', current_user_id)

            if total_published == 0:
                await message.answer(
                    "😔 Пока нет других опубликованных анкет с заполненной активностью. Попробуйте позже.",
                    reply_markup=get_main_menu_keyboard(is_authenticated=True)
                )
                await state.clear()
                return

            logging.info(f"Всего опубликованных пользователей с активностью: {total_published}")

            # Формируем базовый запрос
            query = '''
                SELECT id, username, first_name, age, interests, about, 
                       activity_interest, activity_location, activity_time, 
                       activity_description, photo_id, telegram_id, telegram_real_username
                FROM users 
                WHERE is_published = TRUE 
                AND is_authenticated = TRUE
                AND is_active = TRUE
                AND id != $1
                AND activity_interest IS NOT NULL
            '''
            params = [current_user_id]
            param_counter = 2

            # Исключаем уже просмотренных и лайкнутых
            if excluded_ids:
                query += f" AND id != ALL(${param_counter}::bigint[])"
                params.append(excluded_ids)
                param_counter += 1

            # Добавляем фильтры по активностям
            if filters.get('interest'):
                # Используем точное сравнение для интереса
                query += f" AND activity_interest = ${param_counter}"
                params.append(filters['interest'])
                param_counter += 1
                logging.info(f"Применяем фильтр по интересу: {filters['interest']}")

            if filters.get('location'):
                # Используем ILIKE для частичного совпадения в месте
                query += f" AND activity_location ILIKE ${param_counter}"
                params.append(f'%{filters["location"]}%')
                param_counter += 1
                logging.info(f"Применяем фильтр по месту: {filters['location']}")

            if filters.get('time_period'):
                # Используем точное сравнение для времени
                query += f" AND activity_time = ${param_counter}"
                params.append(filters['time_period'])
                param_counter += 1
                logging.info(f"Применяем фильтр по времени: {filters['time_period']}")

            query += " ORDER BY RANDOM() LIMIT 1"

            logging.info(f"SQL запрос: {query}")
            logging.info(f"Параметры: {params}")

            profile = await conn.fetchrow(query, *params)

        if not profile:
            logging.info("❌ Не найдено подходящих анкет по фильтрам")

            # Проверяем, использовались ли фильтры
            if filters.get('interest') or filters.get('location') or filters.get('time_period'):
                logging.info("Искали с фильтрами, но ничего не нашли")
                # Пробуем найти без фильтров, но с исключениями
                async with db.pool.acquire() as conn:
                    query_no_filters = '''
                        SELECT id, username, first_name, age, interests, about, 
                               activity_interest, activity_location, activity_time, 
                               activity_description, photo_id, telegram_id, telegram_real_username
                        FROM users 
                        WHERE is_published = TRUE 
                        AND is_authenticated = TRUE
                        AND is_active = TRUE
                        AND id != $1
                        AND activity_interest IS NOT NULL
                    '''
                    params_no_filters = [current_user_id]

                    if excluded_ids:
                        query_no_filters += f" AND id != ALL($2::bigint[])"
                        params_no_filters.append(excluded_ids)

                    query_no_filters += " ORDER BY RANDOM() LIMIT 1"

                    profile = await conn.fetchrow(query_no_filters, *params_no_filters)

                    if profile:
                        logging.info("✅ Найден пользователь без учета фильтров")
                    else:
                        # Если все просмотрены, предлагаем сбросить просмотры
                        if total_published > 0 and len(excluded_ids) >= total_published:
                            # Создаем клавиатуру для выбора действия
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [
                                    InlineKeyboardButton(text="🔄 Смотреть заново",
                                                         callback_data="reset_views_and_likes"),
                                    InlineKeyboardButton(text="⏳ Ждать новые", callback_data="wait_new")
                                ]
                            ])

                            if edit:
                                await message.edit_text(
                                    "😔 Вы просмотрели все анкеты по текущим фильтрам!\n\n"
                                    "Вы можете:\n"
                                    "• 🔄 Начать просмотр заново (сбросить просмотренные и лайки)\n"
                                    "• ⏳ Подождать появления новых анкет",
                                    reply_markup=keyboard
                                )
                            else:
                                await message.answer(
                                    "😔 Вы просмотрели все анкеты по текущим фильтрам!\n\n"
                                    "Вы можете:\n"
                                    "• 🔄 Начать просмотр заново (сбросить просмотренные и лайки)\n"
                                    "• ⏳ Подождать появления новых анкет",
                                    reply_markup=keyboard
                                )
                        else:
                            if edit:
                                await message.edit_text(
                                    "😔 Не найдено анкет по текущим фильтрам. Попробуйте изменить фильтры.",
                                    reply_markup=get_main_menu_keyboard(is_authenticated=True)
                                )
                            else:
                                await message.answer(
                                    "😔 Не найдено анкет по текущим фильтрам. Попробуйте изменить фильтры.",
                                    reply_markup=get_main_menu_keyboard(is_authenticated=True)
                                )
                        await state.clear()
                        return
            else:
                # Если фильтров не было, проверяем все ли просмотрены
                if total_published > 0 and len(excluded_ids) >= total_published:
                    # Создаем клавиатуру для выбора действия
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="🔄 Смотреть заново", callback_data="reset_views_and_likes"),
                            InlineKeyboardButton(text="⏳ Ждать новые", callback_data="wait_new")
                        ]
                    ])

                    if edit:
                        await message.edit_text(
                            "😔 Вы просмотрели все анкеты!\n\n"
                            "Вы можете:\n"
                            "• 🔄 Начать просмотр заново (сбросить просмотренные и лайки)\n"
                            "• ⏳ Подождать появления новых анкет",
                            reply_markup=keyboard
                        )
                    else:
                        await message.answer(
                            "😔 Вы просмотрели все анкеты!\n\n"
                            "Вы можете:\n"
                            "• 🔄 Начать просмотр заново (сбросить просмотренные и лайки)\n"
                            "• ⏳ Подождать появления новых анкет",
                            reply_markup=keyboard
                        )
                else:
                    if edit:
                        await message.edit_text(
                            "😔 Пока нет других опубликованных анкет с заполненной активностью. Попробуйте позже.",
                            reply_markup=get_main_menu_keyboard(is_authenticated=True)
                        )
                    else:
                        await message.answer(
                            "😔 Пока нет других опубликованных анкет с заполненной активностью. Попробуйте позже.",
                            reply_markup=get_main_menu_keyboard(is_authenticated=True)
                        )
                await state.clear()
                return

        # Сохраняем текущий профиль в состоянии
        await state.update_data(current_profile_id=profile['id'])
        logging.info(
            f"Найден профиль: ID={profile['id']}, username={profile['username']}, activity_interest={profile['activity_interest']}")

        # Записываем просмотр
        async with db.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO profile_views (viewer_id, viewed_user_id, viewed_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (viewer_id, viewed_user_id) DO NOTHING
                ''', current_user_id, profile['id'])
                logging.info("✅ Просмотр записан в базу")
            except Exception as e:
                logging.error(f"❌ Ошибка при записи просмотра: {e}")

        # Дешифруем данные
        decrypted_first_name = decrypt_data(profile['first_name'])
        decrypted_interests = decrypt_data(profile['interests']) if profile['interests'] else "Не указано"
        decrypted_about = decrypt_data(profile['about']) if profile['about'] else "Не указано"
        decrypted_location = decrypt_data(profile['activity_location']) if profile[
            'activity_location'] else "Не указано"
        decrypted_description = decrypt_data(profile['activity_description']) if profile['activity_description'] else ""

        # Формируем информацию об анкете
        profile_info = (
            "👤 Найденная анкета:\n\n"
            f"👤 Имя: {decrypted_first_name}\n"
            f"🎂 Возраст: {profile['age']} лет\n"
            f"🎯 Интересы: {decrypted_interests}\n"
            f"📝 О себе: {decrypted_about}\n"
        )

        if profile['activity_interest']:
            profile_info += f"\n🎯 Предлагаемая активность:\n"
            profile_info += f"• Интерес: {profile['activity_interest']}\n"
            profile_info += f"• Место: {decrypted_location}\n"
            profile_info += f"• Время: {profile['activity_time']}\n"
            if decrypted_description:
                profile_info += f"• Описание: {decrypted_description}\n"

        profile_info += "\nЧто делаем?"

        logging.info(f"Формируем сообщение с фото: {profile['photo_id'] is not None}")

        try:
            if profile['photo_id']:
                if edit:
                    try:
                        # Пытаемся редактировать существующее сообщение с фото
                        await message.edit_media(
                            media=InputMediaPhoto(
                                media=profile['photo_id'],
                                caption=profile_info
                            ),
                            reply_markup=get_search_keyboard()
                        )
                        logging.info("✅ Сообщение с фото отредактировано")
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            logging.info("Сообщение не изменилось")
                        elif "there is no caption in the message to edit" in str(e):
                            # Отправляем новое сообщение с фото
                            await message.answer_photo(
                                photo=profile['photo_id'],
                                caption=profile_info,
                                reply_markup=get_search_keyboard()
                            )
                            logging.info("✅ Отправлено новое сообщение с фото")
                        elif "there is no text in the message to edit" in str(e):
                            # Отправляем новое сообщение с фото
                            await message.answer_photo(
                                photo=profile['photo_id'],
                                caption=profile_info,
                                reply_markup=get_search_keyboard()
                            )
                            logging.info("✅ Отправлено новое сообщение с фото")
                        else:
                            # Отправляем новое сообщение с фото
                            await message.answer_photo(
                                photo=profile['photo_id'],
                                caption=profile_info,
                                reply_markup=get_search_keyboard()
                            )
                else:
                    # Отправляем новое сообщение с фото
                    await message.answer_photo(
                        photo=profile['photo_id'],
                        caption=profile_info,
                        reply_markup=get_search_keyboard()
                    )
                    logging.info("✅ Отправлено новое сообщение с фото")
            else:
                # Если нет фото, отправляем текстовое сообщение
                if edit:
                    try:
                        await message.edit_text(
                            text=profile_info,
                            reply_markup=get_search_keyboard()
                        )
                        logging.info("✅ Текстовое сообщение отредактировано")
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            logging.info("Сообщение не изменилось")
                        elif "there is no text in the message to edit" in str(e):
                            # Отправляем новое сообщение
                            await message.answer(
                                profile_info,
                                reply_markup=get_search_keyboard()
                            )
                            logging.info("✅ Отправлено новое текстовое сообщение")
                        else:
                            # Отправляем новое сообщение
                            await message.answer(
                                profile_info,
                                reply_markup=get_search_keyboard()
                            )
                else:
                    await message.answer(
                        profile_info,
                        reply_markup=get_search_keyboard()
                    )
                    logging.info("✅ Отправлено новое текстовое сообщение")

        except Exception as e:
            logging.error(f"❌ Ошибка при отправке сообщения: {e}")
            # Пытаемся отправить хотя бы текстовое сообщение
            await message.answer(
                profile_info,
                reply_markup=get_search_keyboard()
            )

        await state.set_state(SearchStates.browsing)
        logging.info("✅ Состояние установлено в SearchStates.browsing")

    except Exception as e:
        logging.error(f"❌ Критическая ошибка в show_next_profile: {e}", exc_info=True)

        # Пытаемся отправить сообщение об ошибке
        try:
            await message.answer(
                "❌ Произошла ошибка при поиске анкет. Попробуйте позже.",
                reply_markup=get_main_menu_keyboard(is_authenticated=True)
            )
        except:
            pass

        await state.clear()


# Обработка лайка
@router.callback_query(SearchStates.browsing, F.data == "like")
async def like_profile(callback: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        profile_id = data.get('current_profile_id')

        if not profile_id:
            await callback.answer("❌ Ошибка: профиль не найден")
            return

        # Получаем ID текущего пользователя
        async with db.pool.acquire() as conn:
            # Получаем данные текущего пользователя
            current_user = await conn.fetchrow(
                "SELECT id, telegram_id, username, first_name, telegram_real_username FROM users WHERE telegram_id = $1",
                callback.from_user.id
            )

            if not current_user:
                await callback.answer("❌ Вы не найдены в базе данных")
                return

            user_id = current_user['id']

            # Получаем данные пользователя, которого лайкаем
            liked_user = await conn.fetchrow(
                "SELECT id, telegram_id, username, first_name, telegram_real_username FROM users WHERE id = $1 AND is_published = TRUE",
                profile_id
            )

            if not liked_user:
                await callback.answer("❌ Пользователь не найден или анкета не опубликована")
                # Показываем следующую анкету
                await asyncio.sleep(1)
                await show_next_profile(callback.message, state, edit=True, user_id=callback.from_user.id)
                return

            # Проверяем, нет ли уже лайка
            existing_like = await conn.fetchrow(
                "SELECT * FROM likes WHERE from_user_id = $1 AND to_user_id = $2",
                user_id, profile_id
            )

            if existing_like:
                await callback.answer("❤️ Вы уже лайкнули этого пользователя")
                # Показываем следующую анкету
                await asyncio.sleep(1)
                await show_next_profile(callback.message, state, edit=True, user_id=callback.from_user.id)
                return

            # Проверяем взаимный лайк (лайкнул ли нас уже этот пользователь)
            mutual_like = await conn.fetchrow(
                "SELECT * FROM likes WHERE from_user_id = $1 AND to_user_id = $2",
                profile_id, user_id
            )

            # Сохраняем лайк
            await conn.execute('''
                INSERT INTO likes (from_user_id, to_user_id, created_at)
                VALUES ($1, $2, NOW())
            ''', user_id, profile_id)

            # Получаем полные данные пользователя для уведомлений
            liked_user_full = await conn.fetchrow(
                "SELECT activity_interest, activity_location, activity_time, activity_description, username, telegram_id, telegram_real_username FROM users WHERE id = $1",
                profile_id
            )

            if mutual_like:
                # Взаимный лайк - создаем встречу
                await conn.execute('''
                    INSERT INTO matches (from_user_id, to_user_id, activity_id, status, from_confirmed, to_confirmed, created_at)
                    VALUES ($1, $2, $2, 'pending', TRUE, FALSE, NOW())
                    ON CONFLICT (from_user_id, to_user_id) DO NOTHING
                ''', user_id, profile_id)

                # Отправляем уведомление пользователю, которого лайкнули
                decrypted_current_name = decrypt_data(current_user['first_name'])

                if liked_user_full:
                    decrypted_location = decrypt_data(liked_user_full['activity_location']) if liked_user_full[
                        'activity_location'] else ""

                    try:
                        telegram_link = get_telegram_link(
                            current_user['telegram_real_username'],
                            current_user['telegram_id']
                        )

                        await callback.bot.send_message(
                            chat_id=liked_user['telegram_id'],
                            text=f"🎉 Взаимный лайк!\n\n"
                                 f"👤 {decrypted_current_name} тоже лайкнул(а) вашу анкету!\n\n"
                                 f"🎯 Хочет прийти на вашу активность: {liked_user_full['activity_interest']}\n"
                                 f"📍 Ваше место: {decrypted_location}\n"
                                 f"⏰ Ваше время: {liked_user_full['activity_time']}\n\n"
                                 f"📞 Связь: {telegram_link}\n\n"
                                 f"Перейдите в '🤝 Мои встречи' -> '📝 Запросы на встречу' чтобы подтвердить встречу!"
                        )
                    except Exception as e:
                        logging.error(f"Не удалось отправить уведомление: {e}")

                await callback.answer("🎉 Взаимный лайк! Встреча создана")

            else:
                # Обычный лайк - создаем запрос на встречу
                await conn.execute('''
                    INSERT INTO matches (from_user_id, to_user_id, activity_id, status, from_confirmed, to_confirmed, created_at)
                    VALUES ($1, $2, $2, 'pending', TRUE, FALSE, NOW())
                    ON CONFLICT (from_user_id, to_user_id) DO NOTHING
                ''', user_id, profile_id)

                # Отправляем уведомление пользователю, которого лайкнули
                decrypted_current_name = decrypt_data(current_user['first_name'])

                if liked_user_full:
                    decrypted_location = decrypt_data(liked_user_full['activity_location']) if liked_user_full[
                        'activity_location'] else ""

                    try:
                        telegram_link = get_telegram_link(
                            current_user['telegram_real_username'],
                            current_user['telegram_id']
                        )

                        await callback.bot.send_message(
                            chat_id=liked_user['telegram_id'],
                            text=f"❤️ Новый запрос на встречу!\n\n"
                                 f"👤 {decrypted_current_name} хочет встретиться с вами!\n\n"
                                 f"🎯 Хочет прийти на вашу активность: {liked_user_full['activity_interest']}\n"
                                 f"📍 Ваше место: {decrypted_location}\n"
                                 f"⏰ Ваше время: {liked_user_full['activity_time']}\n\n"
                                 f"📞 Связь: {telegram_link}\n\n"
                                 f"Перейдите в '🤝 Мои встречи' -> '📝 Запросы на встречу' чтобы подтвердить встречу!"
                        )
                    except Exception as e:
                        logging.error(f"Не удалось отправить уведомление: {e}")

                await callback.answer("❤️ Запрос на встречу отправлен!")

        # Показываем следующую анкету через секунду
        await asyncio.sleep(1)
        await show_next_profile(callback.message, state, edit=True, user_id=callback.from_user.id)

    except Exception as e:
        logging.error(f"❌ Ошибка при обработке лайка: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка, попробуйте еще раз")


# Обработка пропуска
@router.callback_query(SearchStates.browsing, F.data == "skip")
async def skip_profile(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer("➡️ Пропущено")
        await show_next_profile(callback.message, state, edit=True, user_id=callback.from_user.id)
    except Exception as e:
        logging.error(f"❌ Ошибка при пропуске: {e}", exc_info=True)
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Настройка фильтров во время поиска
@router.callback_query(SearchStates.browsing, F.data == "filters")
async def set_filters_during_search(callback: CallbackQuery, state: FSMContext):
    try:
        await safe_edit_message(
            callback.message,
            caption="⚙️ Настройте фильтры поиска:",
            reply_markup=get_save_filter_keyboard()
        )
    except Exception as e:
        logging.error(f"❌ Ошибка при настройке фильтров: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Сохранение фильтра и продолжение поиска
@router.callback_query(F.data == "save_filter")
async def save_filter_and_search(callback: CallbackQuery, state: FSMContext):
    try:
        await safe_edit_message(
            callback.message,
            caption="🔍 Возвращаемся к поиску с текущими фильтрами...",
            reply_markup=None
        )
        await show_next_profile(callback.message, state, edit=True, user_id=callback.from_user.id)
    except Exception as e:
        logging.error(f"❌ Ошибка при сохранении фильтра: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Обработка отмены фильтра
@router.callback_query(F.data == "cancel_filter")
async def cancel_filter(callback: CallbackQuery, state: FSMContext):
    try:
        await safe_edit_message(
            callback.message,
            caption="❌ Настройка фильтров отменена.",
            reply_markup=None
        )
        await callback.answer("❌ Отменено")
    except Exception as e:
        logging.error(f"❌ Ошибка при отмене фильтра: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Обработка поиска с фильтром
@router.callback_query(F.data == "search_with_filter")
async def search_with_filter_callback(callback: CallbackQuery, state: FSMContext):
    try:
        await safe_edit_message(
            callback.message,
            caption="🔍 Начинаем поиск с текущими фильтрами...",
            reply_markup=None
        )
        await show_next_profile(callback.message, state, edit=True, user_id=callback.from_user.id)
    except Exception as e:
        logging.error(f"❌ Ошибка при поиске с фильтром: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Остановка поиска
@router.callback_query(SearchStates.browsing, F.data == "stop_search")
async def stop_search(callback: CallbackQuery, state: FSMContext):
    try:
        # Очищаем состояние
        await state.clear()

        # Пытаемся отредактировать сообщение
        if hasattr(callback.message, 'caption') and callback.message.caption:
            try:
                await callback.message.edit_caption(
                    caption="🔍 Поиск завершен.",
                    reply_markup=None
                )
            except TelegramBadRequest as e:
                if "there is no caption in the message to edit" in str(e):
                    await callback.message.edit_text(
                        text="🔍 Поиск завершен.",
                        reply_markup=None
                    )
        else:
            await callback.message.edit_text(
                text="🔍 Поиск завершен.",
                reply_markup=None
            )

    except Exception as e:
        # Если не удалось редактировать, просто показываем уведомление
        await callback.answer("🔍 Поиск завершен.", show_alert=True)

    try:
        # Отправляем новое сообщение с главным меню
        await callback.message.answer(
            "Вы вышли из режима поиска.",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
    except:
        pass

    await callback.answer()


# Обработка кнопки "Смотреть заново" (сброс просмотров и лайков)
@router.callback_query(F.data == "reset_views_and_likes")
async def reset_views_and_likes_callback(callback: CallbackQuery, state: FSMContext):
    try:
        # Получаем фильтры из состояния
        state_data = await state.get_data()
        filters = state_data.get('current_filters', {})

        # Сбрасываем просмотры и лайки для текущего пользователя
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE telegram_id = $1",
                callback.from_user.id
            )

            if user:
                # Удаляем просмотры
                await conn.execute(
                    "DELETE FROM profile_views WHERE viewer_id = $1",
                    user['id']
                )
                # Удаляем лайки, которые поставил пользователь
                await conn.execute(
                    "DELETE FROM likes WHERE from_user_id = $1",
                    user['id']
                )
                # Удаляем встречи, где пользователь является инициатором
                await conn.execute(
                    "DELETE FROM matches WHERE from_user_id = $1",
                    user['id']
                )

        # Сохраняем фильтры обратно в состояние
        await state.update_data(current_filters=filters)

        # Редактируем сообщение без reply_markup
        await callback.message.edit_text("🔄 Начинаем просмотр заново...")

        # Показываем первую анкету
        await show_next_profile(callback.message, state, user_id=callback.from_user.id)

    except Exception as e:
        logging.error(f"❌ Ошибка при сбросе просмотров и лайков: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Обработка кнопки "Ждать новые"
@router.callback_query(F.data == "wait_new")
async def wait_new_callback(callback: CallbackQuery, state: FSMContext):
    try:
        # Редактируем сообщение без reply_markup
        await callback.message.edit_text(
            "⏳ Вы можете вернуться позже, когда появятся новые анкеты.\n"
            "Также вы можете изменить фильтры поиска или попробовать сбросить просмотренные анкеты.",
            reply_markup=None
        )

        # Отправляем новое сообщение с главным меню
        await callback.message.answer(
            "🏠 Возвращаемся в главное меню.",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
    except Exception as e:
        # Если не удалось редактировать, просто отправляем новое сообщение
        await callback.message.answer(
            "⏳ Вы можете вернуться позже, когда появятся новые анкеты.\n\n"
            "🏠 Возвращаемся в главное меню.",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )

    await state.clear()
    await callback.answer()


# Статистика
@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
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

        # Получаем статистику
        likes_given = await conn.fetchval(
            "SELECT COUNT(*) FROM likes WHERE from_user_id = $1",
            user['id']
        )

        likes_received = await conn.fetchval(
            "SELECT COUNT(*) FROM likes WHERE to_user_id = $1",
            user['id']
        )

        mutual_likes = await conn.fetchval('''
            SELECT COUNT(*) FROM likes l1
            JOIN likes l2 ON l1.from_user_id = l2.to_user_id AND l1.to_user_id = l2.from_user_id
            WHERE l1.from_user_id = $1
        ''', user['id'])

        profile_views = await conn.fetchval(
            "SELECT COUNT(*) FROM profile_views WHERE viewed_user_id = $1",
            user['id']
        )

        # Статистика по активности
        if user['activity_interest']:
            same_activity_users = await conn.fetchval('''
                SELECT COUNT(*) FROM users 
                WHERE is_published = TRUE 
                    AND id != $1 
                    AND activity_interest = $2
            ''', user['id'], user['activity_interest'])
        else:
            same_activity_users = 0

    stats_text = (
        "📊 Ваша статистика:\n\n"
        f"❤️ Лайков отправлено: {likes_given}\n"
        f"❤️ Лайков получено: {likes_received}\n"
        f"🤝 Взаимных лайков: {mutual_likes}\n"
        f"👁️ Просмотров вашей анкеты: {profile_views}\n"
    )

    if user['activity_interest']:
        stats_text += f"\n🎯 Активность: {user['activity_interest']}\n"
        stats_text += f"👥 Пользователей с такой же активностью: {same_activity_users}\n"

    stats_text += f"\n📢 Статус анкеты: {'✅ Опубликована' if user['is_published'] else '❌ Не опубликована'}"

    await message.answer(
        stats_text,
        reply_markup=get_main_menu_keyboard(is_authenticated=True)
    )


# ============================================
# ТЕСТОВЫЕ КОМАНДЫ ДЛЯ ОТЛАДКИ (удалить в продакшене)
# ============================================

@router.message(F.text == "/reset_views_test")
async def reset_views_test(message: Message, state: FSMContext):
    """Сброс просмотров и лайков для текущего пользователя"""
    try:
        await state.clear()

        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT id FROM users WHERE telegram_id = $1",
                message.from_user.id
            )

            if user:
                deleted_views = await conn.execute(
                    "DELETE FROM profile_views WHERE viewer_id = $1",
                    user['id']
                )
                deleted_likes = await conn.execute(
                    "DELETE FROM likes WHERE from_user_id = $1",
                    user['id']
                )
                deleted_matches = await conn.execute(
                    "DELETE FROM matches WHERE from_user_id = $1",
                    user['id']
                )
                await message.answer(
                    f"✅ Просмотры, лайки и встречи сброшены!\n"
                    f"• Удалено просмотров: {deleted_views.split()[-1] if deleted_views else '0'}\n"
                    f"• Удалено лайков: {deleted_likes.split()[-1] if deleted_likes else '0'}\n"
                    f"• Удалено встреч: {deleted_matches.split()[-1] if deleted_matches else '0'}"
                )
            else:
                await message.answer("❌ Вы не найдены в базе данных")

    except Exception as e:
        logging.error(f"❌ Ошибка при сбросе просмотров: {e}")
        await message.answer("❌ Ошибка при сбросе просмотров")


@router.message(F.text == "/check_users")
async def check_users(message: Message):
    """Проверка наличия опубликованных пользователей"""
    try:
        async with db.pool.acquire() as conn:
            # Проверяем текущего пользователя
            current = await conn.fetchrow(
                "SELECT id, username, first_name, is_published, is_authenticated, is_active, activity_interest, telegram_real_username FROM users WHERE telegram_id = $1",
                message.from_user.id
            )

            if not current:
                await message.answer("❌ Вы не найдены в базе данных")
                return

            # Считаем всех опубликованных пользователей кроме себя
            others = await conn.fetch('''
                SELECT id, username, first_name, is_published, is_authenticated, is_active, 
                       activity_interest, activity_location, activity_time, telegram_id, telegram_real_username
                FROM users 
                WHERE telegram_id != $1
                ORDER BY is_published DESC, id
            ''', message.from_user.id)

            # Дешифруем имя текущего пользователя
            current_name = decrypt_data(current['first_name']) if current['first_name'] else "без имени"

            text = f"👤 Ваш профиль:\n"
            text += f"• ID: {current['id']}\n"
            text += f"• Имя: {current_name}\n"
            text += f"• Telegram ID: {current['telegram_id']}\n"
            text += f"• Логин в боте: @{current['username']}\n"
            text += f"• Telegram username: @{current['telegram_real_username'] if current['telegram_real_username'] else 'Не указан'}\n"
            text += f"• Активность: {current['activity_interest'] or 'Не указана'}\n"
            text += f"• Опубликован: {'✅ Да' if current['is_published'] else '❌ Нет'}\n"
            text += f"• Авторизован: {'✅ Да' if current['is_authenticated'] else '❌ Нет'}\n"
            text += f"• Активен: {'✅ Да' if current['is_active'] else '❌ Нет'}\n\n"

            text += f"📊 Всего других пользователей: {len(others)}\n\n"

            if others:
                text += "📋 Список других пользователей:\n"
                published_count = 0
                with_activity_count = 0

                for i, user in enumerate(others, 1):
                    decrypted_name = decrypt_data(user['first_name']) if user['first_name'] else "без имени"
                    status = "✅" if user['is_published'] else "❌"
                    activity_status = "🎯" if user['activity_interest'] else "❌"

                    if user['is_published'] and user['is_authenticated'] and user['is_active']:
                        published_count += 1

                    if user['activity_interest']:
                        with_activity_count += 1

                    text += f"{i}. {status} {activity_status} {decrypted_name} (Telegram: @{user['telegram_real_username'] if user['telegram_real_username'] else user['username']})"

                    if user['activity_interest']:
                        text += f" - {user['activity_interest']}\n"
                    else:
                        text += " - Без активности\n"

            text += f"\n📈 Доступно для поиска: {published_count} пользователей\n"
            text += f"🎯 С заполненной активностью: {with_activity_count} пользователей"

            if published_count == 0:
                text += "\n\n⚠️ Для тестирования создайте еще одного пользователя и опубликуйте его анкету!"

        await message.answer(text)

    except Exception as e:
        logging.error(f"❌ Ошибка при проверке пользователей: {e}")
        await message.answer("❌ Ошибка при проверке пользователей")