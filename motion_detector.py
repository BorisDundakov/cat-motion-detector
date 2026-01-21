import cv2
import os
import datetime
from utils import ensure_dir, save_frame


class MotionDetector:
    def __init__(self, sensitivity=25, min_area=500, camera_index=0):
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.camera_index = camera_index
        self.frame_dir = os.environ.get("FRAME_DIR", "frames")
        ensure_dir(self.frame_dir)

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        first_frame = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break

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

        cap.release()
