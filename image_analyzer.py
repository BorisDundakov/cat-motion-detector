import cv2


# Minimal placeholder for object detection. Users can plug in models here.
class ImageAnalyzer:
    def __init__(self, model_path=None):
        self.model_path = model_path

    def detect_objects(self, image_path):
        # Try to read the image to ensure cv2 is used; return empty list.
        img = cv2.imread(image_path)
        if img is None:
            return []
        return []
