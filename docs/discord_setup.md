# Discord webhook setup — Motion Detector Project

Create a webhook in Discord, copy the URL, and place it in the project config.

---

## 1. Create a Discord webhook
1. Open Discord and select the server where you want notifications.
2. Choose the text channel for notifications.
3. Channel name → Integrations → Webhooks.
4. Create a new webhook, give it a name (e.g. `MotionDetector`) and pick the channel.
5. Click **Copy Webhook URL** and save it somewhere secure on your machine.

---

## 2. Configure the project to use the webhook
Update the `DISCORD_WEBHOOK_URL` entry in the `CONFIG` dictionary inside `config.py`.

Example:
```python
# config.py
CONFIG = {
    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/....",  # <- paste your webhook URL here
    # ... other config entries ...
}
```

That's it — the application will read the webhook URL from `CONFIG["DISCORD_WEBHOOK_URL"]`.