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

Running tests
-------------

Before running tests, ensure you're in the project root and have a virtual
environment active with the project requirements installed (see Quick start).

Install test dependencies (if you haven't already):

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Run the full test suite with `pytest`:

```bash
pytest
```

Run a single test file or test function:

```bash
# run a specific test file
pytest tests/test_motion_detector.py

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
	- **Description**: The camera or video source is opened inside
		`motion_detector.py` by the `MotionDetector` class. By default it opens
		`camera_index=0` (the first attached camera).
	- **Change camera**: you can pass either a camera index (integer) or a
		video file path (string) to `MotionDetector`. Edit
		[main.py](main.py) and instantiate the detector with the desired source. Examples:

```python
# Use an external camera (index 1)
detector = MotionDetector(camera_index=1)

# Use a video file instead of a camera
detector = MotionDetector(camera_index='path/to/video.mp4')
```

	- **Use an environment variable**: optionally set `VIDEO_SOURCE` and add a
		small snippet in `main.py` to interpret it as an int or path:

```python
import os

src = os.environ.get('VIDEO_SOURCE', '0')
try:
		camera_index = int(src)
except ValueError:
		camera_index = src

detector = MotionDetector(camera_index=camera_index)
```

- **Note**: `main.py` is the entrypoint that creates the `MotionDetector`.

Running tests
-------------

Before running tests, ensure you're in the project root and have a virtual
environment active with the project requirements installed (see Quick start).

Install test dependencies (if you haven't already):

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Run the full test suite with `pytest`:

```bash
pytest
```

Run a single test file or test function:

```bash
# run a specific test file
pytest tests/test_motion_detector.py

# run a single test function
pytest tests/test_motion_detector.py::test_motion_detector_saves_frames -q
```

Test output is written to the terminal. The synthetic motion test created for
the motion detector is at [tests/test_motion_detector.py](tests/test_motion_detector.py).



