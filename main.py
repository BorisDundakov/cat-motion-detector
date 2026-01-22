import time
import os
import threading
import signal
import sys
from queue import Queue
from frame_producer import FrameProducer
from motion_detector import MotionDetector
from notifications import TelegramNotifier, DiscordNotifier
from image_analyzer import ImageAnalyzer
from utils import save_frame
from config import CONFIG
from web_server import app, socketio, emit_motion_event
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Global references for cleanup
detector_instance = None
frame_producer_instance = None

def format_motion_message(timestamp: str) -> str:
    """Format timestamp nicely for notifications (Discord style)."""
    date, time_part = timestamp.split("T", 1)
    return (
        "🚨 **Motion detected!**\n"
        f"📅 **Date:** `{date}`\n"
        f"🕒 **Time:** `{time_part}`"
    )

def motion_detection_worker(event_queue):
    """Background thread for motion detection (currently unused, optional)."""
    global detector_instance, frame_producer_instance

    detector = MotionDetector(
        frame_producer=frame_producer_instance,
        sensitivity=CONFIG.get("SENSITIVITY", 25),
        min_area=CONFIG.get("MIN_AREA", 500),
    )
    detector_instance = detector

    print("Motion detector started in background thread")

    try:
        for event in detector.run():
            event_queue.put(event)
    except Exception as e:
        print(f"Error in motion detection: {e}")

def main():
    global frame_producer_instance

    # Initialize frame producer
    frame_producer = FrameProducer(camera_index=CONFIG.get("CAMERA_INDEX", 0))
    frame_producer.start()
    frame_producer_instance = frame_producer

    # Configure web app
    app.config["FRAME_PRODUCER"] = frame_producer

    # Start web server thread
    web_host = CONFIG.get("WEB_HOST", "0.0.0.0")
    web_port = CONFIG.get("WEB_PORT", 5000)
    def run_web_server():
        print(f"Starting web server at http://{web_host}:{web_port}")
        socketio.run(
            app, host=web_host, port=web_port, debug=False, allow_unsafe_werkzeug=True
        )
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Wait briefly for first frame
    time.sleep(0.5)

    # Initialize detector
    detector = MotionDetector(
        frame_producer=frame_producer,
        sensitivity=CONFIG.get("SENSITIVITY", 25),
        min_area=CONFIG.get("MIN_AREA", 500),
        save_frames=False,  # save manually after analysis
    )

    # Initialize notifiers
    telegram_notifier = TelegramNotifier(
        token=CONFIG.get("TELEGRAM_TOKEN"),
        chat_id=CONFIG.get("TELEGRAM_CHAT_ID"),
    )
    discord_notifier = DiscordNotifier(
        webhook_url="https://discord.com/api/webhooks/1463507497233944719/MwLFA_v4OHCmhsga_fUrm57XiKx3UexwQwZftRlqIK8ZFDqHROYv9y265StRrtB5Si05"
        )

    # Choose notifier: Discord preferred, fallback to Telegram
    if discord_notifier.is_configured():
        notifier = discord_notifier
        logger.info("📢 Using Discord notifications")
    elif telegram_notifier.is_configured():
        notifier = telegram_notifier
        logger.info("📢 Using Telegram notifications")
    else:
        notifier = None
        logger.warning("⚠️  No notifier configured")

    # Initialize analyzer
    analyzer = ImageAnalyzer(
        model_path=CONFIG.get("ANALYZER_MODEL_PATH"),
        config_path=CONFIG.get("ANALYZER_CONFIG_PATH"),
        classes_path=CONFIG.get("ANALYZER_CLASSES_PATH"),
    )
    expected_label = CONFIG.get("TARGET_OBJECTS", "")

    print("Starting motion detector. Press Ctrl+C to stop.")

    try:
        for event in detector.run():
            logger.info("Received motion event: %s", event.get("timestamp"))
            frame = None
            frame_path = event.get("frame_path")
            if frame_path:
                logger.info("Motion detected and saved by detector: %s", frame_path)
            else:
                frame = event.get("frame")
                logger.info("Motion detected (in-memory frame) at %s", event["timestamp"])

            # DEBUG: Save frame for inspection
            if frame is not None:
                debug_dir = "debug_frames"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(
                    debug_dir, f"debug_{event['timestamp'].replace(':', '-')}.jpg"
                )
                import cv2 as _cv2
                _cv2.imwrite(debug_path, frame)
                logger.info("DEBUG: Saved frame to %s", debug_path)

            # Analyze the frame
            target = frame if frame is not None else frame_path
            logger.info('Analyzing frame for expected label "%s"', expected_label)
            detections = analyzer.detect_objects(target)
            logger.info("Analyzer returned %d detections", len(detections))

            # Split expected labels
            expected_labels = [label.strip() for label in expected_label.split(",")]

            # Compute best non-matching confidence
            non_matching = [d for d in detections if d.get("label") not in expected_labels]
            best_non_match_conf = max((d.get("confidence", 0.0) for d in non_matching), default=0.0)
            logger.info("Best non-matching confidence=%.2f", best_non_match_conf)

            matches = [d for d in detections if d.get("label") in expected_labels]
            if matches:
                # Save frame if needed
                if frame is not None:
                    save_dir = CONFIG.get("FRAME_DIR", "frames")
                    os.makedirs(save_dir, exist_ok=True)
                    filename = f"motion_{event['timestamp'].replace(':', '-')}.jpg"
                    saved_path = os.path.join(save_dir, filename)
                    import cv2 as _cv2
                    _cv2.imwrite(saved_path, frame)
                    frame_path_to_send = saved_path
                else:
                    frame_path_to_send = frame_path

                # Notification caption
                if isinstance(notifier, DiscordNotifier):
                    caption = format_motion_message(event["timestamp"])
                else:
                    caption = f"{expected_label} detected at {event['timestamp']}: {len(matches)} match(es)"

                # Send notification
                if notifier and notifier.is_configured():
                    notifier.send_photo(frame_path_to_send, caption=caption)
                else:
                    logger.info("Notifier not configured; skipping notification.")

                # Emit event to web interface
                web_event = {
                    "timestamp": event["timestamp"],
                    "frame_path": frame_path_to_send,
                }
                emit_motion_event(web_event)
            else:
                logger.info("No expected object detected; not saving or notifying.")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        try:
            print("Cleaning up resources...")
            if detector_instance:
                detector_instance.running = False
            if frame_producer_instance:
                frame_producer_instance.stop()
            print("Shutdown complete.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
