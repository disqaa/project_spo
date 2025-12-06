from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# Главное меню
def get_main_menu_keyboard(is_authenticated: bool = False):
    builder = ReplyKeyboardBuilder()

    if not is_authenticated:
        builder.add(KeyboardButton(text="🔐 Регистрация"))
        builder.add(KeyboardButton(text="🚪 Войти"))
    else:
        builder.add(KeyboardButton(text="👤 Профиль"))
        builder.add(KeyboardButton(text="🔍 Начать поиск"))
        builder.add(KeyboardButton(text="⚙️ Фильтры поиска"))
        builder.add(KeyboardButton(text="🤝 Мои встречи"))
        builder.add(KeyboardButton(text="📊 Статистика"))
        builder.add(KeyboardButton(text="🚪 Выйти"))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Клавиатура для отмены действий
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


# Инлайн кнопки для подтверждения
def get_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"))
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel"))
    return builder.as_markup()


# Кнопка пропуска (для опциональных полей)
def get_skip_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏩ Пропустить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )


# Клавиатура для возврата в меню
def get_back_to_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
        resize_keyboard=True
    )


# Клавиатура для профиля
def get_profile_keyboard(is_published: bool = False):
    builder = ReplyKeyboardBuilder()

    if is_published:
        builder.add(KeyboardButton(text="🔒 Снять с публикации"))
    else:
        builder.add(KeyboardButton(text="📢 Опубликовать анкету"))

    builder.add(KeyboardButton(text="✏️ Редактировать профиль"))
    builder.add(KeyboardButton(text="🎯 Изменить активность"))
    builder.add(KeyboardButton(text="🔍 Начать поиск"))
    builder.add(KeyboardButton(text="⚙️ Фильтры поиска"))
    builder.add(KeyboardButton(text="🤝 Мои встречи"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))

    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Инлайн кнопки для поиска
def get_search_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❤️ Лайк", callback_data="like"))
    builder.add(InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip"))
    builder.add(InlineKeyboardButton(text="🚪 Выйти из поиска", callback_data="stop_search"))
    return builder.as_markup()


# Инлайн кнопки для сохранения фильтра
def get_save_filter_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💾 Сохранить фильтр", callback_data="save_filter"))
    builder.add(InlineKeyboardButton(text="🔍 Поиск", callback_data="search_with_filter"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_filter"))
    return builder.as_markup()


# Инлайн кнопки для подтверждения встречи
def get_meeting_confirmation_keyboard(match_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Согласен на встречу", callback_data=f"accept_meeting_{match_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_meeting_{match_id}"))
    return builder.as_markup()


# Инлайн кнопки для встреч
def get_meeting_details_keyboard(match_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📞 Написать", callback_data=f"message_{match_id}"))
    builder.add(InlineKeyboardButton(text="❌ Отменить встречу", callback_data=f"cancel_meeting_{match_id}"))
    return builder.as_markup()


# Клавиатура для редактирования профиля
def get_edit_profile_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📝 Изменить интересы"))
    builder.add(KeyboardButton(text="📝 Изменить 'О себе'"))
    builder.add(KeyboardButton(text="📷 Изменить фото"))
    builder.add(KeyboardButton(text="🎯 Изменить активность"))
    builder.add(KeyboardButton(text="↩️ Назад в профиль"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Клавиатура для выбора интереса активности
def get_activity_interests_keyboard():
    interests = ["🏃 Спорт", "🎬 Кино", "☕ Кафе/Бар", "🎮 Настольные игры"]
    builder = ReplyKeyboardBuilder()
    for interest in interests:
        builder.add(KeyboardButton(text=interest))
    builder.add(KeyboardButton(text="❌ Отмена"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Клавиатура для выбора времени активности
def get_activity_time_keyboard():
    times = [
        "👋 Сегодня",
        "📅 Завтра",
        "🗓️ В ближайшие дни",
        "🌆 Вечером",
        "🌅 Утром",
        "🌞 В выходные",
        "⏰ Любое время"
    ]
    builder = ReplyKeyboardBuilder()
    for time in times:
        builder.add(KeyboardButton(text=time))
    builder.add(KeyboardButton(text="❌ Отмена"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


# Клавиатура для фильтров поиска
def get_search_filters_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎯 По интересу"))
    builder.add(KeyboardButton(text="📍 По месту"))
    builder.add(KeyboardButton(text="⏰ По времени"))
    builder.add(KeyboardButton(text="🧹 Сбросить фильтры"))
    builder.add(KeyboardButton(text="🔍 Поиск с фильтрами"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.add(KeyboardButton(text="⚙️ Настройки username"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)




# Клавиатура для предстоящих встреч (отправленные запросы)
def get_upcoming_meetings_keyboard(match_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отменить запрос", callback_data=f"cancel_meeting_{match_id}"))
    return builder.as_markup()

# Обновленная клавиатура для встреч
def get_meetings_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📝 Запросы на встречу"))  # Полученные запросы
    builder.add(KeyboardButton(text="📅 Предстоящие встречи"))  # Отправленные запросы
    builder.add(KeyboardButton(text="✅ Подтвержденные встречи"))
    builder.add(KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)