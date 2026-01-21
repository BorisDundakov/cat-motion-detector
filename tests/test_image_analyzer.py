import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from image_analyzer import ImageAnalyzer

analyzer = ImageAnalyzer()
results = analyzer.detect_objects("tests/test_images/test_cat.jpg")  # Replace with your image filename

if results:
    for obj in results:
        print(f"Detected {obj['label']} with confidence {obj['confidence']:.2f}")
        print(f"Bounding box: {obj['box']}")
else:
    print("No cat detected.")