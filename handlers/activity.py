from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import ActivityStates
from keyboards import (
    get_profile_keyboard, get_cancel_keyboard,
    get_confirmation_keyboard, get_activity_interests_keyboard,
    get_activity_time_keyboard
)
from database import db
from utils import encrypt_data, decrypt_data

router = Router()


# Изменить активность
@router.message(F.text == "🎯 Изменить активность")
async def change_activity(message: Message, state: FSMContext):
    # Получаем текущую активность пользователя
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

    if user and user['activity_interest']:
        decrypted_location = decrypt_data(user['activity_location']) if user['activity_location'] else ""
        decrypted_description = decrypt_data(user['activity_description']) if user['activity_description'] else ""

        await message.answer(
            f"🎯 Ваша текущая активность:\n\n"
            f"Интерес: {user['activity_interest']}\n"
            f"Место: {decrypted_location}\n"
            f"Время: {user['activity_time']}\n"
            f"Описание: {decrypted_description}\n\n"
            f"Выберите новый интерес для встречи:",
            reply_markup=get_activity_interests_keyboard()
        )
    else:
        await message.answer(
            "🎯 Выберите интерес для встречи:\n\n"
            "🏃 Спорт - совместные тренировки, игры\n"
            "🎬 Кино - поход в кинотеатр\n"
            "☕ Кафе/Бар - встреча за чашкой кофе\n"
            "🎮 Настольные игры - игровой вечер",
            reply_markup=get_activity_interests_keyboard()
        )

    await state.set_state(ActivityStates.choosing_interest)


# Обработка выбора интереса
@router.message(ActivityStates.choosing_interest)
async def process_activity_interest(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Изменение активности отменено",
            reply_markup=get_profile_keyboard()
        )
        return

    valid_interests = ["🏃 Спорт", "🎬 Кино", "☕ Кафе/Бар", "🎮 Настольные игры"]

    if message.text not in valid_interests:
        await message.answer(
            "❌ Пожалуйста, выберите интерес из предложенных:",
            reply_markup=get_activity_interests_keyboard()
        )
        return

    await state.update_data(activity_interest=message.text)

    await message.answer(
        f"📍 Отлично! Вы выбрали: {message.text}\n\n"
        "Теперь укажите место встречи (например):\n"
        "• Для спорта: 'Спортзал на Ленина', 'Стадион Центральный'\n"
        "• Для кино: 'Кинотеатр Октябрь', 'Макси'\n"
        "• Для кафе: 'Кофейня на Пушкина', 'Бар Старый город'\n"
        "• Для игр: 'Игровой клуб', 'Домашняя атмосфера'\n\n"
        "Или укажите свое место:",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(ActivityStates.entering_location)


# Обработка ввода места
@router.message(ActivityStates.entering_location)
async def process_activity_location(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Изменение активности отменено",
            reply_markup=get_profile_keyboard()
        )
        return

    if len(message.text) < 3:
        await message.answer(
            "❌ Слишком короткое название места. Минимум 3 символа. Введите еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(activity_location=message.text)

    await message.answer(
        "⏰ Теперь выберите время для встречи:",
        reply_markup=get_activity_time_keyboard()
    )

    await state.set_state(ActivityStates.entering_time)


# Обработка ввода времени
@router.message(ActivityStates.entering_time)
async def process_activity_time(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Изменение активности отменено",
            reply_markup=get_profile_keyboard()
        )
        return

    valid_times = ["👋 Сегодня", "📅 Завтра", "🗓️ В ближайшие дни", "🌆 Вечером",
                   "🌅 Утром", "🌞 В выходные", "⏰ Любое время"]

    if message.text not in valid_times:
        await message.answer(
            "❌ Пожалуйста, выберите время из предложенных:",
            reply_markup=get_activity_time_keyboard()
        )
        return

    await state.update_data(activity_time=message.text)

    await message.answer(
        "📝 Теперь кратко опишите, что вы предлагаете или чего ожидаете:\n"
        "(Например: 'Ищу партнера для игры в настольный теннис', 'Хочу посмотреть новый фильм в компании')",
        reply_markup=get_cancel_keyboard()
    )

    await state.set_state(ActivityStates.entering_description)


# Обработка ввода описания
@router.message(ActivityStates.entering_description)
async def process_activity_description(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Изменение активности отменено",
            reply_markup=get_profile_keyboard()
        )
        return

    if len(message.text) > 500:
        await message.answer(
            "❌ Слишком длинное описание. Максимум 500 символов. Сократите и отправьте еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(activity_description=message.text)

    # Получаем все данные
    data = await state.get_data()

    # Формируем сообщение для подтверждения
    confirmation_text = (
        "🎯 **Проверьте вашу активность:**\n\n"
        f"**Интерес:** {data['activity_interest']}\n"
        f"**Место:** {data['activity_location']}\n"
        f"**Время:** {data['activity_time']}\n"
        f"**Описание:** {data['activity_description']}\n\n"
        "Всё верно? Эта активность будет видна другим пользователям."
    )

    await message.answer(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=get_confirmation_keyboard()
    )

    await state.set_state(ActivityStates.confirmation)


# Подтверждение активности
@router.callback_query(ActivityStates.confirmation)
async def confirm_activity(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "confirm":
        # Шифруем чувствительные данные
        encrypted_location = encrypt_data(data['activity_location'])
        encrypted_description = encrypt_data(data['activity_description'])

        # Сохраняем в базу данных
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE users 
                SET activity_interest = $1, activity_location = $2, 
                    activity_time = $3, activity_description = $4
                WHERE telegram_id = $5
            ''',
                               data['activity_interest'],
                               encrypted_location,
                               data['activity_time'],
                               encrypted_description,
                               callback.from_user.id
                               )

        await callback.message.edit_reply_markup(reply_markup=None)

        await callback.message.answer(
            "✅ Активность сохранена!\n\n"
            f"Теперь другие пользователи смогут найти вас по активности: {data['activity_interest']}",
            reply_markup=get_profile_keyboard()
        )

        await state.clear()

    elif callback.data == "cancel":
        await state.clear()
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "❌ Изменение активности отменено",
            reply_markup=get_profile_keyboard()
        )


# Публикация анкеты с проверкой активности
@router.message(F.text == "📢 Опубликовать анкету")
async def publish_profile_with_activity(message: Message):
    async with db.pool.acquire() as conn:
        # Проверяем, авторизован ли пользователь
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

        # Проверяем, заполнена ли активность
        if not user['activity_interest']:
            await message.answer(
                "❌ Для публикации анкеты необходимо заполнить активность!\n\n"
                "Нажмите '🎯 Изменить активность' чтобы указать:\n"
                "• Интерес для встречи\n"
                "• Место\n"
                "• Время\n\n"
                "Это поможет другим пользователям найти вас.",
                reply_markup=get_profile_keyboard(False)
            )
            return

        # Проверяем, есть ли фото
        if not user['photo_id']:
            await message.answer(
                "❌ Для публикации анкеты необходимо добавить фото!\n"
                "Используйте '✏️ Редактировать профиль' -> '📷 Изменить фото'",
                reply_markup=get_profile_keyboard(False)
            )
            return

        # Обновляем флаг публикации
        await conn.execute(
            "UPDATE users SET is_published = TRUE WHERE telegram_id = $1",
            message.from_user.id
        )

        # Дешифруем данные активности
        decrypted_location = decrypt_data(user['activity_location']) if user['activity_location'] else ""
        decrypted_description = decrypt_data(user['activity_description']) if user['activity_description'] else ""

        await message.answer(
            "✅ Ваша анкета опубликована!\n\n"
            f"🎯 **Ваша активность:**\n"
            f"• Интерес: {user['activity_interest']}\n"
            f"• Место: {decrypted_location}\n"
            f"• Время: {user['activity_time']}\n"
            f"• Описание: {decrypted_description}\n\n"
            "Теперь другие пользователи смогут вас найти в поиске по вашей активности.",
            reply_markup=get_profile_keyboard(True)
        )