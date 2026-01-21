import os
import cv2


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def save_frame(frame, path):
    ensure_dir(os.path.dirname(path) or ".")
    # OpenCV expects BGR; frame should be as-captured
    cv2.imwrite(path, frame)
