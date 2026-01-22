import numpy as np
import cv2
import types
import os
import sys

# Ensure project root is on sys.path so tests can import modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import motion_detector
from motion_detector import MotionDetector


class FakeCapture:
    def __init__(self, frames):
        self.frames = frames
        self.i = 0

    def read(self):
        if self.i >= len(self.frames):
            return False, None
        f = self.frames[self.i]
        self.i += 1
        return True, f

    def release(self):
        pass


def make_frame(shape=(100, 100, 3), color=0):
    return np.full(shape, color, dtype=np.uint8)


def test_motion_detector_saves_frames(monkeypatch, tmp_path):
    # Build frames: three static, two motion, three static
    static = make_frame()
    motion = static.copy()
    # draw a white rectangle to create motion
    cv2.rectangle(motion, (10, 10), (30, 30), (255, 255, 255), -1)

    frames = (
        [static.copy() for _ in range(3)]
        + [motion.copy() for _ in range(2)]
        + [static.copy() for _ in range(3)]
    )

    fake = FakeCapture(frames)

    # Monkeypatch VideoCapture to return our fake capture
    monkeypatch.setattr(cv2, "VideoCapture", lambda idx: fake)

    saved = []

    # Monkeypatch save_frame to capture the path instead of writing to disk
    def fake_save_frame(frame, path):
        saved.append(path)

    # Patch the save_frame used inside motion_detector (it was imported there)
    monkeypatch.setattr(motion_detector, "save_frame", fake_save_frame)

    # Use a short cooldown and small min_area so the small rectangle is detected
    detector = MotionDetector(
        sensitivity=10,
        min_area=50,
        camera_index=0,
        min_motion_frames=1,
        cooldown_seconds=0,
    )

    events = list(detector.run())

    # We expect at least one event (two motion frames present)
    assert len(events) >= 1
    # Save was called at least once and paths look like our frame filenames
    assert len(saved) == len(events)
    for p in saved:
        assert os.path.basename(p).startswith("motion_")
