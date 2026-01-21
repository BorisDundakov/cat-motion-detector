import time
import os
from frame_producer import FrameProducer
from motion_detector import MotionDetector
from notifications import TelegramNotifier
from image_analyzer import ImageAnalyzer
from utils import save_frame
from config import CONFIG
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    # Initialize frame producer
    frame_producer = FrameProducer(camera_index=CONFIG.get("CAMERA_INDEX", 0))
    frame_producer.start()
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
    expected_label = CONFIG.get("EXPECTED_LABEL", "cat")

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
            # compute best non-matching confidence
            non_matching = [d for d in detections if d.get("label") != expected_label]
            best_non_match_conf = max(
                (d.get("confidence", 0.0) for d in non_matching), default=0.0
            )
            logger.info("Best non-matching confidence=%.2f", best_non_match_conf)
            matches = [d for d in detections if d.get("label") == expected_label]
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
            else:
                logger.info("No expected object detected; not saving or notifying.")

            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping.")
    finally:
        try:
            frame_producer.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
