import time
from frame_producer import FrameProducer
from motion_detector import MotionDetector
from notifications import TelegramNotifier
from config import CONFIG


def main():
    # Initialize frame producer
    frame_producer = FrameProducer(camera_index=0)
    frame_producer.start()
    
    # Wait briefly for first frame to be captured
    time.sleep(0.5)
    
    detector = MotionDetector(
        frame_producer=frame_producer,
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
    finally:
        frame_producer.stop()


if __name__ == "__main__":
    main()
