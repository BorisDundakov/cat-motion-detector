import os
import requests


class DiscordNotifier:
    """
    Simple Discord notifier that posts an image to a webhook URL.
    The webhook URL is taken from the constructor parameter or the DISCORD_WEBHOOK_URL environment variable.
    """

    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")

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