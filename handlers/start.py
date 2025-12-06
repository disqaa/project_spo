from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards import get_main_menu_keyboard
from database import db

router = Router()


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
        await message.answer(
            f"👋 С возвращением!\n"
            f"Вы авторизованы как {user['username']}\n\n"
            f"Используйте меню для навигации:",
            reply_markup=get_main_menu_keyboard(is_authenticated=True)
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в бота!\n\n"
            "Для начала работы необходимо:\n"
            "1. Зарегистрироваться - кнопка '🔐 Регистрация'\n"
            "2. Войти в аккаунт - кнопка '🚪 Войти'\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(is_authenticated=False)
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