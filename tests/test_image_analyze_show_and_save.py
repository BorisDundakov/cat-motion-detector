import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from image_analyzer import ImageAnalyzer

# Initialize the analyzer
analyzer = ImageAnalyzer()

# Test with images from test_images directory
test_images_dir = "tests/test_images"
jpg_files = [f for f in os.listdir(test_images_dir) if f.lower().endswith(".jpg")]

if not jpg_files:
    print("No JPG files found in tests/test_images directory.")
else:
    print(f"Found {len(jpg_files)} image(s) to test.\n")
    for image_file in jpg_files:
        image_path = os.path.join(test_images_dir, image_file)
        print(f"Testing image: {image_file}")
        print("=" * 50)
        result = analyzer.show_and_save_cat_detection(image_path)
        if result:
            print(f"✓ Cat detected and saved successfully!\n")
        else:
            print(f"✗ No cat detected in this image.\n")
