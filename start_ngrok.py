import subprocess
import time
import requests
import sys


def start_ngrok_tunnel(port=8000):
    print("🚀 Запуск ngrok туннеля...")

    try:
        # Запускаем ngrok
        process = subprocess.Popen(
            ['ngrok', 'http', str(port), '--region=eu'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("⏳ Ожидание запуска ngrok (10 секунд)...")
        time.sleep(10)

        # Получаем информацию о туннелях через API ngrok
        try:
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])

                if tunnels:
                    for tunnel in tunnels:
                        if tunnel['proto'] == 'https':
                            public_url = tunnel['public_url']
                            print(f"✅ Ngrok запущен!")
                            print(f"🔗 Публичный URL: {public_url}")
                            print(f"📱 Mini App URL: {public_url}/mini")

                            # Записываем URL в файл
                            with open('ngrok_url.txt', 'w') as f:
                                f.write(f"Public URL: {public_url}\n")
                                f.write(f"Mini App URL: {public_url}/mini\n")

                            return public_url
        except:
            print("⚠️  Не удалось получить информацию о туннеле через API")
            print("⚠️  Проверьте, что ngrok запущен: ngrok http 8000 --region=eu")

        print("⚠️  Ngrok процесс запущен, но не удалось получить URL")
        return None

    except FileNotFoundError:
        print("❌ Ngrok не установлен!")
        print("📥 Установите ngrok:")
        print("   1. Скачайте с https://ngrok.com/download")
        print("   2. Распакуйте и добавьте в PATH")
        print("   3. Или используйте: npm install -g ngrok")
        return None
    except Exception as e:
        print(f"❌ Ошибка запуска ngrok: {e}")
        return None


if __name__ == "__main__":
    url = start_ngrok_tunnel(8000)
    if url:
        print("\n🎯 Используйте этот URL в настройках бота:")
        print(f"   {url}/mini")
        print("\n🔄 Чтобы обновить конфигурацию, измените .env файл:")
        print(f"   MINI_APP_URL={url}")
        print("\n⏸️  Нажмите Ctrl+C для остановки ngrok")

        try:
            # Держим процесс открытым
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Ngrok остановлен")
    else:
        sys.exit(1)