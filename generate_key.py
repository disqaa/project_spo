from cryptography.fernet import Fernet
import os

# Генерация ключа шифрования
key = Fernet.generate_key()

# Сохраняем ключ в файл
with open("secret.key", "wb") as key_file:
    key_file.write(key)

print("✅ Ключ шифрования сгенерирован и сохранен в secret.key")
print("⚠️  ВНИМАНИЕ: Не коммитьте этот файл в Git! Добавьте secret.key в .gitignore")