# Motion Detector Project — Team Cat
Quick start
-----------

1. Create a virtual environment and install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. (Optional) Set Telegram env vars to enable notifications:

```bash
export TELEGRAM_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
```

3. Run the detector:

```bash
python main.py
```

Camera Source
-------------

- **File**: [motion_detector.py](motion_detector.py)
	- **Description**: The camera is opened inside `motion_detector.py` by the
		`MotionDetector` class using the `camera_index` parameter (default `0`).
	- **Change camera**: To use a different camera or a video file, edit
		[main.py](main.py) and instantiate `MotionDetector` with the
		`camera_index` argument, for example:

```python
detector = MotionDetector(camera_index=1)
# or use a video file path by passing an integer or by modifying the class
```

- **Note**: `main.py` is the entrypoint that creates the `MotionDetector`.


