import time
from motion_detector import MotionDetector
from notifications import TelegramNotifier
from config import CONFIG


def main():
    detector = MotionDetector(
        sensitivity=CONFIG.get("SENSITIVITY", 25),
        min_area=CONFIG.get("MIN_AREA", 500),
    )
    notifier = TelegramNotifier(
        token=CONFIG.get("TELEGRAM_TOKEN"),
        chat_id=CONFIG.get("TELEGRAM_CHAT_ID"),
    )

    print("Starting motion detector. Press Ctrl+C to stop.")
    try:
        for event in detector.run():
            print(
                f"Motion detected at {event['timestamp']}, saved {event['frame_path']}"
            )
            if notifier.is_configured():
                notifier.send_photo(
                    event["frame_path"],
                    caption=(f"Motion detected at {event['timestamp']}"),
                )
            else:
                print("Telegram notifier not configured;")
                print("skipping notification.")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping.")


if __name__ == "__main__":
    main()
