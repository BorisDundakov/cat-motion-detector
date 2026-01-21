import cv2
import os
import datetime
import time
from utils import ensure_dir, save_frame


class MotionDetector:
    def __init__(self, frame_producer, sensitivity=25, min_area=500):
        """
        Initialize the motion detector.

        Args:
            frame_producer: FrameProducer instance to consume frames from
            sensitivity: Threshold for motion detection (default: 25)
            min_area: Minimum contour area to consider as motion (default: 500)
        """
        self.frame_producer = frame_producer
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.frame_dir = os.environ.get("FRAME_DIR", "frames")
        self.running = False
        ensure_dir(self.frame_dir)

    def run(self):
        """
        Run motion detection on frames from the frame producer.
        
        Yields:
            dict: Motion event with 'timestamp' and 'frame_path' keys
        """
        first_frame = None
        self.running = True

        try:
            while self.running:
                frame = self.frame_producer.get_frame()
                if frame is None:
                    # No frame available yet, wait briefly
                    time.sleep(0.01)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if first_frame is None:
                    first_frame = gray
                    continue

                frame_delta = cv2.absdiff(first_frame, gray)
                thresh_ret = cv2.threshold(
                    frame_delta, self.sensitivity, 255, cv2.THRESH_BINARY
                )
                thresh = thresh_ret[1]
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

                if motion:
                    timestamp = datetime.datetime.now().isoformat()
                    filename = f"motion_{timestamp.replace(':', '-')}.jpg"
                    path = os.path.join(self.frame_dir, filename)
                    save_frame(frame, path)
                    yield {"timestamp": timestamp, "frame_path": path}
        finally:
            self.running = False
