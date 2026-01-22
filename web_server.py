import os
import glob
import time
import cv2
from flask import (
    Flask,
    render_template,
    Response,
    send_from_directory,
    current_app,
    request,
    jsonify,
)
from flask_socketio import SocketIO
from config import CONFIG, save_config, load_config
from frame_producer import FrameProducer

app = Flask(__name__)
app.config["SECRET_KEY"] = "cat-motion-detector-secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# Store recent motion events in memory
recent_events = []
MAX_EVENTS = 100


def restart_camera():
    """Restart the camera with new configuration."""
    frame_producer = current_app.config.get("FRAME_PRODUCER")
    if frame_producer:
        print(f"Restarting camera with index {CONFIG.get('CAMERA_INDEX', 0)}...")
        # Stop the old camera
        frame_producer.stop()
        time.sleep(0.5)  # Give it time to release

        # Update camera index and restart
        new_producer = FrameProducer(camera_index=CONFIG.get("CAMERA_INDEX", 0))
        new_producer.start()
        current_app.config["FRAME_PRODUCER"] = new_producer
        print("Camera restarted successfully")


def add_event(event):
    """Add a motion event to the recent events list."""
    recent_events.insert(0, event)
    if len(recent_events) > MAX_EVENTS:
        recent_events.pop()


@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template("index.html")


@app.route("/api/events", methods=["GET"])
def api_get_recent_events():
    """API endpoint to get recent events."""
    return jsonify({"events": recent_events})


@app.route("/settings")
def settings():
    """Serve the settings/config page."""
    # Load COCO class names
    coco_classes = []
    classes_path = CONFIG.get("ANALYZER_CLASSES_PATH", "yolo_files/coco.names")
    if os.path.exists(classes_path):
        with open(classes_path, "r") as f:
            coco_classes = [line.strip() for line in f.readlines()]

    return render_template("settings.html", config=CONFIG, coco_classes=coco_classes)


@app.route("/api/config", methods=["GET"])
def get_config():
    """API endpoint to get current config values."""
    return jsonify(CONFIG)


@app.route("/api/config", methods=["POST"])
def update_config():
    """API endpoint to update config values."""
    try:
        data = request.get_json()
        camera_index_changed = False
        config_changed = False
        detection_config_changed = False
        old_camera_index = CONFIG.get("CAMERA_INDEX", 0)

        # Update CONFIG with new values and track changes
        for key, value in data.items():
            if key in CONFIG:
                old_value = CONFIG[key]

                # Convert types appropriately
                if key in ["SENSITIVITY", "MIN_AREA", "CAMERA_INDEX", "WEB_PORT"]:
                    new_value = int(value)
                    # Validate camera index is non-negative
                    if key == "CAMERA_INDEX" and new_value < 0:
                        continue  # Skip invalid camera index
                    # Validate sensitivity and min_area are positive
                    if key in ["SENSITIVITY", "MIN_AREA"] and new_value < 1:
                        continue  # Skip invalid values

                    if old_value != new_value:
                        config_changed = True
                        CONFIG[key] = new_value

                        if key == "CAMERA_INDEX":
                            camera_index_changed = True
                        # Mark that detection config changed
                        elif key in ["SENSITIVITY", "MIN_AREA"]:
                            detection_config_changed = True
                elif key == "DEBUG":
                    new_value = str(value).lower() == "true"
                    if old_value != new_value:
                        config_changed = True
                        CONFIG[key] = new_value
                else:
                    if old_value != value:
                        config_changed = True
                        CONFIG[key] = value

        # Only save if something actually changed
        save_success = True
        if config_changed:
            save_success = save_config(CONFIG)

        # Restart camera only if camera index actually changed
        if camera_index_changed:
            restart_camera()

        # Emit event to notify clients of config change (only if changed)
        if config_changed:
            socketio.emit("config_updated", CONFIG)

        # Build appropriate message
        if not config_changed:
            message = "No changes detected."
        else:
            message = "Settings saved successfully!"
            if camera_index_changed:
                message += " Camera restarted."
            if detection_config_changed:
                message += " Please restart the application for sensitivity/area changes to take effect."
            # TARGET_OBJECTS changes are applied automatically, no restart needed

        return jsonify(
            {
                "success": True,
                "config": CONFIG,
                "saved": save_success,
                "message": message,
                "changed": config_changed,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/video_feed")
def video_feed():
    """Route for MJPEG video stream."""
    # Get frame_producer from app config before creating generator
    frame_producer = current_app.config.get("FRAME_PRODUCER")

    if frame_producer is None:
        return "Frame producer not initialized", 503

    def generate():
        while True:
            # Get the current frame from the frame producer
            frame = frame_producer.get_frame()

            if frame is not None:
                try:
                    # Encode the frame as JPEG
                    ret, buffer = cv2.imencode(".jpg", frame)

                    if ret:
                        frame_data = buffer.tobytes()

                        # Yield the frame in MJPEG format
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + frame_data + b"\r\n"
                        )
                except Exception as e:
                    print(f"Error encoding frame: {e}")

            # Wait a bit before getting the next frame
            time.sleep(0.1)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/frames/<filename>")
def serve_frame(filename):
    """Serve individual frame images."""
    frame_dir = CONFIG.get("FRAME_DIR", "frames")
    return send_from_directory(frame_dir, filename)


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    print("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    print("Client disconnected")


def emit_motion_event(event):
    """Emit a motion detection event to all connected clients."""
    # Prepare event data for web clients
    web_event = {
        "timestamp": event["timestamp"],
        "frame_path": event["frame_path"],
        "image_url": f"/frames/{os.path.basename(event['frame_path'])}",
    }

    # Add to recent events (store the web_event with image_url)
    add_event(web_event)

    # Broadcast to all connected clients
    socketio.emit("motion_detected", web_event)


def get_recent_events():
    """Get the list of recent motion events."""
    return recent_events


if __name__ == "__main__":
    # This won't be used when integrated with main.py,
    # but useful for standalone testing
    socketio.run(
        app,
        host=CONFIG.get("WEB_HOST", "0.0.0.0"),
        port=CONFIG.get("WEB_PORT", 5000),
        debug=CONFIG.get("DEBUG", False),
    )