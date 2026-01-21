import time
import cv2
import os
import datetime
import logging
from utils import ensure_dir, save_frame

logger = logging.getLogger(__name__)


class MotionDetector:
    """Motion detector that consumes frames from a FrameProducer or camera."""

    def __init__(
        self,
        frame_producer=None,
        sensitivity=15,
        min_area=500,
        camera_index=None,
        min_motion_frames=2,
        cooldown_seconds=2,
        save_frames=True,
    ):
        self.frame_producer = frame_producer
        self.camera_index = camera_index
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.frame_dir = os.environ.get("FRAME_DIR", "frames")
        self.running = False
        ensure_dir(self.frame_dir)
        self.min_motion_frames = min_motion_frames
        self.cooldown_seconds = cooldown_seconds
        self.save_frames = save_frames

    def run(self):
        """Generator that yields motion events."""
        if self.frame_producer is not None:
            yield from self._run_from_producer()
        elif self.camera_index is not None:
            yield from self._run_from_camera()
        else:
            raise ValueError("Either frame_producer or camera_index must be provided")

    def _run_from_producer(self):
        """Run motion detection from frame producer."""
        avg = None
        motion_counter = 0
        last_saved = None

        self.running = True
        try:
            while self.running:
                frame = None
                try:
                    frame = self.frame_producer.get_frame()
                except Exception:
                    logger.exception("FrameProducer.get_frame() raised")

                if frame is None:
                    time.sleep(0.01)
                    continue

                avg, motion_counter, last_saved, event = self._process_frame(
                    frame, avg, motion_counter, last_saved
                )
                if event is not None:
                    yield event
        finally:
            self.running = False

    def _run_from_camera(self):
        """Run motion detection from camera."""
        cap = cv2.VideoCapture(self.camera_index)
        avg = None
        motion_counter = 0
        last_saved = None

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                avg, motion_counter, last_saved, event = self._process_frame(
                    frame, avg, motion_counter, last_saved
                )
                if event is not None:
                    yield event
        finally:
            cap.release()

    def _process_frame(self, frame, avg, motion_counter, last_saved):
        """Process a single frame and return updated state and optional event.

        Returns:
            tuple: (avg, motion_counter, last_saved, event)
                   event is None unless motion is detected and cooldown passed
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if avg is None:
            return gray.astype("float"), motion_counter, last_saved, None

        cv2.accumulateWeighted(gray, avg, 0.5)
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        _, thresh = cv2.threshold(frame_delta, self.sensitivity, 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        motion = False
        for c in contours:
            if cv2.contourArea(c) < self.min_area:
                continue
            motion = True
            break

        now = datetime.datetime.now()
        if motion:
            motion_counter += 1
            logger.debug("Motion detected; motion_counter=%d", motion_counter)
        else:
            if motion_counter > 0:
                logger.debug("Motion ended; resetting motion_counter")
            motion_counter = 0

        event = None
        if motion_counter >= self.min_motion_frames:
            enough_time = False
            if last_saved is None:
                enough_time = True
            else:
                elapsed = (now - last_saved).total_seconds()
                enough_time = elapsed >= self.cooldown_seconds

            if enough_time:
                timestamp = now.isoformat()
                if self.save_frames:
                    filename = f"motion_{timestamp.replace(':', '-')}.jpg"
                    path = os.path.join(self.frame_dir, filename)
                    try:
                        save_frame(frame, path)
                        logger.info("Motion event saved: %s", path)
                        event = {"timestamp": timestamp, "frame_path": path}
                        last_saved = now
                    except Exception:
                        logger.exception("Failed to save motion frame")
                else:
                    logger.info("Motion event yielded (in-memory) at %s", timestamp)
                    event = {"timestamp": timestamp, "frame": frame}
                    last_saved = now

        return avg, motion_counter, last_saved, event
