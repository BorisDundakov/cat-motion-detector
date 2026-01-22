import time
import os
import threading
import signal
import sys
from queue import Queue
from frame_producer import FrameProducer
from motion_detector import MotionDetector
from notifications import TelegramNotifier
from image_analyzer import ImageAnalyzer
from utils import save_frame
from config import CONFIG
from web_server import app, socketio, emit_motion_event
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Global reference to detector for cleanup
detector_instance = None
frame_producer_instance = None


def motion_detection_worker(event_queue):
    """Worker function that runs motion detection in a separate thread."""
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
            # Put the event in the queue for the main thread to process
            event_queue.put(event)
    except Exception as e:
        print(f"Error in motion detection: {e}")


def main():
    global frame_producer_instance

    # Initialize frame producer
    frame_producer = FrameProducer(camera_index=CONFIG.get("CAMERA_INDEX", 0))
    frame_producer.start()
    frame_producer_instance = frame_producer

    # Configure the web app to use this frame producer
    app.config["FRAME_PRODUCER"] = frame_producer

    # Start web server in a separate thread
    web_host = CONFIG.get("WEB_HOST", "0.0.0.0")
    web_port = CONFIG.get("WEB_PORT", 5000)

    def run_web_server():
        print(f"Starting web server at http://{web_host}:{web_port}")
        socketio.run(
            app, host=web_host, port=web_port, debug=False, allow_unsafe_werkzeug=True
        )

    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # wait briefly for first frame to be captured
    time.sleep(0.5)

    detector = MotionDetector(
        frame_producer=frame_producer,
        sensitivity=CONFIG.get("SENSITIVITY", 25),
        min_area=CONFIG.get("MIN_AREA", 500),
        save_frames=False,  # let main decide when to save
    )
    notifier = TelegramNotifier(
        token=CONFIG.get("TELEGRAM_TOKEN"),
        chat_id=CONFIG.get("TELEGRAM_CHAT_ID"),
    )
    analyzer = ImageAnalyzer(
        model_path=CONFIG.get("ANALYZER_MODEL_PATH"),
        config_path=CONFIG.get("ANALYZER_CONFIG_PATH"),
        classes_path=CONFIG.get("ANALYZER_CLASSES_PATH"),
    )
    expected_label = CONFIG.get("TARGET_OBJECTS")

    print("Starting motion detector. Press Ctrl+C to stop.")
    try:
        for event in detector.run():
            logger.info("Received motion event: %s", event.get("timestamp"))
            # Detector yields either a saved path or a raw frame ndarray
            frame = None
            frame_path = event.get("frame_path")
            if frame_path:
                logger.info("Motion detected and saved by detector: %s", frame_path)
                frame = None
            else:
                logger.info(
                    "Motion detected (in-memory frame) at %s", event["timestamp"]
                )
                frame = event.get("frame")

            # DEBUG: Save frame to inspect what camera sees
            if frame is not None:
                debug_dir = "debug_frames"
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(
                    debug_dir, f"debug_{event['timestamp'].replace(':', '-')}.jpg"
                )
                import cv2 as _cv2

                _cv2.imwrite(debug_path, frame)
                logger.info("DEBUG: Saved frame to %s", debug_path)

            # Analyze the frame (pass ndarray or path)
            target = frame if frame is not None else frame_path
            logger.info('Analyzing frame for expected label "%s"', expected_label)
            detections = analyzer.detect_objects(target)
            logger.info("Analyzer returned %d detections", len(detections))

            # Check for expected label
            if detections:
                for d in detections:
                    logger.info(
                        " - detection: label=%s confidence=%.2f box=%s",
                        d.get("label"),
                        d.get("confidence"),
                        d.get("box"),
                    )

            # Split expected labels (comma-separated)
            expected_labels = [label.strip() for label in expected_label.split(",")]

            # compute best non-matching confidence
            non_matching = [
                d for d in detections if d.get("label") not in expected_labels
            ]
            best_non_match_conf = max(
                (d.get("confidence", 0.0) for d in non_matching), default=0.0
            )
            logger.info("Best non-matching confidence=%.2f", best_non_match_conf)
            matches = [d for d in detections if d.get("label") in expected_labels]
            if matches:
                # If detector didn't save the frame, save it now
                logger.info(
                    'Expected label "%s" matched (%d). Saving/sending.',
                    expected_label,
                    len(matches),
                )
                if frame is not None:
                    save_dir = CONFIG.get("FRAME_DIR", "frames")
                    os.makedirs(save_dir, exist_ok=True)
                    filename = f"motion_{event['timestamp'].replace(':', '-')}.jpg"
                    saved_path = os.path.join(save_dir, filename)
                    # write image
                    import cv2 as _cv2

                    _cv2.imwrite(saved_path, frame)
                    frame_path_to_send = saved_path
                else:
                    frame_path_to_send = frame_path

                caption = f"{expected_label} detected at {event['timestamp']}: {len(matches)} match(es)"
                if notifier.is_configured():
                    notifier.send_photo(frame_path_to_send, caption=caption)
                else:
                    logger.info(
                        "Telegram notifier not configured; skipping notification."
                    )

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
            # Cleanup: stop the motion detector and frame producer
            print("Cleaning up resources...")
            if detector_instance:
                detector_instance.running = False
            if frame_producer_instance:
                frame_producer_instance.stop()

            # Give threads time to cleanup
            print("Shutdown complete.")
        except Exception:
            pass


if __name__ == "__main__":
    main()
