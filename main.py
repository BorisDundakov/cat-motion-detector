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

    print("Starting motion detector. Press Ctrl+C to stop.")
    try:
        for event in detector.run():
            # Reload target objects from CONFIG each iteration (allows dynamic updates)
            target_objects_str = CONFIG.get("TARGET_OBJECTS", "cat")
            target_objects = [obj.strip() for obj in target_objects_str.split(",")]

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

            # Analyze the frame (pass ndarray or path directly to ImageAnalyzer)
            target = frame if frame is not None else frame_path
            logger.info(
                "Analyzing frame for target objects: %s", ", ".join(target_objects)
            )
            detections = analyzer.detect_objects(target)
            logger.info("Analyzer returned %d detections", len(detections))

            # Check for any target objects
            if detections:
                for d in detections:
                    logger.info(
                        " - detection: label=%s confidence=%.2f box=%s",
                        d.get("label"),
                        d.get("confidence"),
                        d.get("box"),
                    )

            # Find matches - any detected object that's in our target list
            matches = [d for d in detections if d.get("label") in target_objects]

            if matches:
                matched_labels = list(set([d.get("label") for d in matches]))
                logger.info(
                    "Target objects detected: %s (%d detections). Saving image with detections.",
                    ", ".join(matched_labels),
                    len(matches),
                )

                # Use ImageAnalyzer to save the image with bounding boxes to frames directory
                success, saved_path, num_detected = (
                    analyzer.show_and_save_identified_image(
                        target,
                        notification_dir=CONFIG.get("FRAME_DIR", "frames"),
                        show_image=False,
                    )
                )

                if success and saved_path:
                    # Send the annotated image from frames folder
                    caption = f"{', '.join(matched_labels)} detected at {event['timestamp']}: {num_detected} object(s)"
                    if notifier.is_configured():
                        notifier.send_photo(saved_path, caption=caption)
                    else:
                        logger.info(
                            "Telegram notifier not configured; skipping notification."
                        )

                    # Emit event to web interface
                    web_event = {
                        "timestamp": event["timestamp"],
                        "frame_path": saved_path,
                    }
                    emit_motion_event(web_event)
                else:
                    logger.error("Failed to save detected image")
            else:
                detected_labels = (
                    list(set([d.get("label") for d in detections]))
                    if detections
                    else []
                )
                if detected_labels:
                    logger.info(
                        "Motion detected but no target objects found. Detected: %s (looking for: %s)",
                        ", ".join(detected_labels),
                        ", ".join(target_objects),
                    )
                else:
                    logger.info(
                        "Motion detected but no objects recognized by YOLO (looking for: %s)",
                        ", ".join(target_objects),
                    )

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