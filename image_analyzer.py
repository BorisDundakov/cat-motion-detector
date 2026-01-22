import cv2
import numpy as np
import os
import datetime
from config import CONFIG


class ImageAnalyzer:
    """YOLO-based image analyzer for detecting objects in images."""

    def __init__(
        self,
        model_path=None,
        config_path=None,
        classes_path=None,
        confidence_threshold=0.5,
        nms_threshold=0.4,
        target_objects=None,
    ):
        """
        Initialize the ImageAnalyzer with YOLO model.

        Args:
            model_path: Path to YOLO weights file
            config_path: Path to YOLO config file
            classes_path: Path to class names file
            confidence_threshold: Minimum confidence for detection (0.0 to 1.0)
            nms_threshold: Non-maximum suppression threshold
            target_objects: Object(s) to detect. Can be a string or list of strings (default: from config, "cat,person")
        """
        self.model_path = model_path or "yolo_files/yolov3.weights"
        self.config_path = config_path or "yolo_files/yolov3.cfg"
        self.classes_path = classes_path or "yolo_files/coco.names"
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        
        # Use target_objects from config if not provided
        if target_objects is None:
            target_objects = CONFIG.get("TARGET_OBJECTS", "cat,person")
        
        # Convert target_objects to a list for uniform handling
        if isinstance(target_objects, str):
            # Handle comma-separated strings
            self.target_objects = [obj.strip() for obj in target_objects.split(",")]
        else:
            self.target_objects = target_objects

        # Load YOLO model
        try:
            self.net = cv2.dnn.readNet(self.model_path, self.config_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model: {e}")

        # Load class labels
        if os.path.exists(self.classes_path):
            with open(self.classes_path, "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
        else:
            self.classes = []
            print(f"Warning: Classes file not found at {self.classes_path}")

    def detect_objects(self, image):
        """
        Detect target objects in an image using YOLO.

        Args:
            image: numpy array (image data) or path to the image file (string)

        Returns:
            List of dictionaries containing detection results with label, confidence, and bounding box
        """
        # Accept either a file path or a numpy ndarray
        if isinstance(image, np.ndarray):
            img = image
        elif isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                return []
        else:
            # Invalid input type
            return []

        return self._detect_in_image(img)

    def _detect_in_image(self, img):
        """
        Internal method to detect target objects in a loaded image.

        Args:
            img: OpenCV image (numpy array)

        Returns:
            List of dictionaries containing detection results
        """
        height, width = img.shape[:2]

        # Prepare the image for YOLO
        blob = cv2.dnn.blobFromImage(
            img, 1 / 255.0, (416, 416), swapRB=True, crop=False
        )
        self.net.setInput(blob)

        # Get YOLO output layer names
        layer_names = self.net.getLayerNames()
        output_layers = [
            layer_names[i - 1] for i in self.net.getUnconnectedOutLayers().flatten()
        ]

        # Perform forward pass
        detections = self.net.forward(output_layers)

        # Collect all detections for NMS
        boxes = []
        confidences = []
        class_ids = []

        for output in detections:
            for detection in output:
                scores = detection[5:]
                class_id = int(scores.argmax())
                confidence = scores[class_id]

                if confidence > self.confidence_threshold:
                    # Check if the detected object is in our target list
                    if self.classes and self.classes[class_id] in self.target_objects:
                        center_x = int(detection[0] * width)
                        center_y = int(detection[1] * height)
                        w = int(detection[2] * width)
                        h = int(detection[3] * height)

                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)

        # Apply Non-Maximum Suppression to remove overlapping boxes
        results = []
        if boxes:
            indices = cv2.dnn.NMSBoxes(
                boxes, confidences, self.confidence_threshold, self.nms_threshold
            )
            if len(indices) > 0:
                for i in indices.flatten():
                    results.append(
                        {
                            "label": self.classes[class_ids[i]],
                            "confidence": confidences[i],
                            "box": boxes[i],
                        }
                    )

        return results

    def draw_detections(self, img, results, color=(0, 255, 0), thickness=2):
        """
        Draw bounding boxes and labels on an image.

        Args:
            img: OpenCV image (numpy array)
            results: List of detection results from detect_objects
            color: BGR color tuple for bounding boxes
            thickness: Line thickness for rectangles

        Returns:
            Image with drawn bounding boxes
        """
        for obj in results:
            x, y, w, h = obj["box"]
            cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)
            label = f"{obj['label']} {obj['confidence']:.2f}"
            cv2.putText(
                img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, thickness
            )
        return img

    def show_and_save_identified_image(
        self, image, notification_dir="notification_iamges", show_image=True
    ):
        """
        Detects target objects, draws bounding boxes, optionally visualizes, and saves the image with a timestamped filename if objects are detected.

        Args:
            image: numpy array (image data) or path to the image file (string)
            notification_dir: Directory to save detected images
            show_image: Whether to display the image with detections

        Returns:
            Tuple of (success: bool, save_path: str or None, num_objects: int)
        """
        # Accept either a file path or a numpy ndarray
        if isinstance(image, np.ndarray):
            img = image
        elif isinstance(image, str):
            img = cv2.imread(image)
            if img is None:
                print(f"Error: Could not read image: {image}")
                return False, None, 0
        else:
            print(f"Error: Invalid image input type")
            return False, None, 0

        results = self._detect_in_image(img)
        num_objects = len(results)

        if not results:
            print("No target objects detected.")
            return False, None, 0

        # Draw detections on image
        img = self.draw_detections(img, results)


        # Save to notification directory with timestamp
        try:
            os.makedirs(notification_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%y-%m-%d_%H-%M-%S")
            save_path = os.path.join(notification_dir, f"{timestamp}.jpg")
            cv2.imwrite(save_path, img)
            print(f"Saved detected image to: {save_path}")
            print(f"Number of objects detected: {num_objects}")
            return True, save_path, num_objects
        except Exception as e:
            print(f"Error saving image: {e}")
            return False, None, num_objects