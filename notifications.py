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
        """Check if Telegram notifier has the required configuration."""
        return bool(self.token and self.chat_id)

    def send_photo(self, photo_path, caption=None):
        """Send a photo to the configured Telegram chat."""
        if not self.is_configured():
            raise RuntimeError("Telegram notifier not configured")

        url = f"{self.api_url}/sendPhoto"
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": self.chat_id, "caption": caption or ""}
            r = requests.post(url, data=data, files=files, timeout=10)
        r.raise_for_status()
        return r.json()


class DiscordNotifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = "https://discord.com/api/webhooks/1463507497233944719/MwLFA_v4OHCmhsga_fUrm57XiKx3UexwQwZftRlqIK8ZFDqHROYv9y265StRrtB5Si05"

    def is_configured(self):
        """Check if Discord webhook URL is configured."""
        return bool(self.webhook_url)

    def send_photo(self, photo_path, caption=None):
        """Send a photo to the configured Discord webhook."""
        if not self.is_configured():
            raise RuntimeError("Discord notifier not configured")

        with open(photo_path, "rb") as f:
            files = {"file": (os.path.basename(photo_path), f, "image/jpeg")}
            data = {"content": caption} if caption else {}
            r = requests.post(self.webhook_url, data=data, files=files, timeout=10)
        r.raise_for_status()
        return r.json() if r.content else {}
