"""
tunnel_handler.py — туннель через Cloudflare (trycloudflare.com).

Не требует аккаунта и работает в России.
Нужен только файл cloudflared.exe в папке проекта (или в PATH).

Скачать: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
Переименовать в cloudflared.exe и положить рядом с main.py.
"""

import subprocess
import threading
import re
import logging
import os

logger = logging.getLogger(__name__)


def _find_cloudflared():
    """Ищет cloudflared в папке проекта и в PATH."""
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")
    if os.path.exists(local):
        return local

    local_unix = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared")
    if os.path.exists(local_unix):
        return local_unix

    import shutil
    return shutil.which("cloudflared")


class TunnelManager:
    def __init__(self):
        self.public_url = None
        self.webapp_url = None
        self.process = None
        self.is_running = False
        self._url_event = threading.Event()

    def start_tunnel(self, port=8000):
        cloudflared = _find_cloudflared()

        if not cloudflared:
            logger.error(
                "❌ cloudflared не найден!\n"
                "   Скачай: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe\n"
                "   Переименуй в cloudflared.exe и положи в папку проекта."
            )
            return None

        logger.info(f"🔗 Запуск Cloudflare-туннеля на порту {port}...")

        try:
            self.process = subprocess.Popen(
                [cloudflared, "tunnel", "--url", f"http://localhost:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.is_running = True

            reader = threading.Thread(target=self._read_output, daemon=True)
            reader.start()

            # Ждём URL до 40 секунд
            if self._url_event.wait(timeout=40):
                logger.info(f"✅ Туннель запущен!")
                logger.info(f"🌐 Публичный URL: {self.public_url}")
                logger.info(f"📱 WebApp URL:    {self.webapp_url}")
                return self.webapp_url
            else:
                logger.error("❌ Туннель не дал URL за 40 секунд")
                self.stop_tunnel()
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка запуска туннеля: {e}")
            return None

    def _read_output(self):
        try:
            for line in self.process.stdout:
                line = line.strip()
                if not line:
                    continue
                logger.debug(f"[tunnel] {line}")

                match = re.search(r"https://[\w-]+\.trycloudflare\.com", line)
                if match and not self._url_event.is_set():
                    self.public_url = match.group(0)
                    self.webapp_url = f"{self.public_url}/mini"
                    self._url_event.set()

        except Exception as e:
            logger.error(f"[tunnel] Ошибка чтения: {e}")

        if self.is_running:
            logger.warning("⚠️ Туннель неожиданно закрылся.")
            self.is_running = False

    def stop_tunnel(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                pass
            self.is_running = False
            logger.info("✅ Туннель остановлен.")

    def get_webapp_url(self):
        return self.webapp_url

    def get_public_url(self):
        return self.public_url


tunnel_manager = TunnelManager()