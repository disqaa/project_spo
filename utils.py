import hashlib
import secrets
import string
from datetime import datetime
import aiofiles
import os
from config import config


# Генерация хеша пароля
def hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(32)

    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000,
        dklen=64
    )

    return salt, hash_obj.hex()


# Проверка пароля
def verify_password(password: str, salt: str, hashed_password: str) -> bool:
    try:
        _, new_hash = hash_password(password, salt)
        return secrets.compare_digest(new_hash, hashed_password)
    except Exception:
        return False


# Сохранение фото
async def save_photo(photo_data: bytes, user_id: int) -> str:
    filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(config.PROFILE_PHOTOS_DIR, filename)

    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(photo_data)

    return filepath


# Проверка возраста
def is_valid_age(age: str) -> tuple[bool, int]:
    try:
        age_int = int(age)
        if 1 <= age_int <= 120:
            return True, age_int
        return False, 0
    except ValueError:
        return False, 0


# Валидация username
def is_valid_username(username: str) -> bool:
    if len(username) < 3 or len(username) > 20:
        return False
    return all(c.isalnum() or c in ('_', '.') for c in username)


# Валидация пароля
def is_valid_password(password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Пароль должен содержать минимум 6 символов"
    return True, ""


# Шифрование данных (упрощенная версия - пока не используем)
def encrypt_data(data: str) -> str:
    return data  # Временно отключаем шифрование


# Дешифрование данных
def decrypt_data(encrypted_data: str) -> str:
    return encrypted_data  # Временно отключаем шифрование