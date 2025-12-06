from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import get_main_menu_keyboard, get_profile_keyboard, get_back_to_menu_keyboard, get_edit_profile_keyboard
from database import db
from utils import decrypt_data, encrypt_data

router = Router()


class EditProfileStates(StatesGroup):
    editing_interests = State()
    editing_about = State()
    editing_photo = State()


# Просмотр профиля
@router.message(F.text == "👤 Профиль")
async def view_profile(message: Message):
    # Получаем пользователя
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

    # Дешифруем данные
    decrypted_first_name = decrypt_data(user['first_name'])
    decrypted_interests = decrypt_data(user['interests']) if user['interests'] else "Не указано"
    decrypted_about = decrypt_data(user['about']) if user['about'] else "Не указано"

    # Формируем информацию о профиле
    profile_info = (
        "👤 **Ваш профиль:**\n\n"
        f"🆔 ID: `{user['id']}`\n"
        f"👤 Логин: `{user['username']}`\n"
        f"👤 Имя: {decrypted_first_name}\n"
        f"🎂 Возраст: {user['age']} лет\n"
        f"🎯 Интересы: {decrypted_interests}\n"
        f"📝 О себе: {decrypted_about}\n"
        f"📢 Статус анкеты: {'✅ Опубликована' if user['is_published'] else '❌ Не опубликована'}\n"
        f"📅 Дата регистрации: {user['created_at'].strftime('%d.%m.%Y %H:%M') if user['created_at'] else 'Неизвестно'}"
    )

    if user['photo_id']:
        await message.answer_photo(
            photo=user['photo_id'],
            caption=profile_info,
            parse_mode="Markdown",
            reply_markup=get_profile_keyboard(user['is_published'])
        )
    else:
        await message.answer(
            profile_info,
            parse_mode="Markdown",
            reply_markup=get_profile_keyboard(user['is_published'])
        )


# Публикация анкеты
@router.message(F.text == "📢 Опубликовать анкету")
async def publish_profile(message: Message):
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

        # Проверяем, заполнены ли обязательные поля
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

        await message.answer(
            "✅ Ваша анкета опубликована!\n"
            "Теперь другие пользователи смогут вас найти в поиске.",
            reply_markup=get_profile_keyboard(True)
        )


# Снятие анкеты с публикации
@router.message(F.text == "🔒 Снять с публикации")
async def unpublish_profile(message: Message):
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

        await conn.execute(
            "UPDATE users SET is_published = FALSE WHERE telegram_id = $1",
            message.from_user.id
        )

        await message.answer(
            "✅ Ваша анкета снята с публикации.",
            reply_markup=get_profile_keyboard(False)
        )


# Редактирование профиля
@router.message(F.text == "✏️ Редактировать профиль")
async def edit_profile(message: Message):
    await message.answer(
        "✏️ **Редактирование профиля:**\n\n"
        "Выберите, что хотите изменить:",
        reply_markup=get_edit_profile_keyboard()
    )


# Назад в профиль
@router.message(F.text == "↩️ Назад в профиль")
async def back_to_profile(message: Message, state: FSMContext):
    await state.clear()
    await view_profile(message)


# Изменить интересы
@router.message(F.text == "📝 Изменить интересы")
async def change_interests(message: Message, state: FSMContext):
    # Получаем текущие интересы пользователя
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

    if user:
        current_interests = decrypt_data(user['interests']) if user['interests'] else ""
        await message.answer(
            f"✏️ Введите новые интересы:\n"
            f"Текущие: {current_interests}\n\n"
            "(Максимум 500 символов)\n"
            "Напишите 'очистить', чтобы удалить интересы",
            reply_markup=get_back_to_menu_keyboard()
        )
    else:
        await message.answer(
            "✏️ Введите новые интересы:\n"
            "(Максимум 500 символов)",
            reply_markup=get_back_to_menu_keyboard()
        )

    await state.set_state(EditProfileStates.editing_interests)


@router.message(EditProfileStates.editing_interests)
async def process_new_interests(message: Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer(
            "Редактирование отменено",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        return

    if message.text.lower() == "очистить":
        new_interests = ""
    else:
        new_interests = message.text.strip()

    if len(new_interests) > 500:
        await message.answer(
            "❌ Слишком длинный текст! Максимум 500 символов\n"
            "Введите интересы еще раз:"
        )
        return

    # Шифруем и сохраняем
    encrypted_interests = encrypt_data(new_interests)

    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET interests = $1 WHERE telegram_id = $2",
            encrypted_interests, message.from_user.id
        )

    await state.clear()

    # Получаем обновленного пользователя для клавиатуры
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

    await message.answer(
        "✅ Интересы обновлены!",
        reply_markup=get_profile_keyboard(user['is_published'] if user else False)
    )


# Изменить "о себе"
@router.message(F.text == "📝 Изменить 'О себе'")
async def change_about(message: Message, state: FSMContext):
    # Получаем текущее "о себе" пользователя
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

    if user:
        current_about = decrypt_data(user['about']) if user['about'] else ""
        await message.answer(
            f"✏️ Введите новую информацию о себе:\n"
            f"Текущая: {current_about}\n\n"
            "(Максимум 1000 символов)\n"
            "Напишите 'очистить', чтобы удалить информацию",
            reply_markup=get_back_to_menu_keyboard()
        )
    else:
        await message.answer(
            "✏️ Введите новую информацию о себе:\n"
            "(Максимум 1000 символов)",
            reply_markup=get_back_to_menu_keyboard()
        )

    await state.set_state(EditProfileStates.editing_about)


@router.message(EditProfileStates.editing_about)
async def process_new_about(message: Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await state.clear()
        await message.answer(
            "Редактирование отменено",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
        return

    if message.text.lower() == "очистить":
        new_about = ""
    else:
        new_about = message.text.strip()

    if len(new_about) > 1000:
        await message.answer(
            "❌ Слишком длинный текст! Максимум 1000 символов\n"
            "Введите текст еще раз:"
        )
        return

    # Шифруем и сохраняем
    encrypted_about = encrypt_data(new_about)

    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET about = $1 WHERE telegram_id = $2",
            encrypted_about, message.from_user.id
        )

    await state.clear()

    # Получаем обновленного пользователя для клавиатуры
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

    await message.answer(
        "✅ Информация о себе обновлена!",
        reply_markup=get_profile_keyboard(user['is_published'] if user else False)
    )