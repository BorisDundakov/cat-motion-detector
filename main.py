import time
import os
import threading
import logging
from frame_producer import FrameProducer
from motion_detector import MotionDetector
from notifications import DiscordNotifier
from image_analyzer import ImageAnalyzer
from utils import save_frame
from config import CONFIG
from web_server import app, socketio, emit_motion_event

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Global references for cleanup
detector_instance = None
frame_producer_instance = None


def format_motion_message(timestamp: str) -> str:
    """Format timestamp nicely for notifications (Discord style)."""
    # timestamp is expected in ISO format (e.g. "2026-01-22T13:45:30.123456")
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
        save_frames=False,  # detector will yield in-memory frame unless configured to save
    )

    # Initialize Discord notifier from CONFIG / environment
    discord_notifier = DiscordNotifier(webhook_url=CONFIG.get("DISCORD_WEBHOOK_URL"))

    if discord_notifier.is_configured():
        notifier = discord_notifier
        logger.info("📢 Using Discord notifications")
    else:
        notifier = None
        logger.warning("⚠️  No notifier configured. Set DISCORD_WEBHOOK_URL in the environment or CONFIG.")

    # Initialize analyzer (kept for optional post-processing / web UI)
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

            # Decide which image to send. Requirement: send only files named starting with "motion_".
            frame_path_to_send = None

            # If detector provided a saved frame path, ensure it starts with "motion_"
            event_frame_path = event.get("frame_path")
            if event_frame_path:
                if os.path.basename(event_frame_path).startswith("motion_"):
                    frame_path_to_send = event_frame_path
                    logger.info("Using detector-saved motion image for notification: %s", frame_path_to_send)
                else:
                    logger.info("Detector-saved image does not start with 'motion_'; skipping send for that file: %s", event_frame_path)

            # If detector provided an in-memory frame, save it with a "motion_" prefix so it will be eligible
            if frame_path_to_send is None and event.get("frame") is not None:
                frame = event.get("frame")
                save_dir = CONFIG.get("FRAME_DIR", "frames")
                os.makedirs(save_dir, exist_ok=True)
                filename = f"motion_{event['timestamp'].replace(':', '-')}.jpg"
                saved_path = os.path.join(save_dir, filename)
                import cv2 as _cv2

                try:
                    _cv2.imwrite(saved_path, frame)
                    frame_path_to_send = saved_path
                    logger.info("Saved in-memory frame as motion image for notification: %s", saved_path)
                except Exception as e:
                    logger.exception("Failed to save in-memory frame for notification: %s", e)
                    frame_path_to_send = None

            # Build caption including timestamp (user requested previous style)
            caption = format_motion_message(event["timestamp"])

            # Send notification only if we have a "motion_" image to attach. Do NOT send text-only messages.
            if notifier and notifier.is_configured() and frame_path_to_send:
                try:
                    notifier.send_photo(frame_path_to_send, caption=caption)
                    logger.info("Sent Discord notification with image: %s", frame_path_to_send)
                except Exception:
                    logger.exception("Failed to send Discord notification")
            else:
                if not frame_path_to_send:
                    logger.info("No 'motion_' image available for this motion event; skipping Discord notification.")
                elif not (notifier and notifier.is_configured()):
                    logger.info("Notifier not configured; skipping notification for this motion event.")

            # Continue with analyzer as before (optional): analyze and emit to web UI if expected objects are found
            target = event.get("frame") if event.get("frame") is not None else event_frame_path
            if target is not None:
                logger.info('Analyzing frame for expected label "%s"', expected_label)
                try:
                    detections = analyzer.detect_objects(target)
                except Exception as e:
                    logger.exception("Analyzer failed: %s", e)
                    detections = []
                logger.info("Analyzer returned %d detections", len(detections))

                expected_labels = [label.strip() for label in expected_label.split(",")]
                matches = [d for d in detections if d.get("label") in expected_labels]

                if matches:
                    # Emit to web interface using the detector-saved motion file if available, else event frame_path
                    frame_path_for_web = frame_path_to_send or event_frame_path
                    web_event = {
                        "timestamp": event["timestamp"],
                        "frame_path": frame_path_for_web,
                    }
                    emit_motion_event(web_event)
                else:
                    logger.info("No expected object detected in this motion event.")
            else:
                logger.debug("No frame available for analysis on this event.")

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