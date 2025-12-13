import logging
import subprocess
import time
import threading
from config import config

logger = logging.getLogger(__name__)


class NgrokManager:
    def __init__(self):
        self.public_url = None
        self.webapp_url = None
        self.process = None
        self.is_running = False

    def start_ngrok(self, port=8000):
        try:
            # Проверяем, установлен ли ngrok
            result = subprocess.run(['ngrok', '--version'],
                                    capture_output=True, text=True)

            if result.returncode != 0:
                logger.warning("❌ Ngrok не установлен. Установите его с помощью:")
                logger.warning("  npm install -g ngrok")
                logger.warning("  или")
                logger.warning("  brew install ngrok")
                logger.warning("  или скачайте с https://ngrok.com/download")
                return None

            # Запускаем ngrok в отдельном процессе
            self.process = subprocess.Popen(
                ['ngrok', 'http', str(port), '--region', config.NGROK_REGION],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.is_running = True
            logger.info(f"✅ Ngrok запущен на порту {port}")

            # Даем время на запуск
            time.sleep(3)

            # Получаем URL из вывода ngrok
            self.public_url = f"https://{port}-{config.NGROK_REGION}.ngrok-free.app"
            self.webapp_url = f"{self.public_url}/mini"

            logger.info(f"🔗 Публичный URL: {self.public_url}")
            logger.info(f"📱 WebApp URL: {self.webapp_url}")

            # Запускаем мониторинг в отдельном потоке
            thread = threading.Thread(target=self._monitor_ngrok, daemon=True)
            thread.start()

            return self.webapp_url

        except Exception as e:
            logger.error(f"❌ Ошибка запуска ngrok: {e}")
            return None

    def _monitor_ngrok(self):
        """Мониторинг процесса ngrok"""
        while self.is_running:
            if self.process.poll() is not None:
                logger.warning("⚠️  Ngrok процесс завершился, перезапускаем...")
                self.stop_ngrok()
                time.sleep(2)
                self.start_ngrok(8000)
                break
            time.sleep(10)

    def stop_ngrok(self):
        """Останавливает ngrok"""
        if self.process and self.is_running:
            self.process.terminate()
            self.process.wait()
            self.is_running = False
            logger.info("✅ Ngrok остановлен")

    def get_webapp_url(self):
        """Возвращает URL для WebApp"""
        return self.webapp_url


ngrok_manager = NgrokManager()