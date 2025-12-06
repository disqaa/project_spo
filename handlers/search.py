from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto, ReplyKeyboardMarkup
import asyncio

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
        await show_next_profile(message, state)
    else:
        # Показываем первую анкету без фильтров
        await message.answer(
            "🔍 Начинаем поиск анкет...",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        await show_next_profile(message, state)


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
            f"🎯 **Текущие фильтры:**\n\n"
            f"• Интерес: {filter_data['interest'] or 'Любой'}\n"
            f"• Место: {filter_data['location'] or 'Любое'}\n"
            f"• Время: {filter_data['time_period'] or 'Любое'}\n\n"
            f"Выберите действие:"
        )
    else:
        filter_text = "🎯 **Настройте фильтры поиска:**\n\nФильтры еще не настроены."

    await message.answer(
        filter_text,
        parse_mode="Markdown",
        reply_markup=get_search_filters_keyboard()
    )


# Выбор фильтра по интересу
@router.message(F.text == "🎯 По интересу")
async def filter_by_interest(message: Message, state: FSMContext):
    interests = ["🏃 Спорт", "🎬 Кино", "☕ Кафе/Бар", "🎮 Настольные игры", "👋 Любой интерес"]

    keyboard = []
    for interest in interests:
        keyboard.append([interest])
    keyboard.append(["❌ Отмена"])

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
        keyboard.append([time])
    keyboard.append(["❌ Отмена"])

    await message.answer(
        "⏰ Выберите период времени:",
        reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )

    await state.set_state(FilterStates.choosing_time)
    await state.update_data(filter_type="time")


# Сброс фильтров
@router.message(F.text == "🧹 Сбросить фильтры")
async def reset_filters(message: Message):
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
    await show_next_profile(message, state)


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
                keyboard=[[i] for i in valid_interests] + [["❌ Отмена"]],
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
                keyboard=[[t] for t in valid_times] + [["❌ Отмена"]],
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

    await state.clear()
    await message.answer(
        f"✅ Фильтр по времени сохранен: {message.text if time_period else 'Любое время'}",
        reply_markup=get_search_filters_keyboard()
    )


# Показать следующую анкету с учетом фильтров
async def show_next_profile(message: Message, state: FSMContext, edit: bool = False):
    """Показывает следующую анкету с учетом фильтров"""
    user_id = None

    # Получаем ID текущего пользователя
    async with db.pool.acquire() as conn:
        current_user = await conn.fetchrow(
            "SELECT id FROM users WHERE telegram_id = $1",
            message.from_user.id
        )
        user_id = current_user['id']

    # Получаем текущие фильтры
    state_data = await state.get_data()
    filters = state_data.get('current_filters', {})

    # Получаем список уже просмотренных пользователей
    async with db.pool.acquire() as conn:
        viewed_users = await conn.fetch(
            "SELECT viewed_user_id FROM profile_views WHERE viewer_id = $1",
            user_id
        )
        viewed_ids = [view['viewed_user_id'] for view in viewed_users]
        viewed_ids.append(user_id)  # Исключаем себя

        # Формируем запрос с учетом фильтров
        query = '''
            SELECT * FROM users 
            WHERE is_published = TRUE 
                AND id NOT IN (SELECT unnest($1::int[]))
                AND is_active = TRUE
                AND is_authenticated = TRUE
        '''
        params = [viewed_ids]

        # Добавляем фильтры
        param_counter = 2

        if filters.get('interest'):
            query += f" AND activity_interest = ${param_counter}"
            params.append(filters['interest'])
            param_counter += 1

        if filters.get('location'):
            query += f" AND activity_location ILIKE ${param_counter}"
            params.append(f'%{filters["location"]}%')
            param_counter += 1

        if filters.get('time_period'):
            query += f" AND activity_time = ${param_counter}"
            params.append(filters['time_period'])
            param_counter += 1

        query += " ORDER BY RANDOM() LIMIT 1"

        profile = await conn.fetchrow(query, *params)

    if not profile:
        # Если не нашли по фильтрам, пробуем найти без фильтров
        if filters.get('interest') or filters.get('location') or filters.get('time_period'):
            await message.answer(
                "😔 Не найдено анкет по текущим фильтрам.\n"
                "Попробуйте изменить или сбросить фильтры.",
                reply_markup=get_main_menu_keyboard(is_authenticated=True)
            )
            await state.clear()
            return

        await message.answer(
            "😔 Пока нет других опубликованных анкет. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        await state.clear()
        return

    # Сохраняем текущий профиль в состоянии
    await state.update_data(current_profile_id=profile['id'])

    # Записываем просмотр
    async with db.pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO profile_views (viewer_id, viewed_user_id)
            VALUES ($1, $2)
            ON CONFLICT (viewer_id, viewed_user_id) DO NOTHING
        ''', user_id, profile['id'])

    # Дешифруем данные
    decrypted_first_name = decrypt_data(profile['first_name'])
    decrypted_interests = decrypt_data(profile['interests']) if profile['interests'] else "Не указано"
    decrypted_about = decrypt_data(profile['about']) if profile['about'] else "Не указано"
    decrypted_location = decrypt_data(profile['activity_location']) if profile['activity_location'] else "Не указано"
    decrypted_description = decrypt_data(profile['activity_description']) if profile['activity_description'] else ""

    # Формируем информацию об анкете
    profile_info = (
        "👤 **Найденная анкета:**\n\n"
        f"👤 Имя: {decrypted_first_name}\n"
        f"🎂 Возраст: {profile['age']} лет\n"
        f"🎯 Интересы: {decrypted_interests}\n"
        f"📝 О себе: {decrypted_about}\n"
    )

    if profile['activity_interest']:
        profile_info += f"\n🎯 **Предлагаемая активность:**\n"
        profile_info += f"• Интерес: {profile['activity_interest']}\n"
        profile_info += f"• Место: {decrypted_location}\n"
        profile_info += f"• Время: {profile['activity_time']}\n"
        if decrypted_description:
            profile_info += f"• Описание: {decrypted_description}\n"

    profile_info += "\nЧто делаем?"

    if profile['photo_id']:
        if edit:
            await message.edit_media(
                media=InputMediaPhoto(media=profile['photo_id'], caption=profile_info),
                reply_markup=get_search_keyboard()
            )
        else:
            await message.answer_photo(
                photo=profile['photo_id'],
                caption=profile_info,
                parse_mode="Markdown",
                reply_markup=get_search_keyboard()
            )
    else:
        if edit:
            await message.edit_text(
                text=profile_info,
                parse_mode="Markdown",
                reply_markup=get_search_keyboard()
            )
        else:
            await message.answer(
                profile_info,
                parse_mode="Markdown",
                reply_markup=get_search_keyboard()
            )

    await state.set_state(SearchStates.browsing)


# ... (импорты остаются такими же)

# Обработка лайка - ИСПРАВЛЕННАЯ ВЕРСИЯ
@router.callback_query(SearchStates.browsing, F.data == "like")
async def like_profile(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    profile_id = data.get('current_profile_id')

    if not profile_id:
        await callback.answer("❌ Ошибка: профиль не найден")
        return

    try:
        # Получаем ID текущего пользователя
        async with db.pool.acquire() as conn:
            current_user = await conn.fetchrow(
                "SELECT id, telegram_id, username, first_name, activity_interest, activity_location, activity_time FROM users WHERE telegram_id = $1",
                callback.from_user.id
            )
            user_id = current_user['id']

            # Проверяем, нет ли взаимного лайка
            mutual_like = await conn.fetchrow('''
                SELECT * FROM likes 
                WHERE user_id = $1 AND liked_user_id = $2
            ''', profile_id, user_id)

            # Получаем данные пользователя, которого лайкнули
            liked_user = await conn.fetchrow(
                "SELECT telegram_id, username, first_name, activity_interest, activity_location, activity_time, activity_description FROM users WHERE id = $1",
                profile_id
            )

            if not liked_user:
                await callback.answer("❌ Пользователь не найден")
                return

            # Сохраняем лайк
            await conn.execute('''
                INSERT INTO likes (user_id, liked_user_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, liked_user_id) DO NOTHING
            ''', user_id, profile_id)

            # Обновляем счетчик лайков у пользователя, которого лайкнули
            await conn.execute(
                "UPDATE users SET likes_received_count = likes_received_count + 1 WHERE id = $1",
                profile_id
            )

            # Создаем запись о встрече (match)
            await conn.execute('''
                INSERT INTO matches (user1_id, user2_id, status)
                VALUES ($1, $2, 'pending')
                ON CONFLICT (user1_id, user2_id) DO NOTHING
            ''', user_id, profile_id)

        if mutual_like:
            # Взаимный лайк - отправляем уведомление обоим
            decrypted_name = decrypt_data(liked_user['first_name'])
            decrypted_location = decrypt_data(liked_user['activity_location']) if liked_user[
                'activity_location'] else ""
            decrypted_description = decrypt_data(liked_user['activity_description']) if liked_user[
                'activity_description'] else ""

            # Уведомление текущему пользователю
            try:
                await callback.message.edit_caption(
                    caption=f"🎉 **Взаимный лайк!**\n\n"
                            f"👤 {decrypted_name} тоже лайкнул(а) вашу анкету!\n\n"
                            f"🎯 Общая активность: {liked_user['activity_interest']}\n"
                            f"📍 Место: {decrypted_location}\n"
                            f"⏰ Время: {liked_user['activity_time']}\n\n"
                            f"📞 Контакт: @{liked_user['username']}\n\n"
                            f"Перейдите в '🤝 Мои встречи' для подтверждения встречи!",
                    reply_markup=None
                )
            except:
                # Если не удалось редактировать сообщение, отправляем новое
                await callback.message.answer(
                    f"🎉 **Взаимный лайк!**\n\n"
                    f"👤 {decrypted_name} тоже лайкнул(а) вашу анкету!\n\n"
                    f"🎯 Общая активность: {liked_user['activity_interest']}\n"
                    f"📍 Место: {decrypted_location}\n"
                    f"⏰ Время: {liked_user['activity_time']}\n\n"
                    f"📞 Контакт: @{liked_user['username']}\n\n"
                    f"Перейдите в '🤝 Мои встречи' для подтверждения встречи!",
                    parse_mode="Markdown"
                )

            # Уведомление другому пользователю
            decrypted_current_name = decrypt_data(current_user['first_name'])
            current_location = decrypt_data(current_user['activity_location']) if current_user[
                'activity_location'] else ""

            try:
                await callback.bot.send_message(
                    chat_id=liked_user['telegram_id'],
                    text=f"🎉 **Взаимный лайк!**\n\n"
                         f"👤 {decrypted_current_name} тоже лайкнул(а) вашу анкету!\n\n"
                         f"🎯 Общая активность: {current_user['activity_interest']}\n"
                         f"📍 Место: {current_location}\n"
                         f"⏰ Время: {current_user['activity_time']}\n\n"
                         f"📞 Контакт: @{current_user['username']}\n\n"
                         f"Перейдите в '🤝 Мои встречи' для подтверждения встречи!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {liked_user['telegram_id']}: {e}")

            await callback.answer("🎉 Взаимный лайк!")

        else:
            # Обычный лайк - уведомляем другого пользователя
            decrypted_current_name = decrypt_data(current_user['first_name'])
            current_location = decrypt_data(current_user['activity_location']) if current_user[
                'activity_location'] else ""

            try:
                await callback.bot.send_message(
                    chat_id=liked_user['telegram_id'],
                    text=f"❤️ **Новый лайк!**\n\n"
                         f"👤 {decrypted_current_name} лайкнул(а) вашу анкету!\n\n"
                         f"🎯 Предлагает: {current_user['activity_interest']}\n"
                         f"📍 Место: {current_location}\n"
                         f"⏰ Время: {current_user['activity_time']}\n\n"
                         f"Перейдите в '🤝 Мои встречи' чтобы ответить на запрос встречи!",
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {liked_user['telegram_id']}: {e}")

            await callback.answer("❤️ Лайк отправлен!")

            # Показываем следующую анкету через секунду
            await asyncio.sleep(1)
            await show_next_profile(callback.message, state, edit=True)

    except Exception as e:
        print(f"❌ Ошибка при обработке лайка: {e}")
        await callback.answer("❌ Произошла ошибка, попробуйте еще раз")


# Обработка пропуска - ИСПРАВЛЕННАЯ ВЕРСИЯ
@router.callback_query(SearchStates.browsing, F.data == "skip")
async def skip_profile(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer("➡️ Пропущено")
        await show_next_profile(callback.message, state, edit=True)
    except Exception as e:
        print(f"❌ Ошибка при пропуске: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# ... (остальной код остается без изменений)


# Настройка фильтров во время поиска
@router.callback_query(SearchStates.browsing, F.data == "filters")
async def set_filters_during_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="⚙️ Настройте фильтры поиска:",
        reply_markup=get_save_filter_keyboard()
    )


# Сохранение фильтра и продолжение поиска
@router.callback_query(F.data == "save_filter")
async def save_filter_and_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="🔍 Возвращаемся к поиску с текущими фильтрами...",
        reply_markup=None
    )
    await show_next_profile(callback.message, state, edit=True)

# Настройка фильтров во время поиска
@router.callback_query(SearchStates.browsing, F.data == "filters")
async def set_filters_during_search(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_caption(
            caption="⚙️ Настройте фильтры поиска:",
            reply_markup=get_save_filter_keyboard()
        )
    except Exception as e:
        print(f"❌ Ошибка при настройке фильтров: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")

# Сохранение фильтра и продолжение поиска
@router.callback_query(F.data == "save_filter")
async def save_filter_and_search(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_caption(
            caption="🔍 Возвращаемся к поиску с текущими фильтрами...",
            reply_markup=None
        )
        await show_next_profile(callback.message, state, edit=True)
    except Exception as e:
        print(f"❌ Ошибка при сохранении фильтра: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")

# Обработка отмены фильтра
@router.callback_query(F.data == "cancel_filter")
async def cancel_filter(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_caption(
            caption="❌ Настройка фильтров отменена.",
            reply_markup=None
        )
        await callback.answer("❌ Отменено")
    except Exception as e:
        print(f"❌ Ошибка при отмене фильтра: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")

# Обработка поиска с фильтром
@router.callback_query(F.data == "search_with_filter")
async def search_with_filter_callback(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_caption(
            caption="🔍 Начинаем поиск с текущими фильтрами...",
            reply_markup=None
        )
        await show_next_profile(callback.message, state, edit=True)
    except Exception as e:
        print(f"❌ Ошибка при поиске с фильтром: {e}")
        await callback.answer("❌ Ошибка, попробуйте еще раз")


# Остановка поиска
@router.callback_query(SearchStates.browsing, F.data == "stop_search")
async def stop_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_caption(
        caption="🔍 Поиск завершен.",
        reply_markup=None
    )
    await callback.message.answer(
        "Вы вышли из режима поиска.",
        reply_markup=get_main_menu_keyboard(is_authenticated=True)
    )
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
            "SELECT COUNT(*) FROM likes WHERE user_id = $1",
            user['id']
        )

        likes_received = await conn.fetchval(
            "SELECT COUNT(*) FROM likes WHERE liked_user_id = $1",
            user['id']
        )

        mutual_likes = await conn.fetchval('''
            SELECT COUNT(*) FROM likes l1
            JOIN likes l2 ON l1.user_id = l2.liked_user_id AND l1.liked_user_id = l2.user_id
            WHERE l1.user_id = $1
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
        "📊 **Ваша статистика:**\n\n"
        f"❤️ Лайков отправлено: {likes_given}\n"
        f"❤️ Лайков получено: {likes_received}\n"
        f"🤝 Взаимных лайков: {mutual_likes}\n"
        f"👁️ Просмотров вашей анкеты: {profile_views}\n"
    )

    if user['activity_interest']:
        stats_text += f"\n🎯 **Активность:** {user['activity_interest']}\n"
        stats_text += f"👥 Пользователей с такой же активностью: {same_activity_users}\n"

    stats_text += f"\n📢 Статус анкеты: {'✅ Опубликована' if user['is_published'] else '❌ Не опубликована'}"

    await message.answer(
        stats_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard(is_authenticated=True)
    )