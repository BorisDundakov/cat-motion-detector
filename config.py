import os

CONFIG = {
    "TELEGRAM_TOKEN": os.environ.get("TELEGRAM_TOKEN"),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID"),
    "SENSITIVITY": int(os.environ.get("SENSITIVITY", "25")),
    "MIN_AREA": int(os.environ.get("MIN_AREA", "500")),
    "FRAME_DIR": os.environ.get("FRAME_DIR", "frames"),
}
