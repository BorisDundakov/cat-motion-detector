# Motion Detector Project — Team Cat

Quick start
-----------

1. Create a virtual environment and install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. (Optional) Configure environment variables (recommended for Discord notifications and runtime settings):

```bash
# Discord webhook used for notifications (recommended)
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# Optional runtime tuning
export FRAME_DIR="frames"
export SENSITIVITY="25"
export MIN_AREA="500"
export CAMERA_INDEX="0"       # or path to a video file
export WEB_HOST="0.0.0.0"
export WEB_PORT="5000"
export DEBUG="False"
export TARGET_OBJECTS="cat,person"
```

3. Run the detector:

```bash
python main.py
```

Notes:
- The application will start a web UI (Socket.IO + Flask) and the motion detector.
- Provide a valid Discord webhook in `DISCORD_WEBHOOK_URL` if you want image notifications.

Camera Source
-------------

- **File**: `motion_detector.py`
  - **Description**: The camera or video source is opened inside the `MotionDetector`
    class using the `camera_index` parameter (default `0`).
  - **Change camera**: To use a different camera index or a video file, update
    `main.py` to pass the desired value to `MotionDetector`:

```python
# Camera index (integer)
detector = MotionDetector(camera_index=1)

# Or use a video file path instead of a camera device
detector = MotionDetector(camera_index='path/to/video.mp4')
```

- **Using an environment variable**: You can set `VIDEO_SOURCE` and parse it in `main.py`:

```python
import os
src = os.environ.get('VIDEO_SOURCE', '0')
try:
    camera_index = int(src)
except ValueError:
    camera_index = src  # treat as path
detector = MotionDetector(camera_index=camera_index)
```

Web UI
------
- The web UI is served by Flask + Flask-SocketIO. By default it runs on
  `WEB_HOST` and `WEB_PORT` from `config.py` (environment variables can override).
- Motion events are available at the frontend via the Socket.IO event `motion_detected`.
- Saved motion images are served from the configured `FRAME_DIR` (default: `frames`).

Notifications
-------------
- Discord notifications are available via a webhook. Set `DISCORD_WEBHOOK_URL`
  in the environment (or in your config) before starting the app.
- The notifier sends only images whose filename starts with `motion_` and includes
  a short caption with a timestamp.

Running tests
-------------

Before running tests, ensure you're in the project root and have a virtual
environment active with the project requirements installed (see Quick start).

Install test dependencies (if any are listed) and run the test suite:

```bash
# run all tests
pytest

# run a specific test file
pytest tests/test_motion_detector.py

# run a single test function
pytest tests/test_motion_detector.py::test_motion_detector_saves_frames -q
```

Troubleshooting
---------------

- Discord notifications not appearing:
  - Verify `DISCORD_WEBHOOK_URL` is set and valid.
  - Check application logs for errors when uploading images.
  - Ensure saved images have filenames starting with `motion_` (the notifier only sends those).

- Camera not opening:
  - Verify camera index or video path is correct.
  - If using a physical camera, ensure no other process is using it.

- Permission errors saving frames:
  - Ensure the process has write permission to `FRAME_DIR`.

Contributing
------------
- Please follow the existing code style and add tests for new behaviors.
- Open an issue or pull request if you want to propose changes.

License
-------
- (Add your project license here)