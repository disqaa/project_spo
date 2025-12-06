from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
import aiofiles
import os

from states import RegistrationStates, LoginStates
from keyboards import get_main_menu_keyboard, get_cancel_keyboard, get_confirmation_keyboard, get_skip_keyboard, \
    get_back_to_menu_keyboard
from utils import (
    hash_password, verify_password,
    is_valid_age,
    is_valid_username, is_valid_password,
    save_photo,
    encrypt_data, decrypt_data
)
from database import db

router = Router()


# Регистрация - начало
@router.message(F.text == "🔐 Регистрация")
async def start_registration(message: Message, state: FSMContext):
    # Сначала проверяем, не зарегистрирован ли уже пользователь
    async with db.pool.acquire() as conn:
        existing_user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

    if existing_user:
        # Если пользователь уже существует, предлагаем войти или восстановить доступ
        if existing_user['is_authenticated']:
            await message.answer(
                f"✅ Вы уже зарегистрированы как {existing_user['username']}!\n"
                f"Вы уже авторизованы.",
                reply_markup=get_main_menu_keyboard(is_authenticated=True)
            )
        else:
            await message.answer(
                f"ℹ️ Аккаунт с вашим Telegram ID уже существует!\n"
                f"Логин: {existing_user['username']}\n\n"
                "Вы можете:\n"
                "1. Войти в существующий аккаунт\n"
                "2. Обратиться к администратору для удаления старого аккаунта",
                reply_markup=get_main_menu_keyboard(is_authenticated=False)
            )
        return

    # Добавляем информацию о использовании Telegram username
    await message.answer(
        "⚠️ Внимание!\n\n"
        "При регистрации мы сохраняем ваш реальный Telegram username (@никнейм).\n"
        "Это позволит другим пользователям связаться с вами при взаимных лайках.\n\n"
        "Если вы не хотите делиться своим Telegram username, вы можете:\n"
        "1. Изменить его в настройках Telegram\n"
        "2. Пропустить этот шаг (но тогда связь будет ограничена)\n\n"
        "Продолжаем регистрацию?\n"
        "Введите логин (от 3 до 20 символов, можно использовать буквы, цифры, точку и _):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_username)


# Обработка логина
@router.message(RegistrationStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    username = message.text.strip()

    # Валидация username
    if not is_valid_username(username):
        await message.answer(
            "❌ Неверный формат логина!\n"
            "Логин должен быть от 3 до 20 символов\n"
            "Можно использовать только буквы, цифры, точку и подчеркивание\n"
            "Попробуйте еще раз:"
        )
        return

    # Проверка на существование username
    async with db.pool.acquire() as conn:
        existing_user = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1",
            username
        )

    if existing_user:
        await message.answer(
            "❌ Этот логин уже занят!\n"
            "Пожалуйста, выберите другой логин:"
        )
        return

    await state.update_data(username=username)
    await message.answer(
        "✅ Логин принят!\n"
        "Теперь введите пароль (минимум 6 символов):"
    )
    await state.set_state(RegistrationStates.waiting_for_password)


# Обработка пароля
@router.message(RegistrationStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    password = message.text.strip()

    # Валидация пароля
    if not is_valid_password(password):
        await message.answer(
            "❌ Пароль должен быть минимум 6 символов!\n"
            "Введите пароль еще раз:"
        )
        return

    await state.update_data(password=password)
    await message.answer(
        "✅ Пароль принят!\n"
        "Теперь введите ваше имя (от 2 до 50 символов):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_first_name)


# Обработка имени
@router.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    first_name = message.text.strip()

    if len(first_name) < 2 or len(first_name) > 50:
        await message.answer(
            "❌ Имя должно быть от 2 до 50 символов\n"
            "Введите имя еще раз:"
        )
        return

    await state.update_data(first_name=first_name)
    await message.answer(
        "✅ Имя принято!\n"
        "Теперь введите ваш возраст (число от 1 до 120):"
    )
    await state.set_state(RegistrationStates.waiting_for_age)


# Обработка возраста
@router.message(RegistrationStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    is_valid_age_check, age = is_valid_age(message.text)

    if not is_valid_age_check:
        await message.answer(
            "❌ Неверный возраст!\n"
            "Введите число от 1 до 120:"
        )
        return

    await state.update_data(age=age)
    await message.answer(
        "✅ Возраст принят!\n"
        "Теперь напишите ваши интересы (хобби, увлечения):\n"
        "Можно пропустить, нажав '⏩ Пропустить'",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_interests)


# Обработка интересов
@router.message(RegistrationStates.waiting_for_interests)
async def process_interests(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    if message.text == "⏩ Пропустить":
        interests = ""
        await message.answer(
            "✅ Пропущено!\n"
            "Теперь расскажите немного о себе:\n"
            "Можно пропустить, нажав '⏩ Пропустить'",
            reply_markup=get_skip_keyboard()
        )
    else:
        interests = message.text.strip()
        if len(interests) > 500:
            await message.answer(
                "❌ Слишком длинный текст! Максимум 500 символов\n"
                "Введите интересы еще раз:"
            )
            return

        await message.answer(
            "✅ Интересы сохранены!\n"
            "Теперь расскажите немного о себе:\n"
            "Можно пропустить, нажав '⏩ Пропустить'",
            reply_markup=get_skip_keyboard()
        )

    await state.update_data(interests=interests)
    await state.set_state(RegistrationStates.waiting_for_about)


# Обработка "о себе"
@router.message(RegistrationStates.waiting_for_about)
async def process_about(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    if message.text == "⏩ Пропустить":
        about = ""
        await message.answer(
            "✅ Пропущено!\n"
            "Теперь отправьте ваше фото (одно фото):",
            reply_markup=get_cancel_keyboard()
        )
    else:
        about = message.text.strip()
        if len(about) > 1000:
            await message.answer(
                "❌ Слишком длинный текст! Максимум 1000 символов\n"
                "Введите текст еще раз:"
            )
            return

        await message.answer(
            "✅ Информация сохранена!\n"
            "Теперь отправьте ваше фото (одно фото):",
            reply_markup=get_cancel_keyboard()
        )

    await state.update_data(about=about)
    await state.set_state(RegistrationStates.waiting_for_photo)


# Обработка фото
@router.message(RegistrationStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    if message.text and message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    # Получаем фото с наилучшим качеством
    photo = message.photo[-1]

    # Получаем файл
    file = await message.bot.get_file(photo.file_id)

    # Скачиваем фото
    photo_data = await message.bot.download_file(file.file_path)

    # Сохраняем данные фото в состоянии
    await state.update_data(
        photo_id=photo.file_id,
        photo_data=photo_data.read()
    )

    # Получаем все данные
    data = await state.get_data()

    # Добавляем реальный Telegram username
    telegram_username = message.from_user.username
    data['telegram_username'] = telegram_username

    # Формируем сообщение для подтверждения
    confirmation_text = (
        "📋 Проверьте ваши данные:\n\n"
        f"👤 Логин в боте: {data['username']}\n"
        f"👤 Telegram username: @{telegram_username if telegram_username else 'Не указан'}\n"
        f"👤 Имя: {data['first_name']}\n"
        f"🎂 Возраст: {data['age']}\n"
    )

    if data.get('interests'):
        confirmation_text += f"🎯 Интересы: {data['interests'][:100]}...\n"

    if data.get('about'):
        confirmation_text += f"📝 О себе: {data['about'][:100]}...\n"

    confirmation_text += f"📷 Фото: отправлено\n\n"
    confirmation_text += f"⚠️ Важно: Telegram username будет доступен другим пользователям при взаимных лайках.\n\n"
    confirmation_text += "Всё верно?"

    await message.answer_photo(
        photo=data['photo_id'],
        caption=confirmation_text,
        reply_markup=get_confirmation_keyboard()
    )
    await state.set_state(RegistrationStates.confirmation)


# Подтверждение регистрации
@router.callback_query(RegistrationStates.confirmation)
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if callback.data == "confirm":
        # Проверяем, не появился ли уже пользователь с таким telegram_id
        async with db.pool.acquire() as conn:
            existing_user = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1",
                callback.from_user.id
            )

        if existing_user:
            await callback.message.edit_caption(
                caption=f"❌ Аккаунт с вашим Telegram ID уже существует!\n"
                        f"Логин: {existing_user['username']}\n\n"
                        f"Пожалуйста, войдите в существующий аккаунт.",
                reply_markup=None
            )
            await state.clear()
            return

        # Создаем хеш пароля
        salt, hashed_password = hash_password(data['password'])

        # Сохраняем фото
        photo_path = await save_photo(data['photo_data'], callback.from_user.id)

        # Получаем опциональные поля
        interests = data.get('interests', '')
        about = data.get('about', '')

        # Получаем Telegram username
        telegram_username = data.get('telegram_username', '')

        # Шифруем данные (если нужно)
        encrypted_first_name = encrypt_data(data['first_name'])
        encrypted_interests = encrypt_data(interests)
        encrypted_about = encrypt_data(about)

        try:
            # Сохраняем в базу данных
            async with db.pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users 
                    (telegram_id, username, password, first_name, age, interests, about, photo_path, photo_id, 
                     is_authenticated, telegram_real_username)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ''',
                                   callback.from_user.id,
                                   data['username'],
                                   f"{salt}:{hashed_password}",
                                   encrypted_first_name,
                                   data['age'],
                                   encrypted_interests,
                                   encrypted_about,
                                   photo_path,
                                   data['photo_id'],
                                   True,
                                   telegram_username
                                   )

            print(
                f"✅ Новый пользователь зарегистрирован: {data['username']}, Telegram ID: {callback.from_user.id}, Telegram username: {telegram_username}")

        except Exception as e:
            print(f"❌ Ошибка при сохранении пользователя: {e}")
            await callback.message.edit_caption(
                caption="❌ Ошибка при регистрации. Попробуйте позже.",
                reply_markup=None
            )
            await state.clear()
            return

        # Удаляем инлайн-клавиатуру
        await callback.message.edit_reply_markup(reply_markup=None)

        await callback.message.answer(
            "✅ Регистрация успешно завершена!\n"
            "Теперь вы авторизованы в системе.\n\n"
            f"👋 Добро пожаловать, {data['first_name']}!\n\n"
            "📢 Чтобы вас могли найти другие пользователи, "
            "опубликуйте свою анкету в профиле.\n\n"
            f"🔗 Ваш Telegram username: @{telegram_username if telegram_username else 'Не указан'}",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )

        await state.clear()

    elif callback.data == "cancel":
        await state.clear()
        await callback.message.edit_caption(
            caption="❌ Регистрация отменена",
            reply_markup=None
        )
        await callback.message.answer(
            "Регистрация отменена",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )


# Логин - начало
@router.message(F.text == "🚪 Войти")
async def start_login(message: Message, state: FSMContext):
    await message.answer(
        "Введите ваш логин:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LoginStates.waiting_for_username)


# Обработка логина при входе
@router.message(LoginStates.waiting_for_username)
async def process_login_username(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Вход отменен",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    username = message.text.strip()

    # Ищем пользователя ТОЛЬКО по логину
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1",
            username
        )

    if not user:
        await message.answer(
            "❌ Пользователь не найден!\n"
            "Проверьте логин или зарегистрируйтесь\n"
            "Введите логин еще раз:"
        )
        return

    await state.update_data(user_id=user['id'], username=username)
    await message.answer(
        "✅ Логин найден!\n"
        "Теперь введите пароль:"
    )
    await state.set_state(LoginStates.waiting_for_password)


# Обработка пароля при входе
@router.message(LoginStates.waiting_for_password)
async def process_login_password(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Вход отменен",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        return

    data = await state.get_data()
    user_id = data.get('user_id')

    if not user_id:
        await message.answer(
            "❌ Ошибка! Попробуйте войти заново",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        await state.clear()
        return

    # Получаем пользователя
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )

    if not user:
        await message.answer(
            "❌ Ошибка! Пользователь не найден",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        await state.clear()
        return

    # Проверяем пароль
    stored_password = user['password']
    try:
        salt, hashed_password = stored_password.split(":")
    except ValueError:
        await message.answer(
            "❌ Ошибка данных. Обратитесь к администратору",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )
        await state.clear()
        return

    if verify_password(message.text, salt, hashed_password):
        # Обновляем данные пользователя, включая Telegram username
        telegram_username = message.from_user.username

        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE users 
                SET is_authenticated = TRUE, telegram_id = $1, last_login = CURRENT_TIMESTAMP,
                    telegram_real_username = $2
                WHERE id = $3
            ''', message.from_user.id, telegram_username, user_id)

        # Дешифруем имя для приветствия
        decrypted_first_name = decrypt_data(user['first_name'])

        await message.answer(
            f"✅ Вход выполнен успешно!\n"
            f"👋 Добро пожаловать, {decrypted_first_name}!\n\n"
            f"🔗 Ваш Telegram username обновлен: @{telegram_username if telegram_username else 'Не указан'}",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
    else:
        await message.answer(
            "❌ Неверный пароль!\n"
            "Попробуйте еще раз или начните заново:",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )

    await state.clear()


# Выход из системы
@router.message(F.text == "🚪 Выйти")
async def logout(message: Message):
    # Находим пользователя
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1",
            message.from_user.id
        )

        if user:
            await conn.execute(
                "UPDATE users SET is_authenticated = FALSE WHERE telegram_id = $1",
                message.from_user.id
            )

    await message.answer(
        "✅ Вы вышли из системы",
        reply_markup=get_main_menu_keyboard(is_authenticated=False)
    )