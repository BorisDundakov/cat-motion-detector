import os

CONFIG = {
    "TELEGRAM_TOKEN": os.environ.get("TELEGRAM_TOKEN"),
    "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID"),
    "SENSITIVITY": int(os.environ.get("SENSITIVITY", "25")),
    "MIN_AREA": int(os.environ.get("MIN_AREA", "500")),
    "FRAME_DIR": os.environ.get("FRAME_DIR", "frames"),
    "WEB_HOST": os.environ.get("WEB_HOST", "0.0.0.0"),
    "WEB_PORT": int(os.environ.get("WEB_PORT", "5000")),
    "DEBUG": os.environ.get("DEBUG", "False").lower() == "true",
    "CAMERA_INDEX": int(os.environ.get("CAMERA_INDEX", "0")),
    "EXPECTED_LABEL": os.environ.get("EXPECTED_LABEL", "cat"),
    "ANALYZER_MODEL_PATH": os.environ.get(
        "ANALYZER_MODEL_PATH", "yolo_files/yolov3.weights"
    ),
    "ANALYZER_CONFIG_PATH": os.environ.get(
        "ANALYZER_CONFIG_PATH", "yolo_files/yolov3.cfg"
    ),
    "ANALYZER_CLASSES_PATH": os.environ.get(
        "ANALYZER_CLASSES_PATH", "yolo_files/coco.names"
    ),
    "TARGET_OBJECTS": os.environ.get("TARGET_OBJECTS", "cat,person"),
}
