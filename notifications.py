import os
import requests


class TelegramNotifier:
    def __init__(self, token=None, chat_id=None):
        self.token = token or os.environ.get("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        if self.token:
            self.api_url = f"https://api.telegram.org/bot{self.token}"
        else:
            self.api_url = None

    def is_configured(self):
        return bool(self.token and self.chat_id)

    def send_photo(self, photo_path, caption=None):
        if not self.is_configured():
            raise RuntimeError("Telegram notifier not configured")

        url = f"{self.api_url}/sendPhoto"
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": self.chat_id, "caption": caption or ""}
            r = requests.post(url, data=data, files=files, timeout=10)
        r.raise_for_status()
        return r.json()
