import cv2
import threading
import time
import logging


class FrameProducer:
    """
    Continuously captures frames from a camera in a separate thread.
    Provides thread-safe access to the latest frame for multiple consumers.
    """

    def __init__(self, camera_index=0, retry_delay=5):
        """
        Initialize the frame producer.

        Args:
            camera_index: Camera device index (default: 0)
            retry_delay: Seconds to wait before retrying after camera failure
        """
        self.camera_index = camera_index
        self.retry_delay = retry_delay
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._cap = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the frame capture thread."""
        if self._running:
            self.logger.warning("FrameProducer already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self.logger.info(f"FrameProducer started for camera {self.camera_index}")

    def stop(self):
        """Stop the frame capture thread and release the camera."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._release_camera()
        self.logger.info("FrameProducer stopped")

    def get_frame(self):
        """
        Get the latest captured frame in a thread-safe manner.

        Returns:
            numpy.ndarray: The latest frame, or None if no frame is available
        """
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def is_running(self):
        """Check if the frame producer is running."""
        return self._running

    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        while self._running:
            if not self._open_camera():
                self.logger.error(
                    f"Failed to open camera {self.camera_index}, "
                    f"retrying in {self.retry_delay}s"
                )
                time.sleep(self.retry_delay)
                continue

            # Capture frames while camera is open and running
            while self._running and self._cap is not None and self._cap.isOpened():
                ret, frame = self._cap.read()
                if not ret:
                    self.logger.warning("Failed to read frame from camera")
                    break

                # Update the shared frame in a thread-safe manner
                with self._lock:
                    self._frame = frame

            # Camera failed or stopped, release and retry
            self._release_camera()
            if self._running:
                self.logger.info(f"Reconnecting to camera in {self.retry_delay}s")
                time.sleep(self.retry_delay)

    def _open_camera(self):
        """
        Open the camera device.

        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        try:
            self._cap = cv2.VideoCapture(self.camera_index)
            if not self._cap.isOpened():
                return False
            self.logger.info(f"Camera {self.camera_index} opened successfully")
            return True
        except Exception as e:
            self.logger.error(f"Exception opening camera: {e}")
            return False

    def _release_camera(self):
        """Release the camera resource."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            cv2.destroyAllWindows()