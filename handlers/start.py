from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import get_main_menu_keyboard
from database import db

router = Router()


class UsernameConsentStates(StatesGroup):
    waiting_for_consent = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Очищаем состояние
    await state.clear()

    # Проверяем, есть ли пользователь в базе
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1 AND is_authenticated = TRUE",
            message.from_user.id
        )

    if user:
        # Пользователь авторизован
        await message.answer(
            f"👋 С возвращением!\n"
            f"Вы авторизованы как {user['username']}\n\n"
            f"Используйте меню для навигации:",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
    else:
        # Пользователь не авторизован - предлагаем разрешить использовать Telegram username
        user_has_telegram_username = message.from_user.username is not None

        if user_has_telegram_username:
            # У пользователя есть Telegram username - предлагаем разрешить его использование
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Разрешить использовать мой Telegram username",
                        callback_data="allow_username"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Не разрешать (продолжить без username)",
                        callback_data="deny_username"
                    )
                ]
            ])

            welcome_text = (
                f"👋 Добро пожаловать в бот знакомств!\n\n"
                f"🔍 Мы обнаружили ваш Telegram username: @{message.from_user.username}\n\n"
                f"⚠️ Для чего это нужно:\n"
                f"• При взаимных лайках другие пользователи смогут легко связаться с вами\n"
                f"• Вы получите прямую ссылку на Telegram профиль собеседника\n"
                f"• Это упрощает организацию встреч\n\n"
                f"🔒 Конфиденциальность:\n"
                f"• Ваш username будет виден ТОЛЬКО при взаимных лайках\n"
                f"• Мы никогда не показываем ваш username без вашего согласия\n"
                f"• Вы можете изменить решение в любое время\n\n"
                f"Выберите вариант:"
            )
        else:
            # У пользователя нет Telegram username
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👤 У меня нет Telegram username",
                        callback_data="no_username"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="ℹ️ Как создать username?",
                        callback_data="how_to_create_username"
                    )
                ]
            ])

            welcome_text = (
                f"👋 Добро пожаловать в бот знакомств!\n\n"
                f"📱 У вас нет Telegram username (@никнейм)\n\n"
                f"⚠️ Рекомендуется создать username для:\n"
                f"• Удобной связи при взаимных лайках\n"
                f"• Быстрого обмена контактами\n"
                f"• Простой организации встреч\n\n"
                f"Без username связь возможна только через Telegram ID, "
                f"что менее удобно для других пользователей.\n\n"
                f"Выберите вариант:"
            )

        await message.answer(
            welcome_text,
            reply_markup=keyboard
        )

        # Сохраняем информацию о username пользователя
        await state.update_data(
            telegram_username=message.from_user.username,
            has_username=user_has_telegram_username
        )
        await state.set_state(UsernameConsentStates.waiting_for_consent)


# Обработка согласия на использование username
@router.callback_query(UsernameConsentStates.waiting_for_consent, F.data == "allow_username")
async def allow_username(callback: CallbackQuery, state: FSMContext):
    # Сохраняем согласие в состоянии (можно также сохранить в базу)
    await state.update_data(username_allowed=True)

    # Убираем inline-клавиатуру из текущего сообщения
    await callback.message.edit_reply_markup(reply_markup=None)

    # Отправляем новое сообщение с reply-клавиатурой
    await callback.message.answer(
        "✅ Вы разрешили использовать ваш Telegram username.\n\n"
        "При взаимных лайках другие пользователи смогут увидеть вашу ссылку на Telegram.\n\n"
        "🔐 Для начала работы необходимо:\n"
        "1. Зарегистрироваться - кнопка '🔐 Регистрация'\n"
        "2. Войти в аккаунт - кнопка '🚪 Войти'\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_authenticated=False)
    )
    await state.clear()


# Обработка отказа от использования username
@router.callback_query(UsernameConsentStates.waiting_for_consent, F.data == "deny_username")
async def deny_username(callback: CallbackQuery, state: FSMContext):
    await state.update_data(username_allowed=False)

    # Убираем inline-клавиатуру из текущего сообщения
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        "❌ Вы отказались от использования Telegram username.\n\n"
        "Примечание:\n"
        "• При взаимных лайках связь будет через Telegram ID\n"
        "• Это менее удобно для других пользователей\n"
        "• Вы можете изменить это решение позже в профиле\n\n"
        "🔐 Для начала работы необходимо:\n"
        "1. Зарегистрироваться - кнопка '🔐 Регистрация'\n"
        "2. Войти в аккаунт - кнопка '🚪 Войти'\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_authenticated=False)
    )
    await state.clear()


# Обработка случая "нет username"
@router.callback_query(UsernameConsentStates.waiting_for_consent, F.data == "no_username")
async def no_username(callback: CallbackQuery, state: FSMContext):
    # Убираем inline-клавиатуру из текущего сообщения
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        "👤 Вы можете продолжить без Telegram username\n\n"
        "При взаимных лайках связь будет установлена через Telegram ID.\n\n"
        "📱 Чтобы создать username в будущем:\n"
        "1. Откройте настройки Telegram\n"
        "2. Перейдите в раздел 'Username'\n"
        "3. Установите желаемый никнейм\n"
        "4. Обновите настройки в боте через профиль\n\n"
        "🔐 Для начала работы необходимо:\n"
        "1. Зарегистрироваться - кнопка '🔐 Регистрация'\n"
        "2. Войти в аккаунт - кнопка '🚪 Войти'\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_authenticated=False)
    )
    await state.clear()


# Информация о создании username
@router.callback_query(UsernameConsentStates.waiting_for_consent, F.data == "how_to_create_username")
async def how_to_create_username(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👤 Продолжить без username",
                callback_data="no_username"
            )
        ]
    ])

    await callback.message.edit_text(
        "📱 Как создать Telegram username:\n\n"
        "На Android/iOS:\n"
        "1. Откройте Telegram\n"
        "2. Нажмите на меню (три полоски)\n"
        "3. Выберите 'Настройки'\n"
        "4. Нажмите на 'Изменить профиль'\n"
        "5. Найдите поле 'Username'\n"
        "6. Введите желаемый никнейм (например, @ivan_ivanov)\n"
        "7. Нажмите 'Сохранить'\n\n"
        "На компьютере:\n"
        "1. Откройте Telegram Desktop\n"
        "2. Нажмите на меню (три полоски)\n"
        "3. Выберите 'Настройки'\n"
        "4. Выберите 'Изменить профиль'\n"
        "5. В поле 'Username' введите желаемый никнейм\n"
        "6. Нажмите 'Сохранить'\n\n"
        "🔑 Советы:\n"
        "• Username должен быть уникальным\n"
        "• Можно использовать буквы, цифры и подчеркивания\n"
        "• Не используйте персональную информацию\n\n"
        "После создания username вернитесь в бот и начните заново (/start)",
        reply_markup=keyboard
    )


# Обработка возврата в главное меню
@router.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()

    # Проверяем авторизацию
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1 AND is_authenticated = TRUE",
            message.from_user.id
        )

    if user:
        await message.answer(
            "🏠 Вы вернулись в главное меню",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
    else:
        await message.answer(
            "🏠 Вы вернулись в главное меню",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
        )


# Дополнительно: команда для изменения настроек username
@router.message(F.text == "⚙️ Настройки username")
async def username_settings(message: Message, state: FSMContext):
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

    telegram_username = message.from_user.username

    if telegram_username:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Разрешить использование",
                    callback_data="update_allow_username"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Запретить использование",
                    callback_data="update_deny_username"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Обновить username",
                    callback_data="update_username"
                )
            ]
        ])

        current_status = "✅ Разрешено" if user['telegram_real_username'] else "❌ Запрещено"

        settings_text = (
            f"⚙️ Настройки Telegram username:\n\n"
            f"📱 Текущий username: @{telegram_username}\n"
            f"🔒 Статус использования: {current_status}\n\n"
            f"Выберите действие:"
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Как создать username?",
                    callback_data="how_to_create_username"
                )
            ]
        ])

        settings_text = (
            f"⚙️ Настройки Telegram username:\n\n"
            f"❌ У вас не установлен Telegram username.\n\n"
            f"Без username связь при взаимных лайках будет через Telegram ID, "
            f"что менее удобно для других пользователей."
        )

    await message.answer(
        settings_text,
        reply_markup=keyboard
    )


# Обработка обновления настроек username
@router.callback_query(F.data == "update_allow_username")
async def update_allow_username(callback: CallbackQuery):
    telegram_username = callback.from_user.username

    if telegram_username:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET telegram_real_username = $1 WHERE telegram_id = $2",
                telegram_username, callback.from_user.id
            )

        await callback.message.edit_text(
            f"✅ Теперь ваш Telegram username (@{telegram_username}) будет использоваться "
            f"при взаимных лайках.\n\n"
            f"Другие пользователи смогут легко связаться с вами через Telegram."
        )
    else:
        await callback.message.edit_text(
            "❌ У вас не установлен Telegram username.\n\n"
            "Пожалуйста, установите username в настройках Telegram и попробуйте снова."
        )


@router.callback_query(F.data == "update_deny_username")
async def update_deny_username(callback: CallbackQuery):
    async with db.pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET telegram_real_username = NULL WHERE telegram_id = $1",
            callback.from_user.id
        )

    await callback.message.edit_text(
        "❌ Вы запретили использование вашего Telegram username.\n\n"
        "При взаимных лайках связь будет установлена через Telegram ID."
    )


@router.callback_query(F.data == "update_username")
async def update_username(callback: CallbackQuery):
    telegram_username = callback.from_user.username

    if telegram_username:
        async with db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET telegram_real_username = $1 WHERE telegram_id = $2",
                telegram_username, callback.from_user.id
            )

        await callback.message.edit_text(
            f"✅ Ваш Telegram username обновлен: @{telegram_username}\n\n"
            f"Теперь он будет использоваться при взаимных лайках."
        )
    else:
        await callback.message.edit_text(
            "❌ У вас не установлен Telegram username.\n\n"
            "Пожалуйста, установите username в настройках Telegram и попробуйте снова."
        )