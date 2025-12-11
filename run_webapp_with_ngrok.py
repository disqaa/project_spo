# run_webapp_with_ngrok.py

import os
import sys
import time
from pyngrok import ngrok, conf
from web_app_sync import app
import threading
import webbrowser


def get_ngrok_auth_token():
    """Получить токен ngrok"""
    # Можно установить через переменную окружения
    token = os.getenv('NGROK_AUTH_TOKEN')
    if not token:
        print("⚠️  NGROK_AUTH_TOKEN не установлен")
        print("📝 Получите токен на https://dashboard.ngrok.com/get-started/your-authtoken")
        token = input("Введите ваш ngrok auth token: ").strip()
        if token:
            os.environ['NGROK_AUTH_TOKEN'] = token
    return token


def start_ngrok_tunnel(port=5000):
    """Запустить ngrok туннель"""
    try:
        # Настраиваем ngrok
        auth_token = get_ngrok_auth_token()
        if auth_token:
            ngrok.set_auth_token(auth_token)

        # Открываем туннель
        tunnel = ngrok.connect(port, bind_tls=True)
        public_url = tunnel.public_url

        print(f"\n{'=' * 60}")
        print("🌐 NGROK ТУННЕЛЬ АКТИВИРОВАН!")
        print(f"{'=' * 60}")
        print(f"📱 WebApp URL: {public_url}/webapp")
        print(f"🗺️  Карта: {public_url}/map")
        print(f"{'=' * 60}")

        # Сохраняем URL для бота
        with open('webapp_url.txt', 'w') as f:
            f.write(f"{public_url}/webapp")

        return public_url

    except Exception as e:
        print(f"❌ Ошибка ngrok: {e}")
        return None


def update_bot_webapp_url(url):
    """Обновить URL WebApp в коде бота"""
    try:
        # Обновляем handlers/map.py
        with open('handlers/map.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # Заменяем URL WebApp
        new_content = content.replace(
            'web_app=WebAppInfo(url="https://ваш-домен.ngrok.io/webapp")',
            f'web_app=WebAppInfo(url="{url}")'
        )

        with open('handlers/map.py', 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✅ URL WebApp обновлен в боте: {url}")

    except Exception as e:
        print(f"⚠️  Не удалось обновить URL в боте: {e}")


def start_flask_server(port=5000):
    """Запустить Flask сервер"""
    print(f"🚀 Запуск Flask сервера на порту {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


def main():
    """Основная функция"""
    print("🚀 ЗАПУСК WEBAPP ДЛЯ TELEGRAM")
    print("=" * 60)

    # Запускаем ngrok
    print("\n1. Запуск ngrok туннеля...")
    public_url = start_ngrok_tunnel(5000)

    if not public_url:
        print("❌ Не удалось запустить ngrok. Завершение работы.")
        sys.exit(1)

    # Обновляем URL в боте
    print("\n2. Обновление URL в коде бота...")
    webapp_url = f"{public_url}/webapp"
    update_bot_webapp_url(webapp_url)

    # Инструкция для BotFather
    print("\n3. Инструкция для BotFather:")
    print("=" * 60)
    print(f"📋 URL для BotFather: {public_url}/webapp")
    print("=" * 60)
    print("\n📝 Действия:")
    print("1. Откройте @BotFather в Telegram")
    print("2. Отправьте команду /mybots")
    print("3. Выберите вашего бота")
    print("4. Выберите 'Bot Settings' -> 'Web App'")
    print(f"5. Вставьте URL: {public_url}/webapp")
    print("6. Сохраните изменения")
    print("=" * 60)

    # Запускаем Flask сервер
    print("\n4. Запуск Flask сервера...")
    print("   Сервер запущен. Нажмите Ctrl+C для остановки.")

    try:
        start_flask_server(5000)
    except KeyboardInterrupt:
        print("\n\n🛑 Остановка сервера...")
        ngrok.kill()
        print("✅ Сервер остановлен")


if __name__ == '__main__':
    main()